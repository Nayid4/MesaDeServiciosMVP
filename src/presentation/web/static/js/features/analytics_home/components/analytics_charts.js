/**
 * Componentes Dumb de Tablas, Semáforos SLA y Barras de Prioridad para el Resumen Analítico.
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

  function slaPillHtml(sla) {
    if (!sla) return '<span class="text-slate-400">--</span>';
    const map = {
      Verde: "bg-emerald-50 text-[#004d28] border-emerald-200/80",
      Amarillo: "bg-amber-50 text-amber-900 border-amber-200",
      Rojo: "bg-red-50 text-red-800 border-red-200",
      Azul: "bg-blue-50 text-blue-900 border-blue-200",
      Gris: "bg-slate-100 text-slate-700 border-slate-200",
    };
    const dotMap = {
      Verde: "bg-[#10b981]",
      Amarillo: "bg-amber-500",
      Rojo: "bg-red-600",
      Azul: "bg-blue-600",
      Gris: "bg-slate-400",
    };
    return `<span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${map[sla.semaphore] || map.Gris}">
      <span class="w-1.5 h-1.5 rounded-full ${dotMap[sla.semaphore] || dotMap.Gris}"></span>
      <span>${esc(sla.label)}</span>
    </span>`;
  }

  function renderStatusBanner(kpis) {
    const banner = document.getElementById("resumen-status-banner");
    const titleEl = document.getElementById("resumen-status-title");
    const detailEl = document.getElementById("resumen-status-detail");
    const updEl = document.getElementById("resumen-updated-label");
    if (!banner || !titleEl || !detailEl) return;

    const total = Number(kpis.total_tickets || 0);
    const open = Number(kpis.open_tickets || 0);
    const breached = Number(kpis.breached_open_count || 0);
    const risk = Number(kpis.at_risk_open_count || 0);

    if (total === 0) {
      banner.className = "rounded-2xl border border-slate-200 bg-white px-4 py-3.5 flex flex-wrap items-center justify-between gap-3";
      titleEl.textContent = "Sin registros en el filtro actual";
      detailEl.textContent = "No hay tickets para mostrar en el alcance o filtros seleccionados.";
    } else if (breached > 0 || risk > 0) {
      banner.className = "rounded-2xl border border-amber-200 bg-amber-50/75 px-4 py-3.5 flex flex-wrap items-center justify-between gap-3";
      titleEl.textContent = "La operación requiere seguimiento prioritario";
      detailEl.textContent = `${open} casos activos · ${breached} SLA vencido(s) y ${risk} próximo(s) a vencer (>= 75%).`;
    } else {
      banner.className = "rounded-2xl border border-emerald-200/80 bg-[#F1F8F4] px-4 py-3.5 flex flex-wrap items-center justify-between gap-3";
      titleEl.textContent = "La operación está bajo control";
      detailEl.textContent = open > 0
        ? `Todos los canales de atención están disponibles. ${open} ticket(s) activos dentro del tiempo objetivo.`
        : "Todos los canales de atención están disponibles. No hay tickets activos en riesgo.";
    }
    if (updEl) updEl.textContent = "Datos reales del servidor";
  }

  function renderPriorityBars(data) {
    const host = document.getElementById("resumen-priority-bars");
    const subEl = document.getElementById("resumen-pending-subtitle");
    const alertTitle = document.getElementById("resumen-sla-alert-title");
    const alertBtn = document.getElementById("resumen-sla-alert-btn");
    if (!host) return;

    const k = data.kpis || {};
    const openByPrio = data.open_by_priority || data.by_priority || {};
    const rows = [
      { key: "P1 Crítica", label: "P1 · Crítica", dot: "bg-red-500", bar: "bg-red-500" },
      { key: "P2 Alta", label: "P2 · Alta", dot: "bg-amber-500", bar: "bg-amber-500" },
      { key: "P3 Media", label: "P3 · Media", dot: "bg-blue-500", bar: "bg-blue-500" },
      { key: "P4 Baja", label: "P4 · Baja", dot: "bg-slate-400", bar: "bg-slate-400" },
    ];
    const totalPending = rows.reduce((acc, r) => acc + Number(openByPrio[r.key] || 0), 0);
    if (subEl) {
      subEl.textContent = totalPending === 1 ? "1 caso abierto necesita atención" : `${totalPending} casos abiertos necesitan atención`;
    }

    const denom = Math.max(1, totalPending);
    host.innerHTML = rows.map((r) => {
      const cnt = Number(openByPrio[r.key] || 0);
      const pct = totalPending > 0 ? Math.round((cnt / denom) * 100) : 0;
      return `<div class="grid grid-cols-12 items-center gap-2 text-xs">
        <div class="col-span-5 flex items-center gap-2 text-slate-700"><span class="w-2 h-2 rounded-full ${r.dot} shrink-0"></span><span class="truncate font-medium">${esc(r.label)}</span></div>
        <div class="col-span-1 text-right font-bold text-slate-900 tabular-nums">${cnt}</div>
        <div class="col-span-4"><div class="h-2 rounded-full bg-slate-100 overflow-hidden"><div class="h-full rounded-full ${r.bar}" style="width: ${pct}%"></div></div></div>
        <div class="col-span-2 text-right text-[11px] text-slate-600 tabular-nums">${pct}%</div>
      </div>`;
    }).join("");

    const atRisk = Number(k.at_risk_open_count || 0) + Number(k.breached_open_count || 0);
    if (alertTitle) alertTitle.textContent = `${atRisk} SLA en riesgo`;
    if (alertBtn) alertBtn.classList.toggle("opacity-75", atRisk === 0);
  }

  function renderRecentAttentionTickets(tickets, onOpenTicket) {
    const tbody = document.getElementById("resumen-recent-tickets-tbody");
    if (!tbody) return;
    if (!tickets || !tickets.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="px-5 py-8 text-center text-slate-600">No hay tickets registrados que requieran atención en este filtro.</td></tr>';
      return;
    }

    tbody.innerHTML = tickets.map((t) => {
      const techName = t.assigned_tech_email || "En cola coordinador";
      const techIni = t.assigned_tech_email ? initialsFrom(t.assigned_tech_email) : "CO";
      return `<tr data-recent-ticket-id="${t.id}" tabindex="0" class="hover:bg-emerald-50/40 cursor-pointer transition">
        <td class="px-5 py-3.5 font-mono font-bold text-[#006837] whitespace-nowrap">${esc(t.ticket_number)}</td>
        <td class="px-5 py-3.5 min-w-[200px]"><p class="font-semibold text-slate-900">${esc(t.title)}</p><p class="text-[11px] text-slate-600 mt-0.5">${esc(t.service_name)}</p></td>
        <td class="px-5 py-3.5 min-w-[160px]"><p class="text-xs font-medium text-slate-800">${esc(t.requester_email || "--")}</p><p class="text-[11px] text-slate-600 mt-0.5">${esc(t.sede || "--")}${t.location ? ` · ${esc(t.location)}` : ""}</p></td>
        <td class="px-5 py-3.5 whitespace-nowrap"><span class="font-semibold text-slate-800">${esc(t.priority)}</span></td>
        <td class="px-5 py-3.5 whitespace-nowrap"><span class="inline-flex items-center gap-1.5 text-slate-700 font-medium"><span class="w-1.5 h-1.5 rounded-full ${statusDotClass(t.status)}"></span><span>${esc(t.status)}</span></span></td>
        <td class="px-5 py-3.5 whitespace-nowrap">${slaPillHtml(t.sla_status)}</td>
        <td class="px-5 py-3.5 whitespace-nowrap"><div class="flex items-center gap-2"><span class="w-6 h-6 rounded-full bg-slate-100 border border-slate-200 text-slate-700 text-[10px] font-bold flex items-center justify-center shrink-0">${esc(techIni)}</span><span class="text-slate-700 truncate max-w-[140px]">${esc(techName)}</span></div></td>
      </tr>`;
    }).join("");

    tbody.querySelectorAll("tr[data-recent-ticket-id]").forEach((tr) => {
      const tid = Number(tr.getAttribute("data-recent-ticket-id"));
      tr.addEventListener("click", () => onOpenTicket?.(tid));
      tr.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onOpenTicket?.(tid);
        }
      });
    });
  }

  const api = { renderStatusBanner, renderPriorityBars, renderRecentAttentionTickets };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CasagbiAnalyticsCharts = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
