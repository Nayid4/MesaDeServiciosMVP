/**
 * Componente Dumb de Página de Detalle: cabecera, stepper ITIL v4, sub-pestañas y delegación de paneles.
 */
(function (root) {
  function esc(val) {
    return root.CasagbiUtils?.escapeHtml ? root.CasagbiUtils.escapeHtml(val) : String(val ?? "");
  }

  function statusToneClass(status) {
    if (status === "En atención") return "bg-emerald-50 text-[#006837] border-emerald-200/80";
    if (status === "Asignado") return "bg-blue-50 text-blue-800 border-blue-200/80";
    if (status === "En espera") return "bg-amber-50 text-amber-800 border-amber-200";
    if (status === "Reabierto") return "bg-red-50 text-red-800 border-red-200";
    if (status === "Resuelto" || status === "Cerrado") return "bg-slate-100 text-slate-700 border-slate-200";
    return "bg-emerald-50 text-[#006837] border-emerald-200/80";
  }

  function dotToneClass(status) {
    if (status === "En atención") return "bg-[#10b981]";
    if (status === "Asignado") return "bg-blue-500";
    if (status === "En espera") return "bg-amber-500";
    if (status === "Reabierto") return "bg-red-600";
    return "bg-slate-400";
  }

  function setDetailMobileTab(tabName) {
    const left = document.getElementById("ticket-detail-left");
    const chatPanel = document.getElementById("ticket-detail-chat-panel");
    const tabs = document.getElementById("detail-mobile-tabs");
    if (!left || !chatPanel || !tabs) return;
    const isChat = tabName === "chat";
    left.classList.toggle("hidden", isChat);
    left.classList.add("xl:block");
    chatPanel.classList.toggle("hidden", !isChat);
    chatPanel.classList.toggle("flex", isChat);
    chatPanel.classList.add("xl:flex");

    tabs.querySelectorAll("[data-detail-tab]").forEach((btn) => {
      const active = btn.getAttribute("data-detail-tab") === tabName;
      btn.className = active
        ? "py-2 rounded-xl bg-[#006837] text-white text-xs font-semibold cursor-pointer"
        : "py-2 rounded-xl bg-slate-100 text-slate-700 text-xs font-semibold cursor-pointer";
    });
  }

  function renderStepper(ticket) {
    const host = document.getElementById("detail-stepper-card");
    if (!host) return;
    const status = ticket.status || "Registrado";
    const step4Label = status === "En espera" ? "En espera" : status === "Reabierto" ? "Reabierto" : "En atención";
    const step5Label = status === "Cerrado" ? "Cerrado" : status === "Anulado" ? "Anulado" : "Resuelto";

    let currentStep = 1;
    if (status === "Registrado") currentStep = ticket.assigned_tech_id ? 3 : 2;
    else if (status === "Asignado") currentStep = 3;
    else if (["En atención", "En espera", "Reabierto"].includes(status)) currentStep = 4;
    else if (["Resuelto", "Cerrado", "Anulado"].includes(status)) currentStep = 5;

    const steps = [
      { n: 1, label: "Registrado" },
      { n: 2, label: "Clasificado" },
      { n: 3, label: "Asignado" },
      { n: 4, label: step4Label },
      { n: 5, label: step5Label },
    ];
    const checkSvg = root.CasagbiIcons ? root.CasagbiIcons.svg("check", "w-4 h-4") : "&#10003;";

    const nodesHtml = steps.map((s, idx) => {
      const done = s.n < currentStep || (s.n === 5 && status === "Cerrado");
      const active = !done && s.n === currentStep;
      const circleCls = done
        ? "bg-[#006837] text-white border-[#006837]"
        : active
          ? "bg-white text-[#006837] border-2 border-[#006837] ring-4 ring-emerald-50"
          : "bg-slate-50 text-slate-500 border border-slate-200";
      const labelCls = done || active ? "text-slate-900 font-bold" : "text-slate-600 font-medium";
      const lineDone = s.n < currentStep;
      const connector = idx < steps.length - 1
        ? `<div class="hidden sm:block flex-1 h-0.5 mx-2 ${lineDone ? "bg-[#006837]" : "bg-slate-200"}" aria-hidden="true"></div>`
        : "";
      return `
        <div class="flex items-center ${idx < steps.length - 1 ? "sm:flex-1" : ""}">
          <div class="flex flex-col items-center gap-1.5 text-center min-w-[78px]">
            <span class="w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold border transition ${circleCls}">${done ? checkSvg : s.n}</span>
            <span class="text-[11px] ${labelCls}">${esc(s.label)}</span>
          </div>
          ${connector}
        </div>`;
    }).join("");

    host.innerHTML = `
      <div class="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p class="text-[11px] font-bold tracking-wider uppercase text-slate-600">SEGUIMIENTO DEL CASO</p>
          <h2 class="text-base font-bold text-slate-900">Ciclo de vida del ticket</h2>
        </div>
        <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border ${statusToneClass(status)}">
          <span class="w-1.5 h-1.5 rounded-full ${dotToneClass(status)}"></span>
          <span>${esc(status)}</span>
        </span>
      </div>
      <div class="grid grid-cols-2 sm:flex sm:items-center sm:justify-between gap-3 pt-1">${nodesHtml}</div>`;
  }

  function updateSubtabButtons(activeTab) {
    const host = document.getElementById("detail-subtabs");
    if (!host) return;
    host.querySelectorAll("[data-detail-subtab]").forEach((btn) => {
      const key = btn.getAttribute("data-detail-subtab");
      const active = key === activeTab;
      btn.setAttribute("aria-selected", String(active));
      const extra = key === "history" ? "inline-flex items-center justify-center gap-2 " : "";
      btn.className = active
        ? `${extra}py-2.5 px-4 rounded-xl bg-[#006837] text-white text-xs sm:text-sm font-semibold text-center transition cursor-pointer`
        : `${extra}py-2.5 px-4 rounded-xl bg-white hover:bg-slate-50 text-slate-700 text-xs sm:text-sm font-semibold text-center transition cursor-pointer`;
      const badge = btn.querySelector("#detail-history-badge");
      if (badge) {
        badge.className = active
          ? "px-2 py-0.5 rounded-full bg-white/20 text-white text-[10px] font-bold tabular-nums"
          : "px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 text-[10px] font-bold tabular-nums";
      }
    });
  }

  function renderTicketDetail(detail, user, catalog, handlers, slaBadgeHtml, opts = {}) {
    const t = detail.ticket;
    const left = document.getElementById("ticket-detail-left");
    const panels = root.CasagbiTicketDetailPanelsView;
    if (!left || !panels) return;

    const setText = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
    const createdFormatted = root.CasagbiUtils?.formatBogotaDate ? root.CasagbiUtils.formatBogotaDate(t.created_at) : t.created_at;
    setText("detail-breadcrumb-code", t.ticket_number);
    setText("detail-version-pill", `v${Number(t.version || 1)}`);
    setText("detail-title", t.title);
    setText("detail-meta-subtitle", `${t.ticket_number} · Creado el ${createdFormatted}`);

    const eventsLen = (detail.audit_events || []).length;
    setText("detail-events-count-label", `${eventsLen} ${eventsLen === 1 ? "evento registrado" : "eventos registrados"}`);
    setText("detail-history-badge", String(eventsLen));
    setText("chat-ticket-code", t.ticket_number);
    const msgLen = (detail.messages || []).length;
    setText("chat-messages-subtitle", `${msgLen} ${msgLen === 1 ? "mensaje" : "mensajes"} · WebSocket en vivo`);

    const headerBadges = document.getElementById("detail-header-badges");
    if (headerBadges) {
      headerBadges.innerHTML = `
        <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border ${statusToneClass(t.status)}">
          <span class="w-1.5 h-1.5 rounded-full ${dotToneClass(t.status)}"></span>
          <span>${esc(t.status)}</span>
        </span>
        <span class="px-3 py-1 rounded-full text-xs font-bold bg-white border border-slate-200 text-slate-900">${esc(t.priority)}</span>
        ${slaBadgeHtml ? slaBadgeHtml(t.sla_status) : ""}`;
    }

    renderStepper(t);

    let currentSubtab = ["summary", "manage", "history"].includes(opts.subtab) ? opts.subtab : "summary";
    const renderActiveSubtab = (nextTab) => {
      currentSubtab = nextTab;
      updateSubtabButtons(currentSubtab);
      handlers.onSubtabChange?.(currentSubtab);
      const localHandlers = { ...handlers, onSwitchSubtab: renderActiveSubtab };
      if (currentSubtab === "manage") panels.renderManagePanel(left, detail, user, catalog, localHandlers);
      else if (currentSubtab === "history") panels.renderHistoryPanel(left, detail);
      else panels.renderSummaryPanel(left, detail, user, localHandlers);
    };

    const subtabHost = document.getElementById("detail-subtabs");
    subtabHost?.querySelectorAll("[data-detail-subtab]").forEach((btn) => {
      btn.onclick = () => renderActiveSubtab(btn.getAttribute("data-detail-subtab"));
    });

    renderActiveSubtab(currentSubtab);
    setDetailMobileTab("info");
  }

  const api = { setDetailMobileTab, renderTicketDetail };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CasagbiTicketDetailView = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
