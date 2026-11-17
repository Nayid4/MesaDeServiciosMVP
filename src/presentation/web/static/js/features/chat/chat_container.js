/**
 * Contenedor Smart del Chat Multimedia (WS efímero, polling 5 s RIC-02, delegación de audio a audio_recorder.js).
 */
(function (root) {
  function createChatContainer({ getUser }) {
    let abortCtrl = null;
    let selectedTicketId = null;
    let chatReadOnly = false;
    let replyToMessage = null;
    let pendingFiles = [];
    let recorder = null;
    let typingTimer = null;
    const hideTimers = new Set();
    const messagesById = new Map();

    function scheduleEditButtonHide(btn, delayMs) {
      const tid = setTimeout(() => {
        hideTimers.delete(tid);
        btn.remove();
      }, delayMs);
      hideTimers.add(tid);
    }

    function clearReplyBanner() {
      replyToMessage = null;
      const banner = document.getElementById("chat-reply-banner");
      const txt = document.getElementById("chat-reply-text");
      if (banner) banner.classList.add("hidden");
      if (txt) txt.textContent = "";
    }

    function upsertMessage(msg) {
      const chatBox = document.getElementById("ticket-chat-messages");
      const view = root.CasagbiChatView;
      if (!chatBox || !view) return;
      const msgId = Number(msg.id || msg.message_id);
      const existing = chatBox.querySelector(`[data-message-id="${msgId}"]`);
      const node = view.renderMessageBubble(msg, {
        user: getUser(),
        readOnly: chatReadOnly,
        messagesById,
        scheduleEditButtonHide,
        onReply: (targetMsg) => {
          replyToMessage = targetMsg;
          const banner = document.getElementById("chat-reply-banner");
          const txt = document.getElementById("chat-reply-text");
          if (banner && txt) {
            txt.textContent = `Respondiendo a ${targetMsg.sender_email}: ${String(targetMsg.message || "").slice(0, 70)}`;
            banner.classList.remove("hidden");
          }
          document.getElementById("ticket-chat-input")?.focus();
        },
        onEdit: async (targetMsg, idNum) => {
          const updatedText = window.prompt("Editar mensaje (máximo 5 minutos desde su envío):", targetMsg.message || "");
          if (updatedText === null || !updatedText.trim()) return;
          try {
            await root.CasagbiTicketChatWS.sendEdit(selectedTicketId, idNum, updatedText.trim());
          } catch (err) {
            root.CasagbiApi.showToast(err.message, "error", err.problem?.title || "No se pudo editar");
          }
        },
        onDelete: async (idNum) => {
          if (!window.confirm("¿Retirar este mensaje? El original se conservará inmutable en auditoría.")) return;
          try {
            await root.CasagbiTicketChatWS.sendDelete(selectedTicketId, idNum);
          } catch (err) {
            root.CasagbiApi.showToast(err.message, "error", err.problem?.title || "No se pudo eliminar");
          }
        },
      });
      if (existing) {
        existing.replaceWith(node);
      } else {
        chatBox.appendChild(node);
        chatBox.scrollTop = chatBox.scrollHeight;
      }
      root.CasagbiTicketChatWS?.setLastMessageId(msgId);
    }

    function connectRealtime(user, maxMsgId) {
      root.CasagbiTicketChatWS.connect(selectedTicketId, {
        lastMessageId: maxMsgId,
        onMessage: (msg) => {
          upsertMessage(msg);
          if (Number(msg.sender_id) !== Number(user.id)) root.CasagbiTicketChatWS.sendRead(selectedTicketId);
        },
        onMessageEdited: upsertMessage,
        onMessageDeleted: upsertMessage,
        onMessagesRead: (evt) => {
          (evt.message_ids || []).forEach((mid) => {
            const cached = messagesById.get(Number(mid));
            if (cached) {
              cached.is_read = true;
              cached.read_at = evt.read_at;
              upsertMessage(cached);
            }
          });
        },
        onTyping: (evt) => {
          const ind = document.getElementById("chat-typing-indicator");
          if (!ind || evt.actor_email === user.email) return;
          if (evt.is_typing) {
            ind.textContent = `${evt.full_name || evt.actor_email} está escribiendo...`;
            ind.classList.remove("hidden");
            clearTimeout(typingTimer);
            typingTimer = setTimeout(() => ind.classList.add("hidden"), 2500);
          } else {
            ind.classList.add("hidden");
          }
        },
        onStatus: (st) => {
          const pill = document.getElementById("ws-status-pill");
          const partLbl = document.getElementById("ws-participants-label");
          if (pill) {
            pill.textContent = chatReadOnly ? "Solo lectura" : st.connected ? "En vivo WS" : "Reconectando";
            pill.className = chatReadOnly
              ? "px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-slate-200 text-slate-700"
              : st.connected
                ? "px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-100 text-emerald-800"
                : "px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-amber-100 text-amber-800";
          }
          if (partLbl && Array.isArray(st.participants)) {
            partLbl.textContent = `Conectados (${st.participants.length}): ${st.participants.map((p) => p.email).join(", ")}`;
          }
        },
      });
    }

    async function mount(detail) {
      destroy();
      if (!detail?.ticket) return;
      abortCtrl = new AbortController();
      const sig = abortCtrl.signal;
      const user = getUser();
      selectedTicketId = detail.ticket.id;
      chatReadOnly = Boolean(detail.chat_read_only);

      const chatBox = document.getElementById("ticket-chat-messages");
      if (chatBox) chatBox.innerHTML = "";
      messagesById.clear();
      clearReplyBanner();
      pendingFiles = [];
      root.CasagbiChatView?.renderAttachmentsPreview([], () => {});

      let maxMsgId = 0;
      (detail.messages || []).forEach((m) => {
        upsertMessage(m);
        maxMsgId = Math.max(maxMsgId, Number(m.id || m.message_id || 0));
      });
      if (chatBox) chatBox.scrollTop = chatBox.scrollHeight;

      const chatInput = document.getElementById("ticket-chat-input");
      const chatBtn = document.getElementById("ticket-chat-send-btn");
      const attachBtn = document.getElementById("chat-attach-btn");
      const recordBtn = document.getElementById("chat-record-btn");
      if (chatInput) {
        chatInput.disabled = chatReadOnly;
        chatInput.placeholder = chatReadOnly ? "Ticket cerrado/anulado: chat en modo solo lectura" : "Escribe un mensaje en tiempo real...";
      }
      if (chatBtn) chatBtn.disabled = chatReadOnly;
      if (attachBtn) attachBtn.disabled = chatReadOnly;
      if (recordBtn) recordBtn.disabled = chatReadOnly;

      connectRealtime(user, maxMsgId);

      recorder = root.CasagbiAudioRecorder?.createAudioRecorder({
        onWarning: (msg, title) => root.CasagbiApi.showToast(msg, "warning", title),
        onError: (msg, title) => root.CasagbiApi.showToast(msg, "error", title),
        onRecordedBlob: async (file, durationSec) => {
          if (!selectedTicketId) return;
          const fd = new FormData();
          fd.append("files", file);
          fd.append("audio_duration_seconds", String(durationSec));
          fd.append("client_message_id", root.CasagbiTicketChatWS.generateClientMessageId());
          if (replyToMessage) fd.append("reply_to_message_id", String(replyToMessage.id));
          try {
            await root.CasagbiApi.postForm(`/api/v1/tickets/${selectedTicketId}/attachments`, fd);
            clearReplyBanner();
          } catch (err) {
            root.CasagbiApi.showToast(err.message, "error", err.problem?.title || "Error subiendo audio");
          }
        },
      });

      document.getElementById("chat-reply-cancel")?.addEventListener("click", clearReplyBanner, { signal: sig });
      attachBtn?.addEventListener("click", () => document.getElementById("chat-file-input")?.click(), { signal: sig });
      document.getElementById("chat-file-input")?.addEventListener("change", (e) => {
        const picked = Array.from(e.target.files || []);
        if (!picked.length) return;
        if (pendingFiles.length + picked.length > 5) {
          root.CasagbiApi.showToast("Máximo 5 archivos por mensaje.", "warning", "Límite de adjuntos");
        } else {
          pendingFiles.push(...picked);
          const refreshPreview = () => root.CasagbiChatView.renderAttachmentsPreview(pendingFiles, (idx) => {
            pendingFiles.splice(idx, 1);
            refreshPreview();
          });
          refreshPreview();
        }
        e.target.value = "";
      }, { signal: sig });

      recordBtn?.addEventListener("click", () => {
        if (selectedTicketId && !chatReadOnly) recorder?.toggle(document.getElementById("chat-audio-status"));
      }, { signal: sig });

      chatInput?.addEventListener("input", () => {
        if (selectedTicketId && !chatReadOnly) root.CasagbiTicketChatWS.sendTyping(selectedTicketId, true);
      }, { signal: sig });

      document.getElementById("ticket-chat-form")?.addEventListener("submit", async (e) => {
        e.preventDefault();
        if (!selectedTicketId || chatReadOnly) return;
        const val = (chatInput?.value || "").trim();
        try {
          if (pendingFiles.length > 0) {
            const fd = new FormData();
            pendingFiles.forEach((f) => fd.append("files", f));
            if (val) fd.append("content", val);
            fd.append("client_message_id", root.CasagbiTicketChatWS.generateClientMessageId());
            if (replyToMessage) fd.append("reply_to_message_id", String(replyToMessage.id));
            if (chatInput) chatInput.value = "";
            const res = await root.CasagbiApi.postForm(`/api/v1/tickets/${selectedTicketId}/attachments`, fd);
            if (res?.message) upsertMessage(res.message);
            pendingFiles = [];
            root.CasagbiChatView.renderAttachmentsPreview([], () => {});
            clearReplyBanner();
            return;
          }
          if (!val) return;
          if (chatInput) chatInput.value = "";
          const replyId = replyToMessage ? Number(replyToMessage.id || replyToMessage.message_id) : null;
          clearReplyBanner();
          await root.CasagbiTicketChatWS.sendMessage(selectedTicketId, val, { reply_to_message_id: replyId });
        } catch (err) {
          root.CasagbiApi.showToast(err.message, "error", err.problem?.title || "Error enviando mensaje");
        }
      }, { signal: sig });
    }

    function destroy() {
      if (abortCtrl) { abortCtrl.abort(); abortCtrl = null; }
      if (typingTimer) { clearTimeout(typingTimer); typingTimer = null; }
      hideTimers.forEach((tid) => clearTimeout(tid));
      hideTimers.clear();
      recorder?.stopAndRelease();
      recorder = null;
      root.CasagbiTicketChatWS?.disconnect?.();
      selectedTicketId = null;
    }

    return { mount, destroy };
  }

  const api = { createChatContainer };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CasagbiChatContainer = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
