/**
 * Interceptor HTTP Fetch con auto-refresh JWT, AbortController por clave de búsqueda,
 * caché GET corta y manejo estándar RFC 7807 Problem Details.
 */
window.CasagbiApi = (() => {
  let refreshPromise = null;
  const activeControllers = new Map();

  function showToast(message, kind = "info", title = "") {
    if (window.CasagbiToast?.show) {
      window.CasagbiToast.show(message, kind, title);
      return;
    }
    const host = document.getElementById("casagbi-toast-container");
    if (!host) return;
    const colors = {
      success: "border-emerald-300 bg-emerald-50 text-emerald-950",
      error: "border-red-300 bg-red-50 text-red-950",
      warning: "border-amber-300 bg-amber-50 text-amber-950",
      info: "border-slate-200 bg-white text-slate-900",
    };
    const card = document.createElement("div");
    card.setAttribute("role", kind === "error" ? "alert" : "status");
    card.className = `pointer-events-auto border rounded-xl p-3.5 shadow-lg text-xs leading-relaxed transition ${colors[kind] || colors.info}`;
    card.innerHTML = `
      ${title ? `<p class="font-semibold mb-0.5">${escapeHtml(title)}</p>` : ""}
      <p>${escapeHtml(message)}</p>
    `;
    host.appendChild(card);
    setTimeout(() => {
      card.classList.add("opacity-0");
      setTimeout(() => card.remove(), 220);
    }, 4500);
  }

  function escapeHtml(str) {
    if (window.CasagbiUtils?.escapeHtml) {
      return window.CasagbiUtils.escapeHtml(str);
    }
    return String(str ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  async function tryRefreshTokens() {
    const refreshToken = window.CasagbiAuthStore.getRefreshToken();
    if (!refreshToken) return false;
    if (refreshPromise) return refreshPromise;

    refreshPromise = (async () => {
      try {
        const res = await fetch("/api/v1/auth/refresh", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (!res.ok) {
          window.CasagbiAuthStore.clearSession();
          return false;
        }
        const data = await res.json();
        window.CasagbiAuthStore.setSession(data);
        return true;
      } catch {
        return false;
      } finally {
        refreshPromise = null;
      }
    })();

    return refreshPromise;
  }

  function abortRequestKey(requestKey) {
    const prev = activeControllers.get(requestKey);
    if (prev) {
      try {
        prev.abort();
      } catch {
        /* ignore */
      }
      activeControllers.delete(requestKey);
    }
  }

  function abortAllRequests() {
    Array.from(activeControllers.keys()).forEach((k) => abortRequestKey(k));
  }

  async function request(path, options = {}, retry = true) {
    const {
      tokenOverride,
      requestKey,
      cancelPrevious = true,
      cacheTtlMs = 0,
      signal: externalSignal,
      rawResponse = false,
      ...fetchOptions
    } = options;

    const method = (fetchOptions.method || "GET").toUpperCase();
    const cacheKey = `${method}:${path}`;

    if (method === "GET" && cacheTtlMs > 0 && window.CasagbiReactiveStore) {
      const cached = window.CasagbiReactiveStore.getCache(cacheKey);
      if (cached !== null) return cached;
    }

    let localController = null;
    let effectiveSignal = externalSignal;
    if (requestKey) {
      if (cancelPrevious) abortRequestKey(requestKey);
      localController = new AbortController();
      activeControllers.set(requestKey, localController);
      if (externalSignal) {
        if (externalSignal.aborted) {
          localController.abort();
        } else {
          externalSignal.addEventListener("abort", () => localController.abort(), { once: true });
        }
      }
      effectiveSignal = localController.signal;
    }

    const headers = new Headers(fetchOptions.headers || {});
    if (!headers.has("Content-Type") && !(fetchOptions.body instanceof FormData)) {
      headers.set("Content-Type", "application/json");
    }
    const token = tokenOverride || window.CasagbiAuthStore.getAccessToken();
    if (token && !headers.has("Authorization")) {
      headers.set("Authorization", `Bearer ${token}`);
    }

    let res;
    try {
      res = await fetch(path, { ...fetchOptions, headers, signal: effectiveSignal });
    } finally {
      if (requestKey && activeControllers.get(requestKey) === localController) {
        activeControllers.delete(requestKey);
      }
    }

    if (res.status === 401 && retry && !tokenOverride && !path.includes("/auth/login") && !path.includes("/auth/refresh")) {
      const refreshed = await tryRefreshTokens();
      if (refreshed) {
        return request(path, options, false);
      }
      window.CasagbiAuthStore.clearSession();
      if (window.location.pathname.startsWith("/dashboard")) {
        window.location.href = "/login?expired=1";
      }
    }

    if (!res.ok) {
      const contentType = res.headers.get("content-type") || "";
      const errBody = contentType.includes("json") ? await res.json() : await res.text();
      const problem =
        typeof errBody === "object" && errBody !== null
          ? errBody
          : { title: "Error HTTP", detail: String(errBody), status: res.status };
      const err = new Error(problem.detail || problem.title || "Error de comunicación");
      err.problem = problem;
      err.status = problem.status || res.status;
      throw err;
    }

    if (rawResponse) {
      return res;
    }

    const contentType = res.headers.get("content-type") || "";
    const body = contentType.includes("json") ? await res.json() : await res.text();

    if (method === "GET" && cacheTtlMs > 0 && window.CasagbiReactiveStore) {
      window.CasagbiReactiveStore.setCache(cacheKey, body, cacheTtlMs);
    } else if (method !== "GET" && window.CasagbiReactiveStore) {
      window.CasagbiReactiveStore.invalidateCache("GET:/api/v1/tickets");
      window.CasagbiReactiveStore.invalidateCache("GET:/api/v1/analytics");
    }

    return body;
  }

  async function downloadFile(path, fallbackFilename = "reporte", extraOptions = {}) {
    const res = await request(path, { ...extraOptions, method: "GET", rawResponse: true });
    const blob = await res.blob();
    const disp = res.headers.get("content-disposition") || "";
    const match = disp.match(/filename="?([^"]+)"?/i);
    const filename = match ? match[1] : fallbackFilename;
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    return filename;
  }

  return {
    request,
    get: (path, extraOptions = {}) => request(path, { ...extraOptions, method: "GET" }),
    post: (path, data, extraOptions = {}) =>
      request(path, { ...extraOptions, method: "POST", body: JSON.stringify(data || {}) }),
    put: (path, data, extraOptions = {}) =>
      request(path, { ...extraOptions, method: "PUT", body: JSON.stringify(data || {}) }),
    patch: (path, data, extraOptions = {}) =>
      request(path, { ...extraOptions, method: "PATCH", body: JSON.stringify(data || {}) }),
    del: (path, extraOptions = {}) =>
      request(path, { ...extraOptions, method: "DELETE" }),
    postForm: (path, formData, extraOptions = {}) =>
      request(path, { ...extraOptions, method: "POST", body: formData }),
    downloadFile,
    abortRequestKey,
    abortAllRequests,
    getActiveRequestsCount: () => activeControllers.size,
    showToast,
    escapeHtml,
    tryRefreshTokens,
  };
})();
