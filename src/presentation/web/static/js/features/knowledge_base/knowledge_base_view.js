/**
 * Vista Dumb de Base de Conocimiento (tarjetas y formulario CRUD, delegando inspector a kb_inspector_view.js).
 */
(function (root) {
  function esc(val) {
    return root.CasagbiUtils?.escapeHtml ? root.CasagbiUtils.escapeHtml(val) : String(val ?? "");
  }

  function svgIcon(name, className = "w-4 h-4") {
    return root.CasagbiIcons?.svg ? root.CasagbiIcons.svg(name, className) : "";
  }

  function safeMarkup(raw) {
    return root.CasagbiKbInspectorView?.safeKbMarkup ? root.CasagbiKbInspectorView.safeKbMarkup(raw) : esc(raw);
  }

  function categoryIconName(serviceName, categoryTopic) {
    const joined = `${String(serviceName || "")} ${String(categoryTopic || "")}`.toLowerCase();
    if (joined.includes("wi-fi") || joined.includes("wifi") || joined.includes("eduroam") || joined.includes("red") || joined.includes("vpn")) return "wifi";
    if (joined.includes("cuenta") || joined.includes("correo") || joined.includes("acceso") || joined.includes("identidad")) return "users";
    return "kb";
  }

  function estimateReadMinutes(article) {
    const plain = `${String(article?.symptoms || "")} ${String(article?.solution_steps || "")}`.replace(/<[^>]+>/g, " ");
    return Math.max(2, Math.min(8, Math.ceil(plain.trim().split(/\s+/).filter(Boolean).length / 45)));
  }

  function statusBadgeClass(status) {
    if (status === "Publicado") return "bg-emerald-50 text-[#004d28] border-emerald-200";
    if (status === "En revisión") return "bg-blue-50 text-blue-900 border-blue-200";
    if (status === "Retirado") return "bg-red-50 text-red-900 border-red-200";
    return "bg-amber-50 text-amber-900 border-amber-200";
  }

  function renderLoading(gridId = "kb-articles-grid") {
    const grid = document.getElementById(gridId);
    if (grid && root.CasagbiSkeletons) grid.innerHTML = root.CasagbiSkeletons.renderKbSkeleton(4);
  }

  function configureRoleControls(userRole) {
    const canAuthor = ["tecnico", "coordinador", "admin"].includes(userRole);
    const canPublish = ["coordinador", "admin"].includes(userRole);
    const canSeeEditorialFilters = ["tecnico", "coordinador", "director", "admin"].includes(userRole);
    document.getElementById("kb-toggle-editor-btn")?.classList.toggle("hidden", !canAuthor);
    document.getElementById("kb-filter-status")?.classList.toggle("hidden", !canSeeEditorialFilters);
    document.getElementById("kb-filter-visibility")?.classList.toggle("hidden", !canSeeEditorialFilters);
    document.getElementById("kb-publish-btn")?.classList.toggle("hidden", !canPublish);
  }

  function toggleEditorVisibility(visible) {
    document.getElementById("kb-create-card")?.classList.toggle("hidden", !visible);
  }

  function populateEditorForm(article, modeLabel = "Nuevo artículo") {
    const setVal = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.value = val ?? "";
    };
    setVal("kb-article-id", article?.id || "");
    setVal("kb-source-ticket-id", article?.source_ticket_id || "");
    setVal("kb-code", article?.code || "");
    setVal("kb-title", article?.title || "");
    if (article?.service_name) setVal("kb-service", article.service_name);
    if (article?.category_topic) setVal("kb-category-topic", article.category_topic);
    if (article?.visibility) setVal("kb-visibility", article.visibility);
    setVal("kb-keywords", article?.keywords || "");
    setVal("kb-symptoms", article?.symptoms || "");
    setVal("kb-probable-cause", article?.probable_cause || "");
    setVal("kb-steps", article?.solution_steps || "");
    setVal("kb-escalation", article?.escalation_criteria || "");
    setVal("kb-change-summary", "");
    const badge = document.getElementById("kb-editor-mode-badge");
    if (badge) badge.textContent = modeLabel;
  }

  function buildWorkspaceCard(a, { canAuthor, canReview, userRole }) {
    const iconName = categoryIconName(a.service_name, a.category_topic);
    const readMins = estimateReadMinutes(a);
    const demoPill = a.is_demo ? '<span class="px-2 py-0.5 rounded-full bg-amber-50 text-amber-900 border border-amber-200 font-semibold text-[10px]">DEMO</span>' : "";
    const statusPill = `<span class="px-2 py-0.5 rounded-full border font-semibold text-[10px] ${statusBadgeClass(a.status)}">${esc(a.status)} · ${esc(a.visibility)}</span>`;
    const notesBanner = a.review_notes
      ? `<div class="p-2.5 rounded-xl bg-amber-50 border border-amber-200 text-[11px] text-amber-950"><strong>Observaciones de revisión:</strong> ${esc(a.review_notes)}</div>`
      : "";

    return `
      <article class="bg-white rounded-2xl border border-slate-200/80 p-5 casagbi-shadow-card flex flex-col justify-between gap-4 hover:border-emerald-200 transition">
        <div class="space-y-3">
          <div class="flex items-start justify-between gap-2">
            <span class="w-9 h-9 rounded-xl bg-emerald-50 border border-emerald-200/70 text-[#006837] flex items-center justify-center shrink-0">${svgIcon(iconName, "w-4 h-4")}</span>
            <div class="flex flex-wrap items-center justify-end gap-1.5">
              <span class="inline-flex items-center gap-1 text-[11px] text-slate-600">${svgIcon("clock", "w-3.5 h-3.5")}<span>${readMins} min</span></span>
              ${demoPill}${statusPill}
            </div>
          </div>
          <div class="space-y-1.5">
            <p class="text-[11px] font-bold tracking-wider uppercase text-[#006837]">${esc(a.category_topic || a.service_name)}</p>
            <h3 class="text-base font-bold text-slate-900 leading-snug">${esc(a.title)}</h3>
            <p class="text-xs text-slate-600 leading-relaxed line-clamp-2">${esc(String(a.symptoms || "").replace(/<[^>]+>/g, " "))}</p>
          </div>
          ${notesBanner}
        </div>
        <div class="pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2">
          <button type="button" data-kb-preview="${a.id}" class="inline-flex items-center gap-1.5 text-xs font-bold text-[#006837] hover:underline cursor-pointer"><span>Leer guía</span>${svgIcon("arrowRight", "w-3.5 h-3.5")}</button>
          <div class="flex flex-wrap gap-1.5">
            ${canAuthor ? `<button type="button" data-kb-edit="${a.id}" class="px-2.5 py-1 rounded-lg border border-slate-200 hover:bg-slate-100 text-slate-700 text-[11px] font-semibold cursor-pointer">Editar</button>` : ""}
            ${canAuthor || userRole === "director" ? `<button type="button" data-kb-versions="${a.id}" class="px-2.5 py-1 rounded-lg border border-slate-200 hover:bg-slate-100 text-slate-700 text-[11px] font-semibold cursor-pointer">v${Number(a.version || 1)}</button>` : ""}
            ${canAuthor && a.status === "Borrador" ? `<button type="button" data-kb-trans="enviar_revision:${a.id}" class="px-2.5 py-1 rounded-lg bg-blue-700 text-white text-[11px] font-semibold cursor-pointer">A revisión</button>` : ""}
            ${canReview && (a.status === "En revisión" || a.status === "Borrador") ? `<button type="button" data-kb-trans="publicar:${a.id}" class="px-2.5 py-1 rounded-lg bg-[#006837] text-white text-[11px] font-semibold cursor-pointer">Publicar</button>` : ""}
            ${canReview && a.status === "En revisión" ? `<button type="button" data-kb-return="${a.id}" class="px-2.5 py-1 rounded-lg bg-amber-700 text-white text-[11px] font-semibold cursor-pointer">Devolver</button>` : ""}
            ${canReview && a.status === "Publicado" ? `<button type="button" data-kb-trans="retirar:${a.id}" class="px-2.5 py-1 rounded-lg bg-red-700 text-white text-[11px] font-semibold cursor-pointer">Retirar</button>` : ""}
            ${canReview && a.status === "Retirado" ? `<button type="button" data-kb-trans="restaurar:${a.id}" class="px-2.5 py-1 rounded-lg bg-[#0D1522] text-white text-[11px] font-semibold cursor-pointer">Restaurar</button>` : ""}
          </div>
        </div>
      </article>`;
  }

  function renderArticles(articles, { gridId = "kb-articles-grid", userRole = "public", handlers = {} } = {}) {
    const grid = document.getElementById(gridId);
    if (!grid) return;
    const canAuthor = ["tecnico", "coordinador", "admin"].includes(userRole);
    const canReview = ["coordinador", "admin"].includes(userRole);
    const isWorkspace = gridId === "kb-articles-grid";
    if (isWorkspace) configureRoleControls(userRole);

    if (!articles || !articles.length) {
      grid.innerHTML = `<div class="col-span-full">${
        root.CasagbiEmptyErrorState
          ? root.CasagbiEmptyErrorState.renderEmptyState({
              title: "No encontramos guías con ese criterio",
              detail: "Prueba con otra palabra clave o ajusta los filtros de servicio, categoría y estado.",
            })
          : '<p class="text-xs text-slate-600 text-center py-6">Sin artículos coincidentes.</p>'
      }</div>`;
      return;
    }

    const byId = new Map();
    articles.forEach((a) => byId.set(Number(a.id), a));

    grid.innerHTML = articles.map((a) => {
      if (isWorkspace) return buildWorkspaceCard(a, { canAuthor, canReview, userRole });
      const categoryPill = a.category_topic ? `<span class="px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 font-medium text-[10px]">${esc(a.category_topic)}</span>` : "";
      return `
        <article class="bg-white rounded-2xl border border-slate-200 p-5 casagbi-shadow-card space-y-2.5 text-xs min-h-[190px] flex flex-col justify-between">
          <div class="space-y-2">
            <div class="flex flex-wrap items-center justify-between gap-1.5">
              <div class="flex flex-wrap items-center gap-1.5"><span class="font-mono font-bold text-[#006837]">${esc(a.code)}</span>${categoryPill}</div>
              <span class="px-2 py-0.5 rounded-full border font-semibold ${statusBadgeClass(a.status)}">${esc(a.status)}</span>
            </div>
            <h4 class="text-sm font-bold text-slate-900">${esc(a.title)}</h4>
            <p class="text-[11px] font-medium text-[#004d28]">${esc(a.service_name)}</p>
            <p class="text-slate-700"><strong>Síntomas:</strong> ${safeMarkup(a.symptoms)}</p>
            <div class="text-slate-800 bg-slate-50 p-3 rounded-xl border border-slate-200 leading-relaxed">
              <p class="font-semibold text-[11px] text-slate-700 mb-1">Pasos de solución:</p>
              <div>${safeMarkup(a.solution_steps)}</div>
            </div>
          </div>
        </article>`;
    }).join("");

    if (!isWorkspace) return;
    grid.querySelectorAll("[data-kb-preview]").forEach((btn) => btn.addEventListener("click", () => {
      const art = byId.get(Number(btn.getAttribute("data-kb-preview")));
      if (art) root.CasagbiKbInspectorView?.renderArticlePreview(art);
    }));
    grid.querySelectorAll("[data-kb-edit]").forEach((btn) => btn.addEventListener("click", () => {
      const art = byId.get(Number(btn.getAttribute("data-kb-edit")));
      if (art) handlers.onEdit?.(art);
    }));
    grid.querySelectorAll("[data-kb-versions]").forEach((btn) => btn.addEventListener("click", () => {
      handlers.onShowVersions?.(Number(btn.getAttribute("data-kb-versions")));
    }));
    grid.querySelectorAll("[data-kb-trans]").forEach((btn) => btn.addEventListener("click", () => {
      const [action, idStr] = String(btn.getAttribute("data-kb-trans")).split(":");
      handlers.onTransition?.(Number(idStr), action);
    }));
    grid.querySelectorAll("[data-kb-return]").forEach((btn) => btn.addEventListener("click", () => {
      handlers.onReturnWithNotes?.(Number(btn.getAttribute("data-kb-return")));
    }));
  }

  const api = {
    renderLoading,
    configureRoleControls,
    toggleEditorVisibility,
    populateEditorForm,
    renderArticles,
    renderArticlePreview: (a, f) => root.CasagbiKbInspectorView?.renderArticlePreview(a, f),
    renderVersionsPanel: (a, v, r, h) => root.CasagbiKbInspectorView?.renderVersionsPanel(a, v, r, h),
    renderComparisonDiff: (c) => root.CasagbiKbInspectorView?.renderComparisonDiff(c),
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CasagbiKnowledgeBaseView = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
