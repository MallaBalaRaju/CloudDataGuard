// =========================================================================
// CloudDataGuard — Frontend JavaScript
// System: Intelligent NoSQL Data Redundancy Removal System
// Architecture: Full CRUD, MongoDB Aggregation, Indexes, explain() Runner
// =========================================================================

// Dynamically determine backend API base
const API = (window.location.origin && window.location.origin.startsWith("http"))
    ? window.location.origin
    : "http://127.0.0.1:8000";

// State
let currentPage     = 1;
let currentSearch   = "";
let currentCategory = "";
let pendingDeleteId = null;


// ═════════════════════════════════════════════════════════════════════════
// INITIALIZATION
// ═════════════════════════════════════════════════════════════════════════

document.addEventListener("DOMContentLoaded", () => {
    checkDatabaseStatus();
    loadDashboard();

    // Forms
    const recordForm = document.getElementById("recordForm");
    if (recordForm) recordForm.addEventListener("submit", addRecord);

    const editForm = document.getElementById("editForm");
    if (editForm) editForm.addEventListener("submit", submitEditRecord);

    // Search enter keys
    const searchInput = document.getElementById("searchInput");
    if (searchInput) {
        searchInput.addEventListener("keydown", e => { if (e.key === "Enter") applySearch(); });
    }
    const filterCat = document.getElementById("filterCategory");
    if (filterCat) {
        filterCat.addEventListener("keydown", e => { if (e.key === "Enter") applySearch(); });
    }

    // Modal backdrops & escape
    ["editModal", "viewModal", "deleteModal"].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener("click", e => {
                if (e.target.id === id) closeAllModals();
            });
        }
    });

    document.addEventListener("keydown", e => {
        if (e.key === "Escape") closeAllModals();
    });

    suggestExplainValue();
});


// ═════════════════════════════════════════════════════════════════════════
// 1. DATABASE CONNECTIVITY
// ═════════════════════════════════════════════════════════════════════════

async function checkDatabaseStatus() {
    const el = document.getElementById("databaseStatus");
    try {
        const res = await fetch(`${API}/database-status`);
        const result = await res.json();
        if (result.status === "connected") {
            el.textContent = "● MongoDB Connected";
            el.className   = "status connected";
        } else {
            el.textContent = "● Database Disconnected";
            el.className   = "status disconnected";
        }
    } catch {
        el.textContent = "● API Offline";
        el.className   = "status disconnected";
    }
}


// ═════════════════════════════════════════════════════════════════════════
// 2. DASHBOARD ORCHESTRATION
// ═════════════════════════════════════════════════════════════════════════

async function loadDashboard() {
    await checkDatabaseStatus();
    await loadStatistics();
    await loadRecords();
    loadIndexes();
    loadDuplicateLogs();
}


// ═════════════════════════════════════════════════════════════════════════
// 3. AGGREGATION STATISTICS (Total, Verified, Duplicates, Bytes, Ratio)
// ═════════════════════════════════════════════════════════════════════════

async function loadStatistics() {
    try {
        const res = await fetch(`${API}/records/stats`);
        if (!res.ok) return;
        const stats = await res.json();

        // Cards
        document.getElementById("totalRecords").textContent     = stats.total_records.toLocaleString();
        document.getElementById("verifiedRecords").textContent  = stats.verified_records.toLocaleString();
        document.getElementById("duplicateRecords").textContent = stats.duplicates_detected.toLocaleString();

        const sm = stats.storage_metrics || {};
        document.getElementById("storedDataSize").textContent   = formatBytes(sm.total_stored_bytes || 0);
        document.getElementById("savedDataSize").textContent    = formatBytes(sm.total_redundant_bytes_saved || 0);
        document.getElementById("dedupRatio").textContent       = `${sm.deduplication_ratio_percent || 0}%`;

        // Render category aggregation table
        renderCategoryTable(stats.categories || []);

    } catch (err) {
        console.error("Stats load error:", err);
    }
}

function renderCategoryTable(categories) {
    const tbody = document.getElementById("categoryTableBody");
    if (!tbody) return;

    if (categories.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="empty">No category data available yet.</td></tr>`;
        return;
    }

    tbody.innerHTML = categories.map(cat => `
        <tr>
            <td><strong>${esc(cat.category)}</strong></td>
            <td><span class="count-badge">${cat.count} docs</span></td>
            <td>${formatBytes(cat.total_bytes)}</td>
            <td>${cat.avg_bytes} bytes</td>
            <td>${cat.latest_record ? fmtDate(cat.latest_record) : "—"}</td>
        </tr>
    `).join("");
}


// ═════════════════════════════════════════════════════════════════════════
// 4. READ ALL (Records Table with Search, Filter & Pagination)
// ═════════════════════════════════════════════════════════════════════════

async function loadRecords() {
    const tbody = document.getElementById("recordsTableBody");
    tbody.innerHTML = `<tr><td colspan="11" class="empty"><span class="spinner"></span> Loading MongoDB records…</td></tr>`;

    const params = new URLSearchParams({
        page:  currentPage,
        limit: 15,
    });
    if (currentSearch)   params.set("search",   currentSearch);
    if (currentCategory) params.set("category", currentCategory);

    try {
        const res    = await fetch(`${API}/records/?${params}`);
        if (!res.ok) throw new Error("Failed to load records");
        const result = await res.json();

        tbody.innerHTML = "";

        if (result.records.length === 0) {
            tbody.innerHTML = `<tr><td colspan="11" class="empty">No records found matching query.</td></tr>`;
            renderPagination(0, 1, 1);
            return;
        }

        const offset = (currentPage - 1) * 15;
        result.records.forEach((record, i) => {
            const shortHash = record.content_hash ? record.content_hash.substring(0, 8) + "…" : "—";
            const row = document.createElement("tr");
            row.innerHTML = `
                <td>${offset + i + 1}</td>
                <td><strong>${esc(record.name)}</strong></td>
                <td>${esc(record.email)}</td>
                <td>${esc(record.phone)}</td>
                <td><span class="category-badge">${esc(record.category)}</span></td>
                <td class="data-cell" title="${esc(record.data)}">${esc(record.data)}</td>
                <td><code class="hash-badge" title="Full SHA-256: ${esc(record.content_hash)}">${shortHash}</code></td>
                <td>${record.size_bytes || 0} B</td>
                <td><span class="status-badge">${esc(record.status)}</span></td>
                <td>${fmtDate(record.created_at)}</td>
                <td>
                    <div class="action-cell">
                        <button class="view-btn"   onclick="openViewModal('${record.id}')" title="Read Single Document">View</button>
                        <button class="edit-btn"   onclick="openEditModal('${record.id}')" title="Update Document">Edit</button>
                        <button class="delete-btn" onclick="openDeleteModal('${record.id}')" title="Delete Document">Delete</button>
                    </div>
                </td>
            `;
            tbody.appendChild(row);
        });

        renderPagination(result.total, result.page, result.pages);

    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="11" class="empty">Unable to load records from MongoDB.</td></tr>`;
        console.error(err);
    }
}

function renderPagination(total, page, pages) {
    const el = document.getElementById("pagination");
    if (!el) return;
    if (pages <= 1) { el.innerHTML = ""; return; }

    let html = `<span class="page-info">Page ${page} of ${pages} &nbsp;&bull;&nbsp; ${total} records</span>`;
    if (page > 1)     html += `<button class="secondary-btn page-btn" onclick="goPage(${page - 1})">‹ Prev</button>`;
    if (page < pages) html += `<button class="secondary-btn page-btn" onclick="goPage(${page + 1})">Next ›</button>`;
    el.innerHTML = html;
}

function goPage(p) {
    currentPage = p;
    loadRecords();
}

function applySearch() {
    currentSearch   = document.getElementById("searchInput").value.trim();
    currentCategory = document.getElementById("filterCategory").value.trim();
    currentPage     = 1;
    loadRecords();
}

function clearSearch() {
    document.getElementById("searchInput").value    = "";
    document.getElementById("filterCategory").value = "";
    currentSearch   = "";
    currentCategory = "";
    currentPage     = 1;
    loadRecords();
}


// ═════════════════════════════════════════════════════════════════════════
// 5. CREATE (Add & Verify Record with SHA-256 Hashing)
// ═════════════════════════════════════════════════════════════════════════

async function addRecord(event) {
    event.preventDefault();

    const btn = document.getElementById("addSubmitBtn");
    const payload = {
        name:     document.getElementById("name").value.trim(),
        email:    document.getElementById("email").value.trim(),
        phone:    document.getElementById("phone").value.trim(),
        category: document.getElementById("category").value.trim(),
        data:     document.getElementById("data").value.trim(),
    };

    btn.disabled    = true;
    btn.textContent = "Verifying & Hashing…";

    try {
        const res = await fetch(`${API}/records/add`, {
            method:  "POST",
            headers: { "Content-Type": "application/json" },
            body:    JSON.stringify(payload),
        });
        const result = await res.json();

        if (res.ok) {
            if (result.status === "success") {
                toast(`Unique record stored! SHA-256: ${result.content_hash.substring(0, 10)}… (${result.size_bytes} bytes)`, "success");
                event.target.reset();
            } else if (result.status === "rejected") {
                let msg = result.message;
                if (result.duplicate_fields?.length) {
                    msg += " Redundant field(s): " + result.duplicate_fields.join(", ");
                }
                if (result.bytes_saved) {
                    msg += ` [Prevented ${result.bytes_saved} bytes of duplicate cloud storage]`;
                }
                toast(msg, "error");
            }
        } else {
            toast(extractError(result), "error");
        }

        await loadDashboard();

    } catch {
        toast("Unable to connect to CloudDataGuard API.", "error");
    } finally {
        btn.disabled    = false;
        btn.textContent = "✔ Submit & Verify Record (Create)";
    }
}


// ═════════════════════════════════════════════════════════════════════════
// 6. READ ONE (View Document Modal with BSON Details)
// ═════════════════════════════════════════════════════════════════════════

async function openViewModal(id) {
    const modal = document.getElementById("viewModal");
    const body  = document.getElementById("viewModalBody");
    body.innerHTML = `<p class="loading-text"><span class="spinner"></span> Loading document from MongoDB…</p>`;
    modal.classList.add("active");
    document.body.style.overflow = "hidden";

    try {
        const res = await fetch(`${API}/records/${id}`);
        if (!res.ok) throw new Error("Document not found");
        const r = await res.json();

        body.innerHTML = `
            <div class="view-grid">
                <div class="view-field">
                    <span class="view-label">MongoDB _id (BSON ObjectId)</span>
                    <code>${esc(r.id)}</code>
                </div>
                <div class="view-field">
                    <span class="view-label">Full Name</span>
                    <strong>${esc(r.name)}</strong>
                </div>
                <div class="view-field">
                    <span class="view-label">Email Address (Unique Index)</span>
                    <span>${esc(r.email)}</span>
                </div>
                <div class="view-field">
                    <span class="view-label">Phone Number (Unique Index)</span>
                    <span>${esc(r.phone)}</span>
                </div>
                <div class="view-field">
                    <span class="view-label">Category (Indexed)</span>
                    <span class="category-badge">${esc(r.category)}</span>
                </div>
                <div class="view-field">
                    <span class="view-label">Status</span>
                    <span class="status-badge">${esc(r.status)}</span>
                </div>
                <div class="view-field full-width">
                    <span class="view-label">SHA-256 Content Hash (Cryptographic Redundancy Key)</span>
                    <code class="hash-full">${esc(r.content_hash || "—")}</code>
                </div>
                <div class="view-field">
                    <span class="view-label">Data Size</span>
                    <span>${r.size_bytes || 0} bytes</span>
                </div>
                <div class="view-field">
                    <span class="view-label">Embedded Metadata (BSON Subdocument)</span>
                    <code>${esc(JSON.stringify(r.metadata || {}))}</code>
                </div>
                <div class="view-field">
                    <span class="view-label">Created At (BSON ISODate)</span>
                    <span>${fmtDate(r.created_at)}</span>
                </div>
                <div class="view-field">
                    <span class="view-label">Updated At</span>
                    <span>${r.updated_at ? fmtDate(r.updated_at) : "— (Never modified)"}</span>
                </div>
                <div class="view-field full-width">
                    <span class="view-label">Stored Data Content / Payload</span>
                    <pre class="data-preview-box">${esc(r.data)}</pre>
                </div>
            </div>
        `;
    } catch {
        body.innerHTML = `<p style="color:#b91c1c;padding:20px;">Failed to load record details from MongoDB.</p>`;
    }
}

function closeViewModal() {
    document.getElementById("viewModal").classList.remove("active");
    document.body.style.overflow = "";
}


// ═════════════════════════════════════════════════════════════════════════
// 7. UPDATE (Edit Modal & Submission)
// ═════════════════════════════════════════════════════════════════════════

async function openEditModal(id) {
    const modal = document.getElementById("editModal");
    clearEditMessage();

    try {
        const res = await fetch(`${API}/records/${id}`);
        if (!res.ok) throw new Error("Document not found");
        const r = await res.json();

        document.getElementById("editRecordId").value = r.id;
        document.getElementById("editName").value     = r.name;
        document.getElementById("editEmail").value    = r.email;
        document.getElementById("editPhone").value    = r.phone;
        document.getElementById("editCategory").value = r.category;
        document.getElementById("editData").value     = r.data;

        modal.classList.add("active");
        document.body.style.overflow = "hidden";
        document.getElementById("editName").focus();

    } catch {
        toast("Unable to load document for editing.", "error");
    }
}

function closeEditModal() {
    document.getElementById("editModal").classList.remove("active");
    document.body.style.overflow = "";
}

async function submitEditRecord(event) {
    event.preventDefault();

    const id  = document.getElementById("editRecordId").value;
    const btn = document.getElementById("editSubmitBtn");

    const payload = {
        name:     document.getElementById("editName").value.trim(),
        email:    document.getElementById("editEmail").value.trim(),
        phone:    document.getElementById("editPhone").value.trim(),
        category: document.getElementById("editCategory").value.trim(),
        data:     document.getElementById("editData").value.trim(),
    };

    btn.disabled    = true;
    btn.textContent = "Updating in MongoDB…";

    try {
        const res = await fetch(`${API}/records/${id}`, {
            method:  "PUT",
            headers: { "Content-Type": "application/json" },
            body:    JSON.stringify(payload),
        });
        const result = await res.json();

        if (res.ok) {
            if (result.status === "success") {
                closeEditModal();
                toast(result.message, "success");
                await loadDashboard();
            } else if (result.status === "rejected") {
                let msg = result.message;
                if (result.duplicate_fields?.length) {
                    msg += " Duplicate: " + result.duplicate_fields.join(", ");
                }
                showEditMessage(msg, "error");
            }
        } else {
            showEditMessage(extractError(result), "error");
        }

    } catch {
        showEditMessage("Unable to connect to CloudDataGuard API.", "error");
    } finally {
        btn.disabled    = false;
        btn.textContent = "💾 Save Changes (Update)";
    }
}

function showEditMessage(msg, type) {
    const el = document.getElementById("editMessage");
    el.textContent = msg;
    el.className   = `inline-message ${type}`;
}
function clearEditMessage() {
    const el = document.getElementById("editMessage");
    el.textContent = "";
    el.className   = "inline-message";
}


// ═════════════════════════════════════════════════════════════════════════
// 8. DELETE (Confirm Modal & Permanent Deletion)
// ═════════════════════════════════════════════════════════════════════════

function openDeleteModal(id) {
    pendingDeleteId = id;
    document.getElementById("deleteModal").classList.add("active");
    document.body.style.overflow = "hidden";
}

function closeDeleteModal() {
    pendingDeleteId = null;
    document.getElementById("deleteModal").classList.remove("active");
    document.body.style.overflow = "";
}

async function confirmDelete() {
    if (!pendingDeleteId) return;

    const btn = document.getElementById("confirmDeleteBtn");
    btn.disabled    = true;
    btn.textContent = "Deleting…";

    try {
        const res = await fetch(`${API}/records/${pendingDeleteId}`, { method: "DELETE" });
        const result = await res.json();

        closeDeleteModal();

        if (res.ok) {
            toast(result.message, "success");
            await loadDashboard();
        } else {
            toast(result.detail || "Unable to delete record.", "error");
        }

    } catch {
        closeDeleteModal();
        toast("Unable to connect to CloudDataGuard API.", "error");
    } finally {
        btn.disabled    = false;
        btn.textContent = "Permanently Delete";
    }
}

function closeAllModals() {
    closeViewModal();
    closeEditModal();
    closeDeleteModal();
}


// ═════════════════════════════════════════════════════════════════════════
// 9. VIVA & ACADEMIC EVALUATION TOOLS
// ═════════════════════════════════════════════════════════════════════════

function switchTab(tabId) {
    document.querySelectorAll(".tab-pane").forEach(el => el.classList.remove("active"));
    document.querySelectorAll(".tab-btn").forEach(el => el.classList.remove("active"));

    const targetPane = document.getElementById(tabId);
    if (targetPane) targetPane.classList.add("active");

    const activeBtn = Array.from(document.querySelectorAll(".tab-btn")).find(btn =>
        btn.getAttribute("onclick").includes(tabId)
    );
    if (activeBtn) activeBtn.classList.add("active");

    if (tabId === "tabIndexes") loadIndexes();
    if (tabId === "tabDuplicates") loadDuplicateLogs();
}

async function loadIndexes() {
    const container = document.getElementById("indexesContent");
    if (!container) return;

    try {
        const res = await fetch(`${API}/records/indexes`);
        if (!res.ok) return;
        const data = await res.json();

        container.innerHTML = `
            <div class="index-group">
                <h4><code>records</code> Collection Indexes</h4>
                <div class="index-cards">
                    ${data.records_collection_indexes.map(idx => `
                        <div class="index-card">
                            <div class="index-name">${idx.name}</div>
                            <div class="index-keys">Key: <code>${JSON.stringify(idx.key)}</code></div>
                            <div class="index-badge ${idx.unique ? 'unique' : 'standard'}">
                                ${idx.unique ? '★ UNIQUE CONSTRAINT' : 'STANDARD INDEX'}
                            </div>
                        </div>
                    `).join("")}
                </div>
            </div>
            <div class="index-group" style="margin-top:16px;">
                <h4><code>duplicate_logs</code> Collection Indexes</h4>
                <div class="index-cards">
                    ${data.duplicate_logs_indexes.map(idx => `
                        <div class="index-card">
                            <div class="index-name">${idx.name}</div>
                            <div class="index-keys">Key: <code>${JSON.stringify(idx.key)}</code></div>
                            <div class="index-badge standard">STANDARD INDEX</div>
                        </div>
                    `).join("")}
                </div>
            </div>
        `;
    } catch (err) {
        container.innerHTML = `<p class="empty">Unable to inspect indexes.</p>`;
    }
}

async function loadDuplicateLogs() {
    const tbody = document.getElementById("duplicateLogsBody");
    if (!tbody) return;

    try {
        const res = await fetch(`${API}/records/logs/duplicates?limit=10`);
        if (!res.ok) return;
        const data = await res.json();

        if (data.logs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="empty">No duplicate attempts recorded yet. Try submitting identical data!</td></tr>`;
            return;
        }

        tbody.innerHTML = data.logs.map((log, i) => `
            <tr>
                <td>${i + 1}</td>
                <td>${esc(log.email)}</td>
                <td>${esc(log.phone)}</td>
                <td><code class="hash-badge">${log.content_hash ? log.content_hash.substring(0, 8) + '…' : '—'}</code></td>
                <td><span class="dup-field-badge">${esc((log.duplicate_fields || []).join(", "))}</span></td>
                <td><span class="saved-badge">+${log.bytes_saved || 0} bytes</span></td>
                <td>${fmtDate(log.detected_at)}</td>
            </tr>
        `).join("");
    } catch {
        tbody.innerHTML = `<tr><td colspan="7" class="empty">Failed to load audit logs.</td></tr>`;
    }
}

function suggestExplainValue() {
    const field = document.getElementById("explainField").value;
    const input = document.getElementById("explainValue");

    if (field === "email") input.value = "alice@example.com";
    else if (field === "phone") input.value = "9876543210";
    else if (field === "category") input.value = "Student";
    else if (field === "name") input.value = "Alice Smith";
    else if (field === "content_hash") input.value = "ca455d6f99a39a68d68c08b17a2db495f219cb7159cb16a04d6347d8da2539f9";
}

async function runExplain() {
    const field = document.getElementById("explainField").value;
    const value = document.getElementById("explainValue").value.trim();
    const resultBox = document.getElementById("explainResult");

    if (!value) {
        toast("Please enter a value to run explain() on.", "error");
        return;
    }

    resultBox.style.display = "block";
    resultBox.innerHTML = `<span class="spinner"></span> Running MongoDB .explain("executionStats")…`;

    try {
        const res = await fetch(`${API}/records/explain?field=${encodeURIComponent(field)}&value=${encodeURIComponent(value)}`);
        if (!res.ok) throw new Error("Explain query failed");
        const exp = await res.json();

        resultBox.innerHTML = `
            <div class="explain-summary ${exp.is_index_used ? 'opt-indexed' : 'opt-collscan'}">
                <div class="stage-tag ${exp.is_index_used ? 'stage-ixscan' : 'stage-collscan'}">
                    STAGE: ${esc(exp.execution_stage)}
                </div>
                <h4>${exp.is_index_used ? '⚡ Query Optimized via Index' : '⚠️ Unindexed Full Collection Scan'}</h4>
                <p>${esc(exp.summary)}</p>
            </div>
            <div class="explain-metrics-grid">
                <div class="exp-metric">
                    <span class="exp-label">Index Used</span>
                    <strong>${esc(exp.index_used)}</strong>
                </div>
                <div class="exp-metric">
                    <span class="exp-label">Execution Time</span>
                    <strong>${exp.execution_time_millis} ms</strong>
                </div>
                <div class="exp-metric">
                    <span class="exp-label">Keys Examined</span>
                    <strong>${exp.total_keys_examined}</strong>
                </div>
                <div class="exp-metric">
                    <span class="exp-label">Docs Examined</span>
                    <strong>${exp.total_docs_examined}</strong>
                </div>
                <div class="exp-metric">
                    <span class="exp-label">Docs Returned</span>
                    <strong>${exp.n_returned}</strong>
                </div>
            </div>
        `;
    } catch (err) {
        resultBox.innerHTML = `<p style="color:#b91c1c;">Explain execution failed. Ensure backend is running.</p>`;
    }
}

function fillSampleData() {
    const demoCategories = ["Computer Science", "Cloud Architecture", "NoSQL Databases", "Cybersecurity", "Data Engineering"];
    const rand = Math.floor(Math.random() * 900) + 100;
    document.getElementById("name").value     = `Student Candidate ${rand}`;
    document.getElementById("email").value    = `candidate.${rand}@university.edu`;
    document.getElementById("phone").value    = `9876543${rand}`;
    document.getElementById("category").value = demoCategories[rand % demoCategories.length];
    document.getElementById("data").value     = `Confidential research paper abstract #${rand}: Distributed transactions and indexing in Intelligent NoSQL databases.`;
    toast("Demo sample data filled into form!", "info");
}


// ═════════════════════════════════════════════════════════════════════════
// 10. NOTIFICATIONS & UTILITIES
// ═════════════════════════════════════════════════════════════════════════

function toast(message, type = "info") {
    const container = document.getElementById("toastContainer");
    if (!container) return;
    const el = document.createElement("div");
    el.className = `toast toast-${type}`;

    const icon = type === "success" ? "✔" : type === "error" ? "🛡" : "ℹ";
    el.innerHTML = `<span>${icon}</span><span>${esc(message)}</span>`;

    container.appendChild(el);
    requestAnimationFrame(() => el.classList.add("show"));

    setTimeout(() => {
        el.classList.remove("show");
        setTimeout(() => el.remove(), 400);
    }, 4500);
}

function esc(value) {
    if (value == null) return "";
    return String(value)
        .replace(/&/g,  "&amp;")
        .replace(/</g,  "&lt;")
        .replace(/>/g,  "&gt;")
        .replace(/"/g,  "&quot;")
        .replace(/'/g,  "&#039;");
}

function fmtDate(dateStr) {
    if (!dateStr) return "—";
    const d = new Date(dateStr);
    return isNaN(d.getTime()) ? dateStr : d.toLocaleString();
}

function formatBytes(bytes) {
    if (bytes == null || isNaN(bytes) || bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

function extractError(result) {
    if (!result.detail) return "An error occurred.";
    if (Array.isArray(result.detail))
        return result.detail.map(e => e.msg).join(", ");
    return result.detail;
}
