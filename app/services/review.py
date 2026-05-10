from collections import Counter, defaultdict
from datetime import date, timedelta

from app.models.automation import AutomationRunStatus
from app.models.learning import LearningSubject
from app.models.review import (
    WeeklyReviewAutomationSummary,
    WeeklyReviewKnowledgeCategoryCount,
    WeeklyReviewKnowledgeNoteSummary,
    WeeklyReviewKnowledgeSummary,
    WeeklyReviewLearningSummary,
    WeeklyReviewOverview,
    WeeklyReviewSubscriptionSummary,
)
from app.services.activity import ActivityService
from app.services.automation import AutomationService
from app.services.learning import LearningService
from app.services.subscription import SubscriptionService
from app.services.work_knowledge import WorkKnowledgeService


class ReviewService:
    def __init__(
        self,
        learning_service: LearningService | None = None,
        subscription_service: SubscriptionService | None = None,
        automation_service: AutomationService | None = None,
        work_knowledge_service: WorkKnowledgeService | None = None,
        activity_service: ActivityService | None = None,
    ) -> None:
        self.learning_service = learning_service or LearningService()
        self.subscription_service = subscription_service or SubscriptionService()
        self.automation_service = automation_service or AutomationService()
        self.work_knowledge_service = work_knowledge_service or WorkKnowledgeService()
        self.activity_service = activity_service or ActivityService()

    def build_weekly_review(self, target_date: date | None = None) -> WeeklyReviewOverview:
        target_date = target_date or date.today()
        period_end = target_date
        period_start = target_date - timedelta(days=6)

        sessions = [
            session
            for session in self.learning_service.list_sessions(limit=500)
            if period_start <= session.started_at.date() <= period_end
        ]
        subscriptions = self.subscription_service.list_subscriptions(active_only=False, reference_date=target_date)
        weekly_subscription_overview = self.subscription_service.build_monthly_overview(target_date=period_start, days_ahead=6)
        runs = [
            run
            for run in self.automation_service.list_recent_runs(limit=200)
            if period_start <= run.started_at.date() <= period_end
        ]
        notes = [
            note
            for note in self.work_knowledge_service.list_notes(limit=500)
            if period_start <= note.created_at.date() <= period_end
        ]
        timeline = self.activity_service.get_timeline_for_period(period_start, period_end, limit=50).items

        learning = self._build_learning_summary(sessions)
        subscription_summary = self._build_subscription_summary(
            subscriptions=subscriptions,
            weekly_overview=weekly_subscription_overview,
            period_start=period_start,
            period_end=period_end,
        )
        automation_summary = self._build_automation_summary(runs)
        knowledge_summary = self._build_knowledge_summary(notes)
        keep_doing = self._build_keep_doing(learning, automation_summary, knowledge_summary)
        needs_attention = self._build_needs_attention(subscription_summary, automation_summary, learning)
        next_week_focus = self._build_next_week_focus(learning, subscription_summary, knowledge_summary)
        headline, summary = self._headline_and_summary(learning, subscription_summary, automation_summary, knowledge_summary)

        return WeeklyReviewOverview(
            target_date=target_date,
            period_start=period_start,
            period_end=period_end,
            headline=headline,
            summary=summary,
            keep_doing=keep_doing,
            needs_attention=needs_attention,
            next_week_focus=next_week_focus,
            learning=learning,
            subscriptions=subscription_summary,
            automations=automation_summary,
            knowledge=knowledge_summary,
            timeline=timeline,
        )

    def _build_learning_summary(self, sessions) -> WeeklyReviewLearningSummary:
        totals_by_day: dict[date, int] = defaultdict(int)
        python_minutes = 0
        japanese_minutes = 0
        sre_minutes = 0
        for session in sessions:
            totals_by_day[session.started_at.date()] += session.duration_minutes
            if session.subject == LearningSubject.python:
                python_minutes += session.duration_minutes
            elif session.subject == LearningSubject.japanese:
                japanese_minutes += session.duration_minutes
            elif session.subject == LearningSubject.sre:
                sre_minutes += session.duration_minutes

        best_day, best_day_minutes = (None, 0)
        if totals_by_day:
            best_day, best_day_minutes = max(
                totals_by_day.items(),
                key=lambda item: (item[1], item[0]),
            )

        total_minutes = python_minutes + japanese_minutes + sre_minutes
        if total_minutes >= 240:
            recommendation = "這週的學習動能夠強，下週重點是守住節奏，不要過度切題。"
        elif total_minutes > 0:
            recommendation = "這週已有穩定訊號，下週優先補上較弱的那一條主線。"
        else:
            recommendation = "這週學習訊號太少，下週先追求最低可持續節奏，而不是追求完整規劃。"

        return WeeklyReviewLearningSummary(
            total_minutes=total_minutes,
            session_count=len(sessions),
            python_minutes=python_minutes,
            japanese_minutes=japanese_minutes,
            sre_minutes=sre_minutes,
            active_days=len(totals_by_day),
            best_day=best_day,
            best_day_minutes=best_day_minutes,
            recommendation=recommendation,
            recent_sessions=sessions[:5],
        )

    def _build_subscription_summary(
        self,
        subscriptions,
        weekly_overview,
        period_start: date,
        period_end: date,
    ) -> WeeklyReviewSubscriptionSummary:
        created_this_week = sum(1 for subscription in subscriptions if period_start <= subscription.created_at.date() <= period_end)
        updated_this_week = sum(1 for subscription in subscriptions if period_start <= subscription.updated_at.date() <= period_end)
        if weekly_overview.missing_schedule_count:
            recommendation = "先補齊缺少扣款週期的訂閱，這是最容易留下未來噪音的地方。"
        elif weekly_overview.upcoming_charges:
            recommendation = "固定支出資料已經能工作，下週可以開始加入提醒或分類上的小優化。"
        else:
            recommendation = "生活管理資料還很安靜，可以慢慢補齊常用服務。"
        return WeeklyReviewSubscriptionSummary(
            active_subscription_count=weekly_overview.active_subscription_count,
            missing_schedule_count=weekly_overview.missing_schedule_count,
            upcoming_charge_count=len(weekly_overview.upcoming_charges),
            new_subscription_count=created_this_week,
            updated_subscription_count=updated_this_week,
            upcoming_charges=weekly_overview.upcoming_charges[:5],
            recommendation=recommendation,
        )

    def _build_automation_summary(self, runs) -> WeeklyReviewAutomationSummary:
        counts = Counter(run.status for run in runs)
        recent_failures = [
            run.summary or f"{run.status} run"
            for run in runs
            if run.status in {AutomationRunStatus.failed, AutomationRunStatus.partial}
        ][:4]
        if counts[AutomationRunStatus.failed] or counts[AutomationRunStatus.partial]:
            recommendation = "下週先修掉最常失敗的自動化，再擴大接入範圍。"
        elif runs:
            recommendation = "自動化目前相對穩定，下週可以接入下一個最常用的外部腳本。"
        else:
            recommendation = "自動化還沒有足夠的週訊號，先讓一個真正在用的腳本開始留下紀錄。"
        return WeeklyReviewAutomationSummary(
            run_count=len(runs),
            success_count=counts[AutomationRunStatus.success],
            partial_count=counts[AutomationRunStatus.partial],
            failed_count=counts[AutomationRunStatus.failed],
            skipped_count=counts[AutomationRunStatus.skipped],
            recent_failures=recent_failures,
            recommendation=recommendation,
        )

    def _build_knowledge_summary(self, notes) -> WeeklyReviewKnowledgeSummary:
        category_counts = Counter(note.category for note in notes)
        if notes:
            recommendation = "開始把這些筆記往可回顧、可 follow-up 的知識層推進，而不只是收集。"
        else:
            recommendation = "這週沒有新增知識筆記，下週可以先從一兩則高價值工作筆記開始。"
        return WeeklyReviewKnowledgeSummary(
            note_count=len(notes),
            follow_up_count=sum(1 for note in notes if note.follow_up),
            categories=[
                WeeklyReviewKnowledgeCategoryCount(category=category, count=count)
                for category, count in sorted(category_counts.items(), key=lambda item: (-item[1], item[0]))
            ],
            recent_notes=[
                WeeklyReviewKnowledgeNoteSummary(
                    id=note.id,
                    title=note.title,
                    category=note.category,
                    created_at=note.created_at,
                    follow_up=note.follow_up,
                )
                for note in notes[:5]
            ],
            recommendation=recommendation,
        )

    def _build_keep_doing(self, learning, automations, knowledge) -> list[str]:
        items = []
        if learning.total_minutes > 0:
            items.append(f"Keep logging learning sessions: this week already captured {learning.total_minutes} minutes.")
        if automations.success_count > 0:
            items.append(f"Keep the current automation cadence: {automations.success_count} successful runs were recorded.")
        if knowledge.note_count > 0:
            items.append(f"Keep capturing work knowledge: {knowledge.note_count} notes were added this week.")
        if not items:
            items.append("Keep the system lightweight: one reliable slice is more valuable than five half-used ones.")
        return items[:3]

    def _build_needs_attention(self, subscriptions, automations, learning) -> list[str]:
        items = []
        if subscriptions.missing_schedule_count:
            items.append(f"{subscriptions.missing_schedule_count} subscriptions still need billing schedule cleanup.")
        if automations.failed_count or automations.partial_count:
            items.append(
                f"{automations.failed_count + automations.partial_count} automation runs were not fully healthy this week."
            )
        if learning.total_minutes == 0:
            items.append("No learning time was logged this week.")
        elif learning.python_minutes == 0 or learning.japanese_minutes == 0 or learning.sre_minutes == 0:
            items.append("One of the main learning tracks was missing this week.")
        if not items:
            items.append("No major operational friction stood out this week.")
        return items[:3]

    def _build_next_week_focus(self, learning, subscriptions, knowledge) -> list[str]:
        items = []
        if learning.sre_minutes == 0:
            items.append("Protect one SRE/Linux practice block early in the week.")
        elif learning.python_minutes < learning.japanese_minutes:
            items.append("Protect one deeper Python build block early in the week.")
        else:
            items.append("Protect one Japanese review block early in the week.")
        if subscriptions.missing_schedule_count:
            items.append("Close the subscription schedule gaps before adding more life-admin detail.")
        if knowledge.follow_up_count:
            items.append("Turn one follow-up note into a reusable checklist or reference.")
        if len(items) < 3:
            items.append("Keep the weekly review short enough that you will actually reopen it.")
        return items[:3]

    def _headline_and_summary(self, learning, subscriptions, automations, knowledge) -> tuple[str, str]:
        if learning.total_minutes >= 240:
            headline = "This week had real momentum."
        elif learning.total_minutes > 0:
            headline = "This week produced useful signals."
        else:
            headline = "This week exposed where the system is still thin."
        summary = (
            f"Learning logged {learning.total_minutes} minutes across {learning.session_count} sessions. "
            f"Subscriptions have {subscriptions.missing_schedule_count} items needing cleanup. "
            f"Automations recorded {automations.run_count} runs. "
            f"Knowledge capture added {knowledge.note_count} notes."
        )
        return headline, summary
