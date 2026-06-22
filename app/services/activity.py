from datetime import date, datetime, time, timezone

from app.models.activity import ActivityEvent, ActivityEventType, ActivityTimelineItem, ActivityTimelineOverview
from app.repositories.activity import ActivityRepository


class ActivityService:
    def __init__(self, repository: ActivityRepository | None = None) -> None:
        self.repository = repository or ActivityRepository()

    def get_recent_timeline(self, limit: int = 20) -> ActivityTimelineOverview:
        events = self.repository.list_recent_events(limit=limit)
        return ActivityTimelineOverview(items=[self._timeline_item(event) for event in events])

    def get_timeline_for_period(
        self,
        start_date: date,
        end_date: date,
        limit: int = 200,
    ) -> ActivityTimelineOverview:
        start_at = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
        end_at = datetime.combine(end_date, time.max, tzinfo=timezone.utc)
        events = self.repository.list_events_between(start_at=start_at, end_at=end_at, limit=limit)
        return ActivityTimelineOverview(items=[self._timeline_item(event) for event in events])

    def _timeline_item(self, event: ActivityEvent) -> ActivityTimelineItem:
        payload = event.payload
        title = "Activity event"
        detail = event.source
        href = None
        tone = "neutral"

        if event.event_type == ActivityEventType.learning_session_created:
            subject = payload.get("subject") or event.subject or "learning"
            title = f"Logged {self._subject_label(str(subject))} session"
            summary = payload.get("summary")
            if summary:
                detail = f"{payload.get('duration_minutes', 0)} minutes · {summary}"
            else:
                detail = f"{payload.get('duration_minutes', 0)} minutes"
            href = "/japanese" if str(subject) == "japanese" else "/dashboard"
            tone = "positive"
        elif event.event_type == ActivityEventType.anki_reviews_imported:
            title = "Imported Anki reviews"
            detail = f"{payload.get('reviews', 0)} reviews captured"
            href = "/japanese"
            tone = "positive"
        elif event.event_type == ActivityEventType.github_commits_imported:
            title = "Imported GitHub activity"
            detail = f"{payload.get('commits', 0)} commits, {payload.get('python_commits', 0)} Python"
            href = "/dashboard"
            tone = "positive"
        elif event.event_type == ActivityEventType.subscription_created:
            title = "Added subscription"
            detail = self._subscription_detail(payload)
            href = "/life-admin/subscriptions"
            tone = "neutral"
        elif event.event_type == ActivityEventType.subscription_updated:
            title = "Updated subscription"
            detail = self._subscription_detail(payload)
            href = "/life-admin/subscriptions"
            tone = "neutral"
        elif event.event_type == ActivityEventType.money_goal_created:
            title = "Created money goal"
            detail = str(payload.get("name") or payload.get("key") or "Money goal")
            href = "/life-admin/money"
            tone = "positive"
        elif event.event_type == ActivityEventType.money_goal_contribution_recorded:
            title = "Recorded money goal contribution"
            detail = self._money_amount_detail(payload)
            href = "/life-admin/money"
            tone = "positive"
        elif event.event_type == ActivityEventType.money_weekly_checkin_recorded:
            title = "Recorded weekly money check-in"
            detail = f"Free cashflow: {payload.get('currency', 'TWD')} {float(payload.get('free_cashflow') or 0):.2f}"
            href = "/life-admin/money"
            tone = "neutral"
        elif event.event_type == ActivityEventType.money_leverage_plan_created:
            title = "Created leverage strategy draft"
            detail = str(payload.get("name") or payload.get("key") or "Leverage strategy")
            href = "/life-admin/money"
            tone = "warning"
        elif event.event_type == ActivityEventType.money_strategy_decision_logged:
            title = "Logged strategy decision"
            detail = str(payload.get("decision") or "Decision recorded")
            href = "/life-admin/money"
            tone = "neutral"
        elif event.event_type == ActivityEventType.work_knowledge_note_created:
            title = "Captured knowledge note"
            detail = str(payload.get("title") or "Work knowledge note")
            href = "/docs#/work-knowledge"
            tone = "positive"
        elif event.event_type == ActivityEventType.automation_run_recorded:
            automation_name = str(payload.get("automation_name") or payload.get("automation_key") or "automation")
            title = f"Automation run: {automation_name}"
            detail = str(payload.get("summary") or payload.get("status") or "Run recorded")
            href = "/docs#/automations"
            tone = "warning" if payload.get("status") in {"failed", "partial"} else "positive"
        elif event.event_type == ActivityEventType.notion_sync_failed:
            title = "Notion sync failed"
            detail = str(payload.get("error") or "Sync failed")
            href = "/docs#/notion"
            tone = "warning"
        elif event.event_type == ActivityEventType.notion_sync_completed:
            title = "Notion sync completed"
            detail = str(payload.get("summary") or "Sync completed")
            href = "/docs#/notion"
            tone = "positive"

        return ActivityTimelineItem(
            id=event.id,
            event_type=event.event_type,
            occurred_at=event.occurred_at,
            source=event.source,
            title=title,
            detail=detail,
            href=href,
            tone=tone,
        )

    def _subject_label(self, subject: str) -> str:
        if subject == "python":
            return "Python"
        if subject == "japanese":
            return "Japanese"
        return subject

    def _subscription_detail(self, payload: dict) -> str:
        name = str(payload.get("name") or "subscription")
        amount = payload.get("amount")
        currency = payload.get("currency")
        if amount is None or currency is None:
            return name
        return f"{name} · {currency} {float(amount):.2f}"

    def _money_amount_detail(self, payload: dict) -> str:
        name = str(payload.get("name") or payload.get("key") or "money goal")
        amount = payload.get("amount")
        currency = payload.get("currency") or "TWD"
        if amount is None:
            return name
        return f"{name} - {currency} {float(amount):.2f}"
