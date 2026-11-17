/**
 * Componentes dumb estándar para estados vacío, error con salida clara y sin permisos.
 */
(function (root) {
  function renderEmptyState({ title = "Sin resultados", detail = "No hay elementos para mostrar con los filtros actuales.", actionHtml = "" } = {}) {
    const esc = root.CasagbiUtils?.escapeHtml || ((s) => String(s ?? ""));
    const icon = root.CasagbiIcons ? root.CasagbiIcons.svg("search", "w-6 h-6 text-slate-500") : "";
    return `
      <div class="rounded-2xl border border-slate-200 bg-white p-8 text-center space-y-2.5">
        <div class="w-11 h-11 rounded-full bg-slate-100 mx-auto flex items-center justify-center">${icon}</div>
        <h4 class="text-sm font-bold text-slate-900">${esc(title)}</h4>
        <p class="text-xs text-slate-600 max-w-md mx-auto">${esc(detail)}</p>
        ${actionHtml}
      </div>
    `;
  }

  function renderErrorState({ title = "No fue posible cargar la información", detail = "Verifica tu conexión e intenta nuevamente.", retryAttr = "data-retry-action" } = {}) {
    const esc = root.CasagbiUtils?.escapeHtml || ((s) => String(s ?? ""));
    const icon = root.CasagbiIcons ? root.CasagbiIcons.svg("alert", "w-6 h-6 text-red-700") : "";
    return `
      <div role="alert" class="rounded-2xl border border-red-200 bg-red-50/70 p-6 text-center space-y-2.5">
        <div class="w-11 h-11 rounded-full bg-red-100 mx-auto flex items-center justify-center">${icon}</div>
        <h4 class="text-sm font-bold text-red-900">${esc(title)}</h4>
        <p class="text-xs text-red-800 max-w-md mx-auto">${esc(detail)}</p>
        <button type="button" ${retryAttr} class="px-4 py-2 rounded-xl bg-red-700 hover:bg-red-800 text-white text-xs font-semibold cursor-pointer">
          Reintentar
        </button>
      </div>
    `;
  }

  function renderForbiddenState({ roleLabel = "tu rol actual" } = {}) {
    const esc = root.CasagbiUtils?.escapeHtml || ((s) => String(s ?? ""));
    const icon = root.CasagbiIcons ? root.CasagbiIcons.svg("lock", "w-6 h-6 text-amber-800") : "";
    return `
      <div role="status" class="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-center space-y-2">
        <div class="w-11 h-11 rounded-full bg-amber-100 mx-auto flex items-center justify-center">${icon}</div>
        <h4 class="text-sm font-bold text-amber-950">Acceso restringido por RBAC</h4>
        <p class="text-xs text-amber-900 max-w-md mx-auto">Esta sección no está habilitada para ${esc(roleLabel)}.</p>
      </div>
    `;
  }

  const api = { renderEmptyState, renderErrorState, renderForbiddenState };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CasagbiEmptyErrorState = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
