/**
 * Utilidades puras de cliente: debounce 350 ms, fechas America/Bogota, URL state,
 * contadores animados, reveal por scroll y escape XSS.
 */
(function (root) {
  function escapeHtml(str) {
    return String(str ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function debounce(fn, delayMs = 350) {
    let timerId = null;
    let lastArgs = null;
    let lastThis = null;

    function debounced(...args) {
      lastArgs = args;
      lastThis = this;
      if (timerId !== null) {
        clearTimeout(timerId);
      }
      timerId = setTimeout(() => {
        timerId = null;
        const invokeArgs = lastArgs;
        const invokeThis = lastThis;
        lastArgs = null;
        lastThis = null;
        fn.apply(invokeThis, invokeArgs);
      }, delayMs);
    }

    debounced.cancel = () => {
      if (timerId !== null) {
        clearTimeout(timerId);
        timerId = null;
      }
      lastArgs = null;
      lastThis = null;
    };

    debounced.flush = () => {
      if (timerId !== null) {
        clearTimeout(timerId);
        timerId = null;
        const invokeArgs = lastArgs || [];
        const invokeThis = lastThis;
        lastArgs = null;
        lastThis = null;
        return fn.apply(invokeThis, invokeArgs);
      }
      return undefined;
    };

    debounced.isPending = () => timerId !== null;
    return debounced;
  }

  function formatBogotaDate(isoString, { includeTime = true } = {}) {
    if (!isoString) return "--";
    const dt = new Date(isoString);
    if (Number.isNaN(dt.getTime())) return String(isoString);
    const opts = {
      timeZone: "America/Bogota",
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    };
    if (includeTime) {
      opts.hour = "2-digit";
      opts.minute = "2-digit";
      opts.hour12 = false;
    }
    return new Intl.DateTimeFormat("es-CO", opts).format(dt);
  }

  function formatRelativeTime(isoString, nowMs = Date.now()) {
    if (!isoString) return "";
    const dt = new Date(isoString);
    if (Number.isNaN(dt.getTime())) return "";
    const diffSec = Math.round((nowMs - dt.getTime()) / 1000);
    if (diffSec < 60) return "hace un momento";
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `hace ${diffMin} min`;
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return `hace ${diffHr} h`;
    const diffDays = Math.floor(diffHr / 24);
    return `hace ${diffDays} d`;
  }

  function readUrlParams(searchStr = null) {
    const raw =
      searchStr !== null
        ? searchStr
        : typeof window !== "undefined" && window.location
          ? window.location.search
          : "";
    const params = new URLSearchParams(raw);
    const out = {};
    params.forEach((value, key) => {
      out[key] = value;
    });
    return out;
  }

  function syncUrlParams(paramsObj) {
    if (typeof window === "undefined" || !window.history || !window.location) return;
    const params = new URLSearchParams(window.location.search);
    Object.entries(paramsObj || {}).forEach(([k, v]) => {
      if (v === null || v === undefined || String(v).trim() === "") {
        params.delete(k);
      } else {
        params.set(k, String(v).trim());
      }
    });
    const qs = params.toString();
    const nextUrl = `${window.location.pathname}${qs ? `?${qs}` : ""}${window.location.hash || ""}`;
    window.history.replaceState(null, "", nextUrl);
  }

  function prefersReducedMotion() {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return false;
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function animateCounter(element, targetNumber, { durationMs = 260, suffix = "", decimals = 0 } = {}) {
    if (!element) return;
    const target = Number(targetNumber || 0);
    if (prefersReducedMotion() || typeof requestAnimationFrame !== "function") {
      element.textContent = `${target.toFixed(decimals)}${suffix}`;
      return;
    }
    const start = performance.now();
    function step(now) {
      const progress = Math.min(1, (now - start) / durationMs);
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = target * eased;
      element.textContent = `${current.toFixed(decimals)}${suffix}`;
      if (progress < 1) {
        requestAnimationFrame(step);
      } else {
        element.textContent = `${target.toFixed(decimals)}${suffix}`;
      }
    }
    requestAnimationFrame(step);
  }

  function setupScrollReveal(scope = null) {
    const doc = scope || (typeof document !== "undefined" ? document : null);
    if (!doc) return () => {};
    const targets = Array.from(doc.querySelectorAll(".casagbi-reveal"));
    if (!targets.length) return () => {};

    if (prefersReducedMotion() || typeof IntersectionObserver === "undefined") {
      targets.forEach((el) => el.classList.add("is-visible"));
      return () => {};
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("is-visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.08, rootMargin: "0px 0px -24px 0px" }
    );
    targets.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }

  const api = {
    escapeHtml,
    debounce,
    formatBogotaDate,
    formatRelativeTime,
    readUrlParams,
    syncUrlParams,
    prefersReducedMotion,
    animateCounter,
    setupScrollReveal,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
  root.CasagbiUtils = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
