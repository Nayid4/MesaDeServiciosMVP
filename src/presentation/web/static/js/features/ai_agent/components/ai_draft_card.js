/**
 * Componente Dumb de Tarjetas Interactivas para el Asistente IA (borrador OR-03, aclaración y datos faltantes).
 */
(function (root) {
  const UPC_SERVICES = [
    "Conectividad y Redes Wi-Fi",
    "Plataformas Académicas (Aula Web / Vortal)",
    "Correo Institucional y Cuentas",
    "Aulas Inteligentes y Videoproyectores",
    "Equipos de Cómputo e Impresoras",
    "Software y Licenciamiento",
  ];
  const UPC_SEDES = ["Sede Sabanas (Valledupar)", "Sede Hurtado (Valledupar)", "Seccional Aguachica"];
  const UPC_LOCATIONS = [
    "Bloque A",
    "Bloque B",
    "Bloque C",
    "Bloque D",
    "Laboratorios de Cómputo",
    "Biblioteca",
    "Edificio Administrativo",
  ];

  function esc(val) {
    return root.CasagbiUtils?.escapeHtml ? root.CasagbiUtils.escapeHtml(val) : String(val ?? "");
  }

  function computeOr03Label(impact, urgency) {
    const matrix = {
      "Alto|Alta": "P1 Crítica (4h)",
      "Alto|Media": "P2 Alta (8h)",
      "Alto|Baja": "P3 Media (24h)",
      "Medio|Alta": "P2 Alta (8h)",
      "Medio|Media": "P3 Media (24h)",
      "Medio|Baja": "P4 Baja (40h)",
      "Bajo|Alta": "P3 Media (24h)",
      "Bajo|Media": "P4 Baja (40h)",
      "Bajo|Baja": "P4 Baja (40h)",
    };
    return matrix[`${impact}|${urgency}`] || "P3 Media (24h)";
  }

  function serviceImpact(svc) {
    if (svc === "Conectividad y Redes Wi-Fi" || svc === "Plataformas Académicas (Aula Web / Vortal)") return "Alto";
    if (svc === "Correo Institucional y Cuentas" || svc === "Aulas Inteligentes y Videoproyectores") return "Medio";
    return "Bajo";
  }

  function buildOptions(list, selected) {
    return list.map((item) => `<option value="${esc(item)}" ${item === selected ? "selected" : ""}>${esc(item)}</option>`).join("");
  }

  function createDraftCardElement(card, handlers) {
    const box = document.createElement("div");
    box.className = "w-full rounded-xl border border-emerald-200 bg-emerald-50/80 p-3 text-xs space-y-2 shadow-xs";
    box.innerHTML = `
      <div class="flex items-center justify-between gap-2">
        <span class="font-semibold text-[#004d28]">Borrador Editable (OR-03)</span>
        <span class="draft-prio-pill px-2 py-0.5 rounded-full bg-white text-[#006837] border border-emerald-200 font-semibold">${esc(card.priority)}</span>
      </div>
      <div class="space-y-1.5 text-[11px] text-slate-700">
        <label class="block"><span class="font-medium text-slate-600">Asunto</span>
          <input type="text" class="draft-title mt-0.5 w-full px-2 py-1 rounded-lg border border-emerald-200 bg-white text-slate-900" value="${esc(card.title)}" />
        </label>
        <label class="block"><span class="font-medium text-slate-600">Servicio TIC (${Number(card.confidence_pct || 0).toFixed(1)}%)</span>
          <select class="draft-service mt-0.5 w-full px-2 py-1 rounded-lg border border-emerald-200 bg-white text-slate-900">${buildOptions(UPC_SERVICES, card.service_name)}</select>
        </label>
        <div class="grid grid-cols-2 gap-1.5">
          <label class="block"><span class="font-medium text-slate-600">Sede</span>
            <select class="draft-sede mt-0.5 w-full px-2 py-1 rounded-lg border border-emerald-200 bg-white text-slate-900">${buildOptions(UPC_SEDES, card.sede)}</select>
          </label>
          <label class="block"><span class="font-medium text-slate-600">Ubicación</span>
            <select class="draft-location mt-0.5 w-full px-2 py-1 rounded-lg border border-emerald-200 bg-white text-slate-900">${buildOptions(UPC_LOCATIONS, card.location)}</select>
          </label>
        </div>
        <label class="block"><span class="font-medium text-slate-600">Urgencia (impacto en tu trabajo)</span>
          <select class="draft-urgency mt-0.5 w-full px-2 py-1 rounded-lg border border-emerald-200 bg-white text-slate-900">
            <option value="Alta" ${card.urgency === "Alta" ? "selected" : ""}>Alta — Detenido sin alternativa</option>
            <option value="Media" ${card.urgency === "Media" ? "selected" : ""}>Media — Avance parcial / alternativa</option>
            <option value="Baja" ${card.urgency === "Baja" ? "selected" : ""}>Baja — Puedo seguir trabajando</option>
          </select>
        </label>
        <label class="block"><span class="font-medium text-slate-600">Descripción</span>
          <textarea rows="2" class="draft-description mt-0.5 w-full px-2 py-1 rounded-lg border border-emerald-200 bg-white text-slate-900">${esc(card.description)}</textarea>
        </label>
      </div>
      <div class="pt-1 flex flex-wrap items-center gap-1.5">
        <button type="button" class="confirm-draft-btn flex-1 px-3 py-1.5 rounded-lg bg-[#006837] hover:bg-[#004d28] text-white font-semibold transition cursor-pointer">Confirmar y Radicar Ticket</button>
        <button type="button" class="draft-human-btn px-2.5 py-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-100 text-slate-700 font-semibold transition cursor-pointer">Ir a formulario</button>
      </div>`;

    const readEditedCard = () => ({
      ...card,
      title: box.querySelector(".draft-title")?.value?.trim() || card.title,
      service_name: box.querySelector(".draft-service")?.value || card.service_name,
      sede: box.querySelector(".draft-sede")?.value || card.sede,
      location: box.querySelector(".draft-location")?.value || card.location,
      urgency: box.querySelector(".draft-urgency")?.value || card.urgency,
      description: box.querySelector(".draft-description")?.value?.trim() || card.description,
    });

    const syncPrioPill = () => {
      const svc = box.querySelector(".draft-service")?.value || card.service_name;
      const urg = box.querySelector(".draft-urgency")?.value || card.urgency;
      const pill = box.querySelector(".draft-prio-pill");
      if (pill) pill.textContent = computeOr03Label(serviceImpact(svc), urg);
    };
    box.querySelector(".draft-service")?.addEventListener("change", syncPrioPill);
    box.querySelector(".draft-urgency")?.addEventListener("change", syncPrioPill);

    const btn = box.querySelector(".confirm-draft-btn");
    btn?.addEventListener("click", () => handlers.onConfirmDraft?.(readEditedCard(), btn));
    box.querySelector(".draft-human-btn")?.addEventListener("click", () => handlers.onHandoffHuman?.(readEditedCard()));
    return box;
  }

  function createClarifyServiceElement(options, handlers) {
    const box = document.createElement("div");
    box.className = "w-full rounded-xl border border-amber-200 bg-amber-50/80 p-2.5 text-xs space-y-2";
    box.innerHTML = `<p class="font-semibold text-amber-950 text-[11px]">Selecciona el servicio TIC que mejor describe tu caso:</p>
      <div class="flex flex-wrap gap-1.5">${(options || UPC_SERVICES).map((svc) => `<button type="button" data-pick-svc="${esc(svc)}" class="px-2.5 py-1 rounded-lg bg-white border border-amber-300 hover:bg-amber-100 text-slate-800 text-[11px] font-medium cursor-pointer">${esc(svc)}</button>`).join("")}</div>`;
    box.querySelectorAll("[data-pick-svc]").forEach((btn) => {
      btn.addEventListener("click", () => handlers.onSelectService?.(btn.getAttribute("data-pick-svc")));
    });
    return box;
  }

  function createMissingFieldsElement(missingFields, partialDraft, handlers) {
    const needSede = !partialDraft?.sede || (missingFields || []).includes("sede");
    const needLoc = !partialDraft?.location || (missingFields || []).includes("location");
    const needUrg = !partialDraft?.urgency || (missingFields || []).includes("urgency");

    const box = document.createElement("form");
    box.className = "w-full rounded-xl border border-blue-200 bg-blue-50/80 p-3 text-xs space-y-2";
    box.innerHTML = `<p class="font-semibold text-blue-950 text-[11px]">Completa estos datos antes del borrador:</p>
      ${needSede ? `<label class="block text-[11px]"><span class="font-medium text-slate-700">Sede UPC *</span><select class="mf-sede mt-0.5 w-full px-2 py-1.5 rounded-lg border border-blue-200 bg-white" required><option value="">Selecciona sede...</option>${buildOptions(UPC_SEDES, partialDraft?.sede)}</select></label>` : ""}
      ${needLoc ? `<label class="block text-[11px]"><span class="font-medium text-slate-700">Ubicación exacta *</span><select class="mf-loc mt-0.5 w-full px-2 py-1.5 rounded-lg border border-blue-200 bg-white" required><option value="">Selecciona bloque o salón...</option>${buildOptions(UPC_LOCATIONS, partialDraft?.location)}</select></label>` : ""}
      ${needUrg ? `<label class="block text-[11px]"><span class="font-medium text-slate-700">¿Puedes seguir trabajando? (Urgencia) *</span><select class="mf-urg mt-0.5 w-full px-2 py-1.5 rounded-lg border border-blue-200 bg-white" required><option value="">Selecciona impacto en tu labor...</option><option value="Alta">No puedo seguir trabajando (Urgencia Alta)</option><option value="Media">Puedo seguir parcialmente / tengo alternativa (Urgencia Media)</option><option value="Baja">Sí puedo seguir trabajando normalmente (Urgencia Baja)</option></select></label>` : ""}
      <button type="submit" class="w-full py-1.5 rounded-lg bg-[#006837] hover:bg-[#004d28] text-white text-[11px] font-semibold cursor-pointer">Continuar al borrador</button>`;

    box.addEventListener("submit", (e) => {
      e.preventDefault();
      handlers.onSubmitMissingFields?.({
        selected_service: partialDraft?.service_name || null,
        selected_sede: box.querySelector(".mf-sede")?.value || partialDraft?.sede || null,
        selected_location: box.querySelector(".mf-loc")?.value || partialDraft?.location || null,
        selected_urgency: box.querySelector(".mf-urg")?.value || partialDraft?.urgency || null,
      });
    });
    return box;
  }

  const api = { createDraftCardElement, createClarifyServiceElement, createMissingFieldsElement };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CasagbiAiDraftCard = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
