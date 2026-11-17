/**
 * Componente Dumb de Detalle, Línea de Tiempo y Formularios ITIL v4 de Ticket.
 */
(function (root) {
  function esc(val) {
    return root.CasagbiUtils?.escapeHtml ? root.CasagbiUtils.escapeHtml(val) : String(val ?? "");
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

  function buildTechActionsHtml(transitions, closingCats) {
    return `
      <div class="pt-3 border-t border-slate-200 space-y-3">
        <p class="text-xs font-bold text-slate-800">Gestión del Ciclo de Vida ITIL v4 (Técnico)</p>
        <div class="flex flex-wrap gap-2">
          ${transitions.includes("En atención") ? '<button type="button" data-quick-status="En atención" class="px-3 py-1.5 rounded-lg bg-[#006837] text-white text-xs font-semibold cursor-pointer">Iniciar / Retomar atención</button>' : ""}
        </div>
        ${transitions.includes("En espera") ? `
          <form id="pause-sla-form" class="flex gap-2">
            <input id="pause-reason-input" type="text" required placeholder="Motivo obligatorio para En espera (pausa reloj SLA)..." class="flex-1 px-3 py-1.5 rounded-lg border border-slate-300 text-xs" />
            <button type="submit" class="px-3 py-1.5 rounded-lg bg-blue-700 text-white text-xs font-semibold cursor-pointer">Pasar a En espera</button>
          </form>` : ""}
        ${transitions.includes("Resuelto") ? `
          <form id="resolve-ticket-form" class="space-y-2 bg-slate-50 p-3 rounded-xl border border-slate-200">
            <p class="text-[11px] font-bold text-slate-700">Documentar Resolución Técnica</p>
            <input id="res-diagnosis" type="text" required placeholder="Diagnóstico técnico obligatorio..." class="w-full px-3 py-1.5 rounded-lg border border-slate-300 text-xs bg-white" />
            <textarea id="res-solution" rows="2" required minlength="20" placeholder="Solución aplicada (mínimo 20 caracteres)..." class="w-full px-3 py-1.5 rounded-lg border border-slate-300 text-xs bg-white"></textarea>
            <div class="flex gap-2">
              <select id="res-category" aria-label="Categoría de cierre del ticket" class="flex-1 px-3 py-1.5 rounded-lg border border-slate-300 text-xs bg-white">${closingCats}</select>
              <button type="submit" class="px-4 py-1.5 rounded-lg bg-emerald-700 text-white text-xs font-semibold cursor-pointer">Marcar Resuelto</button>
            </div>
          </form>` : ""}
      </div>`;
  }

  function buildCoordinatorOpsHtml(t, techOptions) {
    return `
      <div class="pt-3 border-t border-slate-200 space-y-4">
        <form id="reassign-form" class="space-y-2">
          <p class="text-xs font-bold text-slate-800">Reasignación Manual (Coordinador / Admin)</p>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <select id="reassign-tech-id" aria-label="Nuevo técnico asignado" class="px-3 py-1.5 rounded-lg border border-slate-300 text-xs bg-white">${techOptions}</select>
            <input id="reassign-reason" type="text" required minlength="5" placeholder="Motivo obligatorio de reasignación (mín. 5 chars)..." class="px-3 py-1.5 rounded-lg border border-slate-300 text-xs" />
          </div>
          <button type="submit" class="px-3.5 py-1.5 rounded-lg bg-slate-900 text-white text-xs font-semibold cursor-pointer">Reasignar Técnico (SLA intacto)</button>
        </form>
        <form id="adjust-priority-form" class="space-y-2 p-3 rounded-xl bg-slate-50 border border-slate-200">
          <p class="text-xs font-bold text-slate-800">Ajustar Prioridad OR-03 con Justificación</p>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <select id="adj-impact" aria-label="Nivel de impacto OR-03" class="px-3 py-1.5 rounded-lg border border-slate-300 text-xs bg-white">
              <option value="Alto" ${t.impact === "Alto" ? "selected" : ""}>Impacto: Alto</option>
              <option value="Medio" ${t.impact === "Medio" ? "selected" : ""}>Impacto: Medio</option>
              <option value="Bajo" ${t.impact === "Bajo" ? "selected" : ""}>Impacto: Bajo</option>
            </select>
            <select id="adj-urgency" aria-label="Nivel de urgencia OR-03" class="px-3 py-1.5 rounded-lg border border-slate-300 text-xs bg-white">
              <option value="Alta" ${t.urgency === "Alta" ? "selected" : ""}>Urgencia: Alta</option>
              <option value="Media" ${t.urgency === "Media" ? "selected" : ""}>Urgencia: Media</option>
              <option value="Baja" ${t.urgency === "Baja" ? "selected" : ""}>Urgencia: Baja</option>
            </select>
          </div>
          <input id="adj-justification" type="text" required minlength="10" placeholder="Justificación obligatoria del ajuste (mín. 10 caracteres)..." class="w-full px-3 py-1.5 rounded-lg border border-slate-300 text-xs bg-white" />
          <button type="submit" class="px-3.5 py-1.5 rounded-lg bg-[#006837] text-white text-xs font-semibold cursor-pointer">Aplicar Nueva Prioridad OR-03</button>
        </form>
      </div>`;
  }

  function buildOwnerCloseHtml() {
    return `
      <div class="pt-3 border-t border-slate-200 grid grid-cols-1 sm:grid-cols-2 gap-3">
        <form id="rate-close-form" class="p-3 rounded-xl bg-emerald-50 border border-emerald-200 space-y-2">
          <p class="text-xs font-bold text-[#004d28]">Confirmar Cierre y Calificar (1 a 5)</p>
          <select id="csat-score" aria-label="Calificación de satisfacción CSAT" class="w-full px-3 py-1.5 rounded-lg border border-emerald-300 text-xs bg-white">
            <option value="5">5 - Muy satisfecho</option><option value="4">4 - Satisfecho</option><option value="3">3 - Aceptable</option>
            <option value="2">2 - Insatisfecho (comentario obligatorio)</option><option value="1">1 - Muy insatisfecho (comentario obligatorio)</option>
          </select>
          <input id="csat-comment" type="text" placeholder="Comentario opcional (obligatorio con 1 o 2)..." class="w-full px-3 py-1.5 rounded-lg border border-emerald-300 text-xs bg-white" />
          <p id="csat-comment-hint" class="hidden text-[11px] font-semibold text-red-700">Con calificación 1 o 2 debe explicar el motivo (mínimo 5 caracteres).</p>
          <button type="submit" class="w-full py-1.5 rounded-lg bg-[#006837] text-white text-xs font-semibold cursor-pointer">Confirmar y Cerrar Ticket</button>
        </form>
        <form id="reopen-form" class="p-3 rounded-xl bg-amber-50 border border-amber-200 space-y-2">
          <p class="text-xs font-bold text-amber-900">¿No se resolvió el caso?</p>
          <p class="text-[11px] text-amber-800">Puedes reabrir dentro de los 3 días hábiles siguientes a la resolución.</p>
          <input id="reopen-reason" type="text" required placeholder="Motivo obligatorio para reabrir..." class="w-full px-3 py-1.5 rounded-lg border border-amber-300 text-xs bg-white" />
          <button type="submit" class="w-full py-1.5 rounded-lg bg-amber-700 text-white text-xs font-semibold cursor-pointer">Reabrir Ticket</button>
        </form>
      </div>`;
  }

  function renderTicketDetail(detail, user, catalog, handlers, slaBadgeHtml) {
    const t = detail.ticket;
    const left = document.getElementById("ticket-detail-left");
    if (!left) return;
    const transitions = detail.valid_transitions || [];
    const canTechManage = ["tecnico", "coordinador", "admin"].includes(user.role);
    const canProposeKb = ["tecnico", "coordinador", "admin"].includes(user.role);
    const canCoordinatorOps = ["coordinador", "admin"].includes(user.role) && !detail.chat_read_only;
    const canOwnerClose = t.requester_id === user.id && t.status === "Resuelto";

    const timelineHtml = (detail.audit_events || []).map((ev) => `
      <li class="relative pl-5 pb-4 border-l border-emerald-200 last:border-l-0 last:pb-0">
        <span class="absolute -left-1.5 top-1 w-3 h-3 rounded-full bg-[#006837] ring-4 ring-white"></span>
        <p class="text-xs font-bold text-slate-900">${esc(ev.action)}${ev.new_status ? `<span class="ml-1.5 text-[10px] px-2 py-0.5 rounded bg-slate-100 text-slate-700">${esc(ev.new_status)}</span>` : ""}</p>
        <p class="text-[11px] text-slate-600 mt-0.5">${esc(ev.comment || "")}</p>
        <p class="text-[10px] text-slate-600 mt-0.5">${esc(ev.actor_email)} · ${esc(root.CasagbiUtils?.formatBogotaDate ? root.CasagbiUtils.formatBogotaDate(ev.created_at) : ev.created_at)}</p>
      </li>`).join("");

    const techOptions = (detail.available_technicians || []).map((th) => `<option value="${th.id}">${esc(th.full_name)} (${esc(th.area)} · ${Number(th.open_tickets_count ?? 0)} abiertos)</option>`).join("");
    const closingCats = (catalog?.closing_categories || ["Solución definitiva en sitio"]).map((c) => `<option value="${esc(c)}">${esc(c)}</option>`).join("");

    left.innerHTML = `
      <div class="bg-white rounded-2xl border border-slate-200 p-5 casagbi-shadow-card space-y-4">
        <div class="flex flex-wrap items-start justify-between gap-2">
          <div><span class="font-mono text-xs font-bold text-[#006837]">${esc(t.ticket_number)}</span><span class="ml-2 text-[10px] font-mono text-slate-600">v${Number(t.version || 1)}</span><h3 class="text-base font-bold text-slate-900">${esc(t.title)}</h3></div>
          <div class="flex flex-wrap gap-1.5 items-center"><span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-[#004d28]">${esc(t.status)}</span>${slaBadgeHtml ? slaBadgeHtml(t.sla_status) : ""}</div>
        </div>
        <p class="text-xs text-slate-700 leading-relaxed bg-slate-50 p-3.5 rounded-xl border border-slate-200">${esc(t.description)}</p>
        <div class="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
          <div><span class="text-slate-600 block">Solicitante</span><span class="font-mono font-semibold text-slate-900">${esc(t.requester_email)}</span></div>
          <div><span class="text-slate-600 block">Servicio</span><span class="font-semibold text-slate-900">${esc(t.service_name)}</span></div>
          <div><span class="text-slate-600 block">Prioridad OR-03</span><span class="font-semibold text-slate-900">${esc(t.priority)} (${esc(t.impact)} × ${esc(t.urgency)})</span></div>
          <div><span class="text-slate-600 block">Sede / Lugar</span><span class="font-semibold text-slate-900">${esc(t.sede)} · ${esc(t.location)}</span></div>
          <div><span class="text-slate-600 block">Técnico asignado</span><span class="font-mono font-semibold text-slate-900">${esc(t.assigned_tech_email || "En cola coordinador")}</span></div>
          <div><span class="text-slate-600 block">Vencimiento SLA</span><span class="font-mono text-slate-800">${esc(root.CasagbiUtils?.formatBogotaDate ? root.CasagbiUtils.formatBogotaDate(t.resolution_deadline) : (t.resolution_deadline || "--"))}</span></div>
        </div>
        ${t.priority_justification ? `<div class="p-3 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-950"><strong>Justificación de ajuste de prioridad:</strong> ${esc(t.priority_justification)}</div>` : ""}
        ${t.diagnosis || t.solution ? `<div class="p-3.5 rounded-xl bg-emerald-50/70 border border-emerald-200 text-xs space-y-1"><p><strong>Diagnóstico:</strong> ${esc(t.diagnosis || "")}</p><p><strong>Solución:</strong> ${esc(t.solution || "")}</p>${t.closing_category ? `<p><strong>Categoría de cierre:</strong> ${esc(t.closing_category)}</p>` : ""}</div>` : ""}
        ${canProposeKb ? '<div class="flex flex-wrap justify-end pt-1"><button id="propose-kb-from-ticket-btn" type="button" class="px-3.5 py-1.5 rounded-xl border border-[#006837] text-[#006837] hover:bg-emerald-50 text-xs font-semibold cursor-pointer">Proponer artículo KB desde este ticket</button></div>' : ""}
        ${canTechManage && transitions.length ? buildTechActionsHtml(transitions, closingCats) : ""}
        ${canCoordinatorOps ? buildCoordinatorOpsHtml(t, techOptions) : ""}
        ${canOwnerClose ? buildOwnerCloseHtml() : ""}
      </div>
      <div class="bg-white rounded-2xl border border-slate-200 p-5 casagbi-shadow-card"><h4 class="text-xs font-bold text-slate-800 uppercase mb-4">Línea de Tiempo y Trazabilidad Completa</h4><ol>${timelineHtml}</ol></div>`;

    left.querySelector("#propose-kb-from-ticket-btn")?.addEventListener("click", () => handlers.onProposeKbArticle?.(t));
    left.querySelectorAll("[data-quick-status]").forEach((btn) => btn.addEventListener("click", () => handlers.onTransition(t.id, { new_status: btn.getAttribute("data-quick-status") })));
    left.querySelector("#pause-sla-form")?.addEventListener("submit", (e) => { e.preventDefault(); handlers.onTransition(t.id, { new_status: "En espera", comment: document.getElementById("pause-reason-input").value }); });
    left.querySelector("#resolve-ticket-form")?.addEventListener("submit", (e) => {
      e.preventDefault();
      handlers.onTransition(t.id, { new_status: "Resuelto", diagnosis: document.getElementById("res-diagnosis").value, solution: document.getElementById("res-solution").value, closing_category: document.getElementById("res-category").value });
    });
    left.querySelector("#reassign-form")?.addEventListener("submit", (e) => {
      e.preventDefault();
      handlers.onReassign(t.id, { new_tech_id: Number(document.getElementById("reassign-tech-id").value), reason: document.getElementById("reassign-reason").value });
    });
    left.querySelector("#adjust-priority-form")?.addEventListener("submit", (e) => {
      e.preventDefault();
      handlers.onAdjustPriority(t.id, { impact: document.getElementById("adj-impact").value, urgency: document.getElementById("adj-urgency").value, justification: document.getElementById("adj-justification").value });
    });
    const csatSelect = left.querySelector("#csat-score");
    const csatInput = left.querySelector("#csat-comment");
    const csatHint = left.querySelector("#csat-comment-hint");
    csatSelect?.addEventListener("change", () => {
      const low = Number(csatSelect.value) <= 2;
      if (csatInput) { csatInput.required = low; if (low) csatInput.minLength = 5; else csatInput.removeAttribute("minlength"); }
      if (csatHint) csatHint.classList.toggle("hidden", !low);
    });
    left.querySelector("#rate-close-form")?.addEventListener("submit", (e) => {
      e.preventDefault();
      handlers.onRateClose(t.id, { csat_score: Number(document.getElementById("csat-score").value), csat_comment: document.getElementById("csat-comment").value, confirm_close: true });
    });
    left.querySelector("#reopen-form")?.addEventListener("submit", (e) => {
      e.preventDefault();
      handlers.onTransition(t.id, { new_status: "Reabierto", comment: document.getElementById("reopen-reason").value });
    });
    setDetailMobileTab("info");
  }

  const api = { setDetailMobileTab, renderTicketDetail };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CasagbiTicketDetailView = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
