/**
 * Contenedor Smart del Agente IA CASAGBI Nivel 0 (memoria de turnos, timeout 15 s,
 * selectores rápidos de aclaración/campos faltantes, borrador editable y handoff humano).
 */
(function (root) {
  const AGENT_TIMEOUT_MS = 15000;

  function createAiAgentContainer() {
    const history = [];
    let failedAttempts = 0;
    let abortCtrl = null;
    let lastUserIncidentText = "";

    function handoffToHumanForm(card = null) {
      const draft = card || {
        title: (lastUserIncidentText || "Solicitud de soporte TIC").slice(0, 75),
        description:
          lastUserIncidentText.length >= 15
            ? lastUserIncidentText
            : `${lastUserIncidentText || "Caso escalado desde Asistente IA"} — Solicita atención humana.`,
        service_name: "Equipos de Cómputo e Impresoras",
        sede: "Sede Sabanas (Valledupar)",
        location: "Bloque A",
        urgency: "Media",
      };
      root.CasagbiAuthStore?.setPendingDraft?.(draft);
      if (!root.CasagbiAuthStore?.isAuthenticated?.()) {
        root.CasagbiApi?.showToast?.(
          "Inicia sesión con tu cuenta institucional para enviar el formulario al equipo técnico.",
          "info",
          "Atención humana"
        );
        window.location.href = "/login?next=/dashboard#create-ticket";
        return;
      }
      if (window.location.pathname.startsWith("/dashboard")) {
        window.dispatchEvent(new CustomEvent("casagbi:open-create-with-draft", { detail: { draft } }));
        root.CasagbiAiAgentView?.closePanel?.();
      } else {
        window.location.href = "/dashboard#create-ticket";
      }
    }

    async function handleConfirmDraft(card, btn) {
      const view = root.CasagbiAiAgentView;
      if (!root.CasagbiAuthStore.isAuthenticated()) {
        root.CasagbiAuthStore.setPendingDraft(card);
        root.CasagbiApi.showToast(
          "Inicia sesión con tu cuenta institucional para finalizar la radicación.",
          "info",
          "Autenticación requerida"
        );
        window.location.href = "/login?next=/dashboard#create-ticket";
        return;
      }
      btn.disabled = true;
      btn.textContent = "Radicando...";
      try {
        const transcript = history.map((h) => `${h.role.toUpperCase()}: ${h.content}`).join("\n");
        const res = await root.CasagbiApi.post("/api/v1/agent/confirm-draft", {
          title: card.title,
          description: card.description,
          service_name: card.service_name,
          sede: card.sede,
          location: card.location,
          urgency: card.urgency,
          ai_suggested_service: card.service_name,
          ai_confidence: card.confidence_pct,
          transcript,
        });
        const t = res.ticket;
        btn.textContent = `Radicado: ${t.ticket_number}`;
        btn.className = "flex-1 px-3 py-1.5 rounded-lg bg-emerald-700 text-white font-semibold cursor-default";
        view.appendMessage(
          "assistant",
          `Ticket **${t.ticket_number}** radicado exitosamente y asignado a **${t.assigned_tech_email || "Mesa TIC"}** (${t.priority}, SLA ${t.sla_resolution_hours}h).`,
          { tool_invoked: "confirm_draft" },
          viewHandlers
        );
        root.CasagbiApi.showToast(`Ticket ${t.ticket_number} creado correctamente.`, "success", "Ticket radicado");
        window.dispatchEvent(new CustomEvent("casagbi:ticket-created", { detail: t }));
      } catch (err) {
        btn.disabled = false;
        btn.textContent = "Confirmar y Radicar Ticket";
        root.CasagbiApi.showToast(err.message, "error", err.problem?.title || "Error");
      }
    }

    const viewHandlers = {
      onConfirmDraft: handleConfirmDraft,
      onHandoffHuman: handoffToHumanForm,
      onSelectService: (serviceName) => {
        sendTurn(`El servicio es ${serviceName}`, { selected_service: serviceName });
      },
      onSubmitMissingFields: (fields) => {
        const msg = `Ubicación: ${fields.selected_sede}, ${fields.selected_location}. Urgencia: ${fields.selected_urgency}.`;
        sendTurn(msg, fields);
      },
      onSubmitLookupEmail: (code, email) => {
        sendTurn(`Consultar ${code} con correo ${email}`, { email });
      },
    };

    let inFlight = false;

    async function sendTurn(text, extraParams = {}) {
      const view = root.CasagbiAiAgentView;
      const clean = (text || "").trim();
      if (!clean || !view || inFlight) return;
      const simFailure = Boolean(document.getElementById("floating-ai-sim-failure")?.checked);

      inFlight = true;
      lastUserIncidentText = clean;
      const historySnapshot = history.slice(-8);
      history.push({ role: "user", content: clean });
      view.appendMessage("user", clean);
      view.setSendingState?.(true);

      const turnController = new AbortController();
      let timedOut = false;
      const timeoutId = setTimeout(() => {
        timedOut = true;
        turnController.abort();
      }, AGENT_TIMEOUT_MS);

      const onParentAbort = () => turnController.abort();
      abortCtrl?.signal?.addEventListener("abort", onParentAbort, { once: true });

      try {
        const res = await root.CasagbiApi.post(
          "/api/v1/agent/chat",
          {
            message: clean,
            simulate_failure: simFailure,
            failed_attempts: failedAttempts,
            history: historySnapshot,
            email: extraParams.email || null,
            selected_service: extraParams.selected_service || null,
            selected_sede: extraParams.selected_sede || null,
            selected_location: extraParams.selected_location || null,
            selected_urgency: extraParams.selected_urgency || null,
          },
          { requestKey: "ai-agent:turn", signal: turnController.signal }
        );
        if (res.status === "kb_matched") failedAttempts += 1;
        else if (res.status === "draft_ready") failedAttempts = 0;

        view.setSendingState?.(false);
        history.push({ role: "assistant", content: res.reply });
        view.appendMessage(
          "assistant",
          res.reply,
          {
            status: res.status,
            tool_invoked: res.tool_invoked,
            draft_card: res.draft_card,
            service_options: res.service_options,
            missing_fields: res.missing_fields,
            partial_draft: res.partial_draft,
            pending_ticket_code: res.pending_ticket_code,
            offer_manual_form: res.status === "ai_unavailable",
          },
          viewHandlers
        );
      } catch (err) {
        view.setSendingState?.(false);
        if (timedOut) {
          view.appendMessage(
            "assistant",
            "El servicio de IA tardó más de 15 segundos en responder. Preservamos tu texto para que puedas radicar directamente con el formulario.",
            { tool_invoked: "timeout_15s", offer_manual_form: true },
            viewHandlers
          );
          return;
        }
        if (err?.name !== "AbortError") {
          root.CasagbiApi.showToast(err.message, "error", err.problem?.title || "Error del Agente");
        }
      } finally {
        inFlight = false;
        view.setSendingState?.(false);
        clearTimeout(timeoutId);
        abortCtrl?.signal?.removeEventListener("abort", onParentAbort);
      }
    }

    function resetChat() {
      history.length = 0;
      failedAttempts = 0;
      lastUserIncidentText = "";
      root.CasagbiAiAgentView?.clearMessages();
      const welcome =
        "Hola, soy CASAGBI (CASAGBI Agent). Puedo ayudarte a encontrar una guía, consultar el estado de un ticket o preparar una nueva solicitud.";
      history.push({ role: "assistant", content: welcome });
      root.CasagbiAiAgentView?.renderWelcomeIntro?.(welcome, (prompt) => {
        if (prompt) sendTurn(prompt);
      });
    }

    function mount() {
      destroy();
      const panel = document.getElementById("floating-ai-panel");
      const toggle = document.getElementById("floating-ai-toggle");
      if (!panel || !toggle) return;

      abortCtrl = new AbortController();
      const sig = abortCtrl.signal;
      resetChat();

      toggle.addEventListener("click", () => root.CasagbiAiAgentView.togglePanel(), { signal: sig });
      document.getElementById("floating-ai-close")?.addEventListener(
        "click",
        () => root.CasagbiAiAgentView.closePanel(),
        { signal: sig }
      );
      document.getElementById("floating-ai-clear")?.addEventListener("click", resetChat, { signal: sig });
      document.getElementById("floating-ai-human-btn")?.addEventListener(
        "click",
        () => handoffToHumanForm(null),
        { signal: sig }
      );

      const form = document.getElementById("floating-ai-form");
      const input = document.getElementById("floating-ai-input");
      form?.addEventListener(
        "submit",
        async (e) => {
          e.preventDefault();
          const val = (input?.value || "").trim();
          if (!val) return;
          input.value = "";
          await sendTurn(val);
        },
        { signal: sig }
      );

      document.querySelectorAll("[data-open-agent-prompt]").forEach((chip) => {
        chip.addEventListener(
          "click",
          () => {
            root.CasagbiAiAgentView.openPanel();
            const msg = chip.getAttribute("data-open-agent-prompt");
            if (msg) sendTurn(msg);
          },
          { signal: sig }
        );
      });
    }

    function destroy() {
      if (abortCtrl) {
        abortCtrl.abort();
        abortCtrl = null;
      }
      root.CasagbiApi?.abortRequestKey?.("ai-agent:turn");
    }

    return {
      mount,
      destroy,
      openPanel: () => root.CasagbiAiAgentView?.openPanel(),
      sendTurn,
    };
  }

  const api = { createAiAgentContainer };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CasagbiAiAgentContainer = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
