const root = document.getElementById("root");
const LOCALE = "zh-TW";

const fallbackData = {
  status: "prototype",
  date: currentDateString(),
  pulse: {
    total_minutes: 75,
    python_minutes: 45,
    japanese_minutes: 30,
    focus_score: 72,
    tomorrow_priority: "保護一段 Python 練習，再完成一輪日文 Anki。",
  },
  subscriptions: {
    active_subscription_count: 3,
    totals_by_currency: { USD: 20, JPY: 1499, TWD: 75 },
    upcoming_charges: [
      { name: "範例訂閱", currency: "TWD", amount: 75, next_charge_date: "2026-05-28" },
      { name: "ChatGPT Plus", currency: "USD", amount: 20, next_charge_date: null },
      { name: "office365", currency: "JPY", amount: 1499, next_charge_date: null },
    ],
  },
  warnings: [
    "這個首頁目前還是產品方向原型；有些卡片會先用備援資料，等每個後端模組穩定後再完全接上。",
  ],
};

document.addEventListener("DOMContentLoaded", () => {
  void loadDashboard();
});

async function loadDashboard() {
  const [health, pulse, subscriptions] = await Promise.all([
    safeFetchJson("/health"),
    safeFetchJson("/learning/pulse/today"),
    safeFetchJson("/subscriptions/overview/monthly?days_ahead=35"),
  ]);

  const data = {
    ...fallbackData,
    status: health?.status === "ok" ? "live" : "prototype",
    pulse: mergePulse(pulse),
    subscriptions: mergeSubscriptions(subscriptions),
  };
  render(data);
}

function render(data) {
  const totals = Object.entries(data.subscriptions.totals_by_currency);
  const upcomingCharges = data.subscriptions.upcoming_charges.slice(0, 4);

  root.innerHTML = `
    <main class="shell">
      <header class="topbar" data-reveal>
        <div class="brand">
          <span class="brand-mark" aria-hidden="true"></span>
          <div>
            <div class="brand-name">LifeQuest</div>
            <div class="brand-subtitle">學習、生活管理、知識與自動化的個人控制中心。</div>
          </div>
        </div>
        <nav class="nav-pills">
          <a class="pill" href="#modules">模組</a>
          <a class="pill" href="#today">今天</a>
          <a class="pill" href="#money">生活管理</a>
          <a class="pill" href="#vision">路線圖</a>
        </nav>
      </header>

      <section class="hero" data-reveal data-delay="1">
        <div>
          <p class="eyebrow">產品方向</p>
          <h1 class="hero-title">一個你真的會想打開的生活作業系統。</h1>
          <p class="hero-text">
            LifeQuest 最適合保持冷靜又有主見：後端負責保存真實訊號，前端負責幫你快速判斷今天該注意什麼。
          </p>
          <div class="hero-actions">
            <a class="button button-primary" href="/docs">開啟 API 文件</a>
            <a class="button button-secondary" href="/life-admin/subscriptions">訂閱管理</a>
            <a class="button button-secondary" href="/japanese">日文學習</a>
          </div>
        </div>
        <aside class="hero-side">
          <section class="glass-card">
            <div class="status-line">
              <div>
                <div class="mini-label">儀表板狀態</div>
                <strong>${data.status === "live" ? "已連上後端" : "原型模式"}</strong>
              </div>
              <span class="status-chip">${data.status === "live" ? "上線" : "備援"}</span>
            </div>
            <div class="prototype-banner">${escapeHtml(data.warnings[0])}</div>
          </section>
          <section class="hero-mini-grid">
            ${miniCard("今天", formatShortDate(data.date))}
            ${miniCard("專注", `${data.pulse.focus_score}`)}
            ${miniCard("訂閱", `${data.subscriptions.active_subscription_count}`)}
            ${miniCard("模組", "5")}
          </section>
        </aside>
      </section>

      <section class="content-grid">
        <div class="metrics-grid" data-reveal data-delay="1">
          ${metricCard("學習脈搏", `${data.pulse.total_minutes} 分鐘`, "今天記錄到的 Python 與日文學習時間。", "今天")}
          ${metricCard("Python", `${data.pulse.python_minutes} 分鐘`, "實作、腳本與自動化練習時間。", "建造")}
          ${metricCard("日文", `${data.pulse.japanese_minutes} 分鐘`, "Anki、閱讀、聽力或其他日文練習。", "複習")}
          ${metricCard("生活管理", `${totals.length} 種幣別`, "把固定支出集中在同一個地方看。", "掌控")}
        </div>

        <section class="panel" id="modules" data-reveal data-delay="2">
          <div class="section-head">
            <div>
              <h2 class="section-title">核心模組</h2>
              <p class="section-subtitle">這個產品會靠幾個清楚的切片長大，而不是一次變成什麼都做的巨大應用。</p>
            </div>
          </div>
          <div class="module-grid">
            ${moduleCard("學習", "學習紀錄、Anki、GitHub 活動、進度摘要與回顧循環。", "讓動能看得見。", "tone-learning")}
            ${moduleCard("生活管理", "訂閱、固定支出，以及那些很小但不該忘記的生活訊號。", "減少腦內雜訊。", "tone-admin")}
            ${moduleCard("知識", "工作筆記、個人參考資料，以及未來的收件匣與回顧流程。", "讓學到的東西能重複使用。", "tone-knowledge")}
            ${moduleCard("自動化", "既有腳本、執行歷史與操作可觀測性。", "先觀察，再重寫。", "tone-automation")}
            ${moduleCard("週回顧", "把紀錄轉成選擇的人類友善摘要頁。", "把資料變成方向。", "tone-review")}
          </div>
        </section>

        <div class="two-up" id="today">
          <section class="panel" data-reveal data-delay="2">
            <div class="section-head">
              <div>
                <h2 class="section-title">今日流程</h2>
                <p class="section-subtitle">首頁應該很快回答一件事：今天什麼最值得注意？</p>
              </div>
            </div>
            <div class="checklist">
              ${checkItem("保護學習區塊", `Python ${data.pulse.python_minutes} 分鐘、日文 ${data.pulse.japanese_minutes} 分鐘，打開就看得到。`)}
              ${checkItem("檢查明日優先事項", localizePriority(data.pulse.tomorrow_priority, data.pulse))}
              ${checkItem("掃過固定支出", upcomingCharges.length ? `接下來的檢視區間內有 ${upcomingCharges.length} 筆訂閱項目。` : "有些訂閱還缺扣款日期。") }
              ${checkItem("完成閉環", "週回顧之後應該能把學習、生活管理、自動化與知識整理接在一起。")}
            </div>
          </section>

          <section class="panel" data-reveal data-delay="3">
            <div class="section-head">
              <div>
                <h2 class="section-title">前端承諾</h2>
                <p class="section-subtitle">這個 UI 應該像控制中心，而不是一張被硬塞按鈕的試算表。</p>
              </div>
            </div>
            <div class="feed-list">
              ${feedItem("每日首頁", "一個畫面看學習脈搏、生活管理與操作訊號。")}
              ${feedItem("模組頁", "為學習、生活管理、知識與自動化保留各自的專用視圖。")}
              ${feedItem("回顧儀式", "未來加一個更安靜的週回顧頁，幫你決定保留、停止或改善什麼。")}
            </div>
          </section>
        </div>

        <div class="two-up" id="money">
          <section class="panel" data-reveal data-delay="2">
            <div class="section-head">
              <div>
                <h2 class="section-title">生活管理快照</h2>
                <p class="section-subtitle">固定支出很容易忘記，但忘記通常很貴，所以它們值得被放在這裡。</p>
              </div>
            </div>
            <div class="currency-stack">
              ${totals.map(([currency, total]) => currencyRow(currency, total)).join("")}
            </div>
          </section>

          <section class="panel" data-reveal data-delay="3">
            <div class="section-head">
              <div>
                <h2 class="section-title">近期扣款</h2>
                <p class="section-subtitle">已知日期要很清楚；未知日期則要讓人一眼知道還沒整理完。</p>
              </div>
            </div>
            <div class="charge-list">
              ${upcomingCharges.map((charge) => chargeRow(charge)).join("")}
            </div>
          </section>
        </div>

        <section class="panel" id="vision" data-reveal data-delay="3">
          <div class="section-head">
            <div>
              <h2 class="section-title">產品路線圖</h2>
              <p class="section-subtitle">比較穩的路線是：先讓後端可靠，再做一個值得打開的儀表板，最後補上更豐富的回顧流程。</p>
            </div>
          </div>
          <div class="story-grid">
            ${timelineCard("第 1 階段", "可靠的後端切片", "每個領域先把捕捉、儲存、列表與摘要 API 做穩。")}
            ${timelineCard("第 2 階段", "值得打開的首頁", "首頁要用白話解釋今天的學習、金錢、知識與自動化狀態。")}
            ${timelineCard("第 3 階段", "週回顧", "加入更安靜的頁面，幫你決定這週要保留、停止或改善什麼。")}
            ${timelineCard("第 4 階段", "可選的遊戲層", "只有在產品本身已經有用之後，才加入任務或 XP。")}
          </div>
        </section>

        <p class="footer-note" data-reveal data-delay="3">
          這個首頁目前故意先作為產品方向原型，讓我們能早點看到形狀，再用你的真實使用慢慢長大。
        </p>
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

function mergePulse(pulse) {
  if (!pulse) {
    return fallbackData.pulse;
  }
  return {
    total_minutes: pulse.total_minutes ?? fallbackData.pulse.total_minutes,
    python_minutes: pulse.python_minutes ?? 0,
    japanese_minutes: pulse.japanese_minutes ?? 0,
    focus_score: pulse.focus_score ?? fallbackData.pulse.focus_score,
    tomorrow_priority: pulse.tomorrow_priority ?? fallbackData.pulse.tomorrow_priority,
  };
}

function mergeSubscriptions(subscriptions) {
  if (!subscriptions) {
    return fallbackData.subscriptions;
  }
  return {
    active_subscription_count: subscriptions.active_subscription_count ?? fallbackData.subscriptions.active_subscription_count,
    totals_by_currency: subscriptions.totals_by_currency ?? fallbackData.subscriptions.totals_by_currency,
    upcoming_charges: Array.isArray(subscriptions.upcoming_charges)
      ? subscriptions.upcoming_charges
      : fallbackData.subscriptions.upcoming_charges,
  };
}

function miniCard(label, value) {
  return `<div class="mini-card"><div class="mini-label">${escapeHtml(label)}</div><div class="mini-value">${escapeHtml(String(value))}</div></div>`;
}

function metricCard(label, value, text, trend) {
  return `<article class="metric-card"><div class="metric-top"><div class="metric-label">${escapeHtml(label)}</div><div class="metric-trend">${escapeHtml(trend)}</div></div><div class="metric-value">${escapeHtml(value)}</div><div class="metric-text">${escapeHtml(text)}</div></article>`;
}

function moduleCard(title, text, footer, toneClass) {
  return `<article class="module-card ${toneClass}"><div class="module-kicker">核心切片</div><h3 class="module-title">${escapeHtml(title)}</h3><p class="module-text">${escapeHtml(text)}</p><div class="module-footer">${escapeHtml(footer)}</div></article>`;
}

function checkItem(title, meta) {
  return `<article class="check-item"><div class="item-title">${escapeHtml(title)}</div><div class="item-meta">${escapeHtml(meta)}</div></article>`;
}

function feedItem(title, meta) {
  return `<article class="feed-item"><div class="item-title">${escapeHtml(title)}</div><div class="item-meta">${escapeHtml(meta)}</div></article>`;
}

function currencyRow(currency, total) {
  return `<div class="currency-row"><span class="currency-label">${escapeHtml(currency)}</span><span class="currency-value">${escapeHtml(`${currency} ${Number(total).toFixed(2)}`)}</span></div>`;
}

function chargeRow(charge) {
  const dateLabel = charge.next_charge_date ? formatShortDate(charge.next_charge_date) : "缺少日期";
  return `<div class="charge-row"><div><div class="charge-name">${escapeHtml(charge.name)}</div><div class="item-meta">${escapeHtml(`${charge.currency} ${Number(charge.amount).toFixed(2)}`)}</div></div><span class="charge-date">${escapeHtml(dateLabel)}</span></div>`;
}

function timelineCard(step, title, copy) {
  return `<article class="timeline-note"><div class="timeline-step">${escapeHtml(step)}</div><div class="timeline-title">${escapeHtml(title)}</div><div class="timeline-copy">${escapeHtml(copy)}</div></article>`;
}

function localizePriority(priority, pulse) {
  if (priority && containsCjk(priority)) {
    return priority;
  }
  if (!pulse.python_minutes && !pulse.japanese_minutes) {
    return "明天先排一段短學習區塊，把節奏接回來。";
  }
  return "明天先保護一段 Python 自動化練習，再完成一輪日文 Anki。";
}

function currentDateString() {
  const now = new Date();
  const offset = now.getTimezoneOffset();
  return new Date(now.getTime() - offset * 60000).toISOString().slice(0, 10);
}

function formatShortDate(value) {
  return new Date(`${value}T00:00:00`).toLocaleDateString(LOCALE, { month: "short", day: "numeric" });
}

function containsCjk(value) {
  return /[\u3400-\u9fff]/.test(String(value));
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
