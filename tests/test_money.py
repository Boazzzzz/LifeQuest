from datetime import date

from fastapi.testclient import TestClient

from app.core.database import initialize_database
from app.main import app
from app.models.money import (
    LeverageStrategyPlanCreate,
    LoanScenarioCreate,
    MoneyGoalCategory,
    MoneyGoalContributionCreate,
    MoneyGoalCreate,
    MoneyWeeklyCheckinCreate,
    StrategyDecisionLogCreate,
)
from app.services.money import MoneyService, MoneyValidationError


def use_temp_database(tmp_path, monkeypatch):
    database_path = tmp_path / "lifequest.db"
    monkeypatch.setattr("app.core.config.settings.database_path", database_path)
    monkeypatch.setattr("app.core.database.settings.database_path", database_path)
    initialize_database()


def seed_protected_goals(service: MoneyService):
    emergency = service.create_goal(
        MoneyGoalCreate(
            key="emergency-fund",
            name="Emergency Fund",
            category=MoneyGoalCategory.emergency_fund,
            target_amount=400000,
            current_amount=400000,
            monthly_contribution_target=0,
            protected=True,
        )
    )
    hair = service.create_goal(
        MoneyGoalCreate(
            key="hair-transplant-fund",
            name="Hair Transplant Fund",
            category=MoneyGoalCategory.hair_transplant,
            target_amount=180000,
            current_amount=30000,
            monthly_contribution_target=5000,
            protected=True,
        )
    )
    return emergency, hair


def test_money_service_reviews_leverage_plan_with_guardrails(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)
    service = MoneyService()
    seed_protected_goals(service)
    service.record_weekly_checkin(
        MoneyWeeklyCheckinCreate(
            week_start_date=date.fromisoformat("2026-06-15"),
            monthly_income=100000,
            necessary_expenses=30000,
            flexible_expenses=20000,
            investment_contribution=10000,
        )
    )
    loan = service.create_loan_scenario(
        LoanScenarioCreate(
            key="small-loan",
            name="Small loan stress test",
            principal=100000,
            annual_interest_rate=6,
            term_months=84,
        )
    )
    plan = service.create_leverage_plan(
        LeverageStrategyPlanCreate(
            key="tw-2x-50-50",
            name="Taiwan 2x 50/50",
            loan_scenario_key=loan.key,
            protected_goal_keys=["emergency-fund", "hair-transplant-fund"],
        )
    )

    review = service.review_leverage_plan(plan.key)
    reviewed = service.mark_leverage_plan_reviewed(plan.key)

    assert review.failed_count == 0
    assert review.can_mark_reviewed is True
    assert {check.key for check in review.checks} >= {
        "cash_reserve",
        "emergency_fund",
        "debt_service",
        "protected_goals",
        "stress_drawdown",
        "daily_reset_risk",
    }
    assert reviewed.plan.status == "reviewed"


def test_money_service_blocks_high_debt_leverage_plan(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)
    service = MoneyService()
    seed_protected_goals(service)
    service.record_weekly_checkin(
        MoneyWeeklyCheckinCreate(
            week_start_date=date.fromisoformat("2026-06-15"),
            monthly_income=30000,
            necessary_expenses=12000,
            flexible_expenses=8000,
        )
    )
    loan = service.create_loan_scenario(
        LoanScenarioCreate(
            key="heavy-loan",
            name="Heavy loan",
            principal=500000,
            annual_interest_rate=8,
            term_months=60,
        )
    )
    plan = service.create_leverage_plan(
        LeverageStrategyPlanCreate(
            key="loan-funded-plan",
            name="Loan funded plan",
            loan_scenario_key=loan.key,
            protected_goal_keys=["emergency-fund", "hair-transplant-fund"],
        )
    )

    review = service.review_leverage_plan(plan.key)

    assert review.failed_count >= 1
    assert any(check.key == "debt_service" and check.status == "failed" for check in review.checks)
    try:
        service.mark_leverage_plan_reviewed(plan.key)
    except MoneyValidationError as error:
        assert "failed guardrails" in str(error)
    else:
        raise AssertionError("Expected high-debt leverage plan to stay draft")


def test_money_service_requires_emergency_fund_for_leverage_review(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)
    service = MoneyService()
    service.record_weekly_checkin(
        MoneyWeeklyCheckinCreate(
            week_start_date=date.fromisoformat("2026-06-15"),
            monthly_income=80000,
            necessary_expenses=30000,
            flexible_expenses=10000,
        )
    )
    plan = service.create_leverage_plan(LeverageStrategyPlanCreate(key="no-emergency-plan"))

    review = service.review_leverage_plan(plan.key)

    assert review.can_mark_reviewed is False
    assert any(check.key == "emergency_fund" and check.status == "failed" for check in review.checks)


def test_money_goal_contribution_updates_progress(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)
    service = MoneyService()
    service.create_goal(
        MoneyGoalCreate(
            key="hair-transplant-fund",
            name="Hair Transplant Fund",
            category=MoneyGoalCategory.hair_transplant,
            target_amount=100000,
            current_amount=10000,
        )
    )

    updated = service.add_goal_contribution(
        "hair-transplant-fund",
        MoneyGoalContributionCreate(amount=5000, occurred_on=date.fromisoformat("2026-06-20")),
    )

    assert updated.current_amount == 15000
    assert updated.remaining_amount == 85000
    assert updated.progress_pct == 15


def test_money_api_create_review_and_decision_log(tmp_path, monkeypatch):
    use_temp_database(tmp_path, monkeypatch)

    with TestClient(app) as client:
        emergency_response = client.post(
            "/money/goals",
            json={
                "key": "emergency-fund",
                "name": "Emergency Fund",
                "category": "emergency_fund",
                "target_amount": 300000,
                "current_amount": 300000,
            },
        )
        hair_response = client.post(
            "/money/goals",
            json={
                "key": "hair-transplant-fund",
                "name": "Hair Transplant Fund",
                "category": "hair_transplant",
                "target_amount": 180000,
                "current_amount": 20000,
                "monthly_contribution_target": 5000,
            },
        )
        checkin_response = client.post(
            "/money/checkins/weekly",
            json={
                "week_start_date": "2026-06-15",
                "monthly_income": 90000,
                "necessary_expenses": 30000,
                "flexible_expenses": 15000,
                "investment_contribution": 5000,
            },
        )
        plan_response = client.post(
            "/money/leverage-plans",
            json={
                "key": "tw-2x-50-50",
                "name": "Taiwan 2x 50/50",
                "protected_goal_keys": ["emergency-fund", "hair-transplant-fund"],
            },
        )
        review_response = client.get("/money/leverage-plans/tw-2x-50-50/review")
        log_response = client.post(
            "/money/leverage-plans/tw-2x-50-50/decision-log",
            json={
                "decision_date": "2026-06-21",
                "decision": "Keep draft and review later",
                "rationale": "Use LifeQuest as guardrails before taking any real action.",
            },
        )
        overview_response = client.get("/money/overview")
        page_response = client.get("/life-admin/money")

    assert emergency_response.status_code == 201
    assert hair_response.status_code == 201
    assert checkin_response.status_code == 200
    assert plan_response.status_code == 201
    assert review_response.status_code == 200
    assert review_response.json()["failed_count"] == 0
    assert log_response.status_code == 200
    assert overview_response.status_code == 200
    assert overview_response.json()["leverage_plans"][0]["key"] == "tw-2x-50-50"
    assert page_response.status_code == 200
    assert "Money Quest" in page_response.text
