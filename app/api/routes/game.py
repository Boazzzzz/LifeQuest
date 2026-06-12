from datetime import date

from fastapi import APIRouter, HTTPException, Query, status

from app.models.game import GameDailyBoard
from app.services.game import GameQuestActionError, GameQuestNotFoundError, GameService


router = APIRouter(prefix="/game", tags=["game"])


@router.get("/daily-board", response_model=GameDailyBoard)
async def get_daily_board(target_date: date | None = Query(default=None)) -> GameDailyBoard:
    return await GameService().build_daily_board(target_date=target_date)


@router.post("/daily-board/{quest_key}/complete", response_model=GameDailyBoard)
async def complete_daily_quest(
    quest_key: str,
    target_date: date | None = Query(default=None),
) -> GameDailyBoard:
    try:
        return await GameService().complete_quest(quest_key, target_date=target_date)
    except GameQuestNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except GameQuestActionError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error


@router.post("/daily-board/{quest_key}/skip", response_model=GameDailyBoard)
async def skip_daily_quest(
    quest_key: str,
    target_date: date | None = Query(default=None),
) -> GameDailyBoard:
    try:
        return await GameService().skip_quest(quest_key, target_date=target_date)
    except GameQuestNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
