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
  // Update nav buttons
  document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));
  document.getElementById(`tab-${tabName}`).classList.add("active");

  // Update views
  document.querySelectorAll(".tab-view").forEach(view => view.classList.remove("active"));
  document.getElementById(`view-${tabName}`).classList.add("active");
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

    // Load existing outreach
    const outreachRes = await fetch(`${API_BASE}/outreach`);
    const outreachData = await outreachRes.json();
    outreachDrafts = outreachData.drafts || [];
    renderOutreach();

    // Try loading latest profile implicitly
    const profileRes = await fetch(`${API_BASE}/status`); // Let routes evaluate
    // If a profile exists in the DB, it gets populated inside active state
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

  const container = document.getElementById("profile-skills");
  container.innerHTML = "";
  (currentProfile.skills || []).forEach(skill => {
    const tag = document.createElement("span");
    tag.className = "skill-tag";
    tag.innerText = skill;
    container.appendChild(tag);
  });
}

// ---------------------------------------------------------------------------
// Search Controls
// ---------------------------------------------------------------------------
async function startSearch() {
  const location = document.getElementById("target-location").value.trim();
  if (!location) return;

  logEvent("system", `Starting job search in location: ${location}`);
  document.getElementById("start-search-btn").setAttribute("disabled", "true");

  try {
    const res = await fetch(`${API_BASE}/start-search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ location })
    });
    const data = await res.json();
    updateStatusIndicator("running");
  } catch (err) {
    console.error("Search start error", err);
    logEvent("error", "Failed to start active pipeline.");
    document.getElementById("start-search-btn").removeAttribute("disabled");
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
  // If it's standard logging event
  if (msg.event_type === "progress" || msg.event_type === "discovery" || msg.event_type === "error" || msg.event_type === "complete") {
    logEvent(msg.agent || "system", msg.message, msg.event_type === "error");
  }

  // Reload telemetry usage if tokens updated
  if (msg.data && (msg.data.tokens_in || msg.data.tokens_out)) {
    loadInitialData(); // Lazy refresh
  }

  // Handle explicit profile loads
  if (msg.event_type === "profile_loaded") {
    loadInitialData();
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
    card.className = "job-card";

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
  const container = document.getElementById("logs-container");
  
  const entry = document.createElement("div");
  entry.className = `log-entry ${agent} ${isError ? 'error' : ''}`;
  
  const time = document.createElement("span");
  time.className = "log-time";
  time.innerText = new Date().toLocaleTimeString();

  const text = document.createElement("span");
  text.innerText = `[${agent.toUpperCase()}] ${message}`;

  entry.appendChild(time);
  entry.appendChild(text);
  container.appendChild(entry);
  container.scrollTop = container.scrollHeight;
}

function clearLogs() {
  document.getElementById("logs-container").innerHTML = "";
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
