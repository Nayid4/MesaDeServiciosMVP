/**
 * Cliente WebSocket en tiempo real por ticket_id usando ticket de un solo uso (?ws_ticket=),
 * cola de reintentos con client_message_id y polling de respaldo cada 5 s (RIC-02).
 */
window.CasagbiTicketChatWS = (() => {
  let activeSocket = null;
  let activeTicketId = null;
  let activeTokenOverride = null;
  let reconnectTimer = null;
  let fallbackPollTimer = null;
  let intentionalClose = false;
  let lastKnownMessageId = 0;

  let callbacks = {};
  const pendingMessages = [];

  function generateClientMessageId() {
    if (window.crypto && typeof window.crypto.randomUUID === "function") {
      return window.crypto.randomUUID();
    }
    return `cmsg-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
  }

  function updateLastMessageId(msg) {
    const idNum = Number(msg?.id || msg?.message_id || 0);
    if (idNum > lastKnownMessageId) {
      lastKnownMessageId = idNum;
    }
  }

  async function buildSecureWsUrl(ticketId) {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const opts = activeTokenOverride ? { tokenOverride: activeTokenOverride } : {};
    const res = await window.CasagbiApi.post(`/api/v1/tickets/${ticketId}/ws-ticket`, {}, opts);
    return `${proto}//${window.location.host}/api/v1/ws/tickets/${ticketId}?ws_ticket=${encodeURIComponent(res.ws_ticket)}`;
  }

  function stopPolling() {
    if (fallbackPollTimer) {
      clearInterval(fallbackPollTimer);
      fallbackPollTimer = null;
    }
  }

  function startPolling(ticketId) {
    stopPolling();
    fallbackPollTimer = setInterval(async () => {
      if (intentionalClose || activeTicketId !== ticketId) return;
      try {
        const opts = activeTokenOverride ? { tokenOverride: activeTokenOverride } : {};
        const data = await window.CasagbiApi.get(
          `/api/v1/tickets/${ticketId}/messages?after_id=${lastKnownMessageId}`,
          opts
        );
        const list = data?.messages || [];
        if (list.length > 0) {
          list.forEach((m) => {
            updateLastMessageId(m);
            callbacks.onMessage?.(m);
          });
        }
      } catch {
        /* polling silencioso de respaldo RIC-02 */
      }
    }, 5000);
  }

  function flushPendingQueue(ticketId) {
    if (!activeSocket || activeSocket.readyState !== WebSocket.OPEN || activeTicketId !== ticketId) {
      return;
    }
    while (pendingMessages.length > 0) {
      const item = pendingMessages[0];
      try {
        activeSocket.send(JSON.stringify(item));
        pendingMessages.shift();
      } catch {
        break;
      }
    }
  }

  function disconnect() {
    intentionalClose = true;
    activeTicketId = null;
    activeTokenOverride = null;
    lastKnownMessageId = 0;
    stopPolling();
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    if (activeSocket) {
      try {
        activeSocket.close();
      } catch {
        /* ignore */
      }
      activeSocket = null;
    }
  }

  function connect(ticketId, opts = {}) {
    disconnect();
    intentionalClose = false;
    activeTicketId = ticketId;
    activeTokenOverride = opts.tokenOverride || null;
    lastKnownMessageId = Number(opts.lastMessageId || 0);
    callbacks = opts;

    startPolling(ticketId);
    openSocket();
  }

  async function openSocket() {
    const ticketId = activeTicketId;
    if (!ticketId || intentionalClose) return;

    let url = null;
    try {
      url = await buildSecureWsUrl(ticketId);
    } catch {
      if (!intentionalClose && activeTicketId === ticketId) {
        reconnectTimer = setTimeout(openSocket, 3000);
      }
      return;
    }
    if (intentionalClose || activeTicketId !== ticketId) return;

    const ws = new WebSocket(url);
    activeSocket = ws;

    ws.onopen = () => {
      callbacks.onStatus?.({ connected: true });
      flushPendingQueue(ticketId);
    };

    ws.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data);
        if (data.type === "ready" || data.type === "presence") {
          callbacks.onStatus?.({ connected: true, ...data });
        } else if (data.type === "message") {
          updateLastMessageId(data.message);
          callbacks.onMessage?.(data.message);
        } else if (data.type === "message_edited") {
          callbacks.onMessageEdited?.(data.message);
        } else if (data.type === "message_deleted") {
          callbacks.onMessageDeleted?.(data.message);
        } else if (data.type === "typing") {
          callbacks.onTyping?.(data);
        } else if (data.type === "messages_read") {
          callbacks.onMessagesRead?.(data);
        } else if (data.type === "error") {
          window.CasagbiApi.showToast(data.detail || "Error en chat", "error", "Chat de Ticket");
        }
      } catch {
        /* ignore malformed frame */
      }
    };

    ws.onclose = () => {
      callbacks.onStatus?.({ connected: false });
      if (!intentionalClose && activeTicketId === ticketId) {
        reconnectTimer = setTimeout(openSocket, 2500);
      }
    };
  }

  async function sendMessage(ticketId, content, extra = {}) {
    const clean = (content || "").trim();
    if (!clean) return false;
    const clientMessageId = extra.client_message_id || generateClientMessageId();
    const payload = {
      type: "message",
      content: clean,
      client_message_id: clientMessageId,
      reply_to_message_id: extra.reply_to_message_id ?? null,
    };

    if (activeSocket && activeSocket.readyState === WebSocket.OPEN && activeTicketId === ticketId) {
      activeSocket.send(JSON.stringify(payload));
      return true;
    }

    // Encolar y respaldar por REST para entrega inmediata aunque el WS esté reconectando
    pendingMessages.push(payload);
    try {
      const reqOpts = activeTokenOverride ? { tokenOverride: activeTokenOverride } : {};
      const res = await window.CasagbiApi.post(`/api/v1/tickets/${ticketId}/messages`, payload, reqOpts);
      const idx = pendingMessages.findIndex((p) => p.client_message_id === clientMessageId);
      if (idx >= 0) pendingMessages.splice(idx, 1);
      if (res?.message) {
        updateLastMessageId(res.message);
        callbacks.onMessage?.(res.message);
      }
    } catch (err) {
      throw err;
    }
    return true;
  }

  async function sendEdit(ticketId, messageId, content) {
    const clean = (content || "").trim();
    if (!clean) return false;
    const reqOpts = activeTokenOverride ? { tokenOverride: activeTokenOverride } : {};
    const res = await window.CasagbiApi.patch(
      `/api/v1/tickets/${ticketId}/messages/${messageId}`,
      { content: clean },
      reqOpts
    );
    if (res?.message) {
      callbacks.onMessageEdited?.(res.message);
    }
    return true;
  }

  async function sendDelete(ticketId, messageId) {
    const reqOpts = activeTokenOverride ? { tokenOverride: activeTokenOverride } : {};
    const res = await window.CasagbiApi.del(
      `/api/v1/tickets/${ticketId}/messages/${messageId}`,
      reqOpts
    );
    if (res?.message) {
      callbacks.onMessageDeleted?.(res.message);
    }
    return true;
  }

  function sendTyping(ticketId, isTyping = true) {
    if (activeSocket && activeSocket.readyState === WebSocket.OPEN && activeTicketId === ticketId) {
      activeSocket.send(JSON.stringify({ type: "typing", is_typing: Boolean(isTyping) }));
    }
  }

  function sendRead(ticketId) {
    if (activeSocket && activeSocket.readyState === WebSocket.OPEN && activeTicketId === ticketId) {
      activeSocket.send(JSON.stringify({ type: "read" }));
    }
  }

  return {
    connect,
    disconnect,
    sendMessage,
    sendEdit,
    sendDelete,
    sendTyping,
    sendRead,
    generateClientMessageId,
    setLastMessageId: (idNum) => {
      if (Number(idNum || 0) > lastKnownMessageId) lastKnownMessageId = Number(idNum);
    },
  };
})();
