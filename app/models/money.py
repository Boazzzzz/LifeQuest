from __future__ import annotations

from datetime import date, datetime, timezone
from enum import StrEnum
import re
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class MoneyGoalCategory(StrEnum):
    emergency_fund = "emergency_fund"
    hair_transplant = "hair_transplant"
    investment = "investment"
    lifestyle = "lifestyle"
    debt_buffer = "debt_buffer"
    other = "other"


class MoneyGoalStatus(StrEnum):
    active = "active"
    paused = "paused"
    completed = "completed"


class LeverageMarket(StrEnum):
    tw = "tw"
    us = "us"


class LeveragePlanStatus(StrEnum):
    draft = "draft"
    reviewed = "reviewed"
    paused = "paused"
    archived = "archived"


class RebalanceFrequency(StrEnum):
    monthly = "monthly"
    quarterly = "quarterly"
    semiannual = "semiannual"
    annual = "annual"


class RiskCheckStatus(StrEnum):
    passed = "passed"
    warning = "warning"
    failed = "failed"
    info = "info"


class MoneyGoalCreate(BaseModel):
    key: str | None = Field(default=None, min_length=2, max_length=120, pattern=r"^[a-z0-9][a-z0-9_.-]*$")
    name: str = Field(min_length=1, max_length=200)
    category: MoneyGoalCategory = MoneyGoalCategory.other
    target_amount: float = Field(gt=0, le=100_000_000)
    current_amount: float = Field(default=0, ge=0, le=100_000_000)
    currency: str = Field(default="TWD", min_length=3, max_length=8)
    monthly_contribution_target: float = Field(default=0, ge=0, le=10_000_000)
    target_date: date | None = None
    protected: bool = True
    status: MoneyGoalStatus = MoneyGoalStatus.active
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("key", mode="before")
    @classmethod
    def normalize_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        return normalized or None

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("target_date", mode="before")
    @classmethod
    def normalize_target_date(cls, value: date | str | None) -> date | None:
        if value is None or isinstance(value, date):
            return value
        return date.fromisoformat(value)


class MoneyGoal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    key: str
    name: str
    category: MoneyGoalCategory
    target_amount: float
    current_amount: float = 0
    currency: str = "TWD"
    monthly_contribution_target: float = 0
    target_date: date | None = None
    protected: bool = True
    status: MoneyGoalStatus = MoneyGoalStatus.active
    notes: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    progress_pct: float = 0
    remaining_amount: float = 0


class MoneyGoalContributionCreate(BaseModel):
    amount: float = Field(gt=0, le=100_000_000)
    currency: str = Field(default="TWD", min_length=3, max_length=8)
    occurred_on: date = Field(default_factory=date.today)
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("occurred_on", mode="before")
    @classmethod
    def normalize_occurred_on(cls, value: date | str) -> date:
        if isinstance(value, date):
            return value
        return date.fromisoformat(value)


class MoneyGoalContribution(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    goal_id: str
    occurred_on: date
    amount: float
    currency: str = "TWD"
    note: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MoneyWeeklyCheckinCreate(BaseModel):
    week_start_date: date
    monthly_income: float = Field(default=0, ge=0, le=100_000_000)
    necessary_expenses: float = Field(default=0, ge=0, le=100_000_000)
    flexible_expenses: float = Field(default=0, ge=0, le=100_000_000)
    planned_savings: float = Field(default=0, ge=0, le=100_000_000)
    actual_savings: float = Field(default=0, ge=0, le=100_000_000)
    investment_contribution: float = Field(default=0, ge=0, le=100_000_000)
    debt_payment: float = Field(default=0, ge=0, le=100_000_000)
    currency: str = Field(default="TWD", min_length=3, max_length=8)
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("week_start_date", mode="before")
    @classmethod
    def normalize_week_start_date(cls, value: date | str) -> date:
        if isinstance(value, date):
            return value
        return date.fromisoformat(value)

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.strip().upper()


class MoneyWeeklyCheckin(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    week_start_date: date
    monthly_income: float = 0
    necessary_expenses: float = 0
    flexible_expenses: float = 0
    planned_savings: float = 0
    actual_savings: float = 0
    investment_contribution: float = 0
    debt_payment: float = 0
    currency: str = "TWD"
    notes: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    free_cashflow: float = 0
    debt_service_ratio: float | None = None


class LoanScenarioCreate(BaseModel):
    key: str | None = Field(default=None, min_length=2, max_length=120, pattern=r"^[a-z0-9][a-z0-9_.-]*$")
    name: str = Field(min_length=1, max_length=200)
    principal: float = Field(gt=0, le=100_000_000)
    annual_interest_rate: float = Field(ge=0, le=100)
    term_months: int = Field(ge=1, le=480)
    monthly_payment: float | None = Field(default=None, gt=0, le=10_000_000)
    start_date: date | None = None
    purpose: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("key", mode="before")
    @classmethod
    def normalize_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        return normalized or None

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("start_date", mode="before")
    @classmethod
    def normalize_start_date(cls, value: date | str | None) -> date | None:
        if value is None or isinstance(value, date):
            return value
        return date.fromisoformat(value)


class LoanScenario(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    key: str
    name: str
    principal: float
    annual_interest_rate: float
    term_months: int
    monthly_payment: float
    start_date: date | None = None
    purpose: str | None = None
    notes: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LeverageStrategyPlanCreate(BaseModel):
    key: str | None = Field(default=None, min_length=2, max_length=120, pattern=r"^[a-z0-9][a-z0-9_.-]*$")
    name: str = Field(default="Taiwan 2x ETF 50/50 guardrail", min_length=1, max_length=200)
    market: LeverageMarket = LeverageMarket.tw
    base_asset_label: str = Field(default="Taiwan broad equity", min_length=1, max_length=200)
    leveraged_asset_label: str = Field(default="Taiwan 2x ETF", min_length=1, max_length=200)
    currency: str = Field(default="TWD", min_length=3, max_length=8)
    target_total_equity_exposure_pct: float = Field(default=100, ge=0, le=300)
    leveraged_position_pct: float = Field(default=50, ge=0, le=100)
    cash_reserve_pct: float = Field(default=50, ge=0, le=100)
    rebalance_frequency: RebalanceFrequency = RebalanceFrequency.quarterly
    emergency_fund_months_required: float = Field(default=6, ge=0, le=60)
    max_debt_service_ratio: float = Field(default=0.2, ge=0, le=1)
    minimum_cash_reserve_pct: float = Field(default=30, ge=0, le=100)
    max_strategy_drawdown_pct: float = Field(default=35, ge=0, le=100)
    protected_goal_keys: list[str] = Field(default_factory=list)
    loan_scenario_key: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=4000)

    @field_validator("key", "loan_scenario_key", mode="before")
    @classmethod
    def normalize_optional_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().lower()
        return normalized or None

    @field_validator("name", "base_asset_label", "leveraged_asset_label", mode="before")
    @classmethod
    def normalize_label(cls, value: str) -> str:
        return value.strip()

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("protected_goal_keys")
    @classmethod
    def normalize_goal_keys(cls, value: list[str]) -> list[str]:
        return [item.strip().lower() for item in value if item.strip()]


class LeverageStrategyPlan(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    key: str
    name: str
    market: LeverageMarket = LeverageMarket.tw
    base_asset_label: str = "Taiwan broad equity"
    leveraged_asset_label: str = "Taiwan 2x ETF"
    currency: str = "TWD"
    target_total_equity_exposure_pct: float = 100
    leveraged_position_pct: float = 50
    cash_reserve_pct: float = 50
    rebalance_frequency: RebalanceFrequency = RebalanceFrequency.quarterly
    emergency_fund_months_required: float = 6
    max_debt_service_ratio: float = 0.2
    minimum_cash_reserve_pct: float = 30
    max_strategy_drawdown_pct: float = 35
    protected_goal_keys: list[str] = Field(default_factory=list)
    loan_scenario_id: str | None = None
    loan_scenario: LoanScenario | None = None
    status: LeveragePlanStatus = LeveragePlanStatus.draft
    notes: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MoneyRiskCheck(BaseModel):
    key: str
    title: str
    status: RiskCheckStatus
    detail: str
    value: float | None = None
    threshold: float | None = None


class MoneyStressScenario(BaseModel):
    label: str
    etf_drawdown_pct: float
    strategy_drawdown_pct: float
    status: RiskCheckStatus
    detail: str


class LeveragePlanReview(BaseModel):
    plan: LeverageStrategyPlan
    latest_weekly_checkin: MoneyWeeklyCheckin | None = None
    protected_goals: list[MoneyGoal] = Field(default_factory=list)
    checks: list[MoneyRiskCheck] = Field(default_factory=list)
    stress_scenarios: list[MoneyStressScenario] = Field(default_factory=list)
    failed_count: int = 0
    warning_count: int = 0
    can_mark_reviewed: bool = False
    summary: str


class StrategyDecisionLogCreate(BaseModel):
    decision_date: date = Field(default_factory=date.today)
    decision: str = Field(min_length=1, max_length=200)
    rationale: str = Field(min_length=1, max_length=4000)
    emotion: str | None = Field(default=None, max_length=200)
    source_links: list[str] = Field(default_factory=list)

    @field_validator("decision_date", mode="before")
    @classmethod
    def normalize_decision_date(cls, value: date | str) -> date:
        if isinstance(value, date):
            return value
        return date.fromisoformat(value)

    @field_validator("source_links")
    @classmethod
    def normalize_source_links(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]


class StrategyDecisionLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    plan_id: str
    decision_date: date
    decision: str
    rationale: str
    emotion: str | None = None
    source_links: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MoneyAttentionItem(BaseModel):
    severity: RiskCheckStatus = RiskCheckStatus.info
    title: str
    detail: str
    href: str | None = "/life-admin/money"


class MoneyOverview(BaseModel):
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    goals: list[MoneyGoal] = Field(default_factory=list)
    latest_weekly_checkin: MoneyWeeklyCheckin | None = None
    loan_scenarios: list[LoanScenario] = Field(default_factory=list)
    leverage_plans: list[LeverageStrategyPlan] = Field(default_factory=list)
    attention_items: list[MoneyAttentionItem] = Field(default_factory=list)
    total_protected_goal_remaining: dict[str, float] = Field(default_factory=dict)


def generate_money_key(name: str, prefix: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    if slug:
        return slug
    return f"{prefix}-{uuid4().hex[:8]}"
