/**
 * Sub-paneles Dumb de Detalle de Ticket: Resumen, Gestión ITIL v4 e Historial.
 */
(function (root) {
  const OR03 = {
    "Alto|Alta": "P1 Crítica", "Alto|Media": "P2 Alta", "Alto|Baja": "P3 Media",
    "Medio|Alta": "P2 Alta", "Medio|Media": "P3 Media", "Medio|Baja": "P4 Baja",
    "Bajo|Alta": "P3 Media", "Bajo|Media": "P4 Baja", "Bajo|Baja": "P4 Baja",
  };
  const INPUT_CLS = "w-full px-3 py-2 rounded-xl border border-slate-200 text-xs bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-[#006837]/25 focus:border-[#006837]";

  function esc(val) {
    return root.CasagbiUtils?.escapeHtml ? root.CasagbiUtils.escapeHtml(val) : String(val ?? "");
  }

  function formatBogota(iso) {
    return root.CasagbiUtils?.formatBogotaDate ? root.CasagbiUtils.formatBogotaDate(iso) : String(iso || "--");
  }

  function metaCell(iconSvg, label, primary, secondary = "") {
    return `<div class="flex items-start gap-2.5"><span class="w-8 h-8 rounded-lg bg-slate-50 border border-slate-200/80 text-slate-600 flex items-center justify-center shrink-0 mt-0.5">${iconSvg}</span><div class="min-w-0"><span class="block text-[11px] font-medium text-slate-600">${esc(label)}</span><span class="block text-xs font-bold text-slate-900 break-words">${esc(primary)}</span>${secondary ? `<span class="block text-[11px] font-mono text-slate-600 truncate">${esc(secondary)}</span>` : ""}</div></div>`;
  }

  function stepHeader(num, title, subtitle) {
    return `<div class="flex items-start gap-2.5"><span class="w-7 h-7 rounded-lg bg-emerald-50 border border-emerald-200/80 text-[#006837] text-[11px] font-bold flex items-center justify-center shrink-0">${num}</span><div><h3 class="text-xs sm:text-sm font-bold text-slate-900">${title}</h3><p class="text-[11px] text-slate-600">${subtitle}</p></div></div>`;
  }

  function renderSummaryPanel(left, detail, user, handlers) {
    const t = detail.ticket;
    const canProposeKb = ["tecnico", "coordinador", "admin"].includes(user.role);
    const canOwnerClose = t.requester_id === user.id && t.status === "Resuelto";
    const ic = root.CasagbiIcons;
    const s = (n, cls = "w-4 h-4") => (ic ? ic.svg(n, cls) : "");

    left.innerHTML = `
      <div class="bg-white rounded-2xl border border-slate-200/80 p-5 sm:p-6 casagbi-shadow-card space-y-5">
        <div>
          <p class="text-[11px] font-bold tracking-wider uppercase text-slate-600">RESUMEN DEL TICKET</p>
          <h2 class="text-base font-bold text-slate-900">Descripción del caso</h2>
        </div>
        <div class="rounded-xl border border-slate-200/90 bg-slate-50/70 p-4 text-xs sm:text-sm text-slate-700 leading-relaxed whitespace-pre-line">${esc(t.description)}</div>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-x-5 gap-y-4 pt-1">
          ${metaCell(s("users"), "Solicitante", t.requester_full_name || t.requester_email, t.requester_full_name ? t.requester_email : "")}
          ${metaCell(s("sliders"), "Servicio", t.service_name, t.area || "")}
          ${metaCell(s("alert"), "Prioridad", `${t.priority} · ${t.impact} × ${t.urgency}`, `OR-03 (${t.ticket_type || "Incidencia"})`)}
          ${metaCell(s("wifi"), "Sede / lugar", `${t.sede} · ${t.location}`)}
          ${metaCell(s("shieldCheck"), "Técnico asignado", t.assigned_tech_full_name || t.assigned_tech_email || "En cola coordinador", t.assigned_tech_full_name && t.assigned_tech_email ? t.assigned_tech_email : "")}
          ${metaCell(s("clock"), "Vencimiento SLA", formatBogota(t.resolution_deadline), t.sla_status?.label || "")}
        </div>
        ${t.priority_justification ? `<div class="p-3.5 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-950"><strong>Justificación ajuste de prioridad:</strong> ${esc(t.priority_justification)}</div>` : ""}
        ${t.diagnosis || t.solution ? `<div class="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 text-xs space-y-1.5 text-slate-800"><p><strong>Diagnóstico técnico:</strong> ${esc(t.diagnosis || "")}</p><p><strong>Solución aplicada:</strong> ${esc(t.solution || "")}</p>${t.closing_category ? `<p><strong>Categoría de cierre:</strong> ${esc(t.closing_category)}</p>` : ""}</div>` : ""}
        ${t.csat_score ? `<div class="p-3.5 rounded-xl bg-blue-50 border border-blue-200 text-xs text-blue-950"><strong>Evaluación CSAT registrada:</strong> ${Number(t.csat_score)} / 5${t.csat_comment ? ` · "${esc(t.csat_comment)}"` : ""}</div>` : ""}
        ${canOwnerClose ? `<div class="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 flex flex-wrap items-center justify-between gap-2 text-xs"><span class="font-semibold text-[#004d28]">Este ticket fue marcado como Resuelto. Confirma el cierre o califica la atención.</span><button type="button" data-goto-subtab="manage" class="px-3.5 py-1.5 rounded-xl bg-[#006837] hover:bg-[#004d28] text-white font-semibold cursor-pointer">Calificar y cerrar</button></div>` : ""}
        <div class="rounded-xl border border-slate-200/80 bg-slate-50 px-3.5 py-2.5 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-600">
          <span class="inline-flex items-center gap-2">${s("lock", "w-3.5 h-3.5")}<span>La información del solicitante solo está disponible para el equipo asignado al caso.</span></span>
          ${canProposeKb ? '<button id="propose-kb-from-ticket-btn" type="button" class="px-3 py-1 rounded-lg border border-[#006837] text-[#006837] hover:bg-emerald-50 text-[11px] font-semibold cursor-pointer transition">Proponer artículo KB desde este ticket</button>' : ""}
        </div>
      </div>`;

    left.querySelector("#propose-kb-from-ticket-btn")?.addEventListener("click", () => handlers.onProposeKbArticle?.(t));
    left.querySelector("[data-goto-subtab]")?.addEventListener("click", () => handlers.onSwitchSubtab?.("manage"));
  }

  function renderManagePanel(left, detail, user, catalog, handlers) {
    const t = detail.ticket;
    const transitions = detail.valid_transitions || [];
    const canTechManage = ["tecnico", "coordinador", "admin"].includes(user.role);
    const canCoordinatorOps = ["coordinador", "admin"].includes(user.role) && !detail.chat_read_only;
    const canOwnerClose = t.requester_id === user.id && t.status === "Resuelto";
    const arrowSvg = root.CasagbiIcons ? root.CasagbiIcons.svg("arrowRight", "w-3.5 h-3.5") : "";
    const techOpts = (detail.available_technicians || []).map((th) => `<option value="${th.id}" ${Number(th.id) === Number(t.assigned_tech_id) ? "selected" : ""}>${esc(th.full_name)} · ${esc(th.area || "Mesa TIC")} (${Number(th.open_tickets_count ?? 0)} activos)</option>`).join("");
    const closingCats = (catalog?.closing_categories || ["Solución definitiva en sitio"]).map((c) => `<option value="${esc(c)}">${esc(c)}</option>`).join("");
    const rolePill = ["coordinador", "admin"].includes(user.role) ? "Coordinador / Admin" : user.role === "tecnico" ? "Técnico de soporte" : "Usuario solicitante";
    const stateOpts = [
      ...transitions.map((st) => `<option value="${esc(st)}">${esc(st)}</option>`),
      ...(!detail.chat_read_only ? [`<option value="__ATTACH_ONLY__">Mantener en ${esc(t.status)} (solo adjuntar evidencia)</option>`] : []),
    ].join("");
    const levelOpts = (vals, cur) => vals.map((v) => `<option value="${v}" ${cur === v ? "selected" : ""}>${v}</option>`).join("");

    left.innerHTML = `
      <div class="bg-white rounded-2xl border border-slate-200/80 p-5 sm:p-6 casagbi-shadow-card space-y-5">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div><p class="text-[11px] font-bold tracking-wider uppercase text-slate-600">GESTIÓN DEL TICKET</p><h2 class="text-base font-bold text-slate-900">Actualiza la atención</h2></div>
          <span class="px-3 py-1 rounded-xl border border-slate-200 bg-white text-[11px] font-semibold text-slate-700">${esc(rolePill)}</span>
        </div>
        ${detail.chat_read_only && !canOwnerClose ? '<div class="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-700">Este ticket se encuentra cerrado o anulado y no admite cambios operativos adicionales.</div>' : ""}
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
          ${canTechManage && (!detail.chat_read_only || transitions.length) ? `
            <form id="manage-status-form" class="p-4 rounded-2xl border border-slate-200/80 bg-white space-y-3.5">
              ${stepHeader("01", "Cambiar estado", "Describe el avance para dejar trazabilidad.")}
              <select id="manage-status-select" aria-label="Nuevo estado del ticket" class="${INPUT_CLS} font-medium">${stateOpts}</select>
              <div id="manage-resolution-fields" class="hidden space-y-2 p-3 rounded-xl bg-slate-50 border border-slate-200">
                <p class="text-[11px] font-bold text-slate-800">Documentación obligatoria de resolución</p>
                <input id="res-diagnosis" type="text" placeholder="Diagnóstico técnico obligatorio..." class="${INPUT_CLS}" />
                <textarea id="res-solution" rows="2" placeholder="Solución aplicada (mínimo 20 caracteres)..." class="${INPUT_CLS}"></textarea>
                <select id="res-category" aria-label="Categoría de cierre" class="${INPUT_CLS}">${closingCats}</select>
              </div>
              <textarea id="manage-status-comment" rows="3" placeholder="¿Qué cambió? Agrega contexto para el equipo y la persona solicitante..." class="${INPUT_CLS}"></textarea>
              <div class="space-y-1.5">
                <p class="text-[11px] text-slate-700"><strong class="font-semibold">Adjuntar evidencia</strong> · Fotos o documentos · máx. 5 archivos de 10 MB</p>
                <input id="manage-status-files" type="file" multiple accept="image/*,.pdf,.doc,.docx,.txt,.log,.csv,.webm,.ogg,.mp3,.wav" class="block w-full text-xs text-slate-600 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border file:border-slate-200 file:bg-slate-50 file:text-slate-700 file:font-semibold hover:file:bg-slate-100 rounded-xl border border-slate-200 p-1.5 cursor-pointer" />
                <p id="manage-files-preview" class="text-[11px] text-slate-600">Los adjuntos quedan guardados en la conversación y auditoría del caso.</p>
              </div>
              <button id="manage-status-submit" type="submit" class="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#006837] hover:bg-[#004d28] text-white text-xs font-semibold cursor-pointer transition disabled:opacity-60"><span>Guardar cambio de estado</span>${arrowSvg}</button>
            </form>` : !canOwnerClose ? '<div class="p-4 rounded-2xl border border-slate-200 bg-slate-50 text-xs text-slate-600">El equipo de soporte gestiona los cambios de estado y SLA de este caso. Usa la conversación de la derecha para responder al técnico o adjuntar evidencia.</div>' : ""}
          ${canCoordinatorOps ? `
            <div class="space-y-4">
              <form id="reassign-form" class="p-4 rounded-2xl border border-slate-200/80 bg-white space-y-3">
                ${stepHeader("02", "Reasignar responsable", "Elige a la persona que continuará la atención.")}
                <select id="reassign-tech-id" aria-label="Nuevo técnico asignado" class="${INPUT_CLS}">${techOpts}</select>
                <input id="reassign-reason" type="text" required minlength="5" placeholder="Motivo del cambio (mínimo 5 caracteres)" class="${INPUT_CLS}" />
                <button type="submit" class="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-800 text-xs font-semibold cursor-pointer transition"><span>Confirmar reasignación</span>${arrowSvg}</button>
              </form>
              <form id="adjust-priority-form" class="p-4 rounded-2xl border border-slate-200/80 bg-white space-y-3">
                ${stepHeader("03", "Ajustar prioridad", "La prioridad se calcula con impacto y urgencia.")}
                <div class="grid grid-cols-2 gap-2.5">
                  <div><label for="adj-impact" class="block text-[11px] font-semibold text-slate-700 mb-1">Impacto</label><select id="adj-impact" class="${INPUT_CLS}">${levelOpts(["Alto", "Medio", "Bajo"], t.impact)}</select></div>
                  <div><label for="adj-urgency" class="block text-[11px] font-semibold text-slate-700 mb-1">Urgencia</label><select id="adj-urgency" class="${INPUT_CLS}">${levelOpts(["Alta", "Media", "Baja"], t.urgency)}</select></div>
                </div>
                <div class="px-3.5 py-2.5 rounded-xl bg-slate-50 border border-slate-200/80 flex items-center justify-between text-xs">
                  <span class="text-slate-600 font-medium">Prioridad resultante</span>
                  <strong id="adj-live-prio" class="text-slate-900 font-bold">${esc(OR03[`${t.impact}|${t.urgency}`] || "P3 Media")}</strong>
                </div>
                <textarea id="adj-justification" rows="2" required minlength="10" placeholder="Justifica por qué cambian el impacto o la urgencia..." class="${INPUT_CLS}"></textarea>
                <button type="submit" class="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-[#006837] hover:bg-[#004d28] text-white text-xs font-semibold cursor-pointer transition"><span>Guardar prioridad</span>${arrowSvg}</button>
              </form>
            </div>` : ""}
          ${canOwnerClose ? `
            <div class="lg:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
              <form id="rate-close-form" class="p-4 rounded-2xl bg-emerald-50/70 border border-emerald-200 space-y-2.5">
                <h3 class="text-xs font-bold text-[#004d28]">Confirmar cierre y calificar (1 a 5)</h3>
                <select id="csat-score" aria-label="Calificación CSAT" class="w-full px-3 py-2 rounded-xl border border-emerald-300 text-xs bg-white"><option value="5">5 - Muy satisfecho</option><option value="4">4 - Satisfecho</option><option value="3">3 - Aceptable</option><option value="2">2 - Insatisfecho (comentario obligatorio)</option><option value="1">1 - Muy insatisfecho (comentario obligatorio)</option></select>
                <input id="csat-comment" type="text" placeholder="Comentario opcional (obligatorio con 1 o 2)..." class="w-full px-3 py-2 rounded-xl border border-emerald-300 text-xs bg-white" />
                <p id="csat-comment-hint" class="hidden text-[11px] font-semibold text-red-700">Con calificación 1 o 2 debes explicar el motivo (mínimo 5 caracteres).</p>
                <button type="submit" class="w-full py-2 rounded-xl bg-[#006837] hover:bg-[#004d28] text-white text-xs font-semibold cursor-pointer">Confirmar y Cerrar Ticket</button>
              </form>
              <form id="reopen-form" class="p-4 rounded-2xl bg-amber-50/80 border border-amber-200 space-y-2.5">
                <h3 class="text-xs font-bold text-amber-900">¿No se resolvió el caso?</h3>
                <p class="text-[11px] text-amber-800">Puedes reabrir dentro de los 3 días hábiles siguientes a la resolución.</p>
                <input id="reopen-reason" type="text" required placeholder="Motivo obligatorio para reabrir..." class="w-full px-3 py-2 rounded-xl border border-amber-300 text-xs bg-white" />
                <button type="submit" class="w-full py-2 rounded-xl bg-amber-700 hover:bg-amber-800 text-white text-xs font-semibold cursor-pointer">Reabrir Ticket</button>
              </form>
            </div>` : ""}
        </div>
      </div>`;

    bindManageFormEvents(left, t, handlers);
  }

  function bindManageFormEvents(left, t, handlers) {
    const statusSel = left.querySelector("#manage-status-select");
    const resBox = left.querySelector("#manage-resolution-fields");
    const resDiag = left.querySelector("#res-diagnosis");
    const resSol = left.querySelector("#res-solution");
    const commentBox = left.querySelector("#manage-status-comment");
    const filesInput = left.querySelector("#manage-status-files");
    const filesPrev = left.querySelector("#manage-files-preview");

    const syncManageFields = () => {
      const target = statusSel?.value || "";
      const isRes = target === "Resuelto";
      const needsReason = target === "En espera" || target === "Reabierto";
      resBox?.classList.toggle("hidden", !isRes);
      if (resDiag) resDiag.required = isRes;
      if (resSol) { resSol.required = isRes; if (isRes) resSol.minLength = 20; else resSol.removeAttribute("minlength"); }
      if (commentBox) {
        commentBox.required = needsReason;
        commentBox.placeholder = needsReason ? "Motivo obligatorio para pausar SLA o reabrir el ticket..." : "¿Qué cambió? Agrega contexto para el equipo y la persona solicitante...";
      }
    };
    statusSel?.addEventListener("change", syncManageFields);
    syncManageFields();

    filesInput?.addEventListener("change", () => {
      const count = filesInput.files?.length || 0;
      if (filesPrev) filesPrev.textContent = count ? `${count} archivo(s) seleccionado(s) para adjuntar al guardar.` : "Los adjuntos quedan guardados en la conversación y auditoría del caso.";
    });

    left.querySelector("#manage-status-form")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const target = statusSel?.value || "";
      const files = Array.from(filesInput?.files || []);
      const btn = left.querySelector("#manage-status-submit");
      if (target === "__ATTACH_ONLY__" && !files.length) return;
      if (btn) btn.disabled = true;
      try {
        const body = { new_status: target, comment: commentBox?.value || "" };
        if (target === "Resuelto") {
          body.diagnosis = resDiag?.value || "";
          body.solution = resSol?.value || "";
          body.closing_category = left.querySelector("#res-category")?.value || "";
        }
        await handlers.onTransition(t.id, body, { files, subtab: "manage" });
      } finally { if (btn) btn.disabled = false; }
    });

    left.querySelector("#reassign-form")?.addEventListener("submit", (e) => {
      e.preventDefault();
      handlers.onReassign(t.id, { new_tech_id: Number(document.getElementById("reassign-tech-id").value), reason: document.getElementById("reassign-reason").value }, { subtab: "manage" });
    });

    const adjImp = left.querySelector("#adj-impact");
    const adjUrg = left.querySelector("#adj-urgency");
    const livePrio = left.querySelector("#adj-live-prio");
    const updateLivePrio = () => { if (livePrio && adjImp && adjUrg) livePrio.textContent = OR03[`${adjImp.value}|${adjUrg.value}`] || "P3 Media"; };
    adjImp?.addEventListener("change", updateLivePrio);
    adjUrg?.addEventListener("change", updateLivePrio);
    left.querySelector("#adjust-priority-form")?.addEventListener("submit", (e) => {
      e.preventDefault();
      handlers.onAdjustPriority(t.id, { impact: adjImp.value, urgency: adjUrg.value, justification: document.getElementById("adj-justification").value }, { subtab: "manage" });
    });

    const csatSel = left.querySelector("#csat-score");
    const csatTxt = left.querySelector("#csat-comment");
    const csatHint = left.querySelector("#csat-comment-hint");
    csatSel?.addEventListener("change", () => {
      const low = Number(csatSel.value) <= 2;
      if (csatTxt) { csatTxt.required = low; if (low) csatTxt.minLength = 5; else csatTxt.removeAttribute("minlength"); }
      if (csatHint) csatHint.classList.toggle("hidden", !low);
    });
    left.querySelector("#rate-close-form")?.addEventListener("submit", (e) => {
      e.preventDefault();
      handlers.onRateClose(t.id, { csat_score: Number(csatSel.value), csat_comment: csatTxt.value, confirm_close: true }, { subtab: "summary" });
    });
    left.querySelector("#reopen-form")?.addEventListener("submit", (e) => {
      e.preventDefault();
      handlers.onTransition(t.id, { new_status: "Reabierto", comment: document.getElementById("reopen-reason").value }, { subtab: "summary" });
    });
  }

  function renderHistoryPanel(left, detail) {
    const events = detail.audit_events || [];
    const clockIcon = root.CasagbiIcons ? root.CasagbiIcons.svg("clock", "w-3 h-3") : "";
    const items = events.map((ev, idx) => `
      <li class="relative pl-6 pb-5 border-l border-slate-200 last:border-l-0 last:pb-0">
        <span class="absolute -left-[5px] top-1.5 w-2.5 h-2.5 rounded-full ${idx === 0 ? "bg-blue-500" : "bg-[#10b981]"} ring-4 ring-white"></span>
        <div class="flex flex-wrap items-start justify-between gap-2">
          <div class="space-y-1 min-w-0 flex-1">
            <p class="text-xs sm:text-sm font-bold text-slate-900">${esc(ev.action)}${ev.new_status ? `<span class="ml-2 text-[10px] px-2 py-0.5 rounded-full bg-emerald-50 text-[#006837] border border-emerald-200 font-semibold">${esc(ev.new_status)}</span>` : ""}</p>
            ${ev.comment ? `<p class="text-xs text-slate-700">${esc(ev.comment)}</p>` : ""}
            <p class="text-[11px] font-mono text-slate-600">${esc(ev.actor_email || "Sistema CASAGBI")}</p>
          </div>
          <span class="inline-flex items-center gap-1 text-[11px] text-slate-600 font-mono shrink-0">${clockIcon}<span>${esc(formatBogota(ev.created_at))}</span></span>
        </div>
      </li>`).join("");

    left.innerHTML = `
      <div class="bg-white rounded-2xl border border-slate-200/80 p-5 sm:p-6 casagbi-shadow-card space-y-5">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div><p class="text-[11px] font-bold tracking-wider uppercase text-slate-600">HISTORIAL DEL CASO</p><h2 class="text-base font-bold text-slate-900">Línea de tiempo y trazabilidad</h2></div>
          <span class="text-xs text-slate-600 font-medium">${events.length} ${events.length === 1 ? "evento" : "eventos"}</span>
        </div>
        ${events.length ? `<ol class="pt-1">${items}</ol>` : '<p class="text-xs text-slate-600">Sin eventos registrados.</p>'}
      </div>`;
  }

  const api = { renderSummaryPanel, renderManagePanel, renderHistoryPanel };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CasagbiTicketDetailPanelsView = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
