const state = {
  meetings: [],
  selectedMeetingIndex: 0,
  selectedEventIndex: 0,
  analysisMode: "predictor",
  filterText: "",
  sortField: "number",
};

// Keep the stats pane anchored on stable/jockey strike rate while still factoring wet-track profile.
const STATS_INSIGHT_WEIGHTS = Object.freeze({
  trainerJockeyWin: 2,
  wetPlaceProfile: 1,
});
const TOTAL_STATS_INSIGHT_WEIGHT = STATS_INSIGHT_WEIGHTS.trainerJockeyWin + STATS_INSIGHT_WEIGHTS.wetPlaceProfile;

const refs = {
  dateInput: document.getElementById("dateInput"),
  localToggle: document.getElementById("localToggle"),
  loadButton: document.getElementById("loadButton"),
  sourceBadge: document.getElementById("sourceBadge"),
  statusText: document.getElementById("statusText"),
  meetingCount: document.getElementById("meetingCount"),
  meetingList: document.getElementById("meetingList"),
  emptyState: document.getElementById("emptyState"),
  meetingView: document.getElementById("meetingView"),
  meetingHeader: document.getElementById("meetingHeader"),
  eventMeta: document.getElementById("eventMeta"),
  eventButtons: document.getElementById("eventButtons"),
  eventDetails: document.getElementById("eventDetails"),
  analysisSelect: document.getElementById("analysisSelect"),
  analysisBody: document.getElementById("analysisBody"),
  insightsPane: document.getElementById("insightsPane"),
  selectionSection: document.getElementById("selectionSection"),
  selectionList: document.getElementById("selectionList"),
  filterInput: document.getElementById("filterInput"),
  sortSelect: document.getElementById("sortSelect"),
};

let countdownInterval = null;

document.addEventListener("DOMContentLoaded", () => {
  refs.dateInput.value = new Date().toISOString().slice(0, 10);
  refs.loadButton.addEventListener("click", loadMeetings);
  refs.analysisSelect.addEventListener("change", (event) => {
    state.analysisMode = event.target.value;
    renderMeeting();
  });

  document.getElementById("prevDateButton").addEventListener("click", () => navigateDate(-1));
  document.getElementById("nextDateButton").addEventListener("click", () => navigateDate(1));

  refs.filterInput.addEventListener("input", (e) => {
    state.filterText = e.target.value;
    const event = currentEvent();
    refs.selectionList.innerHTML = renderSelections(event);
    wireInteractiveElements();
  });

  refs.sortSelect.addEventListener("change", (e) => {
    state.sortField = e.target.value;
    const event = currentEvent();
    refs.selectionList.innerHTML = renderSelections(event);
    wireInteractiveElements();
  });

  document.addEventListener("keydown", handleKeyboard);
  loadMeetings();
});

function navigateDate(offset) {
  const current = refs.dateInput.value || new Date().toISOString().slice(0, 10);
  const date = new Date(current + "T12:00:00");
  date.setDate(date.getDate() + offset);
  refs.dateInput.value = date.toISOString().slice(0, 10);
  loadMeetings();
}

function handleKeyboard(event) {
  if (["INPUT", "SELECT", "TEXTAREA"].includes(event.target.tagName)) return;
  const meeting = currentMeeting();
  const events = meeting ? (Array.isArray(meeting.events) ? meeting.events : []) : [];
  if (event.key === "ArrowRight") {
    if (state.selectedEventIndex < events.length - 1) {
      state.selectedEventIndex++;
      renderMeeting();
    }
  } else if (event.key === "ArrowLeft") {
    if (state.selectedEventIndex > 0) {
      state.selectedEventIndex--;
      renderMeeting();
    }
  } else if (event.key === "ArrowDown") {
    if (state.selectedMeetingIndex < state.meetings.length - 1) {
      state.selectedMeetingIndex++;
      state.selectedEventIndex = 0;
      renderMeetingList();
      renderMeeting();
    }
  } else if (event.key === "ArrowUp") {
    if (state.selectedMeetingIndex > 0) {
      state.selectedMeetingIndex--;
      state.selectedEventIndex = 0;
      renderMeetingList();
      renderMeeting();
    }
  }
}

async function loadMeetings() {
  setStatus("Loading meetings\u2026");
  refs.loadButton.disabled = true;
  if (countdownInterval) {
    clearInterval(countdownInterval);
    countdownInterval = null;
  }

  try {
    const date = refs.dateInput.value || new Date().toISOString().slice(0, 10);
    const local = refs.localToggle.checked ? "1" : "0";
    const response = await fetch(`/api/meetings?date=${encodeURIComponent(date)}&local=${local}`);
    if (!response.ok) {
      throw new Error(await response.text());
    }

    const payload = await response.json();
    state.meetings = Array.isArray(payload.meetings) ? payload.meetings : [];
    state.selectedMeetingIndex = 0;
    state.selectedEventIndex = 0;
    refs.sourceBadge.textContent = payload.source || "unknown";
    refs.meetingCount.textContent = `${state.meetings.length} loaded`;
    setStatus(`Loaded ${state.meetings.length} meetings for ${payload.date}`);
    renderMeetingList();
    renderMeeting();
  } catch (error) {
    console.error(error);
    setStatus(String(error.message || error), true);
    refs.meetingList.innerHTML = "";
    refs.insightsPane.innerHTML = "";
    refs.selectionList.innerHTML = "";
    refs.emptyState.classList.add("visible");
    refs.meetingView.classList.add("hidden");
    refs.selectionSection.classList.add("hidden");
  } finally {
    refs.loadButton.disabled = false;
  }
}

function renderMeetingList() {
  const groups = new Map();
  state.meetings.forEach((meeting, index) => {
    const group = meeting.state || "Other";
    if (!groups.has(group)) {
      groups.set(group, []);
    }
    groups.get(group).push({ meeting, index });
  });

  refs.meetingList.innerHTML = "";
  for (const [stateName, items] of groups.entries()) {
    const label = document.createElement("div");
    label.className = "group-label";
    label.textContent = stateName;
    refs.meetingList.appendChild(label);

    items.forEach(({ meeting, index }) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `meeting-button${state.selectedMeetingIndex === index ? " active" : ""}`;
      button.innerHTML = `
        <strong>${escapeHtml(meeting.name || "Unknown meeting")}</strong>
        <span class="subtle">${escapeHtml((meeting.events || []).length)} races \xb7 ${escapeHtml(meeting.rail_position || "Rail n/a")}</span>
      `;
      button.addEventListener("click", () => {
        state.selectedMeetingIndex = index;
        state.selectedEventIndex = 0;
        renderMeetingList();
        renderMeeting();
      });
      refs.meetingList.appendChild(button);
    });
  }
}

function currentMeeting() {
  return state.meetings[state.selectedMeetingIndex];
}

function currentEvent() {
  const meeting = currentMeeting();
  if (!meeting) return null;
  const events = Array.isArray(meeting.events) ? meeting.events : [];
  return events[state.selectedEventIndex] || events[0] || null;
}

function renderMeeting() {
  const meeting = currentMeeting();
  if (!meeting) {
    refs.emptyState.classList.add("visible");
    refs.meetingView.classList.add("hidden");
    refs.selectionSection.classList.add("hidden");
    return;
  }

  refs.emptyState.classList.remove("visible");
  refs.meetingView.classList.remove("hidden");
  refs.selectionSection.classList.remove("hidden");

  const events = Array.isArray(meeting.events) ? meeting.events : [];
  const event = events[state.selectedEventIndex] || events[0];
  if (!event) {
    refs.eventButtons.innerHTML = "";
    refs.eventDetails.innerHTML = "<p class='subtle'>No events available.</p>";
    refs.analysisBody.innerHTML = "";
    refs.insightsPane.innerHTML = "";
    refs.selectionList.innerHTML = "";
    refs.selectionSection.classList.add("hidden");
    return;
  }
  state.selectedEventIndex = events.indexOf(event);

  refs.meetingHeader.innerHTML = `
    <div class="meeting-title">
      <div>
        <h2>${escapeHtml(meeting.name || "Unknown meeting")}</h2>
        <p class="subtle">${escapeHtml(meeting.state || "Unknown state")} \xb7 ${escapeHtml(meeting.slug || "")}</p>
      </div>
      <div class="meeting-meta">
        ${chip("Rail", meeting.rail_position || "n/a")}
        ${chip("Events", String(events.length))}
      </div>
    </div>
  `;

  refs.eventMeta.textContent = `${event.name || "Race"} \xb7 ${event.time || "TBC"}`;
  refs.eventButtons.innerHTML = events.map((item, index) => `
    <button type="button" class="event-button${index === state.selectedEventIndex ? " active" : ""}" data-index="${index}">
      R${escapeHtml(String(item.event_number || index + 1))}
    </button>
  `).join("");
  refs.eventButtons.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedEventIndex = Number(button.dataset.index || 0);
      renderMeeting();
    });
  });

  const firstWinOdds = findOdds((event.selections || [])[0]?.odds, "Win");
  const mktPct = firstWinOdds?.market_percentage;
  const mktChip = mktPct
    ? tonedChip("Market", `${formatFloat(mktPct)}%`, "Win book percentage", mktPct > 120 ? "danger" : mktPct > 110 ? "warning" : "success")
    : "";

  refs.eventDetails.innerHTML = `
    <div class="event-highlight-grid">
      <div class="summary-card tone-primary" title="${escapeHtmlAttribute(event.time || "TBC")}">
        <span class="summary-label">Countdown</span>
        <strong><span data-event-time="${escapeHtmlAttribute(event.time || "")}">${escapeHtml(formatCountdown(event.time))}</span></strong>
        <span class="summary-subtle">${escapeHtml(event.time || "TBC")}</span>
      </div>
      ${summaryCard("Prize", formatCurrency(event.prize_money), `${formatNumber(event.starters)} runners`, "purple")}
      ${summaryCard("Pace", formatFloat(event.pace), tooltipText(event.comments), "warning")}
      ${summaryCard("Track", `${event.track_condition || "?"} \xb7 ${event.track_type || "?"}`, event.weather || "n/a", "success")}
    </div>
    <div class="chip-row">
      ${tonedChip("Distance", `${formatNumber(event.distance)}m`, "", "primary")}
      ${tonedChip("Class", event._class || "n/a", "", "purple")}
      ${tonedChip("Weather", event.weather || "n/a", "", "success")}
      ${tonedChip("Starters", formatNumber(event.starters), "", "warning")}
      ${mktChip}
    </div>
  `;

  refs.analysisSelect.value = state.analysisMode;
  refs.analysisBody.innerHTML = renderAnalysis(event);
  refs.insightsPane.innerHTML = renderInsights(event);
  refs.selectionList.innerHTML = renderSelections(event);
  wireInteractiveElements();

  if (countdownInterval) clearInterval(countdownInterval);
  countdownInterval = setInterval(() => {
    document.querySelectorAll("[data-event-time]").forEach((el) => {
      el.textContent = formatCountdown(el.dataset.eventTime);
    });
  }, 1000);
}

function renderAnalysis(event) {
  const selections = [...(event.selections || [])];
  if (state.analysisMode === "speed") {
    selections.sort((left, right) => (right.prediction?.speed || 0) - (left.prediction?.speed || 0));
    return renderTable(
      ["Horse", "Early", "Finish", "Position"],
      selections.slice(0, 10).map((selection) => [
        selection.name,
        formatFloat(selection.prediction?.speed),
        formatFloat(selection.prediction?.finish_speed),
        selection.prediction?.normalized_speed_position || "",
      ]),
    );
  }

  if (state.analysisMode === "stats") {
    selections.sort((left, right) => (right.trainer_jockey_win_percentage || 0) - (left.trainer_jockey_win_percentage || 0));
    return renderTable(
      ["Horse", "Train/Jock %", "Avg Prize", "Wet W/P %"],
      selections.slice(0, 10).map((selection) => [
        selection.name,
        percent(selection.trainer_jockey_win_percentage),
        formatCurrency(selection.average_prize_money),
        `${percent(selection.wet_runs_win_percentage)} / ${percent(selection.wet_runs_place_percentage)}`,
      ]),
    );
  }

  selections.sort((left, right) => (right.punters_edge || 0) - (left.punters_edge || 0));
  return renderTable(
    ["Horse", "Edge", "Model Rank", "Win Chance"],
    selections.slice(0, 10).map((selection) => [
      selection.name,
      formatFloat(selection.punters_edge),
      formatNumber(selection.prediction?.model_rank),
      percent(selection.prediction?.winning_chance),
    ]),
  );
}

// ─── Phase 2: filter + sort ───────────────────────────────────────────────────

function sortedFilteredSelections(selections) {
  let list = [...(selections || [])];

  const q = (state.filterText || "").trim().toLowerCase();
  if (q) {
    list = list.filter((s) => (s.name || "").toLowerCase().includes(q));
  }

  switch (state.sortField) {
    case "edge":
      list.sort((a, b) => safeNumber(b.punters_edge) - safeNumber(a.punters_edge));
      break;
    case "predictor":
      list.sort((a, b) => safeNumber(b.predictor_score) - safeNumber(a.predictor_score));
      break;
    case "speed":
      list.sort((a, b) => safeNumber(b.prediction?.speed) - safeNumber(a.prediction?.speed));
      break;
    case "odds": {
      list.sort((a, b) => {
        const aPrice = safeNumber(findOdds(a.odds, "Win")?.price);
        const bPrice = safeNumber(findOdds(b.odds, "Win")?.price);
        if (!aPrice && !bPrice) return 0;
        if (!aPrice) return 1;
        if (!bPrice) return -1;
        return aPrice - bPrice;
      });
      break;
    }
    default:
      list.sort((a, b) => safeNumber(a.number) - safeNumber(b.number));
  }

  return list;
}

function renderSelections(event) {
  if (!event) return "";
  const selections = sortedFilteredSelections(event.selections);
  return selections.map((selection, selectionIndex) => {
    const runs = Array.isArray(selection.runs) ? selection.runs.slice(0, 10) : [];
    const winOdds = findOdds(selection.odds, "Win");
    const placeOdds = findOdds(selection.odds, "Place");
    const edgeScore = scoreClass(selection.punters_edge);
    const trainerTitle = tooltipText(selection.trainer?.name, [
      `Win ${percent(selection.trainer?.last_year_win_percentage)}`,
      `Place ${percent(selection.trainer?.last_year_place_percentage)}`,
      selection.trainer?.location,
    ]);
    const jockeyTitle = tooltipText(selection.jockey?.name, [
      `Win ${percent(selection.jockey?.last_year_win_percentage)}`,
      `Place ${percent(selection.jockey?.last_year_place_percentage)}`,
    ]);
    const movLabel = winOdds
      ? winOdds.movement > 0
        ? `\u25b2 ${formatFloat(winOdds.movement)}`
        : winOdds.movement < 0
          ? `\u25bc ${formatFloat(Math.abs(winOdds.movement))}`
          : "\u2014 Firm"
      : "";
    const winTitle = movLabel ? `Movement: ${movLabel}` : "";

    return `
      <details class="selection-card edge-${edgeScore}">
        <summary class="selection-summary" data-copy="${escapeHtmlAttribute(copyText(selection, winOdds, placeOdds))}">
          <div class="selection-topline">
            <span class="selection-number">${escapeHtml(formatNumber(selection.number))}</span>
            <div>
              <strong>${escapeHtml(selection.name || "Unknown runner")}</strong>
              <span class="subtle">${escapeHtml(selection.prediction?.normalized_speed_position || "No speed tag")}</span>
            </div>
          </div>
          <div class="selection-summary-grid">
            ${tonedChip("Win", formatPrice(winOdds?.price), winTitle, "success")}
            ${tonedChip("Place", formatPrice(placeOdds?.price), "", "primary")}
            ${tonedChip("Barrier", formatNumber(selection.barrier), "", "warning")}
            ${tonedChip("Weight", formatFloat(selection.weight), "", "purple")}
            ${tonedChip("ROI", percent(selection.roi), "", percentageTone(selection.roi))}
            ${tonedChip("Prep", formatNumber(selection.runs_since_spell), "", "primary")}
            ${chip("Edge", formatFloat(selection.punters_edge), "", edgeScore)}
          </div>
        </summary>
        <div class="selection-body">
          <div class="detail-grid">
            <div class="stack">
              ${chip("Trainer", selection.trainer?.name || "n/a", trainerTitle)}
              ${chip("Jockey", selection.jockey?.name || "n/a", jockeyTitle)}
              ${chip("Train/Jock", percent(selection.trainer_jockey_win_percentage))}
              ${chip("Comments", truncate(selection.comments || "No comments"), tooltipText(selection.comments, selection.external_comments ? Object.entries(selection.external_comments).map(([brand, value]) => `${brand}: ${value}`) : []))}
            </div>
            <div class="stack">
              ${chip("Record", `${formatNumber(selection.total_wins)}W / ${formatNumber(selection.total_places)}P / ${formatNumber(selection.total_runs)}R`)}
              ${chip("Wet", `${percent(selection.wet_runs_win_percentage)} / ${percent(selection.wet_runs_place_percentage)}`)}
              ${chip("Avg Prize", formatCurrency(selection.average_prize_money))}
              ${chip("Gear", selection.gear_changes || "No change", tooltipText(selection.gear_changes || "No gear changes"))}
            </div>
          </div>
          ${renderPreparationStats(selection)}
          ${renderPredictorRatings(selection)}
          ${renderOddsFluctuations(selection)}
          ${renderRunsTable(runs, selectionIndex)}
        </div>
      </details>
    `;
  }).join("");
}

// ─── Phase 2: preparation stats ──────────────────────────────────────────────

function renderPreparationStats(selection) {
  const ps = selection.preparation_stats;
  if (!ps) return "";
  const hasData = (
    safeNumber(ps.first_up_win_percentage) > 0 ||
    safeNumber(ps.second_up_win_percentage) > 0 ||
    safeNumber(ps.third_up_win_percentage) > 0 ||
    safeNumber(ps.nth_up_win_percentage) > 0
  );
  if (!hasData) return "";

  return `
    <div class="detail-subsection">
      <span class="subsection-label">Preparation Profile</span>
      <div class="prep-grid">
        ${renderPrepRow("1st Up", ps.first_up_win_percentage, ps.first_up_average_difference, ps.first_up_stdev_difference)}
        ${renderPrepRow("2nd Up", ps.second_up_win_percentage, ps.second_up_average_difference, ps.second_up_stdev_difference)}
        ${renderPrepRow("3rd Up", ps.third_up_win_percentage, ps.third_up_average_difference, ps.third_up_stdev_difference)}
        ${renderPrepRow("Nth Up", ps.nth_up_win_percentage, ps.nth_up_average_difference, ps.nth_up_stdev_difference)}
      </div>
    </div>
  `;
}

function renderPrepRow(label, winPct, avgDiff, stdevDiff) {
  const pct = safeNumber(winPct) * 100;
  const diff = safeNumber(avgDiff);
  const stdev = safeNumber(stdevDiff);
  const tone = pct >= 30 ? "success" : pct >= 10 ? "warning" : "neutral";
  const diffSign = diff > 0 ? "+" : "";
  return `
    <div class="prep-row">
      <span class="prep-label subtle">${escapeHtml(label)}</span>
      <span class="chip chip-tone-${tone} prep-win">${escapeHtml(percent(pct))} win</span>
      <span class="subtle">${escapeHtml(diffSign + formatFloat(diff))}s avg · \xb1${escapeHtml(formatFloat(stdev))}s</span>
    </div>
  `;
}

// ─── Phase 2: predictor ratings breakdown ─────────────────────────────────────

function renderPredictorRatings(selection) {
  const ratings = selection.predictor_ratings;
  if (!ratings) return "";
  const entries = Object.entries(ratings).filter(([, v]) => safeNumber(v) !== 0);
  if (entries.length === 0) return "";

  const maxVal = Math.max(...entries.map(([, v]) => Math.abs(safeNumber(v))), 0);
  return `
    <div class="detail-subsection">
      <span class="subsection-label">Predictor Components</span>
      <div class="predictor-ratings">
        ${entries.map(([key, value]) => {
          const numVal = safeNumber(value);
          const width = maxVal > 0 ? Math.max(6, (Math.abs(numVal) / maxVal) * 100) : 6;
          const label = key.replaceAll("_", "\u00a0");
          return `
            <div class="rating-row">
              <span class="rating-label subtle">${escapeHtml(label)}</span>
              <span class="meter"><span class="meter-fill tone-purple" style="width:${width}%"></span></span>
              <span class="rating-value">${escapeHtml(formatFloat(numVal))}</span>
            </div>
          `;
        }).join("")}
      </div>
    </div>
  `;
}

// ─── Phase 2: odds price history ──────────────────────────────────────────────

function renderOddsFluctuations(selection) {
  const winOdds = findOdds(selection.odds, "Win");
  const placeOdds = findOdds(selection.odds, "Place");
  const flucts = (winOdds?.fluctuations || []).slice().reverse().slice(0, 12);
  if (flucts.length < 2) return "";

  const prices = flucts.map((f) => safeNumber(f.price));
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const range = maxPrice - minPrice;

  const movement = safeNumber(winOdds.movement || 0);
  const movClass = movement > 0 ? "movement-up" : movement < 0 ? "movement-down" : "";
  const movLabel = movement > 0
    ? `<span class="movement-up">\u25b2 ${escapeHtml(formatFloat(movement))}</span>`
    : movement < 0
      ? `<span class="movement-down">\u25bc ${escapeHtml(formatFloat(Math.abs(movement)))}</span>`
      : `<span class="muted">\u2014 Firm</span>`;

  return `
    <div class="detail-subsection">
      <div class="subsection-label-row">
        <span class="subsection-label">Price History (Win)</span>
        ${movLabel}
        ${placeOdds ? `<span class="muted">Place: ${escapeHtml(formatPrice(placeOdds.price))}</span>` : ""}
      </div>
      <div class="fluct-chart">
        ${flucts.map((f) => {
          const h = range > 0 ? Math.max(18, Math.min(100, ((maxPrice - safeNumber(f.price)) / range) * 78 + 18)) : 50;
          const time = (f.time || "").split(" ")[1] || f.time || "";
          const tone = movClass || "primary";
          return `<div class="fluct-bar tone-${escapeHtml(tone)}" style="height:${h.toFixed(1)}%" title="${escapeHtmlAttribute(formatPrice(f.price) + " @ " + time)}"><span class="fluct-price">${escapeHtml(formatPrice(f.price))}</span></div>`;
        }).join("")}
      </div>
    </div>
  `;
}

// ─── Phase 2: enhanced form runs table ───────────────────────────────────────

function renderRunsTable(runs, selectionIndex) {
  if (runs.length === 0) return "";
  return renderTable(
    ["Date", "Venue", "Pos", "Price", "Margin", "Dist", "Cond", "Wt", "Rivals", "L800", "L600", "L400", "L200", "Tempo"],
    runs.map((run, runIndex) => [
      `<span title="${escapeHtmlAttribute([run.video_comment, run.video_note].filter(Boolean).join("\n"))}" class="run-date-cell">${escapeHtml(run.meeting_date || "")}${run.video_comment ? " \ud83d\udcac" : ""}</span>`,
      `${escapeHtml(run.venue || run.meeting_name || "")}${run.is_trial ? " <em>(Trial)</em>" : ""}`,
      positionCell(run),
      escapeHtml(formatRunPrice(run)),
      escapeHtml(formatRunMargin(run)),
      `${escapeHtml(formatNumber(run.distance))}m`,
      escapeHtml(run.track_condition || ""),
      escapeHtml(formatFloat(run.weight)),
      rivalsCell(run),
      toggleButton(`l800-${selectionIndex}-${runIndex}`, splitDisplay(run, "runner_split_l800"), benchmarkDisplay(run, "runner_time_difference_l800", "runner_race_position_l800", "runner_meeting_position_l800")),
      toggleButton(`l600-${selectionIndex}-${runIndex}`, splitDisplay(run, "runner_split_l600"), benchmarkDisplay(run, "runner_time_difference_l600", "runner_race_position_l600", "runner_meeting_position_l600")),
      toggleButton(`l400-${selectionIndex}-${runIndex}`, splitDisplay(run, "runner_split_l400"), benchmarkDisplay(run, "runner_time_difference_l400", "runner_race_position_l400", "runner_meeting_position_l400")),
      toggleButton(`l200-${selectionIndex}-${runIndex}`, splitDisplay(run, "runner_split_l200"), benchmarkDisplay(run, "runner_time_difference_l200", "runner_race_position_l200", "runner_meeting_position_l200")),
      toggleButton(`tempo-${selectionIndex}-${runIndex}`, run.form_benchmark?.runner_tempo_label || "n/a", formatFloat(run.form_benchmark?.runner_tempo_difference)),
    ]),
  );
}

function positionCell(run) {
  const pos = formatNumber(run.finish_position);
  const starters = safeNumber(run.starters);
  const summaries = Array.isArray(run.position_summaries) ? run.position_summaries : [];
  const keyPoints = [800, 600, 400].map((dist) => {
    const ps = summaries.find((s) => s.distance === dist && s.position !== null && s.position !== undefined);
    return ps ? `${dist}m:\u200b${ps.position}` : null;
  }).filter(Boolean);
  const tooltip = keyPoints.length > 0 ? keyPoints.join("  ") : "";
  const stDesc = starters > 0 ? `/${starters}` : "";
  return `<span class="pos-cell" title="${escapeHtmlAttribute(tooltip)}">${escapeHtml(pos)}${escapeHtml(stDesc)}${tooltip ? " \u2139" : ""}</span>`;
}

function formatRunPrice(run) {
  const open = safeNumber(run.open_price);
  const fluct = safeNumber(run.fluctuation);
  const sp = safeNumber(run.starting_price);
  if (!open && !sp) return "n/a";
  if (fluct && fluct !== open && fluct !== sp) {
    return `$${open.toFixed(1)}/$${fluct.toFixed(1)}/$${sp.toFixed(1)}`;
  }
  return `$${open.toFixed(1)}/$${sp.toFixed(1)}`;
}

function formatRunMargin(run) {
  if (run.margin === null || run.margin === undefined) return "-";
  const margin = safeNumber(run.margin);
  if (margin === 0) {
    const second = safeNumber(run.second_margin);
    return second > 0 ? `+${second.toFixed(2)}` : "0";
  }
  return `${margin.toFixed(2)}`;
}

function rivalsCell(run) {
  const val = safeNumber(run.competitors_won_since);
  if (val === 0) return `<span class="muted">0</span>`;
  return `<span class="rivals-badge" title="${escapeHtmlAttribute(val + " rivals won since this run")}">${escapeHtml(String(val))}</span>`;
}

// ─── Interactions ─────────────────────────────────────────────────────────────

function wireInteractiveElements() {
  document.querySelectorAll("[data-toggle-raw]").forEach((button) => {
    button.addEventListener("click", () => {
      const showingRaw = button.dataset.showing === "raw";
      button.textContent = showingRaw ? button.dataset.benchmark : button.dataset.raw;
      button.dataset.showing = showingRaw ? "benchmark" : "raw";
    });
  });

  document.querySelectorAll(".selection-card summary").forEach((summary) => {
    summary.addEventListener("contextmenu", async (event) => {
      event.preventDefault();
      const text = summary.dataset.copy || "";
      if (!text) {
        return;
      }
      try {
        await navigator.clipboard.writeText(text);
        showToast("Copied selection summary");
      } catch (error) {
        console.error(error);
      }
    });
  });
}

function toggleButton(key, raw, benchmark) {
  const safeRaw = escapeHtml(String(raw || "n/a"));
  const safeBenchmark = escapeHtml(String(benchmark || "n/a"));
  return `<button type="button" data-toggle-raw="${escapeHtmlAttribute(key)}" data-showing="benchmark" data-raw="${escapeHtmlAttribute(safeRaw)}" data-benchmark="${escapeHtmlAttribute(safeBenchmark)}">${safeBenchmark}</button>`;
}

function benchmarkDisplay(run, diffKey, raceKey, meetingKey) {
  const benchmark = run.form_benchmark || {};
  const parts = [formatFloat(benchmark[diffKey])];
  if (benchmark[raceKey] !== undefined && benchmark[raceKey] !== null) {
    parts.push(`R${benchmark[raceKey]}`);
  }
  if (benchmark[meetingKey] !== undefined && benchmark[meetingKey] !== null) {
    parts.push(`M${benchmark[meetingKey]}`);
  }
  return parts.filter(Boolean).join(" \xb7 ") || "n/a";
}

function splitDisplay(run, splitKey) {
  return formatFloat(run.splits?.[splitKey]);
}

function scoreClass(value) {
  const number = Number(value || 0);
  if (number >= 15) return 3;
  if (number >= 10) return 2;
  if (number >= 5) return 1;
  return 0;
}

function renderTable(headers, rows) {
  return `
    <table class="tabular">
      <thead>
        <tr>${headers.map((header) => `<th>${escapeHtml(header)}</th>`).join("")}</tr>
      </thead>
      <tbody>
        ${rows.map((row) => `
          <tr>${row.map((cell) => `<td>${cell && String(cell).startsWith("<") ? cell : escapeHtml(String(cell ?? ""))}</td>`).join("")}</tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

function chip(label, value, title = "", score = 0) {
  return `<span class="chip${score ? ` score-${score}` : ""}" title="${escapeHtmlAttribute(title)}"><strong>${escapeHtml(label)}:</strong> ${escapeHtml(String(value ?? "n/a"))}</span>`;
}

function tonedChip(label, value, title = "", tone = "") {
  return `<span class="chip chip-tone-${escapeHtml(tone || "neutral")}" title="${escapeHtmlAttribute(title)}"><strong>${escapeHtml(label)}:</strong> ${escapeHtml(String(value ?? "n/a"))}</span>`;
}

function summaryCard(label, value, subtitle = "", tone = "primary") {
  return `
    <div class="summary-card tone-${escapeHtml(tone)}" title="${escapeHtmlAttribute(subtitle)}">
      <span class="summary-label">${escapeHtml(label)}</span>
      <strong>${escapeHtml(String(value ?? "n/a"))}</strong>
      <span class="summary-subtle">${escapeHtml(subtitle || " ")}</span>
    </div>
  `;
}

function renderInsights(event) {
  const selections = [...(event.selections || [])];
  return [
    renderInsightBlock(
      "Punters Edge",
      "Best overlays in the field",
      topSelections(selections, (selection) => selection.punters_edge, 5),
      (selection) => formatFloat(selection.punters_edge),
      (selection) => `${selection.prediction?.normalized_speed_position || "No speed tag"} \xb7 Win ${formatPrice(findOdds(selection.odds, "Win")?.price)}`,
      "warning",
    ),
    renderInsightBlock(
      "Predictor",
      "Model score leaders",
      topSelections(selections, (selection) => selection.predictor_score, 5),
      (selection) => formatFloat(selection.predictor_score),
      (selection) => `Rank ${formatNumber(selection.prediction?.model_rank)} \xb7 Chance ${percent(selection.prediction?.winning_chance)}`,
      "purple",
    ),
    renderInsightBlock(
      "Speed",
      "Early pace and finish strength",
      topSelections(selections, (selection) => selection.prediction?.speed, 5),
      (selection) => `${formatFloat(selection.prediction?.speed)} / ${formatFloat(selection.prediction?.finish_speed)}`,
      (selection) => selection.prediction?.normalized_speed_position || "No speed tag",
      "primary",
    ),
    renderInsightBlock(
      "Stats",
      "Trainer / jockey and wet profile",
      topSelections(selections, calculateInsightStatsScore, 5),
      (selection) => `${percent(selection.trainer_jockey_win_percentage)} \xb7 ${percent(selection.wet_runs_win_percentage)}`,
      (selection) => `Wet place ${percent(selection.wet_runs_place_percentage)} \xb7 Avg prize ${formatCurrency(selection.average_prize_money)}`,
      "success",
    ),
  ].join("");
}

function renderInsightBlock(title, subtitle, selections, valueFormatter, metaFormatter, tone) {
  const maxValue = Math.max(...selections.map((selection) => numericInsightValue(selection, title)), 0);
  return `
    <section class="insight-block tone-${escapeHtml(tone)}">
      <div class="insight-heading">
        <div>
          <h3>${escapeHtml(title)}</h3>
          <p class="subtle">${escapeHtml(subtitle)}</p>
        </div>
      </div>
      <div class="insight-rows">
        ${selections.map((selection) => renderInsightRow(selection, valueFormatter(selection), metaFormatter(selection), tone, maxValue, title)).join("")}
      </div>
    </section>
  `;
}

function renderInsightRow(selection, valueText, metaText, tone, maxValue, title) {
  const rawValue = numericInsightValue(selection, title);
  const width = maxValue > 0 ? Math.max(8, (rawValue / maxValue) * 100) : 8;
  return `
    <div class="insight-row">
      <div class="insight-copy">
        <div class="insight-topline">
          <span class="number-pill tone-${escapeHtml(tone)}">${escapeHtml(formatNumber(selection.number))}</span>
          <strong>${escapeHtml(selection.name || "Unknown")}</strong>
        </div>
        <span class="subtle">${escapeHtml(metaText)}</span>
      </div>
      <div class="insight-value">
        <strong>${escapeHtml(valueText)}</strong>
        <span class="meter"><span class="meter-fill tone-${escapeHtml(tone)}" style="width:${width}%"></span></span>
      </div>
    </div>
  `;
}

function topSelections(selections, selector, limit) {
  return [...selections]
    .sort((left, right) => safeNumber(selector(right)) - safeNumber(selector(left)))
    .slice(0, limit);
}

function calculateInsightStatsScore(selection) {
  return (
    (safeNumber(selection.trainer_jockey_win_percentage) * STATS_INSIGHT_WEIGHTS.trainerJockeyWin) +
    (safeNumber(selection.wet_runs_place_percentage) * STATS_INSIGHT_WEIGHTS.wetPlaceProfile)
  ) / TOTAL_STATS_INSIGHT_WEIGHT;
}

function numericInsightValue(selection, title) {
  if (title === "Punters Edge") return safeNumber(selection.punters_edge);
  if (title === "Predictor") return safeNumber(selection.predictor_score);
  if (title === "Speed") return safeNumber(selection.prediction?.speed);
  return calculateInsightStatsScore(selection);
}

function safeNumber(value) {
  const number = Number(value || 0);
  return Number.isFinite(number) ? number : 0;
}

function percentageTone(value) {
  const number = safeNumber(value);
  if (number >= 50) return "purple";
  if (number > 0) return "success";
  if (number < 0) return "danger";
  return "neutral";
}

function findOdds(odds, type) {
  return (odds || []).find((entry) => entry.bet_type === type);
}

function formatCountdown(value) {
  if (!value) {
    return "TBC";
  }
  const now = new Date();
  const [timeText, meridiem] = String(value).split(" ");
  if (!timeText || !meridiem) {
    return String(value);
  }
  const [hourText, minuteText] = timeText.split(":");
  let hour = Number(hourText);
  if (Number.isNaN(hour)) {
    return String(value);
  }
  if (meridiem.toUpperCase() === "PM" && hour !== 12) {
    hour += 12;
  }
  if (meridiem.toUpperCase() === "AM" && hour === 12) {
    hour = 0;
  }
  const eventDate = new Date(now);
  eventDate.setHours(hour, Number(minuteText || 0), 0, 0);
  const deltaMs = eventDate - now;
  const sign = deltaMs < 0 ? "-" : "";
  const delta = Math.abs(Math.round(deltaMs / 1000));
  const hours = Math.floor(delta / 3600);
  const minutes = Math.floor((delta % 3600) / 60);
  const seconds = delta % 60;
  if (hours > 0) return `${sign}${hours}h ${minutes}m`;
  if (minutes > 0) return `${sign}${minutes}m ${seconds}s`;
  return `${sign}${seconds}s`;
}

function copyText(selection, winOdds, placeOdds) {
  return `${selection.number || "?"}. ${selection.name || "Unknown"} | Win ${formatPrice(winOdds?.price)} | Place ${formatPrice(placeOdds?.price)} | Barrier ${formatNumber(selection.barrier)} | Weight ${formatFloat(selection.weight)} | ROI ${percent(selection.roi)}`;
}

function formatCurrency(value) {
  const number = Number(value || 0);
  return new Intl.NumberFormat("en-AU", { style: "currency", currency: "AUD", maximumFractionDigits: number >= 20 ? 0 : 2 }).format(number);
}

function formatPrice(value) {
  const number = Number(value || 0);
  if (!number) return "n/a";
  return number > 20 ? `$${number.toFixed(0)}` : `$${number.toFixed(2)}`;
}

function formatFloat(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(2) : "n/a";
}

function formatNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? String(number) : "n/a";
}

function percent(value) {
  const number = Number(value || 0);
  return `${number.toFixed(1)}%`;
}

function truncate(value) {
  const text = String(value || "");
  return text.length > 96 ? `${text.slice(0, 93)}\u2026` : text;
}

function tooltipText(primary, extras = []) {
  return [primary, ...(extras || [])]
    .flatMap(normalizeTooltipPart)
    .filter(Boolean)
    .join("\n");
}

function normalizeTooltipPart(value) {
  if (value === null || value === undefined || value === "") {
    return [];
  }
  if (Array.isArray(value)) {
    return value.flatMap(normalizeTooltipPart);
  }
  if (typeof value === "object") {
    return Object.entries(value)
      .filter(([, item]) => item !== null && item !== undefined && item !== "")
      .map(([key, item]) => `${key}: ${item}`);
  }
  return [String(value)];
}

function setStatus(message, isError = false) {
  refs.statusText.textContent = message;
  refs.statusText.style.color = isError ? "var(--danger)" : "";
}

function showToast(message) {
  const toast = document.createElement("div");
  toast.className = "copy-toast";
  toast.textContent = message;
  document.body.appendChild(toast);
  window.setTimeout(() => toast.remove(), 1600);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function escapeHtmlAttribute(value) {
  return escapeHtml(value).replaceAll("\n", "&#10;");
}
