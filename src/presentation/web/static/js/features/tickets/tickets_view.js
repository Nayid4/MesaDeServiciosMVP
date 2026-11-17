/**
 * Vista Dumb de Tickets (bandeja, carga coordinador y paginación SQL; delega detalle y creación).
 */
(function (root) {
  function esc(val) {
    return root.CasagbiUtils?.escapeHtml ? root.CasagbiUtils.escapeHtml(val) : String(val ?? "");
  }

  function initialsFrom(value) {
    const raw = String(value || "").trim();
    if (!raw) return "UP";
    const base = raw.includes("@") ? raw.split("@")[0].replace(/[._-]+/g, " ") : raw;
    const parts = base.split(/\s+/).filter(Boolean);
    return parts.length >= 2 ? `${parts[0][0]}${parts[1][0]}`.toUpperCase() : base.slice(0, 2).toUpperCase();
  }

  function statusDotClass(status) {
    if (status === "En atención") return "bg-[#10b981]";
    if (status === "Asignado") return "bg-blue-500";
    if (status === "En espera") return "bg-amber-500";
    if (status === "Reabierto") return "bg-red-600";
    if (status === "Resuelto" || status === "Cerrado") return "bg-slate-400";
    return "bg-emerald-600";
  }

  function slaBadgeHtml(sla) {
    if (!sla) return "";
    const map = { Verde: "bg-emerald-50 text-[#004d28] border-emerald-200/80", Amarillo: "bg-amber-50 text-amber-900 border-amber-200", Rojo: "bg-red-50 text-red-800 border-red-200", Azul: "bg-blue-50 text-blue-900 border-blue-200" };
    const dotMap = { Verde: "bg-[#10b981]", Amarillo: "bg-amber-500", Rojo: "bg-red-600", Azul: "bg-blue-600" };
    return `<span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${map[sla.semaphore] || "bg-slate-100 text-slate-700 border-slate-200"}">
      <span class="w-1.5 h-1.5 rounded-full inline-block ${dotMap[sla.semaphore] || "bg-slate-400"}"></span>
      <span>${esc(sla.semaphore)}: ${esc(sla.label)}</span>
    </span>`;
  }

  function renderCoordinatorWorkload(loads) {
    const panel = document.getElementById("coordinator-workload-panel");
    const list = document.getElementById("coordinator-workload-list");
    if (!panel || !list) return;
    if (!loads || !loads.length) { panel.classList.add("hidden"); list.innerHTML = ""; return; }
    panel.classList.remove("hidden");
    list.innerHTML = loads.map((tech) => `
      <div class="p-2.5 rounded-xl border border-slate-200 bg-slate-50 flex items-center justify-between gap-2">
        <div class="min-w-0"><p class="font-semibold text-slate-900 truncate">${esc(tech.full_name)}</p><p class="text-[10px] text-slate-600 truncate">${esc(tech.area || "Mesa TIC")}</p></div>
        <span class="px-2 py-0.5 rounded-full text-[11px] font-bold shrink-0 ${Number(tech.open_tickets_count) >= 4 ? "bg-amber-100 text-amber-900" : "bg-emerald-100 text-[#004d28]"}">${Number(tech.open_tickets_count || 0)}</span>
      </div>`).join("");
  }

  function renderPagination(page, totalPages, totalItems, pageSize, onPageChange) {
    let cb = onPageChange;
    let size = pageSize;
    if (typeof pageSize === "function") {
      cb = pageSize;
      size = 10;
    }
    const viewCountEl = document.getElementById("tickets-view-count");
    if (viewCountEl) viewCountEl.innerHTML = `<strong class="text-slate-900">${Number(totalItems || 0)} tickets</strong> en esta vista`;
    const host = document.getElementById("tickets-pagination");
    if (host && root.CasagbiPagination) {
      root.CasagbiPagination.render(host, {
        page,
        pages: totalPages,
        total: totalItems,
        pageSize: size || 10,
        ariaLabel: "Paginación de tickets",
        onPageChange: cb,
      });
    }
  }

  function renderTicketsLoading() {
    const tbody = document.getElementById("tickets-table-body");
    if (tbody && root.CasagbiSkeletons) tbody.innerHTML = root.CasagbiSkeletons.renderTableSkeleton(5, 7);
  }

  function renderTicketsError(detail, onRetry) {
    const tbody = document.getElementById("tickets-table-body");
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="7" class="p-4">${root.CasagbiEmptyErrorState ? root.CasagbiEmptyErrorState.renderErrorState({ title: "Error cargando la bandeja de tickets", detail, retryAttr: 'data-tickets-retry="1"' }) : esc(detail)}</td></tr>`;
    tbody.querySelector("[data-tickets-retry]")?.addEventListener("click", onRetry);
  }

  function renderTicketsTable(tickets, selectedTicketId, onSelectTicket) {
    const tbody = document.getElementById("tickets-table-body");
    if (!tbody) return;
    if (!tickets.length) {
      tbody.innerHTML = `<tr><td colspan="7" class="p-4">${root.CasagbiEmptyErrorState ? root.CasagbiEmptyErrorState.renderEmptyState({ title: "No hay tickets que coincidan", detail: "Ajusta los criterios de búsqueda o cambia la vista guardada." }) : "No hay tickets que coincidan."}</td></tr>`;
      return;
    }
    tbody.innerHTML = tickets.map((t) => {
      const techIni = t.assigned_tech_email ? initialsFrom(t.assigned_tech_email) : "CO";
      const techLabel = t.assigned_tech_email || "En cola coordinador";
      return `<tr data-ticket-id="${t.id}" tabindex="0" class="hover:bg-emerald-50/40 cursor-pointer transition ${selectedTicketId === t.id ? "bg-emerald-50/70" : ""}">
        <td class="px-4 py-3.5 font-mono font-bold text-[#006837] whitespace-nowrap">${esc(t.ticket_number)}</td>
        <td class="px-4 py-3.5 min-w-[200px]"><p class="font-semibold text-slate-900">${esc(t.title)}</p><p class="text-[11px] text-slate-600 mt-0.5">${esc(t.service_name)}</p></td>
        <td class="px-4 py-3.5 text-slate-700 min-w-[160px]"><p class="text-[11px] font-semibold text-slate-800">${esc(t.requester_email || "--")}</p><p class="text-[11px] text-slate-600 mt-0.5">${esc(t.sede)} · ${esc(t.location)}</p></td>
        <td class="px-4 py-3.5 whitespace-nowrap"><span class="font-semibold text-slate-800">${esc(t.priority)}</span></td>
        <td class="px-4 py-3.5 whitespace-nowrap"><span class="inline-flex items-center gap-1.5 text-slate-700 font-medium"><span class="w-1.5 h-1.5 rounded-full ${statusDotClass(t.status)}"></span><span>${esc(t.status)}</span></span></td>
        <td class="px-4 py-3.5 whitespace-nowrap">${slaBadgeHtml(t.sla_status)}</td>
        <td class="px-4 py-3.5 whitespace-nowrap"><div class="flex items-center gap-2"><span class="w-6 h-6 rounded-full bg-slate-100 border border-slate-200 text-slate-700 text-[10px] font-bold flex items-center justify-center shrink-0">${esc(techIni)}</span><span class="text-[11px] text-slate-700 truncate max-w-[150px]">${esc(techLabel)}</span></div></td>
      </tr>`;
    }).join("");

    tbody.querySelectorAll("tr[data-ticket-id]").forEach((tr) => {
      const idNum = Number(tr.getAttribute("data-ticket-id"));
      tr.addEventListener("click", () => onSelectTicket(idNum));
      tr.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelectTicket(idNum); } });
    });
  }

  function renderDetailLoading() {
    const container = document.getElementById("ticket-detail-container");
    const mobileTabs = document.getElementById("detail-mobile-tabs");
    const left = document.getElementById("ticket-detail-left");
    if (container) container.classList.remove("hidden");
    if (mobileTabs) mobileTabs.classList.remove("hidden");
    if (left && root.CasagbiSkeletons) left.innerHTML = root.CasagbiSkeletons.renderTicketDetailSkeleton();
  }

  const api = {
    slaBadgeHtml,
    renderCoordinatorWorkload,
    renderPagination,
    renderTicketsLoading,
    renderTicketsError,
    renderTicketsTable,
    renderDetailLoading,
    setDetailMobileTab: (tab) => root.CasagbiTicketDetailView?.setDetailMobileTab(tab),
    renderTicketDetail: (d, u, c, h) => root.CasagbiTicketDetailView?.renderTicketDetail(d, u, c, h, slaBadgeHtml),
    renderCreateKbSuggestions: (a, fn) => root.CasagbiTicketModalsView?.renderCreateKbSuggestions(a, fn),
    renderCreateAttachmentsPreview: (f, p, fn) => root.CasagbiTicketModalsView?.renderCreateAttachmentsPreview(f, p, fn),
    setCreateUploadProgress: (v, p, l) => root.CasagbiTicketModalsView?.setCreateUploadProgress(v, p, l),
    renderOr03LiveEstimate: (s, u) => root.CasagbiTicketModalsView?.renderOr03LiveEstimate(s, u),
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CasagbiTicketsView = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
