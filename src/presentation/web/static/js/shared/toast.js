/**
 * Notificaciones Toast accesibles (role=status / aria-live=polite).
 */
(function (root) {
  function show(message, kind = "info", title = "") {
    if (typeof document === "undefined") return;
    const host = document.getElementById("casagbi-toast-container");
    if (!host) return;
    const esc = root.CasagbiUtils?.escapeHtml || ((s) => String(s ?? ""));
    const colors = {
      success: "border-emerald-300 bg-emerald-50 text-emerald-950",
      error: "border-red-300 bg-red-50 text-red-950",
      warning: "border-amber-300 bg-amber-50 text-amber-950",
      info: "border-slate-200 bg-white text-slate-900",
    };
    const card = document.createElement("div");
    card.setAttribute("role", kind === "error" ? "alert" : "status");
    card.setAttribute("aria-live", kind === "error" ? "assertive" : "polite");
    card.className = `pointer-events-auto border rounded-xl p-3.5 shadow-lg text-xs leading-relaxed transition-all duration-200 ${colors[kind] || colors.info}`;
    card.innerHTML = `
      ${title ? `<p class="font-semibold mb-0.5">${esc(title)}</p>` : ""}
      <p>${esc(message)}</p>
    `;
    host.appendChild(card);
    setTimeout(() => {
      card.classList.add("opacity-0", "translate-x-2");
      setTimeout(() => card.remove(), 220);
    }, 4500);
  }

  const api = { show };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CasagbiToast = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
