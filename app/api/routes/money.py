from fastapi import APIRouter, HTTPException, status

from app.models.money import (
    LeveragePlanReview,
    LeverageStrategyPlan,
    LeverageStrategyPlanCreate,
    LoanScenario,
    LoanScenarioCreate,
    MoneyGoal,
    MoneyGoalContributionCreate,
    MoneyGoalCreate,
    MoneyOverview,
    MoneyWeeklyCheckin,
    MoneyWeeklyCheckinCreate,
    StrategyDecisionLog,
    StrategyDecisionLogCreate,
)
from app.services.money import (
    MoneyConflictError,
    MoneyNotFoundError,
    MoneyService,
    MoneyValidationError,
)


router = APIRouter(prefix="/money", tags=["money"])


@router.get("/overview", response_model=MoneyOverview)
def get_money_overview() -> MoneyOverview:
    return MoneyService().build_overview()


@router.post("/goals", response_model=MoneyGoal, status_code=status.HTTP_201_CREATED)
def create_money_goal(payload: MoneyGoalCreate) -> MoneyGoal:
    try:
        return MoneyService().create_goal(payload)
    except MoneyConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.get("/goals", response_model=list[MoneyGoal])
def list_money_goals() -> list[MoneyGoal]:
    return MoneyService().list_goals()


@router.post("/goals/{goal_ref}/contributions", response_model=MoneyGoal)
def add_money_goal_contribution(goal_ref: str, payload: MoneyGoalContributionCreate) -> MoneyGoal:
    try:
        return MoneyService().add_goal_contribution(goal_ref, payload)
    except MoneyNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except MoneyValidationError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error


@router.post("/checkins/weekly", response_model=MoneyWeeklyCheckin)
def record_weekly_money_checkin(payload: MoneyWeeklyCheckinCreate) -> MoneyWeeklyCheckin:
    return MoneyService().record_weekly_checkin(payload)


@router.post("/loan-scenarios", response_model=LoanScenario, status_code=status.HTTP_201_CREATED)
def create_loan_scenario(payload: LoanScenarioCreate) -> LoanScenario:
    try:
        return MoneyService().create_loan_scenario(payload)
    except MoneyConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.get("/loan-scenarios", response_model=list[LoanScenario])
def list_loan_scenarios() -> list[LoanScenario]:
    return MoneyService().list_loan_scenarios()


@router.post("/leverage-plans", response_model=LeverageStrategyPlan, status_code=status.HTTP_201_CREATED)
def create_leverage_plan(payload: LeverageStrategyPlanCreate) -> LeverageStrategyPlan:
    try:
        return MoneyService().create_leverage_plan(payload)
    except MoneyNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except MoneyConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.get("/leverage-plans", response_model=list[LeverageStrategyPlan])
def list_leverage_plans() -> list[LeverageStrategyPlan]:
    return MoneyService().list_leverage_plans()


@router.get("/leverage-plans/{plan_ref}/review", response_model=LeveragePlanReview)
def review_leverage_plan(plan_ref: str) -> LeveragePlanReview:
    try:
        return MoneyService().review_leverage_plan(plan_ref)
    except MoneyNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/leverage-plans/{plan_ref}/mark-reviewed", response_model=LeveragePlanReview)
def mark_leverage_plan_reviewed(plan_ref: str) -> LeveragePlanReview:
    try:
        return MoneyService().mark_leverage_plan_reviewed(plan_ref)
    except MoneyNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except MoneyValidationError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.post("/leverage-plans/{plan_ref}/decision-log", response_model=StrategyDecisionLog)
def create_strategy_decision_log(plan_ref: str, payload: StrategyDecisionLogCreate) -> StrategyDecisionLog:
    try:
        return MoneyService().create_decision_log(plan_ref, payload)
    except MoneyNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/leverage-plans/{plan_ref}/decision-log", response_model=list[StrategyDecisionLog])
def list_strategy_decision_logs(plan_ref: str) -> list[StrategyDecisionLog]:
    try:
        return MoneyService().list_decision_logs(plan_ref)
    except MoneyNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
