/**
 * Contenedor Smart de Landing Page (caché corta public-summary, IntersectionObserver, FAQ, KB pública y lookup seguro).
 */
(function (root) {
  function createLandingContainer() {
    let abortCtrl = null;
    let disconnectReveal = null;
    let kbContainer = null;

    async function runLookup(code, email, otpCode = null) {
      const view = root.CasagbiLandingView;
      const normalized = (code || "").trim().toUpperCase();
      const cleanEmail = (email || "").trim().toLowerCase();
      const lookupResult = document.getElementById("public-lookup-result");
      if (!normalized || !lookupResult) return;
      if (!cleanEmail) {
        lookupResult.classList.remove("hidden");
        lookupResult.innerHTML = `<p class="text-xs text-amber-900 bg-amber-50 border border-amber-200 rounded-xl p-3">Ingresa el correo institucional asociado al radicado ${root.CasagbiApi.escapeHtml(normalized)}.</p>`;
        document.getElementById("public-lookup-email")?.focus();
        return;
      }

      lookupResult.classList.remove("hidden");
      lookupResult.innerHTML = `<p class="text-xs text-slate-600">Validando radicado ${root.CasagbiApi.escapeHtml(normalized)}...</p>`;

      try {
        const data = await root.CasagbiApi.post(
          "/api/v1/tickets/public/lookup",
          { ticket_code: normalized, email: cleanEmail, otp_code: otpCode },
          { requestKey: "landing:lookup", signal: abortCtrl?.signal }
        );

        if (data.otp_required) {
          const entered = window.prompt(
            `Se envió un código de verificación a ${data.masked_email}. Ingresa el código de 6 dígitos:`
          );
          if (entered) return runLookup(normalized, cleanEmail, entered.trim());
          lookupResult.innerHTML = `<p class="text-xs text-slate-600">Validación OTP cancelada.</p>`;
          return;
        }

        const t = data.ticket || {};
        root.CasagbiAuthStore.setGuestTicketSession(t.id, data.ticket_guest_token, data.masked_email);
        view.renderGuestLookupResult(data, async (txt) => {
          if (data.chat_read_only) return;
          try {
            await root.CasagbiTicketChatWS.sendMessage(t.id, txt);
          } catch (err) {
            root.CasagbiApi.showToast(err.message, "error", "Chat Invitado");
          }
        });

        const chatBox = document.getElementById("guest-chat-messages");
        let maxId = 0;
        const upsertGuestMsg = (m) => {
          if (!chatBox) return;
          const mid = Number(m.id || m.message_id);
          const existing = chatBox.querySelector(`[data-guest-msg-id="${mid}"]`);
          const node = view.renderGuestMessageBubble(m, data.masked_email);
          if (existing) existing.replaceWith(node);
          else {
            chatBox.appendChild(node);
            chatBox.scrollTop = chatBox.scrollHeight;
          }
          root.CasagbiTicketChatWS?.setLastMessageId(mid);
        };
        (data.messages || []).forEach((m) => {
          upsertGuestMsg(m);
          maxId = Math.max(maxId, Number(m.id || m.message_id || 0));
        });

        root.CasagbiTicketChatWS?.connect(t.id, {
          tokenOverride: data.ticket_guest_token,
          lastMessageId: maxId,
          onMessage: upsertGuestMsg,
          onMessageEdited: upsertGuestMsg,
          onMessageDeleted: upsertGuestMsg,
          onStatus: (st) => {
            const lbl = document.getElementById("guest-ws-status");
            if (lbl) lbl.textContent = data.chat_read_only ? "Solo lectura" : st.connected ? "En vivo WS" : "Reconectando...";
          },
        });
      } catch (err) {
        if (err?.name !== "AbortError") {
          view.renderLookupError(err.problem?.title || "Consulta no validada", err.message);
        }
      }
    }

    async function mount() {
      destroy();
      abortCtrl = new AbortController();
      const sig = abortCtrl.signal;
      const view = root.CasagbiLandingView;
      if (!view) return;

      disconnectReveal = root.CasagbiUtils?.setupScrollReveal ? root.CasagbiUtils.setupScrollReveal(document) : null;

      // CTA autenticado
      const authCta = document.getElementById("landing-auth-cta");
      const heroAuthBtn = document.getElementById("hero-auth-btn");
      if (root.CasagbiAuthStore?.isAuthenticated()) {
        if (authCta) {
          authCta.textContent = "Ir al Workspace";
          authCta.href = "/dashboard";
        }
        if (heroAuthBtn) {
          heroAuthBtn.textContent = "Abrir mi Workspace";
          heroAuthBtn.href = "/dashboard";
        }
      }

      document.getElementById("landing-quick-create-btn")?.addEventListener(
        "click",
        () => {
          window.location.href = root.CasagbiAuthStore?.isAuthenticated()
            ? "/dashboard#create-ticket"
            : "/login?next=/dashboard#create-ticket";
        },
        { signal: sig }
      );

      document.getElementById("hero-open-agent-btn")?.addEventListener(
        "click",
        () => {
          root.CasagbiFloatingAgent?.openPanel?.();
        },
        { signal: sig }
      );

      // Acordeón FAQ accesible
      document.querySelectorAll("[data-faq-toggle]").forEach((btn) => {
        btn.addEventListener(
          "click",
          () => {
            const targetId = btn.getAttribute("data-faq-toggle");
            const panel = document.getElementById(targetId);
            const expanded = btn.getAttribute("aria-expanded") === "true";
            btn.setAttribute("aria-expanded", String(!expanded));
            panel?.classList.toggle("hidden", expanded);
          },
          { signal: sig }
        );
      });

      // Resumen público con caché corta (30 s) y skeletons previos
      view.renderCatalogSkeleton();
      try {
        const summary = await root.CasagbiApi.get("/api/v1/tickets/public-summary", {
          requestKey: "landing:summary",
          cacheTtlMs: 30000,
          signal: sig,
        });
        view.renderPublicSummary(summary);
      } catch (err) {
        if (err?.name !== "AbortError") {
          root.CasagbiApi.showToast(err.message, "warning", "Métricas");
        }
      }

      // Base de conocimiento pública con debounce 350 ms y AbortController
      if (root.CasagbiKnowledgeBaseContainer) {
        kbContainer = root.CasagbiKnowledgeBaseContainer.createKnowledgeBaseContainer({
          getUser: () => null,
          gridId: "landing-kb-grid",
          searchInputId: "landing-kb-search",
          serviceSelectId: "landing-kb-service",
          indicatorId: "landing-kb-indicator",
          syncUrl: false,
        });
        await kbContainer.mount();
      }

      // Consulta pública segura
      const lookupInput = document.getElementById("public-lookup-input");
      const lookupEmailInput = document.getElementById("public-lookup-email");
      document.getElementById("public-lookup-form")?.addEventListener(
        "submit",
        (e) => {
          e.preventDefault();
          runLookup(lookupInput?.value, lookupEmailInput?.value);
        },
        { signal: sig }
      );
      document.querySelectorAll("[data-demo-ticket]").forEach((btn) => {
        btn.addEventListener(
          "click",
          () => {
            const code = btn.getAttribute("data-demo-ticket");
            if (lookupInput) lookupInput.value = code;
            runLookup(code, lookupEmailInput?.value);
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
      if (disconnectReveal) {
        disconnectReveal();
        disconnectReveal = null;
      }
      if (kbContainer) {
        kbContainer.destroy();
        kbContainer = null;
      }
      root.CasagbiTicketChatWS?.disconnect?.();
      root.CasagbiApi?.abortRequestKey?.("landing:summary");
      root.CasagbiApi?.abortRequestKey?.("landing:lookup");
    }

    return { mount, destroy };
  }

  const api = { createLandingContainer };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CasagbiLandingContainer = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
