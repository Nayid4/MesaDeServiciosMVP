/**
 * Controlador de acciones ITIL v4, adjuntos en gestión y vistas guardadas sobre tickets.
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
      `<option value="">Vistas guardadas (${saved.length})...</option>`,
      ...saved.map((v, idx) => `<option value="${idx}">${esc(v.name)}</option>`),
    ].join("");
  }

  function updateSavedViewChips(preset) {
    const host = document.getElementById("tickets-saved-views");
    if (!host) return;
    host.querySelectorAll("[data-saved-view]").forEach((btn) => {
      const key = btn.getAttribute("data-saved-view");
      const isSelected = key === preset;
      const base = "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl cursor-pointer transition";
      btn.className = isSelected
        ? `${base} bg-emerald-50 text-[#006837] border border-emerald-200 font-semibold`
        : `${base} text-slate-700 hover:bg-slate-100 font-medium border border-transparent`;
      const badge = btn.querySelector("[data-view-count]");
      if (badge) {
        if (key === "sla-risk" && !isSelected) {
          badge.className = "px-1.5 py-0.2 rounded-full bg-amber-50 text-amber-800 text-[10px] font-bold tabular-nums border border-amber-200";
        } else if (isSelected) {
          badge.className = "px-1.5 py-0.2 rounded-full bg-white text-[#006837] text-[10px] font-bold tabular-nums border border-emerald-200";
        } else {
          badge.className = "px-1.5 py-0.2 rounded-full bg-slate-100 text-slate-700 text-[10px] font-bold tabular-nums";
        }
      }
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

    async function handleUploadAttachments(ticketId, files, caption = "") {
      const picked = Array.from(files || []).slice(0, 5);
      if (!picked.length) return { ok: true };
      const fd = new FormData();
      picked.forEach((f) => fd.append("files", f));
      const cleanCaption = String(caption || "").trim();
      fd.append("content", cleanCaption || "Evidencia adjunta desde gestión del ticket.");
      if (root.CasagbiTicketChatWS?.generateClientMessageId) {
        fd.append("client_message_id", root.CasagbiTicketChatWS.generateClientMessageId());
      }
      try {
        const res = await root.CasagbiApi.postForm(`/api/v1/tickets/${ticketId}/attachments`, fd);
        root.CasagbiApi.showToast(`${picked.length} archivo(s) adjuntado(s) al caso.`, "success");
        return { ok: true, res };
      } catch (err) {
        root.CasagbiApi.showToast(err.message, "error", err.problem?.title || "Error adjuntando evidencia");
        return { ok: false };
      }
    }

    async function handleTransition(ticketId, body, opts = {}) {
      const files = opts.files || [];
      if (files.length) {
        const uploaded = await handleUploadAttachments(ticketId, files, body.comment || "");
        if (!uploaded.ok) return false;
      }
      if (!body.new_status || body.new_status === "__ATTACH_ONLY__") {
        await onReloadAndOpen?.(ticketId, { subtab: opts.subtab || "manage" });
        return true;
      }
      const res = await postVersionedAction(
        `/api/v1/tickets/${ticketId}/transition`,
        body,
        `Ticket actualizado a ${body.new_status}`,
        "Error de transición",
        true
      );
      if (res) await onReloadAndOpen?.(ticketId, { subtab: opts.subtab || "manage" });
      return Boolean(res);
    }

    async function handleReassign(ticketId, body, opts = {}) {
      const res = await postVersionedAction(
        `/api/v1/tickets/${ticketId}/reassign`,
        body,
        "Ticket reasignado manteniendo SLA.",
        "Error",
        false
      );
      if (res) await onReloadAndOpen?.(ticketId, { subtab: opts.subtab || "manage" });
      return Boolean(res);
    }

    async function handleAdjustPriority(ticketId, body, opts = {}) {
      const res = await postVersionedAction(
        `/api/v1/tickets/${ticketId}/priority`,
        body,
        "Prioridad OR-03 ajustada con justificación en bitácora.",
        "Error ajustando prioridad",
        false
      );
      if (res) await onReloadAndOpen?.(ticketId, { subtab: opts.subtab || "manage" });
      return Boolean(res);
    }

    async function handleRateClose(ticketId, body, opts = {}) {
      const res = await postVersionedAction(
        `/api/v1/tickets/${ticketId}/rate`,
        body,
        "Cierre confirmado y calificación registrada.",
        "Error",
        true
      );
      if (res) await onReloadAndOpen?.(ticketId, { subtab: opts.subtab || "summary" });
      return Boolean(res);
    }

    function handleProposeKbArticle(ticket) {
      window.dispatchEvent(new CustomEvent("casagbi:propose-kb", { detail: { ticket } }));
    }

    return {
      readCustomSavedViews,
      saveCustomView,
      renderCustomSavedViewsSelect,
      updateSavedViewChips,
      handleUploadAttachments,
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
