"use strict";

const API = "";  // same origin

// ── Utilities ──────────────────────────────────────────────────────────────

async function apiFetch(path, options = {}) {
  const res = await fetch(API + path, options);
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try { msg = (await res.json()).detail || msg; } catch (_) {}
    throw new Error(msg);
  }
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res.blob();
}

function showStatus(el, msg, type = "info") {
  el.className = `status-msg show ${type}`;
  el.innerHTML = msg;
}

function clearStatus(el) {
  el.className = "status-msg";
  el.textContent = "";
}

function fmtSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function fmtDate(isoStr) {
  if (!isoStr) return "";
  return new Date(isoStr + "Z").toLocaleString();
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ── Dictation ─────────────────────────────────────────────────────────────

function setupDictation() {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return;

  const recognition = new SR();
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.lang = "en-US";

  let activeTextarea = null;
  let activeBtn = null;
  let recording = false;

  recognition.onresult = e => {
    let finals = "";
    for (let i = e.resultIndex; i < e.results.length; i++) {
      if (e.results[i].isFinal) finals += e.results[i][0].transcript + " ";
    }
    if (finals && activeTextarea) {
      activeTextarea.value += (activeTextarea.value.length ? " " : "") + finals.trim();
    }
  };

  recognition.onend = () => { if (recording) recognition.start(); };

  function stopRecording() {
    recording = false;
    recognition.stop();
    if (activeBtn) activeBtn.classList.remove("recording");
    activeBtn = null;
    activeTextarea = null;
  }

  function toggleMic(btn, textarea) {
    if (recording && activeTextarea === textarea) {
      stopRecording();
    } else {
      if (recording) stopRecording();
      activeTextarea = textarea;
      activeBtn = btn;
      recording = true;
      recognition.start();
      btn.classList.add("recording");
    }
  }

  [["mic-note", "note-content"], ["mic-email", "email-content"]].forEach(([btnId, taId]) => {
    const btn = document.getElementById(btnId);
    btn.innerHTML = SVG_MIC;
    btn.hidden = false;
    btn.addEventListener("click", () => toggleMic(btn, document.getElementById(taId)));
  });
}

// ── AI cleanup ─────────────────────────────────────────────────────────────

function setupCleanup() {
  [["cleanup-note", "note-content"], ["cleanup-email", "email-content"]].forEach(([btnId, taId]) => {
    const btn = document.getElementById(btnId);
    btn.innerHTML = SVG_WAND;
    btn.addEventListener("click", async () => {
      const ta = document.getElementById(taId);
      if (!ta.value.trim()) return;
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner"></span>';
      try {
        const result = await apiFetch("/entries/cleanup", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content: ta.value }),
        });
        ta.value = result.content;
      } catch (err) {
        alert(`Cleanup failed: ${err.message}`);
      } finally {
        btn.disabled = false;
        btn.innerHTML = SVG_WAND;
      }
    });
  });
}

setupDictation();
setupCleanup();

// ── Tab switching ──────────────────────────────────────────────────────────

document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");

    if (btn.dataset.tab === "browse") loadEntries();
    if (btn.dataset.tab === "reports") loadReports();
    if (btn.dataset.tab === "template") checkTemplate();
  });
});

// ── Sub-tab switching ──────────────────────────────────────────────────────

document.querySelectorAll(".sub-tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".sub-tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".sub-panel").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`sub-${btn.dataset.sub}`).classList.add("active");
  });
});

// ── File drop zones ────────────────────────────────────────────────────────

function setupDropZone(zoneId, inputId, labelId) {
  const zone = document.getElementById(zoneId);
  const input = document.getElementById(inputId);
  const label = document.getElementById(labelId);

  const IMAGE_EXTS = new Set([".png", ".jpg", ".jpeg", ".webp", ".gif"]);
  function fileLabel(name) {
    const ext = name.slice(name.lastIndexOf(".")).toLowerCase();
    return IMAGE_EXTS.has(ext) ? `🖼 ${name} — will extract text with AI vision` : name;
  }

  zone.addEventListener("click", () => input.click());
  input.addEventListener("change", () => {
    if (input.files.length) label.textContent = fileLabel(input.files[0].name);
  });

  ["dragenter", "dragover"].forEach(ev => {
    zone.addEventListener(ev, e => { e.preventDefault(); zone.classList.add("drag-over"); });
  });
  ["dragleave", "drop"].forEach(ev => {
    zone.addEventListener(ev, e => { e.preventDefault(); zone.classList.remove("drag-over"); });
  });
  zone.addEventListener("drop", e => {
    const files = e.dataTransfer.files;
    if (files.length) {
      input.files = files;
      label.textContent = fileLabel(files[0].name);
    }
  });
}

setupDropZone("drop-zone", "file-input", "drop-label");
setupDropZone("template-drop-zone", "template-file-input", "template-drop-label");

// ── Note form ──────────────────────────────────────────────────────────────

const addStatus = document.getElementById("add-status");

document.getElementById("form-note").addEventListener("submit", async e => {
  e.preventDefault();
  const content = document.getElementById("note-content").value.trim();
  const tags = document.getElementById("note-tags").value;
  const dateVal = document.getElementById("note-date").value;

  const tagList = tags.split(",").map(t => t.trim()).filter(Boolean);

  try {
    clearStatus(addStatus);
    await apiFetch("/entries", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        content,
        source: "manual",
        type: "text",
        date_stamp: dateVal ? new Date(dateVal).toISOString() : null,
        tags: tagList,
      }),
    });
    showStatus(addStatus, "Note added successfully.", "success");
    document.getElementById("form-note").reset();
  } catch (err) {
    showStatus(addStatus, escapeHtml(err.message), "error");
  }
});

// ── Email form ─────────────────────────────────────────────────────────────

document.getElementById("form-email").addEventListener("submit", async e => {
  e.preventDefault();
  const content = document.getElementById("email-content").value.trim();
  const source = document.getElementById("email-source").value.trim() || "email-paste";
  const tags = document.getElementById("email-tags").value;
  const dateVal = document.getElementById("email-date").value;

  const tagList = tags.split(",").map(t => t.trim()).filter(Boolean);

  try {
    clearStatus(addStatus);
    await apiFetch("/entries", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        content,
        source,
        type: "email",
        date_stamp: dateVal ? new Date(dateVal).toISOString() : null,
        tags: tagList,
      }),
    });
    showStatus(addStatus, "Email entry added successfully.", "success");
    document.getElementById("form-email").reset();
  } catch (err) {
    showStatus(addStatus, escapeHtml(err.message), "error");
  }
});

// ── File upload form ───────────────────────────────────────────────────────

document.getElementById("form-file").addEventListener("submit", async e => {
  e.preventDefault();
  const fileInput = document.getElementById("file-input");
  const tags = document.getElementById("file-tags").value;
  const dateVal = document.getElementById("file-date").value;

  if (!fileInput.files.length) {
    showStatus(addStatus, "Please select a file.", "error");
    return;
  }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);
  if (dateVal) formData.append("date_stamp", new Date(dateVal).toISOString());
  if (tags) formData.append("tags", tags);

  try {
    clearStatus(addStatus);
    const submitBtn = e.target.querySelector("button[type=submit]");
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner"></span>Uploading…';

    await apiFetch("/entries/upload", { method: "POST", body: formData });

    showStatus(addStatus, `File "${fileInput.files[0].name}" uploaded successfully.`, "success");
    document.getElementById("form-file").reset();
    document.getElementById("drop-label").innerHTML = 'Drop a file here or <u>click to browse</u>';
  } catch (err) {
    showStatus(addStatus, escapeHtml(err.message), "error");
  } finally {
    const submitBtn = e.target.querySelector("button[type=submit]");
    submitBtn.disabled = false;
    submitBtn.textContent = "Upload File";
  }
});

// ── Browse / Entries ───────────────────────────────────────────────────────

const entriesList = document.getElementById("entries-list");
const entriesCount = document.getElementById("entries-count");

async function loadEntries() {
  const type = document.getElementById("filter-type").value;
  const start = document.getElementById("filter-start").value;
  const end = document.getElementById("filter-end").value;

  const params = new URLSearchParams();
  if (type) params.set("type", type);
  if (start) params.set("start_date", start);
  if (end) params.set("end_date", end + "T23:59:59");

  entriesList.innerHTML = '<div class="empty-state"><span class="spinner"></span> Loading…</div>';

  try {
    const entries = await apiFetch(`/entries?${params}`);
    renderEntries(entries);
  } catch (err) {
    entriesList.innerHTML = `<div class="empty-state">Error: ${escapeHtml(err.message)}</div>`;
  }
}

function renderEntries(entries) {
  if (!entries.length) {
    entriesCount.textContent = "";
    entriesList.innerHTML = '<div class="empty-state">No entries found.</div>';
    return;
  }
  entriesCount.textContent = `${entries.length} entr${entries.length === 1 ? "y" : "ies"}`;
  entriesList.innerHTML = entries.map(entry => {
    const badgeClass = `badge-${entry.type}`;
    const typeLabel = entry.type === "text" ? "note" : entry.type;
    const tags = (entry.tags || []).map(t => `<span class="tag">${escapeHtml(t)}</span>`).join("");
    const content = escapeHtml(entry.content);
    const needsExpand = entry.content.length > 300;

    return `
      <div class="entry-card" data-id="${entry.id}">
        <div class="entry-card-header">
          <div class="entry-meta">
            <span class="entry-type-badge ${badgeClass}">${typeLabel}</span>
            <span>${fmtDate(entry.date_stamp)}</span>
            <span>— ${escapeHtml(entry.source)}</span>
            ${tags ? `<span class="entry-tags">${tags}</span>` : ""}
          </div>
          <button class="btn-danger" data-delete="${entry.id}">Delete</button>
        </div>
        <div class="entry-content" id="content-${entry.id}">${content}</div>
        ${needsExpand ? `<button class="expand-btn" data-id="${entry.id}">Show more</button>` : ""}
      </div>`;
  }).join("");

  // Delete handlers
  entriesList.querySelectorAll("[data-delete]").forEach(btn => {
    btn.addEventListener("click", async () => {
      if (!confirm("Delete this entry?")) return;
      try {
        await apiFetch(`/entries/${btn.dataset.delete}`, { method: "DELETE" });
        btn.closest(".entry-card").remove();
        const remaining = entriesList.querySelectorAll(".entry-card").length;
        entriesCount.textContent = remaining
          ? `${remaining} entr${remaining === 1 ? "y" : "ies"}`
          : "";
        if (!remaining) entriesList.innerHTML = '<div class="empty-state">No entries found.</div>';
      } catch (err) {
        alert(`Delete failed: ${err.message}`);
      }
    });
  });

  // Expand handlers
  entriesList.querySelectorAll(".expand-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const contentEl = document.getElementById(`content-${btn.dataset.id}`);
      const expanded = contentEl.classList.toggle("expanded");
      btn.textContent = expanded ? "Show less" : "Show more";
    });
  });
}

document.getElementById("btn-refresh").addEventListener("click", loadEntries);
document.getElementById("filter-type").addEventListener("change", loadEntries);
document.getElementById("filter-start").addEventListener("change", loadEntries);
document.getElementById("filter-end").addEventListener("change", loadEntries);

// ── Reports ────────────────────────────────────────────────────────────────

const reportStatus = document.getElementById("report-status");
const reportsList = document.getElementById("reports-list");

// Pre-fill defaults for the monthly fields
const now = new Date();
document.getElementById("monthly-year").value = now.getFullYear();
document.getElementById("monthly-month").value = now.getMonth() + 1;

const SVG_MIC = `<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><rect x="7" y="2" width="6" height="9" rx="3"/><path d="M4 10a6 6 0 0 0 12 0"/><line x1="10" y1="16" x2="10" y2="18"/><line x1="7" y1="18" x2="13" y2="18"/></svg>`;
const SVG_WAND = `<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M3 17L11 9"/><path d="M11 3l1.5 1.5L11 6 9.5 4.5z"/><path d="M14 6l1.5 1.5L14 9l-1.5-1.5z"/><path d="M8 3l.5 1L8 5l-1-.5z"/><path d="M15 11l.5 1-.5 1-1-.5z"/></svg>`;

const SVG_EYE = `<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M1 10s3.5-6 9-6 9 6 9 6-3.5 6-9 6-9-6-9-6z"/><circle cx="10" cy="10" r="2.5"/></svg>`;
const SVG_DOWNLOAD = `<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M10 3v10M6 9l4 4 4-4"/><path d="M3 15h14"/></svg>`;
const SVG_TRASH = `<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6h12M8 6V4h4v2M7 6l1 10h4l1-10"/></svg>`;

async function loadReports() {
  reportsList.innerHTML = '<div class="empty-state"><span class="spinner"></span> Loading…</div>';
  try {
    const reports = await apiFetch("/reports");
    if (!reports.length) {
      reportsList.innerHTML = '<div class="empty-state">No reports generated yet.</div>';
      return;
    }
    reportsList.innerHTML = reports.map(r => `
      <div class="report-item" data-filename="${escapeHtml(r.filename)}">
        <span class="report-name">
          <a href="/reports/${encodeURIComponent(r.filename)}" download="${escapeHtml(r.filename)}">${escapeHtml(r.filename)}</a>
        </span>
        <span class="report-size">${fmtSize(r.size)}</span>
        <span class="report-actions">
          <button class="icon-btn preview" title="Preview" data-action="preview" data-filename="${escapeHtml(r.filename)}">${SVG_EYE}</button>
          <a class="icon-btn download" title="Download" href="/reports/${encodeURIComponent(r.filename)}" download="${escapeHtml(r.filename)}">${SVG_DOWNLOAD}</a>
          <button class="icon-btn delete" title="Delete" data-action="delete" data-filename="${escapeHtml(r.filename)}">${SVG_TRASH}</button>
        </span>
      </div>
    `).join("");
  } catch (err) {
    reportsList.innerHTML = `<div class="empty-state">Error: ${escapeHtml(err.message)}</div>`;
  }
}

reportsList.addEventListener("click", async e => {
  const btn = e.target.closest("[data-action]");
  if (!btn) return;
  const filename = btn.dataset.filename;
  if (btn.dataset.action === "preview") previewReport(filename);
  if (btn.dataset.action === "delete") {
    if (!confirm(`Delete "${filename}"?`)) return;
    try {
      await apiFetch(`/reports/${encodeURIComponent(filename)}`, { method: "DELETE" });
      btn.closest(".report-item").remove();
      if (!reportsList.querySelector(".report-item"))
        reportsList.innerHTML = '<div class="empty-state">No reports generated yet.</div>';
    } catch (err) {
      alert(`Delete failed: ${err.message}`);
    }
  }
});

// ── Preview modal ──────────────────────────────────────────────────────────

const previewModal = document.getElementById("preview-modal");
const previewTitle = document.getElementById("preview-title");
const previewBody  = document.getElementById("preview-body");

function closePreview() { previewModal.hidden = true; previewBody.innerHTML = ""; }

document.getElementById("preview-close").addEventListener("click", closePreview);
previewModal.addEventListener("click", e => { if (e.target === previewModal) closePreview(); });

async function previewReport(filename) {
  const ext = filename.slice(filename.lastIndexOf(".")).toLowerCase();
  previewTitle.textContent = filename;
  previewBody.innerHTML = '<span class="spinner"></span> Loading…';
  previewModal.hidden = false;

  if (ext === ".pdf") {
    previewBody.style.whiteSpace = "normal";
    previewBody.innerHTML = `<iframe src="/reports/${encodeURIComponent(filename)}"></iframe>`;
    return;
  }

  try {
    const res = await fetch(`/reports/${encodeURIComponent(filename)}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    if (ext === ".docx") {
      const arrayBuffer = await res.arrayBuffer();
      const result = await mammoth.convertToHtml({ arrayBuffer });
      previewBody.style.whiteSpace = "normal";
      previewBody.innerHTML = `<div class="docx-preview">${result.value}</div>`;
    } else if (ext === ".html") {
      const text = await res.text();
      previewBody.style.whiteSpace = "normal";
      previewBody.innerHTML = `<iframe srcdoc="${escapeHtml(text)}"></iframe>`;
    } else {
      const text = await res.text();
      previewBody.style.whiteSpace = "";
      previewBody.textContent = text;
    }
  } catch (err) {
    previewBody.innerHTML = `<span class="preview-unavailable">Could not load preview: ${escapeHtml(err.message)}</span>`;
  }
}

document.getElementById("btn-weekly").addEventListener("click", async () => {
  const startVal = document.getElementById("weekly-start").value;
  const endVal = document.getElementById("weekly-end").value;
  const btn = document.getElementById("btn-weekly");

  try {
    clearStatus(reportStatus);
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span>Generating…';

    const body = {};
    if (startVal) body.start_date = new Date(startVal).toISOString();
    if (endVal) body.end_date = new Date(endVal + "T23:59:59").toISOString();

    const result = await apiFetch("/reports/intermediate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    showStatus(reportStatus,
      `Intermediate report generated: <a href="/reports/${encodeURIComponent(result.filename)}" download>${escapeHtml(result.filename)}</a>`,
      "success");
    loadReports();
  } catch (err) {
    showStatus(reportStatus, escapeHtml(err.message), "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Generate Intermediate Report";
  }
});

document.getElementById("btn-monthly").addEventListener("click", async () => {
  const year = parseInt(document.getElementById("monthly-year").value);
  const month = parseInt(document.getElementById("monthly-month").value);
  const btn = document.getElementById("btn-monthly");

  try {
    clearStatus(reportStatus);
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span>Generating…';

    const result = await apiFetch("/reports/monthly", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ year, month }),
    });

    showStatus(reportStatus,
      `Monthly report generated: <a href="/reports/${encodeURIComponent(result.filename)}" download>${escapeHtml(result.filename)}</a>`,
      "success");
    loadReports();
  } catch (err) {
    showStatus(reportStatus, escapeHtml(err.message), "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Generate Monthly Report";
  }
});

// ── Template ───────────────────────────────────────────────────────────────

const templateMsg = document.getElementById("template-msg");
const templateBanner = document.getElementById("template-status-banner");

async function checkTemplate() {
  try {
    const status = await apiFetch("/templates/monthly/status");
    if (status.exists) {
      templateBanner.className = "template-banner show ok";
      templateBanner.textContent = `Template active: ${status.filename}`;
    } else {
      templateBanner.className = "template-banner show missing";
      templateBanner.textContent = "No template uploaded yet. Monthly reports cannot be generated until a template is provided.";
    }
  } catch (_) {
    templateBanner.className = "template-banner show missing";
    templateBanner.textContent = "Could not check template status.";
  }
}

document.getElementById("form-template").addEventListener("submit", async e => {
  e.preventDefault();
  const fileInput = document.getElementById("template-file-input");

  if (!fileInput.files.length) {
    showStatus(templateMsg, "Please select a template file.", "error");
    return;
  }

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);

  try {
    clearStatus(templateMsg);
    await apiFetch("/templates/monthly", { method: "POST", body: formData });
    showStatus(templateMsg, "Template uploaded successfully.", "success");
    document.getElementById("form-template").reset();
    document.getElementById("template-drop-label").innerHTML =
      'Drop a template file here or <u>click to browse</u>';
    checkTemplate();
  } catch (err) {
    showStatus(templateMsg, escapeHtml(err.message), "error");
  }
});

document.getElementById("btn-download-template").addEventListener("click", async () => {
  try {
    const blob = await apiFetch("/templates/monthly");
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "monthly_report_template";
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    alert(`Download failed: ${err.message}`);
  }
});
