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

async function loadReports() {
  reportsList.innerHTML = '<div class="empty-state"><span class="spinner"></span> Loading…</div>';
  try {
    const reports = await apiFetch("/reports");
    if (!reports.length) {
      reportsList.innerHTML = '<div class="empty-state">No reports generated yet.</div>';
      return;
    }
    reportsList.innerHTML = reports.map(r => `
      <div class="report-item">
        <a href="/reports/${encodeURIComponent(r.filename)}" download="${escapeHtml(r.filename)}">
          ${escapeHtml(r.filename)}
        </a>
        <span class="report-size">${fmtSize(r.size)}</span>
      </div>
    `).join("");
  } catch (err) {
    reportsList.innerHTML = `<div class="empty-state">Error: ${escapeHtml(err.message)}</div>`;
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

    const result = await apiFetch("/reports/weekly", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    showStatus(reportStatus,
      `Weekly report generated: <a href="/reports/${encodeURIComponent(result.filename)}" download>${escapeHtml(result.filename)}</a>`,
      "success");
    loadReports();
  } catch (err) {
    showStatus(reportStatus, escapeHtml(err.message), "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Generate Weekly Report";
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
