const state = {
  meetings: [],
  selectedMeetingIndex: 0,
  selectedEventIndex: 0,
  analysisMode: "predictor",
};

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
  selectionList: document.getElementById("selectionList"),
};

document.addEventListener("DOMContentLoaded", () => {
  refs.dateInput.value = new Date().toISOString().slice(0, 10);
  refs.loadButton.addEventListener("click", loadMeetings);
  refs.analysisSelect.addEventListener("change", (event) => {
    state.analysisMode = event.target.value;
    renderMeeting();
  });
  loadMeetings();
});

async function loadMeetings() {
  setStatus("Loading meetings…");
  refs.loadButton.disabled = true;

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
    refs.emptyState.classList.add("visible");
    refs.meetingView.classList.add("hidden");
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
        <span class="subtle">${escapeHtml((meeting.events || []).length)} races · ${escapeHtml(meeting.rail_position || "Rail n/a")}</span>
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

function renderMeeting() {
  const meeting = currentMeeting();
  if (!meeting) {
    refs.emptyState.classList.add("visible");
    refs.meetingView.classList.add("hidden");
    return;
  }

  refs.emptyState.classList.remove("visible");
  refs.meetingView.classList.remove("hidden");

  const events = Array.isArray(meeting.events) ? meeting.events : [];
  const event = events[state.selectedEventIndex] || events[0];
  if (!event) {
    refs.eventButtons.innerHTML = "";
    refs.eventDetails.innerHTML = "<p class='subtle'>No events available.</p>";
    refs.analysisBody.innerHTML = "";
    refs.selectionList.innerHTML = "";
    return;
  }
  state.selectedEventIndex = events.indexOf(event);

  refs.meetingHeader.innerHTML = `
    <div class="meeting-title">
      <div>
        <h2>${escapeHtml(meeting.name || "Unknown meeting")}</h2>
        <p class="subtle">${escapeHtml(meeting.state || "Unknown state")} · ${escapeHtml(meeting.slug || "")}</p>
      </div>
      <div class="meeting-meta">
        ${chip("Rail", meeting.rail_position || "n/a")}
        ${chip("Events", String(events.length))}
      </div>
    </div>
  `;

  refs.eventMeta.textContent = `${event.name || "Race"} · ${event.time || "TBC"}`;
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

  refs.eventDetails.innerHTML = `
    <div class="chip-row">
      ${chip("Countdown", formatCountdown(event.time))}
      ${chip("Distance", `${formatNumber(event.distance)}m`)}
      ${chip("Prize", formatCurrency(event.prize_money))}
      ${chip("Pace", event.pace || "n/a", tooltipText(event.comments))}
      ${chip("Class", event._class || "n/a")}
      ${chip("Track", `${event.track_condition || "?"} · ${event.track_type || "?"}`)}
      ${chip("Weather", event.weather || "n/a")}
      ${chip("Starters", formatNumber(event.starters))}
    </div>
  `;

  refs.analysisSelect.value = state.analysisMode;
  refs.analysisBody.innerHTML = renderAnalysis(event);
  refs.selectionList.innerHTML = renderSelections(event);
  wireInteractiveElements();
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

function renderSelections(event) {
  return (event.selections || []).map((selection, selectionIndex) => {
    const runs = Array.isArray(selection.runs) ? selection.runs.slice(0, 10) : [];
    const winOdds = findOdds(selection.odds, "Win");
    const placeOdds = findOdds(selection.odds, "Place");
    const trainerTitle = tooltipText(selection.trainer?.name, [
      `Win ${percent(selection.trainer?.last_year_win_percentage)}`,
      `Place ${percent(selection.trainer?.last_year_place_percentage)}`,
      selection.trainer?.location,
    ]);
    const jockeyTitle = tooltipText(selection.jockey?.name, [
      `Win ${percent(selection.jockey?.last_year_win_percentage)}`,
      `Place ${percent(selection.jockey?.last_year_place_percentage)}`,
    ]);

    return `
      <details class="selection-card">
        <summary class="selection-summary" data-copy="${escapeHtmlAttribute(copyText(selection, winOdds, placeOdds))}">
          <div class="selection-topline">
            <span class="selection-number">${escapeHtml(formatNumber(selection.number))}</span>
            <div>
              <strong>${escapeHtml(selection.name || "Unknown runner")}</strong>
              <span class="subtle">${escapeHtml(selection.prediction?.normalized_speed_position || "No speed tag")}</span>
            </div>
          </div>
          <div class="selection-summary-grid">
            ${chip("Win", formatPrice(winOdds?.price))}
            ${chip("Place", formatPrice(placeOdds?.price))}
            ${chip("Barrier", formatNumber(selection.barrier))}
            ${chip("Weight", formatFloat(selection.weight))}
            ${chip("ROI", percent(selection.roi))}
            ${chip("Prep", formatNumber(selection.runs_since_spell))}
            ${chip("Edge", formatFloat(selection.punters_edge), "", scoreClass(selection.punters_edge))}
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
          ${renderTable(
            ["Date", "Venue", "Pos", "Margin", "Distance", "Cond", "Wt", "L800", "L600", "L400", "L200", "Tempo"],
            runs.map((run, runIndex) => [
              run.meeting_date,
              `${run.venue || run.meeting_name || ""}${run.is_trial ? " (Trial)" : ""}`,
              formatNumber(run.finish_position),
              formatFloat(run.margin),
              `${formatNumber(run.distance)}m`,
              run.track_condition || "",
              formatFloat(run.weight),
              toggleButton(`l800-${selectionIndex}-${runIndex}`, splitDisplay(run, "runner_split_l800"), benchmarkDisplay(run, "runner_time_difference_l800", "runner_race_position_l800", "runner_meeting_position_l800")),
              toggleButton(`l600-${selectionIndex}-${runIndex}`, splitDisplay(run, "runner_split_l600"), benchmarkDisplay(run, "runner_time_difference_l600", "runner_race_position_l600", "runner_meeting_position_l600")),
              toggleButton(`l400-${selectionIndex}-${runIndex}`, splitDisplay(run, "runner_split_l400"), benchmarkDisplay(run, "runner_time_difference_l400", "runner_race_position_l400", "runner_meeting_position_l400")),
              toggleButton(`l200-${selectionIndex}-${runIndex}`, splitDisplay(run, "runner_split_l200"), benchmarkDisplay(run, "runner_time_difference_l200", "runner_race_position_l200", "runner_meeting_position_l200")),
              toggleButton(`tempo-${selectionIndex}-${runIndex}`, run.form_benchmark?.runner_tempo_label || "n/a", formatFloat(run.form_benchmark?.runner_tempo_difference)),
            ]),
          )}
        </div>
      </details>
    `;
  }).join("");
}

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
  return parts.filter(Boolean).join(" · ") || "n/a";
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
          <tr>${row.map((cell) => `<td>${cell && String(cell).startsWith("<button") ? cell : escapeHtml(String(cell ?? ""))}</td>`).join("")}</tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

function chip(label, value, title = "", score = 0) {
  return `<span class="chip${score ? ` score-${score}` : ""}" title="${escapeHtmlAttribute(title)}"><strong>${escapeHtml(label)}:</strong> ${escapeHtml(String(value ?? "n/a"))}</span>`;
}

function currentMeeting() {
  return state.meetings[state.selectedMeetingIndex];
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
  return text.length > 96 ? `${text.slice(0, 93)}…` : text;
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
