/**
 * Contenedor Smart de Login/Registro/Recuperación (/login) con split-screen, validación @unicesar.edu.co y DEMO_MODE.
 */
(function (root) {
  const REMEMBER_EMAIL_KEY = "casagbi_remembered_email_v1";

  function createAuthContainer() {
    let abortCtrl = null;

    async function completeLogin(payload, nextPath) {
      root.CasagbiAuthStore.setSession(payload);
      root.CasagbiApi.showToast(`Bienvenido, ${payload.user.full_name}`, "success", "Sesión JWT iniciada");
      window.location.href = nextPath;
    }

    function restoreRememberedEmail(emailEl) {
      try {
        const saved = window.localStorage.getItem(REMEMBER_EMAIL_KEY);
        const chk = document.getElementById("login-remember-email");
        if (saved && emailEl) {
          emailEl.value = saved;
          if (chk) chk.checked = true;
        }
      } catch { /* ignore */ }
    }

    function persistRememberedEmail(email) {
      try {
        const chk = document.getElementById("login-remember-email");
        if (chk?.checked && email) window.localStorage.setItem(REMEMBER_EMAIL_KEY, email.trim());
        else window.localStorage.removeItem(REMEMBER_EMAIL_KEY);
      } catch { /* ignore */ }
    }

    async function mount() {
      destroy();
      abortCtrl = new AbortController();
      const sig = abortCtrl.signal;
      const view = root.CasagbiAuthView;
      if (!view) return;

      const params = new URLSearchParams(window.location.search);
      const nextPath = params.get("next") || "/dashboard";
      const expiredReason = params.get("expired");
      if (expiredReason === "inactivity") {
        view.showAuthAlert("Tu sesión se cerró automáticamente tras 30 minutos de inactividad.", "warning");
      } else if (expiredReason === "1") {
        view.showAuthAlert("Tu sesión expiró. Ingresa nuevamente con tu cuenta institucional.", "warning");
      }

      const initialMode = params.get("mode") || window.location.hash.replace("#", "") || "login";
      view.switchAuthMode(initialMode, false);

      const emailEl = document.getElementById("login-email");
      const emailHint = document.getElementById("login-email-hint");
      const forgotEmailEl = document.getElementById("forgot-email");
      const forgotHint = document.getElementById("forgot-email-hint");
      const regNameEl = document.getElementById("reg-name");
      const regNameHint = document.getElementById("reg-name-hint");
      const regEmailEl = document.getElementById("reg-email");
      const regHint = document.getElementById("reg-email-hint");
      const regPasswordEl = document.getElementById("reg-password");

      restoreRememberedEmail(emailEl);
      view.bindPasswordToggle(document.getElementById("login-password"), document.getElementById("login-password-toggle"), sig);
      view.bindPasswordToggle(regPasswordEl, document.getElementById("reg-password-toggle"), sig);

      emailEl?.addEventListener("input", () => view.validateInstitutionalEmailHint(emailEl, emailHint), { signal: sig });
      forgotEmailEl?.addEventListener("input", () => view.validateInstitutionalEmailHint(forgotEmailEl, forgotHint), { signal: sig });
      regNameEl?.addEventListener("input", () => view.validateNameHint(regNameEl, regNameHint), { signal: sig });
      regEmailEl?.addEventListener("input", () => view.validateInstitutionalEmailHint(regEmailEl, regHint), { signal: sig });
      regPasswordEl?.addEventListener("input", () => view.renderPasswordStrength(regPasswordEl.value, "reg-strength-fill", "reg-password-hint", false), { signal: sig });

      const goMode = (mode) => {
        view.showAuthAlert("");
        view.switchAuthMode(mode, true);
      };
      document.getElementById("toggle-forgot-btn")?.addEventListener("click", () => {
        if (forgotEmailEl && emailEl?.value && !forgotEmailEl.value) forgotEmailEl.value = emailEl.value;
        goMode("forgot");
      }, { signal: sig });
      document.getElementById("toggle-register-btn")?.addEventListener("click", () => goMode("register"), { signal: sig });
      document.getElementById("back-to-login-from-forgot")?.addEventListener("click", () => goMode("login"), { signal: sig });
      document.getElementById("back-to-login-from-register")?.addEventListener("click", () => goMode("login"), { signal: sig });

      document.getElementById("login-form")?.addEventListener("submit", async (e) => {
        e.preventDefault();
        view.showAuthAlert("");
        if (!emailEl?.value?.trim() || !view.validateInstitutionalEmailHint(emailEl, emailHint)) {
          view.showAuthAlert("Ingresa un correo válido del dominio @unicesar.edu.co.", "error");
          emailEl?.focus();
          return;
        }
        persistRememberedEmail(emailEl.value);
        view.setSubmitting("login-form", true, "Ingresar con cuenta institucional", "Verificando credenciales...");
        try {
          const payload = await root.CasagbiApi.post(
            "/api/v1/auth/login",
            { email: emailEl.value, password: document.getElementById("login-password").value, demo_mode: false },
            { signal: sig }
          );
          await completeLogin(payload, nextPath);
        } catch (err) {
          if (err?.name === "AbortError") return;
          const msg = err.status === 503 ? "El servicio de autenticación no está disponible temporalmente. Intenta en unos segundos." : err.message;
          view.showAuthAlert(msg, "error");
          root.CasagbiApi.showToast(msg, "error", err.problem?.title || "Error de autenticación");
        } finally {
          view.setSubmitting("login-form", false, "Ingresar con cuenta institucional", "Verificando credenciales...");
        }
      }, { signal: sig });

      document.getElementById("forgot-password-form")?.addEventListener("submit", async (e) => {
        e.preventDefault();
        view.showAuthAlert("");
        const statusBox = document.getElementById("forgot-status-msg");
        if (!forgotEmailEl?.value?.trim() || !view.validateInstitutionalEmailHint(forgotEmailEl, forgotHint)) {
          view.showAuthAlert("Ingresa un correo institucional @unicesar.edu.co válido.", "error");
          forgotEmailEl?.focus();
          return;
        }
        view.setSubmitting("forgot-password-form", true, "Enviar instrucciones de recuperación", "Enviando solicitud...");
        try {
          const res = await root.CasagbiApi.post("/api/v1/auth/password-reset/request", { email: forgotEmailEl.value }, { signal: sig });
          if (statusBox) {
            statusBox.textContent = res.message || "Si el correo existe, enviamos instrucciones válidas por 15 min.";
            if (res.demo_reset_url) {
              const link = document.createElement("a");
              link.href = res.demo_reset_url;
              link.className = "block mt-1 font-semibold underline text-[#006837]";
              link.textContent = "Abrir enlace de restablecimiento";
              statusBox.appendChild(link);
            }
            statusBox.classList.remove("hidden");
          }
        } catch (err) {
          if (err?.name !== "AbortError") view.showAuthAlert(err.message, "error");
        } finally {
          view.setSubmitting("forgot-password-form", false, "Enviar instrucciones de recuperación", "Enviando solicitud...");
        }
      }, { signal: sig });

      document.getElementById("register-form")?.addEventListener("submit", async (e) => {
        e.preventDefault();
        view.showAuthAlert("");
        if (!view.validateNameHint(regNameEl, regNameHint) || (regNameEl?.value || "").trim().length < 3) {
          view.showAuthAlert("Ingresa tu nombre completo (mínimo 3 caracteres).", "error");
          regNameEl?.focus();
          return;
        }
        if (!regEmailEl?.value?.trim() || !view.validateInstitutionalEmailHint(regEmailEl, regHint)) {
          view.showAuthAlert("El registro exige una cuenta institucional @unicesar.edu.co.", "error");
          regEmailEl?.focus();
          return;
        }
        if ((regPasswordEl?.value || "").length < 8) {
          view.showAuthAlert("La contraseña debe tener al menos 8 caracteres.", "error");
          regPasswordEl?.focus();
          return;
        }
        if (!document.getElementById("reg-privacy")?.checked) {
          view.showAuthAlert("Debes aceptar el tratamiento de datos personales (Ley 1581).", "error");
          return;
        }
        view.setSubmitting("register-form", true, "Crear cuenta institucional", "Creando cuenta...");
        try {
          const payload = await root.CasagbiApi.post(
            "/api/v1/auth/register",
            {
              full_name: regNameEl.value,
              email: regEmailEl.value,
              password: regPasswordEl.value,
              sede: document.getElementById("reg-sede").value,
              privacy_accepted: true,
            },
            { signal: sig }
          );
          await completeLogin(payload, nextPath);
        } catch (err) {
          if (err?.name === "AbortError") return;
          view.showAuthAlert(err.message, "error");
          root.CasagbiApi.showToast(err.message, "error", err.problem?.title || "Registro inválido");
        } finally {
          view.setSubmitting("register-form", false, "Crear cuenta institucional", "Creando cuenta...");
        }
      }, { signal: sig });

      try {
        const data = await root.CasagbiApi.get("/api/v1/auth/demo-users", { signal: sig });
        view.renderDemoUsers(data, async (demoEmail) => {
          try {
            const payload = await root.CasagbiApi.post("/api/v1/auth/login", { email: demoEmail, demo_mode: true }, { signal: sig });
            await completeLogin(payload, nextPath);
          } catch (err) {
            if (err?.name !== "AbortError") {
              view.showAuthAlert(err.message, "error");
              root.CasagbiApi.showToast(err.message, "error", "Error acceso demo");
            }
          }
        });
      } catch (err) {
        if (err?.name !== "AbortError") view.showAuthAlert("No fue posible consultar el estado del modo demostración.", "warning");
      }
    }

    function destroy() {
      if (abortCtrl) {
        abortCtrl.abort();
        abortCtrl = null;
      }
    }

    return { mount, destroy };
  }

  const api = { createAuthContainer };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CasagbiAuthContainer = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
