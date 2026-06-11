const root = document.getElementById("root");
const LOCALE = "zh-TW";

const fallbackData = {
  target_date: currentDateString(),
  period_start: currentDateString(),
  period_end: currentDateString(),
  headline: "Weekly review is still loading.",
  summary: "When live data is unavailable, this page keeps a readable shell so the shape stays visible.",
  keep_doing: ["Keep the review short and actually reusable."],
  needs_attention: ["Live review data is not available right now."],
  next_week_focus: ["Reconnect the API and then start tightening the review prompts."],
  learning: {
    total_minutes: 0,
    session_count: 0,
    python_minutes: 0,
    japanese_minutes: 0,
    sre_minutes: 0,
    active_days: 0,
    best_day: null,
    best_day_minutes: 0,
    recommendation: "Start with one real week of data and let the page stay honest about it.",
    recent_sessions: [],
  },
  subscriptions: {
    active_subscription_count: 0,
    missing_schedule_count: 0,
    upcoming_charge_count: 0,
    new_subscription_count: 0,
    updated_subscription_count: 0,
    upcoming_charges: [],
    recommendation: "Subscription insight gets much better once the schedule gaps are filled.",
  },
  automations: {
    run_count: 0,
    success_count: 0,
    partial_count: 0,
    failed_count: 0,
    skipped_count: 0,
    recent_failures: [],
    recommendation: "One healthy real-world automation is enough for a useful first weekly review.",
  },
  knowledge: {
    note_count: 0,
    follow_up_count: 0,
    categories: [],
    recent_notes: [],
    recommendation: "The knowledge layer becomes valuable once follow-up starts turning into re-usable references.",
  },
  timeline: [],
};

document.addEventListener("DOMContentLoaded", () => {
  void loadReview();
});

async function loadReview() {
  const params = new URLSearchParams(window.location.search);
  const targetDate = params.get("date") || currentDateString();
  const data = (await safeFetchJson(`/reviews/weekly?target_date=${encodeURIComponent(targetDate)}`)) ?? fallbackData;
  render(data, targetDate);
  bindDateInput();
}

function render(data, targetDate) {
  root.innerHTML = `
    <main class="shell">
      <header class="topbar">
        <div>
          <div class="brand-name">LifeQuest Weekly Review</div>
          <div class="brand-subtitle">首頁回答今天，週回顧回答方向。</div>
        </div>
        <nav class="nav">
          <a class="pill" href="/dashboard">回到首頁</a>
          <a class="pill" href="/japanese">學習切片</a>
          <a class="pill" href="/life-admin/subscriptions">生活管理</a>
        </nav>
      </header>

      <section class="hero">
        <div class="hero-top">
          <div>
            <p class="eyebrow">Weekly Reflection</p>
            <h1 class="hero-title">${escapeHtml(data.headline)}</h1>
            <p class="hero-copy">${escapeHtml(data.summary)}</p>
            <div class="hero-actions">
              <label class="date-input">
                <span>查看週結尾日期</span>
                <input id="review-date" type="date" value="${escapeAttribute(targetDate)}" />
              </label>
              <a class="button button-primary" href="/dashboard">打開 Daily Dashboard</a>
              <a class="button button-secondary" href="/docs">API</a>
            </div>
          </div>
          <aside class="hero-side">
            <div class="hero-note">${escapeHtml(dateRangeLabel(data.period_start, data.period_end))}</div>
            <div class="hero-note">${escapeHtml(data.learning.recommendation)}</div>
            <div class="hero-note">${escapeHtml(data.automations.recommendation)}</div>
          </aside>
        </div>
      </section>

      <section class="stat-grid">
        ${statCard("學習分鐘", String(data.learning.total_minutes))}
        ${statCard("活躍天數", String(data.learning.active_days))}
        ${statCard("自動化執行", String(data.automations.run_count))}
        ${statCard("知識筆記", String(data.knowledge.note_count))}
      </section>

      <section class="panel">
        <div class="section-head">
          <div>
            <h2 class="section-title">本週判讀</h2>
            <p class="section-subtitle">這一區故意用白話，不要讓 review 變成另一張難讀的報表。</p>
          </div>
        </div>
        <div class="triple-grid">
          ${listCard("Keep Doing", data.keep_doing)}
          ${listCard("Needs Attention", data.needs_attention)}
          ${listCard("Next Week Focus", data.next_week_focus)}
        </div>
      </section>

      <section class="panel">
        <div class="section-head">
          <div>
            <h2 class="section-title">模組摘要</h2>
            <p class="section-subtitle">先看各模組的週節奏，再決定下週要補哪一塊。</p>
          </div>
        </div>
        <div class="dual-grid">
          ${learningCard(data.learning)}
          ${subscriptionsCard(data.subscriptions)}
          ${automationsCard(data.automations)}
          ${knowledgeCard(data.knowledge)}
        </div>
      </section>

      <section class="panel">
        <div class="section-head">
          <div>
            <h2 class="section-title">時間軸</h2>
            <p class="section-subtitle">如果這裡開始變得有連續性，LifeQuest 就會越來越像活的系統。</p>
          </div>
        </div>
        <div class="list-stack">
          ${(data.timeline ?? []).length ? data.timeline.map((item) => timelineRow(item)).join("") : emptyState("這週還沒有 activity timeline 事件。")}
        </div>
        <p class="footer-note">第一版週回顧先專注在方向感，而不是一次變成完整績效報表。</p>
      </section>
    </main>
  `;
}

function bindDateInput() {
  const input = document.getElementById("review-date");
  if (!input) {
    return;
  }
  input.addEventListener("change", () => {
    const params = new URLSearchParams(window.location.search);
    params.set("date", input.value || currentDateString());
    window.location.search = params.toString();
  });
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

function statCard(label, value) {
  return `<article class="stat-card"><div class="stat-label">${escapeHtml(label)}</div><div class="stat-value">${escapeHtml(value)}</div></article>`;
}

function listCard(title, items) {
  return `
    <article class="list-card">
      <h3 class="card-title">${escapeHtml(title)}</h3>
      <div class="list-stack">
        ${items.length ? items.map((item) => `<div class="bullet-row">${escapeHtml(item)}</div>`).join("") : emptyState("目前沒有內容。")}
      </div>
    </article>
  `;
}

function learningCard(data) {
  return `
    <article class="list-card">
      <h3 class="card-title">學習</h3>
      <div class="list-stack">
        ${dataRow("總學習", `${data.total_minutes} 分鐘`)}
        ${dataRow("主線分布", `Python ${data.python_minutes} / 日文 ${data.japanese_minutes} / SRE ${data.sre_minutes ?? 0}`)}
        ${dataRow("最佳一天", data.best_day ? `${formatShortDate(data.best_day)} · ${data.best_day_minutes} 分鐘` : "尚無資料")}
        ${data.recent_sessions.length ? data.recent_sessions.map((session) => sessionRow(session)).join("") : emptyState("這週還沒有 learning sessions。")}
      </div>
    </article>
  `;
}

function subscriptionsCard(data) {
  return `
    <article class="list-card">
      <h3 class="card-title">生活管理</h3>
      <div class="list-stack">
        ${dataRow("使用中訂閱", `${data.active_subscription_count} 筆`)}
        ${dataRow("待補排程", `${data.missing_schedule_count} 筆`)}
        ${dataRow("本週變動", `新增 ${data.new_subscription_count} / 更新 ${data.updated_subscription_count}`)}
        ${data.upcoming_charges.length ? data.upcoming_charges.map((charge) => chargeRow(charge)).join("") : emptyState("這週 review 視窗內沒有近期扣款。")}
      </div>
    </article>
  `;
}

function automationsCard(data) {
  return `
    <article class="list-card">
      <h3 class="card-title">自動化</h3>
      <div class="list-stack">
        ${dataRow("執行總數", `${data.run_count} 次`)}
        ${dataRow("成功 / 部分 / 失敗", `${data.success_count} / ${data.partial_count} / ${data.failed_count}`)}
        ${data.recent_failures.length ? data.recent_failures.map((item) => `<div class="bullet-row">${escapeHtml(item)}</div>`).join("") : emptyState("這週沒有顯著失敗紀錄。")}
      </div>
    </article>
  `;
}

function knowledgeCard(data) {
  const categories = (data.categories ?? []).map((item) => `${item.category}: ${item.count}`).join(" / ");
  return `
    <article class="list-card">
      <h3 class="card-title">知識</h3>
      <div class="list-stack">
        ${dataRow("新增筆記", `${data.note_count} 則`)}
        ${dataRow("待 follow-up", `${data.follow_up_count} 則`)}
        ${dataRow("分類分布", categories || "尚無資料")}
        ${data.recent_notes.length ? data.recent_notes.map((note) => noteRow(note)).join("") : emptyState("這週還沒有新增知識筆記。")}
      </div>
    </article>
  `;
}

function timelineRow(item) {
  return `
    <a class="timeline-row" href="${escapeAttribute(item.href || "/dashboard")}">
      <div>
        <div class="item-title">${escapeHtml(item.title)}</div>
        <div class="item-meta">${escapeHtml(item.detail)}</div>
      </div>
      <div class="item-side">
        <span class="tone-badge tone-${escapeAttribute(item.tone || "neutral")}">${escapeHtml(item.tone || "neutral")}</span>
        <div class="item-meta">${escapeHtml(formatDateTime(item.occurred_at))}</div>
      </div>
    </a>
  `;
}

function sessionRow(session) {
  return dataRow(localizeSubject(session.subject), `${session.duration_minutes} 分鐘 · ${session.summary}`);
}

function chargeRow(charge) {
  return dataRow(charge.name, `${charge.currency} ${Number(charge.amount).toFixed(2)} · ${formatShortDate(charge.next_charge_date)}`);
}

function noteRow(note) {
  return dataRow(note.title, `${note.category}${note.follow_up ? " · 有 follow-up" : ""}`);
}

function dataRow(label, value) {
  return `
    <div class="data-row">
      <div class="item-title">${escapeHtml(label)}</div>
      <div class="item-side">
        <div class="item-meta">${escapeHtml(value)}</div>
      </div>
    </div>
  `;
}

function emptyState(text) {
  return `<div class="empty-state">${escapeHtml(text)}</div>`;
}

function localizeSubject(subject) {
  if (subject === "python") {
    return "Python";
  }
  if (subject === "japanese") {
    return "日文";
  }
  if (subject === "sre") {
    return "SRE";
  }
  return subject || "學習";
}

function dateRangeLabel(start, end) {
  return `Review window: ${formatShortDate(start)} to ${formatShortDate(end)}`;
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
