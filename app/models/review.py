from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.activity import ActivityTimelineItem
from app.models.automation import AutomationRunStatus
from app.models.learning import LearningSession
from app.models.subscription import SubscriptionUpcomingCharge
from app.models.work_knowledge import WorkKnowledgeCategory


class WeeklyReviewLearningSummary(BaseModel):
    total_minutes: int = 0
    session_count: int = 0
    python_minutes: int = 0
    japanese_minutes: int = 0
    sre_minutes: int = 0
    active_days: int = 0
    best_day: date | None = None
    best_day_minutes: int = 0
    recommendation: str
    recent_sessions: list[LearningSession] = Field(default_factory=list)


class WeeklyReviewSubscriptionSummary(BaseModel):
    active_subscription_count: int = 0
    missing_schedule_count: int = 0
    upcoming_charge_count: int = 0
    new_subscription_count: int = 0
    updated_subscription_count: int = 0
    upcoming_charges: list[SubscriptionUpcomingCharge] = Field(default_factory=list)
    recommendation: str


class WeeklyReviewAutomationSummary(BaseModel):
    run_count: int = 0
    success_count: int = 0
    partial_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    recent_failures: list[str] = Field(default_factory=list)
    recommendation: str


class WeeklyReviewKnowledgeCategoryCount(BaseModel):
    category: WorkKnowledgeCategory
    count: int = 0


class WeeklyReviewKnowledgeNoteSummary(BaseModel):
    id: str
    title: str
    category: WorkKnowledgeCategory
    created_at: datetime
    follow_up: str | None = None


class WeeklyReviewKnowledgeSummary(BaseModel):
    note_count: int = 0
    follow_up_count: int = 0
    categories: list[WeeklyReviewKnowledgeCategoryCount] = Field(default_factory=list)
    recent_notes: list[WeeklyReviewKnowledgeNoteSummary] = Field(default_factory=list)
    recommendation: str


class WeeklyReviewOverview(BaseModel):
    target_date: date
    period_start: date
    period_end: date
    headline: str
    summary: str
    keep_doing: list[str] = Field(default_factory=list)
    needs_attention: list[str] = Field(default_factory=list)
    next_week_focus: list[str] = Field(default_factory=list)
    learning: WeeklyReviewLearningSummary
    subscriptions: WeeklyReviewSubscriptionSummary
    automations: WeeklyReviewAutomationSummary
    knowledge: WeeklyReviewKnowledgeSummary
    timeline: list[ActivityTimelineItem] = Field(default_factory=list)
