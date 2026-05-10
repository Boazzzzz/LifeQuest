const root = document.getElementById("root");
const LOCALE = "zh-TW";

const fallbackOverview = {
  target_date: currentDateString(),
  hero: {
    status: "prototype",
    headline: "首頁還在接線中，但方向已經很明確。",
    summary: "這裡會慢慢變成你每天打開後，能立刻理解今天狀態與下一步的控制中心。",
    focus_score: 0,
    session_count: 0,
    tomorrow_priority: "先把最小可完成的一步做出來。",
    warnings: ["目前無法讀取 live overview，先使用備援內容。"],
  },
  learning: {
    status: "quiet",
    recommendation: "先完成一小段學習，再讓儀表板開始長出訊號。",
    pulse: {
      total_minutes: 0,
      python_minutes: 0,
      japanese_minutes: 0,
      sre_minutes: 0,
      session_count: 0,
      focus_score: 0,
      tomorrow_priority: "先把最小可完成的一步做出來。",
      integration_warnings: [],
    },
    recent_sessions: [],
  },
  subscriptions: {
    status: "quiet",
    next_charge_name: null,
    next_charge_date: null,
    overview: {
      active_subscription_count: 0,
      paused_subscription_count: 0,
      cancelled_subscription_count: 0,
      missing_schedule_count: 0,
      totals_by_currency: {},
      upcoming_charges: [],
    },
  },
  automations: {
    total_count: 0,
    enabled_count: 0,
    healthy_count: 0,
    needs_attention_count: 0,
    definitions: [],
    recent_runs: [],
  },
  knowledge: {
    note_count: 0,
    follow_up_count: 0,
    recent_notes: [],
  },
  attention_items: [
    {
      severity: "info",
      title: "目前使用備援首頁",
      detail: "後端 overview API 還沒回來時，這裡會先保留一個可閱讀的骨架。",
      href: "/docs",
    },
  ],
  launchpad: [
    {
      key: "learning",
      title: "學習",
      summary: "先從學習切片開始讓控制中心長出真實感。",
      href: "/japanese",
      metric: "0 分鐘",
      status_label: "quiet",
    },
  ],
  recent_activity: [
    {
      id: "fallback-activity-1",
      title: "Overview API is not available yet",
      detail: "This area will show a living stream of learning, subscriptions, automation, and knowledge events.",
      href: "/docs",
      tone: "neutral",
      occurred_at: new Date().toISOString(),
    },
  ],
};

document.addEventListener("DOMContentLoaded", () => {
  void loadDashboard();
});

async function loadDashboard() {
  const overview = (await safeFetchJson("/dashboard/overview")) ?? fallbackOverview;
  render(overview);
}

function render(data) {
  const pulse = data.learning.pulse ?? fallbackOverview.learning.pulse;
  const subscriptionOverview = data.subscriptions.overview ?? fallbackOverview.subscriptions.overview;
  const totals = Object.entries(subscriptionOverview.totals_by_currency ?? {});
  const upcomingCharges = (subscriptionOverview.upcoming_charges ?? []).slice(0, 4);
  const attentionItems = data.attention_items ?? [];
  const launchpad = data.launchpad ?? [];
  const recentSessions = data.learning.recent_sessions ?? [];
  const recentNotes = data.knowledge.recent_notes ?? [];
  const recentRuns = data.automations.recent_runs ?? [];
  const automationDefs = data.automations.definitions ?? [];
  const recentActivity = data.recent_activity ?? [];

  root.innerHTML = `
    <main class="shell">
      <header class="topbar" data-reveal>
        <div class="brand">
          <span class="brand-mark" aria-hidden="true"></span>
          <div>
            <div class="brand-name">LifeQuest</div>
            <div class="brand-subtitle">用一個安靜但有判斷力的首頁，管理學習、生活、知識與自動化。</div>
          </div>
        </div>
        <nav class="nav-pills">
          <a class="pill" href="#attention">注意事項</a>
          <a class="pill" href="#launchpad">模組入口</a>
          <a class="pill" href="#recent">近期訊號</a>
          <a class="pill" href="/docs">API</a>
        </nav>
      </header>

      <section class="hero" data-reveal data-delay="1">
        <div>
          <p class="eyebrow">Daily Control Center</p>
          <h1 class="hero-title">${escapeHtml(data.hero.headline)}</h1>
          <p class="hero-text">${escapeHtml(data.hero.summary)}</p>
          <div class="hero-pill-row">
            ${heroPill("今日日期", formatShortDate(data.target_date))}
            ${heroPill("專注分數", String(pulse.focus_score ?? 0))}
            ${heroPill("學習紀錄", `${pulse.session_count ?? 0} 筆`)}
          </div>
          <div class="hero-actions">
            <a class="button button-primary" href="/japanese">打開學習切片</a>
            <a class="button button-secondary" href="/nightly">睡前自學回顧</a>
            <a class="button button-secondary" href="/life-admin/subscriptions">檢查生活管理</a>
            <a class="button button-secondary" href="/review/weekly">本週回顧</a>
            <a class="button button-secondary" href="/docs">瀏覽 API</a>
          </div>
        </div>
        <aside class="hero-side">
          <section class="glass-card">
            <div class="status-line">
              <div>
                <div class="mini-label">首頁狀態</div>
                <strong>${data.hero.status === "live" ? "Live overview" : "Prototype fallback"}</strong>
              </div>
              <span class="status-chip">${data.hero.status === "live" ? "已連線" : "備援"}</span>
            </div>
            <div class="prototype-banner">${escapeHtml(data.hero.tomorrow_priority)}</div>
            ${renderWarnings(data.hero.warnings ?? [])}
          </section>
          <section class="hero-mini-grid">
            ${miniCard("使用中訂閱", String(subscriptionOverview.active_subscription_count ?? 0))}
            ${miniCard("自動化", String(data.automations.total_count ?? 0))}
            ${miniCard("知識筆記", String(data.knowledge.note_count ?? 0))}
            ${miniCard("待注意", String(attentionItems.length))}
          </section>
        </aside>
      </section>

      <section class="content-grid">
        <div class="metrics-grid" data-reveal data-delay="1">
          ${metricCard("學習脈搏", `${pulse.total_minutes ?? 0} 分鐘`, "今天累積的總學習時間。", statusLabel(data.learning.status))}
          ${metricCard("Python", `${pulse.python_minutes ?? 0} 分鐘`, "實作、腳本與開發練習。", "build")}
          ${metricCard("日文", `${pulse.japanese_minutes ?? 0} 分鐘`, "Anki、閱讀或複習時間。", "review")}
          ${metricCard("SRE", `${pulse.sre_minutes ?? 0} 分鐘`, "Linux、網路、可靠性與維運練習。", "ops")}
          ${metricCard("固定支出", `${subscriptionOverview.active_subscription_count ?? 0} 筆`, "目前仍在使用中的訂閱。", statusLabel(data.subscriptions.status))}
        </div>

        <div class="two-up">
          <section class="panel" id="attention" data-reveal data-delay="2">
            <div class="section-head">
              <div>
                <h2 class="section-title">今天值得注意</h2>
                <p class="section-subtitle">首頁第一件事不是展示資料，而是幫你縮小注意力範圍。</p>
              </div>
            </div>
            <div class="attention-list">
              ${attentionItems.map((item) => attentionRow(item)).join("")}
            </div>
          </section>

          <section class="panel" id="launchpad" data-reveal data-delay="2">
            <div class="section-head">
              <div>
                <h2 class="section-title">下一步去哪裡</h2>
                <p class="section-subtitle">每個模組都應該像一個明確入口，而不是模糊的待辦集合。</p>
              </div>
            </div>
            <div class="launchpad-grid">
              ${launchpad.map((item) => launchpadCard(item)).join("")}
            </div>
          </section>
        </div>

        <div class="two-up" id="recent">
          <section class="panel" data-reveal data-delay="3">
            <div class="section-head">
              <div>
                <h2 class="section-title">近期學習與扣款</h2>
                <p class="section-subtitle">${escapeHtml(data.learning.recommendation)}</p>
              </div>
            </div>
            <div class="signal-grid">
              <div>
                <div class="list-label">近期學習紀錄</div>
                <div class="list-stack">
                  ${recentSessions.length ? recentSessions.map((session) => sessionRow(session)).join("") : emptyState("今天還沒有學習紀錄。")}
                </div>
              </div>
              <div>
                <div class="list-label">近期扣款</div>
                <div class="list-stack">
                  ${upcomingCharges.length ? upcomingCharges.map((charge) => chargeRow(charge)).join("") : emptyState("目前沒有已知的近期扣款。")}
                </div>
              </div>
            </div>
          </section>

          <section class="panel" data-reveal data-delay="3">
            <div class="section-head">
              <div>
                <h2 class="section-title">知識與自動化訊號</h2>
                <p class="section-subtitle">這裡會慢慢變成你觀察「有沒有事情在自己運作」的地方。</p>
              </div>
            </div>
            <div class="signal-grid">
              <div>
                <div class="list-label">近期知識筆記</div>
                <div class="list-stack">
                  ${recentNotes.length ? recentNotes.map((note) => noteRow(note)).join("") : emptyState("還沒有知識筆記，這裡之後會很好用。")}
                </div>
              </div>
              <div>
                <div class="list-label">最近自動化執行</div>
                <div class="list-stack">
                  ${recentRuns.length ? recentRuns.map((run) => automationRunRow(run)).join("") : emptyState("還沒有執行紀錄，先把最常用的一個腳本接進來最划算。")}
                </div>
              </div>
            </div>
          </section>
        </div>

        <section class="panel" data-reveal data-delay="3">
          <div class="section-head">
            <div>
              <h2 class="section-title">Recent Activity</h2>
              <p class="section-subtitle">這一小塊讓首頁開始有「系統正在運作」的流動感，而不只是靜態摘要。</p>
            </div>
          </div>
          <div class="list-stack">
            ${recentActivity.length ? recentActivity.map((item) => activityRow(item)).join("") : emptyState("最近還沒有 activity 事件。")}
          </div>
        </section>

        <section class="panel" data-reveal data-delay="3">
          <div class="section-head">
            <div>
              <h2 class="section-title">模組健康度</h2>
              <p class="section-subtitle">這一區不求完整，但要讓你一眼知道哪些模組已經開始像產品，而不是資料堆。</p>
            </div>
          </div>
          <div class="module-grid">
            ${moduleCard("學習", `今天 ${pulse.total_minutes ?? 0} 分鐘，${pulse.session_count ?? 0} 筆紀錄。`, statusLabel(data.learning.status), "tone-learning")}
            ${moduleCard("生活管理", `使用中 ${subscriptionOverview.active_subscription_count ?? 0} 筆，待補排程 ${subscriptionOverview.missing_schedule_count ?? 0} 筆。`, statusLabel(data.subscriptions.status), "tone-admin")}
            ${moduleCard("知識", `目前 ${data.knowledge.note_count ?? 0} 則筆記，待跟進 ${data.knowledge.follow_up_count ?? 0} 則。`, "capturing", "tone-knowledge")}
            ${moduleCard("自動化", `共 ${data.automations.total_count ?? 0} 個，自動判定待留意 ${data.automations.needs_attention_count ?? 0} 個。`, data.automations.needs_attention_count ? "attention" : "steady", "tone-automation")}
            ${moduleCard("週回顧", "現在已經有專屬頁面，開始把本週訊號變成下週方向。", "live", "tone-review")}
          </div>
          <div class="detail-grid">
            <div>
              <div class="list-label">自動化定義</div>
              <div class="list-stack">
                ${automationDefs.length ? automationDefs.map((item) => automationDefinitionRow(item)).join("") : emptyState("目前還沒有已註冊的自動化。")}
              </div>
            </div>
            <div>
              <div class="list-label">幣別總覽</div>
              <div class="list-stack">
                ${totals.length ? totals.map(([currency, total]) => currencyRow(currency, total)).join("") : emptyState("尚未建立任何訂閱資料。")}
              </div>
            </div>
          </div>
        </section>
      </section>
    </main>
  `;
}

async function safeFetchJson(url) {
  try {
    const response = await fetch(url);
    if (!response.ok) {
      return null;
    }
    return await response.json();
  } catch {
    return null;
  }
}

function heroPill(label, value) {
  return `<div class="hero-pill"><span class="mini-label">${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
}

function miniCard(label, value) {
  return `<div class="mini-card"><div class="mini-label">${escapeHtml(label)}</div><div class="mini-value">${escapeHtml(String(value))}</div></div>`;
}

function metricCard(label, value, text, trend) {
  return `<article class="metric-card"><div class="metric-top"><div class="metric-label">${escapeHtml(label)}</div><div class="metric-trend">${escapeHtml(trend)}</div></div><div class="metric-value">${escapeHtml(value)}</div><div class="metric-text">${escapeHtml(text)}</div></article>`;
}

function moduleCard(title, text, footer, toneClass) {
  return `<article class="module-card ${toneClass}"><div class="module-kicker">Module</div><h3 class="module-title">${escapeHtml(title)}</h3><p class="module-text">${escapeHtml(text)}</p><div class="module-footer">${escapeHtml(footer)}</div></article>`;
}

function launchpadCard(item) {
  return `
    <a class="launchpad-card" href="${escapeAttribute(item.href)}">
      <div class="module-kicker">${escapeHtml(item.status_label)}</div>
      <div class="launchpad-top">
        <h3 class="module-title">${escapeHtml(item.title)}</h3>
        <span class="metric-trend">${escapeHtml(item.metric)}</span>
      </div>
      <p class="module-text">${escapeHtml(item.summary)}</p>
    </a>
  `;
}

function attentionRow(item) {
  return `
    <a class="attention-item" href="${escapeAttribute(item.href || "/dashboard")}">
      <span class="attention-badge attention-${escapeAttribute(item.severity)}">${escapeHtml(item.severity)}</span>
      <div>
        <div class="item-title">${escapeHtml(item.title)}</div>
        <div class="item-meta">${escapeHtml(item.detail)}</div>
      </div>
    </a>
  `;
}

function sessionRow(session) {
  return `
    <article class="signal-row">
      <div>
        <div class="item-title">${escapeHtml(localizeSubject(session.subject))}</div>
        <div class="item-meta">${escapeHtml(session.summary || "未提供摘要")}</div>
      </div>
      <div class="signal-side">
        <strong>${escapeHtml(`${session.duration_minutes} 分鐘`)}</strong>
        <span class="item-meta">${escapeHtml(formatDateTime(session.started_at))}</span>
      </div>
    </article>
  `;
}

function noteRow(note) {
  return `
    <article class="signal-row">
      <div>
        <div class="item-title">${escapeHtml(note.title)}</div>
        <div class="item-meta">${escapeHtml(localizeCategory(note.category))}${note.follow_up ? " · 有 follow-up" : ""}</div>
      </div>
      <div class="signal-side">
        <strong>${escapeHtml(formatDateTime(note.created_at))}</strong>
        <span class="item-meta">${escapeHtml((note.tags ?? []).slice(0, 2).join(" / ") || "筆記")}</span>
      </div>
    </article>
  `;
}

function automationRunRow(run) {
  return `
    <article class="signal-row">
      <div>
        <div class="item-title">${escapeHtml(run.automation_name)}</div>
        <div class="item-meta">${escapeHtml(run.summary || "沒有摘要")}</div>
      </div>
      <div class="signal-side">
        <strong>${escapeHtml(run.status)}</strong>
        <span class="item-meta">${escapeHtml(formatDateTime(run.started_at))}</span>
      </div>
    </article>
  `;
}

function automationDefinitionRow(item) {
  const lastRun = item.last_run_at ? formatDateTime(item.last_run_at) : "尚未執行";
  return `
    <article class="signal-row">
      <div>
        <div class="item-title">${escapeHtml(item.name)}</div>
        <div class="item-meta">${escapeHtml(item.category)} · ${escapeHtml(item.enabled ? "enabled" : "disabled")}</div>
      </div>
      <div class="signal-side">
        <strong>${escapeHtml(item.last_run_status || "pending")}</strong>
        <span class="item-meta">${escapeHtml(lastRun)}</span>
      </div>
    </article>
  `;
}

function activityRow(item) {
  return `
    <a class="activity-row" href="${escapeAttribute(item.href || "/dashboard")}">
      <div>
        <div class="item-title">${escapeHtml(item.title)}</div>
        <div class="item-meta">${escapeHtml(item.detail)}</div>
      </div>
      <div class="signal-side">
        <span class="activity-tone activity-tone-${escapeAttribute(item.tone || "neutral")}">${escapeHtml(item.tone || "neutral")}</span>
        <span class="item-meta">${escapeHtml(formatDateTime(item.occurred_at))}</span>
      </div>
    </a>
  `;
}

function currencyRow(currency, total) {
  return `<div class="currency-row"><span class="currency-label">${escapeHtml(currency)}</span><span class="currency-value">${escapeHtml(`${currency} ${Number(total).toFixed(2)}`)}</span></div>`;
}

function chargeRow(charge) {
  const dateLabel = charge.next_charge_date ? formatShortDate(charge.next_charge_date) : "缺少日期";
  const detail = charge.days_until_charge === 0 ? "今天扣款" : `${charge.days_until_charge} 天後`;
  return `
    <article class="signal-row">
      <div>
        <div class="item-title">${escapeHtml(charge.name)}</div>
        <div class="item-meta">${escapeHtml(`${charge.currency} ${Number(charge.amount).toFixed(2)} · ${detail}`)}</div>
      </div>
      <div class="signal-side">
        <strong>${escapeHtml(dateLabel)}</strong>
        <span class="item-meta">${escapeHtml(charge.schedule_summary || "訂閱")}</span>
      </div>
    </article>
  `;
}

function renderWarnings(warnings) {
  if (!warnings.length) {
    return "";
  }
  return `<div class="warning-list">${warnings.map((warning) => `<div class="warning-row">${escapeHtml(warning)}</div>`).join("")}</div>`;
}

function emptyState(text) {
  return `<div class="empty-state">${escapeHtml(text)}</div>`;
}

function statusLabel(value) {
  switch (value) {
    case "strong":
      return "strong";
    case "active":
      return "active";
    case "needs_review":
      return "needs review";
    case "scheduled":
      return "scheduled";
    case "quiet":
      return "quiet";
    default:
      return String(value || "live");
  }
}

function localizeSubject(subject) {
  if (subject === "python") {
    return "Python";
  }
  if (subject === "japanese") {
    return "日文";
  }
  return subject || "學習";
}

function localizeCategory(category) {
  const labels = {
    linux: "Linux",
    networking: "Networking",
    docker: "Docker",
    nginx: "Nginx",
    database: "Database",
    security: "Security",
    monitoring: "Monitoring",
    cloud: "Cloud",
    automation: "Automation",
    other: "Other",
  };
  return labels[category] || category || "Note";
}

function currentDateString() {
  const now = new Date();
  const offset = now.getTimezoneOffset();
  return new Date(now.getTime() - offset * 60000).toISOString().slice(0, 10);
}

function formatShortDate(value) {
  return new Date(`${value}T00:00:00`).toLocaleDateString(LOCALE, { month: "short", day: "numeric" });
}

function formatDateTime(value) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "未知時間";
  }
  return parsed.toLocaleString(LOCALE, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function escapeAttribute(value) {
  return escapeHtml(value);
}
