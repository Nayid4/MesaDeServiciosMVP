/**
 * Componente Dumb de Previsualización, Historial y Comparación de Versiones KB (XSS-safe).
 */
(function (root) {
  function esc(val) {
    return root.CasagbiUtils?.escapeHtml ? root.CasagbiUtils.escapeHtml(val) : String(val ?? "");
  }

  function safeKbMarkup(raw) {
    let escaped = esc(String(raw ?? ""));
    ["p", "strong", "b", "em", "i", "ul", "ol", "li", "code", "pre", "h4", "h5", "blockquote"].forEach((tag) => {
      escaped = escaped.replaceAll(`&lt;${tag}&gt;`, `<${tag}>`).replaceAll(`&lt;/${tag}&gt;`, `</${tag}>`);
    });
    return escaped
      .replaceAll("&lt;br&gt;", "<br/>")
      .replaceAll("&lt;br/&gt;", "<br/>")
      .replaceAll("&lt;br /&gt;", "<br/>")
      .replaceAll("\n", "<br/>");
  }

  function renderArticlePreview(article, sanitizedFields = null) {
    const panel = document.getElementById("kb-inspector-panel");
    if (!panel) return;
    const symp = sanitizedFields?.symptoms ?? article.symptoms ?? "";
    const cause = sanitizedFields?.probable_cause ?? article.probable_cause ?? "";
    const steps = sanitizedFields?.solution_steps ?? article.solution_steps ?? "";
    const escCrit = sanitizedFields?.escalation_criteria ?? article.escalation_criteria ?? "";

    panel.classList.remove("hidden");
    panel.innerHTML = `
      <div class="flex items-center justify-between gap-2 pb-2 border-b border-slate-200">
        <div>
          <span class="text-[11px] font-bold uppercase text-[#006837]">Previsualización Segura (HTML Saneado)</span>
          <h3 class="text-base font-bold text-slate-900">${esc(article.code || "BORRADOR")} · ${esc(article.title)}</h3>
        </div>
        <button id="kb-inspector-close-btn" type="button" class="px-3 py-1 rounded-lg border border-slate-300 text-xs font-semibold text-slate-700 hover:bg-slate-100 cursor-pointer">Cerrar</button>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
        <div><span class="text-slate-600">Servicio:</span> <strong>${esc(article.service_name)}</strong></div>
        <div><span class="text-slate-600">Categoría:</span> <strong>${esc(article.category_topic || "General")}</strong></div>
        <div><span class="text-slate-600">Visibilidad:</span> <strong>${esc(article.visibility || "Pública")}</strong></div>
      </div>
      <div class="space-y-2 text-xs">
        <p><strong>Síntomas:</strong> ${safeKbMarkup(symp)}</p>
        <p><strong>Causa probable:</strong> ${safeKbMarkup(cause)}</p>
        <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
          <p class="font-bold text-slate-800 mb-1">Pasos de solución:</p>
          <div>${safeKbMarkup(steps)}</div>
        </div>
        <p><strong>Cuándo escalar:</strong> ${safeKbMarkup(escCrit)}</p>
      </div>`;
    panel.querySelector("#kb-inspector-close-btn")?.addEventListener("click", () => panel.classList.add("hidden"));
    panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function renderVersionsPanel(article, versions, userRole, { onCompare, onRestore }) {
    const panel = document.getElementById("kb-inspector-panel");
    if (!panel) return;
    const canRestore = ["tecnico", "coordinador", "admin"].includes(userRole);
    panel.classList.remove("hidden");

    const verOptions = versions.map((v) => `<option value="${v.version_number}">v${v.version_number} (${esc(v.status)})</option>`).join("");

    panel.innerHTML = `
      <div class="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-200">
        <div>
          <span class="text-[11px] font-bold uppercase text-[#006837]">Historial y Comparación de Versiones</span>
          <h3 class="text-base font-bold text-slate-900">${esc(article.code)} · ${esc(article.title)}</h3>
        </div>
        <button id="kb-inspector-close-btn" type="button" class="px-3 py-1 rounded-lg border border-slate-300 text-xs font-semibold text-slate-700 hover:bg-slate-100 cursor-pointer">Cerrar</button>
      </div>
      ${versions.length >= 2 ? `<form id="kb-compare-form" class="p-3 rounded-xl bg-slate-50 border border-slate-200 flex flex-wrap items-center gap-2 text-xs">
        <span class="font-semibold text-slate-700">Comparar versiones:</span>
        <select id="kb-cmp-from" class="px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white">${verOptions}</select>
        <span class="text-slate-600">contra</span>
        <select id="kb-cmp-to" class="px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white">${verOptions}</select>
        <button type="submit" class="px-3.5 py-1.5 rounded-lg bg-[#006837] text-white font-semibold cursor-pointer">Comparar</button>
      </form>` : ""}
      <div id="kb-compare-result" class="hidden space-y-2 text-xs"></div>
      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs">
          <thead class="bg-slate-50 border-b border-slate-200 text-slate-700 text-[11px] uppercase">
            <tr><th scope="col" class="px-3 py-2">Versión</th><th scope="col" class="px-3 py-2">Estado</th><th scope="col" class="px-3 py-2">Autor cambio</th><th scope="col" class="px-3 py-2">Resumen</th><th scope="col" class="px-3 py-2">Fecha</th><th scope="col" class="px-3 py-2 text-right">Acción</th></tr>
          </thead>
          <tbody class="divide-y divide-slate-100">${versions.map((v) => `<tr>
            <td class="px-3 py-2 font-mono font-bold text-[#006837]">v${v.version_number}</td>
            <td class="px-3 py-2">${esc(v.status)}</td>
            <td class="px-3 py-2 font-mono text-[11px]">${esc(v.actor_email)}</td>
            <td class="px-3 py-2 text-slate-700">${esc(v.change_summary || "")}</td>
            <td class="px-3 py-2 font-mono text-[11px] text-slate-600">${esc(root.CasagbiUtils?.formatBogotaDate ? root.CasagbiUtils.formatBogotaDate(v.created_at) : v.created_at)}</td>
            <td class="px-3 py-2 text-right">${canRestore && Number(v.version_number) !== Number(article.version)
              ? `<button type="button" data-kb-restore-ver="${v.version_number}" class="px-2.5 py-1 rounded-lg border border-emerald-300 bg-emerald-50 hover:bg-emerald-100 text-[#004d28] font-semibold cursor-pointer">Restaurar v${v.version_number}</button>`
              : '<span class="text-[11px] text-slate-600">Actual</span>'}</td>
          </tr>`).join("")}</tbody>
        </table>
      </div>`;

    panel.querySelector("#kb-inspector-close-btn")?.addEventListener("click", () => panel.classList.add("hidden"));
    const cmpFrom = panel.querySelector("#kb-cmp-from");
    const cmpTo = panel.querySelector("#kb-cmp-to");
    if (cmpFrom && cmpTo && versions.length >= 2) {
      cmpFrom.value = String(versions[versions.length - 1].version_number);
      cmpTo.value = String(versions[0].version_number);
    }
    panel.querySelector("#kb-compare-form")?.addEventListener("submit", (e) => {
      e.preventDefault();
      onCompare?.(article.id, Number(cmpFrom.value), Number(cmpTo.value));
    });
    panel.querySelectorAll("[data-kb-restore-ver]").forEach((btn) => {
      btn.addEventListener("click", () => onRestore?.(article.id, Number(btn.getAttribute("data-kb-restore-ver"))));
    });
    panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function renderComparisonDiff(comparison) {
    const box = document.getElementById("kb-compare-result");
    if (!box) return;
    box.classList.remove("hidden");
    const diffs = comparison.differences || [];
    if (!diffs.length) {
      box.innerHTML = `<p class="p-3 rounded-xl bg-slate-50 border border-slate-200 text-slate-600">No hay diferencias de contenido entre v${comparison.from_version} y v${comparison.to_version}.</p>`;
      return;
    }
    box.innerHTML = diffs.map((d) => `
      <div class="p-3 rounded-xl border border-slate-200 bg-white space-y-1.5">
        <p class="font-bold text-slate-900">${esc(d.label)} (v${comparison.from_version} vs v${comparison.to_version})</p>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
          <div class="p-2 rounded-lg bg-red-50 border border-red-200 text-red-950"><span class="block text-[10px] font-bold uppercase mb-0.5">Anterior (v${comparison.from_version})</span><div>${safeKbMarkup(d.old_value)}</div></div>
          <div class="p-2 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-950"><span class="block text-[10px] font-bold uppercase mb-0.5">Nuevo (v${comparison.to_version})</span><div>${safeKbMarkup(d.new_value)}</div></div>
        </div>
      </div>`).join("");
  }

  const api = { safeKbMarkup, renderArticlePreview, renderVersionsPanel, renderComparisonDiff };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CasagbiKbInspectorView = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
