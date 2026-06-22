from datetime import date, datetime, timezone

from app.models.automation import AutomationRunStatus
from app.models.dashboard import (
    DashboardAttentionItem,
    DashboardAttentionSeverity,
    DashboardAutomationDefinitionSummary,
    DashboardAutomationRunSummary,
    DashboardAutomationsOverview,
    DashboardHero,
    DashboardKnowledgeNoteSummary,
    DashboardKnowledgeOverview,
    DashboardLaunchpadItem,
    DashboardLearningOverview,
    DashboardOverview,
    DashboardSubscriptionsOverview,
)
from app.models.learning import LearningPulse
from app.models.subscription import SubscriptionMonthlyOverview
from app.services.activity import ActivityService
from app.services.automation import AutomationService
from app.services.learning import LearningService
from app.services.money import MoneyService
from app.services.subscription import SubscriptionService
from app.services.work_knowledge import WorkKnowledgeService


class DashboardService:
    def __init__(
        self,
        learning_service: LearningService | None = None,
        subscription_service: SubscriptionService | None = None,
        automation_service: AutomationService | None = None,
        work_knowledge_service: WorkKnowledgeService | None = None,
        activity_service: ActivityService | None = None,
        money_service: MoneyService | None = None,
    ) -> None:
        self.learning_service = learning_service or LearningService()
        self.subscription_service = subscription_service or SubscriptionService()
        self.automation_service = automation_service or AutomationService()
        self.work_knowledge_service = work_knowledge_service or WorkKnowledgeService()
        self.activity_service = activity_service or ActivityService()
        self.money_service = money_service or MoneyService()

    async def build_overview(self, target_date: date | None = None) -> DashboardOverview:
        target_date = target_date or date.today()
        pulse = await self.learning_service.build_pulse(target_date)
        recent_sessions = self.learning_service.learning_repository.list_sessions_for_date(target_date)[-3:]
        subscription_overview = self.subscription_service.build_monthly_overview(
            target_date=target_date,
            days_ahead=35,
        )
        automation_definitions = self.automation_service.list_definitions()
        recent_runs = self.automation_service.list_recent_runs(limit=5)
        notes = self.work_knowledge_service.list_notes(limit=200)
        money_overview = self.money_service.build_overview()

        automations = self._build_automations_overview(automation_definitions, recent_runs)
        knowledge = self._build_knowledge_overview(notes)
        subscriptions = self._build_subscriptions_overview(subscription_overview)
        attention_items = self._build_attention_items(
            pulse=pulse,
            subscriptions=subscription_overview,
            automations=automations,
            knowledge=knowledge,
            money_attention=money_overview.attention_items,
        )
        hero = self._build_hero(
            target_date=target_date,
            pulse=pulse,
            subscriptions=subscription_overview,
            automations=automations,
            attention_items=attention_items,
        )
        learning = DashboardLearningOverview(
            pulse=pulse,
            recent_sessions=recent_sessions,
            status=self._learning_status(pulse),
            recommendation=self._learning_recommendation(pulse),
        )
        launchpad = self._build_launchpad(
            learning=learning,
            subscriptions=subscriptions,
            automations=automations,
            knowledge=knowledge,
            money_overview=money_overview,
        )
        recent_activity = self.activity_service.get_recent_timeline(limit=6).items

        return DashboardOverview(
            generated_at=datetime.now(timezone.utc),
            target_date=target_date,
            hero=hero,
            learning=learning,
            subscriptions=subscriptions,
            automations=automations,
            knowledge=knowledge,
            attention_items=attention_items,
            launchpad=launchpad,
            recent_activity=recent_activity,
        )

    def _build_hero(
        self,
        target_date: date,
        pulse: LearningPulse,
        subscriptions: SubscriptionMonthlyOverview,
        automations: DashboardAutomationsOverview,
        attention_items: list[DashboardAttentionItem],
    ) -> DashboardHero:
        if pulse.total_minutes >= 120:
            headline = "今天的節奏很穩，先守住這股動能。"
        elif pulse.total_minutes > 0:
            headline = "今天已經有進展，接下來把閉環做完整。"
        else:
            headline = "今天還很空白，先完成一個最小但明確的前進。"

        summary_parts = [
            f"今天累積 {pulse.total_minutes} 分鐘學習，{pulse.session_count} 筆紀錄。",
            f"接下來 35 天內有 {len(subscriptions.upcoming_charges)} 筆已知訂閱扣款。",
        ]
        if automations.total_count:
            summary_parts.append(f"目前追蹤 {automations.total_count} 個自動化，其中 {automations.needs_attention_count} 個需要留意。")
        else:
            summary_parts.append("自動化總覽還在起步階段，現在最重要的是先把觀測面接起來。")
        if not attention_items:
            summary_parts.append("目前沒有明顯警報。")

        return DashboardHero(
            target_date=target_date,
            headline=headline,
            summary=" ".join(summary_parts),
            focus_score=pulse.focus_score,
            session_count=pulse.session_count,
            tomorrow_priority=pulse.tomorrow_priority,
            warnings=pulse.integration_warnings,
        )

    def _build_subscriptions_overview(
        self,
        overview: SubscriptionMonthlyOverview,
    ) -> DashboardSubscriptionsOverview:
        next_charge = overview.upcoming_charges[0] if overview.upcoming_charges else None
        if overview.missing_schedule_count:
            status = "needs_review"
        elif next_charge is not None:
            status = "scheduled"
        else:
            status = "quiet"
        return DashboardSubscriptionsOverview(
            overview=overview,
            status=status,
            next_charge_name=next_charge.name if next_charge is not None else None,
            next_charge_date=next_charge.next_charge_date if next_charge is not None else None,
        )

    def _build_automations_overview(self, definitions, recent_runs) -> DashboardAutomationsOverview:
        definition_map = {definition.id: definition for definition in definitions}
        attention_statuses = {AutomationRunStatus.failed, AutomationRunStatus.partial}
        enabled_count = sum(1 for definition in definitions if definition.enabled)
        needs_attention_count = sum(
            1
            for definition in definitions
            if definition.enabled and definition.last_run_status in attention_statuses
        )
        healthy_count = sum(
            1
            for definition in definitions
            if definition.enabled and definition.last_run_status not in attention_statuses
        )

        ordered_definitions = sorted(
            definitions,
            key=lambda definition: (
                0
                if definition.enabled and definition.last_run_status in attention_statuses
                else 1,
                0 if definition.enabled else 1,
                -(definition.last_run_at.timestamp()) if definition.last_run_at is not None else float("inf"),
                definition.name.casefold(),
            ),
        )

        previews = [
            DashboardAutomationDefinitionSummary(
                key=definition.key,
                name=definition.name,
                category=definition.category,
                enabled=definition.enabled,
                last_run_at=definition.last_run_at,
                last_run_status=definition.last_run_status,
                last_run_summary=definition.last_run_summary,
            )
            for definition in ordered_definitions[:4]
        ]
        run_summaries = []
        for run in recent_runs:
            definition = definition_map.get(run.automation_id)
            if definition is None:
                continue
            run_summaries.append(
                DashboardAutomationRunSummary(
                    automation_key=definition.key,
                    automation_name=definition.name,
                    status=run.status,
                    started_at=run.started_at,
                    finished_at=run.finished_at,
                    summary=run.summary,
                    items_processed=run.items_processed,
                )
            )

        return DashboardAutomationsOverview(
            total_count=len(definitions),
            enabled_count=enabled_count,
            healthy_count=healthy_count,
            needs_attention_count=needs_attention_count,
            definitions=previews,
            recent_runs=run_summaries,
        )

    def _build_knowledge_overview(self, notes) -> DashboardKnowledgeOverview:
        recent_notes = [
            DashboardKnowledgeNoteSummary(
                id=note.id,
                title=note.title,
                category=note.category,
                created_at=note.created_at,
                follow_up=note.follow_up,
                tags=note.tags,
            )
            for note in notes[:4]
        ]
        return DashboardKnowledgeOverview(
            note_count=len(notes),
            follow_up_count=sum(1 for note in notes if note.follow_up),
            recent_notes=recent_notes,
        )

    def _build_attention_items(
        self,
        pulse: LearningPulse,
        subscriptions: SubscriptionMonthlyOverview,
        automations: DashboardAutomationsOverview,
        knowledge: DashboardKnowledgeOverview,
        money_attention,
    ) -> list[DashboardAttentionItem]:
        items: list[DashboardAttentionItem] = []

        if pulse.total_minutes == 0:
            items.append(
                DashboardAttentionItem(
                    severity=DashboardAttentionSeverity.warning,
                    title="今天還沒有學習紀錄",
                    detail="先完成一段最小學習區塊，讓首頁開始出現真實訊號。",
                    href="/japanese",
                )
            )
        for warning in pulse.integration_warnings:
            items.append(
                DashboardAttentionItem(
                    severity=DashboardAttentionSeverity.warning,
                    title="學習整合有警告",
                    detail=warning,
                    href="/docs",
                )
            )

        if subscriptions.missing_schedule_count:
            items.append(
                DashboardAttentionItem(
                    severity=DashboardAttentionSeverity.warning,
                    title="有訂閱仍缺少扣款排程",
                    detail=f"目前有 {subscriptions.missing_schedule_count} 筆訂閱需要補記日期或週期。",
                    href="/life-admin/subscriptions",
                )
            )
        elif subscriptions.upcoming_charges:
            next_charge = subscriptions.upcoming_charges[0]
            if next_charge.days_until_charge <= 3:
                items.append(
                    DashboardAttentionItem(
                        severity=DashboardAttentionSeverity.info,
                        title="近期有訂閱即將扣款",
                        detail=f"{next_charge.name} 將在 {next_charge.days_until_charge} 天內扣款。",
                        href="/life-admin/subscriptions",
                    )
                )

        if automations.needs_attention_count:
            items.append(
                DashboardAttentionItem(
                    severity=DashboardAttentionSeverity.warning,
                    title="有自動化最近執行不穩",
                    detail=f"目前有 {automations.needs_attention_count} 個自動化的最近一次結果需要留意。",
                    href="/docs#/automations",
                )
            )

        if knowledge.follow_up_count:
            items.append(
                DashboardAttentionItem(
                    severity=DashboardAttentionSeverity.info,
                    title="知識筆記裡有待跟進事項",
                    detail=f"最近筆記中有 {knowledge.follow_up_count} 則 follow-up 可以回頭處理。",
                    href="/docs#/work-knowledge",
                )
            )

        for item in money_attention:
            items.append(
                DashboardAttentionItem(
                    severity=DashboardAttentionSeverity.warning
                    if item.severity in {"warning", "failed"}
                    else DashboardAttentionSeverity.info,
                    title=item.title,
                    detail=item.detail,
                    href=item.href,
                )
            )

        if not items:
            items.append(
                DashboardAttentionItem(
                    severity=DashboardAttentionSeverity.positive,
                    title="目前沒有明顯警報",
                    detail="今天可以把注意力放在推進最重要的模組，而不是先滅火。",
                    href="/dashboard",
                )
            )
        return items[:6]

    def _build_launchpad(
        self,
        learning: DashboardLearningOverview,
        subscriptions: DashboardSubscriptionsOverview,
        automations: DashboardAutomationsOverview,
        knowledge: DashboardKnowledgeOverview,
        money_overview,
    ) -> list[DashboardLaunchpadItem]:
        return [
            DashboardLaunchpadItem(
                key="learning",
                title="學習",
                summary="先看今天的學習脈搏、Anki 狀態與日文切片。",
                href="/japanese",
                metric=f"{learning.pulse.total_minutes} 分鐘",
                status_label=learning.status,
            ),
            DashboardLaunchpadItem(
                key="subscriptions",
                title="生活管理",
                summary="追蹤固定支出、扣款日與需要補記的訂閱排程。",
                href="/life-admin/subscriptions",
                metric=f"{subscriptions.overview.active_subscription_count} 筆使用中",
                status_label=subscriptions.status,
            ),
            DashboardLaunchpadItem(
                key="money",
                title="Money Quest",
                summary="Protect goals, review cashflow, and keep leverage plans behind guardrails.",
                href="/life-admin/money",
                metric=f"{len(money_overview.leverage_plans)} plans",
                status_label="attention" if money_overview.attention_items else "steady",
            ),
            DashboardLaunchpadItem(
                key="automations",
                title="自動化",
                summary="確認哪些腳本穩定、哪些還需要觀察或補接。",
                href="/docs#/automations",
                metric=f"{automations.needs_attention_count} 個待留意",
                status_label="attention" if automations.needs_attention_count else "steady",
            ),
            DashboardLaunchpadItem(
                key="knowledge",
                title="知識",
                summary="工作筆記與參考資料要開始長成可回顧、可重用的層。",
                href="/docs#/work-knowledge",
                metric=f"{knowledge.note_count} 則筆記",
                status_label="follow-up" if knowledge.follow_up_count else "capturing",
            ),
        ]

    def _learning_status(self, pulse: LearningPulse) -> str:
        if pulse.total_minutes >= 90:
            return "strong"
        if pulse.total_minutes > 0:
            return "active"
        return "quiet"

    def _learning_recommendation(self, pulse: LearningPulse) -> str:
        if pulse.total_minutes == 0:
            return "先完成一段很短的學習區塊，目標不是完美，而是重新把節奏接上。"
        if pulse.python_minutes == 0:
            return "今天已有進展，接下來可以補一段 Python 實作，讓學習脈搏更完整。"
        if pulse.japanese_minutes == 0:
            return "今天已有進展，接下來補一輪日文複習，讓節奏更平衡。"
        return "今天兩條主線都有訊號，下一步優先把最重要的一個小閉環做完。"
