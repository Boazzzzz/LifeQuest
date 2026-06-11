const root = document.getElementById("root");
const LOCALE = "zh-TW";

const fallbackOverview = {
  target_date: currentDateString(),
  hero: {
    status: "prototype",
    headline: "LifeQuest 控制中心",
    summary: "這裡會整理今天的學習、生活管理、知識和自動化狀態。",
    focus_score: 0,
    session_count: 0,
    tomorrow_priority: "先記錄今天學了什麼。",
    warnings: ["目前無法讀取 live overview，先使用備援內容。"],
  },
  learning: {
    status: "quiet",
    recommendation: "先完成一小段學習，再讓首頁開始長出真實訊號。",
    pulse: {
      total_minutes: 0,
      python_minutes: 0,
      japanese_minutes: 0,
      sre_minutes: 0,
      session_count: 0,
      focus_score: 0,
      tomorrow_priority: "先記錄今天學了什麼。",
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
      detail: "後端 overview API 還沒回來時，這裡會先保留可操作入口。",
      href: "/docs",
    },
  ],
  launchpad: [],
  recent_activity: [],
};

document.addEventListener("DOMContentLoaded", () => {
  void loadDashboard();
});

async function loadDashboard() {
  const overview = (await safeFetchJson("/dashboard/overview")) ?? fallbackOverview;
  render(overview);
}

function render(data) {
  const pulse = data.learning?.pulse ?? fallbackOverview.learning.pulse;
  const subscriptionOverview = data.subscriptions?.overview ?? fallbackOverview.subscriptions.overview;
  const attentionItems = data.attention_items ?? [];
  const recentSessions = data.learning?.recent_sessions ?? [];
  const recentActivity = data.recent_activity ?? [];
  const recentNotes = data.knowledge?.recent_notes ?? [];
  const recentRuns = data.automations?.recent_runs ?? [];
  const upcomingCharges = (subscriptionOverview.upcoming_charges ?? []).slice(0, 3);
  const primaryActions = buildPrimaryActions(data, pulse);
  const modules = buildModules(data, pulse, subscriptionOverview);

  root.innerHTML = `
    <main class="shell">
      <header class="topbar">
        <a class="brand" href="/dashboard">
          <span class="brand-mark" aria-hidden="true">LQ</span>
          <span>
            <strong>LifeQuest</strong>
            <small>Home Hub</small>
          </span>
        </a>
        <nav class="topnav" aria-label="主導覽">
          <a href="/nightly">記錄學習</a>
          <a href="/japanese">日文</a>
          <a href="/life-admin/subscriptions">訂閱</a>
          <a href="/review/weekly">週回顧</a>
        </nav>
      </header>

      <section class="home-hero">
        <div class="hero-main">
          <p class="eyebrow">${escapeHtml(formatShortDate(data.target_date))}</p>
          <h1>${escapeHtml(data.hero?.headline ?? "LifeQuest 控制中心")}</h1>
          <p>${escapeHtml(data.hero?.summary ?? fallbackOverview.hero.summary)}</p>
          <div class="hero-actions">
            <a class="button button-primary" href="/nightly">記錄今天學什麼</a>
            <a class="button button-secondary" href="/japanese">看日文學習</a>
            <a class="button button-secondary" href="/review/weekly">做週回顧</a>
          </div>
        </div>
        <aside class="today-panel" aria-label="今日狀態">
          ${statBlock("今日學習", `${pulse.total_minutes ?? 0} 分鐘`, `${pulse.session_count ?? 0} 筆紀錄`)}
          ${statBlock("專注分數", String(pulse.focus_score ?? 0), data.learning?.status ?? "quiet")}
          ${statBlock("下個優先", data.hero?.tomorrow_priority ?? pulse.tomorrow_priority ?? "先記錄一段學習", "Learning pulse")}
        </aside>
      </section>

      <section class="section-grid quick-grid" aria-label="快速操作">
        ${primaryActions.map(actionCard).join("")}
      </section>

      <section class="content-layout">
        <section class="panel">
          <div class="section-head">
            <h2>模組入口</h2>
            <p>每天打開首頁後，從這裡進入你要處理的區域。</p>
          </div>
          <div class="module-grid">
            ${modules.map(moduleCard).join("")}
          </div>
        </section>

        <aside class="panel">
          <div class="section-head">
            <h2>需要留意</h2>
            <p>LifeQuest 幫你把今天最該看一眼的訊號放在這裡。</p>
          </div>
          <div class="list-stack">
            ${attentionItems.length ? attentionItems.map(attentionRow).join("") : emptyState("目前沒有需要立即處理的提醒。")}
          </div>
        </aside>
      </section>

      <section class="content-layout">
        <section class="panel">
          <div class="section-head">
            <h2>近期學習</h2>
            <p>${escapeHtml(data.learning?.recommendation ?? fallbackOverview.learning.recommendation)}</p>
          </div>
          <div class="list-stack">
            ${recentSessions.length ? recentSessions.map(sessionRow).join("") : emptyState("今天還沒有 learning session。")}
          </div>
        </section>

        <section class="panel">
          <div class="section-head">
            <h2>近期狀態</h2>
            <p>訂閱、知識、自動化和其他事件的簡短摘要。</p>
          </div>
          <div class="status-columns">
            <div>
              <div class="list-label">即將扣款</div>
              <div class="list-stack">
                ${upcomingCharges.length ? upcomingCharges.map(chargeRow).join("") : emptyState("近期沒有已知扣款。")}
              </div>
            </div>
            <div>
              <div class="list-label">活動</div>
              <div class="list-stack">
                ${recentActivity.length ? recentActivity.slice(0, 4).map(activityRow).join("") : emptyState("尚未累積活動紀錄。")}
              </div>
            </div>
          </div>
        </section>
      </section>

      <section class="content-layout">
        <section class="panel compact-panel">
          <div class="section-head">
            <h2>知識</h2>
            <p>最近捕捉的 work knowledge。</p>
          </div>
          <div class="list-stack">
            ${recentNotes.length ? recentNotes.map(noteRow).join("") : emptyState("尚未有近期知識筆記。")}
          </div>
        </section>

        <section class="panel compact-panel">
          <div class="section-head">
            <h2>自動化</h2>
            <p>最近自動化執行結果。</p>
          </div>
          <div class="list-stack">
            ${recentRuns.length ? recentRuns.map(automationRunRow).join("") : emptyState("尚未有近期自動化執行。")}
          </div>
        </section>
      </section>
    </main>
  `;
}

function buildPrimaryActions(data, pulse) {
  return [
    {
      title: "記錄今天學什麼",
      detail: "用 AI check-in 把自然語句整理成 learning session。",
      href: "/nightly",
      metric: `${pulse.total_minutes ?? 0} 分鐘`,
      tone: "learning",
    },
    {
      title: "看日文學習",
      detail: "查看 Anki、日文分鐘、困難卡片和今日脈絡。",
      href: "/japanese",
      metric: `${pulse.japanese_minutes ?? 0} 分鐘`,
      tone: "japanese",
    },
    {
      title: "管理訂閱",
      detail: "檢查每月扣款、缺少排程和即將付款項目。",
      href: "/life-admin/subscriptions",
      metric: `${data.subscriptions?.overview?.active_subscription_count ?? 0} 筆`,
      tone: "admin",
    },
    {
      title: "做週回顧",
      detail: "把學習、訂閱、自動化與知識收束成下週方向。",
      href: "/review/weekly",
      metric: "Review",
      tone: "review",
    },
  ];
}

function buildModules(data, pulse, subscriptionOverview) {
  return [
    {
      title: "Learning",
      href: "/nightly",
      detail: "記錄今天學了什麼，累積 Python、日文與 SRE 的真實學習史。",
      metric: `${pulse.total_minutes ?? 0} 分鐘`,
    },
    {
      title: "Japanese",
      href: "/japanese",
      detail: "看 Anki 複習、日文 session、難卡和當日狀態。",
      metric: `${pulse.japanese_minutes ?? 0} 分鐘`,
    },
    {
      title: "Life Admin",
      href: "/life-admin/subscriptions",
      detail: "管理訂閱、扣款日、狀態和每月成本。",
      metric: `${subscriptionOverview.active_subscription_count ?? 0} active`,
    },
    {
      title: "Automation",
      href: "/docs#/automations",
      detail: "檢查外部自動化、最近執行與需要留意的任務。",
      metric: `${data.automations?.needs_attention_count ?? 0} alerts`,
    },
    {
      title: "Knowledge",
      href: "/docs#/work-knowledge",
      detail: "整理工作中可複用的概念、指令和 follow-up。",
      metric: `${data.knowledge?.note_count ?? 0} notes`,
    },
    {
      title: "Weekly Review",
      href: "/review/weekly",
      detail: "把一週的訊號變成下週可以執行的方向。",
      metric: "weekly",
    },
  ];
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

function statBlock(label, value, detail) {
  return `
    <article class="stat-block">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
      <small>${escapeHtml(detail)}</small>
    </article>
  `;
}

function actionCard(item) {
  return `
    <a class="action-card tone-${escapeAttribute(item.tone)}" href="${escapeAttribute(item.href)}">
      <span class="card-kicker">${escapeHtml(item.metric)}</span>
      <strong>${escapeHtml(item.title)}</strong>
      <p>${escapeHtml(item.detail)}</p>
    </a>
  `;
}

function moduleCard(item) {
  return `
    <a class="module-card" href="${escapeAttribute(item.href)}">
      <div>
        <strong>${escapeHtml(item.title)}</strong>
        <p>${escapeHtml(item.detail)}</p>
      </div>
      <span>${escapeHtml(item.metric)}</span>
    </a>
  `;
}

function attentionRow(item) {
  return `
    <a class="list-row" href="${escapeAttribute(item.href || "/dashboard")}">
      <span class="severity severity-${escapeAttribute(item.severity)}">${escapeHtml(item.severity)}</span>
      <span>
        <strong>${escapeHtml(item.title)}</strong>
        <small>${escapeHtml(item.detail)}</small>
      </span>
    </a>
  `;
}

function sessionRow(session) {
  return `
    <article class="list-row">
      <span>
        <strong>${escapeHtml(localizeSubject(session.subject))}</strong>
        <small>${escapeHtml(session.summary || "沒有摘要")}</small>
      </span>
      <span class="row-side">${escapeHtml(`${session.duration_minutes} 分鐘`)}</span>
    </article>
  `;
}

function chargeRow(charge) {
  const dateLabel = charge.next_charge_date ? formatShortDate(charge.next_charge_date) : "未排程";
  return `
    <article class="list-row">
      <span>
        <strong>${escapeHtml(charge.name)}</strong>
        <small>${escapeHtml(`${charge.currency} ${Number(charge.amount).toFixed(2)}`)}</small>
      </span>
      <span class="row-side">${escapeHtml(dateLabel)}</span>
    </article>
  `;
}

function activityRow(item) {
  return `
    <a class="list-row" href="${escapeAttribute(item.href || "/dashboard")}">
      <span>
        <strong>${escapeHtml(item.title)}</strong>
        <small>${escapeHtml(item.detail)}</small>
      </span>
      <span class="row-side">${escapeHtml(formatDateTime(item.occurred_at))}</span>
    </a>
  `;
}

function noteRow(note) {
  return `
    <article class="list-row">
      <span>
        <strong>${escapeHtml(note.title)}</strong>
        <small>${escapeHtml(`${localizeCategory(note.category)}${note.follow_up ? "，有 follow-up" : ""}`)}</small>
      </span>
      <span class="row-side">${escapeHtml(formatDateTime(note.created_at))}</span>
    </article>
  `;
}

function automationRunRow(run) {
  return `
    <article class="list-row">
      <span>
        <strong>${escapeHtml(run.automation_name)}</strong>
        <small>${escapeHtml(run.summary || "沒有摘要")}</small>
      </span>
      <span class="row-side">${escapeHtml(run.status)}</span>
    </article>
  `;
}

function emptyState(text) {
  return `<div class="empty-state">${escapeHtml(text)}</div>`;
}

function localizeSubject(subject) {
  if (subject === "python") return "Python";
  if (subject === "japanese") return "日文";
  if (subject === "sre") return "SRE";
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
    return "未知";
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
