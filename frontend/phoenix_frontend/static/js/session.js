(() => {
  const appRoot = document.getElementById("session-app");
  if (!appRoot) return;

  const sessionId = appRoot.dataset.sessionId;
  const snapshotTag = document.getElementById("snapshot-json");
  const LOG_MAX_LINES = 1200;
  const VISIBILITY_STORAGE_PREFIX = "phoenix.visible";

  function parseSnapshot() {
    try {
      return JSON.parse(snapshotTag?.textContent || "{}");
    } catch {
      return {};
    }
  }

  const state = {
    snapshot: parseSnapshot(),
    activeSource: null,
    activeJobId: null,
    activeJobKind: "",
    activeTriggerButtonId: "",
    logLines: [],
    componentStatus: {},
    componentDetail: {},
    cycleRequestedRefinement: false,
    awaitingFreshAcquisition: false,
    impactChart: null,
    barrierChart: null,
    copingChart: null,
    timeSeriesChart: null,
    timeSeriesData: null,
    timeSeriesCacheKey: "",
    logsDrawerOpen: false,
    controlDrawerOpen: false,
    sectionVisibilityUser: {},
    sectionVisibilityAuto: {},
    phaseState: [],
    engineFlowFromSummary: [],
    qualityFlowFromSummary: [],
    runtimeEvents: [],
    llmModelFetchTimer: null,
    llmModelLastQuery: "",
    llmModelLoaded: false,
    streamReconnectTimer: null,
    streamReconnectAttempts: 0,
    streamCursorByJob: {},
    lastTerminalJobMarker: "",
  };

  const COMPONENT_DEFS = [
    { id: "cohort_batch", label: "Cohort Batch Runner", category: "ORCHESTRATION" },
    { id: "step01_operationalization", label: "Step 01 Operationalization", category: "MODEL CREATION" },
    { id: "step02_initial_model", label: "Step 02 Initial Model", category: "MODEL CREATION" },
    { id: "step02_visualization", label: "Step 02 Visual Diagnostics", category: "MODEL CREATION" },
    { id: "pseudodata_collection", label: "Data Collection / Pseudodata", category: "ACQUISITION" },
    { id: "manual_data_upload", label: "Manual Data Upload", category: "ACQUISITION" },
    { id: "pipeline_cycle_engine", label: "Cycle Pipeline", category: "ANALYSIS" },
    { id: "readiness_analysis", label: "Readiness Check", category: "ANALYSIS" },
    { id: "network_analysis", label: "Network Time-Series Analysis", category: "ANALYSIS" },
    { id: "impact_quantification", label: "Momentary Impact Quantification", category: "ANALYSIS" },
    { id: "step03_target_selection", label: "Step 03 Target Identification", category: "ANALYSIS" },
    { id: "step04_updated_model", label: "Step 04 Updated Model", category: "MODEL CREATION" },
    { id: "step05_intervention", label: "Step 05 Digital Intervention", category: "INTERVENTION" },
    { id: "impact_visualization", label: "Impact Visualization (Support)", category: "QUALITY + RESEARCH" },
    { id: "evaluation_reporting", label: "Research Reporting (Support)", category: "QUALITY + RESEARCH" },
    { id: "communication_agent", label: "Communication Agent", category: "INTERVENTION" },
  ];

  const JOB_KIND_COMPONENTS = {
    initial_model: ["step01_operationalization", "step02_initial_model", "step02_visualization"],
    synthesize_pseudodata: ["pseudodata_collection"],
    manual_data_upload: ["manual_data_upload"],
    pipeline_cycle: [
      "pipeline_cycle_engine",
      "readiness_analysis",
      "network_analysis",
      "impact_quantification",
      "step03_target_selection",
      "step04_updated_model",
      "step05_intervention",
      "impact_visualization",
      "evaluation_reporting",
    ],
    full_cohort: [
      "cohort_batch",
      "step01_operationalization",
      "step02_initial_model",
      "step02_visualization",
      "pseudodata_collection",
      "pipeline_cycle_engine",
      "readiness_analysis",
      "network_analysis",
      "impact_quantification",
      "step03_target_selection",
      "step04_updated_model",
      "step05_intervention",
      "impact_visualization",
      "evaluation_reporting",
    ],
  };

  const UI = {
    runtimeGrid: document.getElementById("runtime-component-grid"),
    logConsole: document.getElementById("log-console"),
    activeJobId: document.getElementById("active-job-id"),
    activeJobStatus: document.getElementById("active-job-status"),
    activeComponent: document.getElementById("active-component"),
    drawerActiveJobId: document.getElementById("drawer-active-job-id"),
    drawerActiveJobStatus: document.getElementById("drawer-active-job-status"),
    errorBanner: document.getElementById("job-error-banner"),
    logsDrawer: document.getElementById("logs-drawer"),
    logsDrawerOpenBtn: document.getElementById("logs-drawer-open"),
    logsDrawerCloseBtn: document.getElementById("logs-drawer-close"),
    controlDrawer: document.getElementById("control-drawer"),
    controlDrawerOpenBtn: document.getElementById("control-drawer-open"),
    controlDrawerCloseBtn: document.getElementById("control-drawer-close"),
    openLogsFromControlBtn: document.getElementById("open-logs-from-control"),
    drawerBackdrop: document.getElementById("drawer-backdrop"),
    sectionToggles: Array.from(document.querySelectorAll(".section-visibility-toggle")),
    runNextPhaseBtn: document.getElementById("run-next-phase-btn"),
    topbarPipelineStrip: document.getElementById("topbar-pipeline-strip"),
    topbarPipelineNodes: document.getElementById("topbar-pipeline-nodes"),
    runtimeStageSummary: document.getElementById("runtime-stage-summary"),
    runtimeLastEvent: document.getElementById("runtime-last-event"),
    runtimeEventsList: document.getElementById("runtime-events-list"),
    cohortSummary: document.getElementById("cohort-summary"),
    llmModelOptions: document.getElementById("llm-model-options"),
    llmModelInputs: [
      document.getElementById("initial-llm-model"),
      document.getElementById("cycle-llm-model"),
      document.getElementById("cohort-llm-model"),
    ].filter(Boolean),
  };

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function normalizeStatus(status) {
    const raw = String(status || "idle").toLowerCase();
    if (["idle", "queued", "running", "succeeded", "failed"].includes(raw)) return raw;
    if (raw === "done") return "succeeded";
    if (raw === "error") return "failed";
    return "idle";
  }

  function applyStatusClass(node, status) {
    if (!node) return;
    const classes = ["status-idle", "status-queued", "status-running", "status-succeeded", "status-failed"];
    classes.forEach((cls) => node.classList.remove(cls));
    node.classList.add(`status-${normalizeStatus(status)}`);
  }

  function isRunningStatus(status) {
    return ["queued", "running"].includes(normalizeStatus(status));
  }

  function appendLog(line) {
    if (!UI.logConsole) return;
    state.logLines.push(String(line));
    while (state.logLines.length > LOG_MAX_LINES) state.logLines.shift();
    UI.logConsole.textContent = state.logLines.join("\n");
    UI.logConsole.scrollTop = UI.logConsole.scrollHeight;
  }

  function renderRuntimeEvents() {
    if (!UI.runtimeEventsList) return;
    const rows = state.runtimeEvents.slice(0, 8);
    if (!rows.length) {
      UI.runtimeEventsList.innerHTML = "";
      return;
    }
    UI.runtimeEventsList.innerHTML = rows.map((item) => `
      <li><code>${escapeHtml(item.time || "--:--:--")}</code> ${escapeHtml(item.message || "")}</li>
    `).join("");
  }

  function pushRuntimeEvent(message) {
    const raw = String(message || "").trim();
    if (!raw) return;
    const now = new Date();
    const hh = String(now.getHours()).padStart(2, "0");
    const mm = String(now.getMinutes()).padStart(2, "0");
    const ss = String(now.getSeconds()).padStart(2, "0");
    state.runtimeEvents.unshift({ time: `${hh}:${mm}:${ss}`, message: raw.slice(0, 220) });
    while (state.runtimeEvents.length > 20) state.runtimeEvents.pop();
    if (UI.runtimeLastEvent) UI.runtimeLastEvent.textContent = raw.slice(0, 220);
    renderRuntimeEvents();
  }

  function updateBackdrop() {
    if (!UI.drawerBackdrop) return;
    const open = state.logsDrawerOpen || state.controlDrawerOpen;
    UI.drawerBackdrop.hidden = !open;
    UI.drawerBackdrop.classList.toggle("is-open", open);
  }

  function setLogsDrawerOpen(open) {
    state.logsDrawerOpen = Boolean(open);
    if (!UI.logsDrawer) return;
    UI.logsDrawer.classList.toggle("is-open", state.logsDrawerOpen);
    UI.logsDrawer.setAttribute("aria-hidden", state.logsDrawerOpen ? "false" : "true");
    updateBackdrop();
  }

  function setControlDrawerOpen(open) {
    state.controlDrawerOpen = Boolean(open);
    if (!UI.controlDrawer) return;
    UI.controlDrawer.classList.toggle("is-open", state.controlDrawerOpen);
    UI.controlDrawer.setAttribute("aria-hidden", state.controlDrawerOpen ? "false" : "true");
    updateBackdrop();
  }

  function closeDrawers() {
    setLogsDrawerOpen(false);
    setControlDrawerOpen(false);
  }

  function setJobMeta(jobId, status) {
    const safe = normalizeStatus(status);
    if (UI.activeJobId) UI.activeJobId.textContent = jobId || "none";
    if (UI.activeJobStatus) {
      UI.activeJobStatus.textContent = safe.toUpperCase();
      applyStatusClass(UI.activeJobStatus, safe);
    }
    if (UI.drawerActiveJobId) UI.drawerActiveJobId.textContent = jobId || "none";
    if (UI.drawerActiveJobStatus) {
      UI.drawerActiveJobStatus.textContent = safe.toUpperCase();
      applyStatusClass(UI.drawerActiveJobStatus, safe);
    }
  }

  function setActiveComponent(componentId, status = "running") {
    const safeStatus = normalizeStatus(status);
    const label = COMPONENT_DEFS.find((item) => item.id === componentId)?.label || componentId || "idle";
    if (UI.activeComponent) {
      UI.activeComponent.textContent = safeStatus === "idle" ? "idle" : label;
      applyStatusClass(UI.activeComponent, safeStatus);
    }
    if (UI.runtimeStageSummary) {
      const suffix = safeStatus === "idle" ? "" : ` (${safeStatus.toUpperCase()})`;
      UI.runtimeStageSummary.textContent = safeStatus === "idle" ? "Idle" : `${label}${suffix}`;
    }
  }

  function setComponentState(componentId, status, detail = "") {
    const safe = normalizeStatus(status);
    const previousStatus = state.componentStatus[componentId];
    const previousDetail = state.componentDetail[componentId];
    state.componentStatus[componentId] = safe;
    if (detail) state.componentDetail[componentId] = detail;
    const card = UI.runtimeGrid?.querySelector(`[data-component="${componentId}"]`);
    if (card) {
      card.dataset.status = safe;
      const chip = card.querySelector(".status-chip");
      const detailNode = card.querySelector(".runtime-card-detail");
      if (chip) {
        chip.textContent = safe.toUpperCase();
        applyStatusClass(chip, safe);
      }
      if (detailNode) detailNode.textContent = detail || state.componentDetail[componentId] || "—";
    }
    if (safe !== previousStatus || (detail && detail !== previousDetail)) {
      const label = COMPONENT_DEFS.find((item) => item.id === componentId)?.label || componentId;
      const suffix = detail ? `: ${detail}` : "";
      pushRuntimeEvent(`${label} -> ${safe.toUpperCase()}${suffix}`);
    }
    syncRuntimeCardVisibility();
    renderPhaseProgress();
  }

  function shouldShowRuntimeCard(componentId) {
    if (componentId !== "communication_agent") return true;
    const status = normalizeStatus(state.componentStatus[componentId] || "idle");
    if (status !== "idle") return true;
    const stage = String(state.snapshot?.communication_summary?.payload?.stage || "").toLowerCase();
    return stage.startsWith("cycle_");
  }

  function syncRuntimeCardVisibility() {
    if (!UI.runtimeGrid) return;
    COMPONENT_DEFS.forEach((item) => {
      const card = UI.runtimeGrid.querySelector(`[data-component="${item.id}"]`);
      if (!card) return;
      card.classList.toggle("runtime-card-hidden", !shouldShowRuntimeCard(item.id));
    });
  }

  function initRuntimeMap() {
    if (!UI.runtimeGrid) return;
    UI.runtimeGrid.innerHTML = COMPONENT_DEFS.map((item) => `
      <article class="runtime-card" data-component="${item.id}" data-status="idle">
        <div class="runtime-card-head">
          <span class="runtime-card-title">${escapeHtml(item.label)}</span>
          <span class="badge status-chip status-idle">IDLE</span>
        </div>
        <div class="runtime-card-detail">Category: ${escapeHtml(item.category)}</div>
      </article>
    `).join("");
    COMPONENT_DEFS.forEach((item) => {
      state.componentStatus[item.id] = "idle";
      state.componentDetail[item.id] = `Category: ${item.category}`;
    });
    syncRuntimeCardVisibility();
  }

  function sectionVisibilityStorageKey(key) {
    return `${VISIBILITY_STORAGE_PREFIX}.${sessionId}.${key}`;
  }

  function getUserVisibilitySetting(key) {
    if (Object.prototype.hasOwnProperty.call(state.sectionVisibilityUser, key)) {
      return state.sectionVisibilityUser[key];
    }
    const stored = localStorage.getItem(sectionVisibilityStorageKey(key));
    if (stored === "hidden") return false;
    if (stored === "visible") return true;
    return true;
  }

  function setUserVisibilitySetting(key, visible) {
    state.sectionVisibilityUser[key] = Boolean(visible);
    localStorage.setItem(sectionVisibilityStorageKey(key), visible ? "visible" : "hidden");
  }

  function setSectionVisible(key, visible) {
    const section = document.querySelector(`.collapsible-section[data-section-key="${key}"]`);
    if (!section) return;
    section.classList.toggle("hidden", !visible);
  }

  function applySectionVisibility() {
    const togglesByKey = new Map();
    UI.sectionToggles.forEach((toggle) => togglesByKey.set(toggle.dataset.sectionTarget || "", toggle));

    const allKeys = new Set([
      ...Array.from(togglesByKey.keys()),
      ...Array.from(document.querySelectorAll(".collapsible-section")).map((node) => node.dataset.sectionKey || ""),
    ]);

    allKeys.forEach((key) => {
      if (!key) return;
      const autoVisible = state.sectionVisibilityAuto[key] !== false;
      const userVisible = getUserVisibilitySetting(key);
      const finalVisible = autoVisible && userVisible;
      setSectionVisible(key, finalVisible);
      const toggle = togglesByKey.get(key);
      if (toggle) {
        toggle.checked = userVisible;
        toggle.disabled = !autoVisible;
        toggle.title = autoVisible ? "" : "This panel will appear when prerequisite outputs are available.";
      }
    });
  }

  function setCollapsed(section, collapsed, persist = true) {
    const key = section.dataset.sectionKey || "";
    const body = section.querySelector(".section-body");
    const btn = section.querySelector(".toggle-section-btn");
    if (!body || !btn) return;
    body.classList.toggle("is-collapsed", collapsed);
    btn.textContent = collapsed ? "Expand" : "Collapse";
    if (persist && key) {
      localStorage.setItem(`phoenix.section.${sessionId}.${key}`, collapsed ? "collapsed" : "open");
    }
  }

  function initCollapsibleSections() {
    const sections = Array.from(document.querySelectorAll(".collapsible-section"));
    sections.forEach((section) => {
      const key = section.dataset.sectionKey || "";
      const defaultOpen = String(section.dataset.defaultOpen || "true").toLowerCase() === "true";
      const stored = key ? localStorage.getItem(`phoenix.section.${sessionId}.${key}`) : null;
      const collapsed = stored ? stored === "collapsed" : !defaultOpen;
      setCollapsed(section, collapsed, false);
      section.querySelector(".toggle-section-btn")?.addEventListener("click", () => {
        const isCollapsed = section.querySelector(".section-body")?.classList.contains("is-collapsed");
        setCollapsed(section, !isCollapsed);
      });
    });

    document.getElementById("expand-all-btn")?.addEventListener("click", () => {
      sections.forEach((section) => setCollapsed(section, false));
    });
    document.getElementById("collapse-all-btn")?.addEventListener("click", () => {
      sections.forEach((section) => setCollapsed(section, true));
    });
  }

  function initSectionVisibilityControls() {
    UI.sectionToggles.forEach((toggle) => {
      const key = toggle.dataset.sectionTarget || "";
      if (!key) return;
      toggle.checked = getUserVisibilitySetting(key);
      toggle.addEventListener("change", () => {
        setUserVisibilitySetting(key, Boolean(toggle.checked));
        applySectionVisibility();
      });
    });
  }

  function showError(message) {
    if (!UI.errorBanner) return;
    const raw = String(message || "").trim();
    if (!raw) {
      UI.errorBanner.classList.add("hidden");
      UI.errorBanner.textContent = "";
      return;
    }
    const low = raw.toLowerCase();
    let hint = "Inspect realtime logs for the failing component and rerun.";
    if (low.includes("collect_allowed_predictor_paths")) {
      hint = "Step 02 guardrail argument mismatch detected. Pull latest code and rerun model creation.";
      setComponentState("step02_initial_model", "failed", "Guardrail argument mismatch");
    } else if (low.includes("no module named 'shared'")) {
      hint = "Step 02 import bootstrap failure. Pull latest code and rerun model creation.";
      setComponentState("step02_initial_model", "failed", "Import bootstrap failure");
    } else if (low.includes("produced no model artifact") || low.includes("model json is missing")) {
      hint = "Step 02 worker failed before output serialization. Check worker error lines in logs.";
      setComponentState("step02_initial_model", "failed", "Model artifact missing");
    } else if (low.includes("no module named 'pandas'")) {
      hint = "Python dependency missing. Install project requirements in the selected environment.";
    } else if (low.includes("cohort run finished with failures")) {
      hint = "Some cohort patients failed. Open logs and inspect the cohort manifest path in the error message.";
      setComponentState("cohort_batch", "failed", "One or more patients failed");
    } else if (low.includes("session already has running job")) {
      hint = "A job is already running for this session. Wait for completion before launching a new one.";
    }
    UI.errorBanner.innerHTML = `<strong>Runtime error:</strong> ${escapeHtml(raw)}<br><span>${escapeHtml(hint)}</span>`;
    UI.errorBanner.classList.remove("hidden");
    setLogsDrawerOpen(true);
  }

  function setButtonLoading(buttonId, loading, runningLabel = "Processing…") {
    const btn = buttonId ? document.getElementById(buttonId) : null;
    if (!btn) return;
    if (!btn.dataset.defaultLabel) btn.dataset.defaultLabel = btn.textContent || "";
    btn.textContent = loading ? runningLabel : btn.dataset.defaultLabel;
    if (loading) btn.disabled = true;
  }

  function syncControlStates() {
    const busy = Boolean(state.activeSource);
    const hasModel = Boolean(state.snapshot.has_model);
    const hasPseudodata = Boolean(state.snapshot.has_pseudodata) && !state.awaitingFreshAcquisition;
    const setDisabled = (id, disabled, title = "") => {
      const node = document.getElementById(id);
      if (!node) return;
      if (state.activeTriggerButtonId && id === state.activeTriggerButtonId && busy) return;
      node.disabled = Boolean(disabled);
      node.title = title;
    };
    setDisabled("run-initial-model-btn", busy, busy ? "A background job is running." : "");
    setDisabled("synthesize-btn", busy || !hasModel, !hasModel ? "Run model creation first." : "");
    setDisabled("manual-upload-btn", busy || !hasModel, !hasModel ? "Run model creation first." : "");
    setDisabled(
      "run-cycle-btn",
      busy || !hasModel || !hasPseudodata,
      !hasPseudodata ? "Acquire pseudodata first." : "",
    );
    setDisabled("run-cohort-btn", busy, busy ? "A background job is running." : "");
  }

  async function apiGet(path) {
    const res = await fetch(path);
    const payload = await res.json();
    if (!res.ok || payload.status === "error") {
      throw new Error(payload.message || `HTTP ${res.status}`);
    }
    return payload;
  }

  async function apiPost(path, body) {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    });
    const payload = await res.json();
    if (!res.ok || payload.status === "error") {
      throw new Error(payload.message || `HTTP ${res.status}`);
    }
    return payload;
  }

  function renderLlmModelOptions(models) {
    if (!UI.llmModelOptions) return;
    const rows = Array.isArray(models) ? models : [];
    if (!rows.length) return;
    UI.llmModelOptions.innerHTML = rows.map((row) => {
      const id = String(row.id || "").trim();
      const label = String(row.label || id).trim();
      if (!id) return "";
      return `<option value="${escapeHtml(id)}">${escapeHtml(label)}</option>`;
    }).join("");
  }

  async function fetchLlmModelCatalog(query = "") {
    const q = String(query || "").trim();
    const response = await apiGet(`/api/llm/models?q=${encodeURIComponent(q)}&limit=120`);
    const rows = Array.isArray(response.models) ? response.models : [];
    if (rows.length) {
      renderLlmModelOptions(rows);
      state.llmModelLoaded = true;
      state.llmModelLastQuery = q;
    }
  }

  function scheduleLlmModelFetch(query = "") {
    if (state.llmModelFetchTimer) {
      clearTimeout(state.llmModelFetchTimer);
      state.llmModelFetchTimer = null;
    }
    const q = String(query || "").trim();
    state.llmModelFetchTimer = window.setTimeout(() => {
      fetchLlmModelCatalog(q).catch((err) => {
        appendLog(`[frontend] model catalog lookup failed: ${err.message || err}`);
      });
    }, 140);
  }

  function bindModelCatalogAutocomplete() {
    const inputs = UI.llmModelInputs || [];
    if (!inputs.length) return;
    inputs.forEach((node) => {
      node?.addEventListener("focus", () => {
        if (!state.llmModelLoaded) scheduleLlmModelFetch("");
      });
      node?.addEventListener("input", (event) => {
        const value = String(event?.target?.value || "");
        if (value.length >= 1) {
          scheduleLlmModelFetch(value);
        } else if (!state.llmModelLoaded) {
          scheduleLlmModelFetch("");
        }
      });
    });
    scheduleLlmModelFetch("");
  }

  function readBaselines() {
    const rows = [];
    document.querySelectorAll(".baseline-input").forEach((node) => {
      rows.push({ var_id: node.dataset.varId, baseline_0_1: Number(node.value) });
    });
    return rows;
  }

  function destroyCharts() {
    [state.impactChart, state.barrierChart, state.copingChart, state.timeSeriesChart].forEach((chart) => {
      if (chart && typeof chart.destroy === "function") chart.destroy();
    });
    state.impactChart = null;
    state.barrierChart = null;
    state.copingChart = null;
    state.timeSeriesChart = null;
  }

  function buildBarChart(canvasId, labels, values, color) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || typeof Chart === "undefined") return null;
    return new Chart(canvas, {
      type: "bar",
      data: {
        labels,
        datasets: [{ label: "score", data: values, backgroundColor: color, borderRadius: 4 }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: {
            beginAtZero: true,
            max: 1,
            ticks: { color: "#b7cae8" },
            grid: { color: "rgba(109, 136, 180, 0.2)" },
          },
          x: {
            ticks: { color: "#b7cae8" },
            grid: { color: "rgba(109, 136, 180, 0.1)" },
          },
        },
      },
    });
  }

  function parseCsvText(raw) {
    const lines = String(raw || "")
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter((line) => line.length > 0);
    if (!lines.length) return { headers: [], rows: [] };
    const headers = lines[0].split(",").map((cell) => cell.trim());
    const rows = lines.slice(1).map((line) => {
      const cells = line.split(",");
      const row = {};
      headers.forEach((key, idx) => {
        row[key] = String(cells[idx] ?? "").trim();
      });
      return row;
    });
    return { headers, rows };
  }

  function parseNumeric(value) {
    const num = Number(value);
    return Number.isFinite(num) ? num : null;
  }

  async function ensureTimeSeriesData(snapshot) {
    const profileId = String(snapshot?.session?.profile_id || "").trim();
    if (!profileId || !snapshot?.has_pseudodata) {
      state.timeSeriesData = null;
      state.timeSeriesCacheKey = "";
      return null;
    }
    const cacheKey = [
      profileId,
      String(snapshot?.session?.updated_at || ""),
      String(snapshot?.pseudodata_summary?.n_points || ""),
    ].join("|");
    if (state.timeSeriesData && state.timeSeriesCacheKey === cacheKey) {
      return state.timeSeriesData;
    }

    const relPath = `outputs/pseudodata/${profileId}/pseudodata_wide.csv`;
    const response = await fetch(`/api/sessions/${sessionId}/files/${encodeURI(relPath)}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch pseudodata CSV (${response.status}).`);
    }
    const text = await response.text();
    const parsed = parseCsvText(text);
    if (!parsed.headers.length) {
      state.timeSeriesData = null;
      state.timeSeriesCacheKey = cacheKey;
      return null;
    }

    const variableColumns = parsed.headers.filter((name) => !["t_index", "date"].includes(String(name || "").trim()));
    const x = parsed.rows.map((row, idx) => {
      const tVal = parseNumeric(row.t_index);
      if (tVal != null) return tVal;
      return idx + 1;
    });
    const dates = parsed.rows.map((row) => String(row.date || "").trim());
    const series = {};
    variableColumns.forEach((col) => {
      series[col] = parsed.rows.map((row) => parseNumeric(row[col]));
    });

    state.timeSeriesData = {
      x,
      dates,
      series,
      columns: variableColumns,
      rowCount: parsed.rows.length,
    };
    state.timeSeriesCacheKey = cacheKey;
    return state.timeSeriesData;
  }

  function ensureTimeSeriesSelectors(data) {
    const variableSelect = document.getElementById("timeseries-variable-select");
    if (!variableSelect) return;
    const columns = Array.isArray(data?.columns) ? data.columns : [];
    if (!columns.length) {
      variableSelect.innerHTML = `<option value="">No signals</option>`;
      variableSelect.disabled = true;
      return;
    }
    variableSelect.disabled = false;
    const current = String(variableSelect.value || "");
    variableSelect.innerHTML = columns
      .map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`)
      .join("");
    if (current && columns.includes(current)) {
      variableSelect.value = current;
    } else {
      variableSelect.value = columns[0];
    }
  }

  function updateTimeSeriesStatus(text) {
    const node = document.getElementById("timeseries-status");
    if (node) node.textContent = String(text || "");
  }

  function renderTimeSeriesChart() {
    const canvas = document.getElementById("chart-timeseries");
    const variableSelect = document.getElementById("timeseries-variable-select");
    const windowSelect = document.getElementById("timeseries-window-select");
    if (!canvas || !variableSelect || !windowSelect || typeof Chart === "undefined") return;
    const data = state.timeSeriesData;
    if (!data || !Array.isArray(data.columns) || !data.columns.length) {
      if (state.timeSeriesChart && typeof state.timeSeriesChart.destroy === "function") {
        state.timeSeriesChart.destroy();
      }
      state.timeSeriesChart = null;
      updateTimeSeriesStatus("No pseudodata loaded.");
      return;
    }

    const signal = String(variableSelect.value || data.columns[0] || "");
    if (!signal || !data.series[signal]) {
      updateTimeSeriesStatus("Select a signal to display time-series data.");
      return;
    }

    const windowRaw = String(windowSelect.value || "all");
    const requestedWindow = windowRaw === "all" ? data.x.length : Math.max(1, Number(windowRaw) || data.x.length);
    const start = Math.max(0, data.x.length - requestedWindow);
    const xSlice = data.x.slice(start);
    const dateSlice = data.dates.slice(start);
    const ySlice = data.series[signal].slice(start);

    if (state.timeSeriesChart && typeof state.timeSeriesChart.destroy === "function") {
      state.timeSeriesChart.destroy();
    }
    state.timeSeriesChart = new Chart(canvas, {
      type: "line",
      data: {
        labels: xSlice,
        datasets: [
          {
            label: signal,
            data: ySlice,
            borderColor: "#76b1ff",
            backgroundColor: "rgba(118, 177, 255, 0.18)",
            tension: 0.2,
            pointRadius: 1.8,
            pointHoverRadius: 3.2,
            spanGaps: true,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: true, labels: { color: "#c6d8f3" } },
          tooltip: {
            callbacks: {
              title: (ctx) => {
                const idx = Number(ctx?.[0]?.dataIndex ?? -1);
                const date = idx >= 0 ? String(dateSlice[idx] || "") : "";
                const t = idx >= 0 ? String(xSlice[idx] || "") : "";
                return date ? `t=${t} (${date})` : `t=${t}`;
              },
            },
          },
        },
        scales: {
          y: {
            ticks: { color: "#b7cae8" },
            grid: { color: "rgba(109, 136, 180, 0.18)" },
          },
          x: {
            ticks: { color: "#b7cae8", maxTicksLimit: 12 },
            grid: { color: "rgba(109, 136, 180, 0.1)" },
          },
        },
      },
    });

    updateTimeSeriesStatus(
      `Signal=${signal} | points=${xSlice.length} / ${data.x.length} | missing=${ySlice.filter((v) => v == null).length}`,
    );
  }

  async function refreshTimeSeries(snapshot) {
    const variableSelect = document.getElementById("timeseries-variable-select");
    if (!variableSelect) return;
    if (!snapshot?.has_pseudodata) {
      state.timeSeriesData = null;
      state.timeSeriesCacheKey = "";
      variableSelect.innerHTML = `<option value=\"\">No signals</option>`;
      variableSelect.disabled = true;
      renderTimeSeriesChart();
      return;
    }
    try {
      const data = await ensureTimeSeriesData(snapshot);
      ensureTimeSeriesSelectors(data);
      renderTimeSeriesChart();
    } catch (error) {
      updateTimeSeriesStatus(`Time-series load failed: ${error.message || error}`);
    }
  }

  function renderMetricCards(dashboard) {
    const readiness = dashboard.readiness || {};
    const impact = dashboard.impact || {};
    const step05 = dashboard.step05 || {};
    const topPredictor = (impact.top_predictors || [])[0] || {};

    const setText = (id, value) => {
      const node = document.getElementById(id);
      if (node) node.textContent = value;
    };
    setText("metric-readiness-score", `${Number(readiness.score_0_100 || 0).toFixed(1)}`);
    setText("metric-readiness-label", readiness.label || "unknown");
    setText("metric-tier", readiness.tier || "—");
    setText("metric-variant", readiness.tier3_variant || "—");
    setText("metric-top-predictor", topPredictor.predictor || "—");
    setText(
      "metric-top-predictor-score",
      topPredictor.score_0_1 != null ? Number(topPredictor.score_0_1).toFixed(3) : "—",
    );
    setText("metric-barrier-count", String((step05.selected_barriers || []).length || 0));
  }

  function renderDashboard(dashboard) {
    renderMetricCards(dashboard);
    destroyCharts();

    const impactRows = (dashboard.impact?.top_predictors || []).slice(0, 8);
    const barrierRows = (dashboard.step05?.selected_barriers || []).slice(0, 8);
    const copingRows = (dashboard.step05?.selected_coping || []).slice(0, 8);

    state.impactChart = buildBarChart(
      "chart-impact",
      impactRows.map((x) => x.predictor || "n/a"),
      impactRows.map((x) => Number(x.score_0_1 || 0)),
      "#4f8dff",
    );
    state.barrierChart = buildBarChart(
      "chart-barriers",
      barrierRows.map((x) => x.barrier_name || "n/a"),
      barrierRows.map((x) => Number(x.score_0_1 || 0)),
      "#f4b43b",
    );
    state.copingChart = buildBarChart(
      "chart-coping",
      copingRows.map((x) => x.coping_name || "n/a"),
      copingRows.map((x) => Number(x.score_0_1 || 0)),
      "#28c995",
    );

    const renderList = (id, rows, emptyText) => {
      const node = document.getElementById(id);
      if (!node) return;
      const list = Array.isArray(rows) ? rows : [];
      node.innerHTML = list.length
        ? list.map((item) => `<li>${escapeHtml(item)}</li>`).join("")
        : `<li class="muted">${escapeHtml(emptyText)}</li>`;
    };

    renderList("dashboard-readiness-why", dashboard.readiness?.why || [], "No readiness rationale available.");
    const networkNotes = dashboard.network?.notes || [];
    renderList("dashboard-network-notes", networkNotes, "No network notes available.");
    const targetRows = (dashboard.step03?.recommended_targets || []).map((row) => {
      const p = row.predictor || "unknown";
      const s = Number(row.score_0_1 || 0).toFixed(3);
      const r = row.rationale ? ` — ${row.rationale}` : "";
      return `${p} (score=${s})${r}`;
    });
    const step03Empty = dashboard.step03?.status === "skipped"
      ? "Step-03 was skipped (no impact output available)."
      : "No Step-03 targets available.";
    renderList("dashboard-step03-targets", targetRows, step03Empty);

    const step04 = dashboard.step04 || {};
    const step04Rows = [];
    if ((step04.recommended_predictors || []).length) {
      step04Rows.push(`Predictors (${step04.recommended_predictors.length}): ${step04.recommended_predictors.join(", ")}`);
    }
    if ((step04.retained_criteria_ids || []).length) {
      step04Rows.push(`Retained criteria (${step04.retained_criteria_ids.length}): ${step04.retained_criteria_ids.join(", ")}`);
    }
    if ((step04.reason_codes || []).length) {
      step04Rows.push(`Range-policy reasons: ${step04.reason_codes.join(", ")}`);
    }
    const step04Empty = step04.status === "skipped"
      ? "Step-04 was skipped because upstream target selection was unavailable."
      : "No Step-04 updated model details available.";
    renderList("dashboard-step04-updated", step04Rows, step04Empty);

    const summary = String(dashboard.step05?.user_summary || "").trim();
    const step05SummaryNode = document.getElementById("dashboard-step05-summary");
    if (step05SummaryNode) {
      if (summary) {
        step05SummaryNode.textContent = summary;
      } else if (dashboard.step05?.status === "skipped") {
        step05SummaryNode.textContent = "Step-05 intervention was skipped because no handoff outputs were available.";
      } else {
        step05SummaryNode.textContent = "No intervention summary yet.";
      }
    }

    if (dashboard.impact?.status === "skipped") {
      const reason = String(dashboard.impact?.status_reason || "").trim();
      const noteNode = document.getElementById("dashboard-network-notes");
      if (noteNode && reason) {
        const exists = Array.from(noteNode.querySelectorAll("li")).some((li) => li.textContent === reason);
        if (!exists) {
          noteNode.insertAdjacentHTML("beforeend", `<li>${escapeHtml(reason)}</li>`);
        }
      }
    }
  }

  function renderCommunication(communication) {
    const target = document.getElementById("communication-summary");
    if (!target) return;
    const payload = communication?.payload || {};
    const summary = payload.summary || {};
    const stage = String(payload.stage || "").toLowerCase();
    const showCommunication = Boolean(payload && Object.keys(payload).length && stage.startsWith("cycle_"));
    if (!showCommunication) {
      target.innerHTML = `<p class="muted">Communication agent output appears after cycle completion.</p>`;
      const previewNode = document.getElementById("control-communication-preview");
      if (previewNode) previewNode.textContent = "Communication summary will appear after cycle completion.";
      return;
    }
    target.innerHTML = `
      <h3>${escapeHtml(summary.headline || "Communication Summary")}</h3>
      <p>${escapeHtml(summary.summary_markdown || "")}</p>
      <div class="meta-grid">
        <div><strong>LLM enabled:</strong> ${escapeHtml(String(payload.llm_enabled))}</div>
        <div><strong>Stage:</strong> ${escapeHtml(payload.stage || "unknown")}</div>
      </div>
      <pre class="json-view">${escapeHtml(JSON.stringify(payload, null, 2))}</pre>
    `;

    const previewNode = document.getElementById("control-communication-preview");
    if (previewNode) {
      const previewText = String(summary.headline || summary.summary_markdown || "").slice(0, 220).trim();
      previewNode.textContent = previewText || "Communication summary available.";
    }
  }

  function renderCohortSummary(cohortSummary) {
    if (!UI.cohortSummary) return;
    const payload = cohortSummary && typeof cohortSummary === "object" ? cohortSummary : {};
    if (!Object.keys(payload).length) {
      UI.cohortSummary.textContent = "No cohort run artifacts yet.";
      return;
    }
    const status = String(payload.status || "unknown").toUpperCase();
    const runId = String(payload.run_id || "n/a");
    const patientCount = Number(payload.patient_count || 0);
    const completed = Number(payload.summary?.completed || 0);
    const failed = Number(payload.summary?.failed || 0);
    UI.cohortSummary.innerHTML = `
      <div class="meta-grid">
        <div><strong>Run ID:</strong> ${escapeHtml(runId)}</div>
        <div><strong>Status:</strong> ${escapeHtml(status)}</div>
        <div><strong>Patients:</strong> ${escapeHtml(String(patientCount))}</div>
        <div><strong>Completed:</strong> ${escapeHtml(String(completed))}</div>
        <div><strong>Failed:</strong> ${escapeHtml(String(failed))}</div>
      </div>
      <p class="muted compact">Cohort artifacts are persisted per generated session under workspace sessions and cohort manifest outputs.</p>
    `;
  }

  function derivePipelineSignals() {
    const snapshot = state.snapshot || {};
    const dashboard = snapshot.pipeline_dashboard || {};
    const hasIntake = Boolean(snapshot.session?.complaint_text);
    const hasModel = Boolean(snapshot.has_model);
    const hasAcquisition = Boolean(snapshot.has_pseudodata) && !state.awaitingFreshAcquisition;
    const communicationStage = String(snapshot.communication_summary?.payload?.stage || "").toLowerCase();
    const hasFinalCommunication = communicationStage.startsWith("cycle_");
    const hasAnalysis = Boolean(
      snapshot.has_pipeline_summary ||
      (dashboard.readiness && (dashboard.readiness.tier || dashboard.readiness.label !== "unknown")) ||
      (dashboard.impact?.top_predictors || []).length ||
      dashboard.step03?.status === "generated" ||
      dashboard.step04?.status === "generated"
    );
    const hasIntervention = Boolean(
      (dashboard.step05?.selected_barriers || []).length ||
      String(dashboard.step05?.user_summary || "").trim() ||
      dashboard.step05?.status === "generated" ||
      hasFinalCommunication
    );
    return { hasIntake, hasModel, hasAcquisition, hasAnalysis, hasIntervention };
  }

  function phaseRunningFlags() {
    return {
      model: isRunningStatus(state.componentStatus.step01_operationalization) ||
        isRunningStatus(state.componentStatus.step02_initial_model) ||
        isRunningStatus(state.componentStatus.step04_updated_model),
      acquisition: isRunningStatus(state.componentStatus.pseudodata_collection) ||
        isRunningStatus(state.componentStatus.manual_data_upload),
      analysis: isRunningStatus(state.componentStatus.pipeline_cycle_engine) ||
        isRunningStatus(state.componentStatus.readiness_analysis) ||
        isRunningStatus(state.componentStatus.network_analysis) ||
        isRunningStatus(state.componentStatus.impact_quantification) ||
        isRunningStatus(state.componentStatus.step03_target_selection),
      intervention: isRunningStatus(state.componentStatus.step05_intervention) ||
        isRunningStatus(state.componentStatus.communication_agent),
    };
  }

  function computePhases() {
    const engineFlow = Array.isArray(state.engineFlowFromSummary) ? state.engineFlowFromSummary : [];
    if (engineFlow.length > 0) {
        const mapped = engineFlow.map((row, index) => {
          const rawStatus = String(row.status || "pending").toLowerCase();
          let status = "pending";
          if (rawStatus === "succeeded") status = "done";
          else if (rawStatus === "running") status = "active";
          return {
            key: String(row.stage_id || `stage_${index}`),
            label: String(row.label || row.stage_id || `Stage ${index + 1}`),
            note: String(row.description || ""),
            done: status === "done",
            active: status === "active",
            status,
          };
        });
        if (!mapped.some((row) => row.status === "active")) {
          const next = mapped.find((row) => row.status !== "done");
          if (next) {
            next.status = "active";
            next.active = true;
          }
        }
        return mapped;
    }

    const s = derivePipelineSignals();
    const running = phaseRunningFlags();
    const failed = {
      model:
        normalizeStatus(state.componentStatus.step01_operationalization) === "failed" ||
        normalizeStatus(state.componentStatus.step02_initial_model) === "failed" ||
        normalizeStatus(state.componentStatus.step04_updated_model) === "failed",
      acquisition:
        normalizeStatus(state.componentStatus.pseudodata_collection) === "failed" ||
        normalizeStatus(state.componentStatus.manual_data_upload) === "failed",
      analysis:
        normalizeStatus(state.componentStatus.pipeline_cycle_engine) === "failed" ||
        normalizeStatus(state.componentStatus.readiness_analysis) === "failed" ||
        normalizeStatus(state.componentStatus.network_analysis) === "failed" ||
        normalizeStatus(state.componentStatus.impact_quantification) === "failed" ||
        normalizeStatus(state.componentStatus.step03_target_selection) === "failed",
      intervention:
        normalizeStatus(state.componentStatus.step05_intervention) === "failed" ||
        normalizeStatus(state.componentStatus.communication_agent) === "failed",
    };
    const phases = [
      {
        key: "intake",
        label: "INTAKE",
        note: "Complaint and context captured",
        done: s.hasIntake,
        active: false,
      },
      {
        key: "model",
        label: "MODEL CREATION",
        note: "Operationalization and observation model construction",
        done: s.hasModel && !failed.model,
        active: running.model,
      },
      {
        key: "acquisition",
        label: "ACQUISITION",
        note: state.awaitingFreshAcquisition
          ? "Fresh data required for requested refinement"
          : "Collect or synthesize time-series data",
        done: s.hasAcquisition && !failed.acquisition,
        active: running.acquisition,
      },
      {
        key: "analysis",
        label: "ANALYSIS",
        note: "Readiness, network, impact, and target selection",
        done: s.hasAnalysis && !failed.analysis,
        active: running.analysis,
      },
      {
        key: "intervention",
        label: "INTERVENTION",
        note: "Step-05 intervention translation and final communication output",
        done: s.hasIntervention && !failed.intervention,
        active: running.intervention,
      },
    ];

    let activeIndex = phases.findIndex((phase) => phase.active);
    if (activeIndex === -1) {
      activeIndex = phases.findIndex((phase) => !phase.done);
    }

    const decorated = phases.map((phase, index) => {
      const failedPhase = (phase.key === "model" && failed.model)
        || (phase.key === "acquisition" && failed.acquisition)
        || (phase.key === "analysis" && failed.analysis)
        || (phase.key === "intervention" && failed.intervention);
      if (phase.done) return { ...phase, status: "done" };
      if (failedPhase) return { ...phase, status: "pending" };
      if (index === activeIndex) return { ...phase, status: "active" };
      return { ...phase, status: "pending" };
    });
    return decorated;
  }

  function renderTopbarProgress(phases) {
    if (!UI.topbarPipelineStrip || !UI.topbarPipelineNodes) return;
    if (!phases.length) {
      UI.topbarPipelineStrip.classList.add("hidden");
      UI.topbarPipelineStrip.setAttribute("aria-hidden", "true");
      return;
    }
    UI.topbarPipelineStrip.classList.remove("hidden");
    UI.topbarPipelineStrip.setAttribute("aria-hidden", "false");
    UI.topbarPipelineNodes.innerHTML = phases.map((phase, index) => `
      <span class="topbar-phase-chip topbar-phase-chip--${phase.status}">${escapeHtml(phase.label)}</span>${index < phases.length - 1 ? '<span class="topbar-phase-link">—</span>' : ''}
    `).join("");
  }

  function renderPhaseProgress() {
    const decorated = computePhases();
    state.phaseState = decorated;
    renderTopbarProgress(decorated);

    const runNextLabel = UI.runNextPhaseBtn;
    if (runNextLabel) {
      const next = decorated.find((phase) => phase.status !== "done");
      if (next) {
        runNextLabel.textContent = `Run ${next.label}`;
      } else {
        runNextLabel.textContent = "Run Next Phase";
      }
    }
  }

  function populateCollectionSummary(collection) {
    const node = document.getElementById("collection-summary");
    if (!node) return;
    node.innerHTML = `
      <div><strong>Variables:</strong> ${collection.variable_count ?? 0}</div>
      <div><strong>Criteria:</strong> ${collection.criteria_count ?? 0}</div>
      <div><strong>Predictors:</strong> ${collection.predictor_count ?? 0}</div>
    `;
  }

  function populateCollectionTable(collection) {
    const body = document.querySelector("#collection-table tbody");
    if (!body) return;
    const rows = (collection.variables || []).map((row) => `
      <tr>
        <td><code>${escapeHtml(row.var_id)}</code><br>${escapeHtml(row.label || "")}</td>
        <td>${escapeHtml(row.role || "")}</td>
        <td>${escapeHtml(row.question || "")}</td>
        <td>${escapeHtml(row.response_scale || "")}</td>
        <td>
          <input class="baseline-input" type="number" min="0" max="1" step="0.01"
            value="${row.default_baseline_0_1 ?? 0.5}" data-var-id="${escapeHtml(row.var_id)}">
        </td>
      </tr>
    `);
    body.innerHTML = rows.join("");
  }

  function updateInspectionPanel(snapshot) {
    const setText = (id, value) => {
      const node = document.getElementById(id);
      if (node) node.textContent = String(value);
    };
    const collection = snapshot.collection_schema || {};
    setText("inspect-variables-count", collection.variable_count ?? 0);
    setText("inspect-criteria-count", collection.criteria_count ?? 0);
    setText("inspect-predictors-count", collection.predictor_count ?? 0);
    setText("inspect-visuals-count", (snapshot.visuals || []).length);

    if (!snapshot.communication_summary?.payload) {
      const previewNode = document.getElementById("control-communication-preview");
      if (previewNode) previewNode.textContent = "Communication summary appears after cycle completion.";
    }
  }

  function renderSnapshot() {
    const snapshot = state.snapshot || {};
    const session = snapshot.session || {};
    const sessionNotes = session.notes || {};
    const modelSummary = snapshot.model_summary || {};
    const collection = snapshot.collection_schema || {};
    const visuals = snapshot.visuals || [];
    const pseudoSummary = snapshot.pseudodata_summary || {};
    const pipelineSummary = snapshot.pipeline_summary || {};
    const dashboard = snapshot.pipeline_dashboard || {};
    const cohortSummary = snapshot.cohort_summary || {};
    state.engineFlowFromSummary = Array.isArray(pipelineSummary.engine_stage_flow) ? pipelineSummary.engine_stage_flow : [];
    state.qualityFlowFromSummary = Array.isArray(pipelineSummary.quality_and_research_flow)
      ? pipelineSummary.quality_and_research_flow
      : [];

    if (!state.activeSource) {
      state.awaitingFreshAcquisition = Boolean(sessionNotes.awaiting_fresh_acquisition);
      state.cycleRequestedRefinement = Boolean(sessionNotes.cycle_requested_refinement);
    }
    const refineToggle = document.getElementById("cycle-request-refinement");
    if (refineToggle && !state.activeSource) {
      refineToggle.checked = state.cycleRequestedRefinement;
    }

    const cycleEl = document.getElementById("current-cycle");
    if (cycleEl) cycleEl.textContent = String(session.current_cycle ?? 0);
    const updatedEl = document.getElementById("session-updated");
    if (updatedEl) updatedEl.textContent = session.updated_at || "—";

    const modelSummaryEl = document.getElementById("model-summary");
    if (modelSummaryEl) {
      modelSummaryEl.innerHTML = snapshot.has_model
        ? `
          <div class="meta-grid">
            <div><strong>Criteria:</strong> ${modelSummary.criteria_count ?? 0}</div>
            <div><strong>Predictors:</strong> ${modelSummary.predictor_count ?? 0}</div>
          </div>
          <p>${escapeHtml(modelSummary.model_summary || "")}</p>
        `
        : `<p class="muted">No model artifacts yet. Run model creation first.</p>`;
    }

    const visualGrid = document.getElementById("visual-grid");
    if (visualGrid) {
      if (!visuals.length) {
        visualGrid.innerHTML = `<p class="muted">No visuals generated yet.</p>`;
      } else {
        visualGrid.innerHTML = visuals.map((item) => {
          const relPath = encodeURI(item.relative_path || "");
          const ext = String(item.name || "").toLowerCase();
          const preview = ext.endsWith(".png") || ext.endsWith(".svg") || ext.endsWith(".gif");
          return `
            <a class="visual-card" target="_blank" href="/api/sessions/${sessionId}/files/${relPath}">
              ${preview ? `<img class="visual-thumb" src="/api/sessions/${sessionId}/files/${relPath}" alt="${escapeHtml(item.name)}">` : ""}
              <span>${escapeHtml(item.name)}</span>
            </a>
          `;
        }).join("");
      }
    }

    populateCollectionSummary(collection);
    populateCollectionTable(collection);

    const pseudoNode = document.getElementById("pseudodata-summary");
    if (pseudoNode) {
      pseudoNode.innerHTML = Object.keys(pseudoSummary).length
        ? `<h4>Current pseudodata summary</h4><pre class="json-view">${escapeHtml(JSON.stringify(pseudoSummary, null, 2))}</pre>`
        : "";
    }

    const pipeNode = document.getElementById("pipeline-summary");
    const rawWrap = document.getElementById("pipeline-summary-raw-wrap");
    const rawNode = document.getElementById("pipeline-summary-raw");
    if (pipeNode) {
      if (!Object.keys(pipelineSummary).length) {
        pipeNode.innerHTML = `<p class="muted">No cycle summary yet.</p>`;
        if (rawWrap) rawWrap.classList.add("hidden");
      } else {
        const stages = Array.isArray(pipelineSummary.stage_results) ? pipelineSummary.stage_results : [];
        const engineFlow = Array.isArray(pipelineSummary.engine_stage_flow) ? pipelineSummary.engine_stage_flow : [];
        const supportFlow = Array.isArray(pipelineSummary.quality_and_research_flow)
          ? pipelineSummary.quality_and_research_flow
          : [];
        state.engineFlowFromSummary = engineFlow;
        state.qualityFlowFromSummary = supportFlow;
        const flowTable = (rows, title) => {
          if (!rows.length) return "";
          return `
            <h4>${escapeHtml(title)}</h4>
            <div class="table-wrap">
              <table class="data-table">
                <thead>
                  <tr><th>Stage</th><th>Status</th><th>Source</th><th>Duration (s)</th></tr>
                </thead>
                <tbody>
                  ${rows.map((row) => `
                    <tr>
                      <td>${escapeHtml(String(row.label || row.stage_id || "unknown"))}</td>
                      <td>${escapeHtml(String(row.status || "unknown"))}</td>
                      <td>${escapeHtml(String(row.source_stage || "—"))}</td>
                      <td>${escapeHtml(String(Number(row.duration_seconds || 0).toFixed(3)))}</td>
                    </tr>
                  `).join("")}
                </tbody>
              </table>
            </div>
          `;
        };
        pipeNode.innerHTML = `
          <div class="meta-grid">
            <div><strong>Run ID:</strong> ${escapeHtml(String(pipelineSummary.run_id || "—"))}</div>
            <div><strong>Cycle:</strong> ${escapeHtml(String(pipelineSummary.cycle_index || "—"))}</div>
            <div><strong>Status:</strong> ${escapeHtml(String(pipelineSummary.status || "unknown"))}</div>
            <div><strong>Impact profiles:</strong> ${escapeHtml(String((pipelineSummary.impact_profiles || []).length || 0))}</div>
          </div>
          ${flowTable(engineFlow, "Core Engine Flow")}
          ${flowTable(supportFlow, "Quality + Research Flow")}
          <div class="table-wrap">
            <table class="data-table">
              <thead>
                <tr><th>Stage</th><th>Return code</th><th>Duration (s)</th></tr>
              </thead>
              <tbody>
                ${stages.map((stage) => `
                  <tr>
                    <td>${escapeHtml(String(stage.stage || "unknown"))}</td>
                    <td>${escapeHtml(String(stage.return_code ?? "—"))}</td>
                    <td>${escapeHtml(String(Number(stage.duration_seconds || 0).toFixed(3)))}</td>
                  </tr>
                `).join("")}
              </tbody>
            </table>
          </div>
        `;
        if (rawWrap && rawNode) {
          rawNode.textContent = JSON.stringify(pipelineSummary, null, 2);
          rawWrap.classList.remove("hidden");
        }
      }
    }

    renderDashboard(dashboard);
    renderCommunication(snapshot.communication_summary || {});
    renderCohortSummary(cohortSummary);
    const communicationStage = String(snapshot.communication_summary?.payload?.stage || "").toLowerCase();
    const hasFinalCommunication = communicationStage.startsWith("cycle_");

    state.sectionVisibilityAuto = {
      step01_02: true,
      model_visuals: Boolean(snapshot.has_model),
      data_collection: Boolean(snapshot.has_model),
      cycle: Boolean(snapshot.has_model),
      cohort: true,
      dashboard: Boolean(snapshot.has_pipeline_summary || Object.keys(dashboard).length),
      communication: hasFinalCommunication,
    };
    applySectionVisibility();

    if (snapshot.has_model) {
      setComponentState("step01_operationalization", "succeeded", "Criteria mapped");
      setComponentState("step02_initial_model", "succeeded", "Initial model created");
      if (visuals.length > 0) {
        setComponentState("step02_visualization", "succeeded", "Visual diagnostics ready");
      }
    }
    if (snapshot.has_pseudodata && !state.awaitingFreshAcquisition) {
      setComponentState("pseudodata_collection", "succeeded", "Acquisition completed");
    }
    if (snapshot.has_pipeline_summary) {
      const stageRows = Array.isArray(pipelineSummary.stage_results) ? pipelineSummary.stage_results : [];
      const stageStatus = {};
      stageRows.forEach((row) => {
        const key = String(row.stage || "").trim().toLowerCase();
        if (!key) return;
        const code = Number(row.return_code);
        stageStatus[key] = Number.isFinite(code) && code === 0 ? "succeeded" : "failed";
      });
      const supportRows = Array.isArray(pipelineSummary.quality_and_research_flow)
        ? pipelineSummary.quality_and_research_flow
        : [];
      const supportStatusById = {};
      supportRows.forEach((row) => {
        const key = String(row.stage_id || "").trim();
        if (!key) return;
        supportStatusById[key] = String(row.status || "skipped").toLowerCase();
      });

      setComponentState("pipeline_cycle_engine", "succeeded", "Cycle completed");
      setComponentState("readiness_analysis", "succeeded", "Readiness output available");
      setComponentState("network_analysis", "succeeded", "Network output available");
      if ((dashboard.impact?.top_predictors || []).length > 0) {
        setComponentState("impact_quantification", "succeeded", "Impact output available");
      } else {
        setComponentState("impact_quantification", "idle", "Impact not generated for selected method path");
      }
      if (dashboard.step03?.status === "generated") {
        setComponentState("step03_target_selection", "succeeded", "Targets selected");
      } else {
        setComponentState("step03_target_selection", "idle", "Skipped (no impact profile)");
      }
      if (dashboard.step05?.status === "generated") {
        setComponentState("step05_intervention", "succeeded", "Intervention available");
      } else {
        setComponentState("step05_intervention", "idle", "Skipped (no handoff output)");
      }
      if (stageStatus.visualization === "succeeded" || supportStatusById.impact_visualization_support === "succeeded") {
        setComponentState("impact_visualization", "succeeded", "Support visuals generated");
      } else if (stageStatus.visualization === "failed") {
        setComponentState("impact_visualization", "failed", "Support visualization failed");
      } else {
        setComponentState("impact_visualization", "idle", "Support visualization skipped");
      }
      if (stageStatus.reporting === "succeeded" || supportStatusById.research_reporting_support === "succeeded") {
        setComponentState("evaluation_reporting", "succeeded", "Research report generated");
      } else if (stageStatus.reporting === "failed") {
        setComponentState("evaluation_reporting", "failed", "Research reporting failed");
      } else {
        setComponentState("evaluation_reporting", "idle", "Support reporting skipped");
      }
      if (dashboard.step04?.status === "generated" && (dashboard.step04?.recommended_predictors || []).length > 0) {
        setComponentState("step04_updated_model", "succeeded", "Updated model available");
      } else if (dashboard.step04?.status === "skipped") {
        setComponentState("step04_updated_model", "idle", "Skipped (no Step-03 targets)");
      }
      const commStage = String(snapshot.communication_summary?.payload?.stage || "").toLowerCase();
      if (commStage.startsWith("cycle_")) {
        setComponentState("communication_agent", "succeeded", "Summary generated");
      } else {
        setComponentState("communication_agent", "idle", "Generated after final cycle stage");
      }
    }
    if (Object.keys(cohortSummary).length) {
      const cohortStatus = String(cohortSummary.status || "").toLowerCase();
      if (cohortStatus === "succeeded") {
        setComponentState("cohort_batch", "succeeded", "Cohort run completed");
      } else if (cohortStatus === "failed") {
        setComponentState("cohort_batch", "failed", "Cohort run has failed patients");
      } else if (cohortStatus === "running") {
        setComponentState("cohort_batch", "running", "Cohort run in progress");
      }
    }
    syncRuntimeCardVisibility();

    updateInspectionPanel(snapshot);
    renderPhaseProgress();
    refreshTimeSeries(snapshot).catch((err) => {
      updateTimeSeriesStatus(`Time-series load failed: ${err.message || err}`);
    });
    syncControlStates();
  }

  function parseComponentFromLog(line) {
    const text = String(line || "");
    const componentMarker = text.match(/\[component:([a-z0-9_]+)\]\s+status=([a-z_]+)(?:\s+(.*))?/i);
    if (componentMarker) {
      const rawStatus = String(componentMarker[2] || "").toLowerCase();
      return {
        componentId: componentMarker[1],
        status: rawStatus === "heartbeat" ? "running" : componentMarker[2],
        detail: rawStatus === "heartbeat"
          ? `Still running ${String(componentMarker[3] || "").trim()}`
          : (componentMarker[3] || "").trim(),
      };
    }
    const low = text.toLowerCase();
    if (low.includes("llm.health_check.start")) {
      return {
        componentId: "pipeline_cycle_engine",
        status: "running",
        detail: "Running LLM startup health check",
      };
    }
    if (low.includes("llm.health_check.failed")) {
      return {
        componentId: "pipeline_cycle_engine",
        status: "running",
        detail: "LLM unavailable; fallback mode enabled where supported",
      };
    }
    if (low.includes("llm.health_check.ok") || low.includes("llm.health_check.passed")) {
      return {
        componentId: "pipeline_cycle_engine",
        status: "running",
        detail: "LLM startup health check passed",
      };
    }
    const stageEvent = low.match(
      /\b(operationalization|initial_model|pseudodata|readiness|network|impact|handoff|intervention|translation_communication|visualization|reporting|pipeline)\.(start|done|failed|skipped|dry_run|parallel_start)\b/,
    );
    if (stageEvent) {
      const stage = stageEvent[1];
      const event = stageEvent[2];
      const stageToComponent = {
        operationalization: "step01_operationalization",
        initial_model: "step02_initial_model",
        pseudodata: "pseudodata_collection",
        readiness: "readiness_analysis",
        network: "network_analysis",
        impact: "impact_quantification",
        handoff: "step03_target_selection",
        intervention: "step05_intervention",
        translation_communication: "communication_agent",
        visualization: "impact_visualization",
        reporting: "evaluation_reporting",
        pipeline: "pipeline_cycle_engine",
      };
      const componentId = stageToComponent[stage] || "pipeline_cycle_engine";
      if (event === "start" || event === "parallel_start") {
        return {
          componentId,
          status: "running",
          detail: event === "parallel_start" ? "Running in parallel branch" : "Stage started",
        };
      }
      if (event === "done") return { componentId, status: "succeeded", detail: "Stage completed" };
      if (event === "failed") return { componentId, status: "failed", detail: "Stage failed" };
      return { componentId, status: "idle", detail: "Stage skipped" };
    }
    if (low.includes("apiconnectionerror") || low.includes("provider_unavailable")) {
      return {
        componentId: state.activeJobKind === "pipeline_cycle" ? "pipeline_cycle_engine" : "step02_initial_model",
        status: "running",
        detail: "LLM provider unavailable; fallback path in use",
      };
    }
    if (low.includes("heuristic_fallback_llm_failure")) {
      return {
        componentId: "step05_intervention",
        status: "succeeded",
        detail: "Fallback intervention generated (LLM unavailable)",
      };
    }
    if (low.includes("worker error")) {
      return {
        componentId: state.activeJobKind === "pipeline_cycle" ? "pipeline_cycle_engine" : "step02_initial_model",
        status: "failed",
        detail: "Worker error",
      };
    }
    if (low.includes("llm call start")) {
      return { componentId: "step02_initial_model", status: "running", detail: "LLM generation in progress" };
    }
    if (low.includes("llm call ok")) {
      return { componentId: "step02_initial_model", status: "running", detail: "LLM response received; validating output" };
    }
    if (low.includes("auto-repair: attempt")) {
      return { componentId: "step02_initial_model", status: "running", detail: "Auto-repair pass running" };
    }
    if (low.includes("critic loop")) {
      return { componentId: "step02_initial_model", status: "running", detail: "Critic/guardrail validation loop" };
    }
    if (low.includes("running step 01")) return { componentId: "step01_operationalization", status: "running", detail: "Processing complaint" };
    if (low.includes("running step 02")) return { componentId: "step02_initial_model", status: "running", detail: "Constructing initial model" };
    if (low.includes("generating step 02 visualizations")) return { componentId: "step02_visualization", status: "running", detail: "Rendering model figures" };
    if (low.includes("running integrated phoenix analysis cycle")) return { componentId: "pipeline_cycle_engine", status: "running", detail: "Running cycle stages" };
    if (low.includes("03_readiness_check") || low.includes("00_readiness_check")) {
      return { componentId: "readiness_analysis", status: "running", detail: "Readiness diagnostics" };
    }
    if (low.includes("04_time_series_analysis") || low.includes("01_time_series_analysis")) {
      return { componentId: "network_analysis", status: "running", detail: "Network estimation" };
    }
    if (low.includes("05_momentary_impact_coefficients") || low.includes("02_momentary_impact")) {
      return { componentId: "impact_quantification", status: "running", detail: "Impact quantification" };
    }
    if (low.includes("06_target_identification_and_model_update") || low.includes("03_treatment_target_handoff")) {
      return { componentId: "step03_target_selection", status: "running", detail: "Target handoff and model update" };
    }
    if (low.includes("step04_updated_observation_model")) return { componentId: "step04_updated_model", status: "running", detail: "Updated model synthesis" };
    if (low.includes("07_hapa_digital_intervention") || low.includes("03b_translation_digital_intervention")) {
      return { componentId: "step05_intervention", status: "running", detail: "Intervention translation" };
    }
    if (low.includes("08_treatment_translation_communication") || low.includes("06_treatment_translation_communication") || low.includes("translation_communication")) {
      return { componentId: "communication_agent", status: "running", detail: "Final treatment communication" };
    }
    if (low.includes("09_impact_visualizations") || low.includes("visualization_run_summary")) {
      return { componentId: "impact_visualization", status: "running", detail: "Generating support visuals" };
    }
    if (low.includes("10_research_reports") || low.includes("run_report.json")) {
      return { componentId: "evaluation_reporting", status: "running", detail: "Generating research report" };
    }
    if (low.includes("communication summary")) return { componentId: "communication_agent", status: "running", detail: "Communication pass" };
    return null;
  }

  function kindFromPath(path) {
    if (path.includes("/initial-model")) return "initial_model";
    if (path.includes("/synthesize")) return "synthesize_pseudodata";
    if (path.includes("/manual-data")) return "manual_data_upload";
    if (path.includes("/run-cycle")) return "pipeline_cycle";
    if (path.includes("/full-cohort")) return "full_cohort";
    return "";
  }

  function primeComponentsForJob(kind) {
    const list = JOB_KIND_COMPONENTS[kind] || [];
    list.forEach((componentId) => {
      const current = state.componentStatus[componentId] || "idle";
      if (!isRunningStatus(current)) setComponentState(componentId, "queued", "Queued");
    });
    if (list.length) setActiveComponent(list[0], "queued");
  }

  function finalizeComponentsForJob(kind, status) {
    const safe = normalizeStatus(status);
    const list = JOB_KIND_COMPONENTS[kind] || [];
    list.forEach((componentId) => {
      const current = state.componentStatus[componentId] || "idle";
      if (safe === "succeeded" && isRunningStatus(current)) {
        setComponentState(componentId, "succeeded", "Completed");
      }
      if (safe === "failed" && isRunningStatus(current)) {
        setComponentState(componentId, "failed", "Failed");
      }
    });
    setActiveComponent("idle", "idle");
  }

  async function refreshSnapshot() {
    const response = await apiGet(`/api/sessions/${sessionId}/snapshot`);
    state.snapshot = response.snapshot || {};
    renderSnapshot();
  }

  function clearStreamReconnectTimer() {
    if (state.streamReconnectTimer) {
      clearTimeout(state.streamReconnectTimer);
      state.streamReconnectTimer = null;
    }
  }

  async function finalizeJobFromStatus(jobId, finalStatus, kind, errorMessage = "") {
    const marker = `${jobId}:${finalStatus}`;
    if (state.lastTerminalJobMarker === marker) return;
    state.lastTerminalJobMarker = marker;
    clearStreamReconnectTimer();
    state.streamReconnectAttempts = 0;
    state.activeJobKind = kind || state.activeJobKind;
    setJobMeta(jobId, finalStatus);
    appendLog(`[frontend] Job ${jobId} finished with status=${finalStatus}`);
    pushRuntimeEvent(`Job ${jobId} finished with status ${finalStatus.toUpperCase()}`);

    if (errorMessage) {
      appendLog(`[frontend] Error: ${errorMessage}`);
      showError(errorMessage);
    } else {
      showError("");
    }

    if (state.activeJobKind === "pipeline_cycle" && finalStatus === "succeeded") {
      state.awaitingFreshAcquisition = state.cycleRequestedRefinement;
    }
    if (["synthesize_pseudodata", "manual_data_upload"].includes(state.activeJobKind) && finalStatus === "succeeded") {
      state.awaitingFreshAcquisition = false;
    }

    finalizeComponentsForJob(state.activeJobKind, finalStatus);

    if (state.activeSource) {
      state.activeSource.close();
      state.activeSource = null;
    }

    setButtonLoading(state.activeTriggerButtonId, false);
    state.activeTriggerButtonId = "";
    syncControlStates();
    try {
      await refreshSnapshot();
    } catch (err) {
      appendLog(`[frontend] Snapshot refresh failed: ${err.message || err}`);
    }
  }

  function scheduleStreamReconnect(jobId) {
    if (state.streamReconnectTimer) return;
    state.streamReconnectAttempts += 1;
    const attempt = state.streamReconnectAttempts;
    const delayMs = Math.min(6000, 400 * (2 ** Math.min(attempt, 4)));
    state.streamReconnectTimer = window.setTimeout(async () => {
      state.streamReconnectTimer = null;
      if (state.activeJobId !== jobId) return;
      try {
        const payload = await apiGet(`/api/jobs/${jobId}`);
        const job = payload.job || {};
        const status = normalizeStatus(job.status || "running");
        if (status === "succeeded" || status === "failed") {
          await finalizeJobFromStatus(jobId, status, String(job.kind || state.activeJobKind), String(job.error || ""));
          return;
        }
        const cursor = Number(state.streamCursorByJob[jobId] || 0);
        appendLog(`[frontend] Reconnecting stream for ${jobId} from cursor=${cursor} (attempt ${attempt}).`);
        attachStream(jobId, String(job.kind || state.activeJobKind), cursor, true);
      } catch (err) {
        appendLog(`[frontend] Stream reconnect check failed: ${err.message || err}`);
        scheduleStreamReconnect(jobId);
      }
    }, delayMs);
  }

  function attachStream(jobId, kindHint = "", afterCursor = 0, reconnecting = false) {
    if (state.activeSource) {
      state.activeSource.close();
      state.activeSource = null;
    }
    clearStreamReconnectTimer();
    state.activeJobId = jobId;
    state.activeJobKind = kindHint || state.activeJobKind;
    const seedCursor = Math.max(0, Number(afterCursor || state.streamCursorByJob[jobId] || 0) || 0);
    state.streamCursorByJob[jobId] = seedCursor;
    setJobMeta(jobId, "running");
    syncControlStates();
    if (reconnecting) {
      appendLog(`[frontend] Reconnected to job ${jobId}.`);
      pushRuntimeEvent(`Reconnected to job ${jobId}`);
    } else {
      appendLog(`[frontend] Connected to job ${jobId}`);
      pushRuntimeEvent(`Connected to job ${jobId}`);
      setLogsDrawerOpen(true);
    }

    const streamUrl = seedCursor > 0
      ? `/api/jobs/${jobId}/stream?after=${seedCursor}`
      : `/api/jobs/${jobId}/stream`;
    state.activeSource = new EventSource(streamUrl);
    state.activeSource.onmessage = (event) => {
      let payload = {};
      try {
        payload = JSON.parse(event.data || "{}");
      } catch {
        payload = {};
      }

      if (payload.type === "log") {
        const entry = payload.entry || {};
        const idx = Number(entry.index);
        if (Number.isFinite(idx)) {
          state.streamCursorByJob[jobId] = Math.max(Number(state.streamCursorByJob[jobId] || 0), idx);
        }
        const line = String(entry.line || "");
        const low = line.toLowerCase();
        appendLog(`[${entry.timestamp || ""}] [${entry.level || "INFO"}] ${line}`);
        const parsed = parseComponentFromLog(line);
        if (parsed?.componentId) {
          setComponentState(parsed.componentId, parsed.status || "running", parsed.detail || line.slice(0, 140));
          setActiveComponent(parsed.componentId, parsed.status || "running");
        }
        if (low.includes("handoff.start")) {
          setComponentState("step04_updated_model", "running", "Updated model synthesis");
        }
        if (low.includes("handoff.done")) {
          setComponentState("step04_updated_model", "succeeded", "Updated model available");
        }
        if (low.includes("cohort_batch")) {
          setComponentState("cohort_batch", parsed?.status || "running", parsed?.detail || "Cohort orchestration");
          setActiveComponent("cohort_batch", parsed?.status || "running");
        }
        return;
      }

      if (payload.type === "heartbeat") {
        const cursor = Number(payload.cursor);
        if (Number.isFinite(cursor)) {
          state.streamCursorByJob[jobId] = Math.max(Number(state.streamCursorByJob[jobId] || 0), cursor);
        }
        return;
      }

      if (payload.type === "status") {
        const finalStatus = normalizeStatus(payload.status || "idle");
        const cursor = Number(payload.cursor);
        if (Number.isFinite(cursor)) {
          state.streamCursorByJob[jobId] = Math.max(Number(state.streamCursorByJob[jobId] || 0), cursor);
        }
        finalizeJobFromStatus(jobId, finalStatus, String(payload.kind || state.activeJobKind), String(payload.error || ""))
          .catch((err) => appendLog(`[frontend] Finalize job failed: ${err.message || err}`));
      }
    };

    state.activeSource.onerror = () => {
      if (state.activeJobId !== jobId) return;
      if (state.activeSource) {
        state.activeSource.close();
        state.activeSource = null;
      }
      appendLog(`[frontend] Stream disconnected for ${jobId}; retrying…`);
      scheduleStreamReconnect(jobId);
    };
  }

  async function launchJob(path, payload, triggerButtonId, processingLabel) {
    const kind = kindFromPath(path);
    appendLog(`[frontend] Launching job at ${path}`);
    pushRuntimeEvent(`Launching ${kind || "job"}`);
    showError("");
    if (kind) primeComponentsForJob(kind);
    state.activeTriggerButtonId = triggerButtonId || "";
    setButtonLoading(triggerButtonId, true, processingLabel || "Processing…");
    if (kind === "pipeline_cycle") {
      state.cycleRequestedRefinement = Boolean(payload?.request_model_refinement);
    }
    const result = await apiPost(path, payload);
    state.lastTerminalJobMarker = "";
    state.streamCursorByJob[result.job_id] = 0;
    attachStream(result.job_id, kind);
  }

  function bindActions() {
    document.getElementById("run-initial-model-btn")?.addEventListener("click", async () => {
      try {
        await launchJob(
          `/api/sessions/${sessionId}/jobs/initial-model`,
          {
            llm_model: document.getElementById("initial-llm-model")?.value || "gpt-5-nano",
            disable_llm: Boolean(document.getElementById("initial-disable-llm")?.checked),
            prompt_budget_tokens: Number(document.getElementById("initial-prompt-budget")?.value || 400000),
            max_workers: Number(document.getElementById("initial-max-workers")?.value || 12),
            critic_max_iterations: Number(document.getElementById("initial-critic-iterations")?.value || 2),
            critic_pass_threshold: Number(document.getElementById("initial-critic-threshold")?.value || 0.74),
            hard_ontology_constraint: Boolean(document.getElementById("initial-hard-ontology")?.checked),
          },
          "run-initial-model-btn",
          "Processing model creation…",
        );
      } catch (err) {
        appendLog(`[frontend] ${err.message}`);
        setButtonLoading("run-initial-model-btn", false);
        state.activeTriggerButtonId = "";
        setJobMeta(state.activeJobId, "failed");
        showError(err.message);
        syncControlStates();
      }
    });

    document.getElementById("synthesize-btn")?.addEventListener("click", async () => {
      try {
        await launchJob(
          `/api/sessions/${sessionId}/jobs/synthesize`,
          {
            n_points: Number(document.getElementById("synth-points")?.value || 84),
            missing_rate: Number(document.getElementById("synth-missing")?.value || 0.1),
            seed: Number(document.getElementById("synth-seed")?.value || 42),
            baselines: readBaselines(),
          },
          "synthesize-btn",
          "Synthesizing data…",
        );
      } catch (err) {
        appendLog(`[frontend] ${err.message}`);
        setButtonLoading("synthesize-btn", false);
        state.activeTriggerButtonId = "";
        setJobMeta(state.activeJobId, "failed");
        showError(err.message);
        syncControlStates();
      }
    });

    document.getElementById("manual-upload-btn")?.addEventListener("click", async () => {
      const csvText = document.getElementById("manual-csv")?.value || "";
      if (!csvText.trim()) {
        appendLog("[frontend] Manual CSV is empty.");
        return;
      }
      try {
        await launchJob(
          `/api/sessions/${sessionId}/jobs/manual-data`,
          { csv_text: csvText },
          "manual-upload-btn",
          "Saving data…",
        );
      } catch (err) {
        appendLog(`[frontend] ${err.message}`);
        setButtonLoading("manual-upload-btn", false);
        state.activeTriggerButtonId = "";
        setJobMeta(state.activeJobId, "failed");
        showError(err.message);
        syncControlStates();
      }
    });

    document.getElementById("run-cycle-btn")?.addEventListener("click", async () => {
      const requestRefinement = Boolean(document.getElementById("cycle-request-refinement")?.checked);
      const includeIntervention = Boolean(document.getElementById("cycle-include-intervention")?.checked);
      try {
        await launchJob(
          `/api/sessions/${sessionId}/jobs/run-cycle`,
          {
            llm_model: document.getElementById("cycle-llm-model")?.value || "gpt-5-nano",
            profile_memory_window: Number(document.getElementById("cycle-memory-window")?.value || 3),
            handoff_critic_max_iterations: Number(document.getElementById("cycle-handoff-critic-iterations")?.value || 2),
            handoff_critic_pass_threshold: Number(document.getElementById("cycle-handoff-critic-threshold")?.value || 0.74),
            intervention_critic_max_iterations: Number(document.getElementById("cycle-intervention-critic-iterations")?.value || 2),
            intervention_critic_pass_threshold: Number(document.getElementById("cycle-intervention-critic-threshold")?.value || 0.74),
            network_boot: Number(document.getElementById("cycle-network-boot")?.value || 40),
            network_block_len: Number(document.getElementById("cycle-network-block-len")?.value || 14),
            network_jobs: Number(document.getElementById("cycle-network-jobs")?.value || 4),
            run_impact_visualizations: Boolean(document.getElementById("cycle-run-visualizations")?.checked),
            run_treatment_communication: Boolean(document.getElementById("cycle-run-communication")?.checked),
            parallel_branches: Boolean(document.getElementById("cycle-parallel-branches")?.checked),
            hard_ontology_constraint: Boolean(document.getElementById("cycle-hard-ontology")?.checked),
            disable_llm: Boolean(document.getElementById("cycle-disable-llm")?.checked),
            request_model_refinement: requestRefinement,
            include_intervention: includeIntervention,
          },
          "run-cycle-btn",
          requestRefinement ? "Running analysis + refinement…" : "Running analysis…",
        );
      } catch (err) {
        appendLog(`[frontend] ${err.message}`);
        setButtonLoading("run-cycle-btn", false);
        state.activeTriggerButtonId = "";
        setJobMeta(state.activeJobId, "failed");
        showError(err.message);
        syncControlStates();
      }
    });

    document.getElementById("run-cohort-btn")?.addEventListener("click", async () => {
      try {
        await launchJob(
          `/api/sessions/${sessionId}/jobs/full-cohort`,
          {
            patient_count: Number(document.getElementById("cohort-patient-count")?.value || 10),
            parallel_patients: Number(document.getElementById("cohort-parallel-patients")?.value || 2),
            llm_model: document.getElementById("cohort-llm-model")?.value || "gpt-5-nano",
            disable_llm: Boolean(document.getElementById("cohort-disable-llm")?.checked),
            n_points: Number(document.getElementById("cohort-pseudodata-points")?.value || 84),
            missing_rate: Number(document.getElementById("cohort-pseudodata-missing")?.value || 0.1),
            seed: Number(document.getElementById("cohort-pseudodata-seed")?.value || 42),
            include_intervention: Boolean(document.getElementById("cohort-include-intervention")?.checked),
            run_impact_visualizations: Boolean(document.getElementById("cohort-run-visualizations")?.checked),
            run_treatment_communication: Boolean(document.getElementById("cohort-run-communication")?.checked),
            parallel_branches: Boolean(document.getElementById("cohort-parallel-branches")?.checked),
          },
          "run-cohort-btn",
          "Running cohort pipeline…",
        );
      } catch (err) {
        appendLog(`[frontend] ${err.message}`);
        setButtonLoading("run-cohort-btn", false);
        state.activeTriggerButtonId = "";
        setJobMeta(state.activeJobId, "failed");
        showError(err.message);
        syncControlStates();
      }
    });

    document.getElementById("timeseries-variable-select")?.addEventListener("change", () => {
      renderTimeSeriesChart();
    });
    document.getElementById("timeseries-window-select")?.addEventListener("change", () => {
      renderTimeSeriesChart();
    });

    UI.runNextPhaseBtn?.addEventListener("click", () => {
      const phases = state.phaseState || [];
      const next = phases.find((phase) => phase.status !== "done");
      if (!next) {
        appendLog("[frontend] All phases completed for the current iteration.");
        return;
      }
      if (next.key === "model") {
        document.getElementById("run-initial-model-btn")?.click();
        return;
      }
      if (next.key === "acquisition") {
        document.getElementById("synthesize-btn")?.click();
        return;
      }
      if (next.key === "analysis" || next.key === "intervention") {
        const includeInterventionToggle = document.getElementById("cycle-include-intervention");
        if (includeInterventionToggle && next.key === "intervention") {
          includeInterventionToggle.checked = true;
        }
        document.getElementById("run-cycle-btn")?.click();
        return;
      }
      appendLog(`[frontend] ${next.label} has no executable action.`);
    });

    UI.logsDrawerOpenBtn?.addEventListener("click", () => {
      setControlDrawerOpen(false);
      setLogsDrawerOpen(true);
    });
    UI.logsDrawerCloseBtn?.addEventListener("click", () => setLogsDrawerOpen(false));
    UI.controlDrawerOpenBtn?.addEventListener("click", () => {
      setLogsDrawerOpen(false);
      setControlDrawerOpen(true);
    });
    UI.controlDrawerCloseBtn?.addEventListener("click", () => setControlDrawerOpen(false));
    UI.openLogsFromControlBtn?.addEventListener("click", () => {
      setControlDrawerOpen(false);
      setLogsDrawerOpen(true);
    });
    UI.drawerBackdrop?.addEventListener("click", () => closeDrawers());

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeDrawers();
    });
  }

  initRuntimeMap();
  initCollapsibleSections();
  initSectionVisibilityControls();
  bindActions();
  bindModelCatalogAutocomplete();
  setJobMeta("none", "idle");
  setActiveComponent("idle", "idle");
  renderRuntimeEvents();
  renderSnapshot();
})();
