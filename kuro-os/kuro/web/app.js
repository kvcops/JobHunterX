/* ---------------------------------------------------------------------------
   Kuro OS — Frontend Application Logic (app.js)
   Handles WebSockets, HTTP REST endpoints, state sync, telemetry counters,
   and dynamic UI element bindings.

   NOTE: This file is functionally identical to the original, with three
   compatibility fixes for the redesigned markup:
     1. renderJobs() now stamps data-status on each card (the redesign
        renders "clean-job-card" / "clean-status-pill", not the old
        "job-card" / "job-status-indicator" classes filterJobs relied on).
     2. filterJobs() now reads that data-status attribute instead of
        looking for classes that no longer exist, and no longer depends
        on the synthetic window.event (deprecated / unreliable) — it now
        takes the clicked element explicitly.
     3. Sidebar telemetry IDs (stat-discovered/applied) are unique again;
        the ATS tab's own header counts (stat-discovered-bar / stat-applied-bar)
        are updated alongside them so nothing is left stale.
   --------------------------------------------------------------------------- */

// State
let ws = null;
let currentProfile = null;
let jobs = [];
let outreachDrafts = [];
let tokenUsage = {};
let activeOutreachId = null;
let pipelineMode = "automatic";
// Active ATS-queue filter; "matched" is the default high-score view so the
// best jobs surface first. Re-applied after every render (see applyJobFilter).
let activeJobFilter = "matched";

// Match score percentage helper (prevents NA / NaN)
function getMatchScorePercent(job) {
  if (!job) return 0;
  let score = job.match_score;
  if (score === undefined || score === null) {
    if (job.validation && typeof job.validation === "object") {
      score = job.validation.match_score;
    }
  }
  if (typeof score === "string") {
    score = parseFloat(score);
  }
  if (isNaN(score) || score === null || score === undefined) {
    return 0;
  }
  if (score > 1) {
    return Math.min(100, Math.round(score));
  }
  return Math.round(score * 100);
}


// WS Configuration
let wsReconnectDelay = 1000;
const maxWsReconnectDelay = 30000;

// Host details helper
const API_BASE = `${window.location.protocol}//${window.location.host}/api`;
const WS_BASE = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`;

// ---------------------------------------------------------------------------
// Document Ready Init
// ---------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  setupEventListeners();
  connectWebSocket();
  loadInitialData();
});

// ---------------------------------------------------------------------------
// Toast Notifications
// ---------------------------------------------------------------------------
function showToast(message, type = "success") {
  const existing = document.querySelector(".toast-notification");
  if (existing) existing.remove();

  const toast = document.createElement("div");
  toast.className = `toast-notification toast-${type}`;
  toast.innerHTML = `
    <div class="toast-icon">
      ${type === "success"
        ? '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>'
        : '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>'
      }
    </div>
    <span class="toast-message">${message}</span>
  `;
  document.body.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add("toast-show"));
  setTimeout(() => {
    toast.classList.remove("toast-show");
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// ---------------------------------------------------------------------------
// Setup Event Listeners
// ---------------------------------------------------------------------------
function setupEventListeners() {
  // Theme Toggle
  document.getElementById("theme-toggle").addEventListener("click", toggleTheme);

  // Resume Upload Drop Zone
  const dropZone = document.getElementById("drop-zone");
  const fileInput = document.getElementById("resume-input");

  dropZone.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", handleFileSelect);

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("dragover");
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    if (e.dataTransfer.files.length > 0) {
      uploadResume(e.dataTransfer.files[0]);
    }
  });

  // Start Search Button
  const startSearchBtn = document.getElementById("start-search-btn");
  if (startSearchBtn) {
    startSearchBtn.addEventListener("click", startSearch);
  }

  // Global Action Buttons (Reset System & Save Profile)
  const resetBtn = document.getElementById("reset-system-btn");
  if (resetBtn) {
    resetBtn.addEventListener("click", resetSystemAction);
  }

  const headerResetBtn = document.getElementById("header-reset-btn");
  if (headerResetBtn) {
    headerResetBtn.addEventListener("click", resetSystemAction);
  }

  const saveProfBtn = document.getElementById("save-profile-btn");
  if (saveProfBtn) {
    saveProfBtn.addEventListener("click", saveProfileChanges);
  }

  // Keyboard escape handler for modals
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeResetModal();
      if (typeof closeOutreachModal === "function") closeOutreachModal();
      if (typeof closeJobDetailsModal === "function") closeJobDetailsModal();
    }
  });
}


// ---------------------------------------------------------------------------
// Theme Management
// ---------------------------------------------------------------------------
function initTheme() {
  const savedTheme = localStorage.getItem("theme");
  const systemTheme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  const activeTheme = savedTheme || systemTheme;
  document.documentElement.setAttribute("data-theme", activeTheme);
}

function toggleTheme() {
  const currentTheme = document.documentElement.getAttribute("data-theme");
  const newTheme = currentTheme === "dark" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", newTheme);
  localStorage.setItem("theme", newTheme);
}

// ---------------------------------------------------------------------------
// Tab Navigation
// ---------------------------------------------------------------------------
function switchTab(tabName) {
  // Update nav buttons in top bar
  document.querySelectorAll(".dock-tab-btn, .tab-btn").forEach(btn => btn.classList.remove("active"));
  const topTabBtn = document.getElementById(`tab-${tabName}`);
  if (topTabBtn) {
    topTabBtn.classList.add("active");
    topTabBtn.classList.remove("pulse-highlight");
  }

  // Update views
  document.querySelectorAll(".tab-view").forEach(view => view.classList.remove("active"));
  const activeView = document.getElementById(`view-${tabName}`);
  if (activeView) activeView.classList.add("active");

  // Render intervention cards when switching to intervention tab
  if (tabName === "intervention") {
    renderInterventionCards();
  }
}

// ---------------------------------------------------------------------------
// Load Initial Data & Locations
// ---------------------------------------------------------------------------
let allLocations = [];

async function loadLocations() {
  try {
    const res = await fetch(`${API_BASE}/locations`);
    if (!res.ok) return;
    const data = await res.json();
    const locs = data.locations || [];
    allLocations = locs;

    setupCustomLocationDropdown(locs);
  } catch (err) {
    console.error("Failed to load locations", err);
  }
}

function setupCustomLocationDropdown(locs) {
  const hiddenInput = document.getElementById("target-location");
  const triggerText = document.getElementById("custom-location-selected-text");
  const popover = document.getElementById("custom-location-popover");
  const trigger = document.getElementById("custom-location-trigger");
  const searchInput = document.getElementById("custom-location-search-input");

  if (!trigger || !popover) return;

  const currentVal = hiddenInput ? hiddenInput.value : "hyderabad";

  // Toggle popover on trigger click
  trigger.onclick = (e) => {
    e.stopPropagation();
    const isHidden = popover.classList.contains("hidden");
    if (isHidden) {
      popover.classList.remove("hidden");
      trigger.classList.add("open");
      if (searchInput) {
        searchInput.value = "";
        renderCustomLocationOptions(allLocations, hiddenInput ? hiddenInput.value : "hyderabad");
        searchInput.focus();
      }
    } else {
      popover.classList.add("hidden");
      trigger.classList.remove("open");
    }
  };

  // Close popover when clicking outside
  document.addEventListener("click", (e) => {
    if (popover && !popover.contains(e.target) && trigger && !trigger.contains(e.target)) {
      popover.classList.add("hidden");
      trigger.classList.remove("open");
    }
  });

  // Search filter handler
  if (searchInput) {
    searchInput.oninput = () => {
      const q = searchInput.value.toLowerCase().trim();
      const filtered = allLocations.filter(loc =>
        loc.label.toLowerCase().includes(q) || loc.key.toLowerCase().includes(q)
      );
      renderCustomLocationOptions(filtered, hiddenInput ? hiddenInput.value : "hyderabad");
    };
  }

  // Initial options render
  renderCustomLocationOptions(allLocations, currentVal);
}

function renderCustomLocationOptions(locs, activeKey) {
  const optionsList = document.getElementById("custom-location-options-list");
  const hiddenInput = document.getElementById("target-location");
  const triggerText = document.getElementById("custom-location-selected-text");
  const popover = document.getElementById("custom-location-popover");
  const trigger = document.getElementById("custom-location-trigger");

  if (!optionsList) return;
  optionsList.innerHTML = "";

  if (!locs || locs.length === 0) {
    optionsList.innerHTML = `<div class="custom-select-no-results">No tech hubs found</div>`;
    return;
  }

  locs.forEach(loc => {
    const item = document.createElement("div");
    const isActive = loc.key.toLowerCase() === activeKey.toLowerCase();
    item.className = `custom-select-option ${isActive ? 'active' : ''}`;
    item.innerHTML = `
      <span class="option-label">${escapeHtml(loc.label)}</span>
      <span class="option-badge">${loc.company_count} Companies</span>
    `;
    item.onclick = (e) => {
      e.stopPropagation();
      if (hiddenInput) hiddenInput.value = loc.key;
      if (triggerText) triggerText.innerText = `${loc.label} (${loc.company_count} Companies)`;
      if (popover) popover.classList.add("hidden");
      if (trigger) trigger.classList.remove("open");
      renderCustomLocationOptions(allLocations, loc.key);
    };
    optionsList.appendChild(item);

    if (isActive && triggerText) {
      triggerText.innerText = `${loc.label} (${loc.company_count} Companies)`;
    }
  });
}

async function loadInitialData() {
  try {
    // Load Locations Dropdown
    await loadLocations();

    // Load Status & Token Telemetry
    const statusRes = await fetch(`${API_BASE}/status`);
    const statusData = await statusRes.json();
    updateStatusIndicator(statusData.status);
    updateTokenTelemetry(statusData.token_usage);
    if (statusData.pipeline_mode) {
      pipelineMode = statusData.pipeline_mode;
      updatePipelineModeUI(pipelineMode);
    }

    // Load existing jobs
    const jobsRes = await fetch(`${API_BASE}/jobs`);
    const jobsData = await jobsRes.json();
    jobs = jobsData.jobs || [];
    renderJobs();
    renderResumes();

    // Load existing outreach
    const outreachRes = await fetch(`${API_BASE}/outreach`);
    const outreachData = await outreachRes.json();
    outreachDrafts = outreachData.drafts || [];
    renderOutreach();

    // Load latest profile
    const profileRes = await fetch(`${API_BASE}/profile`);
    if (profileRes.ok) {
      const profileData = await profileRes.json();
      if (profileData.profile) {
        currentProfile = profileData.profile;
        renderProfileCard();
        renderProfileEditor();
        if (currentProfile.suggested_role) {
          const roleInput = document.getElementById("target-role");
          if (roleInput) roleInput.value = currentProfile.suggested_role;
        }
        document.getElementById("start-search-btn").removeAttribute("disabled");
      }
    }

    // Load pending intervention sessions
    try {
      const intvRes = await fetch(`${API_BASE}/interventions`);
      if (intvRes.ok) {
        const intvData = await intvRes.json();
        const sessions = intvData.interventions || [];
        interventionSessions.length = 0;
        sessions.forEach(s => {
          interventionSessions.push({
            job_id: s.job_id,
            type: s.hitl_type,
            url: s.url,
            company: s.company || "",
            role: s.role || "",
            timestamp: s.created_at,
            db_id: s.id,
          });
        });
        renderInterventionCards();
      }
    } catch (intvErr) {
      // Silently fail — intervention tab works via WebSocket events
    }

  } catch (err) {
    console.error("Error loading initial dashboard data", err);
    logEvent("system", "Failed to contact local API server.");
  }
}

// ---------------------------------------------------------------------------
// Resume Upload Handler
// ---------------------------------------------------------------------------
function handleFileSelect(e) {
  if (e.target.files.length > 0) {
    uploadResume(e.target.files[0]);
  }
}

async function uploadResume(file) {
  const dropZone = document.getElementById("drop-zone");
  dropZone.querySelector("p").innerText = "Extracting profile...";
  dropZone.querySelector("span").innerText = "Running Gemma 4 parsing model";

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch(`${API_BASE}/upload-resume`, {
      method: "POST",
      body: formData
    });

    if (!res.ok) throw new Error("Upload failed");

    const data = await res.json();
    currentProfile = data.profile;

    // Render profile card
    renderProfileCard();

    dropZone.querySelector("p").innerText = "Resume Uploaded";
    dropZone.querySelector("span").innerText = file.name;
    document.getElementById("start-search-btn").removeAttribute("disabled");

    logEvent("system", `Profile successfully parsed: ${currentProfile.name}`);
  } catch (err) {
    console.error("Resume parsing error", err);
    dropZone.querySelector("p").innerText = "Failed to parse PDF";
    dropZone.querySelector("span").innerText = "Please try again";
    logEvent("error", "Failed to extract candidate resume details.");
  }
}

function renderProfileCard() {
  if (!currentProfile) return;
  const card = document.getElementById("profile-card");
  if (card) card.classList.remove("hidden");

  const nameEl = document.getElementById("profile-name");
  if (nameEl) nameEl.innerText = currentProfile.name || "Candidate Name";

  const emailEl = document.getElementById("profile-email");
  if (emailEl) emailEl.innerText = currentProfile.email || "N/A";

  const phoneEl = document.getElementById("profile-phone");
  if (phoneEl) phoneEl.innerText = currentProfile.phone || "N/A";

  const locEl = document.getElementById("profile-location");
  if (locEl) locEl.innerText = currentProfile.location || "";

  const expTag = document.getElementById("profile-relevant-exp");
  if (expTag) {
    expTag.innerText = currentProfile.relevant_experience ? `Exp: ${currentProfile.relevant_experience}` : "Exp: N/A";
  }

  const langTag = document.getElementById("profile-languages-badge");
  if (langTag) {
    const langs = Array.isArray(currentProfile.languages) ? currentProfile.languages.join(", ") : (currentProfile.languages || "");
    langTag.innerText = langs ? `Languages: ${langs}` : "Languages: N/A";
  }

  const container = document.getElementById("profile-skills");
  if (container) {
    container.innerHTML = "";
  }
}

// ---------------------------------------------------------------------------
// Search Controls
// ---------------------------------------------------------------------------
async function startSearch() {
  const location = document.getElementById("target-location").value.trim();
  const role = document.getElementById("target-role").value.trim();
  const limitInput = document.getElementById("target-analysis-limit");
  const limit = limitInput ? parseInt(limitInput.value, 10) || 25 : 25;

  if (!location) return;

  logEvent("system", `Starting job search for "${role || 'Software Engineer'}" in "${location}" (Max ${limit} Companies)`);
  document.getElementById("start-search-btn").setAttribute("disabled", "true");

  // Reset progress bar
  const bar = document.getElementById("sidebar-progress-bar");
  if (bar) bar.style.width = "0%";
  const progressStatus = document.getElementById("sidebar-progress-status");
  if (progressStatus) progressStatus.innerText = "Initializing search node...";

  // Show halt button
  const haltBtn = document.getElementById("halt-browser-btn");
  if (haltBtn) haltBtn.classList.remove("hidden");

  try {
    const res = await fetch(`${API_BASE}/start-search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ location, role, limit })
    });
    const data = await res.json();
    updateStatusIndicator("running");
  } catch (err) {
    console.error("Search start error", err);
    logEvent("error", "Failed to start active pipeline.");
    document.getElementById("start-search-btn").removeAttribute("disabled");
    if (haltBtn) haltBtn.classList.add("hidden");
  }
}

// ---------------------------------------------------------------------------
// WebSocket Manager
// ---------------------------------------------------------------------------
function connectWebSocket() {
  ws = new WebSocket(WS_BASE);

  ws.onopen = () => {
    console.log("WebSocket connected");
    wsReconnectDelay = 1000; // Reset backoff
    logEvent("system", "Connected to agent telemetry stream.");
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleSocketMessage(data);
  };

  ws.onclose = () => {
    console.warn("WebSocket disconnected, reconnecting...");
    setTimeout(connectWebSocket, wsReconnectDelay);
    wsReconnectDelay = Math.min(wsReconnectDelay * 2, maxWsReconnectDelay);
  };

  ws.onerror = (err) => {
    console.error("WebSocket error", err);
  };
}

function handleSocketMessage(msg) {
  // Handle search progress events
  if (msg.event_type === "search_progress" || msg.event_type === "validation_progress") {
    const pct = msg.data ? msg.data.percentage : 0;
    const bar = document.getElementById("sidebar-progress-bar");
    if (bar) bar.style.width = `${pct}%`;
    const progressStatus = document.getElementById("sidebar-progress-status");
    if (progressStatus) progressStatus.innerText = msg.message;
    logEvent(msg.agent || "system", msg.message, false);
  }

  // If it's standard logging event
  if (msg.event_type === "progress" || msg.event_type === "discovery" || msg.event_type === "error" || msg.event_type === "complete") {
    logEvent(msg.agent || "system", msg.message, msg.event_type === "error");
  }

  if (msg.event_type === "complete") {
    const bar = document.getElementById("sidebar-progress-bar");
    if (bar) bar.style.width = "100%";
    const progressStatus = document.getElementById("sidebar-progress-status");
    if (progressStatus) progressStatus.innerText = "Search Complete!";

    // Hide halt button
    const haltBtn = document.getElementById("halt-browser-btn");
    if (haltBtn) haltBtn.classList.add("hidden");

    // Re-enable start search
    const startSearchBtn = document.getElementById("start-search-btn");
    if (startSearchBtn) startSearchBtn.removeAttribute("disabled");
  }

  if (msg.event_type === "error") {
    // Re-enable start search on error
    const startSearchBtn = document.getElementById("start-search-btn");
    if (startSearchBtn) startSearchBtn.removeAttribute("disabled");
    const haltBtn = document.getElementById("halt-browser-btn");
    if (haltBtn) haltBtn.classList.add("hidden");
  }

  // Reload telemetry usage if tokens updated
  if (msg.data && (msg.data.tokens_in || msg.data.tokens_out)) {
    loadInitialData(); // Lazy refresh
  }

  // Handle explicit profile loads or updates
  if (msg.event_type === "profile_loaded" || msg.event_type === "profile_updated") {
    loadInitialData();
  }

  // Handle system reset
  if (msg.event_type === "reset") {
    handleSystemReset();
  }

  // Handle pipeline mode changes
  if (msg.event_type === "pipeline_mode_changed" && msg.data && msg.data.mode) {
    pipelineMode = msg.data.mode;
    updatePipelineModeUI(pipelineMode);
  }

  // Handle browser agent automation steps
  if (msg.event_type === "browser_step") {
    handleBrowserStep(msg.data);
  }

  // Handle live browser real-time frame streaming
  if (msg.event_type === "browser_stream_frame") {
    handleBrowserStreamFrame(msg.data);
  }

  // Handle HITL Request Event (redirect to intervention tab)
  if (msg.event_type === "hitl_request") {
    // Already handled by intervention_needed event
  }

  // Handle Intervention Needed Event (non-blocking HITL)
  if (msg.event_type === "intervention_needed") {
    addInterventionCard(msg.data);
  }

  // Handle streaming real-time job discovery & scoring events
  if (msg.event_type === "job_found" && msg.data && msg.data.job) {
    const existing = jobs.find(j => j.id === msg.data.job.id);
    if (!existing) {
      jobs.push(msg.data.job);
      renderJobs();
    }
  }

  if (msg.event_type === "job_scored" && msg.data) {
    const job = jobs.find(j => j.id === msg.data.job_id);
    if (job) {
      job.match_score = msg.data.match_score;
      if (msg.data.reason) {
        job.validation_json = JSON.stringify({ score_reason: msg.data.reason, match_score: msg.data.match_score });
      }
      renderJobs();
    }
  }

  // Reload data for job/outreach updates
  if (msg.event_type === "discovery" || msg.event_type === "complete" || msg.event_type === "job_deleted" || msg.event_type === "jobs_cleared") {
    loadInitialData();
  }

  // Live status transitions (validating → matched/applying → applied/...):
  // patch the in-memory job list so pills, counters, and the active filter
  // update instantly without a full reload.
  if (msg.event_type === "job_status_changed" && msg.data && msg.data.job_id && msg.data.status) {
    const job = jobs.find(j => j.id === msg.data.job_id);
    if (job) {
      job.status = msg.data.status;
      renderJobs();
    } else {
      loadInitialData();
    }
  }
}

// ---------------------------------------------------------------------------
// Intervention Tab
// ---------------------------------------------------------------------------
const interventionSessions = [];

function addInterventionCard(data) {
  interventionSessions.push({
    job_id: data.job_id,
    type: data.type,
    url: data.url,
    company: data.company || "",
    role: data.role || "",
    timestamp: new Date().toISOString(),
    screenshot: data.screenshot || null,
    db_id: data.db_id,
  });
  renderInterventionCards();
  // Auto-switch to intervention tab
  switchTab("intervention");
}

function renderInterventionCards() {
  const intvBadge = document.getElementById("tab-count-intervention");
  if (intvBadge) {
    intvBadge.innerText = interventionSessions.length;
    if (interventionSessions.length > 0) intvBadge.classList.add("warning");
    else intvBadge.classList.remove("warning");
  }

  const container = document.getElementById("intervention-cards-container");
  if (!container) return;

  if (interventionSessions.length === 0) {
    container.innerHTML = `
      <div class="empty-state-view">
        <div class="empty-state-icon">
          <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
        </div>
        <h3>No pending interventions</h3>
        <p>When the browser agent encounters a login, CAPTCHA, or OTP it can't solve, the session will appear here for you to continue manually.</p>
      </div>`;
    return;
  }

  container.innerHTML = interventionSessions.map((s, idx) => {
    const time = new Date(s.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const typeLabel = {
      login: "Login Required",
      captcha: "CAPTCHA",
      mfa: "MFA / OTP",
      manual_form: "Complex Form",
      too_complex: "Too Complex",
    }[s.type] || s.type;

    const screenshotHtml = s.screenshot
      ? `<div class="intervention-card-screenshot"><img src="${API_BASE}/screenshots/${s.job_id}?t=${Date.now()}" alt="Browser state" onerror="this.parentElement.style.display='none'"></div>`
      : '';

    return `
      <div class="intervention-card" data-job-id="${s.job_id}">
        <div class="intervention-card-header">
          <div class="intervention-card-type">
            <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            ${typeLabel}
          </div>
          <span class="intervention-card-timestamp">${time}</span>
        </div>
        <div class="intervention-card-title">${s.role || "Application"}</div>
        <div class="intervention-card-company">${s.company}</div>
        ${screenshotHtml}
        <div class="intervention-card-url">${s.url || ""}</div>
        <div class="intervention-card-actions">
          <button class="intervention-card-btn continue-btn" onclick="continueIntervention(${idx})">
            <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
            Open Browser
          </button>
          <button class="intervention-card-btn resolve-btn" onclick="resolveIntervention(${idx})">
            <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
            Resolve
          </button>
          <button class="intervention-card-btn skip-btn" onclick="skipIntervention(${idx})">
            Skip
          </button>
        </div>
      </div>`;
  }).join("");
}

function continueIntervention(idx) {
  const session = interventionSessions[idx];
  if (!session) return;
  // Open a new window to the browser URL using the persistent profile
  window.open(session.url, "_blank");
}

async function resolveIntervention(idx) {
  const session = interventionSessions[idx];
  if (!session) return;
  if (session.db_id) {
    try {
      await fetch(`${API_BASE}/interventions/${session.db_id}/resolve?status=resolved`, {
        method: "POST",
      });
    } catch (e) {
      console.error("Failed to resolve intervention:", e);
    }
  }
  interventionSessions.splice(idx, 1);
  renderInterventionCards();
}

async function skipIntervention(idx) {
  const session = interventionSessions[idx];
  if (!session) return;
  if (session.db_id) {
    try {
      await fetch(`${API_BASE}/interventions/${session.db_id}/resolve?status=skipped`, {
        method: "POST",
      });
    } catch (e) {
      console.error("Failed to skip intervention:", e);
    }
  }
  interventionSessions.splice(idx, 1);
  renderInterventionCards();
}

// ---------------------------------------------------------------------------
// UI Renders & Formatting
// ---------------------------------------------------------------------------
function renderJobs() {
  const container = document.getElementById("jobs-container");
  if (jobs.length === 0) {
    container.innerHTML = `
      <div class="empty-state-view">
        <div class="empty-state-icon">📁</div>
        <h3>No job listings in queue</h3>
        <p>Upload your resume PDF and click "Start Job Discovery" to surface opportunities.</p>
      </div>`;
    updateJobsStatCounters(0, 0, 0, 0, 0);
    return;
  }

  let appliedCount = 0;
  let matchedCount = 0;
  let applyingCount = 0;
  let needsAttentionCount = 0;
  let lowScoreCount = 0;
  container.innerHTML = "";

  // High-score first: jobs with a validated match score sort above
  // unvalidated/discovered ones, so the best matches lead the queue.
  const sortedJobs = [...jobs].sort((a, b) => {
    const scoreDiff = getMatchScorePercent(b) - getMatchScorePercent(a);
    if (scoreDiff !== 0) return scoreDiff;
    return (a.company || "").localeCompare(b.company || "");
  });

  sortedJobs.forEach(job => {
    const card = document.createElement("div");
    const matchPercent = getMatchScorePercent(job);
    const applyUrl = job.apply_url || job.career_page_url || "#";

    // Determine effective status based on score threshold (60%) for discovered jobs
    const st = job.status || "discovered";
    let effectiveStatus = st;
    if (st === "discovered") {
      if (matchPercent >= 60) {
        effectiveStatus = "matched";
      } else {
        effectiveStatus = "low_score";
      }
    } else if (st === "skipped" || st === "failed") {
      effectiveStatus = "low_score";
    }

    if (effectiveStatus === "matched" || effectiveStatus === "validating" || effectiveStatus === "applying") matchedCount++;
    if (st === "applying" || st === "validating") applyingCount++;
    if (effectiveStatus === "applied" || effectiveStatus === "applied_manual" || effectiveStatus === "force_applied") appliedCount++;
    if (effectiveStatus === "needs_attention") needsAttentionCount++;
    if (effectiveStatus === "low_score") lowScoreCount++;

    // Use LLM-generated summary if available, fallback to raw JD snippet
    const snippetText = job.one_line_summary
      || (job.jd_text ? stripHtml(job.jd_text).slice(0, 130).trim() + "..." : "");

    // Use LLM-validated skills if available, fallback to naive substring match
    let matchingSkills = [];
    let missingSkills = [];
    if (job.skills_matched && job.skills_matched.length > 0) {
      matchingSkills = job.skills_matched.slice(0, 4);
      missingSkills = (job.skills_missing || []).slice(0, 2);
    } else {
      const userSkills = (currentProfile && currentProfile.skills) ? currentProfile.skills : [];
      if (job.jd_text && userSkills.length > 0) {
        const jdLower = job.jd_text.toLowerCase();
        matchingSkills = userSkills.filter(skill => jdLower.includes(skill.toLowerCase())).slice(0, 4);
      }
    }
    const matchingSkillsHtml = matchingSkills.map(skill =>
      `<span class="premium-tech-tag"><span class="tag-dot"></span>${escapeHtml(skill)}</span>`
    ).join("");
    const missingSkillsHtml = missingSkills.map(skill =>
      `<span class="premium-tech-tag" style="opacity:0.5;"><span class="tag-dot" style="background:#f87171;"></span>${escapeHtml(skill)}</span>`
    ).join("");

    // Clean up source label so it never overflows
    let rawSource = job.source || 'ATS';
    let sourceLabel = rawSource.replace(/_/g, ' ');
    if (sourceLabel.toUpperCase().includes('INDEXED')) sourceLabel = 'Indexed';
    else if (sourceLabel.toUpperCase().includes('DIRECT ATS')) sourceLabel = 'Direct ATS';
    else if (sourceLabel.length > 14) sourceLabel = sourceLabel.slice(0, 12) + '..';

    // Status Pill text and class
    const statusText = {
      matched: "Matched",
      validating: "Validating",
      applying: "Applying",
      applied: "Applied",
      applied_manual: "Applied",
      force_applied: "Applied",
      needs_attention: "Attention",
      failed: "Failed",
      skipped: "Skipped",
      low_score: "Low Score"
    }[effectiveStatus] || "Discovered";

    const statusPillClass = {
      matched: "pill-matched",
      validating: "pill-applying",
      applying: "pill-applying",
      applied: "pill-applied",
      applied_manual: "pill-applied",
      force_applied: "pill-applied",
      needs_attention: "pill-attention",
      failed: "pill-failed",
      low_score: "pill-discovered"
    }[effectiveStatus] || "pill-discovered";

    // data-status drives filterJobs() below — the redesigned card markup
    // ("clean-job-card" / "clean-status-pill") no longer carries the old
    // "job-status-indicator <status>" class the original filter relied on.
    card.className = "clean-job-card clickable-card";
    card.dataset.status = effectiveStatus;
    card.innerHTML = `
      <div class="clean-card-header">
        <div class="clean-header-titles" onclick="openJobDetailsModal('${job.id}')" style="cursor: pointer;">
          <div class="clean-company">${escapeHtml(job.company)}</div>
          <div class="clean-role">${escapeHtml(job.role || "Software Engineering Role")}</div>
          ${job.location ? `<div class="clean-location">📍 ${escapeHtml(job.location)}</div>` : ''}
        </div>
        <div class="clean-header-pills">
          <span class="clean-match-pill">${matchPercent}% Match</span>
          <span class="clean-status-pill ${statusPillClass}">${statusText}</span>
        </div>
      </div>

      ${snippetText ? `
      <div class="clean-snippet" onclick="openJobDetailsModal('${job.id}')" style="cursor: pointer;">
        ${escapeHtml(snippetText)}
      </div>` : ''}

      ${matchingSkillsHtml ? `
      <div class="clean-skills-row">
        ${matchingSkillsHtml}${missingSkillsHtml}
      </div>` : ''}

      <div class="clean-card-footer">
        <span class="clean-source-tag">${escapeHtml(sourceLabel)}</span>
        <div class="clean-footer-actions">
          <button class="clean-btn sec" onclick="openJobDetailsModal('${job.id}')">Details</button>
          <a href="${escapeHtml(applyUrl)}" target="_blank" rel="noopener noreferrer" class="clean-btn icon-link" title="Open Application Link">↗</a>
          ${effectiveStatus === 'matched' || effectiveStatus === 'applied' || job.tailored_pdf ? `<button class="clean-btn sec" onclick="downloadResume('${job.id}')">CV</button>` : ''}
          ${effectiveStatus === 'applying' || effectiveStatus === 'validating' ? `<span class="clean-btn applying">Applying...</span>` : ''}
          ${effectiveStatus === 'applied' || effectiveStatus === 'force_applied' ? `<span class="clean-btn applied" style="background: rgba(34,197,94,0.15); color: #4ade80; border: 1px solid rgba(34,197,94,0.3); font-size: 0.78rem; padding: 3px 8px; border-radius: 4px;">Applied ✓</span>` : ''}
          ${effectiveStatus === 'needs_attention' ? `<button class="clean-btn warn" onclick="triggerHitlResume('${job.id}')">Solve Block</button><button class="clean-btn prim" onclick="applyToJob(event, '${job.id}')">Retry Apply</button>` : ''}
          ${effectiveStatus === 'failed' || effectiveStatus === 'skipped' ? `<button class="clean-btn prim" onclick="applyToJob(event, '${job.id}')">Retry Apply</button>` : ''}
          ${effectiveStatus === 'discovered' || effectiveStatus === 'matched' ? `<button class="clean-btn prim" onclick="applyToJob(event, '${job.id}')">Apply</button>` : ''}
          <button class="clean-btn del-btn" onclick="deleteSingleJob(event, '${job.id}')" title="Delete job posting" style="color: #f87171; background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.2); font-size: 0.78rem; padding: 3px 8px; cursor: pointer;">🗑️</button>
        </div>
      </div>
    `;
    container.appendChild(card);
  });

  updateJobsStatCounters(jobs.length, appliedCount, matchedCount, applyingCount, needsAttentionCount, lowScoreCount);

  // Re-apply the user's active filter so newly rendered/streamed cards
  // respect it (e.g. filter stuck on "Matched" while discovery streams in).
  applyJobFilter();
}

// Updates both the sidebar telemetry counters and the ATS tab's own header
// bar (which has separate IDs to avoid duplicate-ID collisions).
function updateJobsStatCounters(discovered, applied, matched, applying, needsAttention, lowScore) {
  const setText = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.innerText = val;
  };
  setText("stat-discovered", discovered);
  setText("stat-applied", applied);
  setText("stat-discovered-bar", discovered);
  setText("stat-applied-bar", applied);
  setText("stat-matched", matched);
  setText("stat-needs-attention", needsAttention);
  setText("stat-low-score", lowScore || 0);

  // Update filter pill counts dynamically
  const updatePill = (id, baseText, count) => {
    const el = document.getElementById(id);
    if (el) el.innerText = `${baseText} (${count})`;
  };
  updatePill("btn-filter-all", "All Jobs", discovered);
  updatePill("btn-filter-matched", "Matched", matched);
  updatePill("btn-filter-applying", "Applying", applying);
  updatePill("btn-filter-applied", "Applied", applied);
  updatePill("btn-filter-needs_attention", "Attention", needsAttention);
  updatePill("btn-filter-low_score", "Low Score", lowScore);

  const atsBadge = document.getElementById("tab-count-ats");
  if (atsBadge) {
    atsBadge.innerText = discovered;
    if (discovered > 0) atsBadge.classList.add("has-items");
    else atsBadge.classList.remove("has-items");
  }
}

function renderResumes() {
  const container = document.getElementById("resumes-container");
  if (!container) return;

  const matchedJobs = jobs.filter(j => {
    const st = j.status || 'discovered';
    const score = getMatchScorePercent(j);
    return st === 'matched' || st === 'applied' || st === 'applying' || st === 'needs_attention' || (st === 'discovered' && score >= 60);
  });

  const cvBadge = document.getElementById("tab-count-resumes");
  if (cvBadge) {
    cvBadge.innerText = matchedJobs.length;
    if (matchedJobs.length > 0) cvBadge.classList.add("has-items");
    else cvBadge.classList.remove("has-items");
  }

  if (matchedJobs.length === 0) {
    container.innerHTML = `
      <div class="empty-state-view">
        <div class="empty-state-icon">📄</div>
        <h3>No tailored resumes generated yet</h3>
        <p>Tailored resumes and CVs created for matched job postings will appear here automatically.</p>
      </div>`;
    return;
  }

  container.innerHTML = "";
  matchedJobs.forEach(job => {
    const card = document.createElement("div");
    card.className = "clean-job-card clickable-card";
    card.dataset.status = job.status || "discovered";

    const matchPercent = getMatchScorePercent(job);

    card.innerHTML = `
      <div class="clean-card-header" onclick="openJobDetailsModal('${job.id}')" style="cursor: pointer;">
        <div class="clean-header-titles">
          <div class="clean-company">${escapeHtml(job.company)}</div>
          <div class="clean-role">${escapeHtml(job.role || "Software Role")}</div>
        </div>
        <div class="clean-header-pills">
          <span class="clean-match-pill">${matchPercent}% Match</span>
          <span class="clean-status-pill pill-applied">ATS Tailored</span>
        </div>
      </div>
      <div class="clean-card-footer">
        <span class="clean-source-tag">${(job.status || "discovered").replace('_', ' ')}</span>
        <div class="clean-footer-actions">
          <button class="clean-btn sec" onclick="openJobDetailsModal('${job.id}')">View JD</button>
          <button class="clean-btn prim" onclick="downloadResume('${job.id}')">Download CV</button>
        </div>
      </div>
    `;
    container.appendChild(card);
  });
}

// ---------------------------------------------------------------------------
function formatSourceText(src) {
  if (!src) return "Indexed Web";
  const s = src.toLowerCase();
  if (s.includes("instahyre")) return "Instahyre";
  if (s.includes("linkedin")) return "LinkedIn";
  if (s.includes("naukri")) return "Naukri";
  if (s.includes("indeed")) return "Indeed";
  if (s.includes("wellfound") || s.includes("angel")) return "Wellfound";
  if (s.includes("greenhouse")) return "Greenhouse";
  if (s.includes("lever")) return "Lever";
  let cleaned = src.replace(/^search_indexed_/, "").replace(/^portal_/, "").replace(/_/g, " ").trim();
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}

function openJobDetailsModal(jobId) {
  const job = jobs.find(j => j.id === jobId);
  if (!job) return;

  document.getElementById("jd-modal-company").innerText = job.company || "Company Name";
  document.getElementById("jd-modal-role-pill").innerText = job.role || "Software Engineering Role";
  document.getElementById("jd-modal-location").innerText = job.location || "India / Remote";
  document.getElementById("jd-modal-source").innerText = formatSourceText(job.source);

  const matchPercent = getMatchScorePercent(job);
  const matchClass = matchPercent >= 70 ? "conf-high" : matchPercent >= 40 ? "conf-med" : "conf-low";
  const matchBadge = document.getElementById("jd-modal-match-score");
  if (matchBadge) {
    matchBadge.className = `jd-meta-val conf-badge ${matchClass}`;
    matchBadge.innerText = `${matchPercent}% Match`;
  }

  const statusBadge = document.getElementById("jd-modal-status");
  if (statusBadge) {
    statusBadge.className = `jd-meta-val job-status-indicator ${job.status}`;
    statusBadge.innerText = (job.status || "discovered").replace('_', ' ');
  }

  // Render Candidate vs Job Alignment Summary
  const v = job.validation || {};
  const expEl = document.getElementById("jd-modal-exp-comparison");
  const skillsEl = document.getElementById("jd-modal-skills-comparison");
  const reasoningEl = document.getElementById("jd-modal-reasoning");

  if (expEl) {
    // Use LLM experience verdict if available, fallback to old format
    const expVerdict = job.experience_verdict || v.experience_verdict;
    if (expVerdict) {
      expEl.innerHTML = `<strong>Experience:</strong> ${escapeHtml(expVerdict)}`;
    } else {
      const candidateExp = currentProfile ? (currentProfile.relevant_experience || "N/A") : "N/A";
      const reqExp = v.required_experience || "Extracted from JD";
      expEl.innerHTML = `<strong>Experience:</strong> Candidate: ${escapeHtml(candidateExp)} vs Required: ${escapeHtml(reqExp)}`;
    }
  }

  if (skillsEl) {
    // Use LLM skills if available, fallback to old format
    const matched = (job.skills_matched || v.matching_skills || []).join(", ") || "None specified";
    const missing = (job.skills_missing || v.missing_skills || []).join(", ") || "None missing";
    const needed = (job.skills_needed || []).join(", ");
    let html = `<strong>Matched:</strong> <span style="color:#4ade80;">${escapeHtml(matched)}</span>`;
    html += ` | <strong>Missing:</strong> <span style="color:#f87171;">${escapeHtml(missing)}</span>`;
    if (needed) {
      html += `<br><strong>Skills Required:</strong> ${escapeHtml(needed)}`;
    }
    skillsEl.innerHTML = html;
  }

  if (reasoningEl) {
    const summary = job.one_line_summary || v.reasoning || "";
    reasoningEl.innerText = summary ? `"${summary}"` : "Evaluation completed.";
  }

  const applyUrl = job.apply_url || job.career_page_url || "#";
  const applyBtn = document.getElementById("jd-modal-apply-link");
  if (applyBtn) applyBtn.href = applyUrl;

  const downloadBtn = document.getElementById("jd-modal-download-cv-btn");
  if (downloadBtn) {
    downloadBtn.onclick = () => downloadResume(job.id);
  }

  const jdContainer = document.getElementById("jd-modal-body");
  if (jdContainer) {
    jdContainer.innerHTML = formatJdText(job.jd_text);
  }

  const modal = document.getElementById("job-details-modal");
  if (modal) modal.classList.remove("hidden");
}

function closeJobDetailsModal() {
  const modal = document.getElementById("job-details-modal");
  if (modal) modal.classList.add("hidden");
}

function formatJdText(rawText) {
  if (!rawText || !rawText.trim()) {
    return `<p class="jd-placeholder-text">No detailed job description text recorded for this posting.</p>`;
  }

  // Strip any raw HTML tags/entities that leaked through, producing clean text.
  let text = rawText;
  if (/<\/?(p|div|span|h\d|ul|ol|li|br|strong|em|a|b|i)\b/i.test(text)) {
    const tmp = document.createElement("div");
    tmp.innerHTML = text;
    // Convert <li> to bullet lines and <br>/<p> to newlines first
    tmp.querySelectorAll("li").forEach(li => li.insertAdjacentText("afterbegin", "\n• "));
    tmp.querySelectorAll("br, p, div, h1, h2, h3, h4, h5, h6").forEach(el => el.insertAdjacentText("afterend", "\n"));
    text = tmp.textContent || "";
  }
  // Decode leftover entities (&nbsp; &amp; etc.) and tidy whitespace
  text = text.replace(/&nbsp;/g, " ").replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&#39;/g, "'");
  text = text.replace(/\r\n/g, "\n").replace(/[ \t]+\n/g, "\n").replace(/\n{3,}/g, "\n\n").trim();

  const lines = text.split('\n');
  let formattedHtml = '';
  let inList = false;

  lines.forEach(line => {
    const trimmed = line.trim();
    if (!trimmed) {
      if (inList) {
        formattedHtml += '</ul>';
        inList = false;
      }
      return;
    }

    if (trimmed.startsWith('•') || trimmed.startsWith('-') || trimmed.startsWith('*') || /^\d+\.\s/.test(trimmed)) {
      if (!inList) {
        formattedHtml += '<ul class="jd-bullet-list">';
        inList = true;
      }
      const itemContent = escapeHtml(trimmed.replace(/^([•\-\*]|\d+\.)\s*/, ''));
      formattedHtml += `<li>${itemContent}</li>`;
    } else if (trimmed.endsWith(':') || (trimmed.length < 60 && (trimmed.toLowerCase().includes('requirement') || trimmed.toLowerCase().includes('responsibil') || trimmed.toLowerCase().includes('about') || trimmed.toLowerCase().includes('skill') || trimmed.toLowerCase().includes('qualificat')))) {
      if (inList) {
        formattedHtml += '</ul>';
        inList = false;
      }
      formattedHtml += `<h5 class="jd-subheading">${escapeHtml(trimmed)}</h5>`;
    } else {
      if (inList) {
        formattedHtml += '</ul>';
        inList = false;
      }
      formattedHtml += `<p class="jd-paragraph">${escapeHtml(trimmed)}</p>`;
    }
  });

  if (inList) {
    formattedHtml += '</ul>';
  }

  return formattedHtml;
}


function renderOutreach() {
  const container = document.getElementById("outreach-container");
  if (outreachDrafts.length === 0) {
    container.innerHTML = `
      <div class="empty-state-view">
        <div class="empty-state-icon">✉️</div>
        <h3>No outreach drafts found</h3>
        <p>Personalized outreach email templates will display here once matches are processed.</p>
      </div>`;
    const outreachStat = document.getElementById("stat-outreach");
    if (outreachStat) outreachStat.innerText = "0";
    return;
  }

  container.innerHTML = "";
  outreachDrafts.forEach(draft => {
    const card = document.createElement("div");

    const score = draft.confidence || 0;
    const confClass = score > 0.7 ? "conf-high" : score > 0.4 ? "conf-med" : "conf-low";

    const initial = draft.company ? draft.company.trim().charAt(0).toUpperCase() : '?';
    const bestEmail = draft.email_guesses && draft.email_guesses.length > 0 ? draft.email_guesses[0].address : "No email guessed";
    const emailStatusLabel = draft.email_guesses && draft.email_guesses.length > 0 && draft.email_guesses[0].mx_valid ? "MX Verified" : "MX Checked";
    const emailStatusClass = draft.email_guesses && draft.email_guesses.length > 0 && draft.email_guesses[0].mx_valid ? "email-verified" : "email-unverified";

    card.className = "outreach-card-premium";
    card.innerHTML = `
      <div class="outreach-premium-header">
        <div class="outreach-avatar">${initial}</div>
        <div class="outreach-info">
          <div class="outreach-company">${escapeHtml(draft.company)}</div>
          <div class="outreach-contact-row">
            <span class="outreach-contact-name">${escapeHtml(draft.contact_name)}</span>
            <span class="outreach-role-tag">${escapeHtml(draft.contact_role)}</span>
          </div>
        </div>
      </div>

      <div class="outreach-email-bar">
        <div class="email-icon">
          <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
        </div>
        <div class="email-value-text ${emailStatusClass}">${escapeHtml(bestEmail)}</div>
        <span class="mx-pill ${emailStatusClass}">${emailStatusLabel}</span>
      </div>

      <!-- Mini email mockup card -->
      <div class="outreach-email-preview">
        <div class="preview-subject"><strong>Subj:</strong> ${escapeHtml(draft.subject || 'Pitching Candidate Fit')}</div>
        <div class="preview-body">${escapeHtml(draft.body ? draft.body.slice(0, 110) + "..." : "Generating pitch details...")}</div>
      </div>

      <div class="outreach-card-footer">
        <div class="footer-left" style="display:flex; align-items:center; gap:6px;">
          <span class="conf-badge ${confClass}">Fit confidence: ${(score * 100).toFixed(0)}%</span>
          <span class="outreach-status-pill ${draft.status}">${escapeHtml(draft.status)}</span>
        </div>
        <button class="outreach-send-btn-premium" onclick="openOutreachComposer('${draft.id}')">
          <span>Review Pitch</span>
          <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
        </button>
      </div>
    `;
    container.appendChild(card);
  });

  const outreachStat = document.getElementById("stat-outreach");
  if (outreachStat) outreachStat.innerText = outreachDrafts.length;

  const outreachBadge = document.getElementById("tab-count-outreach");
  if (outreachBadge) {
    outreachBadge.innerText = outreachDrafts.length;
    if (outreachDrafts.length > 0) outreachBadge.classList.add("has-items");
    else outreachBadge.classList.remove("has-items");
  }
}

// ---------------------------------------------------------------------------
// Telemetry Indicators
// ---------------------------------------------------------------------------
function updateStatusIndicator(status) {
  const badge = document.getElementById("status-badge");
  badge.className = `status-badge ${status}`;
  const textEl = badge.querySelector(".status-text");
  if (textEl) {
    textEl.innerText = status;
  } else {
    badge.innerText = status;
  }

  if (status === "idle" || status === "complete") {
    document.getElementById("start-search-btn").removeAttribute("disabled");
  }
}

function updateTokenTelemetry(tokenMap) {
  let total = 0;
  if (tokenMap) {
    Object.values(tokenMap).forEach(usage => {
      total += (usage.tokens_in || 0) + (usage.tokens_out || 0);
    });
  }
  document.getElementById("stat-tokens").innerText = total.toLocaleString();
}

function togglePipelineMode() {
  const nextMode = (pipelineMode === "automatic") ? "manual" : "automatic";
  setPipelineMode(nextMode);
}

async function setPipelineMode(mode) {
  try {
    const res = await fetch(`${API_BASE}/pipeline-mode?mode=${encodeURIComponent(mode)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: mode })
    });
    if (res.ok) {
      const data = await res.json();
      pipelineMode = data.mode;
      updatePipelineModeUI(pipelineMode);
      showToast(`Pipeline mode set to: ${pipelineMode.toUpperCase()}`, "success");
    }
  } catch (err) {
    console.error("Failed to set pipeline mode", err);
  }
}

function updatePipelineModeUI(mode) {
  const autoBtn = document.getElementById("mode-btn-automatic");
  const manualBtn = document.getElementById("mode-btn-manual");
  if (autoBtn && manualBtn) {
    if (mode === "manual") {
      autoBtn.classList.remove("active");
      manualBtn.classList.add("active");
    } else {
      manualBtn.classList.remove("active");
      autoBtn.classList.add("active");
    }
  }

  const toggleBtn = document.getElementById("header-mode-toggle-btn");
  const modeText = document.getElementById("header-mode-text");
  const pulseDot = document.getElementById("mode-pulse-dot");

  if (toggleBtn && modeText && pulseDot) {
    if (mode === "manual") {
      toggleBtn.className = "compact-mode-pill manual";
      toggleBtn.title = "Execution Mode: Manual (triggers apply per job). Click to switch to Automatic.";
      modeText.innerText = "Manual Mode";
      pulseDot.className = "mode-pulse-dot manual";
    } else {
      toggleBtn.className = "compact-mode-pill auto";
      toggleBtn.title = "Execution Mode: Automatic (runs end-to-end). Click to switch to Manual.";
      modeText.innerText = "Auto Mode";
      pulseDot.className = "mode-pulse-dot automatic";
    }
  }
}




function updatePipelinePhase(agent, msgLower) {
  const phasePill = document.getElementById("terminal-phase-pill");
  const stepDiscovery = document.getElementById("step-node-discovery");
  const stepEval = document.getElementById("step-node-eval");
  const stepTailor = document.getElementById("step-node-tailor");
  const stepApply = document.getElementById("step-node-apply");

  if (!phasePill) return;

  if (msgLower.includes("discovery") || msgLower.includes("searching") || msgLower.includes("channel") || agent === "geo_search") {
    phasePill.innerText = "Phase 1/4";
    if (stepDiscovery) { stepDiscovery.className = "stepper-node active"; }
  } else if (msgLower.includes("evaluat") || msgLower.includes("fit") || agent === "job_evaluator") {
    phasePill.innerText = "Phase 2/4";
    if (stepDiscovery) stepDiscovery.className = "stepper-node completed";
    if (stepEval) stepEval.className = "stepper-node active";
  } else if (msgLower.includes("tailor") || msgLower.includes("pdf") || agent === "validator_tailor") {
    phasePill.innerText = "Phase 3/4";
    if (stepDiscovery) stepDiscovery.className = "stepper-node completed";
    if (stepEval) stepEval.className = "stepper-node completed";
    if (stepTailor) stepTailor.className = "stepper-node active";
  } else if (msgLower.includes("apply") || msgLower.includes("browser") || agent === "browser_agent") {
    phasePill.innerText = "Phase 4/4";
    if (stepDiscovery) stepDiscovery.className = "stepper-node completed";
    if (stepEval) stepEval.className = "stepper-node completed";
    if (stepTailor) stepTailor.className = "stepper-node completed";
    if (stepApply) stepApply.className = "stepper-node active";
  } else if (msgLower.includes("complete")) {
    phasePill.innerText = "Complete";
    [stepDiscovery, stepEval, stepTailor, stepApply].forEach(n => { if (n) n.className = "stepper-node completed"; });
  }
}

function logEvent(agent, message, isError = false) {
  const statusTextEl = document.getElementById("sidebar-progress-status");
  const dotEl = document.getElementById("sidebar-progress-dot");
  const miniLogsEl = document.getElementById("progress-mini-logs");

  const msgLower = message.toLowerCase();
  updatePipelinePhase(agent, msgLower);

  if (statusTextEl && dotEl && miniLogsEl) {
    let statusLabel = "System Active";
    let isIdle = false;

    if (msgLower.includes("idle") || msgLower.includes("system initialized")) {
      statusLabel = "System Idle";
      isIdle = true;
    } else if (msgLower.includes("discovery") || msgLower.includes("searching") || msgLower.includes("scraped")) {
      statusLabel = "Searching Roles";
    } else if (msgLower.includes("validat") || msgLower.includes("score") || msgLower.includes("evaluat")) {
      statusLabel = "Evaluating Candidate Fit";
    } else if (msgLower.includes("apply") || msgLower.includes("filling") || msgLower.includes("automation")) {
      statusLabel = "Auto-Applying via Chromium";
    } else if (msgLower.includes("submitted") || msgLower.includes("completed")) {
      statusLabel = "Job Applied!";
    } else if (agent === "deep_research") {
      statusLabel = "Researching Decision Makers";
    }

    statusTextEl.innerText = statusLabel;

    dotEl.className = "status-pulse-dot";
    if (isError) {
      dotEl.classList.add("error");
    } else if (!isIdle) {
      dotEl.classList.add("running");
    }

    const now = new Date();
    const timeStr = now.toTimeString().split(" ")[0];

    const entry = document.createElement("div");
    entry.className = `mini-log-item ${isError ? 'error' : ''}`;

    const agentKey = agent || "system";
    entry.innerHTML = `<span class="log-time">${timeStr}</span> <span class="log-agent-tag ${escapeHtml(agentKey)}">${escapeHtml(agentKey)}</span> ${escapeHtml(message)}`;

    if (miniLogsEl.children.length === 1 && miniLogsEl.children[0].innerText.includes("Ready")) {
      miniLogsEl.innerHTML = "";
    }

    miniLogsEl.appendChild(entry);

    while (miniLogsEl.children.length > 25) {
      miniLogsEl.removeChild(miniLogsEl.firstChild);
    }

    miniLogsEl.scrollTop = miniLogsEl.scrollHeight;
  }
}

function clearLogs() {
  const miniLogsEl = document.getElementById("progress-mini-logs");
  if (miniLogsEl) {
    miniLogsEl.innerHTML = `<div class="mini-log-item"><span class="log-time">00:00:00</span> <span class="log-agent-tag system">system</span> Ready.</div>`;
  }
}

// ---------------------------------------------------------------------------
// HITL Intervention - now handled via intervention tab cards
// ---------------------------------------------------------------------------
function triggerHitlResume(jobId) {
  const job = jobs.find(j => j.id === jobId);
  if (job) {
    const url = job.apply_url || job.career_page_url;
    if (url) window.open(url, "_blank");
  }
}

// ---------------------------------------------------------------------------
// Outreach Composer Modal
// ---------------------------------------------------------------------------
function openOutreachComposer(draftId) {
  activeOutreachId = draftId;
  const draft = outreachDrafts.find(d => d.id === draftId);
  if (!draft) return;

  document.getElementById("modal-contact-details").innerText = `${draft.contact_name} (${draft.contact_role})`;
  document.getElementById("composer-subject").value = draft.subject;
  document.getElementById("composer-body").value = draft.body;

  const toInput = document.getElementById("composer-to");
  const bestEmail = draft.email_guesses && draft.email_guesses.length > 0 ? draft.email_guesses[0].address : "";
  if (toInput) {
    toInput.value = bestEmail;
  }

  const guessesList = document.getElementById("modal-email-guesses");
  guessesList.innerHTML = "";

  (draft.email_guesses || []).forEach((guess, idx) => {
    const item = document.createElement("div");
    item.className = "email-guess-item clickable-guess" + (guess.address === bestEmail ? " active-guess" : "");

    const label = guess.mx_valid === false ? " (MX Failed)" : " (MX Verified)";
    const style = guess.mx_valid === false ? "color: var(--danger)" : "color: var(--success)";

    item.innerHTML = `
      <div class="guess-address-line">
        <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 4px; vertical-align: middle;"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/></svg>
        <span>${escapeHtml(guess.address)}</span>
      </div>
      <div class="guess-meta">
        <span class="conf-badge conf-med" style="${style}">${guess.pattern}${label}</span>
      </div>
    `;

    item.onclick = () => {
      if (toInput) {
        toInput.value = guess.address;
      }
      document.querySelectorAll(".email-guess-item").forEach(el => el.classList.remove("active-guess"));
      item.classList.add("active-guess");
    };

    guessesList.appendChild(item);
  });

  document.getElementById("outreach-modal").classList.remove("hidden");
}

function closeOutreachModal() {
  document.getElementById("outreach-modal").classList.add("hidden");
  activeOutreachId = null;
}

async function discardOutreachDraft() {
  if (!activeOutreachId) return;
  try {
    await fetch(`${API_BASE}/outreach/${activeOutreachId}/discard`, {
      method: "POST"
    });
    closeOutreachModal();
    loadInitialData();
  } catch (err) {
    console.error("Failed to discard draft", err);
  }
}

async function saveOutreachDraft() {
  if (!activeOutreachId) return;
  const to = document.getElementById("composer-to")?.value || "";
  const subject = document.getElementById("composer-subject")?.value || "";
  const body = document.getElementById("composer-body")?.value || "";

  try {
    const res = await fetch(`${API_BASE}/outreach/${activeOutreachId}/save`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ to_addr: to, subject: subject, body: body })
    });
    if (res.ok) {
      logEvent("system", "Outreach draft changes saved successfully.");
      // Update local cache
      const draft = outreachDrafts.find(d => d.id === activeOutreachId);
      if (draft) {
        draft.subject = subject;
        draft.body = body;
        if (draft.email_guesses && draft.email_guesses.length > 0) {
          if (draft.email_guesses[0].address !== to) {
            draft.email_guesses = [{address: to, pattern: "user_edit", mx_valid: null}].concat(draft.email_guesses);
          }
        } else {
          draft.email_guesses = [{address: to, pattern: "user_edit", mx_valid: null}];
        }
      }
      renderOutreach();
    }
  } catch (err) {
    console.error("Failed to save draft", err);
  }
}

async function triggerMailtoHandoff() {
  if (!activeOutreachId) return;

  const to = document.getElementById("composer-to")?.value || "";
  const subject = document.getElementById("composer-subject")?.value || "";
  const body = document.getElementById("composer-body")?.value || "";

  // Save edits first, then open mail client
  await saveOutreachDraft();

  const mailtoUri = `mailto:${encodeURIComponent(to)}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  window.location.href = mailtoUri;
  closeOutreachModal();
  logEvent("system", "Handoff to default system mail client completed.");
}

async function triggerGmailWebHandoff() {
  if (!activeOutreachId) return;

  const to = document.getElementById("composer-to")?.value || "";
  const subject = document.getElementById("composer-subject")?.value || "";
  const body = document.getElementById("composer-body")?.value || "";

  // Save edits first, then open Gmail
  await saveOutreachDraft();

  const gmailUrl = `https://mail.google.com/mail/?view=cm&fs=1&to=${encodeURIComponent(to)}&su=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  window.open(gmailUrl, "_blank");
  closeOutreachModal();
  logEvent("outreach", "Opened draft in Gmail Web (New Tab).");
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function downloadResume(jobId) {
  window.open(`${API_BASE}/jobs/${jobId}/resume-pdf`, "_blank");
}

function formatJobStatus(status) {
  const labels = {
    discovered: "Discovered",
    matched: "Matched",
    applying: "Applying",
    applied: "Applied",
    applied_manual: "Applied (Manual)",
    needs_attention: "Needs Attention",
    failed: "Failed",
    skipped: "Skipped",
  };
  return labels[status] || status.replace(/_/g, " ");
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

function stripHtml(html) {
  if (!html) return "";
  const tmp = document.createElement("div");
  tmp.innerHTML = html;
  return tmp.textContent || tmp.innerText || "";
}

function filterJobs(status, triggerEl) {
  activeJobFilter = status || "all";
  document.querySelectorAll(".filter-pill").forEach(btn => btn.classList.remove("active"));
  if (triggerEl) {
    triggerEl.classList.add("active");
  }
  applyJobFilter();
}

const JOB_STATUS_BUCKETS = {
  matched: new Set(["matched", "validating", "applying"]),
  applying: new Set(["applying", "validating"]),
  applied: new Set(["applied", "applied_manual", "force_applied"]),
  needs_attention: new Set(["needs_attention"]),
  low_score: new Set(["low_score", "discovered", "skipped", "failed"])
};

function jobStatusInFilter(status, filter) {
  if (!filter || filter === "all") return true;
  const bucket = JOB_STATUS_BUCKETS[filter];
  return bucket ? bucket.has(status || "discovered") : false;
}

function applyJobFilter() {
  const cards = document.querySelectorAll("#jobs-container .clean-job-card");
  let visibleCount = 0;

  cards.forEach(card => {
    const cardStatus = card.dataset.status || "discovered";
    const show = jobStatusInFilter(cardStatus, activeJobFilter);
    card.style.display = show ? "flex" : "none";
    if (show) visibleCount++;
  });
  return visibleCount;
}
// Candidate Profile & Reset Features
// ---------------------------------------------------------------------------
let editedSkills = [];
let editedExperience = [];
let editedEducation = [];
let editedProjects = [];

function updateLanguageChips() {
  const input = document.getElementById("prof-languages");
  const preview = document.getElementById("languages-chips-preview");
  if (!input || !preview) return;
  const langs = input.value.split(",").map(l => l.trim()).filter(l => l.length > 0);
  preview.innerHTML = "";
  langs.forEach(lang => {
    const chip = document.createElement("span");
    chip.className = "lang-preview-chip";
    chip.innerText = lang;
    preview.appendChild(chip);
  });
}

function renderProfileEditor() {
  if (!currentProfile) return;

  // Set personal details
  document.getElementById("prof-name").value = currentProfile.name || "";
  document.getElementById("prof-email").value = currentProfile.email || "";
  document.getElementById("prof-phone").value = currentProfile.phone || "";
  document.getElementById("prof-linkedin").value = currentProfile.linkedin || "";
  if (document.getElementById("prof-github")) document.getElementById("prof-github").value = currentProfile.github || "";
  if (document.getElementById("prof-portfolio")) document.getElementById("prof-portfolio").value = currentProfile.portfolio || "";
  document.getElementById("prof-location").value = currentProfile.location || "";
  if (document.getElementById("prof-present-address")) document.getElementById("prof-present-address").value = currentProfile.present_address || "";
  if (document.getElementById("prof-suggested-role")) document.getElementById("prof-suggested-role").value = currentProfile.suggested_role || "";
  const targetRoleInput = document.getElementById("target-role");
  if (targetRoleInput && currentProfile.suggested_role) {
    targetRoleInput.value = currentProfile.suggested_role;
  }
  if (document.getElementById("prof-relevant-experience")) document.getElementById("prof-relevant-experience").value = currentProfile.relevant_experience || "";
  if (document.getElementById("prof-languages")) {
    const langs = Array.isArray(currentProfile.languages) ? currentProfile.languages.join(", ") : (currentProfile.languages || "");
    document.getElementById("prof-languages").value = langs;
  }
  document.getElementById("prof-summary").value = currentProfile.summary || "";

  // Populate Q&A Memory fields
  const qa = currentProfile.qa_memory || {};
  if (document.getElementById("qa-salary")) document.getElementById("qa-salary").value = qa.expected_salary || "";
  if (document.getElementById("qa-current-ctc")) document.getElementById("qa-current-ctc").value = qa.current_ctc || "";
  if (document.getElementById("qa-expected-ctc")) document.getElementById("qa-expected-ctc").value = qa.expected_ctc || "";
  if (document.getElementById("qa-notice")) document.getElementById("qa-notice").value = qa.notice_period || "";
  if (document.getElementById("qa-work-auth")) document.getElementById("qa-work-auth").value = qa.work_authorization || "";
  if (document.getElementById("qa-sponsorship")) document.getElementById("qa-sponsorship").value = qa.requires_sponsorship || "";
  if (document.getElementById("qa-work-mode")) document.getElementById("qa-work-mode").value = qa.preferred_work_mode || "";
  if (document.getElementById("qa-relocate")) document.getElementById("qa-relocate").value = qa.willing_to_relocate || "";


  // Initialize scoped lists
  if (editedSkills.length === 0 && currentProfile.skills) {
    editedSkills = [...currentProfile.skills];
  }
  if (editedExperience.length === 0 && currentProfile.experience) {
    editedExperience = JSON.parse(JSON.stringify(currentProfile.experience));
  }
  if (editedEducation.length === 0 && currentProfile.education) {
    editedEducation = JSON.parse(JSON.stringify(currentProfile.education));
  }
  if (editedProjects.length === 0 && currentProfile.projects) {
    editedProjects = JSON.parse(JSON.stringify(currentProfile.projects));
  }

  updateLanguageChips();
  renderSkillsEditor();
  renderExperienceEditor();
  renderEducationEditor();
  renderProjectsEditor();
  setupEditorListeners();
}

function renderSkillsEditor() {
  const container = document.getElementById("editor-skills-list");
  container.innerHTML = "";
  editedSkills.forEach(skill => {
    const chip = document.createElement("span");
    chip.className = "editor-skill-chip";
    chip.innerHTML = `${escapeHtml(skill)} <button type="button" class="del-skill-btn">&times;</button>`;
    chip.querySelector(".del-skill-btn").addEventListener("click", () => {
      editedSkills = editedSkills.filter(s => s !== skill);
      renderSkillsEditor();
    });
    container.appendChild(chip);
  });
}

function renderExperienceEditor() {
  const container = document.getElementById("editor-experience-list");
  container.innerHTML = "";

  editedExperience.forEach((exp, index) => {
    const block = document.createElement("div");
    block.className = "experience-block-card";
    block.innerHTML = `
      <div class="exp-block-header">
        <h4>Experience Entry ${index + 1}</h4>
        <button type="button" class="btn-delete-item">Remove</button>
      </div>
      <div class="form-grid">
        <div class="form-group">
          <label>Company</label>
          <input type="text" class="exp-company" value="${escapeHtml(exp.company || '')}">
        </div>
        <div class="form-group">
          <label>Role</label>
          <input type="text" class="exp-role" value="${escapeHtml(exp.role || '')}">
        </div>
        <div class="form-group">
          <label>Start Date</label>
          <input type="text" class="exp-start" value="${escapeHtml(exp.start || '')}">
        </div>
        <div class="form-group">
          <label>End Date</label>
          <input type="text" class="exp-end" value="${escapeHtml(exp.end || '')}">
        </div>
        <div class="form-group full-width">
          <label>Bullets (one per line)</label>
          <textarea class="exp-bullets" rows="3">${(exp.bullets || []).map(b => escapeHtml(b)).join('\n')}</textarea>
        </div>
      </div>
    `;

    block.querySelector(".btn-delete-item").addEventListener("click", () => {
      syncCurrentEditorArrays();
      editedExperience.splice(index, 1);
      renderExperienceEditor();
    });

    container.appendChild(block);
  });
}

function renderEducationEditor() {
  const container = document.getElementById("editor-education-list");
  if (!container) return;
  container.innerHTML = "";

  editedEducation.forEach((edu, index) => {
    const block = document.createElement("div");
    block.className = "education-block-card";
    block.innerHTML = `
      <div class="edu-block-header">
        <h4>Education Entry ${index + 1}</h4>
        <button type="button" class="btn-delete-item">Remove</button>
      </div>
      <div class="form-grid">
        <div class="form-group">
          <label>Institution / University / School</label>
          <input type="text" class="edu-institution" value="${escapeHtml(edu.institution || '')}">
        </div>
        <div class="form-group">
          <label>Degree / Qualification</label>
          <input type="text" class="edu-degree" value="${escapeHtml(edu.degree || '')}">
        </div>
        <div class="form-group">
          <label>Start Date / Year</label>
          <input type="text" class="edu-start" value="${escapeHtml(edu.start || '')}">
        </div>
        <div class="form-group">
          <label>End Date / Year</label>
          <input type="text" class="edu-end" value="${escapeHtml(edu.end || '')}">
        </div>
        <div class="form-group">
          <label>Grade / CGPA / Percentage</label>
          <input type="text" class="edu-grade" placeholder="e.g. 8.9 CGPA or 92%" value="${escapeHtml(edu.grade || '')}">
        </div>
        <div class="form-group full-width">
          <label>Specialization / Coursework / Honors</label>
          <input type="text" class="edu-details" placeholder="e.g. Computer Science, Algorithms, Honors" value="${escapeHtml(edu.details || '')}">
        </div>
      </div>
    `;

    block.querySelector(".btn-delete-item").addEventListener("click", () => {
      syncCurrentEditorArrays();
      editedEducation.splice(index, 1);
      renderEducationEditor();
    });

    container.appendChild(block);
  });
}

function renderProjectsEditor() {
  const container = document.getElementById("editor-projects-list");
  if (!container) return;
  container.innerHTML = "";

  editedProjects.forEach((proj, index) => {
    const block = document.createElement("div");
    block.className = "project-block-card";
    block.innerHTML = `
      <div class="proj-block-header">
        <h4>Project Entry ${index + 1}</h4>
        <button type="button" class="btn-delete-item">Remove</button>
      </div>
      <div class="form-grid">
        <div class="form-group">
          <label>Project Title / Name</label>
          <input type="text" class="proj-title" value="${escapeHtml(proj.title || '')}">
        </div>
        <div class="form-group">
          <label>Project Link / URL</label>
          <input type="text" class="proj-url" value="${escapeHtml(proj.url || '')}">
        </div>
        <div class="form-group full-width">
          <label>Technologies Used (comma-separated)</label>
          <input type="text" class="proj-tech" value="${escapeHtml(Array.isArray(proj.technologies) ? proj.technologies.join(', ') : (proj.technologies || ''))}">
        </div>
        <div class="form-group full-width">
          <label>Project Description / Key Details</label>
          <textarea class="proj-desc" rows="3">${escapeHtml(proj.description || '')}</textarea>
        </div>
      </div>
    `;

    block.querySelector(".btn-delete-item").addEventListener("click", () => {
      syncCurrentEditorArrays();
      editedProjects.splice(index, 1);
      renderProjectsEditor();
    });

    container.appendChild(block);
  });
}

function syncCurrentEditorArrays() {
  const expCards = document.querySelectorAll(".experience-block-card");
  editedExperience = Array.from(expCards).map(card => {
    const bulletsText = card.querySelector(".exp-bullets").value;
    const bullets = bulletsText.split('\n').map(b => b.trim()).filter(b => b.length > 0);
    return {
      company: card.querySelector(".exp-company").value.trim(),
      role: card.querySelector(".exp-role").value.trim(),
      start: card.querySelector(".exp-start").value.trim(),
      end: card.querySelector(".exp-end").value.trim(),
      bullets: bullets
    };
  });

  const eduCards = document.querySelectorAll(".education-block-card");
  editedEducation = Array.from(eduCards).map(card => {
    const gradeInput = card.querySelector(".edu-grade");
    const detailsInput = card.querySelector(".edu-details");
    return {
      institution: card.querySelector(".edu-institution").value.trim(),
      degree: card.querySelector(".edu-degree").value.trim(),
      start: card.querySelector(".edu-start").value.trim(),
      end: card.querySelector(".edu-end").value.trim(),
      grade: gradeInput ? gradeInput.value.trim() : "",
      details: detailsInput ? detailsInput.value.trim() : ""
    };
  });

  const projCards = document.querySelectorAll(".project-block-card");
  editedProjects = Array.from(projCards).map(card => {
    const techText = card.querySelector(".proj-tech").value;
    const technologies = techText.split(',').map(t => t.trim()).filter(t => t.length > 0);
    return {
      title: card.querySelector(".proj-title").value.trim(),
      url: card.querySelector(".proj-url").value.trim(),
      description: card.querySelector(".proj-desc").value.trim(),
      technologies: technologies
    };
  });
}

let editorListenersInitialized = false;

function setupEditorListeners() {
  if (editorListenersInitialized) return;

  // Add Skill button
  document.getElementById("add-skill-btn").addEventListener("click", addSkillFromInput);
  document.getElementById("new-skill-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addSkillFromInput();
    }
  });

  // Add Experience
  document.getElementById("add-exp-btn").addEventListener("click", () => {
    syncCurrentEditorArrays();
    editedExperience.push({ company: "", role: "", start: "", end: "", bullets: [] });
    renderExperienceEditor();
  });

  // Add Education
  document.getElementById("add-edu-btn").addEventListener("click", () => {
    syncCurrentEditorArrays();
    editedEducation.push({ institution: "", degree: "", start: "", end: "" });
    renderEducationEditor();
  });

  // Add Project
  document.getElementById("add-proj-btn").addEventListener("click", () => {
    syncCurrentEditorArrays();
    editedProjects.push({ title: "", description: "", url: "", technologies: [] });
    renderProjectsEditor();
  });

  const langInput = document.getElementById("prof-languages");
  if (langInput) {
    langInput.addEventListener("input", updateLanguageChips);
  }

  // Save Profile Changes
  document.getElementById("save-profile-btn").addEventListener("click", saveProfileChanges);

  // Reset Database & Stop Agent
  document.getElementById("reset-system-btn").addEventListener("click", resetSystemAction);

  editorListenersInitialized = true;
}

function addSkillFromInput() {
  const input = document.getElementById("new-skill-input");
  const value = input.value.trim();
  if (value && !editedSkills.includes(value)) {
    editedSkills.push(value);
    input.value = "";
    renderSkillsEditor();
  }
}

async function saveProfileChanges() {
  syncCurrentEditorArrays();

  const updatedProfile = {
    name: document.getElementById("prof-name").value.trim(),
    email: document.getElementById("prof-email").value.trim(),
    phone: document.getElementById("prof-phone").value.trim(),
    linkedin: document.getElementById("prof-linkedin").value.trim(),
    github: document.getElementById("prof-github") ? document.getElementById("prof-github").value.trim() : (currentProfile.github || ""),
    portfolio: document.getElementById("prof-portfolio") ? document.getElementById("prof-portfolio").value.trim() : (currentProfile.portfolio || ""),
    location: document.getElementById("prof-location").value.trim(),
    present_address: document.getElementById("prof-present-address") ? document.getElementById("prof-present-address").value.trim() : (currentProfile.present_address || ""),
    permanent_address: document.getElementById("prof-permanent-address") ? document.getElementById("prof-permanent-address").value.trim() : (currentProfile.permanent_address || ""),
    suggested_role: document.getElementById("target-role") ? document.getElementById("target-role").value.trim() : (currentProfile.suggested_role || ""),
    relevant_experience: document.getElementById("prof-relevant-experience") ? document.getElementById("prof-relevant-experience").value.trim() : (currentProfile.relevant_experience || ""),
    languages: document.getElementById("prof-languages") ? document.getElementById("prof-languages").value.split(",").map(l => l.trim()).filter(l => l) : (currentProfile.languages || []),
    summary: document.getElementById("prof-summary").value.trim(),
    skills: editedSkills,
    experience: editedExperience,
    education: editedEducation,
    projects: editedProjects,
    competitions: currentProfile.competitions || [],
    achievements: currentProfile.achievements || [],
    qa_memory: {
      expected_salary: document.getElementById("qa-salary") ? document.getElementById("qa-salary").value.trim() : ((currentProfile.qa_memory || {}).expected_salary || ""),
      current_ctc: document.getElementById("qa-current-ctc") ? document.getElementById("qa-current-ctc").value.trim() : ((currentProfile.qa_memory || {}).current_ctc || ""),
      expected_ctc: document.getElementById("qa-expected-ctc") ? document.getElementById("qa-expected-ctc").value.trim() : ((currentProfile.qa_memory || {}).expected_ctc || ""),
      notice_period: document.getElementById("qa-notice") ? document.getElementById("qa-notice").value.trim() : ((currentProfile.qa_memory || {}).notice_period || ""),
      work_authorization: document.getElementById("qa-work-auth") ? document.getElementById("qa-work-auth").value.trim() : ((currentProfile.qa_memory || {}).work_authorization || ""),
      requires_sponsorship: document.getElementById("qa-sponsorship") ? document.getElementById("qa-sponsorship").value.trim() : ((currentProfile.qa_memory || {}).requires_sponsorship || ""),
      preferred_work_mode: document.getElementById("qa-work-mode") ? document.getElementById("qa-work-mode").value.trim() : ((currentProfile.qa_memory || {}).preferred_work_mode || ""),
      willing_to_relocate: document.getElementById("qa-relocate") ? document.getElementById("qa-relocate").value.trim() : ((currentProfile.qa_memory || {}).willing_to_relocate || ""),
      custom_answers: (currentProfile.qa_memory || {}).custom_answers || {}
    }
  };


  try {
    const res = await fetch(`${API_BASE}/profile`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(updatedProfile)
    });

    if (res.ok) {
      logEvent("system", "Candidate profile details saved successfully.");
      currentProfile = updatedProfile;
      renderProfileCard();
      showToast("Profile saved successfully!", "success");
    } else {
      throw new Error("Save request failed");
    }
  } catch (err) {
    console.error("Save profile error", err);
    logEvent("error", "Failed to save profile changes.");
  }
}

async function applyToJob(event, jobId) {
  event.stopPropagation();
  const btn = event.target;
  btn.disabled = true;
  btn.innerText = "⏳ Starting...";
  btn.classList.add("applying-indicator");

  try {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/apply`, {
      method: "POST",
    });
    if (res.ok) {
      logEvent("system", `Application pipeline launched for job ${jobId.slice(0, 8)}...`);
      btn.innerText = "⏳ Applying...";
      // Update the job's local status
      const job = jobs.find(j => j.id === jobId);
      if (job) job.status = "applying";
      renderJobs();
    } else {
      throw new Error(`HTTP ${res.status}`);
    }
  } catch (err) {
    console.error("Apply error", err);
    logEvent("error", `Failed to launch application: ${err.message}`);
    btn.innerText = "🚀 Apply";
    btn.disabled = false;
    btn.classList.remove("applying-indicator");
  }
}

// ---------------------------------------------------------------------------
// Toast Notification Engine
// ---------------------------------------------------------------------------
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  const icon = type === "success" ? "✓" : type === "clear" ? "🗑️" : type === "error" ? "⚠️" : "ℹ️";
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <div class="toast-icon">${icon}</div>
    <div class="toast-message">${escapeHtml(message)}</div>
  `;

  container.appendChild(toast);

  requestAnimationFrame(() => {
    toast.classList.add("visible");
  });

  setTimeout(() => {
    toast.classList.remove("visible");
    setTimeout(() => {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 400);
  }, 3500);
}

// ---------------------------------------------------------------------------
// Canvas Particle Dustbin Disintegration Engine
// ---------------------------------------------------------------------------
function animateDustbinDisintegration(targetCards, onComplete) {
  if (!targetCards || targetCards.length === 0) {
    if (onComplete) onComplete();
    return;
  }

  const canvas = document.getElementById("particle-disintegration-canvas");
  const widget = document.getElementById("dustbin-animation-widget");
  if (!canvas || !widget) {
    if (onComplete) onComplete();
    return;
  }

  // Set high-DPI canvas size
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
  const ctx = canvas.getContext("2d");

  // Destination point: Open mouth of the dustbin can
  const destX = window.innerWidth - 100;
  const destY = window.innerHeight - 140;

  // Step 1: Slide up dustbin widget & open lid dramatically
  widget.classList.add("visible");
  widget.classList.add("open-lid");

  const particles = [];
  const particleColors = [
    "#ef4444", "#f87171", "#dc2626", "#f59e0b", "#fbbf24",
    "#f43f5e", "#ec4899", "#a855f7", "#ffffff", "#38bdf8"
  ];

  targetCards.forEach(card => {
    if (card && card.classList) card.classList.add("disintegrating-card");
    const rect = card ? card.getBoundingClientRect() : { left: window.innerWidth / 2, top: window.innerHeight / 2, width: 300, height: 180 };
    
    // Density: ~200-350 particles per card for Thanos snap disintegrate
    const cols = 25;
    const rows = 12;
    const cellW = rect.width / cols;
    const cellH = rect.height / rows;

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const startX = rect.left + c * cellW + Math.random() * cellW;
        const startY = rect.top + r * cellH + Math.random() * cellH;

        particles.push({
          startX: startX,
          startY: startY,
          curX: startX,
          curY: startY,
          vx: (Math.random() - 0.5) * 8, // Explosive initial velocity
          vy: (Math.random() - 0.5) * 8 - 3,
          size: Math.random() * 4 + 2,
          color: particleColors[Math.floor(Math.random() * particleColors.length)],
          phase: 1, // Phase 1 = Explode dust, Phase 2 = Swirl to dustbin
          progress: 0,
          delay: (c / cols) * 0.25 + (r / rows) * 0.15, // Wave disintegration from top-left
          speed: 0.015 + Math.random() * 0.02,
          curve: (Math.random() - 0.5) * 160,
        });
      }
    }
  });

  let startTime = null;
  const totalDuration = 1800; // 1.8s total epic sequence

  function drawFrame(timestamp) {
    if (!startTime) startTime = timestamp;
    const elapsed = timestamp - startTime;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    let activeCount = 0;

    particles.forEach(p => {
      // Delay before particle breaks off
      if (elapsed < p.delay * 1000) {
        activeCount++;
        return;
      }

      p.progress += p.speed;
      if (p.progress >= 1) return;

      activeCount++;
      const t = p.progress;

      // Phase 1 (0 to 0.3): Burst outward in dust cloud
      if (t < 0.25) {
        const burstT = t / 0.25;
        p.curX = p.startX + p.vx * burstT * 12;
        p.curY = p.startY + p.vy * burstT * 12;
      } else {
        // Phase 2 (0.25 to 1.0): Accelerate into Dustbin Vortex
        const flightT = (t - 0.25) / 0.75;
        const burstX = p.startX + p.vx * 12;
        const burstY = p.startY + p.vy * 12;

        const controlX = (burstX + destX) / 2 + p.curve;
        const controlY = Math.min(burstY, destY) - 150;

        p.curX = (1 - flightT) * (1 - flightT) * burstX + 2 * (1 - flightT) * flightT * controlX + flightT * flightT * destX;
        p.curY = (1 - flightT) * (1 - flightT) * burstY + 2 * (1 - flightT) * flightT * controlY + flightT * flightT * destY;
      }

      const alpha = t > 0.85 ? (1 - t) / 0.15 : 1;

      // Draw particle with glowing motion trail
      ctx.save();
      ctx.globalAlpha = alpha;
      ctx.fillStyle = p.color;
      ctx.shadowBlur = 12;
      ctx.shadowColor = p.color;

      ctx.beginPath();
      ctx.arc(p.curX, p.curY, p.size * (1 - t * 0.5), 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    });

    // Dustbin pulse glow during particle suction
    if (elapsed > 500 && elapsed < 1400) {
      widget.classList.add("pulse-glow");
    } else {
      widget.classList.remove("pulse-glow");
    }

    if (elapsed < totalDuration && activeCount > 0) {
      requestAnimationFrame(drawFrame);
    } else {
      // Step 3: Slam lid closed, clear canvas, pulse shockwave
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      widget.classList.remove("open-lid");
      widget.classList.remove("pulse-glow");
      widget.classList.add("lid-slam");

      setTimeout(() => {
        widget.classList.remove("visible");
        widget.classList.remove("lid-slam");
        if (onComplete) onComplete();
      }, 550);
    }
  }

  requestAnimationFrame(drawFrame);
}

async function deleteSingleJob(event, jobId) {
  if (event) event.stopPropagation();
  const cardBtn = event ? event.currentTarget : null;
  const card = cardBtn ? cardBtn.closest(".clean-job-card") : null;
  const cardsToAnimate = card ? [card] : [];

  animateDustbinDisintegration(cardsToAnimate, async () => {
    try {
      const res = await fetch(`${API_BASE}/jobs/${jobId}`, {
        method: "DELETE"
      });
      if (res.ok) {
        jobs = jobs.filter(j => j.id !== jobId);
        await loadInitialData();
        showToast("Job posting & associated CVs deleted", "success");
      }
    } catch (err) {
      console.error("Delete job error", err);
      showToast("Failed to delete job", "error");
    }
  });
}

function clearAllJobs() {
  const modal = document.getElementById("clear-confirm-modal");
  if (modal) modal.classList.remove("hidden");
}

function closeClearModal() {
  const modal = document.getElementById("clear-confirm-modal");
  if (modal) modal.classList.add("hidden");
}

async function confirmClearAllJobs() {
  closeClearModal();
  const allCards = Array.from(document.querySelectorAll(".clean-job-card"));

  animateDustbinDisintegration(allCards, async () => {
    try {
      const res = await fetch(`${API_BASE}/jobs/clear`, {
        method: "POST"
      });
      if (res.ok) {
        jobs = [];
        outreachDrafts = [];
        interventionSessions.length = 0;
        await loadInitialData();
        showToast("All jobs, optimized CVs & outreach drafts cleared!", "clear");
      }
    } catch (err) {
      console.error("Clear jobs error", err);
      showToast("Failed to clear jobs", "error");
    }
  });
}

function resetSystemAction() {
  const modal = document.getElementById("reset-confirm-modal");
  const btn = document.getElementById("confirm-reset-btn");
  if (btn) {
    btn.removeAttribute("disabled");
    const spinner = btn.querySelector(".btn-spinner");
    const text = btn.querySelector(".btn-text");
    if (spinner) spinner.classList.add("hidden");
    if (text) text.innerText = "Yes, Stop Agent & Reset";
  }
  if (modal) modal.classList.remove("hidden");
}

function closeResetModal() {
  const modal = document.getElementById("reset-confirm-modal");
  if (modal) modal.classList.add("hidden");
}

async function confirmResetSystem() {
  const btn = document.getElementById("confirm-reset-btn");
  const spinner = btn ? btn.querySelector(".btn-spinner") : null;
  const text = btn ? btn.querySelector(".btn-text") : null;

  if (btn) btn.setAttribute("disabled", "true");
  if (spinner) spinner.classList.remove("hidden");
  if (text) text.innerText = "Halting Agents & Wiping Data...";

  try {
    const res = await fetch(`${API_BASE}/reset`, {
      method: "POST"
    });
    if (res.ok) {
      if (text) text.innerText = "System Reset Complete!";
      logEvent("system", "System database wiped and active tasks halted.");
      setTimeout(() => {
        closeResetModal();
        window.location.reload();
      }, 800);
    } else {
      throw new Error("Reset call failed");
    }
  } catch (err) {
    console.error("Reset error", err);
    if (text) text.innerText = "Reset Failed - Try Again";
    if (btn) btn.removeAttribute("disabled");
    if (spinner) spinner.classList.add("hidden");
  }
}

function handleSystemReset() {
  logEvent("system", "System database wiped. Reloading dashboard...");
  setTimeout(() => {
    window.location.reload();
  }, 1000);
}


let browserStepLog = [];

function handleBrowserStreamFrame(data) {
  // Live URL + title only (no screenshots). The real Chrome window is on the
  // user's desktop; this panel shows what page the agent is currently on.
  const urlInput = document.getElementById("browser-url-input");
  const liveUrl = document.getElementById("browser-live-url");
  const pageTitle = document.getElementById("browser-page-title");

  if (urlInput && data.url) urlInput.innerText = data.url;
  if (liveUrl && data.url) liveUrl.innerText = data.url;
  if (pageTitle && data.title) pageTitle.innerText = data.title || data.url;

  // Switch from idle standby to live state
  const idle = document.getElementById("browser-idle-state");
  const live = document.getElementById("browser-live-state");
  if (idle && live) {
    idle.classList.add("hidden");
    live.classList.remove("hidden");
  }

  const activeBadge = document.getElementById("browser-active-badge");
  if (activeBadge) activeBadge.classList.remove("hidden");

  const haltBtn = document.getElementById("halt-browser-btn");
  if (haltBtn) haltBtn.classList.remove("hidden");
}

function handleBrowserStep(data) {
  const activeBadge = document.getElementById("browser-active-badge");
  if (activeBadge) activeBadge.classList.remove("hidden");

  const haltBtn = document.getElementById("halt-browser-btn");
  if (haltBtn) haltBtn.classList.remove("hidden");

  const urlInput = document.getElementById("browser-url-input");
  if (urlInput) urlInput.innerText = data.url || "about:blank";

  const liveUrl = document.getElementById("browser-live-url");
  const pageTitle = document.getElementById("browser-page-title");
  if (liveUrl && data.url) liveUrl.innerText = data.url;
  if (pageTitle) pageTitle.innerText = data.action ? data.action.slice(0, 60) : "Working…";

  const idle = document.getElementById("browser-idle-state");
  const live = document.getElementById("browser-live-state");
  if (idle && live) {
    idle.classList.add("hidden");
    live.classList.remove("hidden");
  }

  const stepCount = document.getElementById("timeline-step-count");
  if (stepCount) {
    stepCount.innerText = `${data.step} Steps Executed`;
  }

  const stepsLogContainer = document.getElementById("browser-steps-log");
  if (stepsLogContainer) {
    if (data.step === 1 || browserStepLog.length === 0) {
      stepsLogContainer.innerHTML = "";
      browserStepLog = [];
    }

    const stepItem = document.createElement("div");
    stepItem.className = "browser-step-item";
    stepItem.innerHTML = `
      <div class="step-badge">Step ${data.step}</div>
      <div class="step-desc">${escapeHtml(data.action)}</div>
      <div class="step-meta">${escapeHtml(data.company)} — ${escapeHtml(data.role)}</div>
    `;
    stepsLogContainer.appendChild(stepItem);
    stepsLogContainer.scrollTop = stepsLogContainer.scrollHeight;
  }

  browserStepLog.push(data);

  const browserTabBtn = document.getElementById("tab-browser");
  if (browserTabBtn && !browserTabBtn.classList.contains("active")) {
    browserTabBtn.classList.add("pulse-highlight");
  }
}

async function haltBrowserAction() {
  const haltBtn = document.getElementById("halt-browser-btn");
  if (haltBtn) {
    haltBtn.setAttribute("disabled", "true");
    haltBtn.innerText = "Halting...";
  }
  try {
    const res = await fetch(`${API_BASE}/stop-browser`, {
      method: "POST"
    });
    if (res.ok) {
      logEvent("system", "Halt requested. Active browser session stopped.");
      const activeBadge = document.getElementById("browser-active-badge");
      if (activeBadge) activeBadge.classList.add("hidden");

      const idle = document.getElementById("browser-idle-state");
      const live = document.getElementById("browser-live-state");
      const canvas = document.getElementById("browser-cdp-canvas");
      if (live) live.classList.add("hidden");
      if (canvas) canvas.classList.add("hidden");
      if (idle) idle.classList.remove("hidden");
    }
  } catch (err) {
    console.error("Error halting browser", err);
    logEvent("error", "Failed to halt browser.");
  } finally {
    if (haltBtn) {
      haltBtn.removeAttribute("disabled");
      haltBtn.classList.add("hidden");
      haltBtn.innerText = "Halt Browser";
    }
  }
}

// Track the active job_id for takeover/release calls.
let _activeBrowserJobId = "";
let _takeoverActive = false;

// Wire up the click-to-takeover surface once DOM is ready.
(function wireTakeoverSurface() {
  const attach = () => {
    const surface = document.getElementById("browser-viewport-surface");
    const cta = document.getElementById("browser-takeover-cta");
    const target = cta || surface;
    if (!target) { setTimeout(attach, 200); return; }
    target.addEventListener("click", () => {
      if (_takeoverActive) return;
      requestBrowserTakeover();
    });
  };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", attach);
  } else {
    attach();
  }
})();

async function requestBrowserTakeover() {
  try {
    const url = `${API_BASE}/browser/takeover${_activeBrowserJobId ? "?job_id=" + encodeURIComponent(_activeBrowserJobId) : ""}`;
    const res = await fetch(url, { method: "POST" });
    if (!res.ok) throw new Error("takeover failed");
    const data = await res.json();
    _takeoverActive = true;
    showTakeoverOverlay();
    logEvent("system", "Browser control taken over. Chrome window focused.");
  } catch (err) {
    console.error("takeover error", err);
    logEvent("error", "Could not take over browser. Is a session running?");
  }
}

async function releaseBrowserControl() {
  try {
    const url = `${API_BASE}/browser/release${_activeBrowserJobId ? "?job_id=" + encodeURIComponent(_activeBrowserJobId) : ""}`;
    const res = await fetch(url, { method: "POST" });
    if (!res.ok) throw new Error("release failed");
    _takeoverActive = false;
    hideTakeoverOverlay();
    logEvent("system", "Browser control released. Agent resuming.");
  } catch (err) {
    console.error("release error", err);
    _takeoverActive = false;
    hideTakeoverOverlay();
  }
}

function showTakeoverOverlay() {
  const overlay = document.getElementById("browser-takeover-overlay");
  const live = document.getElementById("browser-live-state");
  const canvas = document.getElementById("browser-cdp-canvas");
  if (overlay) overlay.classList.remove("hidden");
  if (live) live.classList.add("hidden");
  if (canvas) canvas.classList.add("hidden");
  const chipAgent = document.getElementById("live-chip-agent");
  const chipWindow = document.getElementById("live-chip-window");
  if (chipAgent) chipAgent.classList.add("hidden");
  if (chipWindow) chipWindow.classList.remove("hidden");
}

function hideTakeoverOverlay() {
  const overlay = document.getElementById("browser-takeover-overlay");
  const live = document.getElementById("browser-live-state");
  const canvas = document.getElementById("browser-cdp-canvas");
  if (overlay) overlay.classList.add("hidden");
  if (live) live.classList.remove("hidden");
  if (canvas) canvas.classList.remove("hidden");
  const chipAgent = document.getElementById("live-chip-agent");
  const chipWindow = document.getElementById("live-chip-window");
  if (chipAgent) chipAgent.classList.remove("hidden");
  if (chipWindow) chipWindow.classList.add("hidden");
}

// Track the active job id from incoming browser events.
const _origHandleBrowserStep = window.handleBrowserStep;
window.handleBrowserStep = function(data) {
  if (data && data.job_id) _activeBrowserJobId = data.job_id;
  if (_origHandleBrowserStep) _origHandleBrowserStep(data);
};
const _origHandleBrowserStreamFrame = window.handleBrowserStreamFrame;
window.handleBrowserStreamFrame = function(data) {
  if (data && data.job_id) _activeBrowserJobId = data.job_id;
  if (_origHandleBrowserStreamFrame) _origHandleBrowserStreamFrame(data);
};

// ---------------------------------------------------------------------------
// CDP Live Stream — Embedded Browser Canvas
// ---------------------------------------------------------------------------
let _browserWs = null;
let _browserCanvas = null;
let _browserCtx = null;
let _browserWsConnected = false;

function initBrowserCDPStream() {
  _browserCanvas = document.getElementById("browser-cdp-canvas");
  if (_browserCanvas) {
    _browserCtx = _browserCanvas.getContext("2d");
    // Capture mouse events on the canvas
    _browserCanvas.addEventListener("mousedown", (e) => _sendCanvasMouseEvent(e, "click"));
    _browserCanvas.addEventListener("mouseup", (e) => _sendCanvasMouseEvent(e, "up"));
    _browserCanvas.addEventListener("mousemove", (e) => {
      if (e.buttons) _sendCanvasMouseEvent(e, "move");
    });
    _browserCanvas.addEventListener("dblclick", (e) => _sendCanvasMouseEvent(e, "dblclick"));
    _browserCanvas.addEventListener("wheel", (e) => {
      e.preventDefault();
      _sendCanvasWheelEvent(e);
    }, { passive: false });
    // Keyboard events — focus canvas first
    _browserCanvas.setAttribute("tabindex", "0");
    _browserCanvas.addEventListener("keydown", (e) => _sendCanvasKeyEvent(e, "keyDown"));
    _browserCanvas.addEventListener("keyup", (e) => _sendCanvasKeyEvent(e, "keyUp"));
  }
  connectBrowserWebSocket();
}

function connectBrowserWebSocket() {
  if (_browserWs && _browserWs.readyState === WebSocket.OPEN) return;
  const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/browser`;
  _browserWs = new WebSocket(wsUrl);

  _browserWs.onopen = () => {
    _browserWsConnected = true;
    console.log("Browser CDP WebSocket connected");
  };

  _browserWs.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.type === "frame" && msg.data) {
      renderCDPFrame(msg.data, msg.width, msg.height);
    }
  };

  _browserWs.onclose = () => {
    _browserWsConnected = false;
    // Reconnect after delay if still on browser tab
    setTimeout(() => {
      const browserTab = document.getElementById("tab-browser");
      if (browserTab && browserTab.classList.contains("active")) {
        connectBrowserWebSocket();
      }
    }, 3000);
  };

  _browserWs.onerror = (err) => {
    console.error("Browser CDP WS error", err);
  };
}

function renderCDPFrame(b64Data, width, height) {
  if (!_browserCanvas || !_browserCtx) return;

  // Show canvas, hide idle/live state overlays
  const idle = document.getElementById("browser-idle-state");
  const live = document.getElementById("browser-live-state");
  const takeover = document.getElementById("browser-takeover-overlay");
  if (idle) idle.classList.add("hidden");
  if (live) live.classList.add("hidden");
  if (takeover && !takeover.classList.contains("hidden")) return; // Don't hide takeover overlay
  _browserCanvas.classList.remove("hidden");

  const img = new Image();
  img.onload = () => {
    _browserCanvas.width = img.width;
    _browserCanvas.height = img.height;
    _browserCtx.drawImage(img, 0, 0);
  };
  img.src = "data:image/jpeg;base64," + b64Data;
}

function _getCanvasCoords(e) {
  if (!_browserCanvas) return { x: 0, y: 0 };
  const rect = _browserCanvas.getBoundingClientRect();
  const scaleX = _browserCanvas.width / rect.width;
  const scaleY = _browserCanvas.height / rect.height;
  return {
    x: Math.round((e.clientX - rect.left) * scaleX),
    y: Math.round((e.clientY - rect.top) * scaleY),
  };
}

function _sendCanvasMouseEvent(e, action) {
  if (!_browserWs || _browserWs.readyState !== WebSocket.OPEN) return;
  const coords = _getCanvasCoords(e);
  _browserWs.send(JSON.stringify({
    type: "mouse",
    action: action,
    x: coords.x,
    y: coords.y,
    button: e.button,
  }));
}

function _sendCanvasWheelEvent(e) {
  if (!_browserWs || _browserWs.readyState !== WebSocket.OPEN) return;
  const coords = _getCanvasCoords(e);
  _browserWs.send(JSON.stringify({
    type: "wheel",
    x: coords.x,
    y: coords.y,
    deltaX: e.deltaX,
    deltaY: e.deltaY,
  }));
}

function _sendCanvasKeyEvent(e, action) {
  if (!_browserWs || _browserWs.readyState !== WebSocket.OPEN) return;
  // Don't send modifier-only keys that would conflict with browser shortcuts
  if (["Control", "Alt", "Shift", "Meta"].includes(e.key)) return;
  _browserWs.send(JSON.stringify({
    type: "keyboard",
    action: action,
    key: e.key,
    code: e.code,
    text: action === "keyDown" ? e.key : "",
  }));
  e.preventDefault();
}

// Initialize CDP stream when DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initBrowserCDPStream);
} else {
  initBrowserCDPStream();
}

// Reconnect browser WS when switching to browser tab
const _origSwitchTab = window.switchTab;
window.switchTab = function(tabName) {
  if (_origSwitchTab) _origSwitchTab(tabName);
  if (tabName === "browser") {
    connectBrowserWebSocket();
    if (_browserCanvas) _browserCanvas.focus();
  }
};

// ---------------------------------------------------------------------------
// Clear All Jobs & System Reset Modals
// ---------------------------------------------------------------------------

function clearAllJobs() {
  const modal = document.getElementById("clear-confirm-modal");
  if (modal) modal.classList.remove("hidden");
}

function closeClearModal() {
  const modal = document.getElementById("clear-confirm-modal");
  if (modal) modal.classList.add("hidden");
}

async function confirmClearAllJobs() {
  const btn = document.getElementById("confirm-clear-btn");
  if (btn) btn.setAttribute("disabled", "true");
  try {
    const res = await fetch(`${API_BASE}/jobs/clear`, { method: "POST" });
    const data = await res.json();
    closeClearModal();
    logEvent("system", `Cleared ${data.cleared_count || 0} jobs from queue.`);
    loadInitialData();
  } catch (err) {
    console.error("Failed to clear jobs:", err);
    logEvent("error", "Failed to clear jobs from queue.");
  } finally {
    if (btn) btn.removeAttribute("disabled");
  }
}

function handleSystemReset() {
  jobs = [];
  renderJobs();
  const container = document.getElementById("jobs-container");
  if (container) container.innerHTML = `<div class="empty-state">Queue reset. Ready for new search.</div>`;
  loadInitialData();
}