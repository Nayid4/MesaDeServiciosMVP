/**
 * Estado reactivo de sesión JWT + token de invitado por ticket + control de inactividad (30 min).
 */
window.CasagbiAuthStore = (() => {
  const ACCESS_KEY = "casagbi_access_token";
  const REFRESH_KEY = "casagbi_refresh_token";
  const USER_KEY = "casagbi_user";
  const PENDING_DRAFT_KEY = "casagbi_pending_agent_draft";
  const GUEST_TOKENS_KEY = "casagbi_guest_ticket_tokens";
  const INACTIVITY_MS = 30 * 60 * 1000; // 30 minutos (RF-01 / RNF-07)

  let inactivityTimer = null;

  function resetInactivityTimer() {
    if (inactivityTimer) clearTimeout(inactivityTimer);
    if (!isAuthenticated()) return;
    inactivityTimer = setTimeout(() => {
      clearSession();
      if (window.location.pathname.startsWith("/dashboard")) {
        window.location.href = "/login?expired=inactivity";
      }
    }, INACTIVITY_MS);
  }

  ["click", "keydown", "mousemove", "touchstart"].forEach((evt) => {
    window.addEventListener(evt, resetInactivityTimer, { passive: true });
  });

  function getAccessToken() {
    return localStorage.getItem(ACCESS_KEY) || "";
  }

  function getRefreshToken() {
    return localStorage.getItem(REFRESH_KEY) || "";
  }

  function getUser() {
    try {
      const raw = localStorage.getItem(USER_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  function setSession(payload) {
    if (payload.access_token) {
      localStorage.setItem(ACCESS_KEY, payload.access_token);
    }
    if (payload.refresh_token) {
      localStorage.setItem(REFRESH_KEY, payload.refresh_token);
    }
    if (payload.user) {
      localStorage.setItem(USER_KEY, JSON.stringify(payload.user));
    }
    resetInactivityTimer();
    window.dispatchEvent(new CustomEvent("casagbi:auth-changed", { detail: getUser() }));
  }

  function clearSession() {
    if (inactivityTimer) {
      clearTimeout(inactivityTimer);
      inactivityTimer = null;
    }
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
    window.dispatchEvent(new CustomEvent("casagbi:auth-changed", { detail: null }));
  }

  function isAuthenticated() {
    return Boolean(getAccessToken() && getUser());
  }

  function hasRole(...roles) {
    const u = getUser();
    return Boolean(u && roles.includes(u.role));
  }

  function hasPermission(perm) {
    const u = getUser();
    return Boolean(u && Array.isArray(u.permissions) && u.permissions.includes(perm));
  }

  function setGuestTicketSession(ticketId, token, maskedEmail) {
    try {
      const map = JSON.parse(sessionStorage.getItem(GUEST_TOKENS_KEY) || "{}");
      map[String(ticketId)] = { token, maskedEmail, savedAt: Date.now() };
      sessionStorage.setItem(GUEST_TOKENS_KEY, JSON.stringify(map));
    } catch {
      /* ignore storage failure */
    }
  }

  function getGuestTicketSession(ticketId) {
    try {
      const map = JSON.parse(sessionStorage.getItem(GUEST_TOKENS_KEY) || "{}");
      return map[String(ticketId)] || null;
    } catch {
      return null;
    }
  }

  function setPendingDraft(draft) {
    if (draft) {
      sessionStorage.setItem(PENDING_DRAFT_KEY, JSON.stringify(draft));
    } else {
      sessionStorage.removeItem(PENDING_DRAFT_KEY);
    }
  }

  function popPendingDraft() {
    try {
      const raw = sessionStorage.getItem(PENDING_DRAFT_KEY);
      sessionStorage.removeItem(PENDING_DRAFT_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  if (isAuthenticated()) {
    resetInactivityTimer();
  }

  return {
    getAccessToken,
    getRefreshToken,
    getUser,
    setSession,
    clearSession,
    isAuthenticated,
    hasRole,
    hasPermission,
    setGuestTicketSession,
    getGuestTicketSession,
    setPendingDraft,
    popPendingDraft,
  };
})();
