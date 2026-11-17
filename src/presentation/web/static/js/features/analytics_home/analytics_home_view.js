/**
 * Vista Dumb de Analítica y KPIs (delega tablas, prioridades y banners a analytics_charts.js).
 */
(function (root) {
  function esc(val) {
    return root.CasagbiUtils?.escapeHtml ? root.CasagbiUtils.escapeHtml(val) : String(val ?? "");
  }

  function svgIcon(name, className = "w-4 h-4") {
    return root.CasagbiIcons?.svg ? root.CasagbiIcons.svg(name, className) : "";
  }

  function renderLoadingState() {
    const cards = document.getElementById("kpi-cards-grid");
    if (cards && root.CasagbiSkeletons) cards.innerHTML = root.CasagbiSkeletons.renderKpiSkeleton(4);
    const tblSvc = document.getElementById("table-by-service-body");
    const tblTech = document.getElementById("table-tech-workload-body");
    const tblRecent = document.getElementById("resumen-recent-tickets-tbody");
    if (tblSvc && root.CasagbiSkeletons) tblSvc.innerHTML = root.CasagbiSkeletons.renderTableSkeleton(4, 3);
    if (tblTech && root.CasagbiSkeletons) tblTech.innerHTML = root.CasagbiSkeletons.renderTableSkeleton(4, 4);
    if (tblRecent && root.CasagbiSkeletons) tblRecent.innerHTML = root.CasagbiSkeletons.renderTableSkeleton(4, 7);
  }

  function renderErrorState(detail, onRetry) {
    const cards = document.getElementById("kpi-cards-grid");
    if (!cards || !root.CasagbiEmptyErrorState) return;
    cards.innerHTML = `<div class="col-span-full">${root.CasagbiEmptyErrorState.renderErrorState({
      title: "Error al cargar los indicadores del resumen",
      detail,
      retryAttr: 'data-kpi-retry="1"',
    })}</div>`;
    cards.querySelector("[data-kpi-retry]")?.addEventListener("click", onRetry);
  }

  function renderKpiCards(k) {
    const cardsConfig = [
      {
        id: "kpi-val-total",
        title: "Tickets registrados",
        num: Number(k.total_tickets || 0),
        decimals: 0,
        suffix: "",
        leftSub: `${k.open_tickets || 0} abiertos actualmente`,
        rightSub: `${k.resolved_or_closed || 0} resueltos`,
        icon: "tickets",
        iconBox: "bg-emerald-50 text-[#006837] border-emerald-200/70",
      },
      {
        id: "kpi-val-sla",
        title: "Cumplimiento SLA",
        num: Number(k.sla_compliance_pct || 0),
        decimals: 1,
        suffix: "%",
        leftSub: "Objetivo institucional: 95%",
        rightSub: `En riesgo/vencido: ${Number(k.at_risk_open_count || 0) + Number(k.breached_open_count || 0)}`,
        icon: "shieldCheck",
        iconBox: "bg-blue-50 text-blue-700 border-blue-200/70",
      },
      {
        id: "kpi-val-res",
        title: "Primera respuesta",
        num: Number(k.avg_first_response_min || 0),
        decimals: 1,
        suffix: " min",
        leftSub: "Promedio del periodo",
        rightSub: `Resolución: ${Number(k.avg_resolution_hours || 0).toFixed(1)} h`,
        icon: "clock",
        iconBox: "bg-amber-50 text-amber-700 border-amber-200/70",
      },
      {
        id: "kpi-val-csat",
        title: "Satisfacción CSAT",
        num: Number(k.avg_csat || 0),
        decimals: 1,
        suffix: " / 5",
        leftSub: `${Number(k.csat_count || 0)} evaluaciones recibidas`,
        rightSub: `Reapertura: ${Number(k.reopen_rate_pct || 0).toFixed(1)}%`,
        icon: "chatBubble",
        iconBox: "bg-purple-50 text-purple-700 border-purple-200/70",
      },
    ];

    const grid = document.getElementById("kpi-cards-grid");
    if (!grid) return;
    grid.innerHTML = cardsConfig.map((c) => `
      <article class="bg-white rounded-2xl border border-slate-200/80 p-5 casagbi-shadow-card min-h-[126px] flex flex-col justify-between gap-3">
        <div class="flex items-center justify-between gap-2">
          <p class="text-xs font-medium text-slate-600">${esc(c.title)}</p>
          <span class="w-8 h-8 rounded-xl border flex items-center justify-center shrink-0 ${c.iconBox}">${svgIcon(c.icon, "w-4 h-4")}</span>
        </div>
        <p id="${c.id}" class="text-3xl font-extrabold text-slate-900 tracking-tight tabular-nums">0</p>
        <div class="flex items-center justify-between gap-2 text-[11px]">
          <span class="text-slate-600">${esc(c.leftSub)}</span>
          <span class="font-semibold text-[#006837] shrink-0">${esc(c.rightSub)}</span>
        </div>
      </article>`).join("");

    cardsConfig.forEach((c) => {
      const el = document.getElementById(c.id);
      if (root.CasagbiUtils?.animateCounter) {
        root.CasagbiUtils.animateCounter(el, c.num, { decimals: c.decimals, suffix: c.suffix });
      } else if (el) {
        el.textContent = `${c.num.toFixed(c.decimals)}${c.suffix}`;
      }
    });
  }

  function renderEquivalentTables(data, total) {
    const byServiceEntries = Object.entries(data.by_service || {});
    const totalTickets = Math.max(1, Number(total || 0));
    const tblSvc = document.getElementById("table-by-service-body");
    if (tblSvc) {
      tblSvc.innerHTML = byServiceEntries.length
        ? byServiceEntries.map(([svc, cnt]) => `<tr>
            <td class="px-3 py-2 font-medium text-slate-800">${esc(svc)}</td>
            <td class="px-3 py-2 text-right font-mono font-semibold text-slate-900">${Number(cnt)}</td>
            <td class="px-3 py-2 text-right text-slate-600">${((Number(cnt) / totalTickets) * 100).toFixed(1)}%</td>
          </tr>`).join("")
        : '<tr><td colspan="3" class="px-3 py-4 text-center text-slate-600">Sin registros en este filtro.</td></tr>';
    }

    const workload = data.technician_workload || [];
    const tblTech = document.getElementById("table-tech-workload-body");
    if (tblTech) {
      tblTech.innerHTML = workload.length
        ? workload.map((w) => `<tr>
            <td class="px-3 py-2 font-medium text-slate-800">${esc(w.full_name || w.email)}</td>
            <td class="px-3 py-2 text-slate-600">${esc(w.area || "Mesa TIC")}</td>
            <td class="px-3 py-2 text-right font-mono font-semibold text-[#006837]">${Number(w.open_tickets || 0)}</td>
            <td class="px-3 py-2 text-right font-mono text-slate-700">${Number(w.resolved_tickets || 0)}</td>
          </tr>`).join("")
        : '<tr><td colspan="4" class="px-3 py-4 text-center text-slate-600">Sin técnicos activos en alcance.</td></tr>';
    }
  }

  function renderKpisData(data, handlers = {}) {
    const k = data.kpis || {};
    const scopeEl = document.getElementById("kpi-scope-badge");
    if (scopeEl) scopeEl.textContent = data.scope_label || "Alcance operativo (RF-22)";

    const charts = root.CasagbiAnalyticsCharts;
    charts?.renderStatusBanner(k);
    renderKpiCards(k);

    const legendRec = document.getElementById("resumen-legend-received");
    const legendRes = document.getElementById("resumen-legend-resolved");
    if (legendRec) legendRec.textContent = String(Number(k.total_tickets || 0));
    if (legendRes) legendRes.textContent = String(Number(k.resolved_or_closed || 0));

    charts?.renderPriorityBars(data);
    charts?.renderRecentAttentionTickets(data.recent_attention_tickets || [], handlers.onOpenTicket);
    renderEquivalentTables(data, k.total_tickets);
  }

  const api = { renderLoadingState, renderErrorState, renderKpisData };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CasagbiAnalyticsHomeView = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
