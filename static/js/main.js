/* ═══════════════════════════════════════════
   SwimRank – Main JavaScript
═══════════════════════════════════════════ */

// ── Sidebar (mobile) ────────────────────────────────────────────────
const sidebar  = document.getElementById("sidebar");
const overlay  = document.getElementById("sidebar-overlay");
const hamburger = document.getElementById("hamburger");

hamburger?.addEventListener("click", () => {
    sidebar.classList.toggle("open");
    overlay.classList.toggle("active");
});
overlay?.addEventListener("click", () => {
    sidebar.classList.remove("open");
    overlay.classList.remove("active");
});
// Close sidebar on nav link click (mobile)
sidebar?.querySelectorAll(".nav-link").forEach(link => {
    link.addEventListener("click", () => {
        sidebar.classList.remove("open");
        overlay.classList.remove("active");
    });
});

// ── Tabs (Cadastros) ─────────────────────────────────────────────────
function switchTab(tabId, btn) {
    document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.getElementById("pane-" + tabId)?.classList.add("active");
    btn.classList.add("active");
}

// ── Event Accordion (Dashboard) ──────────────────────────────────────
function togglePanel(panelId) {
    document.getElementById(panelId)?.classList.toggle("open");
}

function expandAllPanels() {
    document.querySelectorAll(".event-panel").forEach(p => p.classList.add("open"));
}

function collapseAllPanels() {
    document.querySelectorAll(".event-panel").forEach(p => p.classList.remove("open"));
}

document.addEventListener("DOMContentLoaded", () => {
    const firstPanel = document.querySelector(".event-panel");
    firstPanel?.classList.add("open");
});

// ── Drag & Drop Upload ───────────────────────────────────────────────
const dropZone  = document.getElementById("drop-zone");
const fileInput = document.getElementById("file-input");
const filePreview = document.getElementById("file-preview");
const fileName  = document.getElementById("file-name");
const uploadBtn = document.getElementById("upload-btn");
const dropIcon  = document.getElementById("drop-icon");
const dropTitle = document.getElementById("drop-title");

function onFileSelected(file) {
    if (!file) return;
    fileName.textContent = file.name;
    filePreview.style.display = "inline-flex";
    uploadBtn.style.display = "block";
    dropIcon.textContent = "✅";
    dropTitle.textContent = "Arquivo pronto para envio";
}

fileInput?.addEventListener("change", () => { onFileSelected(fileInput.files[0]); });

dropZone?.addEventListener("dragover", (e) => { e.preventDefault(); dropZone.classList.add("drag-over"); });
dropZone?.addEventListener("dragleave", () => { dropZone.classList.remove("drag-over"); });
dropZone?.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
    const file = e.dataTransfer.files[0];
    if (file) {
        const dt = new DataTransfer();
        dt.items.add(file);
        fileInput.files = dt.files;
        onFileSelected(file);
    }
});

// ── Upload form loading state ─────────────────────────────────────────
document.getElementById("upload-form")?.addEventListener("submit", () => {
    if (uploadBtn) {
        uploadBtn.disabled = true;
        uploadBtn.innerHTML = "⏳ Processando…";
    }
    const progress = document.getElementById("upload-progress");
    if (progress) progress.style.display = "block";
});

// ── Flash auto-dismiss ───────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".flash").forEach((f) => {
        const delay = f.classList.contains("flash-error") ? 10000 : 5000;
        setTimeout(() => {
            f.style.opacity = "0";
            f.style.transform = "translateY(-8px)";
            f.style.transition = "all 0.4s ease";
            setTimeout(() => f?.remove(), 400);
        }, delay);
    });
});

/* ═══════════════════════════════════════════
   TOAST NOTIFICATIONS
═══════════════════════════════════════════ */
let _toastContainer = null;

function showToast(message, type = "info") {
    if (!_toastContainer) {
        _toastContainer = document.createElement("div");
        _toastContainer.className = "toast-container";
        document.body.appendChild(_toastContainer);
    }

    const icons = { success: "✅", error: "❌", warning: "⚠️", info: "ℹ️" };
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<span>${icons[type] || "ℹ️"}</span><span>${message}</span>`;
    _toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateY(12px) scale(0.96)";
        toast.style.transition = "all 0.35s ease";
        setTimeout(() => toast.remove(), 350);
    }, 3500);
}

/* ═══════════════════════════════════════════
   CONFIRM MODAL (replaces browser confirm())
═══════════════════════════════════════════ */
let _modalResolve = null;

function _ensureModal() {
    if (document.getElementById("confirm-modal")) return;

    const overlay = document.createElement("div");
    overlay.className = "modal-overlay";
    overlay.id = "confirm-modal";
    overlay.innerHTML = `
        <div class="modal-box" role="dialog" aria-modal="true" aria-labelledby="modal-title">
            <span class="modal-icon" id="modal-icon">⚠️</span>
            <div class="modal-title" id="modal-title">Confirmar</div>
            <div class="modal-body" id="modal-body"></div>
            <div class="modal-actions">
                <button class="btn btn-ghost" id="modal-cancel">Cancelar</button>
                <button class="btn btn-danger" id="modal-confirm">Remover</button>
            </div>
        </div>`;
    document.body.appendChild(overlay);

    document.getElementById("modal-cancel").addEventListener("click", () => _resolveModal(false));
    document.getElementById("modal-confirm").addEventListener("click", () => _resolveModal(true));
    overlay.addEventListener("click", (e) => { if (e.target === overlay) _resolveModal(false); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") _resolveModal(false); });
}

function _resolveModal(value) {
    const overlay = document.getElementById("confirm-modal");
    if (overlay) overlay.classList.remove("active");
    if (_modalResolve) { _modalResolve(value); _modalResolve = null; }
}

function showConfirm(title, body, confirmLabel = "Remover", icon = "🗑️") {
    _ensureModal();
    document.getElementById("modal-icon").textContent = icon;
    document.getElementById("modal-title").textContent = title;
    document.getElementById("modal-body").innerHTML = body;
    document.getElementById("modal-confirm").textContent = confirmLabel;
    document.getElementById("confirm-modal").classList.add("active");
    return new Promise(resolve => { _modalResolve = resolve; });
}

/* ═══════════════════════════════════════════
   DELETE RECORD (fetch DELETE with modal)
═══════════════════════════════════════════ */
async function confirmDelete(url, rowId, label) {
    const confirmed = await showConfirm(
        "Confirmar remoção",
        `Deseja remover <strong>${label}</strong>? Esta ação não pode ser desfeita.`,
        "Remover",
        "🗑️"
    );
    if (!confirmed) return;

    try {
        const res = await fetch(url, { method: "DELETE" });
        if (res.ok) {
            const row = document.getElementById(rowId);
            if (row) {
                row.classList.add("deleting");
                setTimeout(() => {
                    row.remove();
                    // Recalculate visible count
                    const tbody = document.getElementById("students-tbody");
                    if (tbody) {
                        const visible = [...tbody.querySelectorAll("tr")].filter(r => r.style.display !== "none").length;
                        const pill = document.getElementById("students-visible-count");
                        if (pill) pill.textContent = visible;
                    }
                }, 350);
            }
            showToast(`"${label}" removido com sucesso.`, "success");
        } else {
            showToast("Erro ao remover. Tente novamente.", "error");
        }
    } catch {
        showToast("Falha de conexão. Tente novamente.", "error");
    }
}

// Legacy alias (delete without label — not used but kept for safety)
async function deleteRecord(url, rowId, label) {
    return confirmDelete(url, rowId, label);
}
