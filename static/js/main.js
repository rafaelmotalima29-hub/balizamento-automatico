/* ═══════════════════════════════════════════
   SwimRank – Main JavaScript
═══════════════════════════════════════════ */

// ── Sidebar (mobile) ────────────────────────────────────────────────
const sidebar = document.getElementById("sidebar");
const overlay = document.getElementById("sidebar-overlay");
const hamburger = document.getElementById("hamburger");

hamburger?.addEventListener("click", () => {
    sidebar.classList.toggle("open");
    overlay.classList.toggle("active");
});
overlay?.addEventListener("click", () => {
    sidebar.classList.remove("open");
    overlay.classList.remove("active");
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

// Auto-open first accordion panel on page load
document.addEventListener("DOMContentLoaded", () => {
    const firstPanel = document.querySelector(".event-panel");
    firstPanel?.classList.add("open");
});

// ── Drag & Drop Upload ───────────────────────────────────────────────
const dropZone = document.getElementById("drop-zone");
const fileInput = document.getElementById("file-input");
const filePreview = document.getElementById("file-preview");
const fileName = document.getElementById("file-name");
const uploadBtn = document.getElementById("upload-btn");
const dropIcon = document.getElementById("drop-icon");
const dropTitle = document.getElementById("drop-title");

function onFileSelected(file) {
    if (!file) return;
    fileName.textContent = file.name;
    filePreview.style.display = "inline-flex";
    uploadBtn.style.display = "block";
    dropIcon.textContent = "✅";
    dropTitle.textContent = "Arquivo pronto para envio";
}

fileInput?.addEventListener("change", () => {
    onFileSelected(fileInput.files[0]);
});

dropZone?.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("drag-over");
});
dropZone?.addEventListener("dragleave", () => {
    dropZone.classList.remove("drag-over");
});
dropZone?.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("drag-over");
    const file = e.dataTransfer.files[0];
    if (file) {
        // Assign to input
        const dt = new DataTransfer();
        dt.items.add(file);
        fileInput.files = dt.files;
        onFileSelected(file);
    }
});

// ── Delete record (fetch DELETE) ─────────────────────────────────────
async function deleteRecord(url, rowId, label) {
    if (!confirm(`Remover "${label}"? Esta ação não pode ser desfeita.`)) return;

    try {
        const res = await fetch(url, { method: "DELETE" });
        if (res.ok) {
            const row = document.getElementById(rowId);
            row?.classList.add("deleting");
            setTimeout(() => row?.remove(), 350);
        } else {
            alert("Erro ao remover. Tente novamente.");
        }
    } catch {
        alert("Falha de conexão. Tente novamente.");
    }
}

// ── Upload form loading state ────────────────────────────────────────
const uploadForm = document.getElementById("upload-form");
uploadForm?.addEventListener("submit", () => {
    if (uploadBtn) {
        uploadBtn.disabled = true;
        uploadBtn.textContent = "⏳ Processando…";
    }
});

// ── Flash auto-dismiss ───────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
    const flashes = document.querySelectorAll(".flash");
    flashes.forEach((f) => {
        // Errors stay longer so the user has time to read them
        const delay = f.classList.contains("flash-error") ? 10000 : 5000;
        setTimeout(() => {
            f.style.opacity = "0";
            f.style.transform = "translateY(-8px)";
            f.style.transition = "all 0.4s ease";
            setTimeout(() => f?.remove(), 400);
        }, delay);
    });
});
