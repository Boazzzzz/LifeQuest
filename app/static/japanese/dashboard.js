const root = document.getElementById("root");
const LOCALE = "zh-TW";

const state = {
  selectedDate: currentDateString(),
  dashboard: null,
  loading: true,
  error: "",
};

document.addEventListener("DOMContentLoaded", () => {
  void loadDashboard();
});

async function loadDashboard() {
  state.loading = true;
  state.error = "";
  render();

  try {
    const params = new URLSearchParams({
      date: state.selectedDate,
      history_days: "7",
      difficult_days: "14",
      difficult_limit: "8",
    });
    const response = await fetch(`/learning/japanese/dashboard?${params.toString()}`);
    if (!response.ok) {
      throw new Error(`儀表板請求失敗，HTTP 狀態碼：${response.status}`);
    }
    state.dashboard = await response.json();
  } catch (caught) {
    state.error = caught instanceof Error ? caught.message : "未知的儀表板錯誤";
  } finally {
    state.loading = false;
    render();
  }
}

function render() {
  if (state.loading && !state.dashboard) {
    root.innerHTML = `
      <div class="loading-shell">
        <p class="eyebrow">LifeQuest</p>
        <h1 class="hero-title">正在載入日文學習儀表板</h1>
        <p class="hero-copy">正在整理 Anki 快照、複習歷史與日文學習紀錄。</p>
      </div>
    `;
    return;
  }

  if (state.error && !state.dashboard) {
    root.innerHTML = `
      <div class="error-shell">
        <p class="eyebrow">LifeQuest</p>
        <h1 class="hero-title">日文學習儀表板暫時無法使用</h1>
        <p class="hero-copy">${escapeHtml(state.error)}</p>
      </div>
    `;
    return;
  }

  if (!state.dashboard) {
    root.innerHTML = `
      <div class="error-shell">
        <p class="eyebrow">LifeQuest</p>
        <h1 class="hero-title">日文學習儀表板暫時無法使用</h1>
        <p class="hero-copy">後端沒有回傳儀表板資料。</p>
      </div>
    `;
    return;
  }

  const dashboard = state.dashboard;
  const ankiToday = dashboard.anki_today;
  const reviewedToday = dashboard.reviewed_today;
  const pulse = dashboard.pulse;
  const historyDays = dashboard.history.days ?? [];
  const difficultCards = dashboard.difficult_cards ?? [];
  const japaneseSessions = dashboard.japanese_sessions ?? [];

  root.innerHTML = `
    <main class="page-shell">
      <section class="hero">
        <div class="hero-main">
          <p class="eyebrow">LifeQuest 日文學習</p>
          <h1 class="hero-title">每日 Anki 儀表板</h1>
          <p class="hero-copy">
            這個頁面故意做得很窄：只看今天複習了什麼、哪些量正在累積、哪些卡片可能需要回頭照顧，
            不試圖取代 Anki 本身。
          </p>
        </div>
        <aside class="hero-side">
          <div class="controls">
            <div class="field-group">
              <label for="dashboard-date">查看日期</label>
              <input id="dashboard-date" type="date" value="${escapeAttribute(state.selectedDate)}" />
            </div>
          </div>
          <div class="button-row">
            <button type="button" id="refresh-dashboard">重新整理</button>
            <a class="ghost" href="/learning/japanese/dashboard?date=${encodeURIComponent(state.selectedDate)}">開啟 JSON</a>
          </div>
          <div class="hero-stat-list">
            <div class="hero-stat">
              <span>目標日期</span>
              <strong>${formatDate(dashboard.target_date)}</strong>
            </div>
            <div class="hero-stat">
              <span>同步狀態</span>
              <strong>${formatSyncStatus(ankiToday.sync_status)}</strong>
            </div>
            <div class="hero-stat">
              <span>今日摘要</span>
              <strong>${buildAnkiSummary(ankiToday, reviewedToday)}</strong>
            </div>
          </div>
        </aside>
      </section>

      <section class="layout">
        <div class="summary-grid">
          ${metricCard("複習次數", ankiToday.reviews, "設定牌組範圍內的 Anki 複習事件總數。")}
          ${metricCard("碰過卡片", reviewedToday.total_unique_cards, "今天實際碰過的卡片數，包含新學習與複習。")}
          ${metricCard("日文分鐘", dashboard.japanese_minutes, `Anki 之外額外記錄了 ${dashboard.japanese_session_count} 段日文學習。`)}
          ${metricCard("待處理卡片", ankiToday.due_count, `新卡 ${ankiToday.new_due_count}，學習中 ${ankiToday.learn_due_count}，複習 ${ankiToday.review_due_count}`)}
          ${metricCard("連續天數", ankiToday.streak_days, "明天再碰一次日文，就能把鏈條接住。")}
        </div>

        <div class="two-up">
          <section class="panel">
            <div class="section-head">
              <div>
                <h2 class="section-title">Anki 按鈕分布</h2>
                <p class="section-subtitle">比泛用的正確率更誠實，能看出今天卡片是順還是卡。</p>
              </div>
            </div>
            <div class="bar-stack">
              ${renderButtonBar("重來（Again）", ankiToday.again_count, ankiToday.reviews, "fill-again")}
              ${renderButtonBar("困難（Hard）", ankiToday.hard_count, ankiToday.reviews, "fill-hard")}
              ${renderButtonBar("普通（Good）", ankiToday.good_count, ankiToday.reviews, "fill-good")}
              ${renderButtonBar("簡單（Easy）", ankiToday.easy_count, ankiToday.reviews, "fill-easy")}
            </div>
            <div class="status-banner" style="margin-top: 16px;">
              <strong>建議：</strong> ${buildAnkiRecommendation(ankiToday)}
              <br />
              <strong>同步提醒：</strong> ${buildSyncHint(ankiToday)}
            </div>
          </section>

          <section class="panel">
            <div class="section-head">
              <div>
                <h2 class="section-title">今日學習脈絡</h2>
                <p class="section-subtitle">除了卡片數量之外，LifeQuest 對今天日文學習狀態的理解。</p>
              </div>
            </div>
            <div class="cards-list">
              <div class="card-note">
                <div class="card-note-title">學習摘要</div>
                <div class="card-note-meta">${buildPulseSummary(dashboard, ankiToday, reviewedToday)}</div>
              </div>
              <div class="card-note">
                <div class="card-note-title">明日優先事項</div>
                <div class="card-note-meta">${buildTomorrowPriority(pulse, ankiToday)}</div>
              </div>
              <div class="card-note">
                <div class="card-note-title">牌組範圍</div>
                <div class="card-note-meta">${escapeHtml(formatDeckScope(reviewedToday))}</div>
              </div>
            </div>
          </section>
        </div>

        <section class="panel">
          <div class="section-head">
            <div>
              <h2 class="section-title">近 7 天</h2>
              <p class="section-subtitle">先看複習量，再看非重來率。</p>
            </div>
          </div>
          ${
            historyDays.length
              ? `
                <div class="history-grid">
                  <div class="history-bars">
                    ${renderHistoryBars(historyDays)}
                  </div>
                  <div class="chip-row">
                    <span class="chip">總複習：${dashboard.history.total_reviews}</span>
                    <span class="chip">平均非重來：${formatPercent(dashboard.history.average_accuracy)}</span>
                    <span class="chip">最佳日期：${escapeHtml(dashboard.history.best_review_day ?? "無資料")}</span>
                  </div>
                </div>
              `
              : `<div class="empty-banner"><strong>還沒有歷史資料。</strong> 連續幾天執行 <span class="mono">import-anki</span> 後，這裡就會長出趨勢。</div>`
          }
        </section>

        <div class="two-up">
          <section class="panel">
            <div class="section-head">
              <div>
                <h2 class="section-title">今日卡片</h2>
                <p class="section-subtitle">以卡片為單位整理今天碰過的內容，重複複習會合併成同一列。</p>
              </div>
            </div>
            ${
              reviewedToday.cards?.length
                ? `
                  <div class="table-shell">
                    <table>
                      <thead>
                        <tr>
                          <th>時間</th>
                          <th>卡片</th>
                          <th>牌組</th>
                          <th>次數</th>
                          <th>按鈕</th>
                        </tr>
                      </thead>
                      <tbody>
                        ${reviewedToday.cards
                          .map(
                            (card) => `
                              <tr>
                                <td class="mono">${formatTime(card.last_reviewed_at)}</td>
                                <td>${escapeHtml(card.label)}</td>
                                <td>${escapeHtml(shortDeck(card.deck_name))}</td>
                                <td>${card.review_count}</td>
                                <td class="mono">重${card.again_count} 困${card.hard_count} 普${card.good_count} 易${card.easy_count}</td>
                              </tr>
                            `,
                          )
                          .join("")}
                      </tbody>
                    </table>
                  </div>
                `
                : `<div class="empty-banner"><strong>找不到今日卡片。</strong> 通常代表這天在目前牌組範圍內沒有 Anki 複習紀錄。</div>`
            }
          </section>

          <section class="panel">
            <div class="section-head">
              <div>
                <h2 class="section-title">薄弱卡片</h2>
                <p class="section-subtitle">近期快照中反覆出問題的卡片，適合拿來做小範圍補強。</p>
              </div>
            </div>
            ${
              difficultCards.length
                ? `
                  <div class="cards-list">
                    ${difficultCards
                      .map(
                        (card) => `
                          <article class="card-note">
                            <div class="card-note-head">
                              <div>
                                <div class="card-note-title">${escapeHtml(card.label)}</div>
                                <div class="card-note-meta">最近出現：${formatDate(card.last_seen_on)}</div>
                              </div>
                              <div class="chip">${card.hit_count} 次</div>
                            </div>
                          </article>
                        `,
                      )
                      .join("")}
                  </div>
                `
                : `<div class="empty-banner"><strong>近期沒有困難卡片。</strong> 這是很舒服的問題，先收下。</div>`
            }
          </section>
        </div>

        <section class="panel">
          <div class="section-head">
            <div>
              <h2 class="section-title">額外日文學習紀錄</h2>
              <p class="section-subtitle">文法、閱讀、聽力或 Anki 之外的練習可以放在這裡。</p>
            </div>
          </div>
          ${
            japaneseSessions.length
              ? `
                <div class="sessions-list">
                  ${japaneseSessions
                    .map(
                      (session) => `
                        <article class="session-note">
                          <div class="session-note-head">
                            <div>
                              <div class="session-note-title">${escapeHtml(session.summary)}</div>
                              <div class="session-note-meta">
                                ${session.duration_minutes} 分鐘，${escapeHtml(formatSessionSource(session.source))}，${formatDateTime(session.started_at)}
                              </div>
                            </div>
                            <div class="chip">${escapeHtml(session.tags?.length ? session.tags.join(", ") : "手動紀錄")}</div>
                          </div>
                        </article>
                      `,
                    )
                    .join("")}
                </div>
              `
              : `<div class="empty-banner"><strong>還沒有額外日文學習紀錄。</strong> Anki 已經接上了；這塊之後可以放文法、閱讀、聽力或寫作練習。</div>`
          }
        </section>
      </section>
    </main>
  `;

  bindControls();
}

function bindControls() {
  const dateInput = document.getElementById("dashboard-date");
  const refreshButton = document.getElementById("refresh-dashboard");

  if (dateInput) {
    dateInput.addEventListener("change", (event) => {
      state.selectedDate = event.target.value;
      void loadDashboard();
    });
  }

  if (refreshButton) {
    refreshButton.addEventListener("click", () => {
      void loadDashboard();
    });
  }
}

function metricCard(label, value, helpText) {
  return `
    <article class="panel metric-card">
      <div class="metric-label">${escapeHtml(label)}</div>
      <div class="metric-value">${value}</div>
      <div class="metric-help">${escapeHtml(helpText)}</div>
    </article>
  `;
}

function renderButtonBar(label, value, total, fillClass) {
  const percentage = total > 0 ? (value / total) * 100 : 0;
  return `
    <div class="bar-row">
      <div class="bar-row-label">${escapeHtml(label)}</div>
      <div class="bar-track">
        <div class="bar-fill ${fillClass}" style="width: ${percentage}%"></div>
      </div>
      <div class="mono">${value}</div>
    </div>
  `;
}

function renderHistoryBars(historyDays) {
  const maxReviews = Math.max(...historyDays.map((entry) => entry.reviews), 1);
  return historyDays
    .map((day) => {
      const height = Math.max((day.reviews / maxReviews) * 100, day.reviews > 0 ? 12 : 4);
      return `
        <div class="history-day">
          <div class="history-day-top">${formatShortDate(day.snapshot_date)}</div>
          <div class="history-column-shell">
            <div class="history-column" style="height: ${height}%"></div>
          </div>
          <div class="history-day-bottom">
            <div class="history-value">${day.reviews}</div>
            <div class="history-rate">${formatPercent(day.non_again_rate)}</div>
          </div>
        </div>
      `;
    })
    .join("");
}

function buildAnkiSummary(ankiToday, reviewedToday) {
  if (!ankiToday.reviews) {
    return "今天還沒有 Anki 複習紀錄。";
  }

  const againText = ankiToday.again_count
    ? `按重來 ${ankiToday.again_count} 次`
    : "沒有按重來";
  return `${ankiToday.reviews} 次複習，${reviewedToday.total_unique_cards} 張卡片，${againText}。`;
}

function buildAnkiRecommendation(ankiToday) {
  if (!ankiToday.reviews) {
    return "先做一小段 Anki，把今天的日文節奏點起來。";
  }
  if (ankiToday.again_count > 0) {
    return "今天有按重來的卡片，明天可以先看薄弱卡片，再開始新卡。";
  }
  if (ankiToday.hard_count >= 3) {
    return "困難偏多，明天先用短回合複習，不急著加太多新卡。";
  }
  return "節奏很穩，明天維持一段短 Anki，再搭配一點文法或閱讀。";
}

function buildSyncHint(ankiToday) {
  if (ankiToday.sync_status === "snapshot_fresh") {
    return "快照是新的；如果晚點又用手機複習，記得讓桌面 Anki 同步後再匯入。";
  }
  if (ankiToday.sync_status === "snapshot_missing") {
    return "目前沒有快照，請先執行 Anki 匯入流程。";
  }
  if (ankiToday.sync_status === "disabled") {
    return "Anki 整合目前未啟用，請檢查 ANKI_ENABLED 設定。";
  }
  return "若手機剛同步過，請確認桌面 Anki 已開啟並完成同步。";
}

function buildPulseSummary(dashboard, ankiToday, reviewedToday) {
  const sessionText = dashboard.japanese_minutes
    ? `Anki 之外還有 ${dashboard.japanese_minutes} 分鐘日文學習`
    : "Anki 之外尚未記錄其他日文學習";
  return `今天有 ${ankiToday.reviews} 次 Anki 複習、${reviewedToday.total_unique_cards} 張卡片；${sessionText}。`;
}

function buildTomorrowPriority(pulse, ankiToday) {
  if (pulse?.tomorrow_priority && containsCjk(pulse.tomorrow_priority)) {
    return escapeHtml(pulse.tomorrow_priority);
  }
  if (!ankiToday.reviews) {
    return "明天先完成一段短 Anki，讓日文學習重新進入節奏。";
  }
  return "明天先保留一段短 Anki，再挑一個文法、閱讀或聽力小任務補強。";
}

function formatSyncStatus(value) {
  const labels = {
    snapshot_fresh: "快照已更新",
    snapshot_stale: "快照可能偏舊",
    snapshot_missing: "尚未匯入快照",
    disabled: "Anki 未啟用",
    unavailable: "無法連線",
  };
  return labels[value] ?? value ?? "無資料";
}

function formatDeckScope(reviewedToday) {
  if (reviewedToday.configured_decks?.length) {
    return reviewedToday.configured_decks.join(", ");
  }
  if (reviewedToday.decks?.length) {
    return reviewedToday.decks.join(", ");
  }
  return "未設定";
}

function formatSessionSource(value) {
  const labels = {
    manual: "手動紀錄",
    anki: "Anki",
    github: "GitHub",
  };
  return labels[value] ?? value ?? "未知來源";
}

function currentDateString() {
  const now = new Date();
  const offset = now.getTimezoneOffset();
  const localDate = new Date(now.getTime() - offset * 60000);
  return localDate.toISOString().slice(0, 10);
}

function formatDate(value) {
  if (!value) {
    return "無資料";
  }
  return new Date(`${value}T00:00:00`).toLocaleDateString(LOCALE, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function formatShortDate(value) {
  if (!value) {
    return "無資料";
  }
  return new Date(`${value}T00:00:00`).toLocaleDateString(LOCALE, {
    month: "short",
    day: "numeric",
  });
}

function formatTime(value) {
  return new Date(value).toLocaleTimeString(LOCALE, {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDateTime(value) {
  return new Date(value).toLocaleString(LOCALE, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatPercent(value) {
  return typeof value === "number" ? `${value.toFixed(1)}%` : "無資料";
}

function shortDeck(value) {
  if (!value) {
    return "未設定";
  }
  const parts = value.split("::");
  return parts.length > 2 ? parts.slice(-2).join(" / ") : value;
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

function escapeAttribute(value) {
  return escapeHtml(value);
}
