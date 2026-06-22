import sqlite3
from datetime import datetime, timezone

from app.core.exceptions import ConflictError, LifeQuestValidationError, NotFoundError
from app.models.activity import ActivityEvent, ActivityEventType
from app.models.money import (
    LeveragePlanReview,
    LeveragePlanStatus,
    LeverageStrategyPlan,
    LeverageStrategyPlanCreate,
    LoanScenario,
    LoanScenarioCreate,
    MoneyAttentionItem,
    MoneyGoal,
    MoneyGoalCategory,
    MoneyGoalContribution,
    MoneyGoalContributionCreate,
    MoneyGoalCreate,
    MoneyGoalStatus,
    MoneyOverview,
    MoneyRiskCheck,
    MoneyStressScenario,
    MoneyWeeklyCheckin,
    MoneyWeeklyCheckinCreate,
    RiskCheckStatus,
    StrategyDecisionLog,
    StrategyDecisionLogCreate,
    generate_money_key,
)
from app.repositories.activity import ActivityRepository
from app.repositories.money import MoneyRepository


class MoneyNotFoundError(NotFoundError):
    pass


class MoneyConflictError(ConflictError):
    pass


class MoneyValidationError(LifeQuestValidationError):
    pass


class MoneyService:
    def __init__(
        self,
        repository: MoneyRepository | None = None,
        activity_repository: ActivityRepository | None = None,
    ) -> None:
        self.repository = repository or MoneyRepository()
        self.activity_repository = activity_repository or ActivityRepository()

    def create_goal(self, payload: MoneyGoalCreate) -> MoneyGoal:
        now = datetime.now(timezone.utc)
        goal = MoneyGoal(
            key=payload.key or generate_money_key(payload.name, "goal"),
            name=payload.name,
            category=payload.category,
            target_amount=payload.target_amount,
            current_amount=payload.current_amount,
            currency=payload.currency,
            monthly_contribution_target=payload.monthly_contribution_target,
            target_date=payload.target_date,
            protected=payload.protected,
            status=payload.status,
            notes=payload.notes,
            created_at=now,
            updated_at=now,
        )
        try:
            created = self.repository.create_goal(goal)
        except sqlite3.IntegrityError as error:
            raise MoneyConflictError(f"Money goal already exists: {goal.key}") from error
        self._record_activity(
            ActivityEventType.money_goal_created,
            {
                "goal_id": created.id,
                "key": created.key,
                "name": created.name,
                "target_amount": created.target_amount,
                "currency": created.currency,
            },
        )
        return self.repository.get_goal_by_key(created.key) or created

    def list_goals(self) -> list[MoneyGoal]:
        return self.repository.list_goals()

    def add_goal_contribution(self, goal_ref: str, payload: MoneyGoalContributionCreate) -> MoneyGoal:
        goal = self._get_goal(goal_ref)
        if goal.currency != payload.currency:
            raise MoneyValidationError(
                f"Contribution currency {payload.currency} does not match goal currency {goal.currency}."
            )

        now = datetime.now(timezone.utc)
        contribution = MoneyGoalContribution(
            goal_id=goal.id,
            occurred_on=payload.occurred_on,
            amount=payload.amount,
            currency=payload.currency,
            note=payload.note,
            created_at=now,
        )
        self.repository.create_goal_contribution(contribution)
        goal.current_amount = round(goal.current_amount + contribution.amount, 2)
        if goal.current_amount >= goal.target_amount and goal.status == MoneyGoalStatus.active:
            goal.status = MoneyGoalStatus.completed
        goal.updated_at = now
        updated = self.repository.update_goal(goal)
        self._record_activity(
            ActivityEventType.money_goal_contribution_recorded,
            {
                "goal_id": updated.id,
                "key": updated.key,
                "name": updated.name,
                "amount": contribution.amount,
                "currency": contribution.currency,
            },
        )
        return self.repository.get_goal_by_key(updated.key) or updated

    def record_weekly_checkin(self, payload: MoneyWeeklyCheckinCreate) -> MoneyWeeklyCheckin:
        now = datetime.now(timezone.utc)
        checkin = MoneyWeeklyCheckin(
            week_start_date=payload.week_start_date,
            monthly_income=payload.monthly_income,
            necessary_expenses=payload.necessary_expenses,
            flexible_expenses=payload.flexible_expenses,
            planned_savings=payload.planned_savings,
            actual_savings=payload.actual_savings,
            investment_contribution=payload.investment_contribution,
            debt_payment=payload.debt_payment,
            currency=payload.currency,
            notes=payload.notes,
            created_at=now,
            updated_at=now,
        )
        saved = self.repository.upsert_weekly_checkin(checkin)
        self._record_activity(
            ActivityEventType.money_weekly_checkin_recorded,
            {
                "week_start_date": saved.week_start_date.isoformat(),
                "currency": saved.currency,
                "free_cashflow": saved.free_cashflow,
                "debt_service_ratio": saved.debt_service_ratio,
            },
        )
        return saved

    def create_loan_scenario(self, payload: LoanScenarioCreate) -> LoanScenario:
        now = datetime.now(timezone.utc)
        scenario = LoanScenario(
            key=payload.key or generate_money_key(payload.name, "loan"),
            name=payload.name,
            principal=payload.principal,
            annual_interest_rate=payload.annual_interest_rate,
            term_months=payload.term_months,
            monthly_payment=payload.monthly_payment
            or self._calculate_monthly_payment(payload.principal, payload.annual_interest_rate, payload.term_months),
            start_date=payload.start_date,
            purpose=payload.purpose,
            notes=payload.notes,
            created_at=now,
            updated_at=now,
        )
        try:
            return self.repository.create_loan_scenario(scenario)
        except sqlite3.IntegrityError as error:
            raise MoneyConflictError(f"Loan scenario already exists: {scenario.key}") from error

    def list_loan_scenarios(self) -> list[LoanScenario]:
        return self.repository.list_loan_scenarios()

    def create_leverage_plan(self, payload: LeverageStrategyPlanCreate) -> LeverageStrategyPlan:
        now = datetime.now(timezone.utc)
        loan_scenario_id = None
        if payload.loan_scenario_key:
            loan = self.repository.get_loan_by_key_or_id(payload.loan_scenario_key)
            if loan is None:
                raise MoneyNotFoundError(f"Loan scenario not found: {payload.loan_scenario_key}")
            loan_scenario_id = loan.id

        plan = LeverageStrategyPlan(
            key=payload.key or generate_money_key(payload.name, "leverage-plan"),
            name=payload.name,
            market=payload.market,
            base_asset_label=payload.base_asset_label,
            leveraged_asset_label=payload.leveraged_asset_label,
            currency=payload.currency,
            target_total_equity_exposure_pct=payload.target_total_equity_exposure_pct,
            leveraged_position_pct=payload.leveraged_position_pct,
            cash_reserve_pct=payload.cash_reserve_pct,
            rebalance_frequency=payload.rebalance_frequency,
            emergency_fund_months_required=payload.emergency_fund_months_required,
            max_debt_service_ratio=payload.max_debt_service_ratio,
            minimum_cash_reserve_pct=payload.minimum_cash_reserve_pct,
            max_strategy_drawdown_pct=payload.max_strategy_drawdown_pct,
            protected_goal_keys=payload.protected_goal_keys,
            loan_scenario_id=loan_scenario_id,
            status=LeveragePlanStatus.draft,
            notes=payload.notes,
            created_at=now,
            updated_at=now,
        )
        try:
            created = self.repository.create_leverage_plan(plan)
        except sqlite3.IntegrityError as error:
            raise MoneyConflictError(f"Leverage strategy plan already exists: {plan.key}") from error
        self._record_activity(
            ActivityEventType.money_leverage_plan_created,
            {
                "plan_id": created.id,
                "key": created.key,
                "name": created.name,
                "status": created.status.value,
            },
        )
        return created

    def list_leverage_plans(self) -> list[LeverageStrategyPlan]:
        return self.repository.list_leverage_plans()

    def build_overview(self) -> MoneyOverview:
        goals = self.repository.list_goals()
        latest_checkin = self.repository.get_latest_weekly_checkin()
        loan_scenarios = self.repository.list_loan_scenarios()
        leverage_plans = self.repository.list_leverage_plans()
        attention_items = self._build_attention_items(goals, latest_checkin, leverage_plans)
        totals: dict[str, float] = {}
        for goal in goals:
            if not goal.protected or goal.status != MoneyGoalStatus.active:
                continue
            totals[goal.currency] = round(totals.get(goal.currency, 0.0) + goal.remaining_amount, 2)
        return MoneyOverview(
            goals=goals,
            latest_weekly_checkin=latest_checkin,
            loan_scenarios=loan_scenarios,
            leverage_plans=leverage_plans,
            attention_items=attention_items,
            total_protected_goal_remaining=totals,
        )

    def review_leverage_plan(self, plan_ref: str) -> LeveragePlanReview:
        plan = self._get_leverage_plan(plan_ref)
        latest_checkin = self.repository.get_latest_weekly_checkin()
        goals = self.repository.list_goals()
        protected_goals = self._protected_goals_for_plan(plan, goals)
        checks = [
            self._cash_reserve_check(plan),
            self._weekly_checkin_check(latest_checkin),
            self._emergency_fund_check(plan, latest_checkin, goals),
            self._debt_service_check(plan, latest_checkin),
            self._protected_goal_check(plan, latest_checkin, protected_goals),
        ]
        stress_scenarios = self._build_stress_scenarios(plan)
        checks.extend(self._stress_checks(plan, stress_scenarios))
        failed_count = sum(1 for check in checks if check.status == RiskCheckStatus.failed)
        warning_count = sum(1 for check in checks if check.status == RiskCheckStatus.warning)
        can_mark_reviewed = failed_count == 0

        if failed_count:
            summary = "This strategy is still in draft because one or more guardrails failed."
        elif warning_count:
            summary = "No hard stop was triggered, but warnings should be reviewed before any real-world decision."
        else:
            summary = "No guardrail failed. This means the plan was reviewed, not that it is recommended."

        return LeveragePlanReview(
            plan=plan,
            latest_weekly_checkin=latest_checkin,
            protected_goals=protected_goals,
            checks=checks,
            stress_scenarios=stress_scenarios,
            failed_count=failed_count,
            warning_count=warning_count,
            can_mark_reviewed=can_mark_reviewed,
            summary=summary,
        )

    def mark_leverage_plan_reviewed(self, plan_ref: str) -> LeveragePlanReview:
        review = self.review_leverage_plan(plan_ref)
        if not review.can_mark_reviewed:
            raise MoneyValidationError("This leverage plan still has failed guardrails and must remain draft.")
        review.plan.status = LeveragePlanStatus.reviewed
        review.plan.updated_at = datetime.now(timezone.utc)
        self.repository.update_leverage_plan(review.plan)
        return self.review_leverage_plan(plan_ref)

    def create_decision_log(self, plan_ref: str, payload: StrategyDecisionLogCreate) -> StrategyDecisionLog:
        plan = self._get_leverage_plan(plan_ref)
        log = StrategyDecisionLog(
            plan_id=plan.id,
            decision_date=payload.decision_date,
            decision=payload.decision,
            rationale=payload.rationale,
            emotion=payload.emotion,
            source_links=payload.source_links,
        )
        created = self.repository.create_decision_log(log)
        self._record_activity(
            ActivityEventType.money_strategy_decision_logged,
            {
                "plan_id": plan.id,
                "key": plan.key,
                "decision": created.decision,
                "decision_date": created.decision_date.isoformat(),
            },
        )
        return created

    def list_decision_logs(self, plan_ref: str) -> list[StrategyDecisionLog]:
        plan = self._get_leverage_plan(plan_ref)
        return self.repository.list_decision_logs_for_plan(plan.id)

    def _get_goal(self, goal_ref: str) -> MoneyGoal:
        goal = self.repository.get_goal_by_key_or_id(goal_ref)
        if goal is None:
            raise MoneyNotFoundError(f"Money goal not found: {goal_ref}")
        return goal

    def _get_leverage_plan(self, plan_ref: str) -> LeverageStrategyPlan:
        plan = self.repository.get_leverage_plan_by_key_or_id(plan_ref)
        if plan is None:
            raise MoneyNotFoundError(f"Leverage strategy plan not found: {plan_ref}")
        return plan

    def _calculate_monthly_payment(self, principal: float, annual_rate: float, term_months: int) -> float:
        monthly_rate = annual_rate / 100 / 12
        if monthly_rate == 0:
            return round(principal / term_months, 2)
        multiplier = (1 + monthly_rate) ** term_months
        payment = principal * monthly_rate * multiplier / (multiplier - 1)
        return round(payment, 2)

    def _build_attention_items(
        self,
        goals: list[MoneyGoal],
        latest_checkin: MoneyWeeklyCheckin | None,
        leverage_plans: list[LeverageStrategyPlan],
    ) -> list[MoneyAttentionItem]:
        items: list[MoneyAttentionItem] = []
        draft_plans = [plan for plan in leverage_plans if plan.status == LeveragePlanStatus.draft]
        if draft_plans:
            items.append(
                MoneyAttentionItem(
                    severity=RiskCheckStatus.warning,
                    title="Leverage plan still in draft",
                    detail=f"{len(draft_plans)} strategy plan needs guardrail review before being treated as reviewed.",
                )
            )
        if latest_checkin is None and (goals or leverage_plans):
            items.append(
                MoneyAttentionItem(
                    severity=RiskCheckStatus.warning,
                    title="Weekly money check-in missing",
                    detail="Record income, expenses, savings, and debt pressure before making money decisions.",
                )
            )
        protected_remaining = sum(goal.remaining_amount for goal in goals if goal.protected and goal.status == "active")
        if protected_remaining > 0:
            items.append(
                MoneyAttentionItem(
                    severity=RiskCheckStatus.info,
                    title="Protected goals are active",
                    detail=f"Keep TWD {protected_remaining:.0f} of protected goals visible before adding risk.",
                )
            )
        return items[:4]

    def _cash_reserve_check(self, plan: LeverageStrategyPlan) -> MoneyRiskCheck:
        status = (
            RiskCheckStatus.passed
            if plan.cash_reserve_pct >= plan.minimum_cash_reserve_pct
            else RiskCheckStatus.failed
        )
        return MoneyRiskCheck(
            key="cash_reserve",
            title="Cash reserve guardrail",
            status=status,
            detail=(
                f"Strategy keeps {plan.cash_reserve_pct:.1f}% cash; minimum is "
                f"{plan.minimum_cash_reserve_pct:.1f}%."
            ),
            value=plan.cash_reserve_pct,
            threshold=plan.minimum_cash_reserve_pct,
        )

    def _weekly_checkin_check(self, latest_checkin: MoneyWeeklyCheckin | None) -> MoneyRiskCheck:
        if latest_checkin is None:
            return MoneyRiskCheck(
                key="weekly_checkin",
                title="Cashflow data",
                status=RiskCheckStatus.failed,
                detail="No weekly money check-in exists yet. Cashflow is required before reviewing leverage.",
            )
        return MoneyRiskCheck(
            key="weekly_checkin",
            title="Cashflow data",
            status=RiskCheckStatus.passed,
            detail=f"Latest check-in is {latest_checkin.week_start_date.isoformat()}.",
        )

    def _emergency_fund_check(
        self,
        plan: LeverageStrategyPlan,
        latest_checkin: MoneyWeeklyCheckin | None,
        goals: list[MoneyGoal],
    ) -> MoneyRiskCheck:
        emergency_goal = next(
            (
                goal
                for goal in goals
                if goal.category == MoneyGoalCategory.emergency_fund and goal.status == MoneyGoalStatus.active
            ),
            None,
        )
        if latest_checkin is None:
            return MoneyRiskCheck(
                key="emergency_fund",
                title="Emergency fund",
                status=RiskCheckStatus.failed,
                detail="Emergency reserve months cannot be calculated without a weekly check-in.",
            )
        monthly_burn = latest_checkin.necessary_expenses + latest_checkin.flexible_expenses
        if monthly_burn <= 0:
            return MoneyRiskCheck(
                key="emergency_fund",
                title="Emergency fund",
                status=RiskCheckStatus.failed,
                detail="Monthly expenses are zero or missing, so emergency reserve months cannot be trusted.",
            )
        if emergency_goal is None:
            return MoneyRiskCheck(
                key="emergency_fund",
                title="Emergency fund",
                status=RiskCheckStatus.failed,
                detail="Create an active emergency fund goal before reviewing leverage.",
            )
        reserve_months = emergency_goal.current_amount / monthly_burn
        status = (
            RiskCheckStatus.passed
            if reserve_months >= plan.emergency_fund_months_required
            else RiskCheckStatus.failed
        )
        return MoneyRiskCheck(
            key="emergency_fund",
            title="Emergency fund",
            status=status,
            detail=(
                f"Emergency reserve covers {reserve_months:.1f} months; required is "
                f"{plan.emergency_fund_months_required:.1f} months."
            ),
            value=round(reserve_months, 2),
            threshold=plan.emergency_fund_months_required,
        )

    def _debt_service_check(
        self,
        plan: LeverageStrategyPlan,
        latest_checkin: MoneyWeeklyCheckin | None,
    ) -> MoneyRiskCheck:
        loan = plan.loan_scenario
        if loan is None:
            return MoneyRiskCheck(
                key="debt_service",
                title="Debt service pressure",
                status=RiskCheckStatus.passed,
                detail="No loan scenario is attached to this strategy.",
            )
        if latest_checkin is None or latest_checkin.monthly_income <= 0:
            return MoneyRiskCheck(
                key="debt_service",
                title="Debt service pressure",
                status=RiskCheckStatus.failed,
                detail="Monthly income is required to review a loan-funded strategy.",
            )
        ratio = (latest_checkin.debt_payment + loan.monthly_payment) / latest_checkin.monthly_income
        status = RiskCheckStatus.passed if ratio <= plan.max_debt_service_ratio else RiskCheckStatus.failed
        return MoneyRiskCheck(
            key="debt_service",
            title="Debt service pressure",
            status=status,
            detail=(
                f"Debt payments would use {ratio:.1%} of monthly income; limit is "
                f"{plan.max_debt_service_ratio:.1%}."
            ),
            value=round(ratio, 4),
            threshold=plan.max_debt_service_ratio,
        )

    def _protected_goal_check(
        self,
        plan: LeverageStrategyPlan,
        latest_checkin: MoneyWeeklyCheckin | None,
        protected_goals: list[MoneyGoal],
    ) -> MoneyRiskCheck:
        if not protected_goals:
            return MoneyRiskCheck(
                key="protected_goals",
                title="Protected goals",
                status=RiskCheckStatus.warning,
                detail="No protected goals are linked. Consider protecting emergency and hair-transplant goals.",
            )
        required_monthly = sum(goal.monthly_contribution_target for goal in protected_goals)
        if latest_checkin is None:
            return MoneyRiskCheck(
                key="protected_goals",
                title="Protected goals",
                status=RiskCheckStatus.failed,
                detail="Protected goal pressure cannot be reviewed without a weekly check-in.",
            )
        available_after_savings = latest_checkin.free_cashflow - latest_checkin.investment_contribution
        loan_payment = plan.loan_scenario.monthly_payment if plan.loan_scenario else 0
        available_after_savings -= loan_payment
        status = RiskCheckStatus.passed if available_after_savings >= required_monthly else RiskCheckStatus.failed
        return MoneyRiskCheck(
            key="protected_goals",
            title="Protected goals",
            status=status,
            detail=(
                f"Protected goals need TWD {required_monthly:.0f}/month; projected free cash after "
                f"investment and attached loan is TWD {available_after_savings:.0f}."
            ),
            value=round(available_after_savings, 2),
            threshold=round(required_monthly, 2),
        )

    def _build_stress_scenarios(self, plan: LeverageStrategyPlan) -> list[MoneyStressScenario]:
        scenarios = []
        for drawdown in (30.0, 50.0, 70.0):
            strategy_drawdown = plan.leveraged_position_pct * drawdown / 100
            status = (
                RiskCheckStatus.passed
                if strategy_drawdown <= plan.max_strategy_drawdown_pct
                else RiskCheckStatus.failed
            )
            scenarios.append(
                MoneyStressScenario(
                    label=f"Leveraged ETF -{drawdown:.0f}%",
                    etf_drawdown_pct=drawdown,
                    strategy_drawdown_pct=round(strategy_drawdown, 2),
                    status=status,
                    detail=(
                        f"At {plan.leveraged_position_pct:.1f}% position size, this implies about "
                        f"{strategy_drawdown:.1f}% strategy drawdown before any behavior mistakes."
                    ),
                )
            )
        return scenarios

    def _stress_checks(
        self,
        plan: LeverageStrategyPlan,
        scenarios: list[MoneyStressScenario],
    ) -> list[MoneyRiskCheck]:
        worst = max(scenarios, key=lambda item: item.strategy_drawdown_pct)
        status = RiskCheckStatus.passed if worst.status == RiskCheckStatus.passed else RiskCheckStatus.failed
        return [
            MoneyRiskCheck(
                key="stress_drawdown",
                title="Drawdown stress test",
                status=status,
                detail=(
                    f"Worst scenario is {worst.strategy_drawdown_pct:.1f}% strategy drawdown; "
                    f"maximum allowed is {plan.max_strategy_drawdown_pct:.1f}%."
                ),
                value=worst.strategy_drawdown_pct,
                threshold=plan.max_strategy_drawdown_pct,
            ),
            MoneyRiskCheck(
                key="daily_reset_risk",
                title="Daily reset and volatility risk",
                status=RiskCheckStatus.info,
                detail="Leveraged ETFs target daily exposure; long holding periods can diverge from a simple multiple.",
            ),
        ]

    def _protected_goals_for_plan(
        self,
        plan: LeverageStrategyPlan,
        goals: list[MoneyGoal],
    ) -> list[MoneyGoal]:
        if plan.protected_goal_keys:
            keys = set(plan.protected_goal_keys)
            return [goal for goal in goals if goal.key in keys and goal.status == MoneyGoalStatus.active]
        return [goal for goal in goals if goal.protected and goal.status == MoneyGoalStatus.active]

    def _record_activity(self, event_type: ActivityEventType, payload: dict) -> None:
        self.activity_repository.create_event(
            ActivityEvent(
                event_type=event_type,
                source="money",
                payload=payload,
            )
        )
