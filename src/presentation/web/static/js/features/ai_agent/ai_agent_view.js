/**
 * Vista Dumb del Widget Flotante de Agente IA (delegando tarjetas interactivas a ai_draft_card.js).
 */
(function (root) {
  function esc(val) {
    return root.CasagbiUtils?.escapeHtml ? root.CasagbiUtils.escapeHtml(val) : String(val ?? "");
  }

  function formatRichText(text) {
    return esc(text || "")
      .replace(/\*\*(.+?)\*\*/g, "<strong class='font-semibold text-slate-900'>$1</strong>")
      .replace(/(^|[^*])\*([^*]+?)\*(?!\*)/g, "$1<em class='italic text-slate-600'>$2</em>")
      .replace(/`([^`]+)`/g, "<code class='px-1 py-0.5 rounded bg-slate-200/70 text-slate-800 text-[11px] font-mono'>$1</code>")
      .replace(/\n/g, "<br/>");
  }

  function createLookupEmailElement(pendingCode, handlers) {
    const box = document.createElement("form");
    box.className = "w-full rounded-xl border border-slate-200 bg-white p-2.5 text-xs space-y-2";
    box.innerHTML = `
      <label class="block text-[11px] font-medium text-slate-700">Correo institucional del titular para <span class="font-mono text-[#006837]">${esc(pendingCode)}</span></label>
      <div class="flex gap-1.5">
        <input type="email" required placeholder="usuario@unicesar.edu.co" class="lk-email flex-1 px-2.5 py-1.5 rounded-lg border border-slate-300 text-[11px]" />
        <button type="submit" class="px-3 py-1.5 rounded-lg bg-[#006837] text-white text-[11px] font-semibold cursor-pointer">Validar</button>
      </div>`;
    box.addEventListener("submit", (e) => {
      e.preventDefault();
      const email = box.querySelector(".lk-email")?.value?.trim();
      if (email) handlers.onSubmitLookupEmail?.(pendingCode, email);
    });
    return box;
  }

  function createManualFormElement(handlers) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "px-3 py-1.5 rounded-lg border border-[#006837] bg-white hover:bg-emerald-50 text-[#006837] text-[11px] font-semibold cursor-pointer";
    btn.textContent = "Abrir formulario manual (Hablar con una persona)";
    btn.addEventListener("click", () => handlers.onHandoffHuman?.(null));
    return btn;
  }

  function appendMessage(role, content, meta = {}, rawHandlers = null) {
    const container = document.getElementById("floating-ai-messages");
    if (!container) return;
    const handlers = typeof rawHandlers === "function" ? { onConfirmDraft: rawHandlers } : rawHandlers || {};
    const draftUi = root.CasagbiAiDraftCard;

    const wrapper = document.createElement("div");
    wrapper.className = (role === "user" ? "flex justify-end" : "flex flex-col items-start gap-2") + " casagbi-msg-enter";

    const bubble = document.createElement("div");
    bubble.className = role === "user"
      ? "max-w-[85%] rounded-2xl rounded-br-sm bg-[#006837] text-white px-3.5 py-2.5 text-xs leading-relaxed shadow-sm"
      : "max-w-[92%] rounded-2xl rounded-bl-sm bg-white border border-slate-200 text-slate-700 px-3.5 py-2.5 text-xs leading-relaxed shadow-xs";

    if (role === "assistant" && meta.tool_invoked) {
      const badge = document.createElement("div");
      badge.className = "mb-1.5 inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-full bg-emerald-50 text-[#006837] border border-emerald-200";
      badge.textContent = `Tool: ${meta.tool_invoked}`;
      bubble.appendChild(badge);
      const txt = document.createElement("div");
      txt.innerHTML = formatRichText(content);
      bubble.appendChild(txt);
    } else {
      bubble.innerHTML = role === "user" ? esc(content) : formatRichText(content);
    }
    wrapper.appendChild(bubble);

    if (role === "assistant") {
      if (meta.status === "needs_clarification" && handlers.onSelectService && draftUi) {
        wrapper.appendChild(draftUi.createClarifyServiceElement(meta.service_options, handlers));
      } else if (meta.status === "needs_missing_fields" && handlers.onSubmitMissingFields && draftUi) {
        wrapper.appendChild(draftUi.createMissingFieldsElement(meta.missing_fields, meta.partial_draft, handlers));
      } else if (meta.status === "lookup_needs_email" && handlers.onSubmitLookupEmail) {
        wrapper.appendChild(createLookupEmailElement(meta.pending_ticket_code, handlers));
      } else if (meta.offer_manual_form && handlers.onHandoffHuman) {
        wrapper.appendChild(createManualFormElement(handlers));
      }
      if (meta.draft_card && handlers.onConfirmDraft && draftUi) {
        wrapper.appendChild(draftUi.createDraftCardElement(meta.draft_card, handlers));
      }
    }

    container.appendChild(wrapper);
    container.scrollTop = container.scrollHeight;
  }

  function renderWelcomeIntro(welcomeText, onChipSelect) {
    const container = document.getElementById("floating-ai-messages");
    if (!container) return;
    const section = document.createElement("div");
    section.className = "space-y-3 casagbi-msg-enter";
    section.innerHTML = `<p class="text-[11px] font-bold tracking-wider uppercase text-[#006837]">PUNTO ÚNICO DE CONTACTO</p>
      <div class="rounded-2xl border border-slate-200/90 bg-white px-4 py-3.5 text-[13px] text-slate-700 leading-relaxed shadow-xs">${formatRichText(welcomeText)}</div>`;

    const chips = [
      { label: "Consultar radicado", prompt: "Quiero consultar el estado de un ticket" },
      { label: "Wi-Fi Eduroam", prompt: "No puedo conectar a Wi-Fi Eduroam en mi portátil" },
      { label: "Crear solicitud", prompt: "Necesito crear un ticket de soporte TIC" },
    ];
    const chipRow = document.createElement("div");
    chipRow.className = "flex flex-wrap gap-2";
    chips.forEach((chip) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.setAttribute("data-agent-chip", chip.prompt);
      btn.className = "px-3.5 py-1.5 rounded-full border border-emerald-200 bg-emerald-50/75 hover:bg-emerald-100 text-[#006837] text-xs font-medium transition cursor-pointer";
      btn.textContent = chip.label;
      btn.addEventListener("click", () => onChipSelect?.(chip.prompt));
      chipRow.appendChild(btn);
    });
    section.appendChild(chipRow);
    container.appendChild(section);
    container.scrollTop = container.scrollHeight;
  }

  function setSendingState(isSending) {
    const container = document.getElementById("floating-ai-messages");
    const sendBtn = document.getElementById("floating-ai-send-btn");
    const input = document.getElementById("floating-ai-input");
    if (sendBtn) sendBtn.disabled = Boolean(isSending);
    if (input) input.disabled = Boolean(isSending);
    if (!container) return;
    const existing = container.querySelector("#floating-ai-loading-indicator");
    if (isSending && !existing) {
      const loader = document.createElement("div");
      loader.id = "floating-ai-loading-indicator";
      loader.className = "flex items-center gap-2 text-xs text-slate-600 px-2 py-1";
      loader.innerHTML = '<span class="w-2 h-2 rounded-full bg-[#006837] animate-pulse"></span><span>Consultando base de conocimiento e IA...</span>';
      container.appendChild(loader);
      container.scrollTop = container.scrollHeight;
    } else if (!isSending && existing) {
      existing.remove();
    }
  }

  const api = {
    appendMessage,
    renderWelcomeIntro,
    setSendingState,
    clearMessages() {
      const container = document.getElementById("floating-ai-messages");
      if (container) container.innerHTML = "";
    },
    openPanel() {
      document.getElementById("floating-ai-panel")?.classList.remove("hidden");
      document.getElementById("floating-ai-input")?.focus();
    },
    togglePanel() {
      const panel = document.getElementById("floating-ai-panel");
      if (!panel) return;
      panel.classList.toggle("hidden");
      if (!panel.classList.contains("hidden")) document.getElementById("floating-ai-input")?.focus();
    },
    closePanel() {
      document.getElementById("floating-ai-panel")?.classList.add("hidden");
    },
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CasagbiAiAgentView = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
