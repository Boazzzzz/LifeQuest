from datetime import date

from fastapi import APIRouter, HTTPException, Query, status

from app.models.subscription import (
    SubscriptionLifecycleStatus,
    Subscription,
    SubscriptionCreate,
    SubscriptionMonthlyOverview,
    SubscriptionUpdate,
)
from app.services.subscription import (
    SubscriptionConflictError,
    SubscriptionNotFoundError,
    SubscriptionService,
)

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.post("", response_model=Subscription, status_code=status.HTTP_201_CREATED)
def create_subscription(payload: SubscriptionCreate) -> Subscription:
    try:
        return SubscriptionService().create_subscription(payload)
    except SubscriptionConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.get("", response_model=list[Subscription])
def list_subscriptions(
    active_only: bool = Query(default=False),
    needs_review_only: bool = Query(default=False),
    status: SubscriptionLifecycleStatus | None = Query(default=None),
) -> list[Subscription]:
    subscriptions = SubscriptionService().list_subscriptions(active_only=active_only)
    if needs_review_only:
        subscriptions = [subscription for subscription in subscriptions if subscription.schedule_status == "needs_review"]
    if status is not None:
        subscriptions = [subscription for subscription in subscriptions if subscription.status == status]
    return subscriptions


@router.get("/overview/monthly", response_model=SubscriptionMonthlyOverview)
def get_monthly_subscription_overview(
    target_date: date | None = Query(default=None),
    days_ahead: int = Query(default=30, ge=1, le=365),
) -> SubscriptionMonthlyOverview:
    return SubscriptionService().build_monthly_overview(target_date=target_date, days_ahead=days_ahead)


@router.get("/{subscription_ref}", response_model=Subscription)
def get_subscription(subscription_ref: str) -> Subscription:
    try:
        return SubscriptionService().get_subscription(subscription_ref)
    except SubscriptionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.patch("/{subscription_ref}", response_model=Subscription)
def update_subscription(subscription_ref: str, payload: SubscriptionUpdate) -> Subscription:
    try:
        return SubscriptionService().update_subscription(subscription_ref, payload)
    except SubscriptionNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except SubscriptionConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
