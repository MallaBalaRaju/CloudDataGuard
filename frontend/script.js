// ========================================
// CloudDataGuard - Frontend JavaScript
// ========================================

const API_BASE_URL = "http://127.0.0.1:8000";


// ========================================
// Page Initialization
// ========================================

document.addEventListener("DOMContentLoaded", () => {
    checkDatabaseStatus();
    loadDashboard();

    const form = document.getElementById("recordForm");
    if (form) {
        form.addEventListener("submit", addRecord);
    }

    const editForm = document.getElementById("editForm");
    if (editForm) {
        editForm.addEventListener("submit", submitEditRecord);
    }

    // Close modal when clicking the backdrop
    const modalOverlay = document.getElementById("editModal");
    if (modalOverlay) {
        modalOverlay.addEventListener("click", (e) => {
            if (e.target === modalOverlay) {
                closeEditModal();
            }
        });
    }

    // Close modal with Escape key
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            closeEditModal();
        }
    });
});


// ========================================
// Check MongoDB Connection
// ========================================

async function checkDatabaseStatus() {

    const statusElement = document.getElementById("databaseStatus");

    try {

        const response = await fetch(
            `${API_BASE_URL}/database-status`
        );

        const result = await response.json();

        if (result.status === "connected") {

            statusElement.textContent = "● MongoDB Connected";
            statusElement.className = "status connected";

        } else {

            statusElement.textContent = "● Database Disconnected";
            statusElement.className = "status disconnected";
        }

    } catch (error) {

        statusElement.textContent = "● API Offline";
        statusElement.className = "status disconnected";

        console.error("Database status error:", error);
    }
}


// ========================================
// Load Dashboard
// ========================================

async function loadDashboard() {

    await checkDatabaseStatus();
    await loadStatistics();
    await loadRecords();
}


// ========================================
// Load Statistics
// ========================================

async function loadStatistics() {

    try {

        const response = await fetch(
            `${API_BASE_URL}/records/stats`
        );

        if (!response.ok) {
            throw new Error("Failed to load statistics");
        }

        const stats = await response.json();

        document.getElementById("totalRecords").textContent =
            stats.total_records;

        document.getElementById("verifiedRecords").textContent =
            stats.verified_records;

        document.getElementById("duplicateRecords").textContent =
            stats.duplicates_detected;

    } catch (error) {

        console.error("Statistics error:", error);
    }
}


// ========================================
// Load Records  (Read All)
// ========================================

async function loadRecords() {

    const tableBody =
        document.getElementById("recordsTableBody");

    try {

        const response = await fetch(
            `${API_BASE_URL}/records/`
        );

        if (!response.ok) {
            throw new Error("Failed to load records");
        }

        const result = await response.json();

        tableBody.innerHTML = "";

        if (result.records.length === 0) {

            tableBody.innerHTML = `
                <tr>
                    <td colspan="8" class="empty">
                        No records found.
                    </td>
                </tr>
            `;

            return;
        }

        result.records.forEach(record => {

            const row = document.createElement("tr");

            row.innerHTML = `
                <td>${escapeHTML(record.name)}</td>
                <td>${escapeHTML(record.email)}</td>
                <td>${escapeHTML(record.phone)}</td>
                <td>${escapeHTML(record.category)}</td>
                <td>${escapeHTML(record.data)}</td>

                <td>
                    <span class="status-badge">
                        ${escapeHTML(record.status)}
                    </span>
                </td>

                <td>
                    ${formatDate(record.created_at)}
                </td>

                <td>
                    <div class="action-cell">
                        <button
                            class="edit-btn"
                            onclick="openEditModal('${record.id}')"
                        >
                            Edit
                        </button>
                        <button
                            class="delete-btn"
                            onclick="deleteRecord('${record.id}')"
                        >
                            Delete
                        </button>
                    </div>
                </td>
            `;

            tableBody.appendChild(row);
        });

    } catch (error) {

        console.error("Records error:", error);

        tableBody.innerHTML = `
            <tr>
                <td colspan="8" class="empty">
                    Unable to load records.
                </td>
            </tr>
        `;
    }
}


// ========================================
// Add Record  (Create)
// ========================================

async function addRecord(event) {

    event.preventDefault();

    const messageElement =
        document.getElementById("message");

    const submitButton =
        event.target.querySelector("button[type='submit']");

    const record = {

        name: document.getElementById("name").value.trim(),

        email: document.getElementById("email").value.trim(),

        phone: document.getElementById("phone").value.trim(),

        category:
            document.getElementById("category").value.trim(),

        data:
            document.getElementById("data").value.trim()
    };


    submitButton.disabled = true;
    submitButton.textContent = "Checking...";


    try {

        const response = await fetch(
            `${API_BASE_URL}/records/add`,
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify(record)
            }
        );


        const result = await response.json();


        // -----------------------------
        // Successful or duplicate result
        // -----------------------------

        if (response.ok) {

            if (result.status === "success") {

                showMessage(
                    result.message,
                    "success"
                );

                event.target.reset();

            } else if (result.status === "rejected") {

                let duplicateMessage =
                    result.message;

                if (
                    result.duplicate_fields &&
                    result.duplicate_fields.length > 0
                ) {

                    duplicateMessage +=
                        " Duplicate field(s): " +
                        result.duplicate_fields.join(", ");
                }

                showMessage(
                    duplicateMessage,
                    "error"
                );
            }

            await loadDashboard();

        } else {

            // FastAPI validation error
            let errorMessage =
                "Unable to add record.";

            if (result.detail) {

                if (Array.isArray(result.detail)) {

                    errorMessage =
                        result.detail
                            .map(error => error.msg)
                            .join(", ");

                } else {

                    errorMessage =
                        result.detail;
                }
            }

            showMessage(
                errorMessage,
                "error"
            );
        }


    } catch (error) {

        console.error("Add record error:", error);

        showMessage(
            "Unable to connect to CloudDataGuard API.",
            "error"
        );

    } finally {

        submitButton.disabled = false;
        submitButton.textContent =
            "Add & Verify Record";
    }
}


// ========================================
// Open Edit Modal  (Read One → pre-fill)
// ========================================

async function openEditModal(recordId) {

    const modal = document.getElementById("editModal");
    const editMessage = document.getElementById("editMessage");

    // Clear previous state
    editMessage.className = "message";
    editMessage.textContent = "";

    try {

        const response = await fetch(
            `${API_BASE_URL}/records/${recordId}`
        );

        if (!response.ok) {
            throw new Error("Failed to fetch record");
        }

        const record = await response.json();

        // Pre-fill the edit form
        document.getElementById("editRecordId").value  = record.id;
        document.getElementById("editName").value      = record.name;
        document.getElementById("editEmail").value     = record.email;
        document.getElementById("editPhone").value     = record.phone;
        document.getElementById("editCategory").value  = record.category;
        document.getElementById("editData").value      = record.data;

        // Show modal
        modal.classList.add("active");
        document.body.style.overflow = "hidden";

        // Focus the first field
        document.getElementById("editName").focus();

    } catch (error) {

        console.error("Open edit modal error:", error);
        showMessage("Unable to load record for editing.", "error");
    }
}


// ========================================
// Close Edit Modal
// ========================================

function closeEditModal() {
    const modal = document.getElementById("editModal");
    modal.classList.remove("active");
    document.body.style.overflow = "";
}


// ========================================
// Submit Edit Record  (Update)
// ========================================

async function submitEditRecord(event) {

    event.preventDefault();

    const recordId =
        document.getElementById("editRecordId").value;

    const editMessage =
        document.getElementById("editMessage");

    const submitButton =
        document.getElementById("editSubmitBtn");

    const updates = {
        name:     document.getElementById("editName").value.trim(),
        email:    document.getElementById("editEmail").value.trim(),
        phone:    document.getElementById("editPhone").value.trim(),
        category: document.getElementById("editCategory").value.trim(),
        data:     document.getElementById("editData").value.trim()
    };

    submitButton.disabled = true;
    submitButton.textContent = "Saving...";

    try {

        const response = await fetch(
            `${API_BASE_URL}/records/${recordId}`,
            {
                method: "PUT",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify(updates)
            }
        );

        const result = await response.json();

        if (response.ok) {

            if (result.status === "success") {

                closeEditModal();
                showMessage(result.message, "success");
                await loadDashboard();

            } else if (result.status === "rejected") {

                let msg = result.message;

                if (
                    result.duplicate_fields &&
                    result.duplicate_fields.length > 0
                ) {
                    msg += " Duplicate field(s): " +
                        result.duplicate_fields.join(", ");
                }

                showEditMessage(msg, "error");
            }

        } else {

            let errorMessage = "Unable to update record.";

            if (result.detail) {

                if (Array.isArray(result.detail)) {
                    errorMessage =
                        result.detail
                            .map(e => e.msg)
                            .join(", ");
                } else {
                    errorMessage = result.detail;
                }
            }

            showEditMessage(errorMessage, "error");
        }

    } catch (error) {

        console.error("Update record error:", error);
        showEditMessage(
            "Unable to connect to CloudDataGuard API.",
            "error"
        );

    } finally {

        submitButton.disabled = false;
        submitButton.textContent = "Save Changes";
    }
}


// ========================================
// Delete Record  (Delete)
// ========================================

async function deleteRecord(recordId) {

    const confirmed =
        confirm(
            "Are you sure you want to delete this record?"
        );

    if (!confirmed) {
        return;
    }


    try {

        const response = await fetch(
            `${API_BASE_URL}/records/${recordId}`,
            {
                method: "DELETE"
            }
        );


        const result = await response.json();


        if (response.ok) {

            showMessage(
                result.message,
                "success"
            );

            await loadDashboard();

        } else {

            showMessage(
                result.detail || "Unable to delete record.",
                "error"
            );
        }


    } catch (error) {

        console.error("Delete error:", error);

        showMessage(
            "Unable to connect to CloudDataGuard API.",
            "error"
        );
    }
}


// ========================================
// Display Message (main form area)
// ========================================

function showMessage(message, type) {

    const messageElement =
        document.getElementById("message");

    messageElement.textContent = message;

    messageElement.className =
        `message ${type}`;


    setTimeout(() => {

        messageElement.className =
            "message";

        messageElement.textContent = "";

    }, 5000);
}


// ========================================
// Display Message (inside edit modal)
// ========================================

function showEditMessage(message, type) {

    const messageElement =
        document.getElementById("editMessage");

    messageElement.textContent = message;
    messageElement.className = `message ${type}`;

    setTimeout(() => {
        messageElement.className = "message";
        messageElement.textContent = "";
    }, 5000);
}


// ========================================
// Format Date
// ========================================

function formatDate(dateString) {

    if (!dateString) {
        return "-";
    }

    const date = new Date(dateString);

    return date.toLocaleString();
}


// ========================================
// HTML Security
// ========================================

function escapeHTML(value) {

    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
