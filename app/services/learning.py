from datetime import date, datetime, timedelta, timezone

from app.integrations.anki import AnkiAdapter, AnkiDailyStats
from app.integrations.github import GitHubAdapter, GitHubDailyPythonActivity
from app.models.activity import ActivityEvent, ActivityEventType
from app.models.anki import (
    AnkiDailySnapshot,
    AnkiDifficultCardTrend,
    AnkiHistoryDay,
    AnkiHistoryOverview,
    AnkiReviewedTodayOverview,
    AnkiTodayOverview,
)
from app.models.japanese import JapaneseDashboardOverview
from app.models.learning import LearningPulse, LearningSession, LearningSessionCreate, LearningSubject
from app.repositories.activity import ActivityRepository
from app.repositories.anki import AnkiSnapshotRepository
from app.repositories.learning import LearningRepository


class LearningService:
    def __init__(
        self,
        learning_repository: LearningRepository | None = None,
        activity_repository: ActivityRepository | None = None,
        anki_snapshot_repository: AnkiSnapshotRepository | None = None,
        anki_adapter: AnkiAdapter | None = None,
        github_adapter: GitHubAdapter | None = None,
    ) -> None:
        self.learning_repository = learning_repository or LearningRepository()
        self.activity_repository = activity_repository or ActivityRepository()
        self.anki_snapshot_repository = anki_snapshot_repository or AnkiSnapshotRepository()
        self.anki_adapter = anki_adapter or AnkiAdapter()
        self.github_adapter = github_adapter or GitHubAdapter()

    def create_session(self, payload: LearningSessionCreate) -> LearningSession:
        ended_at = payload.ended_at
        started_at = payload.started_at

        if started_at is None and ended_at is None:
            ended_at = datetime.now(timezone.utc)
            started_at = ended_at - timedelta(minutes=payload.duration_minutes)
        elif started_at is None and ended_at is not None:
            started_at = ended_at - timedelta(minutes=payload.duration_minutes)
        elif started_at is not None and ended_at is None:
            ended_at = started_at + timedelta(minutes=payload.duration_minutes)

        session = LearningSession(
            subject=payload.subject,
            started_at=started_at,
            ended_at=ended_at,
            duration_minutes=payload.duration_minutes,
            source=payload.source,
            summary=payload.summary,
            difficulty=payload.difficulty,
            energy_level=payload.energy_level,
            tags=payload.tags,
        )
        self.learning_repository.create_session(session)
        self.activity_repository.create_event(
            ActivityEvent(
                event_type=ActivityEventType.learning_session_created,
                subject=session.subject,
                source=session.source.value,
                payload={
                    "session_id": session.id,
                    "subject": session.subject.value,
                    "duration_minutes": session.duration_minutes,
                    "summary": session.summary,
                },
            )
        )
        return session

    def list_sessions(self, limit: int = 100, offset: int = 0) -> list[LearningSession]:
        return self.learning_repository.list_sessions(limit=limit, offset=offset)

    async def build_today_pulse(self) -> LearningPulse:
        return await self.build_pulse(date.today())

    def get_anki_snapshot(self, target_date: date) -> AnkiDailySnapshot | None:
        return self.anki_snapshot_repository.get_snapshot_for_date(target_date)

    async def get_anki_reviewed_today_overview(self, target_date: date | None = None) -> AnkiReviewedTodayOverview:
        return await self.anki_adapter.get_reviewed_today_overview(target_date=target_date)

    async def get_japanese_dashboard(
        self,
        target_date: date | None = None,
        history_days: int = 7,
        difficult_days: int = 14,
        difficult_limit: int = 10,
    ) -> JapaneseDashboardOverview:
        target_date = target_date or date.today()
        pulse = await self.build_pulse(target_date)
        if target_date == date.today():
            anki_today = await self.get_anki_today_overview()
        else:
            snapshot = self.anki_snapshot_repository.get_snapshot_for_date(target_date)
            anki_today = self.build_anki_overview(
                stats=await self._anki_stats_for_date(target_date),
                source="snapshot" if snapshot is not None else "live",
                imported_at=snapshot.imported_at if snapshot is not None else None,
            )
        reviewed_today = await self.get_anki_reviewed_today_overview(target_date=target_date)
        history = self.get_anki_history(days=max(1, history_days), end_date=target_date)
        difficult_cards = self.get_anki_difficult_card_history(
            days=max(1, difficult_days),
            limit=max(1, difficult_limit),
            end_date=target_date,
        )
        japanese_sessions = [
            session
            for session in self.learning_repository.list_sessions_for_date(target_date)
            if session.subject == LearningSubject.japanese
        ]
        japanese_minutes = sum(session.duration_minutes for session in japanese_sessions)
        return JapaneseDashboardOverview(
            target_date=target_date,
            pulse=pulse,
            anki_today=anki_today,
            reviewed_today=reviewed_today,
            history=history,
            difficult_cards=difficult_cards,
            japanese_sessions=japanese_sessions,
            japanese_session_count=len(japanese_sessions),
            japanese_minutes=japanese_minutes,
        )

    def get_anki_history(self, days: int = 7, end_date: date | None = None) -> AnkiHistoryOverview:
        snapshots = list(reversed(self.anki_snapshot_repository.list_recent_snapshots(days, end_date=end_date)))
        history_days = [
            AnkiHistoryDay(
                snapshot_date=snapshot.snapshot_date,
                reviews=snapshot.reviews,
                accuracy=snapshot.accuracy,
                non_again_rate=snapshot.non_again_rate,
                again_count=snapshot.again_count,
                hard_count=snapshot.hard_count,
                good_count=snapshot.good_count,
                easy_count=snapshot.easy_count,
                due_count=snapshot.due_count,
                imported_at=snapshot.imported_at,
            )
            for snapshot in snapshots
        ]
        best_snapshot = max(snapshots, key=lambda snapshot: snapshot.reviews, default=None)
        accuracy_values = [snapshot.accuracy for snapshot in snapshots if snapshot.accuracy is not None]
        average_accuracy = (
            round(sum(accuracy_values) / len(accuracy_values), 1) if accuracy_values else None
        )
        return AnkiHistoryOverview(
            days=history_days,
            streak_days=self._anki_streak_days(snapshots),
            best_review_day=best_snapshot.snapshot_date if best_snapshot is not None else None,
            total_reviews=sum(snapshot.reviews for snapshot in snapshots),
            average_accuracy=average_accuracy,
        )

    def get_anki_difficult_card_history(
        self,
        days: int = 7,
        limit: int = 10,
        end_date: date | None = None,
    ) -> list[AnkiDifficultCardTrend]:
        snapshots = self.anki_snapshot_repository.list_recent_snapshots(days, end_date=end_date)
        trends: dict[str, AnkiDifficultCardTrend] = {}
        for snapshot in snapshots:
            for label in snapshot.difficult_cards:
                existing = trends.get(label)
                if existing is None:
                    trends[label] = AnkiDifficultCardTrend(
                        label=label,
                        hit_count=1,
                        last_seen_on=snapshot.snapshot_date,
                    )
                else:
                    existing.hit_count += 1
                    if snapshot.snapshot_date > existing.last_seen_on:
                        existing.last_seen_on = snapshot.snapshot_date
        return sorted(
            trends.values(),
            key=lambda trend: (-trend.hit_count, trend.label.casefold()),
        )[:limit]

    async def get_anki_today_overview(self) -> AnkiTodayOverview:
        snapshot = self.anki_snapshot_repository.get_snapshot_for_date(date.today())
        if snapshot is not None:
            return self.build_anki_overview(
                stats=AnkiDailyStats(
                    enabled=True,
                    connected=True,
                    scope=snapshot.scope,
                    reviews=snapshot.reviews,
                    accuracy=snapshot.accuracy,
                    non_again_rate=snapshot.non_again_rate,
                    again_count=snapshot.again_count,
                    hard_count=snapshot.hard_count,
                    good_count=snapshot.good_count,
                    easy_count=snapshot.easy_count,
                    due_count=snapshot.due_count,
                    new_due_count=snapshot.new_due_count,
                    learn_due_count=snapshot.learn_due_count,
                    review_due_count=snapshot.review_due_count,
                    difficult_cards=snapshot.difficult_cards,
                    decks=snapshot.decks,
                ),
                source="snapshot",
                imported_at=snapshot.imported_at,
            )

        stats = await self.anki_adapter.get_daily_stats(date.today())
        return self.build_anki_overview(stats=stats, source="live", imported_at=None)

    async def import_anki_today(self) -> AnkiDailyStats:
        stats = await self.anki_adapter.get_daily_stats(date.today())
        if stats.connected:
            snapshot = self.anki_snapshot_repository.upsert_daily_snapshot(
                AnkiDailySnapshot(
                    snapshot_date=date.today(),
                    scope=stats.scope,
                    reviews=stats.reviews,
                    accuracy=stats.accuracy,
                    non_again_rate=stats.non_again_rate,
                    again_count=stats.again_count,
                    hard_count=stats.hard_count,
                    good_count=stats.good_count,
                    easy_count=stats.easy_count,
                    due_count=stats.due_count,
                    new_due_count=stats.new_due_count,
                    learn_due_count=stats.learn_due_count,
                    review_due_count=stats.review_due_count,
                    difficult_cards=stats.difficult_cards,
                    decks=stats.decks,
                )
            )
            self.activity_repository.create_event(
                ActivityEvent(
                    event_type=ActivityEventType.anki_reviews_imported,
                    subject=LearningSubject.japanese,
                    source="anki",
                    payload={
                        **stats.model_dump(mode="json"),
                        "snapshot_id": snapshot.id,
                        "snapshot_date": snapshot.snapshot_date.isoformat(),
                        "imported_at": snapshot.imported_at.isoformat(),
                    },
                )
            )
        return stats

    async def import_github_today(self) -> GitHubDailyPythonActivity:
        activity = await self.github_adapter.get_daily_python_activity(date.today())
        if activity.connected:
            self.activity_repository.create_event(
                ActivityEvent(
                    event_type=ActivityEventType.github_commits_imported,
                    subject=LearningSubject.python,
                    source="github",
                    payload=activity.model_dump(mode="json"),
                )
            )
        return activity

    async def build_pulse(self, target_date: date) -> LearningPulse:
        sessions = self.learning_repository.list_sessions_for_date(target_date)
        anki_stats = await self._anki_stats_for_date(target_date)
        github_stats = await self.github_adapter.get_daily_python_activity(target_date)
        integration_warnings = []
        if anki_stats.error:
            integration_warnings.append(f"Anki: {anki_stats.error}")
        if github_stats.error:
            integration_warnings.append(f"GitHub: {github_stats.error}")

        python_minutes = sum(
            session.duration_minutes for session in sessions if session.subject == LearningSubject.python
        )
        japanese_minutes = sum(
            session.duration_minutes for session in sessions if session.subject == LearningSubject.japanese
        )
        sre_minutes = sum(
            session.duration_minutes for session in sessions if session.subject == LearningSubject.sre
        )
        total_minutes = python_minutes + japanese_minutes + sre_minutes
        focus_score = self._calculate_focus_score(
            python_minutes=python_minutes,
            japanese_minutes=japanese_minutes,
            sre_minutes=sre_minutes,
            anki_reviews=anki_stats.reviews,
            github_commits=github_stats.python_commits,
        )

        return LearningPulse(
            date=target_date,
            python_minutes=python_minutes,
            japanese_minutes=japanese_minutes,
            sre_minutes=sre_minutes,
            total_minutes=total_minutes,
            session_count=len(sessions),
            anki_reviews=anki_stats.reviews,
            anki_accuracy=anki_stats.accuracy,
            anki_difficult_cards=anki_stats.difficult_cards,
            github_commits=github_stats.commits,
            github_python_commits=github_stats.python_commits,
            github_repositories=github_stats.repositories,
            github_python_files=github_stats.python_files,
            focus_score=focus_score,
            summary=self._build_summary(
                python_minutes,
                japanese_minutes,
                sre_minutes,
                anki_stats.reviews,
                github_stats.python_commits,
            ),
            tomorrow_priority=self._build_tomorrow_priority(python_minutes, japanese_minutes, sre_minutes),
            integration_warnings=integration_warnings,
        )

    async def _anki_stats_for_date(self, target_date: date) -> AnkiDailyStats:
        snapshot = self.anki_snapshot_repository.get_snapshot_for_date(target_date)
        if snapshot is not None:
            return AnkiDailyStats(
                enabled=True,
                connected=True,
                scope=snapshot.scope,
                reviews=snapshot.reviews,
                accuracy=snapshot.accuracy,
                non_again_rate=snapshot.non_again_rate,
                again_count=snapshot.again_count,
                hard_count=snapshot.hard_count,
                good_count=snapshot.good_count,
                easy_count=snapshot.easy_count,
                due_count=snapshot.due_count,
                new_due_count=snapshot.new_due_count,
                learn_due_count=snapshot.learn_due_count,
                review_due_count=snapshot.review_due_count,
                difficult_cards=snapshot.difficult_cards,
                decks=snapshot.decks,
            )
        return await self.anki_adapter.get_daily_stats(target_date)

    def build_anki_overview(
        self,
        stats: AnkiDailyStats,
        source: str,
        imported_at: datetime | None,
    ) -> AnkiTodayOverview:
        recent_snapshots = self.anki_snapshot_repository.list_recent_snapshots(30)
        if source == "live" and stats.reviews > 0 and all(
            snapshot.snapshot_date != date.today() for snapshot in recent_snapshots
        ):
            recent_snapshots = [
                AnkiDailySnapshot(
                    snapshot_date=date.today(),
                    scope=stats.scope,
                    reviews=stats.reviews,
                    accuracy=stats.accuracy,
                    non_again_rate=stats.non_again_rate,
                    again_count=stats.again_count,
                    hard_count=stats.hard_count,
                    good_count=stats.good_count,
                    easy_count=stats.easy_count,
                    due_count=stats.due_count,
                    new_due_count=stats.new_due_count,
                    learn_due_count=stats.learn_due_count,
                    review_due_count=stats.review_due_count,
                    difficult_cards=stats.difficult_cards,
                    decks=stats.decks,
                    imported_at=imported_at or datetime.now(timezone.utc),
                ),
                *recent_snapshots,
            ]
        review_load = self._anki_review_load(stats.reviews)
        summary = self._anki_summary(stats.reviews, stats.accuracy, stats.again_count)
        recommendation = self._anki_recommendation(stats.reviews, stats.accuracy, stats.again_count)
        sync_status, sync_hint = self._anki_sync_guidance(source=source, imported_at=imported_at, connected=stats.connected)
        return AnkiTodayOverview(
            enabled=stats.enabled,
            connected=stats.connected,
            source=source,
            scope=stats.scope,
            sync_status=sync_status,
            sync_hint=sync_hint,
            imported_at=imported_at,
            reviews=stats.reviews,
            accuracy=stats.accuracy,
            non_again_rate=stats.non_again_rate,
            again_count=stats.again_count,
            hard_count=stats.hard_count,
            good_count=stats.good_count,
            easy_count=stats.easy_count,
            due_count=stats.due_count,
            new_due_count=stats.new_due_count,
            learn_due_count=stats.learn_due_count,
            review_due_count=stats.review_due_count,
            streak_days=self._anki_streak_days(recent_snapshots),
            difficult_cards=stats.difficult_cards,
            decks=stats.decks,
            configured_decks=stats.configured_decks,
            missing_decks=stats.missing_decks,
            review_load=review_load,
            summary=summary,
            recommendation=recommendation,
            error=stats.error,
        )

    def _anki_sync_guidance(self, source: str, imported_at: datetime | None, connected: bool) -> tuple[str, str]:
        if not connected:
            return (
                "anki_unavailable",
                "Open desktop Anki, sync it, and run import-anki after AnkiConnect becomes reachable.",
            )

        if source == "live":
            return (
                "live_not_snapshotted",
                "If you reviewed on mobile, sync phone -> AnkiWeb -> desktop Anki, then run import-anki to save today's snapshot.",
            )

        if imported_at is None:
            return (
                "snapshot_unknown_age",
                "If you reviewed more cards on mobile after the last import, sync desktop Anki and run import-anki again.",
            )

        age = datetime.now(timezone.utc) - imported_at.astimezone(timezone.utc)
        if age >= timedelta(hours=6):
            return (
                "snapshot_may_be_stale",
                "This snapshot is a few hours old. If you reviewed more on mobile since then, sync desktop Anki and rerun import-anki.",
            )

        return (
            "snapshot_fresh",
            "Snapshot looks fresh. After more mobile reviews later today, sync desktop Anki and rerun import-anki.",
        )

    def _anki_streak_days(self, snapshots: list[AnkiDailySnapshot]) -> int:
        snapshot_dates = sorted(
            {snapshot.snapshot_date for snapshot in snapshots if snapshot.reviews > 0},
            reverse=True,
        )
        if not snapshot_dates:
            return 0

        streak_days = 0
        expected_date = snapshot_dates[0]
        for snapshot_date in snapshot_dates:
            if snapshot_date != expected_date:
                break
            streak_days += 1
            expected_date -= timedelta(days=1)
        return streak_days

    def _anki_review_load(self, reviews: int) -> str:
        if reviews == 0:
            return "none"
        if reviews < 20:
            return "light"
        if reviews < 80:
            return "steady"
        return "heavy"

    def _anki_summary(self, reviews: int, accuracy: float | None, again_count: int) -> str:
        if reviews == 0:
            return "No Anki reviews recorded today."
        if accuracy is None:
            return f"Reviewed {reviews} cards today."
        if accuracy >= 90 and again_count <= 5:
            return f"Strong Anki day: {reviews} reviews at {accuracy:.1f}% accuracy."
        if accuracy < 75:
            return f"Challenging Anki day: {reviews} reviews at {accuracy:.1f}% accuracy."
        return f"Solid Anki day: {reviews} reviews, {again_count} Again answers."

    def _anki_recommendation(self, reviews: int, accuracy: float | None, again_count: int) -> str:
        if reviews == 0:
            return "Do one short Anki review block to keep the streak warm."
        if accuracy is not None and accuracy < 75:
            return "Slow down on the hardest cards and review leeches before adding new material."
        if again_count >= 10:
            return "Revisit the cards you missed most and do a shorter follow-up review later."
        if reviews >= 80:
            return "Keep tomorrow's Anki block lighter so review fatigue does not stack up."
        return "Keep the same Anki pace tomorrow and pair it with one focused grammar or coding block."

    def _calculate_focus_score(
        self,
        python_minutes: int,
        japanese_minutes: int,
        sre_minutes: int,
        anki_reviews: int,
        github_commits: int,
    ) -> int:
        score = 0
        score += min(python_minutes, 90) // 3
        score += min(japanese_minutes, 90) // 3
        score += min(sre_minutes, 90) // 3
        score += min(anki_reviews, 100) // 5
        score += min(github_commits, 5) * 4
        return min(score, 100)

    def _build_summary(
        self,
        python_minutes: int,
        japanese_minutes: int,
        sre_minutes: int,
        anki_reviews: int,
        github_commits: int,
    ) -> str:
        parts = []
        if python_minutes:
            parts.append(f"Python {python_minutes} min")
        if japanese_minutes:
            parts.append(f"Japanese {japanese_minutes} min")
        if sre_minutes:
            parts.append(f"SRE {sre_minutes} min")
        if anki_reviews:
            parts.append(f"Anki {anki_reviews} reviews")
        if github_commits:
            parts.append(f"GitHub {github_commits} commits")
        return ", ".join(parts) if parts else "No learning activity recorded yet."

    def _build_tomorrow_priority(self, python_minutes: int, japanese_minutes: int, sre_minutes: int) -> str:
        if python_minutes == 0 and japanese_minutes == 0 and sre_minutes == 0:
            return "Log one short self-learning session before bed."
        if python_minutes < japanese_minutes:
            return "Prioritize one focused Python practice block."
        if sre_minutes == 0:
            return "Prioritize one SRE/Linux note or lab."
        if japanese_minutes < python_minutes:
            return "Prioritize Anki reviews and one N3 grammar block."
        return "Keep balance: one Python exercise, one Japanese review block, and one SRE note."
