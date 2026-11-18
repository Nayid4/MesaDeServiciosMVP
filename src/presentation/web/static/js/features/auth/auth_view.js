/**
 * Vista Dumb de Autenticación: cambio de vistas (login/recuperar/registro), validación visual y toggles.
 * Sin llamadas fetch ni WebSocket.
 */
(function (root) {
  const MODE_META = {
    login: {
      heading: "Acceso institucional UPC",
      subtitle: "Ingresa con tu cuenta institucional para continuar al espacio de servicios TIC.",
      focusId: "login-email",
    },
    forgot: {
      heading: "Recupera tu acceso",
      subtitle: "Te guiaremos para restablecer la contraseña asociada a tu correo institucional.",
      focusId: "forgot-email",
    },
    register: {
      heading: "Crea tu cuenta institucional",
      subtitle: "Completa tus datos para solicitar acceso a los servicios de la Mesa TIC.",
      focusId: "reg-name",
    },
  };

  const EYE_OPEN_SVG =
    '<svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" /><circle cx="12" cy="12" r="3" /></svg>';
  const EYE_CLOSED_SVG =
    '<svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M9.88 9.88a3 3 0 1 0 4.24 4.24" /><path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68" /><path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61" /><line x1="2" x2="22" y1="2" y2="22" /></svg>';

  function esc(val) {
    return root.CasagbiUtils?.escapeHtml ? root.CasagbiUtils.escapeHtml(val) : String(val ?? "");
  }

  function showAuthAlert(message, kind = "error") {
    const box = document.getElementById("login-status-banner");
    if (!box) return;
    if (!message) {
      box.classList.add("hidden");
      box.textContent = "";
      return;
    }
    const styles = {
      error: "border-red-300 bg-red-50 text-red-900",
      warning: "border-amber-300 bg-amber-50 text-amber-900",
      info: "border-emerald-300 bg-emerald-50 text-emerald-950",
    };
    box.className = `rounded-xl border px-3.5 py-2.5 text-xs leading-relaxed ${styles[kind] || styles.info}`;
    box.textContent = message;
    box.classList.remove("hidden");
  }

  function switchAuthMode(mode, focusInput = true) {
    const target = MODE_META[mode] ? mode : "login";
    const meta = MODE_META[target];
    const headingEl = document.getElementById("login-heading");
    const subEl = document.getElementById("auth-subtitle");
    if (headingEl) headingEl.textContent = meta.heading;
    if (subEl) subEl.textContent = meta.subtitle;

    [["login", "auth-view-login"], ["forgot", "auth-view-forgot"], ["register", "auth-view-register"]].forEach(([key, id]) => {
      document.getElementById(id)?.classList.toggle("hidden", key !== target);
    });

    const demoPanel = document.getElementById("demo-users-panel");
    if (demoPanel) {
      const enabled = demoPanel.getAttribute("data-demo-enabled") === "1";
      demoPanel.classList.toggle("hidden", !(enabled && target === "login"));
    }

    document.getElementById("toggle-forgot-btn")?.setAttribute("aria-expanded", String(target === "forgot"));
    document.getElementById("toggle-register-btn")?.setAttribute("aria-expanded", String(target === "register"));

    if (focusInput) document.getElementById(meta.focusId)?.focus();
  }

  function bindPasswordToggle(inputEl, toggleBtn, signal) {
    if (!inputEl || !toggleBtn) return;
    const opts = signal ? { signal } : undefined;
    toggleBtn.addEventListener("click", () => {
      const show = inputEl.type === "password";
      inputEl.type = show ? "text" : "password";
      toggleBtn.setAttribute("aria-pressed", String(show));
      toggleBtn.innerHTML = show ? EYE_CLOSED_SVG : EYE_OPEN_SVG;
    }, opts);
  }

  function validateInstitutionalEmailHint(inputEl, hintEl) {
    if (!inputEl || !hintEl) return true;
    const val = (inputEl.value || "").trim().toLowerCase();
    if (!val) {
      hintEl.textContent = "Debe pertenecer al dominio @unicesar.edu.co.";
      hintEl.className = "text-[11px] text-slate-500 mt-1.5";
      inputEl.classList.remove("border-red-500");
      return true;
    }
    if (!val.endsWith("@unicesar.edu.co") || val.startsWith("@") || val.includes(" ")) {
      hintEl.textContent = "Solo se admiten cuentas institucionales @unicesar.edu.co.";
      hintEl.className = "text-[11px] font-semibold text-red-700 mt-1.5";
      inputEl.classList.add("border-red-500");
      return false;
    }
    hintEl.textContent = "Dominio institucional UPC válido.";
    hintEl.className = "text-[11px] font-semibold text-[#006837] mt-1.5";
    inputEl.classList.remove("border-red-500");
    return true;
  }

  function validateNameHint(inputEl, hintEl) {
    if (!inputEl || !hintEl) return true;
    const val = (inputEl.value || "").trim();
    if (!val) {
      hintEl.classList.add("hidden");
      inputEl.classList.remove("border-red-500");
      return true;
    }
    if (val.length < 3) {
      hintEl.textContent = "Ingresa tu nombre completo (mínimo 3 caracteres).";
      hintEl.classList.remove("hidden");
      inputEl.classList.add("border-red-500");
      return false;
    }
    hintEl.classList.add("hidden");
    inputEl.classList.remove("border-red-500");
    return true;
  }

  function renderPasswordStrength(pw, barId, hintId, strictComplexity = false) {
    const bar = document.getElementById(barId);
    const hint = document.getElementById(hintId);
    const val = String(pw || "");
    let score = 0;
    if (val.length >= 8) score += 25;
    if (/[A-Z]/.test(val)) score += 25;
    if (/[a-z]/.test(val)) score += 25;
    if (/[0-9!@#$%^&*(),.?":{}|<>_\-+=/\\[\]]/.test(val)) score += 25;

    if (bar) {
      bar.style.width = `${val ? score : 0}%`;
      bar.className = `casagbi-strength-fill ${score >= 100 ? "bg-[#006837]" : score >= 50 ? "bg-amber-500" : "bg-red-500"}`;
    }
    if (hint) {
      if (!val) {
        hint.textContent = strictComplexity ? "Combina 8+ caracteres, mayúscula, minúscula y número o símbolo." : "Usa al menos 8 caracteres.";
        hint.className = "text-[11px] text-slate-500 mt-1";
      } else if (strictComplexity && score < 100) {
        hint.textContent = "Falta: 8+ caracteres, mayúscula, minúscula y número o símbolo.";
        hint.className = "text-[11px] font-semibold text-amber-800 mt-1";
      } else if (val.length < 8) {
        hint.textContent = `Mínimo 8 caracteres (llevas ${val.length}).`;
        hint.className = "text-[11px] font-semibold text-red-700 mt-1";
      } else {
        hint.textContent = score >= 100 ? "Contraseña robusta." : "Contraseña válida (puedes reforzarla con mayúsculas/símbolos).";
        hint.className = "text-[11px] font-semibold text-[#006837] mt-1";
      }
    }
  }

  function setSubmitting(formId, busy, idleLabel, busyLabel) {
    const btn = document.querySelector(`#${formId} button[type="submit"]`);
    if (!btn) return;
    btn.disabled = busy;
    btn.classList.toggle("opacity-70", busy);
    const span = btn.querySelector("span") || btn;
    span.textContent = busy ? busyLabel : idleLabel;
  }

  function renderDemoUsers(demoData, onQuickLogin) {
    const panel = document.getElementById("demo-users-panel");
    const grid = document.getElementById("demo-users-grid");
    if (!panel || !grid) return;

    const enabled = Boolean(demoData?.demo_mode && (demoData.users || []).length);
    panel.setAttribute("data-demo-enabled", enabled ? "1" : "0");
    if (!enabled) {
      panel.classList.add("hidden");
      return;
    }
    const isLoginVisible = !document.getElementById("auth-view-login")?.classList.contains("hidden");
    panel.classList.toggle("hidden", !isLoginVisible);

    grid.innerHTML = demoData.users
      .map(
        (u) => `
        <button type="button" data-demo-email="${esc(u.email)}" class="text-left p-2.5 rounded-xl border border-amber-200/80 bg-white hover:border-[#006837] hover:bg-emerald-50/40 transition flex items-center justify-between gap-2 cursor-pointer">
          <div class="min-w-0">
            <p class="text-xs font-bold text-slate-900 truncate">${esc(u.full_name)}</p>
            <p class="text-[10px] text-slate-600 truncate">${esc(u.role_label || u.role)}</p>
          </div>
          <span class="px-2 py-0.5 rounded-full text-[9px] font-bold bg-emerald-100 text-[#004d28] uppercase shrink-0">${esc(u.role)}</span>
        </button>`
      )
      .join("");

    grid.querySelectorAll("[data-demo-email]").forEach((btn) => {
      btn.addEventListener("click", () => onQuickLogin(btn.getAttribute("data-demo-email")));
    });
  }

  const api = {
    showAuthAlert,
    switchAuthMode,
    bindPasswordToggle,
    validateInstitutionalEmailHint,
    validateNameHint,
    renderPasswordStrength,
    setSubmitting,
    renderDemoUsers,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CasagbiAuthView = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
