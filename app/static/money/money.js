const root = document.getElementById("root");

let currentOverview = null;
let currentReview = null;
let message = "";
let messageIsError = false;

document.addEventListener("DOMContentLoaded", () => {
  void loadMoney();
});

root.addEventListener("submit", (event) => {
  const form = event.target.closest("[data-form]");
  if (!form) {
    return;
  }
  event.preventDefault();
  void handleFormSubmit(form);
});

root.addEventListener("click", (event) => {
  const button = event.target.closest("[data-action]");
  if (!button) {
    return;
  }
  void handleAction(button);
});

async function loadMoney() {
  currentOverview = await safeFetchJson("/money/overview");
  render();
}

function render() {
  const overview = currentOverview ?? {
    goals: [],
    loan_scenarios: [],
    leverage_plans: [],
    attention_items: [],
    total_protected_goal_remaining: {},
    latest_weekly_checkin: null,
  };
  const protectedTotal = Object.entries(overview.total_protected_goal_remaining ?? {})
    .map(([currency, amount]) => `${currency} ${formatMoney(amount)}`)
    .join(", ") || "TWD 0";
  const latest = overview.latest_weekly_checkin;
  const draftCount = (overview.leverage_plans ?? []).filter((plan) => plan.status === "draft").length;

  root.innerHTML = `
    <main class="shell">
      <header class="topbar">
        <a class="brand" href="/dashboard">
          <span class="brand-mark">LQ</span>
          <span>
            <strong>LifeQuest</strong>
            <small>Money Quest</small>
          </span>
        </a>
        <nav class="topnav" aria-label="Money navigation">
          <a href="/dashboard">Dashboard</a>
          <a href="/life-admin/subscriptions">Subscriptions</a>
          <a href="/review/weekly">Weekly Review</a>
        </nav>
      </header>

      <section class="hero">
        <div>
          <p class="eyebrow">Finance guardrails, not autopilot</p>
          <h1>財務作戰室</h1>
          <p>
            這裡不是券商，也不是投資建議機器。它的任務是幫你保護植髮基金、緊急預備金和現金流，
            再把槓桿 ETF 與信貸計畫留在可檢查、可反悔、可記錄的地方。
          </p>
          <div class="hero-actions">
            <a class="button button-primary" href="#weekly-checkin">做本週金錢檢查</a>
            <a class="button button-secondary" href="#leverage-plan">建立槓桿策略草案</a>
            <a class="button button-secondary" href="#review-plan">檢核策略紅燈</a>
          </div>
        </div>
        <aside class="metric-grid" aria-label="Money metrics">
          ${metricCard("Protected goals", protectedTotal, "先保護生活主線，再談槓桿。")}
          ${metricCard("Draft plans", String(draftCount), "draft 代表還不能當成已審核策略。")}
          ${metricCard("Free cashflow", latest ? `${latest.currency} ${formatMoney(latest.free_cashflow)}` : "No check-in", latest ? `week ${latest.week_start_date}` : "先記錄一週現金流")}
          ${metricCard("Debt ratio", latest?.debt_service_ratio != null ? formatPercent(latest.debt_service_ratio) : "Unknown", "信貸月付壓力需要被看見。")}
        </aside>
      </section>

      ${message ? `<div class="message ${messageIsError ? "message-error" : ""}">${escapeHtml(message)}</div>` : ""}

      <section class="content-grid">
        <section class="panel">
          <div class="panel-head">
            <h2>保護目標</h2>
            <p>植髮基金、緊急預備金、重要生活目標，都應該在策略之前先被看見。</p>
          </div>
          <div class="list-stack">
            ${(overview.goals ?? []).length ? overview.goals.map(goalRow).join("") : emptyState("還沒有 money goal。可以先建立「植髮基金」或「緊急預備金」。")}
          </div>
        </section>

        <section class="panel">
          <div class="panel-head">
            <h2>注意事項</h2>
            <p>LifeQuest 只會提醒你哪裡需要慢下來，不會鼓勵你加大風險。</p>
          </div>
          <div class="list-stack">
            ${(overview.attention_items ?? []).length ? overview.attention_items.map(attentionRow).join("") : emptyState("目前沒有金錢紅燈。保持這種清醒感，很可以。")}
          </div>
        </section>
      </section>

      <section class="content-grid">
        <section class="panel">
          <div class="panel-head">
            <h2>槓桿 ETF 策略草案</h2>
            <p>策略只會從 draft 變成 reviewed，不會變成「建議買進」。這個差別很重要。</p>
          </div>
          <div class="list-stack">
            ${(overview.leverage_plans ?? []).length ? overview.leverage_plans.map(planRow).join("") : emptyState("還沒有槓桿策略草案。")}
          </div>
        </section>

        <section class="panel" id="review-plan">
          <div class="panel-head">
            <h2>策略紅燈檢核</h2>
            <p>輸入 plan key 檢查現金、信貸、保護目標與壓力測試。</p>
          </div>
          ${reviewForm()}
          ${currentReview ? reviewPanel(currentReview) : ""}
        </section>
      </section>

      <section class="form-grid">
        ${goalForm()}
        ${contributionForm(overview.goals ?? [])}
        ${weeklyCheckinForm(latest)}
        ${loanForm()}
        ${leveragePlanForm(overview.goals ?? [], overview.loan_scenarios ?? [])}
        ${decisionLogForm(overview.leverage_plans ?? [])}
      </section>
    </main>
  `;
}

function goalForm() {
  return `
    <form class="form-card" data-form="goal">
      <h3>新增保護目標</h3>
      <div class="field-grid">
        <label>名稱<input name="name" required placeholder="植髮基金" /></label>
        <label>key<input name="key" placeholder="hair-transplant-fund" /></label>
        <label>類別
          <select name="category">
            <option value="hair_transplant">hair_transplant</option>
            <option value="emergency_fund">emergency_fund</option>
            <option value="investment">investment</option>
            <option value="lifestyle">lifestyle</option>
            <option value="other">other</option>
          </select>
        </label>
        <label>目標金額<input name="target_amount" required type="number" min="1" step="1" value="150000" /></label>
        <label>目前金額<input name="current_amount" type="number" min="0" step="1" value="0" /></label>
        <label>每月目標投入<input name="monthly_contribution_target" type="number" min="0" step="1" value="5000" /></label>
        <label>幣別<input name="currency" value="TWD" /></label>
        <label>目標日期<input name="target_date" type="date" /></label>
        <label class="field-wide">備註<textarea name="notes" placeholder="這筆錢被保護，不能被衝動投資吃掉。"></textarea></label>
        <label><span>保護這個目標</span><input name="protected" type="checkbox" checked /></label>
      </div>
      <button class="button button-primary" type="submit">建立目標</button>
    </form>
  `;
}

function contributionForm(goals) {
  return `
    <form class="form-card" data-form="contribution">
      <h3>紀錄目標投入</h3>
      <div class="field-grid">
        <label>目標
          <select name="goal_ref" required>
            ${goals.map((goal) => `<option value="${escapeAttribute(goal.key)}">${escapeHtml(goal.name)}</option>`).join("")}
          </select>
        </label>
        <label>金額<input name="amount" required type="number" min="1" step="1" value="1000" /></label>
        <label>幣別<input name="currency" value="TWD" /></label>
        <label>日期<input name="occurred_on" type="date" value="${todayString()}" /></label>
        <label class="field-wide">備註<textarea name="note" placeholder="例如：本月先存下來，讓未來的自己比較穩。"></textarea></label>
      </div>
      <button class="button button-primary" type="submit" ${goals.length ? "" : "disabled"}>紀錄投入</button>
    </form>
  `;
}

function weeklyCheckinForm(latest) {
  return `
    <form class="form-card" id="weekly-checkin" data-form="weekly-checkin">
      <h3>本週金錢檢查</h3>
      <div class="field-grid">
        <label>週起始日<input name="week_start_date" required type="date" value="${latest?.week_start_date ?? currentWeekStart()}" /></label>
        <label>月收入<input name="monthly_income" type="number" min="0" step="1" value="${latest?.monthly_income ?? 0}" /></label>
        <label>必要支出<input name="necessary_expenses" type="number" min="0" step="1" value="${latest?.necessary_expenses ?? 0}" /></label>
        <label>彈性支出<input name="flexible_expenses" type="number" min="0" step="1" value="${latest?.flexible_expenses ?? 0}" /></label>
        <label>計畫儲蓄<input name="planned_savings" type="number" min="0" step="1" value="${latest?.planned_savings ?? 0}" /></label>
        <label>實際儲蓄<input name="actual_savings" type="number" min="0" step="1" value="${latest?.actual_savings ?? 0}" /></label>
        <label>投資投入<input name="investment_contribution" type="number" min="0" step="1" value="${latest?.investment_contribution ?? 0}" /></label>
        <label>既有債務月付<input name="debt_payment" type="number" min="0" step="1" value="${latest?.debt_payment ?? 0}" /></label>
        <label>幣別<input name="currency" value="${latest?.currency ?? "TWD"}" /></label>
        <label class="field-wide">備註<textarea name="notes" placeholder="本週花費壓力、情緒、需要保護的東西。">${escapeHtml(latest?.notes ?? "")}</textarea></label>
      </div>
      <button class="button button-primary" type="submit">儲存週檢查</button>
    </form>
  `;
}

function loanForm() {
  return `
    <form class="form-card" data-form="loan">
      <h3>建立信貸情境</h3>
      <p class="helper">這只是壓力測試用，不代表建議借款。</p>
      <div class="field-grid">
        <label>名稱<input name="name" required placeholder="信貸投入股市情境" /></label>
        <label>key<input name="key" placeholder="stock-loan-scenario" /></label>
        <label>本金<input name="principal" required type="number" min="1" step="1" value="500000" /></label>
        <label>年利率 %<input name="annual_interest_rate" required type="number" min="0" max="100" step="0.01" value="6" /></label>
        <label>期數（月）<input name="term_months" required type="number" min="1" max="480" step="1" value="84" /></label>
        <label>月付金（可空白自算）<input name="monthly_payment" type="number" min="1" step="1" /></label>
        <label>開始日期<input name="start_date" type="date" /></label>
        <label class="field-wide">目的<textarea name="purpose" placeholder="例如：只作為策略壓力測試，不直接執行。"></textarea></label>
      </div>
      <button class="button button-primary" type="submit">建立信貸情境</button>
    </form>
  `;
}

function leveragePlanForm(goals, loans) {
  return `
    <form class="form-card" id="leverage-plan" data-form="leverage-plan">
      <h3>建立槓桿 ETF 策略草案</h3>
      <div class="field-grid">
        <label>名稱<input name="name" required value="台股正2 50/50 檢核" /></label>
        <label>key<input name="key" placeholder="tw-2x-50-50" /></label>
        <label>市場<select name="market"><option value="tw">tw</option><option value="us">us</option></select></label>
        <label>槓桿資產<input name="leveraged_asset_label" value="台股正2" /></label>
        <label>正2比重 %<input name="leveraged_position_pct" type="number" min="0" max="100" step="1" value="50" /></label>
        <label>現金比重 %<input name="cash_reserve_pct" type="number" min="0" max="100" step="1" value="50" /></label>
        <label>最低現金 %<input name="minimum_cash_reserve_pct" type="number" min="0" max="100" step="1" value="30" /></label>
        <label>最大策略回撤 %<input name="max_strategy_drawdown_pct" type="number" min="0" max="100" step="1" value="35" /></label>
        <label>緊急金月數<input name="emergency_fund_months_required" type="number" min="0" max="60" step="1" value="6" /></label>
        <label>信貸月付上限 %<input name="max_debt_service_ratio" type="number" min="0" max="100" step="1" value="20" /></label>
        <label>信貸情境
          <select name="loan_scenario_key">
            <option value="">不使用信貸</option>
            ${loans.map((loan) => `<option value="${escapeAttribute(loan.key)}">${escapeHtml(loan.name)}</option>`).join("")}
          </select>
        </label>
        <label>再平衡<select name="rebalance_frequency"><option value="quarterly">quarterly</option><option value="monthly">monthly</option><option value="semiannual">semiannual</option><option value="annual">annual</option></select></label>
        <label class="field-wide">保護目標 keys<input name="protected_goal_keys" value="${goals.filter((goal) => goal.protected).map((goal) => goal.key).join(",")}" /></label>
        <label class="field-wide">備註<textarea name="notes" placeholder="先寫下為什麼要做、什麼情況不能做。"></textarea></label>
      </div>
      <button class="button button-primary" type="submit">建立策略草案</button>
    </form>
  `;
}

function reviewForm() {
  const firstPlan = currentOverview?.leverage_plans?.[0]?.key ?? "";
  return `
    <form class="form-card" data-form="review">
      <div class="field-grid">
        <label>plan key<input name="plan_ref" required value="${escapeAttribute(firstPlan)}" /></label>
      </div>
      <button class="button button-primary" type="submit">檢核策略</button>
      ${currentReview?.can_mark_reviewed ? `<button class="button button-secondary" type="button" data-action="mark-reviewed" data-plan-ref="${escapeAttribute(currentReview.plan.key)}">標記為 reviewed</button>` : ""}
    </form>
  `;
}

function decisionLogForm(plans) {
  return `
    <form class="form-card" data-form="decision-log">
      <h3>紀錄策略決策</h3>
      <div class="field-grid">
        <label>策略
          <select name="plan_ref" required>
            ${plans.map((plan) => `<option value="${escapeAttribute(plan.key)}">${escapeHtml(plan.name)}</option>`).join("")}
          </select>
        </label>
        <label>日期<input name="decision_date" type="date" value="${todayString()}" /></label>
        <label class="field-wide">決策<input name="decision" required placeholder="例如：本週不執行，只完成檢核。" /></label>
        <label class="field-wide">理由<textarea name="rationale" required placeholder="把理由寫下來，未來的你會謝謝現在的你。"></textarea></label>
        <label class="field-wide">情緒<textarea name="emotion" placeholder="例如：有點 FOMO，但還能冷靜。"></textarea></label>
      </div>
      <button class="button button-primary" type="submit" ${plans.length ? "" : "disabled"}>寫入決策日誌</button>
    </form>
  `;
}

function reviewPanel(review) {
  return `
    <div class="review-grid">
      <div class="message ${review.failed_count ? "message-error" : ""}">
        ${escapeHtml(review.summary)}
      </div>
      <div class="list-stack">
        ${review.checks.map(riskRow).join("")}
      </div>
      <div class="panel-head">
        <h3>壓力測試</h3>
      </div>
      <div class="list-stack">
        ${review.stress_scenarios.map(stressRow).join("")}
      </div>
    </div>
  `;
}

async function handleFormSubmit(form) {
  const formName = form.dataset.form;
  const data = Object.fromEntries(new FormData(form).entries());
  try {
    if (formName === "goal") {
      await postJson("/money/goals", {
        key: optionalString(data.key),
        name: data.name,
        category: data.category,
        target_amount: numberValue(data.target_amount),
        current_amount: numberValue(data.current_amount),
        currency: data.currency,
        monthly_contribution_target: numberValue(data.monthly_contribution_target),
        target_date: optionalString(data.target_date),
        protected: Boolean(data.protected),
        notes: optionalString(data.notes),
      });
      setMessage("目標已建立。主線資源先被保護起來。");
    } else if (formName === "contribution") {
      await postJson(`/money/goals/${encodeURIComponent(data.goal_ref)}/contributions`, {
        amount: numberValue(data.amount),
        currency: data.currency,
        occurred_on: data.occurred_on,
        note: optionalString(data.note),
      });
      setMessage("投入已紀錄。小步也算數。");
    } else if (formName === "weekly-checkin") {
      await postJson("/money/checkins/weekly", {
        week_start_date: data.week_start_date,
        monthly_income: numberValue(data.monthly_income),
        necessary_expenses: numberValue(data.necessary_expenses),
        flexible_expenses: numberValue(data.flexible_expenses),
        planned_savings: numberValue(data.planned_savings),
        actual_savings: numberValue(data.actual_savings),
        investment_contribution: numberValue(data.investment_contribution),
        debt_payment: numberValue(data.debt_payment),
        currency: data.currency,
        notes: optionalString(data.notes),
      });
      setMessage("週檢查已儲存。這就是財務版的存檔點。");
    } else if (formName === "loan") {
      await postJson("/money/loan-scenarios", {
        key: optionalString(data.key),
        name: data.name,
        principal: numberValue(data.principal),
        annual_interest_rate: numberValue(data.annual_interest_rate),
        term_months: numberValue(data.term_months),
        monthly_payment: optionalNumber(data.monthly_payment),
        start_date: optionalString(data.start_date),
        purpose: optionalString(data.purpose),
      });
      setMessage("信貸情境已建立。它現在只是壓力測試素材，不是行動指令。");
    } else if (formName === "leverage-plan") {
      await postJson("/money/leverage-plans", {
        key: optionalString(data.key),
        name: data.name,
        market: data.market,
        leveraged_asset_label: data.leveraged_asset_label,
        leveraged_position_pct: numberValue(data.leveraged_position_pct),
        cash_reserve_pct: numberValue(data.cash_reserve_pct),
        minimum_cash_reserve_pct: numberValue(data.minimum_cash_reserve_pct),
        max_strategy_drawdown_pct: numberValue(data.max_strategy_drawdown_pct),
        emergency_fund_months_required: numberValue(data.emergency_fund_months_required),
        max_debt_service_ratio: numberValue(data.max_debt_service_ratio) / 100,
        loan_scenario_key: optionalString(data.loan_scenario_key),
        rebalance_frequency: data.rebalance_frequency,
        protected_goal_keys: splitKeys(data.protected_goal_keys),
        notes: optionalString(data.notes),
      });
      setMessage("槓桿策略草案已建立。它會保持 draft，直到紅燈檢核通過。");
    } else if (formName === "review") {
      currentReview = await safeFetchJson(`/money/leverage-plans/${encodeURIComponent(data.plan_ref)}/review`);
      if (!currentReview) {
        throw new Error("Review request failed.");
      }
      setMessage("策略檢核完成。請先看紅燈，不要急著行動。");
    } else if (formName === "decision-log") {
      await postJson(`/money/leverage-plans/${encodeURIComponent(data.plan_ref)}/decision-log`, {
        decision_date: data.decision_date,
        decision: data.decision,
        rationale: data.rationale,
        emotion: optionalString(data.emotion),
      });
      setMessage("決策日誌已寫入。這是防止 FOMO 的黑盒子。");
    }
    await loadMoney();
  } catch (error) {
    setMessage(error.message || "Action failed.", true);
    render();
  }
}

async function handleAction(button) {
  if (button.dataset.action !== "mark-reviewed") {
    return;
  }
  try {
    const planRef = button.dataset.planRef;
    currentReview = await postJson(`/money/leverage-plans/${encodeURIComponent(planRef)}/mark-reviewed`, {});
    setMessage("策略已標記為 reviewed。這只代表檢核通過，不代表建議投資。");
    await loadMoney();
  } catch (error) {
    setMessage(error.message || "Action failed.", true);
    render();
  }
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

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || `Request failed: ${response.status}`);
  }
  return await response.json();
}

function setMessage(text, isError = false) {
  message = text;
  messageIsError = isError;
}

function goalRow(goal) {
  return `
    <article class="list-row">
      <span>
        <strong>${escapeHtml(goal.name)}</strong>
        <small>${escapeHtml(goal.key)} · ${escapeHtml(goal.category)} · ${formatMoney(goal.progress_pct)}%</small>
        <small>${escapeHtml(goal.currency)} ${formatMoney(goal.current_amount)} / ${formatMoney(goal.target_amount)}，還差 ${formatMoney(goal.remaining_amount)}</small>
      </span>
      <span class="pill pill-${escapeAttribute(goal.status)}">${escapeHtml(goal.status)}</span>
    </article>
  `;
}

function attentionRow(item) {
  return `
    <article class="list-row">
      <span>
        <strong>${escapeHtml(item.title)}</strong>
        <small>${escapeHtml(item.detail)}</small>
      </span>
      <span class="pill pill-${escapeAttribute(item.severity)}">${escapeHtml(item.severity)}</span>
    </article>
  `;
}

function planRow(plan) {
  const loan = plan.loan_scenario ? ` · loan: ${plan.loan_scenario.name}` : "";
  return `
    <article class="list-row">
      <span>
        <strong>${escapeHtml(plan.name)}</strong>
        <small>${escapeHtml(plan.key)} · ${escapeHtml(plan.market)} · ${escapeHtml(plan.rebalance_frequency)}${escapeHtml(loan)}</small>
        <small>${formatMoney(plan.leveraged_position_pct)}% ${escapeHtml(plan.leveraged_asset_label)} / ${formatMoney(plan.cash_reserve_pct)}% cash</small>
      </span>
      <span class="pill pill-${escapeAttribute(plan.status)}">${escapeHtml(plan.status)}</span>
    </article>
  `;
}

function riskRow(check) {
  return `
    <article class="risk-row">
      <span class="pill pill-${escapeAttribute(check.status)}">${escapeHtml(check.status)}</span>
      <span>
        <strong>${escapeHtml(check.title)}</strong>
        <small>${escapeHtml(check.detail)}</small>
      </span>
    </article>
  `;
}

function stressRow(item) {
  return `
    <article class="risk-row">
      <span class="pill pill-${escapeAttribute(item.status)}">${escapeHtml(item.status)}</span>
      <span>
        <strong>${escapeHtml(item.label)}</strong>
        <small>${escapeHtml(item.detail)}</small>
      </span>
    </article>
  `;
}

function metricCard(label, value, detail) {
  return `
    <article class="metric">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
      <small>${escapeHtml(detail)}</small>
    </article>
  `;
}

function emptyState(text) {
  return `<div class="empty">${escapeHtml(text)}</div>`;
}

function optionalString(value) {
  const text = String(value ?? "").trim();
  return text || null;
}

function optionalNumber(value) {
  const text = String(value ?? "").trim();
  if (!text) {
    return null;
  }
  return numberValue(text);
}

function numberValue(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function splitKeys(value) {
  return String(value ?? "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function formatMoney(value) {
  return Number(value ?? 0).toLocaleString("zh-TW", {
    maximumFractionDigits: 2,
  });
}

function formatPercent(value) {
  return `${(Number(value ?? 0) * 100).toFixed(1)}%`;
}

function todayString() {
  const now = new Date();
  const offset = now.getTimezoneOffset();
  return new Date(now.getTime() - offset * 60000).toISOString().slice(0, 10);
}

function currentWeekStart() {
  const now = new Date(`${todayString()}T00:00:00`);
  const day = now.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  now.setDate(now.getDate() + diff);
  return now.toISOString().slice(0, 10);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function escapeAttribute(value) {
  return escapeHtml(value);
}
