from datetime import date, datetime, timedelta, timezone

from app.integrations.anki import AnkiAdapter
from app.integrations.github import GitHubAdapter
from app.models.activity import ActivityEvent, ActivityEventType
from app.models.learning import LearningPulse, LearningSession, LearningSessionCreate, LearningSubject
from app.repositories.activity import ActivityRepository
from app.repositories.learning import LearningRepository


class LearningService:
    def __init__(
        self,
        learning_repository: LearningRepository | None = None,
        activity_repository: ActivityRepository | None = None,
        anki_adapter: AnkiAdapter | None = None,
        github_adapter: GitHubAdapter | None = None,
    ) -> None:
        self.learning_repository = learning_repository or LearningRepository()
        self.activity_repository = activity_repository or ActivityRepository()
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
                payload={"session_id": session.id, "duration_minutes": session.duration_minutes},
            )
        )
        return session

    def list_sessions(self, limit: int = 100) -> list[LearningSession]:
        return self.learning_repository.list_sessions(limit=limit)

    async def build_today_pulse(self) -> LearningPulse:
        return await self.build_pulse(date.today())

    async def build_pulse(self, target_date: date) -> LearningPulse:
        sessions = self.learning_repository.list_sessions_for_date(target_date)
        anki_stats = await self.anki_adapter.get_daily_stats(target_date)
        github_stats = await self.github_adapter.get_daily_python_activity(target_date)

        python_minutes = sum(
            session.duration_minutes for session in sessions if session.subject == LearningSubject.python
        )
        japanese_minutes = sum(
            session.duration_minutes for session in sessions if session.subject == LearningSubject.japanese
        )
        total_minutes = python_minutes + japanese_minutes
        focus_score = self._calculate_focus_score(
            python_minutes=python_minutes,
            japanese_minutes=japanese_minutes,
            anki_reviews=anki_stats.reviews,
            github_commits=github_stats.commits,
        )

        return LearningPulse(
            date=target_date,
            python_minutes=python_minutes,
            japanese_minutes=japanese_minutes,
            total_minutes=total_minutes,
            session_count=len(sessions),
            anki_reviews=anki_stats.reviews,
            anki_accuracy=anki_stats.accuracy,
            github_commits=github_stats.commits,
            focus_score=focus_score,
            summary=self._build_summary(python_minutes, japanese_minutes, anki_stats.reviews, github_stats.commits),
            tomorrow_priority=self._build_tomorrow_priority(python_minutes, japanese_minutes),
        )

    def _calculate_focus_score(
        self,
        python_minutes: int,
        japanese_minutes: int,
        anki_reviews: int,
        github_commits: int,
    ) -> int:
        score = 0
        score += min(python_minutes, 90) // 3
        score += min(japanese_minutes, 90) // 3
        score += min(anki_reviews, 100) // 5
        score += min(github_commits, 5) * 4
        return min(score, 100)

    def _build_summary(self, python_minutes: int, japanese_minutes: int, anki_reviews: int, github_commits: int) -> str:
        parts = []
        if python_minutes:
            parts.append(f"Python {python_minutes} min")
        if japanese_minutes:
            parts.append(f"Japanese {japanese_minutes} min")
        if anki_reviews:
            parts.append(f"Anki {anki_reviews} reviews")
        if github_commits:
            parts.append(f"GitHub {github_commits} commits")
        return ", ".join(parts) if parts else "No learning activity recorded yet."

    def _build_tomorrow_priority(self, python_minutes: int, japanese_minutes: int) -> str:
        if python_minutes == 0 and japanese_minutes == 0:
            return "Log one short Python session and one Anki review block."
        if python_minutes < japanese_minutes:
            return "Prioritize one focused Python practice block."
        if japanese_minutes < python_minutes:
            return "Prioritize Anki reviews and one N3 grammar block."
        return "Keep balance: one Python exercise and one Japanese review block."

