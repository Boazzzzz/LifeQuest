import json
from datetime import datetime

from app.core.database import execute, fetch_all, fetch_one, select_limit_clause
from app.models.money import (
    LeverageStrategyPlan,
    LoanScenario,
    MoneyGoal,
    MoneyGoalContribution,
    MoneyWeeklyCheckin,
    StrategyDecisionLog,
)


class MoneyRepository:
    def create_goal(self, goal: MoneyGoal) -> MoneyGoal:
        execute(
            """
            INSERT INTO money_goals (
                id, goal_key, name, category, target_amount, current_amount,
                currency, monthly_contribution_target, target_date, protected,
                status, notes, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            self._goal_values(goal),
        )
        return goal

    def update_goal(self, goal: MoneyGoal) -> MoneyGoal:
        execute(
            """
            UPDATE money_goals
            SET name = ?, category = ?, target_amount = ?, current_amount = ?,
                currency = ?, monthly_contribution_target = ?, target_date = ?,
                protected = ?, status = ?, notes = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                goal.name,
                goal.category.value,
                goal.target_amount,
                goal.current_amount,
                goal.currency,
                goal.monthly_contribution_target,
                goal.target_date.isoformat() if goal.target_date else None,
                1 if goal.protected else 0,
                goal.status.value,
                goal.notes,
                goal.updated_at.isoformat(),
                goal.id,
            ),
        )
        return goal

    def list_goals(self, limit: int = 500) -> list[MoneyGoal]:
        limit_clause = select_limit_clause(limit)
        query = f"""
            SELECT {limit_clause}* FROM money_goals
            ORDER BY status ASC, protected DESC, created_at DESC
        """
        rows = fetch_all(query) if limit_clause else fetch_all(f"{query}\nLIMIT ?", (limit,))
        return [self._hydrate_goal(self._row_to_goal(row)) for row in rows]

    def get_goal_by_key(self, goal_key: str) -> MoneyGoal | None:
        row = fetch_one("SELECT * FROM money_goals WHERE goal_key = ?", (goal_key,))
        return self._hydrate_goal(self._row_to_goal(row)) if row else None

    def get_goal_by_key_or_id(self, goal_ref: str) -> MoneyGoal | None:
        row = fetch_one(
            "SELECT * FROM money_goals WHERE goal_key = ? OR id = ?",
            (goal_ref, goal_ref),
        )
        return self._hydrate_goal(self._row_to_goal(row)) if row else None

    def create_goal_contribution(self, contribution: MoneyGoalContribution) -> MoneyGoalContribution:
        execute(
            """
            INSERT INTO money_goal_contributions (
                id, goal_id, occurred_on, amount, currency, note, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                contribution.id,
                contribution.goal_id,
                contribution.occurred_on.isoformat(),
                contribution.amount,
                contribution.currency,
                contribution.note,
                contribution.created_at.isoformat(),
            ),
        )
        return contribution

    def upsert_weekly_checkin(self, checkin: MoneyWeeklyCheckin) -> MoneyWeeklyCheckin:
        existing = self.get_weekly_checkin(checkin.week_start_date.isoformat())
        if existing is None:
            execute(
                """
                INSERT INTO money_weekly_checkins (
                    id, week_start_date, monthly_income, necessary_expenses,
                    flexible_expenses, planned_savings, actual_savings,
                    investment_contribution, debt_payment, currency, notes,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._weekly_checkin_values(checkin),
            )
            return self._hydrate_weekly_checkin(checkin)

        checkin.id = existing.id
        checkin.created_at = existing.created_at
        execute(
            """
            UPDATE money_weekly_checkins
            SET monthly_income = ?, necessary_expenses = ?, flexible_expenses = ?,
                planned_savings = ?, actual_savings = ?, investment_contribution = ?,
                debt_payment = ?, currency = ?, notes = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                checkin.monthly_income,
                checkin.necessary_expenses,
                checkin.flexible_expenses,
                checkin.planned_savings,
                checkin.actual_savings,
                checkin.investment_contribution,
                checkin.debt_payment,
                checkin.currency,
                checkin.notes,
                checkin.updated_at.isoformat(),
                checkin.id,
            ),
        )
        return self._hydrate_weekly_checkin(checkin)

    def get_weekly_checkin(self, week_start_date: str) -> MoneyWeeklyCheckin | None:
        row = fetch_one(
            "SELECT * FROM money_weekly_checkins WHERE week_start_date = ?",
            (week_start_date,),
        )
        return self._hydrate_weekly_checkin(self._row_to_weekly_checkin(row)) if row else None

    def get_latest_weekly_checkin(self) -> MoneyWeeklyCheckin | None:
        row = fetch_one(
            """
            SELECT * FROM money_weekly_checkins
            ORDER BY week_start_date DESC
            """
        )
        return self._hydrate_weekly_checkin(self._row_to_weekly_checkin(row)) if row else None

    def create_loan_scenario(self, scenario: LoanScenario) -> LoanScenario:
        execute(
            """
            INSERT INTO money_loan_scenarios (
                id, loan_key, name, principal, annual_interest_rate,
                term_months, monthly_payment, start_date, purpose, notes,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            self._loan_values(scenario),
        )
        return scenario

    def list_loan_scenarios(self, limit: int = 200) -> list[LoanScenario]:
        limit_clause = select_limit_clause(limit)
        query = f"""
            SELECT {limit_clause}* FROM money_loan_scenarios
            ORDER BY created_at DESC
        """
        rows = fetch_all(query) if limit_clause else fetch_all(f"{query}\nLIMIT ?", (limit,))
        return [self._row_to_loan(row) for row in rows]

    def get_loan_by_key_or_id(self, loan_ref: str) -> LoanScenario | None:
        row = fetch_one(
            "SELECT * FROM money_loan_scenarios WHERE loan_key = ? OR id = ?",
            (loan_ref, loan_ref),
        )
        return self._row_to_loan(row) if row else None

    def create_leverage_plan(self, plan: LeverageStrategyPlan) -> LeverageStrategyPlan:
        execute(
            """
            INSERT INTO money_leverage_strategy_plans (
                id, plan_key, name, market, base_asset_label, leveraged_asset_label,
                currency, target_total_equity_exposure_pct, leveraged_position_pct,
                cash_reserve_pct, rebalance_frequency, emergency_fund_months_required,
                max_debt_service_ratio, minimum_cash_reserve_pct,
                max_strategy_drawdown_pct, protected_goal_keys, loan_scenario_id,
                status, notes, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            self._leverage_plan_values(plan),
        )
        return self._attach_loan(plan)

    def update_leverage_plan(self, plan: LeverageStrategyPlan) -> LeverageStrategyPlan:
        execute(
            """
            UPDATE money_leverage_strategy_plans
            SET name = ?, market = ?, base_asset_label = ?, leveraged_asset_label = ?,
                currency = ?, target_total_equity_exposure_pct = ?,
                leveraged_position_pct = ?, cash_reserve_pct = ?,
                rebalance_frequency = ?, emergency_fund_months_required = ?,
                max_debt_service_ratio = ?, minimum_cash_reserve_pct = ?,
                max_strategy_drawdown_pct = ?, protected_goal_keys = ?,
                loan_scenario_id = ?, status = ?, notes = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                plan.name,
                plan.market.value,
                plan.base_asset_label,
                plan.leveraged_asset_label,
                plan.currency,
                plan.target_total_equity_exposure_pct,
                plan.leveraged_position_pct,
                plan.cash_reserve_pct,
                plan.rebalance_frequency.value,
                plan.emergency_fund_months_required,
                plan.max_debt_service_ratio,
                plan.minimum_cash_reserve_pct,
                plan.max_strategy_drawdown_pct,
                json.dumps(plan.protected_goal_keys, ensure_ascii=False),
                plan.loan_scenario_id,
                plan.status.value,
                plan.notes,
                plan.updated_at.isoformat(),
                plan.id,
            ),
        )
        return self._attach_loan(plan)

    def list_leverage_plans(self, limit: int = 200) -> list[LeverageStrategyPlan]:
        limit_clause = select_limit_clause(limit)
        query = f"""
            SELECT {limit_clause}* FROM money_leverage_strategy_plans
            ORDER BY status ASC, created_at DESC
        """
        rows = fetch_all(query) if limit_clause else fetch_all(f"{query}\nLIMIT ?", (limit,))
        return [self._attach_loan(self._row_to_leverage_plan(row)) for row in rows]

    def get_leverage_plan_by_key_or_id(self, plan_ref: str) -> LeverageStrategyPlan | None:
        row = fetch_one(
            "SELECT * FROM money_leverage_strategy_plans WHERE plan_key = ? OR id = ?",
            (plan_ref, plan_ref),
        )
        return self._attach_loan(self._row_to_leverage_plan(row)) if row else None

    def create_decision_log(self, log: StrategyDecisionLog) -> StrategyDecisionLog:
        execute(
            """
            INSERT INTO money_strategy_decision_logs (
                id, plan_id, decision_date, decision, rationale, emotion,
                source_links, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                log.id,
                log.plan_id,
                log.decision_date.isoformat(),
                log.decision,
                log.rationale,
                log.emotion,
                json.dumps(log.source_links, ensure_ascii=False),
                log.created_at.isoformat(),
            ),
        )
        return log

    def list_decision_logs_for_plan(self, plan_id: str, limit: int = 20) -> list[StrategyDecisionLog]:
        limit_clause = select_limit_clause(limit)
        query = f"""
            SELECT {limit_clause}* FROM money_strategy_decision_logs
            WHERE plan_id = ?
            ORDER BY decision_date DESC, created_at DESC
        """
        rows = fetch_all(query, (plan_id,)) if limit_clause else fetch_all(f"{query}\nLIMIT ?", (plan_id, limit))
        return [self._row_to_decision_log(row) for row in rows]

    def _goal_values(self, goal: MoneyGoal) -> tuple:
        return (
            goal.id,
            goal.key,
            goal.name,
            goal.category.value,
            goal.target_amount,
            goal.current_amount,
            goal.currency,
            goal.monthly_contribution_target,
            goal.target_date.isoformat() if goal.target_date else None,
            1 if goal.protected else 0,
            goal.status.value,
            goal.notes,
            goal.created_at.isoformat(),
            goal.updated_at.isoformat(),
        )

    def _weekly_checkin_values(self, checkin: MoneyWeeklyCheckin) -> tuple:
        return (
            checkin.id,
            checkin.week_start_date.isoformat(),
            checkin.monthly_income,
            checkin.necessary_expenses,
            checkin.flexible_expenses,
            checkin.planned_savings,
            checkin.actual_savings,
            checkin.investment_contribution,
            checkin.debt_payment,
            checkin.currency,
            checkin.notes,
            checkin.created_at.isoformat(),
            checkin.updated_at.isoformat(),
        )

    def _loan_values(self, scenario: LoanScenario) -> tuple:
        return (
            scenario.id,
            scenario.key,
            scenario.name,
            scenario.principal,
            scenario.annual_interest_rate,
            scenario.term_months,
            scenario.monthly_payment,
            scenario.start_date.isoformat() if scenario.start_date else None,
            scenario.purpose,
            scenario.notes,
            scenario.created_at.isoformat(),
            scenario.updated_at.isoformat(),
        )

    def _leverage_plan_values(self, plan: LeverageStrategyPlan) -> tuple:
        return (
            plan.id,
            plan.key,
            plan.name,
            plan.market.value,
            plan.base_asset_label,
            plan.leveraged_asset_label,
            plan.currency,
            plan.target_total_equity_exposure_pct,
            plan.leveraged_position_pct,
            plan.cash_reserve_pct,
            plan.rebalance_frequency.value,
            plan.emergency_fund_months_required,
            plan.max_debt_service_ratio,
            plan.minimum_cash_reserve_pct,
            plan.max_strategy_drawdown_pct,
            json.dumps(plan.protected_goal_keys, ensure_ascii=False),
            plan.loan_scenario_id,
            plan.status.value,
            plan.notes,
            plan.created_at.isoformat(),
            plan.updated_at.isoformat(),
        )

    def _row_to_goal(self, row) -> MoneyGoal:
        return MoneyGoal(
            id=row["id"],
            key=row["goal_key"],
            name=row["name"],
            category=row["category"],
            target_amount=float(row["target_amount"]),
            current_amount=float(row["current_amount"]),
            currency=row["currency"],
            monthly_contribution_target=float(row["monthly_contribution_target"]),
            target_date=datetime.fromisoformat(row["target_date"]).date() if row["target_date"] else None,
            protected=bool(row["protected"]),
            status=row["status"],
            notes=row["notes"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _hydrate_goal(self, goal: MoneyGoal) -> MoneyGoal:
        goal.remaining_amount = round(max(0.0, goal.target_amount - goal.current_amount), 2)
        goal.progress_pct = round(min(100.0, (goal.current_amount / goal.target_amount) * 100), 2)
        return goal

    def _row_to_weekly_checkin(self, row) -> MoneyWeeklyCheckin:
        return MoneyWeeklyCheckin(
            id=row["id"],
            week_start_date=datetime.fromisoformat(row["week_start_date"]).date(),
            monthly_income=float(row["monthly_income"]),
            necessary_expenses=float(row["necessary_expenses"]),
            flexible_expenses=float(row["flexible_expenses"]),
            planned_savings=float(row["planned_savings"]),
            actual_savings=float(row["actual_savings"]),
            investment_contribution=float(row["investment_contribution"]),
            debt_payment=float(row["debt_payment"]),
            currency=row["currency"],
            notes=row["notes"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _hydrate_weekly_checkin(self, checkin: MoneyWeeklyCheckin) -> MoneyWeeklyCheckin:
        checkin.free_cashflow = round(
            checkin.monthly_income
            - checkin.necessary_expenses
            - checkin.flexible_expenses
            - checkin.debt_payment,
            2,
        )
        checkin.debt_service_ratio = (
            round(checkin.debt_payment / checkin.monthly_income, 4)
            if checkin.monthly_income > 0
            else None
        )
        return checkin

    def _row_to_loan(self, row) -> LoanScenario:
        return LoanScenario(
            id=row["id"],
            key=row["loan_key"],
            name=row["name"],
            principal=float(row["principal"]),
            annual_interest_rate=float(row["annual_interest_rate"]),
            term_months=int(row["term_months"]),
            monthly_payment=float(row["monthly_payment"]),
            start_date=datetime.fromisoformat(row["start_date"]).date() if row["start_date"] else None,
            purpose=row["purpose"],
            notes=row["notes"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _row_to_leverage_plan(self, row) -> LeverageStrategyPlan:
        return LeverageStrategyPlan(
            id=row["id"],
            key=row["plan_key"],
            name=row["name"],
            market=row["market"],
            base_asset_label=row["base_asset_label"],
            leveraged_asset_label=row["leveraged_asset_label"],
            currency=row["currency"],
            target_total_equity_exposure_pct=float(row["target_total_equity_exposure_pct"]),
            leveraged_position_pct=float(row["leveraged_position_pct"]),
            cash_reserve_pct=float(row["cash_reserve_pct"]),
            rebalance_frequency=row["rebalance_frequency"],
            emergency_fund_months_required=float(row["emergency_fund_months_required"]),
            max_debt_service_ratio=float(row["max_debt_service_ratio"]),
            minimum_cash_reserve_pct=float(row["minimum_cash_reserve_pct"]),
            max_strategy_drawdown_pct=float(row["max_strategy_drawdown_pct"]),
            protected_goal_keys=json.loads(row["protected_goal_keys"]),
            loan_scenario_id=row["loan_scenario_id"],
            status=row["status"],
            notes=row["notes"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _attach_loan(self, plan: LeverageStrategyPlan) -> LeverageStrategyPlan:
        if plan.loan_scenario_id:
            plan.loan_scenario = self.get_loan_by_key_or_id(plan.loan_scenario_id)
        return plan

    def _row_to_decision_log(self, row) -> StrategyDecisionLog:
        return StrategyDecisionLog(
            id=row["id"],
            plan_id=row["plan_id"],
            decision_date=datetime.fromisoformat(row["decision_date"]).date(),
            decision=row["decision"],
            rationale=row["rationale"],
            emotion=row["emotion"],
            source_links=json.loads(row["source_links"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )
