from datetime import date, datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, Field

from app.models.activity import ActivityTimelineItem
from app.models.automation import AutomationCategory, AutomationRunStatus
from app.models.learning import LearningPulse, LearningSession
from app.models.subscription import SubscriptionMonthlyOverview
from app.models.work_knowledge import WorkKnowledgeCategory


class DashboardAttentionSeverity(StrEnum):
    info = "info"
    warning = "warning"
    positive = "positive"


class DashboardHero(BaseModel):
    target_date: date
    status: str = "live"
    headline: str
    summary: str
    focus_score: int = Field(default=0, ge=0, le=100)
    session_count: int = 0
    tomorrow_priority: str
    warnings: list[str] = Field(default_factory=list)


class DashboardAttentionItem(BaseModel):
    severity: DashboardAttentionSeverity = DashboardAttentionSeverity.info
    title: str
    detail: str
    href: str | None = None


class DashboardLaunchpadItem(BaseModel):
    key: str
    title: str
    summary: str
    href: str
    metric: str
    status_label: str


class DashboardLearningOverview(BaseModel):
    pulse: LearningPulse
    recent_sessions: list[LearningSession] = Field(default_factory=list)
    status: str
    recommendation: str


class DashboardSubscriptionsOverview(BaseModel):
    overview: SubscriptionMonthlyOverview
    status: str
    next_charge_name: str | None = None
    next_charge_date: date | None = None


class DashboardAutomationDefinitionSummary(BaseModel):
    key: str
    name: str
    category: AutomationCategory
    enabled: bool
    last_run_at: datetime | None = None
    last_run_status: AutomationRunStatus | None = None
    last_run_summary: str | None = None


class DashboardAutomationRunSummary(BaseModel):
    automation_key: str
    automation_name: str
    status: AutomationRunStatus
    started_at: datetime
    finished_at: datetime | None = None
    summary: str | None = None
    items_processed: int = 0


class DashboardAutomationsOverview(BaseModel):
    total_count: int = 0
    enabled_count: int = 0
    healthy_count: int = 0
    needs_attention_count: int = 0
    definitions: list[DashboardAutomationDefinitionSummary] = Field(default_factory=list)
    recent_runs: list[DashboardAutomationRunSummary] = Field(default_factory=list)


class DashboardKnowledgeNoteSummary(BaseModel):
    id: str
    title: str
    category: WorkKnowledgeCategory
    created_at: datetime
    follow_up: str | None = None
    tags: list[str] = Field(default_factory=list)


class DashboardKnowledgeOverview(BaseModel):
    note_count: int = 0
    follow_up_count: int = 0
    recent_notes: list[DashboardKnowledgeNoteSummary] = Field(default_factory=list)


class DashboardOverview(BaseModel):
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    target_date: date
    hero: DashboardHero
    learning: DashboardLearningOverview
    subscriptions: DashboardSubscriptionsOverview
    automations: DashboardAutomationsOverview
    knowledge: DashboardKnowledgeOverview
    attention_items: list[DashboardAttentionItem] = Field(default_factory=list)
    launchpad: list[DashboardLaunchpadItem] = Field(default_factory=list)
    recent_activity: list[ActivityTimelineItem] = Field(default_factory=list)
