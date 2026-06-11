from dataclasses import dataclass
from datetime import date, datetime, timezone

from app.models.game import (
    GameDailyBoard,
    GameQuest,
    GameQuestAction,
    GameQuestCompletionType,
    GameQuestEvent,
    GameQuestStatus,
)
from app.models.learning import LearningPulse
from app.repositories.game import GameQuestEventRepository
from app.services.learning import LearningService


class GameQuestNotFoundError(ValueError):
    pass


class GameQuestActionError(ValueError):
    pass


@dataclass(frozen=True)
class GameQuestDefinition:
    key: str
    title: str
    description: str
    xp: int
    category: str
    completion_type: GameQuestCompletionType


DEFAULT_DAILY_QUESTS = [
    GameQuestDefinition(
        key="python-focus",
        title="鍛造 Python",
        description="完成至少 25 分鐘 Python 實作、腳本或自動化練習。",
        xp=30,
        category="learning",
        completion_type=GameQuestCompletionType.learning_signal,
    ),
    GameQuestDefinition(
        key="japanese-review",
        title="日文巡禮",
        description="完成至少 15 分鐘日文學習，或讓 Anki 今天有複習紀錄。",
        xp=25,
        category="learning",
        completion_type=GameQuestCompletionType.learning_signal,
    ),
    GameQuestDefinition(
        key="life-admin-check",
        title="整理背包",
        description="掃過生活管理訊號，例如訂閱、待確認支出或小型行政事項。",
        xp=10,
        category="life-admin",
        completion_type=GameQuestCompletionType.manual,
    ),
    GameQuestDefinition(
        key="daily-brief",
        title="讀取任務簡報",
        description="看過今天的 LifeQuest 儀表板，知道下一步要做什麼。",
        xp=10,
        category="review",
        completion_type=GameQuestCompletionType.manual,
    ),
]


class GameService:
    def __init__(
        self,
        repository: GameQuestEventRepository | None = None,
        learning_service: LearningService | None = None,
    ) -> None:
        self.repository = repository or GameQuestEventRepository()
        self.learning_service = learning_service or LearningService()
        self.quest_definitions = {quest.key: quest for quest in DEFAULT_DAILY_QUESTS}

    async def build_daily_board(self, target_date: date | None = None) -> GameDailyBoard:
        board_date = target_date or date.today()
        pulse = await self.learning_service.build_pulse(board_date)
        events = self.repository.list_events_for_date(board_date)
        quests = [self._build_quest(definition, pulse, events.get(definition.key)) for definition in DEFAULT_DAILY_QUESTS]
        completed_count = sum(1 for quest in quests if quest.status == GameQuestStatus.completed)
        skipped_count = sum(1 for quest in quests if quest.status == GameQuestStatus.skipped)
        earned_xp = sum(quest.xp for quest in quests if quest.status == GameQuestStatus.completed)
        available_xp = sum(quest.xp for quest in quests)
        return GameDailyBoard(
            target_date=board_date,
            quests=quests,
            completed_count=completed_count,
            skipped_count=skipped_count,
            total_count=len(quests),
            earned_xp=earned_xp,
            available_xp=available_xp,
            gentle_message=self._gentle_message(completed_count, skipped_count, len(quests)),
        )

    async def complete_quest(self, quest_key: str, target_date: date | None = None) -> GameDailyBoard:
        definition = self._get_definition(quest_key)
        if definition.completion_type != GameQuestCompletionType.manual:
            raise GameQuestActionError("This quest is completed automatically from LifeQuest learning signals.")
        self._record_event(definition.key, GameQuestAction.completed, target_date)
        return await self.build_daily_board(target_date)

    async def skip_quest(self, quest_key: str, target_date: date | None = None) -> GameDailyBoard:
        definition = self._get_definition(quest_key)
        self._record_event(definition.key, GameQuestAction.skipped, target_date)
        return await self.build_daily_board(target_date)

    def _build_quest(
        self,
        definition: GameQuestDefinition,
        pulse: LearningPulse,
        event: GameQuestEvent | None,
    ) -> GameQuest:
        auto_completed, progress_label = self._learning_progress(definition, pulse)
        status = GameQuestStatus.pending
        completion_source = None
        if auto_completed:
            status = GameQuestStatus.completed
            completion_source = "learning_signal"
        elif event is not None and event.action == GameQuestAction.completed:
            status = GameQuestStatus.completed
            completion_source = event.source
        elif event is not None and event.action == GameQuestAction.skipped:
            status = GameQuestStatus.skipped
            completion_source = event.source

        return GameQuest(
            key=definition.key,
            title=definition.title,
            description=definition.description,
            xp=definition.xp,
            category=definition.category,
            completion_type=definition.completion_type,
            status=status,
            progress_label=progress_label,
            action_label=self._action_label(status, definition.completion_type),
            completion_source=completion_source,
        )

    def _learning_progress(self, definition: GameQuestDefinition, pulse: LearningPulse) -> tuple[bool, str]:
        if definition.key == "python-focus":
            completed = pulse.python_minutes >= 25
            return completed, f"Python {pulse.python_minutes}/25 分鐘"
        if definition.key == "japanese-review":
            completed = pulse.japanese_minutes >= 15 or pulse.anki_reviews > 0
            return completed, f"日文 {pulse.japanese_minutes}/15 分鐘，Anki {pulse.anki_reviews} 張"
        return False, "手動確認"

    def _action_label(self, status: GameQuestStatus, completion_type: GameQuestCompletionType) -> str | None:
        if status == GameQuestStatus.completed:
            return "已完成"
        if status == GameQuestStatus.skipped:
            return "今天先休息"
        if completion_type == GameQuestCompletionType.learning_signal:
            return "等待學習訊號"
        return "可手動完成"

    def _gentle_message(self, completed_count: int, skipped_count: int, total_count: int) -> str:
        if completed_count == total_count:
            return "今日任務全數完成。很好，冒險者，今天的營火可以安穩一點。"
        if completed_count == 0 and skipped_count > 0:
            return "今天先把節奏保住就好。跳過不是失敗，是重新分配體力。"
        if completed_count == 0:
            return "先挑一個最小任務開始。LifeQuest 不扣分，只幫你把路標點亮。"
        return f"已完成 {completed_count} 個任務。剩下的可以慢慢來，今天不是 KPI，是一段旅程。"

    def _record_event(
        self,
        quest_key: str,
        action: GameQuestAction,
        target_date: date | None,
    ) -> GameQuestEvent:
        now = datetime.now(timezone.utc)
        return self.repository.upsert_event(
            GameQuestEvent(
                quest_key=quest_key,
                event_date=target_date or date.today(),
                action=action,
                created_at=now,
                updated_at=now,
            )
        )

    def _get_definition(self, quest_key: str) -> GameQuestDefinition:
        definition = self.quest_definitions.get(quest_key)
        if definition is None:
            raise GameQuestNotFoundError(f"Quest not found: {quest_key}")
        return definition
