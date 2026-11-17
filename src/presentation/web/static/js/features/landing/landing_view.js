/**
 * Vista Dumb de Landing Page pública (skeletons, métricas animadas, catálogo SLA, consulta invitado y FAQ acordeón).
 */
(function (root) {
  function esc(val) {
    return root.CasagbiUtils?.escapeHtml ? root.CasagbiUtils.escapeHtml(val) : String(val ?? "");
  }

  function renderCatalogSkeleton() {
    const grid = document.getElementById("landing-services-grid");
    if (grid && root.CasagbiSkeletons) {
      grid.innerHTML = root.CasagbiSkeletons.renderLandingCatalogSkeleton(6);
    }
  }

  function renderPublicSummary(summary) {
    const m = summary.metrics || {};
    const anim = (id, val, decimals = 0, suffix = "") => {
      const el = document.getElementById(id);
      if (!el) return;
      if (root.CasagbiUtils?.animateCounter) {
        root.CasagbiUtils.animateCounter(el, val, { decimals, suffix });
      } else {
        el.textContent = `${Number(val || 0).toFixed(decimals)}${suffix}`;
      }
    };
    anim("metric-total-tickets", Number(m.total_tickets || 0), 0, "");
    anim("metric-sla-pct", Number(m.sla_compliance_pct ?? 100), 1, "%");
    anim("metric-resp-min", Number(m.avg_first_response_min || 0), 0, " min");
    anim("metric-csat", Number(m.avg_csat || 0), 1, " / 5");

    const catalogGrid = document.getElementById("landing-services-grid");
    const kbSelect = document.getElementById("landing-kb-service");
    const services = summary.services || [];
    if (catalogGrid) {
      catalogGrid.innerHTML = services
        .map(
          (svc) => `
          <article class="rounded-2xl bg-white border border-slate-200 p-5 casagbi-shadow-card hover:border-emerald-300 transition min-h-[146px]">
            <div class="flex items-center justify-between gap-2 mb-2.5">
              <span class="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-emerald-50 text-[#006837] border border-emerald-200">
                ${esc(svc.area)}
              </span>
              <span class="text-[11px] text-slate-600 font-mono font-semibold">MS-${esc(svc.category_prefix || "GEN")}- · Impacto ${esc(svc.base_impact)}</span>
            </div>
            <h3 class="text-base font-semibold text-slate-900 mb-1.5">${esc(svc.service_name)}</h3>
            <p class="text-xs text-slate-600 leading-relaxed">${esc(svc.description)}</p>
          </article>
        `
        )
        .join("");
    }
    if (kbSelect) {
      kbSelect.innerHTML = `<option value="">Todos los servicios TIC</option>${services
        .map((s) => `<option value="${esc(s.service_name)}">${esc(s.service_name)}</option>`)
        .join("")}`;
    }
  }

  function renderGuestMessageBubble(msg, maskedOwnerEmail) {
    const msgId = Number(msg.id || msg.message_id);
    const isDeleted = Boolean(msg.is_deleted);
    const isMe = msg.sender_role === "invitado" || msg.sender_email === maskedOwnerEmail;
    const div = document.createElement("div");
    div.setAttribute("data-guest-msg-id", String(msgId));
    div.className = (isMe ? "flex flex-col items-end gap-0.5" : "flex flex-col items-start gap-0.5") + " casagbi-msg-enter";
    const attHtml =
      !isDeleted && Array.isArray(msg.attachments) && msg.attachments.length
        ? msg.attachments
            .map(
              (a) =>
                `<a href="${esc(a.signed_download_url || "#")}" target="_blank" rel="noopener" class="mt-1 inline-block underline text-[11px]">${esc(a.original_name)}</a>`
            )
            .join(" ")
        : "";
    div.innerHTML = `
      <span class="text-[10px] text-slate-600">${esc(msg.sender_email)} · ${esc(msg.sender_role)}</span>
      <div class="max-w-[85%] rounded-2xl px-3 py-2 text-xs ${
        isDeleted
          ? "bg-slate-100 text-slate-600 italic"
          : isMe
            ? "bg-[#006837] text-white"
            : "bg-white border border-slate-200 text-slate-800"
      }">${isDeleted ? "Este mensaje fue eliminado" : esc(msg.message).replaceAll("\n", "<br/>")} ${attHtml}</div>
    `;
    return div;
  }

  function renderGuestLookupResult(data, onChatSubmit) {
    const lookupResult = document.getElementById("public-lookup-result");
    if (!lookupResult) return;
    const t = data.ticket || {};
    const sla = t.sla_status || {};

    const timelineHtml = (data.timeline || [])
      .map(
        (ev) => `
        <li class="relative pl-5 pb-3 border-l border-emerald-200 last:border-l-0 last:pb-0">
          <span class="absolute -left-1.5 top-1 w-3 h-3 rounded-full bg-[#006837] ring-4 ring-white"></span>
          <p class="text-xs font-semibold text-slate-800">${esc(ev.action)}
            ${ev.new_status ? `<span class="ml-1.5 text-[11px] px-2 py-0.5 rounded bg-slate-100 text-slate-700">${esc(ev.new_status)}</span>` : ""}
          </p>
          <p class="text-[11px] text-slate-600 mt-0.5">${esc(ev.comment || "")}</p>
          <p class="text-[10px] text-slate-600 mt-0.5">${esc(root.CasagbiUtils?.formatBogotaDate ? root.CasagbiUtils.formatBogotaDate(ev.created_at) : String(ev.created_at).slice(0, 16))}</p>
        </li>
      `
      )
      .join("");

    lookupResult.innerHTML = `
      <div class="rounded-2xl border border-slate-200 bg-slate-50/70 p-5 space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div>
            <span class="text-xs font-mono font-semibold text-[#006837]">${esc(t.ticket_number)}</span>
            <span class="ml-2 text-[11px] px-2 py-0.5 rounded-full bg-slate-200 text-slate-700">Invitado: ${esc(data.masked_email)}</span>
            <h4 class="text-sm font-bold text-slate-900 mt-1">${esc(t.title)}</h4>
          </div>
          <div class="flex flex-wrap gap-1.5">
            <span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-[#004d28]">${esc(t.status)}</span>
            <span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-200 text-slate-800">${esc(t.priority)}</span>
          </div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs bg-white rounded-xl p-3 border border-slate-200">
          <div><span class="text-slate-600 block">Servicio / Área</span><span class="font-medium text-slate-900">${esc(t.service_name)}</span></div>
          <div><span class="text-slate-600 block">Sede / Ubicación</span><span class="font-medium text-slate-900">${esc(t.sede)} · ${esc(t.location)}</span></div>
          <div><span class="text-slate-600 block">Semáforo SLA</span><span class="font-semibold text-slate-900">${esc(sla.semaphore || "")} · ${esc(sla.label || "")}</span></div>
        </div>
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div class="bg-white rounded-xl p-4 border border-slate-200">
            <p class="text-xs font-semibold text-slate-700 mb-2">Línea de tiempo (correos enmascarados)</p>
            <ol class="mt-2">${timelineHtml}</ol>
          </div>
          <div class="bg-white rounded-xl border border-slate-200 flex flex-col h-72 overflow-hidden">
            <div class="px-3 py-2 bg-slate-50 border-b border-slate-200 flex items-center justify-between text-xs">
              <span class="font-semibold text-slate-800">Chat del Ticket (Sesión Invitado)</span>
              <span id="guest-ws-status" class="text-[11px] text-slate-600">Conectando...</span>
            </div>
            <div id="guest-chat-messages" class="flex-1 overflow-y-auto p-3 space-y-2 bg-slate-50/40" aria-live="polite"></div>
            <form id="guest-chat-form" class="p-2 border-t border-slate-200 flex gap-2">
              <input id="guest-chat-input" type="text" ${data.chat_read_only ? "disabled" : ""} placeholder="${data.chat_read_only ? "Solo lectura" : "Escribe al técnico asignado..."}" class="flex-1 px-3 py-1.5 rounded-lg border border-slate-300 text-xs" />
              <button type="submit" ${data.chat_read_only ? "disabled" : ""} class="px-3.5 py-1.5 rounded-lg bg-[#006837] text-white text-xs font-semibold cursor-pointer">Enviar</button>
            </form>
          </div>
        </div>
      </div>
    `;

    document.getElementById("guest-chat-form")?.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const inp = document.getElementById("guest-chat-input");
      const txt = (inp?.value || "").trim();
      if (!txt) return;
      inp.value = "";
      await onChatSubmit(txt);
    });
  }

  function renderLookupError(title, detail) {
    const lookupResult = document.getElementById("public-lookup-result");
    if (!lookupResult) return;
    lookupResult.classList.remove("hidden");
    lookupResult.innerHTML = `
      <div role="alert" class="rounded-xl border border-red-200 bg-red-50 p-4 text-xs text-red-900">
        <p class="font-semibold">${esc(title)}</p>
        <p class="mt-0.5">${esc(detail)}</p>
      </div>
    `;
  }

  const api = {
    renderCatalogSkeleton,
    renderPublicSummary,
    renderGuestMessageBubble,
    renderGuestLookupResult,
    renderLookupError,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CasagbiLandingView = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
