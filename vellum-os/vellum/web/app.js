/* ---------------------------------------------------------------------------
   Vellum OS — Frontend Application Logic (app.js)
   Handles WebSockets, HTTP REST endpoints, state sync, telemetry counters,
   and dynamic UI element bindings.
   --------------------------------------------------------------------------- */

// State
let ws = null;
let currentProfile = null;
let jobs = [];
let outreachDrafts = [];
let tokenUsage = {};
let hitlActiveJobId = null;
let activeOutreachId = null;

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
  document.getElementById("start-search-btn").addEventListener("click", startSearch);

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
      if (typeof closeHitlModal === "function") closeHitlModal();
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
}

// ---------------------------------------------------------------------------
// Load Initial Data
// ---------------------------------------------------------------------------
async function loadInitialData() {
  try {
    // Load Status & Token Telemetry
    const statusRes = await fetch(`${API_BASE}/status`);
    const statusData = await statusRes.json();
    updateStatusIndicator(statusData.status);
    updateTokenTelemetry(statusData.token_usage);

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
  card.classList.remove("hidden");

  document.getElementById("profile-name").innerText = currentProfile.name;
  document.getElementById("profile-email").innerText = currentProfile.email;
  document.getElementById("profile-phone").innerText = currentProfile.phone;
  document.getElementById("profile-location").innerText = currentProfile.location;

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
    (currentProfile.skills || []).forEach(skill => {
      const tag = document.createElement("span");
      tag.className = "skill-tag";
      tag.innerText = skill;
      container.appendChild(tag);
    });
  }
}

// ---------------------------------------------------------------------------
// Search Controls
// ---------------------------------------------------------------------------
async function startSearch() {
  const location = document.getElementById("target-location").value.trim();
  const role = document.getElementById("target-role").value.trim();
  if (!location) return;

  logEvent("system", `Starting job search for "${role || 'Software Engineer'}" in "${location}"`);
  document.getElementById("start-search-btn").setAttribute("disabled", "true");

  // Reset progress bar
  const bar = document.getElementById("sidebar-progress-bar");
  if (bar) bar.style.width = "0%";
  const progressStatus = document.getElementById("sidebar-progress-status");
  if (progressStatus) progressStatus.innerText = "Initializing search...";

  // Show halt button
  const haltBtn = document.getElementById("halt-browser-btn");
  if (haltBtn) haltBtn.classList.remove("hidden");

  try {
    const res = await fetch(`${API_BASE}/start-search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ location, role })
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
  if (msg.event_type === "search_progress") {
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

  // Handle browser agent automation steps
  if (msg.event_type === "browser_step") {
    handleBrowserStep(msg.data);
  }

  // Handle live browser real-time frame streaming
  if (msg.event_type === "browser_stream_frame") {
    handleBrowserStreamFrame(msg.data);
  }

  // Handle HITL Request Event
  if (msg.event_type === "hitl_request") {
    showHitlModal(msg.job_id, msg.data.type, msg.message, msg.data.url);
  }

  // Reload data for job/outreach updates
  if (msg.event_type === "discovery" || msg.event_type === "complete") {
    loadInitialData();
  }
}

// ---------------------------------------------------------------------------
// UI Renders & Formatting
// ---------------------------------------------------------------------------
function renderJobs() {
  const container = document.getElementById("jobs-container");
  if (jobs.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <span class="empty-icon">📁</span>
        <p>No job listings found yet.</p>
      </div>`;
    document.getElementById("stat-discovered").innerText = "0";
    document.getElementById("stat-applied").innerText = "0";
    return;
  }

  let appliedCount = 0;
  container.innerHTML = "";

  jobs.forEach(job => {
    if (job.status === "applied") appliedCount++;

    const card = document.createElement("div");
    card.className = "job-card job-card-enhanced";

    // Build badges for scoring
    const confidenceScore = job.discovery_confidence || 0;
    const matchScore = job.match_score || 0;
    const confClass = confidenceScore > 0.7 ? "conf-high" : confidenceScore > 0.4 ? "conf-med" : "conf-low";
    const matchClass = matchScore > 0.7 ? "conf-high" : matchScore > 0.4 ? "conf-med" : "conf-low";

    card.innerHTML = `
      <div class="card-header">
        <div>
          <div class="company-title">${escapeHtml(job.company)}</div>
          <div class="role-title">${escapeHtml(job.role || "Software Engineering Role")}</div>
        </div>
      </div>
      <div class="badge-row">
        <span class="conf-badge ${confClass}">Discover: ${(confidenceScore * 100).toFixed(0)}%</span>
        <span class="conf-badge ${matchClass}">Match: ${(matchScore * 100).toFixed(0)}%</span>
      </div>
      <div class="card-footer">
        <span class="job-status-indicator ${job.status}">${job.status.replace('_', ' ')}</span>
        ${job.status === 'matched' ? `<button class="card-action-btn" onclick="downloadResume('${job.id}')">Download tailored PDF</button>` : ''}
        ${job.status === 'needs_attention' ? `<button class="card-action-btn" onclick="triggerHitlResume('${job.id}')">Review & Solve</button>` : ''}
      </div>
    `;
    container.appendChild(card);
  });

  document.getElementById("stat-discovered").innerText = jobs.length;
  document.getElementById("stat-applied").innerText = appliedCount;
}

function renderResumes() {
  const container = document.getElementById("resumes-container");
  if (!container) return;

  const matchedJobs = jobs.filter(j => j.status === 'matched' || j.status === 'applied' || j.status === 'applying' || j.status === 'needs_attention');

  if (matchedJobs.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon-circle">📄</div>
        <h3>No tailored resumes generated yet</h3>
        <p>Tailored resumes and CVs created for matched job postings will appear here automatically.</p>
      </div>`;
    return;
  }

  container.innerHTML = "";
  matchedJobs.forEach(job => {
    const card = document.createElement("div");
    card.className = "job-card job-card-enhanced";

    const matchScore = job.match_score || 0;
    const matchClass = matchScore > 0.7 ? "conf-high" : matchScore > 0.4 ? "conf-med" : "conf-low";

    card.innerHTML = `
      <div class="card-header">
        <div>
          <div class="company-title">${escapeHtml(job.company)}</div>
          <div class="role-title">${escapeHtml(job.role || "Software Role")}</div>
        </div>
      </div>
      <div class="badge-row">
        <span class="conf-badge ${matchClass}">Match: ${(matchScore * 100).toFixed(0)}%</span>
        <span class="conf-badge conf-high">ATS Resume Tailored</span>
      </div>
      <div class="card-footer">
        <span class="job-status-indicator ${job.status}">${job.status.replace('_', ' ')}</span>
        <button class="card-action-btn" onclick="downloadResume('${job.id}')">📥 Download PDF CV</button>
      </div>
    `;
    container.appendChild(card);
  });
}


function renderOutreach() {
  const container = document.getElementById("outreach-container");
  if (outreachDrafts.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <span class="empty-icon">✉️</span>
        <p>No outreach drafts generated.</p>
      </div>`;
    document.getElementById("stat-outreach").innerText = "0";
    return;
  }

  container.innerHTML = "";
  outreachDrafts.forEach(draft => {
    const card = document.createElement("div");
    card.className = "outreach-card";

    const score = draft.confidence || 0;
    const confClass = score > 0.7 ? "conf-high" : score > 0.4 ? "conf-med" : "conf-low";

    card.innerHTML = `
      <div class="card-header">
        <div>
          <div class="company-title">${escapeHtml(draft.company)}</div>
          <div class="role-title">${escapeHtml(draft.contact_name)} (${escapeHtml(draft.contact_role)})</div>
        </div>
      </div>
      <div class="badge-row">
        <span class="conf-badge ${confClass}">Confidence: ${(score * 100).toFixed(0)}%</span>
        <span class="conf-badge conf-med">MX Records Checked</span>
      </div>
      <div class="card-footer">
        <span class="job-status-indicator matched">${escapeHtml(draft.status)}</span>
        <button class="card-action-btn" onclick="openOutreachComposer('${draft.id}')">Compose & Send</button>
      </div>
    `;
    container.appendChild(card);
  });

  document.getElementById("stat-outreach").innerText = outreachDrafts.length;
}

// ---------------------------------------------------------------------------
// Telemetry Indicators
// ---------------------------------------------------------------------------
function updateStatusIndicator(status) {
  const badge = document.getElementById("status-badge");
  badge.className = `status-badge ${status}`;
  badge.innerText = status;

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

function logEvent(agent, message, isError = false) {
  const statusTextEl = document.getElementById("sidebar-progress-status");
  const dotEl = document.getElementById("sidebar-progress-dot");
  const miniLogsEl = document.getElementById("progress-mini-logs");
  
  if (statusTextEl && dotEl && miniLogsEl) {
    const msgLower = message.toLowerCase();
    let statusLabel = "System Active";
    let isIdle = false;
    
    if (msgLower.includes("idle") || msgLower.includes("system initialized")) {
      statusLabel = "System Idle";
      isIdle = true;
    } else if (msgLower.includes("discovery") || msgLower.includes("searching") || msgLower.includes("scraped")) {
      statusLabel = "Searching Roles";
    } else if (msgLower.includes("validat") || msgLower.includes("score")) {
      statusLabel = "Matching Profile";
    } else if (msgLower.includes("apply") || msgLower.includes("filling") || msgLower.includes("automation")) {
      statusLabel = "Auto-Applying";
    } else if (msgLower.includes("submitted") || msgLower.includes("completed")) {
      statusLabel = "Job Applied!";
    } else if (agent === "outreach") {
      statusLabel = "Outreach Active";
    }
    
    statusTextEl.innerText = statusLabel;
    
    dotEl.className = "status-dot";
    if (isError) {
      dotEl.classList.add("error");
    } else if (isIdle) {
      // Idle has no pulse
    } else {
      dotEl.classList.add("running");
    }
    
    const entry = document.createElement("div");
    entry.className = "mini-log-item";
    if (isError) entry.classList.add("error");
    else if (msgLower.includes("success") || msgLower.includes("completed") || msgLower.includes("submitted")) {
      entry.classList.add("success");
    }
    entry.innerText = message;
    
    if (miniLogsEl.children.length === 1 && miniLogsEl.children[0].innerText.includes("Ready")) {
      miniLogsEl.innerHTML = "";
    }
    
    miniLogsEl.appendChild(entry);
    
    while (miniLogsEl.children.length > 5) {
      miniLogsEl.removeChild(miniLogsEl.firstChild);
    }
    
    miniLogsEl.scrollTop = miniLogsEl.scrollHeight;
  }
}

function clearLogs() {
  const miniLogsEl = document.getElementById("progress-mini-logs");
  if (miniLogsEl) {
    miniLogsEl.innerHTML = `<div class="mini-log-item">Ready.</div>`;
  }
}

// ---------------------------------------------------------------------------
// HITL Interaction Overlay
// ---------------------------------------------------------------------------
function showHitlModal(jobId, type, message, url) {
  hitlActiveJobId = jobId;
  document.getElementById("hitl-message").innerText = message;
  document.getElementById("hitl-url").href = url;
  
  // Try loading screenshot dynamically
  document.getElementById("hitl-screenshot").src = `${API_BASE}/screenshots/${jobId}/last.png?t=${Date.now()}`;
  document.getElementById("hitl-modal").classList.remove("hidden");
}

function closeHitlModal() {
  document.getElementById("hitl-modal").classList.add("hidden");
  hitlActiveJobId = null;
}

async function submitHitlResponse(action) {
  if (!hitlActiveJobId) return;

  try {
    const res = await fetch(`${API_BASE}/resume-agent`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        job_id: hitlActiveJobId,
        action: action
      })
    });
    
    closeHitlModal();
    loadInitialData();
  } catch (err) {
    console.error("Failed to resume agent state", err);
  }
}

function triggerHitlResume(jobId) {
  const job = jobs.find(j => j.id === jobId);
  if (job) {
    showHitlModal(job.id, "manual_form", "Needs attention — please verify details or perform the next steps.", job.apply_url || job.career_page_url);
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

  const guessesList = document.getElementById("modal-email-guesses");
  guessesList.innerHTML = "";
  
  (draft.email_guesses || []).forEach(guess => {
    const item = document.createElement("div");
    item.className = "email-guess-item";
    
    const label = guess.mx_valid === false ? " (MX Failed)" : " (MX Verified)";
    const style = guess.mx_valid === false ? "color: var(--error-color)" : "color: var(--success-color)";
    
    item.innerHTML = `
      <span>${escapeHtml(guess.address)}</span>
      <div class="guess-meta">
        <span class="conf-badge conf-med" style="${style}">${guess.pattern}${label}</span>
      </div>
    `;
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

async function triggerMailtoHandoff() {
  if (!activeOutreachId) return;
  
  // Sync local edits back to server representation (optional, let's just trigger URI)
  try {
    const res = await fetch(`${API_BASE}/outreach/${activeOutreachId}/open-mail`, {
      method: "POST"
    });
    closeOutreachModal();
    logEvent("system", "Handoff to default system mail client completed.");
  } catch (err) {
    console.error("Failed to handoff mail", err);
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function downloadResume(jobId) {
  window.open(`${API_BASE}/jobs/${jobId}/resume-pdf`, "_blank");
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

// Minimal job state filter
function filterJobs(status) {
  document.querySelectorAll(".filter-btn").forEach(btn => btn.classList.remove("active"));
  event.target.classList.add("active");

  const cards = document.querySelectorAll(".job-card");
  cards.forEach(card => {
    const indicator = card.querySelector(".job-status-indicator");
    if (!indicator) return;
    
    if (status === 'all' || indicator.classList.contains(status)) {
      card.style.display = "flex";
    } else {
      card.style.display = "none";
    }
  });
}

// ---------------------------------------------------------------------------
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
  if (document.getElementById("prof-permanent-address")) document.getElementById("prof-permanent-address").value = currentProfile.permanent_address || "";
  if (document.getElementById("prof-suggested-role")) document.getElementById("prof-suggested-role").value = currentProfile.suggested_role || "";
  if (document.getElementById("prof-relevant-experience")) document.getElementById("prof-relevant-experience").value = currentProfile.relevant_experience || "";
  if (document.getElementById("prof-languages")) {
    const langs = Array.isArray(currentProfile.languages) ? currentProfile.languages.join(", ") : (currentProfile.languages || "");
    document.getElementById("prof-languages").value = langs;
  }
  document.getElementById("prof-summary").value = currentProfile.summary || "";

  
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
          <label>Institution</label>
          <input type="text" class="edu-institution" value="${escapeHtml(edu.institution || '')}">
        </div>
        <div class="form-group">
          <label>Degree</label>
          <input type="text" class="edu-degree" value="${escapeHtml(edu.degree || '')}">
        </div>
        <div class="form-group">
          <label>Start Date</label>
          <input type="text" class="edu-start" value="${escapeHtml(edu.start || '')}">
        </div>
        <div class="form-group">
          <label>End Date</label>
          <input type="text" class="edu-end" value="${escapeHtml(edu.end || '')}">
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
    return {
      institution: card.querySelector(".edu-institution").value.trim(),
      degree: card.querySelector(".edu-degree").value.trim(),
      start: card.querySelector(".edu-start").value.trim(),
      end: card.querySelector(".edu-end").value.trim()
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
    suggested_role: document.getElementById("prof-suggested-role") ? document.getElementById("prof-suggested-role").value.trim() : (currentProfile.suggested_role || ""),
    relevant_experience: document.getElementById("prof-relevant-experience") ? document.getElementById("prof-relevant-experience").value.trim() : (currentProfile.relevant_experience || ""),
    languages: document.getElementById("prof-languages") ? document.getElementById("prof-languages").value.split(",").map(l => l.trim()).filter(l => l) : (currentProfile.languages || []),
    summary: document.getElementById("prof-summary").value.trim(),
    skills: editedSkills,
    experience: editedExperience,
    education: editedEducation,
    projects: editedProjects,
    competitions: currentProfile.competitions || [],
    achievements: currentProfile.achievements || []
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
      alert("Profile changes saved successfully!");
    } else {
      throw new Error("Save request failed");
    }
  } catch (err) {
    console.error("Save profile error", err);
    logEvent("error", "Failed to save profile changes.");
  }
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
  const img = document.getElementById("browser-viewport-img");
  const idle = document.getElementById("browser-idle-state");
  const urlInput = document.getElementById("browser-url-input");
  
  if (urlInput && data.url) {
    urlInput.innerText = data.url;
  }
  
  if (data.screenshot && img && idle) {
    img.src = `data:image/jpeg;base64,${data.screenshot}`;
    img.classList.remove("hidden");
    idle.classList.add("hidden");
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
  
  const img = document.getElementById("browser-viewport-img");
  const idle = document.getElementById("browser-idle-state");
  if (data.screenshot && img && idle) {
    img.src = `data:image/png;base64,${data.screenshot}`;
    img.classList.remove("hidden");
    idle.classList.add("hidden");
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
      
      const img = document.getElementById("browser-viewport-img");
      const idle = document.getElementById("browser-idle-state");
      if (img && idle) {
        img.classList.add("hidden");
        idle.classList.remove("hidden");
      }
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
