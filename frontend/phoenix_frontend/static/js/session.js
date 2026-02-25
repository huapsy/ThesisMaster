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
    if (typeof switchTab === 'function') switchTab('logs');
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
    const dropdown = document.getElementById("llm-autocomplete-dropdown");
    if (!dropdown) return;
    const rows = Array.isArray(models) ? models : [];
    state._llmCatalog = rows;
    if (!rows.length) {
      dropdown.innerHTML = `<div class="autocomplete-item muted">No models found</div>`;
      return;
    }
    dropdown.innerHTML = rows.slice(0, 40).map((row) => {
      const id = String(row.id || "").trim();
      if (!id) return "";
      return `<div class="autocomplete-item" data-model-id="${escapeHtml(id)}"><span class="model-id">${escapeHtml(id)}</span></div>`;
    }).join("");
  }

  function showLlmDropdown() {
    const dropdown = document.getElementById("llm-autocomplete-dropdown");
    if (dropdown) dropdown.classList.remove("hidden");
  }
  function hideLlmDropdown() {
    setTimeout(() => {
      const dropdown = document.getElementById("llm-autocomplete-dropdown");
      if (dropdown) dropdown.classList.add("hidden");
    }, 180);
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

    /* Click handler on the dropdown */
    const dropdown = document.getElementById("llm-autocomplete-dropdown");
    if (dropdown) {
      dropdown.addEventListener("mousedown", (e) => {
        e.preventDefault(); /* prevent blur */
        const item = e.target.closest(".autocomplete-item");
        if (!item) return;
        const modelId = item.dataset.modelId;
        if (!modelId) return;
        /* Set ALL visible LLM model inputs to the selected model */
        inputs.forEach((inp) => { if (inp) inp.value = modelId; });
        hideLlmDropdown();
      });
    }

    inputs.forEach((node) => {
      node?.addEventListener("focus", () => {
        if (!state.llmModelLoaded) scheduleLlmModelFetch("");
        showLlmDropdown();
      });
      node?.addEventListener("blur", hideLlmDropdown);
      node?.addEventListener("input", (event) => {
        const value = String(event?.target?.value || "");
        if (value.length >= 1) {
          scheduleLlmModelFetch(value);
        } else if (!state.llmModelLoaded) {
          scheduleLlmModelFetch("");
        }
        showLlmDropdown();
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

  const SERIES_COLORS = [
    "#4f8dff",
    "#11c4a5",
    "#f59f3a",
    "#e4588f",
    "#8d6bff",
    "#18b6d9",
    "#f06d5f",
    "#6ccf5f",
    "#f2c84b",
    "#4bc0ff",
    "#ff7ab6",
    "#a5b4fc",
  ];

  function colorForSeries(index, alpha = 1) {
    const idx = Math.abs(Number(index) || 0) % SERIES_COLORS.length;
    const hex = SERIES_COLORS[idx];
    if (alpha >= 1) return hex;
    const rgb = hex.replace("#", "");
    const r = parseInt(rgb.slice(0, 2), 16);
    const g = parseInt(rgb.slice(2, 4), 16);
    const b = parseInt(rgb.slice(4, 6), 16);
    return `rgba(${r}, ${g}, ${b}, ${Math.max(0, Math.min(1, alpha))})`;
  }

  function buildVarLabelMap(snapshot) {
    const map = {};
    const schemaVars = snapshot?.collection_schema?.variables || [];
    schemaVars.forEach((row) => {
      const varId = String(row?.var_id || "").trim();
      if (!varId) return;
      const label = String(row?.label || "").trim();
      if (label) map[varId] = label;
    });
    const opVars = snapshot?.operationalization_summary?.variables || [];
    opVars.forEach((row) => {
      const varId = String(row?.var_id || "").trim();
      if (!varId || map[varId]) return;
      const label = String(row?.label || "").trim();
      if (label) map[varId] = label;
    });
    return map;
  }

  function toDisplayLabel(varId, labelMap) {
    const token = String(varId || "").trim();
    const label = String((labelMap || {})[token] || token).trim();
    if (!token) return label || "unknown";
    if (!label || label === token) return token;
    return `${label} (${token})`;
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
    const labelMap = buildVarLabelMap(snapshot);
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
      labelMap,
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
    const labelMap = data?.labelMap || {};
    const rows = [`<option value="__all__">All variables</option>`];
    columns.forEach((name) => {
      rows.push(`<option value="${escapeHtml(name)}">${escapeHtml(toDisplayLabel(name, labelMap))}</option>`);
    });
    variableSelect.innerHTML = rows.join("");
    if (current && columns.includes(current)) {
      variableSelect.value = current;
    } else if (current === "__all__") {
      variableSelect.value = "__all__";
    } else {
      variableSelect.value = "__all__";
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
    if (!signal || (signal !== "__all__" && !data.series[signal])) {
      updateTimeSeriesStatus("Select a signal to display time-series data.");
      return;
    }

    const windowRaw = String(windowSelect.value || "all");
    const requestedWindow = windowRaw === "all" ? data.x.length : Math.max(1, Number(windowRaw) || data.x.length);
    const start = Math.max(0, data.x.length - requestedWindow);
    const xSlice = data.x.slice(start);
    const dateSlice = data.dates.slice(start);
    const labelMap = data.labelMap || {};
    const signalColumns = signal === "__all__" ? data.columns : [signal];
    const datasets = signalColumns.map((column) => {
      const ySlice = (data.series[column] || []).slice(start);
      const baseIndex = Math.max(0, data.columns.indexOf(column));
      const color = colorForSeries(baseIndex, 1);
      return {
        label: toDisplayLabel(column, labelMap),
        data: ySlice,
        borderColor: color,
        backgroundColor: colorForSeries(baseIndex, signal === "__all__" ? 0.08 : 0.16),
        tension: 0.2,
        pointRadius: signal === "__all__" ? 1.2 : 1.8,
        pointHoverRadius: signal === "__all__" ? 2.2 : 3.2,
        borderWidth: signal === "__all__" ? 1.8 : 2.2,
        spanGaps: true,
      };
    });

    if (state.timeSeriesChart && typeof state.timeSeriesChart.destroy === "function") {
      state.timeSeriesChart.destroy();
    }
    state.timeSeriesChart = new Chart(canvas, {
      type: "line",
      data: {
        labels: xSlice,
        datasets,
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: true, labels: { color: "#c6d8f3", boxWidth: 12 } },
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
    if (signal === "__all__") {
      const aggregateMissing = signalColumns.reduce((acc, col) => {
        const ys = (data.series[col] || []).slice(start);
        return acc + ys.filter((v) => v == null).length;
      }, 0);
      updateTimeSeriesStatus(
        `Signals=${signalColumns.length} | points=${xSlice.length} / ${data.x.length} | missing cells=${aggregateMissing}`,
      );
    } else {
      const ySlice = (data.series[signal] || []).slice(start);
      updateTimeSeriesStatus(
        `Signal=${toDisplayLabel(signal, labelMap)} | points=${xSlice.length} / ${data.x.length} | missing=${ySlice.filter((v) => v == null).length}`,
      );
    }
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
    const labelMap = buildVarLabelMap(state.snapshot || {});
    const topPredictorName = topPredictor.predictor_display
      || topPredictor.predictor_label
      || toDisplayLabel(topPredictor.predictor || "", labelMap)
      || "—";

    const setText = (id, value) => {
      const node = document.getElementById(id);
      if (node) node.textContent = value;
    };
    setText("metric-readiness-score", `${Number(readiness.score_0_100 || 0).toFixed(1)}`);
    setText("metric-readiness-label", readiness.label || "unknown");
    setText("metric-tier", readiness.tier || "—");
    setText("metric-variant", readiness.tier3_variant || "—");
    setText("metric-top-predictor", topPredictorName);
    setText(
      "metric-top-predictor-score",
      topPredictor.score_0_1 != null ? Number(topPredictor.score_0_1).toFixed(3) : "—",
    );
    setText("metric-barrier-count", String((step05.selected_barriers || []).length || 0));
  }

  function renderDashboard(dashboard) {
    renderMetricCards(dashboard);
    destroyCharts();
    const labelMap = buildVarLabelMap(state.snapshot || {});

    const impactRows = (dashboard.impact?.top_predictors || []).slice(0, 8);
    const barrierRows = (dashboard.step05?.selected_barriers || []).slice(0, 8);
    const copingRows = (dashboard.step05?.selected_coping || []).slice(0, 8);

    state.impactChart = buildBarChart(
      "chart-impact",
      impactRows.map((x) => x.predictor_display || x.predictor_label || toDisplayLabel(x.predictor || "", labelMap) || "n/a"),
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
      const p = row.predictor_label || toDisplayLabel(row.predictor || "", labelMap) || "unknown";
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
    const predictorRows = Array.isArray(step04.recommended_predictor_rows)
      ? step04.recommended_predictor_rows
      : [];
    if (predictorRows.length) {
      const predictorText = predictorRows
        .map((row) => toDisplayLabel(row?.predictor || "", { ...(labelMap || {}), [String(row?.predictor || "")]: String(row?.label || "") }))
        .join(", ");
      step04Rows.push(`Predictors (${predictorRows.length}): ${predictorText}`);
    } else if ((step04.recommended_predictors || []).length) {
      const predictorText = (step04.recommended_predictors || []).map((id) => toDisplayLabel(id, labelMap)).join(", ");
      step04Rows.push(`Predictors (${step04.recommended_predictors.length}): ${predictorText}`);
    }
    if ((step04.retained_criteria_ids || []).length) {
      const retained = (step04.retained_criteria_ids || []).map((id) => toDisplayLabel(id, labelMap)).join(", ");
      step04Rows.push(`Retained criteria (${step04.retained_criteria_ids.length}): ${retained}`);
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

    /* HAPA Intervention Message — prominent panel in Dashboard */
    const interventionPanel = document.getElementById("panel-intervention-message");
    const interventionText = document.getElementById("dashboard-intervention-message");
    const interventionStructured = document.getElementById("dashboard-intervention-structure");
    if (interventionPanel && interventionText) {
      if (summary) {
        interventionText.textContent = summary;
        const selectedTargets = (dashboard.step05?.selected_targets || []).slice(0, 5);
        const selectedBarriers = (dashboard.step05?.selected_barriers || []).slice(0, 6);
        const selectedCoping = (dashboard.step05?.selected_coping || []).slice(0, 6);
        const hapaPlan = (dashboard.step05?.hapa_component_plan || []).slice(0, 4);
        const phasedPlan = (dashboard.step05?.phased_delivery_plan || []).slice(0, 3);
        const monitoring = (dashboard.step05?.monitoring_plan || []).slice(0, 5);
        const safety = (dashboard.step05?.safety_notes || []).slice(0, 4);

        const mkList = (rows, fn, emptyText) => (
          Array.isArray(rows) && rows.length
            ? `<ul>${rows.map((item) => `<li>${fn(item)}</li>`).join("")}</ul>`
            : `<p class="muted compact">${escapeHtml(emptyText)}</p>`
        );

        if (interventionStructured) {
          interventionStructured.innerHTML = `
            <div class="detail-grid" style="margin-top:10px">
              <article class="detail-card">
                <h3>Selected Treatment Targets</h3>
                ${mkList(
                  selectedTargets,
                  (item) => `${escapeHtml(String(item.predictor_label || item.predictor || "target"))} (priority=${Number(item.priority_0_1 || 0).toFixed(3)})`,
                  "No treatment targets reported.",
                )}
              </article>
              <article class="detail-card">
                <h3>Top Barriers</h3>
                ${mkList(
                  selectedBarriers,
                  (item) => `${escapeHtml(String(item.barrier_name || "barrier"))} (score=${Number(item.score_0_1 || 0).toFixed(3)})`,
                  "No barriers reported.",
                )}
              </article>
              <article class="detail-card">
                <h3>Top Coping Strategies</h3>
                ${mkList(
                  selectedCoping,
                  (item) => `${escapeHtml(String(item.coping_name || "strategy"))} (score=${Number(item.score_0_1 || 0).toFixed(3)})`,
                  "No coping strategies reported.",
                )}
              </article>
              <article class="detail-card">
                <h3>HAPA Components</h3>
                ${mkList(
                  hapaPlan,
                  (item) => `<strong>${escapeHtml(String(item.component || "component"))}</strong>: ${escapeHtml(String(item.objective || ""))}`,
                  "No HAPA component plan reported.",
                )}
              </article>
              <article class="detail-card">
                <h3>Phased Delivery</h3>
                ${mkList(
                  phasedPlan,
                  (item) => `<strong>${escapeHtml(String(item.phase || "phase"))}</strong> (${escapeHtml(String(item.time_window || ""))}): ${escapeHtml(String(item.primary_goal || ""))}`,
                  "No phased delivery plan reported.",
                )}
              </article>
              <article class="detail-card">
                <h3>Monitoring and Safety</h3>
                ${mkList(
                  [...monitoring, ...safety],
                  (item) => escapeHtml(String(item || "")),
                  "No monitoring/safety notes reported.",
                )}
              </article>
            </div>
          `;
        }
        interventionPanel.style.display = "block";
      } else {
        if (interventionStructured) interventionStructured.innerHTML = "";
        interventionPanel.style.display = "none";
      }
    }

    /* Static image galleries are intentionally hidden in frontend; dashboard uses computed charts instead. */
    const cycleVisualsPanel = document.getElementById("panel-cycle-visuals");
    if (cycleVisualsPanel) cycleVisualsPanel.style.display = "none";

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
    const listBlock = (title, rows, emptyText) => {
      const values = Array.isArray(rows) ? rows.filter((x) => String(x || "").trim()) : [];
      return `
        <article class="detail-card">
          <h3>${escapeHtml(title)}</h3>
          ${values.length
            ? `<ul class="detail-list">${values.map((item) => `<li>${escapeHtml(String(item))}</li>`).join("")}</ul>`
            : `<p class="muted compact">${escapeHtml(emptyText)}</p>`
          }
        </article>
      `;
    };

    target.innerHTML = `
      <h3>${escapeHtml(summary.headline || "Communication Summary")}</h3>
      <p>${escapeHtml(summary.summary_markdown || "")}</p>
      <div class="meta-grid">
        <div><strong>LLM enabled:</strong> ${escapeHtml(String(payload.llm_enabled))}</div>
        <div><strong>Stage:</strong> ${escapeHtml(payload.stage || "unknown")}</div>
      </div>
      <div class="detail-grid" style="margin-top:10px">
        ${listBlock("Key Points", summary.key_points || [], "No key points reported.")}
        ${listBlock("Risks / Caveats", summary.risks || [], "No specific risks reported.")}
        ${listBlock("Recommended Next Actions", summary.recommended_next_actions || [], "No next actions reported.")}
      </div>
      <details style="margin-top:10px">
        <summary>Raw communication JSON</summary>
        <pre class="json-view">${escapeHtml(JSON.stringify(payload, null, 2))}</pre>
      </details>
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
    /* Always use the 5-phase stepper logic based on pipeline signals */

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
        done: true,  /* Always done — session exists with complaint */
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
    var stepper = document.getElementById("pipeline-progress");
    if (!stepper) return;
    if (!phases.length) return;

    var stepNodes = stepper.querySelectorAll(".step-node");
    var connectors = stepper.querySelectorAll(".step-connector");

    phases.forEach(function (phase, i) {
      var node = stepNodes[i];
      if (!node) return;
      node.classList.remove("done", "running", "error");
      if (phase.status === "done") node.classList.add("done");
      else if (phase.status === "active") node.classList.add("running");
      else if (phase.status === "error") node.classList.add("error");
    });

    for (var i = 0; i < connectors.length; i++) {
      var conn = connectors[i];
      conn.classList.remove("done", "active");
      var left = phases[i];
      var right = phases[i + 1];
      if (left && right) {
        if (left.status === "done" && right.status === "done") conn.classList.add("done");
        else if (left.status === "done" && right.status === "active") conn.classList.add("active");
      }
    }
  }

  /* Per-component step badges: each step independently tracked */
  function updateStepStatusBadges() {
    var componentBadgeMap = [
      { componentId: "step01_operationalization", badgeId: "step01-status", panelId: "panel-step01" },
      { componentId: "step02_initial_model", badgeId: "step02-status", panelId: "panel-step02" },
      { componentId: "pseudodata_collection", badgeId: "step03-acq-status", panelId: "panel-step03" },
      { componentId: "pipeline_cycle_engine", badgeId: "step04-cycle-status", panelId: "panel-step04" },
    ];

    var snapshot = state.snapshot || {};
    /* Determine per-component state considering both live status AND snapshot */
    componentBadgeMap.forEach(function (m) {
      var liveStatus = normalizeStatus(state.componentStatus[m.componentId] || "");
      var label = "PENDING";
      var statusClass = "status-idle";
      var panelState = ""; /* empty | panel-active | panel-complete */

      /* For Step 01/02: if model exists in snapshot, they completed previously */
      if (m.componentId === "step01_operationalization" && snapshot.has_model && !liveStatus) {
        liveStatus = "succeeded";
      }
      if (m.componentId === "step02_initial_model" && snapshot.has_model && !liveStatus) {
        liveStatus = "succeeded";
      }
      if (m.componentId === "pseudodata_collection" && snapshot.has_pseudodata && !liveStatus) {
        liveStatus = "succeeded";
      }
      if (m.componentId === "pipeline_cycle_engine" && snapshot.has_pipeline_summary && !liveStatus) {
        liveStatus = "succeeded";
      }

      if (liveStatus === "succeeded" || liveStatus === "done") {
        label = "DONE"; statusClass = "status-succeeded"; panelState = "panel-complete";
      } else if (liveStatus === "running") {
        label = "RUNNING"; statusClass = "status-running"; panelState = "panel-active";
      } else if (liveStatus === "queued") {
        label = "QUEUED"; statusClass = "status-queued"; panelState = "";
      } else if (liveStatus === "failed" || liveStatus === "error") {
        label = "ERROR"; statusClass = "status-failed"; panelState = "";
      }

      /* Update badge */
      var el = document.getElementById(m.badgeId);
      if (el) {
        el.textContent = label;
        el.className = "panel-step-status status-chip " + statusClass;
      }
      /* Update panel border state */
      var panel = document.getElementById(m.panelId);
      if (panel) {
        panel.classList.remove("panel-active", "panel-complete");
        if (panelState) panel.classList.add(panelState);
      }
    });
  }

  /* Progressive disclosure: lock future steps until prerequisites are met */
  function updateStepVisibility() {
    var snapshot = state.snapshot || {};
    var hasModel = Boolean(snapshot.has_model);
    var hasPseudodata = Boolean(snapshot.has_pseudodata) && !state.awaitingFreshAcquisition;

    /* Also unlock if Step 01/02 are currently running (user should see them) */
    var step01Live = normalizeStatus(state.componentStatus.step01_operationalization || "");
    var step02Live = normalizeStatus(state.componentStatus.step02_initial_model || "");
    var modelInProgress = step01Live === "running" || step01Live === "queued" || step02Live === "running" || step02Live === "queued";

    /* Step 03: unlock when model is complete */
    var panel03 = document.getElementById("panel-step03");
    if (panel03) {
      if (hasModel || modelInProgress) {
        panel03.classList.remove("panel-locked");
      } else {
        panel03.classList.add("panel-locked");
      }
    }

    /* Step 04: unlock when data is ready */
    var panel04 = document.getElementById("panel-step04");
    if (panel04) {
      if (hasPseudodata) {
        panel04.classList.remove("panel-locked");
      } else {
        panel04.classList.add("panel-locked");
      }
    }

    /* Also render Step 01 output if criteria are available */
    renderStep01Output();
  }

  /* Render Step 01 output: prefer operationalization CSV summary, fallback to model schema */
  function renderStep01Output() {
    var outputEl = document.getElementById("step01-output");
    if (!outputEl) return;
    var snapshot = state.snapshot || {};
    var op = snapshot.operationalization_summary || {};
    var opErrors = Array.isArray(op.errors) ? op.errors.filter(function (x) { return String(x || "").trim(); }) : [];
    var source = String(op.source || "").trim();
    var criteria = Array.isArray(op.variables) ? op.variables : [];
    var hasMappedSource = source.indexOf("mapped_csv") === 0;
    if (!criteria.length) {
      if (!hasMappedSource) {
        var schema = snapshot.collection_schema || {};
        var variables = schema.variables || [];
        criteria = variables
          .filter(function (v) { return String(v.role || "").toLowerCase() === "criterion"; })
          .map(function (v) {
            return {
              var_id: String(v.var_id || ""),
              label: String(v.label || v.var_id || ""),
              ontology_path: String(v.ontology_path || ""),
              mapping_status: "MODEL_SCHEMA",
              confidence_0_1: null,
            };
          });
      }
    }

    if (!criteria.length) {
      if (hasMappedSource) {
        var complaintOnly = String(op.complaint_text || snapshot.session?.complaint_text || "").trim();
        if (complaintOnly.length > 220) complaintOnly = complaintOnly.slice(0, 220) + "...";
        var errHtml = '<div class="step-output">';
        errHtml += '<h4>⚠ Operationalization produced no mapped variables</h4>';
        errHtml += '<p class="muted compact">Source: <code>' + escapeHtml(source || "mapped_csv") + '</code></p>';
        if (complaintOnly) {
          errHtml += '<p class="muted compact"><strong>Input complaint used:</strong> ' + escapeHtml(complaintOnly) + '</p>';
        }
        if (opErrors.length) {
          errHtml += '<ul class="detail-list">';
          opErrors.slice(0, 4).forEach(function (item) {
            errHtml += '<li>' + escapeHtml(String(item)) + '</li>';
          });
          errHtml += '</ul>';
        } else {
          errHtml += '<p class="muted compact">No explicit error text was returned. Check Step-01 logs for details.</p>';
        }
        errHtml += '</div>';
        outputEl.innerHTML = errHtml;
        return;
      }
      outputEl.innerHTML = "";
      return;
    }

    var html = '<div class="step-output"><h4>✓ Mapped Criteria (' + criteria.length + ' variables)</h4>';
    var complaintPreview = String(op.complaint_text || snapshot.session?.complaint_text || "").trim();
    var sessionComplaint = String(snapshot.session?.complaint_text || "").trim();
    var mismatchWarning = String(op.mismatch_warning || "").trim();
    var hasMismatch = op.matches_session_complaint === false || Boolean(mismatchWarning);
    var avgConfidence = Number(op.confidence_avg_0_1 || 0);
    var domains = Array.isArray(op.ontology_domains) ? op.ontology_domains : [];
    if (complaintPreview.length > 220) complaintPreview = complaintPreview.slice(0, 220) + "...";
    if (sessionComplaint.length > 220) sessionComplaint = sessionComplaint.slice(0, 220) + "...";
    html += '<div class="meta-grid compact" style="margin:8px 0">';
    html += '<div><strong>Mapped:</strong> ' + criteria.length + '</div>';
    html += '<div><strong>Avg confidence:</strong> ' + avgConfidence.toFixed(2) + '</div>';
    html += '<div><strong>Ontology domains:</strong> ' + escapeHtml(domains.slice(0, 3).join(", ") || "n/a") + '</div>';
    html += '</div>';
    if (source) {
      html += '<p class="muted compact">Source: <code>' + escapeHtml(source) + '</code> · high-level ontology alignment is displayed per criterion.</p>';
    }
    if (complaintPreview) {
      html += '<p class="muted compact"><strong>Input complaint used:</strong> ' + escapeHtml(complaintPreview) + '</p>';
    }
    if (opErrors.length) {
      html += '<p class="alert error compact"><strong>Step-01 warnings:</strong> ' + escapeHtml(opErrors[0]) + '</p>';
    }
    if (hasMismatch) {
      html += '<p class="alert error compact"><strong>Warning:</strong> '
        + escapeHtml(mismatchWarning || "Mapped complaint text does not match session intake complaint.")
        + '</p>';
      if (sessionComplaint) {
        html += '<p class="muted compact"><strong>Current session complaint:</strong> ' + escapeHtml(sessionComplaint) + '</p>';
      }
    }
    html += '<ul class="criteria-list">';
    criteria.forEach(function (c) {
      var confValue = c.confidence_0_1 == null ? null : Number(c.confidence_0_1);
      var conf = confValue == null || Number.isNaN(confValue) ? "" : " · conf=" + confValue.toFixed(2);
      var status = String(c.mapping_status || "").trim();
      var meta = [String(c.ontology_path || "").trim(), status ? ("status=" + status) : "", conf].filter(Boolean).join(" | ");
      var confBar = "";
      if (confValue != null && !Number.isNaN(confValue)) {
        var pct = Math.max(0, Math.min(100, Math.round(confValue * 100)));
        confBar = '<span class="criteria-conf-bar"><span class="criteria-conf-fill" style="width:' + pct + '%"></span></span>';
      }
      html += '<li>'
        + '<span class="criteria-id">' + escapeHtml(String(c.var_id || "")) + '</span>'
        + '<span class="criteria-label">' + escapeHtml(String(c.label || c.var_id || "")) + '</span>'
        + confBar
        + '<span class="criteria-conf">' + escapeHtml(meta) + '</span>'
        + '</li>';
    });
    html += '</ul></div>';
    outputEl.innerHTML = html;
  }

  /* Update analysis sub-stage items in the decomposed Step 04 panel */
  function updateAnalysisSubStages() {
    var container = document.getElementById("analysis-sub-stages");
    if (!container) return;

    var items = container.querySelectorAll(".sub-stage-item");
    items.forEach(function (item) {
      var compId = item.getAttribute("data-component");
      if (!compId) return;
      var liveStatus = normalizeStatus(state.componentStatus[compId] || "");
      var detail = state.componentDetail[compId] || "";

      /* Determine display status */
      var label = "IDLE";
      var statusClass = "status-idle";
      if (liveStatus === "running") { label = "RUNNING"; statusClass = "status-running"; }
      else if (liveStatus === "succeeded" || liveStatus === "done") { label = "DONE"; statusClass = "status-succeeded"; }
      else if (liveStatus === "queued") { label = "QUEUED"; statusClass = "status-queued"; }
      else if (liveStatus === "failed" || liveStatus === "error") { label = "FAILED"; statusClass = "status-failed"; }

      item.setAttribute("data-status", liveStatus || "idle");
      var chip = item.querySelector(".status-chip");
      if (chip) {
        chip.textContent = label;
        chip.className = "status-chip " + statusClass;
      }
      var detailEl = item.querySelector(".sub-stage-detail");
      /* Only overwrite detail if it's meaningful (not a category label) */
      if (detailEl && detail && !detail.startsWith("Category:")) {
        detailEl.textContent = detail;
      }
    });
  }

  function renderPhaseProgress() {
    const decorated = computePhases();
    state.phaseState = decorated;
    renderTopbarProgress(decorated);
    updateStepStatusBadges();
    updateStepVisibility();
    updateAnalysisSubStages();

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
      const note = visuals.length
        ? "Static visual artifact previews are hidden in the frontend. Use the interactive dashboard charts for analysis."
        : "Interactive dashboard charts are used instead of static image previews.";
      visualGrid.innerHTML = `<p class="muted">${escapeHtml(note)}</p>`;
    }

    populateCollectionSummary(collection);
    populateCollectionTable(collection);

    const pseudoNode = document.getElementById("pseudodata-summary");
    if (pseudoNode) {
      if (Object.keys(pseudoSummary).length) {
        var vars = Array.isArray(pseudoSummary.variables) ? pseudoSummary.variables : [];
        pseudoNode.innerHTML = `
          <div class="pseudodata-card">
            <h4>✓ Pseudodata Generated</h4>
            <div class="meta-grid">
              <div><strong>Time points:</strong> ${pseudoSummary.n_points || 0}</div>
              <div><strong>Criteria:</strong> ${pseudoSummary.criteria_count || 0}</div>
              <div><strong>Predictors:</strong> ${pseudoSummary.predictor_count || 0}</div>
              <div><strong>Missing rate:</strong> ${(Number(pseudoSummary.missing_rate_target || 0) * 100).toFixed(0)}%</div>
              <div><strong>Profile:</strong> ${escapeHtml(pseudoSummary.profile_id || "—")}</div>
            </div>
            ${vars.length ? `
              <div class="table-wrap" style="margin-top:8px">
                <table class="data-table">
                  <thead><tr><th>ID</th><th>Role</th><th>Baseline</th><th>Missing %</th><th>Scale</th></tr></thead>
                  <tbody>
                    ${vars.map(v => `
                      <tr>
                        <td><code>${escapeHtml(v.var_id)}</code></td>
                        <td>${escapeHtml(v.role)}</td>
                        <td>${Number(v.baseline_0_1 || 0).toFixed(2)}</td>
                        <td>${(Number(v.missing_rate_empirical || 0) * 100).toFixed(1)}%</td>
                        <td>${v.scale_min}–${v.scale_max}</td>
                      </tr>
                    `).join("")}
                  </tbody>
                </table>
              </div>
            ` : ""}
          </div>
        `;
      } else {
        pseudoNode.innerHTML = "";
      }
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

        /* Filter out skipped stages — they ran during model creation, not the cycle */
        const activeEngine = engineFlow.filter(r => String(r.status || "").toLowerCase() !== "skipped");
        const activeSupport = supportFlow.filter(r => String(r.status || "").toLowerCase() !== "skipped");

        const flowTable = (rows, title) => {
          if (!rows.length) return "";
          return `
            <h4>${escapeHtml(title)}</h4>
            <div class="table-wrap">
              <table class="data-table">
                <thead>
                  <tr><th>Stage</th><th>Status</th><th>Duration (s)</th></tr>
                </thead>
                <tbody>
                  ${rows.map((row) => `
                    <tr>
                      <td>${escapeHtml(String(row.label || row.stage_id || "unknown"))}</td>
                      <td><span class="status-chip ${row.status === "succeeded" ? "status-succeeded" : row.status === "failed" ? "status-failed" : "status-idle"}">${escapeHtml(String(row.status || "unknown"))}</span></td>
                      <td>${escapeHtml(String(Number(row.duration_seconds || 0).toFixed(1)))}</td>
                    </tr>
                  `).join("")}
                </tbody>
              </table>
            </div>
          `;
        };
        const totalDuration = stages.reduce((s, r) => s + Number(r.duration_seconds || 0), 0);
        pipeNode.innerHTML = `
          <div class="step-output">
            <h4>✓ Cycle Complete</h4>
            <div class="meta-grid">
              <div><strong>Run ID:</strong> <code>${escapeHtml(String(pipelineSummary.run_id || "—"))}</code></div>
              <div><strong>Cycle:</strong> ${escapeHtml(String(pipelineSummary.cycle_index || "—"))}</div>
              <div><strong>Status:</strong> ${escapeHtml(String(pipelineSummary.status || "unknown"))}</div>
              <div><strong>Total duration:</strong> ${totalDuration.toFixed(1)}s</div>
            </div>
          </div>
          ${flowTable(activeEngine, "Analysis Engine Stages")}
          ${flowTable(activeSupport, "Support Stages")}
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
    if (low.includes("retrying once with network_jobs=1")) {
      return {
        componentId: "network_analysis",
        status: "running",
        detail: "Parallel network run failed; retrying with single worker",
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
      if (typeof switchTab === 'function') switchTab('logs');
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
    const summarizeLaunchPayload = (jobKind, body) => {
      const p = body || {};
      if (jobKind === "initial_model") {
        return `model=${p.llm_model || "gpt-5-nano"} | workers=${p.max_workers || 12} | disable_llm=${Boolean(p.disable_llm)} | hard_ontology=${Boolean(p.hard_ontology_constraint)}`;
      }
      if (jobKind === "pipeline_cycle") {
        return `model=${p.llm_model || "gpt-5-nano"} | net_jobs=${p.network_jobs || 1} | parallel=${Boolean(p.parallel_branches)} | intervention=${Boolean(p.include_intervention)} | communication=${Boolean(p.run_treatment_communication)} | disable_llm=${Boolean(p.disable_llm)}`;
      }
      if (jobKind === "synthesize_pseudodata") {
        return `points=${p.n_points || 84} | missing_rate=${p.missing_rate ?? 0.1} | seed=${p.seed ?? 42}`;
      }
      if (jobKind === "full_cohort") {
        return `patients=${p.patient_count || 10} | parallel_patients=${p.parallel_patients || 2} | cycles=${p.cycles || 1} | disable_llm=${Boolean(p.disable_llm)}`;
      }
      return "";
    };
    appendLog(`[frontend] Launching job at ${path}`);
    const payloadSummary = summarizeLaunchPayload(kind, payload);
    if (payloadSummary) {
      appendLog(`[frontend] Launch config: ${payloadSummary}`);
    }
    pushRuntimeEvent(`Launching ${kind || "job"}`);
    if (payloadSummary) {
      pushRuntimeEvent(payloadSummary);
    }
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

    /* Drawer button bindings removed — replaced by tab-based layout */
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
