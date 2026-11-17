/**
 * Store global minimalista (solo sesión, tema, notificaciones) y caché corta de respuestas del servidor.
 */
(function (root) {
  const initialState = {
    theme: "light",
    notifications: [],
    unreadCount: 0,
    sidebarCollapsed: false,
  };

  let state = { ...initialState };
  const listeners = new Set();
  const serverCache = new Map();

  function getState() {
    return state;
  }

  function setState(partial) {
    state = { ...state, ...(partial || {}) };
    listeners.forEach((fn) => {
      try {
        fn(state);
      } catch {
        /* ignore subscriber error */
      }
    });
  }

  function subscribe(fn) {
    listeners.add(fn);
    return () => listeners.delete(fn);
  }

  function getCache(key, nowMs = Date.now()) {
    const entry = serverCache.get(key);
    if (!entry) return null;
    if (entry.expiresAt <= nowMs) {
      serverCache.delete(key);
      return null;
    }
    return entry.data;
  }

  function setCache(key, data, ttlMs = 30000, nowMs = Date.now()) {
    serverCache.set(key, {
      data,
      expiresAt: nowMs + Math.max(0, Number(ttlMs || 0)),
    });
  }

  function invalidateCache(prefix = "") {
    if (!prefix) {
      serverCache.clear();
      return;
    }
    Array.from(serverCache.keys()).forEach((k) => {
      if (String(k).startsWith(prefix)) serverCache.delete(k);
    });
  }

  function getListenerCount() {
    return listeners.size;
  }

  const api = {
    getState,
    setState,
    subscribe,
    getCache,
    setCache,
    invalidateCache,
    getListenerCount,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
  root.CasagbiReactiveStore = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
