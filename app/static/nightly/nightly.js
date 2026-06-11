const root = document.getElementById("root");
const LOCALE = "zh-TW";

const state = {
  pulse: null,
  anki: null,
  sessions: [],
  loading: true,
  drafting: false,
  saving: false,
  input: "",
  draft: null,
  message: "",
  error: "",
};

document.addEventListener("DOMContentLoaded", () => {
  void loadNightly();
});

async function loadNightly() {
  state.loading = true;
  state.error = "";
  render();

  try {
    const [pulse, anki, sessions] = await Promise.all([
      fetchJson("/learning/pulse/today"),
      fetchJson("/learning/anki/today"),
      fetchJson("/learning/sessions?limit=100"),
    ]);
    state.pulse = pulse;
    state.anki = anki;
    state.sessions = Array.isArray(sessions) ? sessions : [];
  } catch (caught) {
    state.error = caught instanceof Error ? caught.message : "讀取今晚資料失敗。";
  } finally {
    state.loading = false;
    render();
  }
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const responseText = await response.text();
    let detail = responseText.trim();
    try {
      const payload = JSON.parse(responseText);
      detail = String(payload.detail || payload.error || detail).trim();
    } catch {
      // Keep non-JSON server text.
    }
    throw new Error(`API 回應失敗：${response.status}${detail ? `，${detail}` : ""}`);
  }
  return response.json();
}

function render() {
  const todaySessions = sessionsForToday();
  root.innerHTML = `
    <main class="shell">
      <header class="topbar">
        <a class="brand" href="/dashboard">
          <span class="brand-mark" aria-hidden="true"></span>
          <span>LifeQuest</span>
        </a>
        <nav class="nav">
          <a class="pill-link" href="/japanese">日文</a>
          <a class="pill-link" href="/review/weekly">週回顧</a>
          <a class="pill-link" href="/dashboard">控制中心</a>
        </nav>
      </header>

      <section class="hero">
        <div>
          <p class="eyebrow">Codex Nightly Check-in</p>
          <h1 class="hero-title">今晚做了什麼？</h1>
        </div>
        <aside class="hero-side">
          ${statCard("今日學習", `${state.pulse?.total_minutes ?? 0} 分鐘`, `${state.pulse?.session_count ?? 0} 筆紀錄`)}
          ${statCard("Anki", ankiLabel(), ankiSubLabel())}
          ${statCard("明天優先", state.pulse?.tomorrow_priority ?? "先補一段短紀錄", "LifeQuest learning pulse")}
        </aside>
      </section>

      <section class="grid">
        <section class="panel chat-panel">
          <div class="chat-stream" aria-live="polite">
            ${assistantBubble("我在。把今天的學習、練習或排障丟給我，我會先整理成一筆 learning session 草稿。")}
            ${state.input ? userBubble(state.input) : ""}
            ${state.drafting ? assistantBubble("我正在整理，先把時間、主題和標籤抓出來。") : ""}
            ${state.draft ? draftBubble(state.draft) : ""}
          </div>

          <form id="checkin-form" class="composer">
            <textarea
              id="checkin-input"
              name="checkin"
              placeholder="例如：今天 Anki 複習 18 分鐘，另外看了 N3 文法，ている / てある 還有點卡。"
            >${escapeHtml(state.input)}</textarea>
            <div class="button-row">
              <button class="button button-primary" type="submit" ${state.drafting || state.saving ? "disabled" : ""}>
                ${state.drafting ? "整理中" : "讓 Codex 整理"}
              </button>
              <button class="button button-secondary" type="button" id="refresh-page">重新整理</button>
            </div>
          </form>

          ${state.message ? `<div class="message message-ok">${escapeHtml(state.message)}</div>` : ""}
          ${state.error ? `<div class="message message-error">${escapeHtml(state.error)}</div>` : ""}
        </section>

        <section class="panel">
          <h2 class="section-title">今天已記錄</h2>
          <div class="session-list">
            ${
              state.loading
                ? `<div class="empty">正在讀取今天的學習紀錄...</div>`
                : todaySessions.length
                  ? todaySessions.map((session) => sessionRow(session)).join("")
                  : `<div class="empty">今天還沒有 learning session。</div>`
            }
          </div>
        </section>
      </section>
    </main>
  `;

  bindControls();
}

function bindControls() {
  document.getElementById("refresh-page")?.addEventListener("click", () => {
    void loadNightly();
  });

  document.getElementById("checkin-input")?.addEventListener("input", (event) => {
    state.input = event.currentTarget.value;
  });

  document.getElementById("checkin-form")?.addEventListener("submit", (event) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    void draftCheckin(String(formData.get("checkin") || ""));
  });

  document.getElementById("save-draft")?.addEventListener("click", () => {
    void saveDraft(new FormData(document.getElementById("draft-form")));
  });

  document.getElementById("clear-draft")?.addEventListener("click", () => {
    state.draft = null;
    state.message = "";
    state.error = "";
    render();
  });
}

async function draftCheckin(text) {
  const cleaned = text.trim();
  state.message = "";
  state.error = "";
  if (!cleaned) {
    state.error = "先輸入今天做了什麼。";
    render();
    return;
  }

  state.input = cleaned;
  state.drafting = true;
  state.draft = null;
  render();

  try {
    state.draft = await fetchJson("/learning/checkin/draft", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: cleaned }),
    });
  } catch (caught) {
    state.error = caught instanceof Error ? caught.message : "整理失敗。";
  } finally {
    state.drafting = false;
    render();
  }
}

async function saveDraft(formData) {
  state.saving = true;
  state.message = "";
  state.error = "";
  render();

  const payload = {
    subject: String(formData.get("subject") || "japanese"),
    duration_minutes: Number(formData.get("duration") || 0),
    summary: String(formData.get("summary") || "").trim(),
    difficulty: nullableNumber(formData.get("difficulty")),
    energy_level: nullableNumber(formData.get("energy")),
    tags: parseTags(String(formData.get("tags") || "")),
  };

  try {
    if (!payload.summary) {
      throw new Error("摘要不能是空的。");
    }
    if (!Number.isFinite(payload.duration_minutes) || payload.duration_minutes <= 0) {
      throw new Error("分鐘數要大於 0。");
    }
    await fetchJson("/learning/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    state.message = "已存成 learning session。";
    state.input = "";
    state.draft = null;
    await loadNightly();
  } catch (caught) {
    state.error = caught instanceof Error ? caught.message : "儲存失敗。";
  } finally {
    state.saving = false;
    render();
  }
}

function assistantBubble(text) {
  return `
    <article class="bubble assistant">
      <div class="bubble-name">Codex</div>
      <p>${escapeHtml(text)}</p>
    </article>
  `;
}

function userBubble(text) {
  return `
    <article class="bubble user">
      <div class="bubble-name">你</div>
      <p>${escapeHtml(text)}</p>
    </article>
  `;
}

function draftBubble(draft) {
  const sourceLabel = draft.draft_source === "ai" ? "AI 已幫你整理成草稿。" : "先用本地整理成草稿。";
  const warningHtml = (draft.warnings ?? []).length
    ? `<div class="draft-warning">${(draft.warnings ?? []).map((warning) => escapeHtml(warning)).join("<br />")}</div>`
    : "";
  return `
    <article class="bubble assistant draft">
      <div class="bubble-name">Codex</div>
      <p>${escapeHtml(sourceLabel)}</p>
      <p>${escapeHtml(draft.assistant_note)}</p>
      ${warningHtml}
      <form id="draft-form" class="draft-form">
        <div class="form-grid">
          <label class="field">
            <span>主題</span>
            <select name="subject">
              ${subjectOption("japanese", "日文", draft.subject)}
              ${subjectOption("python", "Python", draft.subject)}
              ${subjectOption("sre", "SRE", draft.subject)}
            </select>
          </label>
          <label class="field">
            <span>分鐘</span>
            <input name="duration" type="number" min="1" max="1440" value="${draft.duration_minutes}" />
          </label>
          <label class="field">
            <span>難度</span>
            <select name="difficulty">
              ${numberOption("", "未填", draft.difficulty ?? "")}
              ${[1, 2, 3, 4, 5].map((value) => numberOption(value, `${value}`, draft.difficulty ?? "")).join("")}
            </select>
          </label>
          <label class="field">
            <span>能量</span>
            <select name="energy">
              ${numberOption("", "未填", draft.energy_level ?? "")}
              ${[1, 2, 3, 4, 5].map((value) => numberOption(value, `${value}`, draft.energy_level ?? "")).join("")}
            </select>
          </label>
          <label class="field field-full">
            <span>摘要</span>
            <textarea name="summary">${escapeHtml(draft.summary)}</textarea>
          </label>
          <label class="field field-full">
            <span>標籤</span>
            <input name="tags" value="${escapeAttribute((draft.tags ?? []).join(", "))}" />
          </label>
        </div>
        <div class="button-row">
          <button class="button button-primary" type="button" id="save-draft" ${state.saving ? "disabled" : ""}>
            ${state.saving ? "儲存中" : "確認儲存"}
          </button>
          <button class="button button-secondary" type="button" id="clear-draft">重寫</button>
        </div>
      </form>
    </article>
  `;
}

function subjectOption(value, label, selectedValue) {
  return `<option value="${escapeAttribute(value)}" ${value === selectedValue ? "selected" : ""}>${escapeHtml(label)}</option>`;
}

function numberOption(value, label, selectedValue) {
  return `<option value="${escapeAttribute(value)}" ${String(value) === String(selectedValue) ? "selected" : ""}>${escapeHtml(label)}</option>`;
}

function statCard(label, value, detail) {
  return `
    <article class="stat-card">
      <div class="stat-label">${escapeHtml(label)}</div>
      <strong class="stat-value">${escapeHtml(value)}</strong>
      <div class="mini-label">${escapeHtml(detail)}</div>
    </article>
  `;
}

function sessionRow(session) {
  return `
    <article class="session-row">
      <div>
        <div class="session-title">${escapeHtml(session.summary)}</div>
        <div class="session-meta">${escapeHtml(localizeSubject(session.subject))} · ${session.duration_minutes} 分鐘 · ${formatTime(session.started_at)}</div>
        <div class="tag-row">${(session.tags ?? []).map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join("")}</div>
      </div>
      <strong>${escapeHtml(difficultyLabel(session.difficulty, session.energy_level))}</strong>
    </article>
  `;
}

function sessionsForToday() {
  const today = currentDateString();
  return state.sessions.filter((session) => dateKey(session.started_at) === today);
}

function ankiLabel() {
  if (!state.anki) {
    return state.loading ? "讀取中" : "未知";
  }
  if (state.anki.enabled === false) {
    return "未啟用";
  }
  return `${state.anki.reviews ?? 0} reviews`;
}

function ankiSubLabel() {
  if (!state.anki) {
    return "等待 Anki 狀態";
  }
  if (state.anki.enabled === false) {
    return "ANKI_ENABLED=false";
  }
  if (state.anki.reviews > 0) {
    return `Again ${state.anki.again_count ?? 0} · Hard ${state.anki.hard_count ?? 0}`;
  }
  return "今天尚未匯入 Anki 複習";
}

function localizeSubject(subject) {
  if (subject === "japanese") {
    return "日文";
  }
  if (subject === "python") {
    return "Python";
  }
  if (subject === "sre") {
    return "SRE";
  }
  return subject || "學習";
}

function difficultyLabel(difficulty, energy) {
  const parts = [];
  if (difficulty) {
    parts.push(`難度 ${difficulty}`);
  }
  if (energy) {
    parts.push(`能量 ${energy}`);
  }
  return parts.join(" / ") || "已記錄";
}

function parseTags(value) {
  const tags = value
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
  return Array.from(new Set(["nightly-checkin", ...tags]));
}

function nullableNumber(value) {
  if (value === null || value === "") {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function currentDateString() {
  const now = new Date();
  const offset = now.getTimezoneOffset();
  return new Date(now.getTime() - offset * 60000).toISOString().slice(0, 10);
}

function dateKey(value) {
  const parsed = new Date(value);
  const offset = parsed.getTimezoneOffset();
  return new Date(parsed.getTime() - offset * 60000).toISOString().slice(0, 10);
}

function formatTime(value) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "未知時間";
  }
  return parsed.toLocaleTimeString(LOCALE, {
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
