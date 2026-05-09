const root = document.getElementById("root");

const categories = [
  "ai",
  "productivity",
  "membership",
  "entertainment",
  "education",
  "software",
  "cloud",
  "finance",
  "utilities",
  "other",
];

const lifecycleLabels = {
  active: "\u4f7f\u7528\u4e2d",
  paused: "\u66ab\u505c",
  cancelled: "\u5df2\u53d6\u6d88",
};

const emptyOverview = {
  active_subscription_count: 0,
  paused_subscription_count: 0,
  cancelled_subscription_count: 0,
  scheduled_subscription_count: 0,
  totals_by_currency: {},
  totals_by_category: {},
  upcoming_charges: [],
};

const appState = {
  overview: emptyOverview,
  subscriptions: [],
  filter: "all",
  editingRef: null,
  usingFallback: false,
  message: null,
};

document.addEventListener("DOMContentLoaded", () => {
  renderLoading();
  void loadPage();
});

async function loadPage(message = null) {
  const [overview, subscriptions] = await Promise.all([
    safeFetchJson("/subscriptions/overview/monthly?days_ahead=40"),
    safeFetchJson("/subscriptions"),
  ]);

  appState.overview = overview ?? emptyOverview;
  appState.subscriptions = Array.isArray(subscriptions) ? subscriptions : [];
  appState.usingFallback = overview === null || subscriptions === null;
  appState.message = message ?? (appState.usingFallback
    ? { type: "error", text: "\u8a02\u95b1 API \u8b80\u53d6\u4e0d\u5b8c\u6574\uff0c\u9801\u9762\u5df2\u96b1\u85cf\u793a\u7bc4\u8cc7\u6599\u3002" }
    : null);
  render();
}

function renderLoading() {
  root.innerHTML = `
    <main class="shell">
      <section class="hero loading-card">
        <div>
          <p class="eyebrow">Life Admin</p>
          <h1 class="hero-title">\u6b63\u5728\u8b80\u53d6\u8a02\u95b1</h1>
          <p class="hero-copy">\u6b63\u5728\u5f9e LifeQuest \u6574\u7406\u6bcf\u6708\u6263\u6b3e\u6e05\u55ae\u3002</p>
        </div>
      </section>
    </main>
  `;
}

function render() {
  const overview = appState.overview;
  const subscriptions = appState.subscriptions;
  const categoryRows = Object.entries(overview.totals_by_category ?? {});
  const upcomingCharges = overview.upcoming_charges ?? [];
  const filteredSubscriptions = filterSubscriptions(subscriptions, appState.filter);
  const counts = getFilterCounts(subscriptions);
  const monthlyTwd = estimateMonthlyTwd(overview.totals_by_currency);

  root.innerHTML = `
    <main class="shell">
      <div class="topbar" data-reveal>
        <a class="back-link" href="/dashboard">\u56de\u5230\u7e3d\u89bd</a>
        <a class="back-link" href="/docs#/subscriptions">API \u6587\u4ef6</a>
      </div>

      <section class="hero" data-reveal data-delay="1">
        <div>
          <p class="eyebrow">Life Admin</p>
          <h1 class="hero-title">\u8a02\u95b1\u652f\u51fa\uff0c\u4e00\u773c\u770b\u6e05\u3002</h1>
          <p class="hero-copy">
            \u53ea\u4fdd\u7559\u6bcf\u6708\u6263\u6b3e\u65e5\uff1a\u8a02\u95b1\u4ec0\u9ebc\u3001\u91d1\u984d\u591a\u5c11\u3001\u5e7e\u865f\u6263\u6b3e\u3002
            \u8cc7\u6599\u8f38\u5165\u5f97\u6e05\u695a\uff0c\u5f8c\u9762\u624d\u4e0d\u6703\u8b8a\u6210\u751f\u6d3b\u8ff7\u9727\u3002
          </p>
        </div>
        <aside class="hero-side">
          <div class="mini-stack">
            ${miniCard("\u6bcf\u6708\u7e3d\u652f\u51fa", `NT$ ${formatWhole(monthlyTwd)}`, "mini-card-highlight")}
            ${miniCard("\u4f7f\u7528\u4e2d", overview.active_subscription_count)}
            ${miniCard("\u66ab\u505c", overview.paused_subscription_count ?? 0)}
            ${miniCard("\u5373\u5c07\u6263\u6b3e", upcomingCharges.length)}
          </div>
          <div class="mini-note">
            ${appState.usingFallback
              ? "\u5f8c\u7aef\u8b80\u53d6\u4e0d\u5b8c\u6574\u6642\uff0c\u9019\u9801\u4e0d\u6703\u518d\u986f\u793a\u5047\u8cc7\u6599\u3002"
              : "\u76ee\u524d\u986f\u793a\u7684\u662f\u672c\u6a5f\u8cc7\u6599\u5eab\u4e2d\u7684\u771f\u5be6\u8a02\u95b1\u8cc7\u6599\u3002"}
          </div>
        </aside>
      </section>

      ${messageBanner(appState.message)}

      <section class="stats-grid" data-reveal data-delay="1">
        ${statCard("\u6bcf\u6708\u7e3d\u652f\u51fa", `NT$ ${formatWhole(monthlyTwd)}`, "\u4ee5\u65b0\u81fa\u5e63\u4f30\u7b97\uff1aUSD x 30\uff0cJPY / 5\u3002")}
        ${statCard("\u4f7f\u7528\u4e2d", overview.active_subscription_count, "\u6703\u8a08\u5165\u76ee\u524d\u6bcf\u6708\u652f\u51fa\u3002")}
        ${statCard("\u66ab\u505c", overview.paused_subscription_count ?? 0, "\u4fdd\u7559\u7d00\u9304\uff0c\u4f46\u4e0d\u8a08\u5165\u652f\u51fa\u3002")}
        ${statCard("\u5373\u5c07\u6263\u6b3e", upcomingCharges.length, "\u672a\u4f86 40 \u5929\u5167\u5df2\u77e5\u6263\u6b3e\u3002")}
      </section>

      <section class="content-grid">
        ${registryPanel(filteredSubscriptions, counts)}

        <div class="two-up">
          <section class="panel" data-reveal data-delay="2">
            <div class="section-head">
              <div>
                <h2 class="section-title">\u6bcf\u6708\u91d1\u984d</h2>
                <p class="section-subtitle">\u53ea\u8a08\u7b97\u76ee\u524d\u4f7f\u7528\u4e2d\u7684\u8a02\u95b1\u3002</p>
              </div>
            </div>
            <div class="currency-grid">
              ${twdSummaryRow(monthlyTwd)}
              ${Object.entries(overview.totals_by_currency ?? {})
                .map(([currency, total]) => currencyRow(currency, `${currency} ${formatAmount(total)}`))
                .join("") || `<div class="empty-state">\u76ee\u524d\u6c92\u6709\u4f7f\u7528\u4e2d\u7684\u8a02\u95b1\u91d1\u984d\u3002</div>`}
            </div>
          </section>

          <section class="panel" data-reveal data-delay="3">
            <div class="section-head">
              <div>
                <h2 class="section-title">\u5206\u985e\u6bd4\u4f8b</h2>
                <p class="section-subtitle">\u5feb\u901f\u770b\u76ee\u524d\u82b1\u8cbb\u662f\u5426\u9084\u7b26\u5408\u4f60\u7684\u91cd\u5fc3\u3002</p>
              </div>
            </div>
            <div class="currency-grid">
              ${categoryRows.length
                ? categoryRows.map(([category, totals]) => currencyRow(category, formatCategoryTotals(totals))).join("")
                : `<div class="empty-state">\u76ee\u524d\u6c92\u6709\u5206\u985e\u91d1\u984d\u3002</div>`}
            </div>
          </section>
        </div>

        <section class="panel" data-reveal data-delay="2">
          <div class="section-head">
            <div>
              <h2 class="section-title">\u5373\u5c07\u6263\u6b3e</h2>
              <p class="section-subtitle">\u672a\u4f86 40 \u5929\u5167\u7684\u5df2\u77e5\u6263\u6b3e\u3002</p>
            </div>
            <span class="pill pill-ok">${upcomingCharges.length} \u7b46</span>
          </div>
          <div class="list-stack">
            ${upcomingCharges.length
              ? upcomingCharges.map((charge) => upcomingChargeCard(charge)).join("")
              : `<div class="empty-state">\u672a\u4f86 40 \u5929\u5167\u6c92\u6709\u5df2\u77e5\u6263\u6b3e\u3002</div>`}
          </div>
        </section>

        ${editorPanel(subscriptions)}
      </section>
    </main>
  `;

  bindEvents();
}

function registryPanel(filteredSubscriptions, counts) {
  return `
    <section class="panel registry-panel" data-reveal data-delay="2">
      <div class="section-head registry-head">
        <div>
          <p class="eyebrow">Your Records</p>
          <h2 class="section-title">\u6211\u7684\u8a02\u95b1</h2>
          <p class="section-subtitle">\u8a02\u95b1\u540d\u7a31\u3001\u91d1\u984d\u3001\u6bcf\u6708\u6263\u6b3e\u65e5\u662f\u5fc5\u586b\u8cc7\u6599\u3002</p>
        </div>
        <button class="button secondary-button" type="button" data-action="new-record">\u65b0\u589e\u8a02\u95b1</button>
      </div>

      <div class="filter-bar" aria-label="Subscription filters">
        ${filterButton("all", "\u5168\u90e8", counts.all)}
        ${filterButton("active", "\u4f7f\u7528\u4e2d", counts.active)}
        ${filterButton("paused", "\u66ab\u505c", counts.paused)}
        ${filterButton("cancelled", "\u5df2\u53d6\u6d88", counts.cancelled)}
      </div>

      <div class="table-list">
        ${filteredSubscriptions.length
          ? filteredSubscriptions.map((subscription) => subscriptionRow(subscription)).join("")
          : `<div class="empty-state">\u9019\u500b\u7be9\u9078\u76ee\u524d\u6c92\u6709\u8a02\u95b1\u3002</div>`}
      </div>
    </section>
  `;
}

function editorPanel(subscriptions) {
  const editing = subscriptions.find((item) => getSubscriptionRef(item) === appState.editingRef);
  const item = editing ?? getBlankSubscription();
  const isEditing = Boolean(editing);

  return `
    <section class="panel editor-panel" id="subscription-editor" data-reveal data-delay="2">
      <div class="section-head editor-head">
        <div>
          <h2 class="section-title">${isEditing ? "\u7de8\u8f2f\u8a02\u95b1" : "\u65b0\u589e\u8a02\u95b1"}</h2>
          <p class="section-subtitle">
            ${isEditing
              ? "\u66f4\u65b0\u9019\u7b46\u6bcf\u6708\u8a02\u95b1\u8cc7\u6599\u3002"
              : "\u8acb\u628a\u8a02\u95b1\u4ec0\u9ebc\u3001\u91d1\u984d\u3001\u6bcf\u6708\u6263\u6b3e\u65e5\u586b\u6e05\u695a\u3002"}
          </p>
        </div>
        ${isEditing ? `<span class="pill pill-neutral">\u7de8\u8f2f\u4e2d ${escapeHtml(item.key)}</span>` : ""}
      </div>

      <form class="subscription-form" id="subscription-form">
        <div class="form-grid">
          <label class="field">
            <span>Key</span>
            <input name="key" value="${escapeAttribute(item.key ?? "")}" placeholder="optional-stable-key" ${isEditing ? "disabled" : ""} />
          </label>

          <label class="field field-wide">
            <span>\u8a02\u95b1\u4ec0\u9ebc</span>
            <input name="name" value="${escapeAttribute(item.name ?? "")}" placeholder="ChatGPT Plus" required />
          </label>

          <label class="field">
            <span>\u8a02\u95b1\u91d1\u984d</span>
            <input name="amount" type="number" min="0.01" step="0.01" value="${escapeAttribute(item.amount ?? "")}" required />
          </label>

          <label class="field">
            <span>\u5e63\u5225</span>
            <input name="currency" maxlength="8" value="${escapeAttribute(item.currency ?? "TWD")}" placeholder="TWD" required />
          </label>

          <label class="field">
            <span>\u6bcf\u6708\u6263\u6b3e\u65e5</span>
            <input name="billing_day" type="number" min="1" max="31" value="${escapeAttribute(item.billing_day ?? "")}" placeholder="28" required />
          </label>

          <label class="field">
            <span>\u72c0\u614b</span>
            <select name="status">
              ${optionList(Object.keys(lifecycleLabels), item.status ?? "active", lifecycleLabels)}
            </select>
          </label>

          <label class="field">
            <span>\u5206\u985e</span>
            <select name="category">
              ${optionList(categories, item.category ?? "other")}
            </select>
          </label>

          <label class="field field-wide">
            <span>\u6a19\u7c64</span>
            <input name="tags" value="${escapeAttribute((item.tags ?? []).join(", "))}" placeholder="ai, coding, study" />
          </label>

          <label class="field field-full">
            <span>\u5099\u8a3b</span>
            <textarea name="notes" rows="3" placeholder="\u70ba\u4ec0\u9ebc\u4fdd\u7559\u3001\u4e4b\u5f8c\u8981\u4e0d\u8981\u6aa2\u67e5...">${escapeHtml(item.notes ?? "")}</textarea>
          </label>
        </div>

        <div class="form-actions">
          <button class="button primary-button" type="submit">${isEditing ? "\u5132\u5b58\u4fee\u6539" : "\u65b0\u589e\u8a02\u95b1"}</button>
          <button class="button secondary-button" type="button" data-action="reset-form">${isEditing ? "\u53d6\u6d88\u7de8\u8f2f" : "\u6e05\u7a7a\u8868\u55ae"}</button>
        </div>
      </form>
    </section>
  `;
}

function bindEvents() {
  const form = document.getElementById("subscription-form");
  form?.addEventListener("submit", handleFormSubmit);

  document.querySelector('[data-action="reset-form"]')?.addEventListener("click", () => {
    appState.editingRef = null;
    appState.message = null;
    render();
  });

  document.querySelector('[data-action="new-record"]')?.addEventListener("click", () => {
    appState.editingRef = null;
    appState.message = null;
    render();
    scrollEditorIntoView();
  });

  document.querySelectorAll("[data-filter]").forEach((button) => {
    button.addEventListener("click", () => {
      appState.filter = button.dataset.filter ?? "all";
      render();
    });
  });

  document.querySelectorAll("[data-edit]").forEach((button) => {
    button.addEventListener("click", () => {
      appState.editingRef = button.dataset.edit ?? null;
      appState.message = null;
      render();
      scrollEditorIntoView();
    });
  });

  document.querySelectorAll("[data-status-action]").forEach((button) => {
    button.addEventListener("click", () => {
      void updateLifecycleStatus(button.dataset.ref, button.dataset.statusAction, button);
    });
  });
}

async function handleFormSubmit(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const submitButton = form.querySelector('button[type="submit"]');
  const isEditing = Boolean(appState.editingRef);

  try {
    const payload = buildPayloadFromForm(new FormData(form), isEditing);
    submitButton.disabled = true;
    submitButton.textContent = isEditing ? "\u5132\u5b58\u4e2d..." : "\u65b0\u589e\u4e2d...";

    const url = isEditing ? `/subscriptions/${encodeURIComponent(appState.editingRef)}` : "/subscriptions";
    const response = await fetch(url, {
      method: isEditing ? "PATCH" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error(await getApiErrorMessage(response));
    }

    appState.editingRef = null;
    await loadPage({ type: "success", text: isEditing ? "\u8a02\u95b1\u5df2\u66f4\u65b0\u3002" : "\u8a02\u95b1\u5df2\u65b0\u589e\u3002" });
  } catch (error) {
    appState.message = {
      type: "error",
      text: error instanceof Error ? error.message : "\u7121\u6cd5\u5132\u5b58\u8a02\u95b1\u3002",
    };
    render();
  }
}

async function updateLifecycleStatus(ref, status, button) {
  if (!ref || !status) {
    return;
  }

  try {
    button.disabled = true;
    const response = await fetch(`/subscriptions/${encodeURIComponent(ref)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });

    if (!response.ok) {
      throw new Error(await getApiErrorMessage(response));
    }

    await loadPage({ type: "success", text: `\u8a02\u95b1\u72c0\u614b\u5df2\u6539\u70ba ${lifecycleLabels[status] ?? status}\u3002` });
  } catch (error) {
    appState.message = {
      type: "error",
      text: error instanceof Error ? error.message : "\u7121\u6cd5\u66f4\u65b0\u8a02\u95b1\u72c0\u614b\u3002",
    };
    render();
  }
}

function buildPayloadFromForm(formData, isEditing) {
  const name = String(formData.get("name") || "").trim();
  const amount = Number(formData.get("amount"));
  const currency = String(formData.get("currency") || "").trim().toUpperCase();
  const billingDay = Number(formData.get("billing_day"));

  if (!name) {
    throw new Error("\u8acb\u586b\u5beb\u8a02\u95b1\u540d\u7a31\u3002");
  }
  if (!Number.isFinite(amount) || amount <= 0) {
    throw new Error("\u91d1\u984d\u5fc5\u9808\u5927\u65bc 0\u3002");
  }
  if (currency.length < 3) {
    throw new Error("\u5e63\u5225\u8acb\u586b TWD\u3001USD\u3001JPY\u3001USDT \u9019\u985e\u4ee3\u78bc\u3002");
  }
  if (!Number.isInteger(billingDay) || billingDay < 1 || billingDay > 31) {
    throw new Error("\u8acb\u586b\u5beb 1 \u5230 31 \u4e4b\u9593\u7684\u6bcf\u6708\u6263\u6b3e\u65e5\u3002");
  }

  const payload = {
    name,
    amount,
    currency,
    billing_day: billingDay,
    recurrence_kind: "monthly",
    anchor_charge_date: null,
    interval_days: null,
    status: String(formData.get("status") || "active"),
    category: String(formData.get("category") || "other"),
    notes: normalizeNullableString(formData.get("notes")),
    tags: parseTags(formData.get("tags")),
  };

  if (!isEditing) {
    const key = normalizeNullableString(formData.get("key"));
    if (key) {
      payload.key = key;
    }
  }

  return payload;
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

async function getApiErrorMessage(response) {
  try {
    const payload = await response.json();
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
    if (Array.isArray(payload.detail) && payload.detail.length) {
      return payload.detail.map((item) => item.msg || "Validation error").join(" ");
    }
  } catch {
    return `Request failed with status ${response.status}.`;
  }
  return `Request failed with status ${response.status}.`;
}

function filterSubscriptions(subscriptions, filter) {
  if (filter === "all") {
    return subscriptions;
  }
  return subscriptions.filter((item) => (item.status ?? "active") === filter);
}

function getFilterCounts(subscriptions) {
  return {
    all: subscriptions.length,
    active: subscriptions.filter((item) => (item.status ?? "active") === "active").length,
    paused: subscriptions.filter((item) => item.status === "paused").length,
    cancelled: subscriptions.filter((item) => item.status === "cancelled").length,
  };
}

function getBlankSubscription() {
  return {
    key: "",
    name: "",
    amount: "",
    currency: "TWD",
    status: "active",
    category: "other",
    billing_day: "",
    notes: "",
    tags: [],
  };
}

function miniCard(label, value, className = "") {
  return `<div class="mini-card ${escapeAttribute(className)}"><div class="mini-label">${escapeHtml(label)}</div><div class="mini-value">${escapeHtml(String(value))}</div></div>`;
}

function statCard(label, value, help) {
  return `<section class="stat-card"><div class="stat-label">${escapeHtml(label)}</div><div class="stat-value">${escapeHtml(String(value))}</div><div class="stat-help">${escapeHtml(help)}</div></section>`;
}

function currencyRow(label, value) {
  return `<div class="currency-row"><span class="currency-label">${escapeHtml(label)}</span><span class="currency-value">${escapeHtml(String(value))}</span></div>`;
}

function twdSummaryRow(total) {
  return `<div class="currency-row currency-row-highlight"><span class="currency-label">\u6bcf\u6708\u7e3d\u652f\u51fa\uff08\u65b0\u81fa\u5e63\u4f30\u7b97\uff09</span><span class="currency-value">${escapeHtml(`NT$ ${formatWhole(total)}`)}</span></div>`;
}

function upcomingChargeCard(charge) {
  const meta = `${formatMoney(charge)} | ${formatShortDate(charge.next_charge_date)} | ${daysUntilText(charge.days_until_charge)}`;
  return listCard(charge.name, meta, formatScheduleSummary(charge.schedule_summary));
}

function listCard(title, meta, note) {
  return `<article class="list-card"><div class="row-title">${escapeHtml(title)}</div><div class="row-meta">${escapeHtml(meta)}</div><div class="row-meta">${escapeHtml(note ?? "")}</div></article>`;
}

function subscriptionRow(subscription) {
  const lifecycle = subscription.status ?? "active";
  const schedule = subscription.schedule_status ?? "";
  const lifecycleClass = `life-${lifecycle}`;
  const ref = getSubscriptionRef(subscription);

  return `
    <article class="table-row">
      <div>
        <div class="row-title">${escapeHtml(subscription.name)}</div>
        <div class="row-meta">${escapeHtml(subscription.key)} | ${escapeHtml(subscription.category ?? "other")}</div>
        <div class="row-meta">${escapeHtml(subscription.notes || "\u5c1a\u7121\u5099\u8a3b")}</div>
      </div>
      <div>
        <div class="row-title">${escapeHtml(formatMoney(subscription))}</div>
        <div class="row-meta">${escapeHtml(formatMonthlyDay(subscription))}</div>
      </div>
      <div>
        <span class="pill status-chip ${lifecycleClass}">${escapeHtml(lifecycleLabels[lifecycle] ?? lifecycle)}</span>
        ${schedule === "scheduled" ? `<span class="pill status-chip status-scheduled">\u5df2\u6392\u5b9a</span>` : ""}
        <div class="row-meta">${escapeHtml(subscription.next_charge_date ? formatShortDate(subscription.next_charge_date) : "\u5c1a\u7121\u4e0b\u6b21\u6263\u6b3e\u65e5")}</div>
      </div>
      <div class="row-actions">
        <button class="button ghost-button compact-button" type="button" data-edit="${escapeAttribute(ref)}">\u7de8\u8f2f</button>
        ${statusButtons(subscription, ref)}
      </div>
    </article>
  `;
}

function statusButtons(subscription, ref) {
  const lifecycle = subscription.status ?? "active";
  if (lifecycle === "active") {
    return `
      <button class="button ghost-button compact-button" type="button" data-ref="${escapeAttribute(ref)}" data-status-action="paused">\u66ab\u505c</button>
      <button class="button ghost-button compact-button danger-button" type="button" data-ref="${escapeAttribute(ref)}" data-status-action="cancelled">\u53d6\u6d88</button>
    `;
  }
  if (lifecycle === "paused") {
    return `
      <button class="button ghost-button compact-button" type="button" data-ref="${escapeAttribute(ref)}" data-status-action="active">\u6062\u5fa9</button>
      <button class="button ghost-button compact-button danger-button" type="button" data-ref="${escapeAttribute(ref)}" data-status-action="cancelled">\u53d6\u6d88</button>
    `;
  }
  return `<button class="button ghost-button compact-button" type="button" data-ref="${escapeAttribute(ref)}" data-status-action="active">\u6062\u5fa9</button>`;
}

function filterButton(filter, label, count) {
  const isActive = appState.filter === filter;
  return `
    <button class="filter-button ${isActive ? "is-active" : ""}" type="button" data-filter="${escapeAttribute(filter)}">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(String(count))}</strong>
    </button>
  `;
}

function messageBanner(message) {
  if (!message) {
    return "";
  }
  return `
    <div class="message-banner ${message.type === "error" ? "message-error" : "message-success"}" role="status" data-reveal>
      ${escapeHtml(message.text)}
    </div>
  `;
}

function optionList(values, selectedValue, labels = null) {
  return values
    .map((value) => {
      const selected = value === selectedValue ? "selected" : "";
      const label = labels?.[value] ?? value;
      return `<option value="${escapeAttribute(value)}" ${selected}>${escapeHtml(label)}</option>`;
    })
    .join("");
}

function formatCategoryTotals(totals) {
  return Object.entries(totals)
    .map(([currency, total]) => `${currency} ${formatAmount(total)}`)
    .join(", ");
}

function formatMonthlyDay(subscription) {
  return subscription.billing_day
    ? `\u6bcf\u6708 ${subscription.billing_day} \u865f\u6263\u6b3e`
    : "\u5c1a\u672a\u8a18\u9304\u6bcf\u6708\u6263\u6b3e\u65e5";
}

function formatScheduleSummary(summary) {
  if (!summary) {
    return "";
  }
  const monthlyMatch = String(summary).match(/^Monthly on day (\d+)$/);
  if (monthlyMatch) {
    return `\u6bcf\u6708 ${monthlyMatch[1]} \u865f\u6263\u6b3e`;
  }
  if (summary === "Paused subscription") {
    return "\u66ab\u505c\u4e2d\u7684\u8a02\u95b1";
  }
  if (summary === "Cancelled subscription") {
    return "\u5df2\u53d6\u6d88\u7684\u8a02\u95b1";
  }
  return summary;
}

function formatMoney(item) {
  return `${item.currency} ${formatAmount(item.amount)}`;
}

function formatAmount(value) {
  return Number(value).toLocaleString(undefined, {
    minimumFractionDigits: Number(value) % 1 === 0 ? 0 : 2,
    maximumFractionDigits: 2,
  });
}

function estimateMonthlyTwd(totalsByCurrency) {
  return Object.entries(totalsByCurrency ?? {}).reduce((sum, [currency, total]) => {
    return sum + currencyToTwd(currency, Number(total));
  }, 0);
}

function currencyToTwd(currency, amount) {
  if (!Number.isFinite(amount)) {
    return 0;
  }
  const normalized = String(currency).toUpperCase();
  if (normalized === "TWD" || normalized === "NTD") {
    return amount;
  }
  if (normalized === "USD" || normalized === "USDT") {
    return amount * 30;
  }
  if (normalized === "JPY") {
    return amount / 5;
  }
  return 0;
}

function formatWhole(value) {
  return Math.round(value).toLocaleString();
}

function formatShortDate(value) {
  return new Date(`${value}T00:00:00`).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

function daysUntilText(value) {
  if (value === 0) {
    return "\u4eca\u5929";
  }
  if (value === 1) {
    return "\u660e\u5929";
  }
  return `${value} \u5929\u5f8c`;
}

function getSubscriptionRef(subscription) {
  return subscription.key || subscription.id;
}

function normalizeNullableString(value) {
  const normalized = String(value ?? "").trim();
  return normalized || null;
}

function parseTags(value) {
  return String(value ?? "")
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

function scrollEditorIntoView() {
  document.getElementById("subscription-editor")?.scrollIntoView({ behavior: "smooth", block: "start" });
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
