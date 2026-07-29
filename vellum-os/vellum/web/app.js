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
  const limitInput = document.getElementById("target-analysis-limit");
  const limit = limitInput ? parseInt(limitInput.value, 10) || 50 : 50;

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
    if (job.status === "applied" || job.status === "applied_manual") appliedCount++;

    const card = document.createElement("div");
    card.className = "job-card job-card-enhanced clickable-card";

    // Build badges for scoring
    const confidenceScore = job.discovery_confidence || 0;
    const matchScore = job.match_score || (job.validation ? job.validation.match_score : 0);
    const confClass = confidenceScore > 0.7 ? "conf-high" : confidenceScore > 0.4 ? "conf-med" : "conf-low";
    const matchClass = matchScore > 0.7 ? "conf-high" : matchScore > 0.4 ? "conf-med" : "conf-low";

    const snippetText = job.jd_text ? job.jd_text.slice(0, 140) + "..." : "";
    const applyUrl = job.apply_url || job.career_page_url || "#";

    card.innerHTML = `
      <div class="card-header" onclick="openJobDetailsModal('${job.id}')" style="cursor: pointer;">
        <div>
          <div class="company-title">${escapeHtml(job.company)}</div>
          <div class="role-title">${escapeHtml(job.role || "Software Engineering Role")}</div>
        </div>
      </div>
      <div class="badge-row" onclick="openJobDetailsModal('${job.id}')" style="cursor: pointer;">
        <span class="conf-badge ${confClass}">Source: ${escapeHtml(job.source || 'ATS')}</span>
        <span class="conf-badge ${matchClass}">Match: ${(matchScore * 100).toFixed(0)}%</span>
      </div>
      ${snippetText ? `<div class="job-jd-snippet" onclick="openJobDetailsModal('${job.id}')" style="cursor: pointer;">${escapeHtml(snippetText)} <span class="jd-read-more-link">View Full JD & Details →</span></div>` : ''}
      <div class="job-meta-footer">
        <span class="job-location-badge">📍 ${escapeHtml(job.location || 'India / Remote')}</span>
        <a href="${escapeHtml(applyUrl)}" target="_blank" rel="noopener noreferrer" class="apply-link-badge">Direct Link ↗</a>
      </div>
      <div class="card-footer" style="margin-top: 8px;">
        <button class="card-action-btn view-jd-btn" onclick="openJobDetailsModal('${job.id}')">📄 View Job & JD</button>
        <span class="job-status-indicator ${job.status}">${job.status.replace('_', ' ')}</span>
        ${job.status === 'matched' || job.status === 'applied' ? `<button class="card-action-btn" onclick="downloadResume('${job.id}')">Download CV</button>` : ''}
        ${job.status !== 'skipped' && job.status !== 'applied' && job.status !== 'applying' ? `<button class="card-action-btn apply-btn" onclick="applyToJob(event, '${job.id}')">🚀 Apply</button>` : ''}
        ${job.status === 'applying' ? `<span class="card-action-btn applying-indicator">⏳ Applying...</span>` : ''}
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
    card.className = "job-card job-card-enhanced clickable-card";

    const matchScore = job.match_score || (job.validation ? job.validation.match_score : 0);
    const matchClass = matchScore > 0.7 ? "conf-high" : matchScore > 0.4 ? "conf-med" : "conf-low";

    card.innerHTML = `
      <div class="card-header" onclick="openJobDetailsModal('${job.id}')" style="cursor: pointer;">
        <div>
          <div class="company-title">${escapeHtml(job.company)}</div>
          <div class="role-title">${escapeHtml(job.role || "Software Role")}</div>
        </div>
      </div>
      <div class="badge-row" onclick="openJobDetailsModal('${job.id}')" style="cursor: pointer;">
        <span class="conf-badge ${matchClass}">Match: ${(matchScore * 100).toFixed(0)}%</span>
        <span class="conf-badge conf-high">ATS Resume Tailored</span>
      </div>
      <div class="card-footer">
        <button class="card-action-btn view-jd-btn" onclick="openJobDetailsModal('${job.id}')">📄 View Job & JD</button>
        <span class="job-status-indicator ${job.status}">${job.status.replace('_', ' ')}</span>
        <button class="card-action-btn" onclick="downloadResume('${job.id}')">📥 Download PDF CV</button>
      </div>
    `;
    container.appendChild(card);
  });
}

// ---------------------------------------------------------------------------
// Job & Job Description (JD) Details Modal Viewer
// ---------------------------------------------------------------------------
function openJobDetailsModal(jobId) {
  const job = jobs.find(j => j.id === jobId);
  if (!job) return;

  document.getElementById("jd-modal-company").innerText = job.company || "Company Name";
  document.getElementById("jd-modal-role-pill").innerText = job.role || "Software Engineering Role";
  document.getElementById("jd-modal-location").innerText = job.location || "India / Remote";
  document.getElementById("jd-modal-source").innerText = job.source || "ATS Discovery";

  const matchScore = job.match_score || (job.validation ? job.validation.match_score : 0);
  const matchClass = matchScore > 0.7 ? "conf-high" : matchScore > 0.4 ? "conf-med" : "conf-low";
  const matchBadge = document.getElementById("jd-modal-match-score");
  if (matchBadge) {
    matchBadge.className = `jd-meta-val conf-badge ${matchClass}`;
    matchBadge.innerText = `${(matchScore * 100).toFixed(0)}% Fit Match`;
  }

  const statusBadge = document.getElementById("jd-modal-status");
  if (statusBadge) {
    statusBadge.className = `jd-meta-val job-status-indicator ${job.status}`;
    statusBadge.innerText = (job.status || "discovered").replace('_', ' ');
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
    card.className = "outreach-card premium-glass-card";

    const score = draft.confidence || 0;
    const confClass = score > 0.7 ? "conf-high" : score > 0.4 ? "conf-med" : "conf-low";
    
    const initial = draft.company ? draft.company.trim().charAt(0).toUpperCase() : '?';
    const bestEmail = draft.email_guesses && draft.email_guesses.length > 0 ? draft.email_guesses[0].address : "No email guessed";
    const emailStatusLabel = draft.email_guesses && draft.email_guesses.length > 0 && draft.email_guesses[0].mx_valid ? "MX Verified" : "MX Checked";
    const emailStatusClass = draft.email_guesses && draft.email_guesses.length > 0 && draft.email_guesses[0].mx_valid ? "email-verified" : "email-unverified";

    card.innerHTML = `
      <div class="outreach-card-header">
        <div class="company-avatar">${initial}</div>
        <div class="company-info-block">
          <div class="company-title">${escapeHtml(draft.company)}</div>
          <div class="role-title">${escapeHtml(draft.contact_name)}</div>
          <div class="contact-role-badge">${escapeHtml(draft.contact_role)}</div>
        </div>
      </div>
      
      <div class="outreach-details-body">
        <div class="detail-row">
          <span class="detail-label">Recipient:</span>
          <span class="detail-value ${emailStatusClass}">${escapeHtml(bestEmail)}</span>
        </div>
        ${draft.subject ? `
        <div class="detail-row">
          <span class="detail-label">Subject:</span>
          <span class="detail-value subject-value">${escapeHtml(draft.subject)}</span>
        </div>` : ''}
      </div>

      <div class="badge-row">
        <span class="conf-badge ${confClass}">Confidence: ${(score * 100).toFixed(0)}%</span>
        <span class="conf-badge mx-badge ${emailStatusClass}">${emailStatusLabel}</span>
      </div>

      <div class="card-footer">
        <span class="outreach-status-badge ${draft.status}">${escapeHtml(draft.status)}</span>
        <button class="card-action-btn premium-btn" onclick="openOutreachComposer('${draft.id}')">
          <span>Compose & Send</span>
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
        </button>
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
    
    dotEl.className = "status-dot";
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
    miniLogsEl.innerHTML = `<div class="mini-log-item"><span class="log-time">00:00:00</span> <span class="log-agent-tag system">SYSTEM</span> Ready.</div>`;
  }
}

// ---------------------------------------------------------------------------
// HITL Interaction Overlay
// ---------------------------------------------------------------------------
function showHitlModal(jobId, type, message, url) {
  hitlActiveJobId = jobId;
  document.getElementById("hitl-message").innerText = message;
  
  const hitlUrlEl = document.getElementById("hitl-url");
  if (hitlUrlEl) hitlUrlEl.href = url || "#";

  const hitlTabBtn = document.getElementById("hitl-open-tab-btn");
  if (hitlTabBtn) hitlTabBtn.href = url || "#";
  
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
    showHitlModal(job.id, "manual_form", "Needs attention — please verify details or complete form steps manually.", job.apply_url || job.career_page_url);
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
    const style = guess.mx_valid === false ? "color: var(--error-color)" : "color: var(--success-color)";
    
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

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}

// Minimal job state filter
function filterJobs(status) {
  document.querySelectorAll(".filter-pill").forEach(btn => btn.classList.remove("active"));
  if (window.event && window.event.target) window.event.target.classList.add("active");

  const cards = document.querySelectorAll("#jobs-container .job-card");
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
    suggested_role: document.getElementById("prof-suggested-role") ? document.getElementById("prof-suggested-role").value.trim() : (currentProfile.suggested_role || ""),
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
      alert("Profile changes saved successfully!");
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
