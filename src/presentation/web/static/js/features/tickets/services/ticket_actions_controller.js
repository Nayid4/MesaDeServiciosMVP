/**
 * Controlador de acciones ITIL v4 y vistas guardadas sobre tickets.
 */
(function (root) {
  const SAVED_VIEWS_STORAGE_KEY = "casagbi_saved_ticket_views_v1";

  function readCustomSavedViews() {
    try {
      const raw = window.localStorage.getItem(SAVED_VIEWS_STORAGE_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  }

  function saveCustomView(viewObj) {
    const saved = readCustomSavedViews();
    saved.push(viewObj);
    try {
      window.localStorage.setItem(SAVED_VIEWS_STORAGE_KEY, JSON.stringify(saved.slice(-10)));
    } catch {
      /* ignore */
    }
  }

  function renderCustomSavedViewsSelect() {
    const sel = document.getElementById("custom-saved-views-select");
    if (!sel) return;
    const esc = root.CasagbiApi.escapeHtml;
    const saved = readCustomSavedViews();
    sel.innerHTML = [
      `<option value="">Mis vistas guardadas (${saved.length})...</option>`,
      ...saved.map((v, idx) => `<option value="${idx}">${esc(v.name)}</option>`),
    ].join("");
  }

  function updateSavedViewChips(preset) {
    const host = document.getElementById("tickets-saved-views");
    if (!host) return;
    host.querySelectorAll("[data-saved-view]").forEach((btn) => {
      const isSelected = btn.getAttribute("data-saved-view") === preset;
      const base = btn.getAttribute("data-saved-view") === "sla-risk"
        ? "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl cursor-pointer transition"
        : "px-3 py-1.5 rounded-xl cursor-pointer transition";
      btn.className = isSelected
        ? `${base} bg-emerald-50 text-[#006837] border border-emerald-200 font-semibold`
        : `${base} text-slate-700 hover:bg-slate-100 font-medium`;
    });
  }

  function createTicketActionsController({ getCurrentDetail, onReloadAndOpen }) {
    async function postVersionedAction(url, body, successMsg, errorTitle, emitStatusEvent = false) {
      try {
        const cur = getCurrentDetail();
        await root.CasagbiApi.post(url, { ...body, version: body.version ?? cur?.ticket?.version ?? null });
        root.CasagbiApi.showToast(successMsg, "success");
        if (emitStatusEvent) window.dispatchEvent(new CustomEvent("casagbi:ticket-status-changed"));
        return true;
      } catch (err) {
        root.CasagbiApi.showToast(err.message, err.status === 409 ? "warning" : "error", err.problem?.title || errorTitle);
        if (err.status === 409) return "conflict";
        return false;
      }
    }

    async function handleTransition(ticketId, body) {
      const res = await postVersionedAction(
        `/api/v1/tickets/${ticketId}/transition`,
        body,
        `Ticket actualizado a ${body.new_status}`,
        "Error de transición",
        true
      );
      if (res) await onReloadAndOpen?.(ticketId);
    }

    async function handleReassign(ticketId, body) {
      const res = await postVersionedAction(
        `/api/v1/tickets/${ticketId}/reassign`,
        body,
        "Ticket reasignado manteniendo SLA.",
        "Error",
        false
      );
      if (res) await onReloadAndOpen?.(ticketId);
    }

    async function handleAdjustPriority(ticketId, body) {
      const res = await postVersionedAction(
        `/api/v1/tickets/${ticketId}/priority`,
        body,
        "Prioridad OR-03 ajustada con justificación en bitácora.",
        "Error ajustando prioridad",
        false
      );
      if (res) await onReloadAndOpen?.(ticketId);
    }

    async function handleRateClose(ticketId, body) {
      const res = await postVersionedAction(
        `/api/v1/tickets/${ticketId}/rate`,
        body,
        "Cierre confirmado y calificación registrada.",
        "Error",
        true
      );
      if (res) await onReloadAndOpen?.(ticketId);
    }

    function handleProposeKbArticle(ticket) {
      window.dispatchEvent(new CustomEvent("casagbi:propose-kb", { detail: { ticket } }));
    }

    return {
      readCustomSavedViews,
      saveCustomView,
      renderCustomSavedViewsSelect,
      updateSavedViewChips,
      handleTransition,
      handleReassign,
      handleAdjustPriority,
      handleRateClose,
      handleProposeKbArticle,
    };
  }

  const api = { createTicketActionsController, readCustomSavedViews, saveCustomView, renderCustomSavedViewsSelect, updateSavedViewChips };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CasagbiTicketActionsController = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
