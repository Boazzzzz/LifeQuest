const root = document.getElementById("root");
const LOCALE = "zh-TW";

const templates = [
  {
    key: "japanese-grammar",
    title: "日文文法",
    subject: "japanese",
    minutes: 20,
    summary: "日文文法練習",
    tags: ["nightly-checkin", "japanese", "grammar"],
  },
  {
    key: "japanese-reading",
    title: "日文閱讀 / 聽力",
    subject: "japanese",
    minutes: 20,
    summary: "日文閱讀或聽力練習",
    tags: ["nightly-checkin", "japanese", "input"],
  },
  {
    key: "python-automation",
    title: "Python 自動化",
    subject: "python",
    minutes: 30,
    summary: "Python 自動化練習",
    tags: ["nightly-checkin", "python", "automation"],
  },
  {
    key: "sre-linux",
    title: "SRE / Linux",
    subject: "sre",
    minutes: 30,
    summary: "SRE 或 Linux 練習",
    tags: ["nightly-checkin", "sre", "linux"],
  },
  {
    key: "kubernetes",
    title: "Kubernetes",
    subject: "sre",
    minutes: 30,
    summary: "Kubernetes 學習或實驗",
    tags: ["nightly-checkin", "sre", "kubernetes"],
  },
  {
    key: "anki-time",
    title: "Anki 時間補登",
    subject: "japanese",
    minutes: 10,
    summary: "日文 Anki 複習",
    tags: ["nightly-checkin", "japanese", "anki"],
  },
];

const state = {
  selectedTemplateKey: templates[0].key,
  pulse: null,
  anki: null,
  sessions: [],
  loading: true,
  saving: false,
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
    state.error = caught instanceof Error ? caught.message : "讀取睡前回顧資料失敗。";
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
      // Non-JSON errors still carry useful text from the server.
    }
    throw new Error(`API 請求失敗：${response.status}${detail ? `，${detail}` : ""}`);
  }
  return response.json();
}

function render() {
  const template = selectedTemplate();
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
          <a class="pill-link" href="/dashboard">總覽</a>
        </nav>
      </header>

      <section class="hero">
        <div>
          <p class="eyebrow">Nightly Learning Check-in</p>
          <h1 class="hero-title">睡前自學回顧</h1>
          <p class="hero-copy">
            這不是待辦清單，而是一天結束前的收束：LifeQuest 先顯示自動抓到的訊號，
            你只補登今天實際做過、但機器不知道的自學。
          </p>
        </div>
        <aside class="hero-side">
          ${statCard("今日學習", `${state.pulse?.total_minutes ?? 0} 分鐘`, `${state.pulse?.session_count ?? 0} 筆手動紀錄`)}
          ${statCard("Anki", ankiLabel(), ankiSubLabel())}
          ${statCard("SRE", `${state.pulse?.sre_minutes ?? 0} 分鐘`, "Linux、Kubernetes、可靠性練習")}
        </aside>
      </section>

      <section class="grid">
        <section class="panel">
          <h2 class="section-title">今天還做了什麼？</h2>
          <p class="section-subtitle">選一個模板，調整時間和一句話摘要。儲存後會直接進入 learning session。</p>

          <div class="template-grid">
            ${templates.map((item) => templateCard(item)).join("")}
          </div>

          <form id="nightly-form" style="margin-top: 18px;">
            <div class="form-grid">
              <div class="field">
                <label for="subject">主線</label>
                <select id="subject" name="subject">
                  ${subjectOption("japanese", "日文", template.subject)}
                  ${subjectOption("python", "Python", template.subject)}
                  ${subjectOption("sre", "SRE", template.subject)}
                </select>
              </div>

              <div class="field">
                <label for="duration">分鐘</label>
                <input id="duration" name="duration" type="number" min="1" max="1440" value="${template.minutes}" />
              </div>

              <div class="field">
                <label for="difficulty">難度</label>
                <select id="difficulty" name="difficulty">
                  ${numberOption("", "未填", "")}
                  ${[1, 2, 3, 4, 5].map((value) => numberOption(value, `${value}`, "")).join("")}
                </select>
              </div>

              <div class="field">
                <label for="energy">精神</label>
                <select id="energy" name="energy">
                  ${numberOption("", "未填", "")}
                  ${[1, 2, 3, 4, 5].map((value) => numberOption(value, `${value}`, "")).join("")}
                </select>
              </div>

              <div class="field field-full">
                <label for="summary">一句話摘要</label>
                <textarea id="summary" name="summary">${escapeHtml(template.summary)}</textarea>
              </div>

              <div class="field field-full">
                <label for="tags">標籤</label>
                <input id="tags" name="tags" value="${escapeAttribute(template.tags.join(", "))}" />
              </div>
            </div>

            <div class="button-row">
              <button class="button button-primary" type="submit" ${state.saving ? "disabled" : ""}>
                ${state.saving ? "儲存中..." : "儲存今天的自學"}
              </button>
              <button class="button button-secondary" type="button" id="refresh-page">重新讀取</button>
            </div>

            ${state.message ? `<div class="message message-ok">${escapeHtml(state.message)}</div>` : ""}
            ${state.error ? `<div class="message message-error">${escapeHtml(state.error)}</div>` : ""}
          </form>
        </section>

        <section class="panel">
          <h2 class="section-title">今天已經記錄</h2>
          <p class="section-subtitle">這裡包含你手動補登的 sessions；Anki review 會顯示在上方，不一定要重複補登。</p>
          <div class="session-list">
            ${
              state.loading
                ? `<div class="empty">正在讀取今天的學習紀錄...</div>`
                : todaySessions.length
                  ? todaySessions.map((session) => sessionRow(session)).join("")
                  : `<div class="empty">今天還沒有手動自學紀錄。選左邊一個項目，先補一筆就好。</div>`
            }
          </div>
        </section>
      </section>
    </main>
  `;

  bindControls();
}

function bindControls() {
  document.querySelectorAll("[data-template]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedTemplateKey = button.getAttribute("data-template") || templates[0].key;
      state.message = "";
      state.error = "";
      render();
    });
  });

  document.getElementById("refresh-page")?.addEventListener("click", () => {
    void loadNightly();
  });

  document.getElementById("nightly-form")?.addEventListener("submit", (event) => {
    event.preventDefault();
    void saveSession(new FormData(event.currentTarget));
  });
}

async function saveSession(formData) {
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
      throw new Error("請填一句話摘要。");
    }
    if (!Number.isFinite(payload.duration_minutes) || payload.duration_minutes <= 0) {
      throw new Error("分鐘數需要大於 0。");
    }
    await fetchJson("/learning/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    state.message = "已記錄今天的自學。小小一筆，也是在替未來的你鋪路。";
    await loadNightly();
  } catch (caught) {
    state.error = caught instanceof Error ? caught.message : "儲存失敗。";
  } finally {
    state.saving = false;
    render();
  }
}

function selectedTemplate() {
  return templates.find((item) => item.key === state.selectedTemplateKey) ?? templates[0];
}

function templateCard(item) {
  const selected = item.key === state.selectedTemplateKey ? "selected" : "";
  return `
    <button class="template-card ${selected}" type="button" data-template="${escapeAttribute(item.key)}">
      <div class="template-title">${escapeHtml(item.title)}</div>
      <div class="template-meta">${escapeHtml(localizeSubject(item.subject))} · ${item.minutes} 分鐘</div>
    </button>
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
    return state.loading ? "讀取中" : "無資料";
  }
  if (state.anki.enabled === false) {
    return "未啟用";
  }
  return `${state.anki.reviews ?? 0} reviews`;
}

function ankiSubLabel() {
  if (!state.anki) {
    return "桌面 Anki 同步後會出現在這裡";
  }
  if (state.anki.enabled === false) {
    return "ANKI_ENABLED=false";
  }
  if (state.anki.reviews > 0) {
    return `重來 ${state.anki.again_count ?? 0} · 困難 ${state.anki.hard_count ?? 0}`;
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
    parts.push(`精神 ${energy}`);
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
    return "時間未知";
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
