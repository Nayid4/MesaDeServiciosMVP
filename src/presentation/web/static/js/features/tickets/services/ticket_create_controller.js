/**
 * Contenedor controlador de Creación de Tickets (borrador local, validación blur, KB, IA y adjuntos).
 */
(function (root) {
  const CREATE_DRAFT_STORAGE_KEY = "casagbi_create_ticket_draft_v1";

  function generateIdemKey() {
    if (window.crypto && typeof window.crypto.randomUUID === "function") return window.crypto.randomUUID();
    return `idem-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
  }

  function setFieldError(inputId, errorId, msg) {
    const input = document.getElementById(inputId);
    const errEl = document.getElementById(errorId);
    if (!input || !errEl) return true;
    if (msg) {
      errEl.textContent = msg;
      errEl.classList.remove("hidden");
      input.classList.add("border-red-500");
      input.setAttribute("aria-invalid", "true");
      return false;
    }
    errEl.textContent = "";
    errEl.classList.add("hidden");
    input.classList.remove("border-red-500");
    input.removeAttribute("aria-invalid");
    return true;
  }

  function validateField(id) {
    const val = (document.getElementById(id)?.value || "").trim();
    if (id === "ct-title") return setFieldError(id, "ct-title-error", val.length < 5 ? "El asunto debe tener al menos 5 caracteres." : "");
    if (id === "ct-desc") return setFieldError(id, "ct-desc-error", val.length < 15 ? "Detalla el problema en al menos 15 caracteres para diagnosticarlo mejor." : "");
    if (id === "ct-service") return setFieldError(id, "ct-service-error", !val ? "Selecciona un servicio TIC del catálogo." : "");
    if (id === "ct-urgency") return setFieldError(id, "ct-urgency-error", !val ? "Indica el nivel de urgencia del incidente." : "");
    if (id === "ct-sede") return setFieldError(id, "ct-sede-error", !val ? "Selecciona la sede UPC." : "");
    if (id === "ct-location") return setFieldError(id, "ct-location-error", !val ? "Selecciona la ubicación o bloque." : "");
    return true;
  }

  function createTicketFormContainer({ onCreated }) {
    let abortCtrl = null;
    let debouncedSuggest = null;
    let lastAiSuggestion = null;
    let pendingIdemKey = null;
    let createInFlight = false;
    let pendingAttachments = [];
    let previewUrls = [];

    function revokePreviewUrls() {
      previewUrls.forEach((url) => { if (url) { try { URL.revokeObjectURL(url); } catch { /* ignore */ } } });
      previewUrls = [];
    }

    function refreshAttachmentsPreview() {
      revokePreviewUrls();
      previewUrls = pendingAttachments.map((f) => (String(f.type || "").startsWith("image/") ? URL.createObjectURL(f) : ""));
      root.CasagbiTicketsView?.renderCreateAttachmentsPreview(pendingAttachments, previewUrls, (idx) => {
        pendingAttachments.splice(idx, 1);
        refreshAttachmentsPreview();
      });
    }

    function saveLocalDraft() {
      try {
        const draft = {
          title: document.getElementById("ct-title")?.value || "",
          description: document.getElementById("ct-desc")?.value || "",
          service_name: document.getElementById("ct-service")?.value || "",
          urgency: document.getElementById("ct-urgency")?.value || "Media",
          sede: document.getElementById("ct-sede")?.value || "",
          location: document.getElementById("ct-location")?.value || "",
          savedAt: new Date().toISOString(),
        };
        const hasText = Boolean(draft.title.trim() || draft.description.trim());
        const banner = document.getElementById("ct-draft-banner");
        if (hasText) {
          window.localStorage.setItem(CREATE_DRAFT_STORAGE_KEY, JSON.stringify(draft));
          banner?.classList.remove("hidden");
        } else {
          window.localStorage.removeItem(CREATE_DRAFT_STORAGE_KEY);
          banner?.classList.add("hidden");
        }
      } catch { /* ignore */ }
    }

    function restoreLocalDraft() {
      try {
        const raw = window.localStorage.getItem(CREATE_DRAFT_STORAGE_KEY);
        if (!raw) return;
        const draft = JSON.parse(raw);
        [["ct-title", draft.title], ["ct-desc", draft.description], ["ct-service", draft.service_name], ["ct-urgency", draft.urgency], ["ct-sede", draft.sede], ["ct-location", draft.location]].forEach(([id, v]) => {
          const el = document.getElementById(id);
          if (el && v) el.value = v;
        });
        if (draft.title || draft.description) document.getElementById("ct-draft-banner")?.classList.remove("hidden");
      } catch { /* ignore */ }
    }

    function clearLocalDraft() {
      try { window.localStorage.removeItem(CREATE_DRAFT_STORAGE_KEY); } catch { /* ignore */ }
      document.getElementById("ct-draft-banner")?.classList.add("hidden");
    }

    async function previewAi(showToastOnFail = true) {
      const title = document.getElementById("ct-title")?.value || "";
      const desc = document.getElementById("ct-desc")?.value || "";
      const simFail = Boolean(document.getElementById("create-sim-ai-fail")?.checked);
      const box = document.getElementById("ct-ai-preview-box");
      if ((title + desc).trim().length < 6 || !box) return;
      const esc = root.CasagbiApi.escapeHtml;
      try {
        const pred = await root.CasagbiApi.post("/api/v1/tickets/classify-preview", { title, description: desc, simulate_failure: simFail }, { requestKey: "tickets:classify", signal: abortCtrl?.signal });
        lastAiSuggestion = pred;
        if (pred.predicted_service) document.getElementById("ct-service").value = pred.predicted_service;
        if (pred.predicted_urgency) document.getElementById("ct-urgency").value = pred.predicted_urgency;
        root.CasagbiTicketsView?.renderOr03LiveEstimate?.(document.getElementById("ct-service")?.value || "", document.getElementById("ct-urgency")?.value || "Media");
        box.innerHTML = `<strong>Sugerencia IA (${esc(pred.model_name)}):</strong> Servicio <span class="font-semibold text-[#006837]">${esc(pred.predicted_service)}</span> (${Number(pred.confidence_pct).toFixed(1)}%) · Prioridad estimada <strong>${esc(pred.estimated_priority)}</strong> (SLA ${pred.estimated_sla_hours}h)`;
        root.CasagbiTicketsView?.renderCreateKbSuggestions(pred.suggested_articles || [], (code) => {
          window.dispatchEvent(new CustomEvent("casagbi:open-kb-search", { detail: { code } }));
        });
      } catch (err) {
        if (err?.name === "AbortError") return;
        lastAiSuggestion = null;
        box.innerHTML = `<span class="text-amber-800 font-semibold">${esc(err.message)}</span>`;
        if (showToastOnFail) root.CasagbiApi.showToast(err.message, "warning", err.problem?.title || "Contingencia RNF-06");
      }
    }

    async function handleCreateSubmit(form, sig) {
      const allOk = ["ct-title", "ct-desc", "ct-service", "ct-urgency", "ct-sede", "ct-location"].map(validateField).every(Boolean);
      if (!allOk || createInFlight) return;
      const submitBtn = form.querySelector('button[type="submit"]');
      const originalText = submitBtn ? submitBtn.textContent : "";
      createInFlight = true;
      if (!pendingIdemKey) pendingIdemKey = generateIdemKey();
      if (submitBtn) { submitBtn.disabled = true; submitBtn.classList.add("opacity-60", "cursor-not-allowed"); submitBtn.textContent = "Radicando..."; }
      try {
        if (pendingAttachments.length) root.CasagbiTicketsView?.setCreateUploadProgress(true, 25, "Creando radicado institucional...");
        const created = await root.CasagbiApi.post("/api/v1/tickets", {
          title: document.getElementById("ct-title").value,
          description: document.getElementById("ct-desc").value,
          service_name: document.getElementById("ct-service").value,
          urgency: document.getElementById("ct-urgency").value,
          sede: document.getElementById("ct-sede").value,
          location: document.getElementById("ct-location").value,
          ai_suggested_service: lastAiSuggestion?.predicted_service || null,
          ai_confidence: lastAiSuggestion?.confidence_pct || null,
          ai_human_validated: Boolean(lastAiSuggestion),
        }, { headers: { "Idempotency-Key": pendingIdemKey }, signal: sig });
        pendingIdemKey = null;

        if (pendingAttachments.length > 0 && created?.id) {
          root.CasagbiTicketsView?.setCreateUploadProgress(true, 65, "Subiendo adjuntos validados por firma binaria...");
          const fd = new FormData();
          pendingAttachments.forEach((f) => fd.append("files", f));
          fd.append("content", "Evidencia adjunta al momento de radicar el ticket.");
          await root.CasagbiApi.postForm(`/api/v1/tickets/${created.id}/attachments`, fd, { signal: sig });
          root.CasagbiTicketsView?.setCreateUploadProgress(true, 100, "Adjuntos cargados correctamente.");
        }
        clearLocalDraft();
        pendingAttachments = [];
        refreshAttachmentsPreview();
        root.CasagbiApi.showToast(
          created.deduplicated ? (created.notice || `Se conservó el radicado existente ${created.ticket_number}.`) : `Ticket ${created.ticket_number} asignado a ${created.assigned_tech_email || "Mesa TIC"}.`,
          created.deduplicated ? "warning" : "success",
          created.deduplicated ? "Solicitud ya radicada" : "Ticket Radicado"
        );
        form.reset();
        lastAiSuggestion = null;
        root.CasagbiTicketsView?.renderCreateKbSuggestions([], () => {});
        await onCreated?.(created);
      } catch (err) {
        if (err?.name !== "AbortError") root.CasagbiApi.showToast(err.message, "error", err.problem?.title || "Error radicando ticket");
      } finally {
        createInFlight = false;
        root.CasagbiTicketsView?.setCreateUploadProgress(false, 0, "");
        if (submitBtn) { submitBtn.disabled = false; submitBtn.classList.remove("opacity-60", "cursor-not-allowed"); submitBtn.textContent = originalText || "Confirmar y Radicar Ticket"; }
      }
    }

    async function mount(ctx = {}) {
      destroy();
      abortCtrl = new AbortController();
      const sig = abortCtrl.signal;
      pendingAttachments = [];
      refreshAttachmentsPreview();
      root.CasagbiTicketsView?.setCreateUploadProgress(false, 0, "");

      if (ctx.pendingDraft) {
        [["ct-title", ctx.pendingDraft.title], ["ct-desc", ctx.pendingDraft.description], ["ct-service", ctx.pendingDraft.service_name], ["ct-urgency", ctx.pendingDraft.urgency], ["ct-sede", ctx.pendingDraft.sede], ["ct-location", ctx.pendingDraft.location]].forEach(([id, v]) => {
          const el = document.getElementById(id);
          if (el && v) el.value = v;
        });
      } else {
        restoreLocalDraft();
      }

      const form = document.getElementById("create-ticket-form");
      debouncedSuggest = root.CasagbiUtils.debounce(() => previewAi(false), 350);

      ["ct-title", "ct-desc", "ct-service", "ct-urgency", "ct-sede", "ct-location"].forEach((id) => {
        const el = document.getElementById(id);
        el?.addEventListener("blur", () => validateField(id), { signal: sig });
        el?.addEventListener(el?.tagName === "SELECT" ? "change" : "input", () => { if (el.getAttribute("aria-invalid") === "true") validateField(id); }, { signal: sig });
      });
      ["ct-title", "ct-desc"].forEach((id) => document.getElementById(id)?.addEventListener("input", () => { saveLocalDraft(); debouncedSuggest(); }, { signal: sig }));
      form?.addEventListener("input", () => { if (!createInFlight) pendingIdemKey = null; saveLocalDraft(); }, { signal: sig });
      form?.addEventListener("change", () => { if (!createInFlight) pendingIdemKey = null; saveLocalDraft(); }, { signal: sig });

      document.getElementById("ct-clear-draft-btn")?.addEventListener("click", () => {
        clearLocalDraft();
        form?.reset();
        pendingAttachments = [];
        refreshAttachmentsPreview();
        root.CasagbiTicketsView?.renderCreateKbSuggestions([], () => {});
      }, { signal: sig });

      document.getElementById("ct-attachments-input")?.addEventListener("change", (e) => {
        const picked = Array.from(e.target.files || []);
        if (!picked.length) return;
        if (pendingAttachments.length + picked.length > 5) root.CasagbiApi.showToast("Máximo 5 archivos adjuntos al radicar.", "warning", "Límite de adjuntos");
        else { pendingAttachments.push(...picked); refreshAttachmentsPreview(); }
        e.target.value = "";
      }, { signal: sig });

      document.getElementById("ct-analyze-btn")?.addEventListener("click", () => previewAi(true), { signal: sig });
      const updateOr03Box = () => root.CasagbiTicketsView?.renderOr03LiveEstimate(document.getElementById("ct-service")?.value || "", document.getElementById("ct-urgency")?.value || "Media");
      updateOr03Box();
      document.getElementById("ct-service")?.addEventListener("change", updateOr03Box, { signal: sig });
      document.getElementById("ct-urgency")?.addEventListener("change", updateOr03Box, { signal: sig });
      document.getElementById("ct-open-ai-helper-btn")?.addEventListener("click", () => root.CasagbiAiAgentView?.openPanel?.(), { signal: sig });
      document.getElementById("ct-toggle-sla-table-btn")?.addEventListener("click", (e) => {
        const panel = document.getElementById("ct-sla-table-panel");
        if (panel) e.currentTarget?.setAttribute("aria-expanded", String(!panel.classList.toggle("hidden")));
      }, { signal: sig });
      form?.addEventListener("submit", async (e) => { e.preventDefault(); await handleCreateSubmit(form, sig); }, { signal: sig });
    }

    function destroy() {
      if (debouncedSuggest?.cancel) { debouncedSuggest.cancel(); debouncedSuggest = null; }
      if (abortCtrl) { abortCtrl.abort(); abortCtrl = null; }
      revokePreviewUrls();
      root.CasagbiApi?.abortRequestKey?.("tickets:classify");
    }

    return { mount, destroy };
  }

  const api = { createTicketFormContainer };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CasagbiTicketCreateController = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
