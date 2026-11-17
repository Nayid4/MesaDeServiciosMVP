/**
 * Diálogo modal accesible (role="dialog", Escape, restauración de foco).
 */
(function (root) {
  let activeOverlay = null;
  let lastFocused = null;

  function closeModal() {
    if (activeOverlay) {
      activeOverlay.remove();
      activeOverlay = null;
    }
    if (typeof document !== "undefined") {
      document.removeEventListener("keydown", onKeyDown);
    }
    if (lastFocused && typeof lastFocused.focus === "function") {
      lastFocused.focus();
      lastFocused = null;
    }
  }

  function onKeyDown(evt) {
    if (evt.key === "Escape") {
      closeModal();
    }
  }

  function openModal({ title = "Confirmación", contentHtml = "", confirmLabel = "Aceptar", onConfirm = null } = {}) {
    if (typeof document === "undefined") return;
    closeModal();
    lastFocused = document.activeElement;
    const esc = root.CasagbiUtils?.escapeHtml || ((s) => String(s ?? ""));

    const overlay = document.createElement("div");
    overlay.className = "fixed inset-0 z-[80] bg-slate-900/50 backdrop-blur-[1px] flex items-center justify-center p-4";
    overlay.innerHTML = `
      <div role="dialog" aria-modal="true" aria-labelledby="casagbi-modal-title" class="bg-white rounded-2xl border border-slate-200 max-w-md w-full p-5 shadow-2xl space-y-4">
        <div class="flex items-center justify-between gap-2">
          <h3 id="casagbi-modal-title" class="text-sm font-bold text-slate-900">${esc(title)}</h3>
          <button type="button" data-modal-close aria-label="Cerrar diálogo" class="p-1 rounded-lg text-slate-500 hover:bg-slate-100 cursor-pointer">
            ${root.CasagbiIcons ? root.CasagbiIcons.svg("close", "w-4 h-4") : "Cerrar"}
          </button>
        </div>
        <div class="text-xs text-slate-700 leading-relaxed">${contentHtml}</div>
        <div class="flex justify-end gap-2 pt-2">
          <button type="button" data-modal-close class="px-3.5 py-2 rounded-xl border border-slate-300 text-xs font-semibold text-slate-700 hover:bg-slate-100 cursor-pointer">Cancelar</button>
          <button type="button" data-modal-confirm class="px-4 py-2 rounded-xl bg-[#006837] hover:bg-[#004d28] text-white text-xs font-semibold cursor-pointer">${esc(confirmLabel)}</button>
        </div>
      </div>
    `;
    overlay.querySelectorAll("[data-modal-close]").forEach((btn) => {
      btn.addEventListener("click", closeModal);
    });
    overlay.querySelector("[data-modal-confirm]")?.addEventListener("click", async () => {
      try {
        if (typeof onConfirm === "function") await onConfirm();
      } finally {
        closeModal();
      }
    });
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) closeModal();
    });
    document.body.appendChild(overlay);
    activeOverlay = overlay;
    document.addEventListener("keydown", onKeyDown);
    overlay.querySelector("[data-modal-confirm]")?.focus();
  }

  const api = { openModal, closeModal };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CasagbiModal = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
