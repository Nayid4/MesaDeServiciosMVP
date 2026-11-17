/**
 * Contenedor Smart de Login/Registro (/login) con validación @unicesar.edu.co, mensajes claros y DEMO_MODE.
 */
(function (root) {
  function createAuthContainer() {
    let abortCtrl = null;

    async function completeLogin(payload, nextPath) {
      root.CasagbiAuthStore.setSession(payload);
      root.CasagbiApi.showToast(`Bienvenido, ${payload.user.full_name}`, "success", "Sesión JWT iniciada");
      window.location.href = nextPath;
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

      const emailEl = document.getElementById("login-email");
      const emailHint = document.getElementById("login-email-hint");
      const regEmailEl = document.getElementById("reg-email");
      const regHint = document.getElementById("reg-email-hint");

      emailEl?.addEventListener("input", () => view.validateInstitutionalEmailHint(emailEl, emailHint), { signal: sig });
      regEmailEl?.addEventListener("input", () => view.validateInstitutionalEmailHint(regEmailEl, regHint), { signal: sig });

      document.getElementById("login-form")?.addEventListener(
        "submit",
        async (e) => {
          e.preventDefault();
          view.showAuthAlert("");
          if (!view.validateInstitutionalEmailHint(emailEl, emailHint)) {
            view.showAuthAlert("Ingresa un correo válido del dominio @unicesar.edu.co.", "error");
            return;
          }
          view.setSubmitting("login-form", true, "Ingresar con Cuenta Institucional", "Verificando credenciales...");
          try {
            const payload = await root.CasagbiApi.post(
              "/api/v1/auth/login",
              {
                email: emailEl.value,
                password: document.getElementById("login-password").value,
                demo_mode: false,
              },
              { signal: sig }
            );
            await completeLogin(payload, nextPath);
          } catch (err) {
            if (err?.name === "AbortError") return;
            const msg = err.status === 503
              ? "El servicio de autenticación no está disponible temporalmente. Intenta en unos segundos."
              : err.message;
            view.showAuthAlert(msg, "error");
            root.CasagbiApi.showToast(msg, "error", err.problem?.title || "Error de autenticación");
          } finally {
            view.setSubmitting("login-form", false, "Ingresar con Cuenta Institucional", "Verificando credenciales...");
          }
        },
        { signal: sig }
      );

      document.getElementById("toggle-forgot-btn")?.addEventListener(
        "click",
        () => {
          const ff = document.getElementById("forgot-password-form");
          const hidden = ff?.classList.toggle("hidden");
          const btn = document.getElementById("toggle-forgot-btn");
          if (btn) btn.setAttribute("aria-expanded", String(!hidden));
        },
        { signal: sig }
      );

      document.getElementById("forgot-password-form")?.addEventListener(
        "submit",
        async (e) => {
          e.preventDefault();
          const emailInput = document.getElementById("forgot-email");
          const statusBox = document.getElementById("forgot-status-msg");
          if (!emailInput) return;
          view.setSubmitting("forgot-password-form", true, "Enviar enlace de recuperación (15 min)", "Enviando solicitud...");
          try {
            const res = await root.CasagbiApi.post(
              "/api/v1/auth/password-reset/request",
              { email: emailInput.value },
              { signal: sig }
            );
            if (statusBox) {
              statusBox.textContent = res.message || "Si el correo existe, enviamos instrucciones válidas por 15 min.";
              if (res.demo_reset_url) {
                const link = document.createElement("a");
                link.href = res.demo_reset_url;
                link.className = "block mt-1 font-semibold underline text-[#006837]";
                link.textContent = "Abrir enlace de prueba";
                statusBox.appendChild(link);
              }
              statusBox.classList.remove("hidden");
            }
          } catch (err) {
            if (err?.name !== "AbortError") view.showAuthAlert(err.message, "error");
          } finally {
            view.setSubmitting("forgot-password-form", false, "Enviar enlace de recuperación (15 min)", "Enviando solicitud...");
          }
        },
        { signal: sig }
      );

      document.getElementById("toggle-register-btn")?.addEventListener(
        "click",
        () => {
          const rf = document.getElementById("register-form");
          const hidden = rf?.classList.toggle("hidden");
          const btn = document.getElementById("toggle-register-btn");
          if (btn) btn.setAttribute("aria-expanded", String(!hidden));
        },
        { signal: sig }
      );

      document.getElementById("register-form")?.addEventListener(
        "submit",
        async (e) => {
          e.preventDefault();
          if (!view.validateInstitutionalEmailHint(regEmailEl, regHint)) {
            view.showAuthAlert("El registro exige cuenta institucional @unicesar.edu.co.", "error");
            return;
          }
          view.setSubmitting("register-form", true, "Registrar y Entrar", "Creando cuenta...");
          try {
            const payload = await root.CasagbiApi.post(
              "/api/v1/auth/register",
              {
                full_name: document.getElementById("reg-name").value,
                email: regEmailEl.value,
                password: document.getElementById("reg-password").value,
                sede: document.getElementById("reg-sede").value,
                privacy_accepted: document.getElementById("reg-privacy").checked,
              },
              { signal: sig }
            );
            await completeLogin(payload, nextPath);
          } catch (err) {
            if (err?.name === "AbortError") return;
            view.showAuthAlert(err.message, "error");
            root.CasagbiApi.showToast(err.message, "error", err.problem?.title || "Registro inválido");
          } finally {
            view.setSubmitting("register-form", false, "Registrar y Entrar", "Creando cuenta...");
          }
        },
        { signal: sig }
      );

      try {
        const data = await root.CasagbiApi.get("/api/v1/auth/demo-users", { signal: sig });
        view.renderDemoUsers(data, async (demoEmail) => {
          try {
            const payload = await root.CasagbiApi.post(
              "/api/v1/auth/login",
              { email: demoEmail, demo_mode: true },
              { signal: sig }
            );
            await completeLogin(payload, nextPath);
          } catch (err) {
            if (err?.name !== "AbortError") {
              view.showAuthAlert(err.message, "error");
              root.CasagbiApi.showToast(err.message, "error", "Error acceso demo");
            }
          }
        });
      } catch (err) {
        if (err?.name !== "AbortError") {
          view.showAuthAlert("No fue posible consultar el estado del modo demostración.", "warning");
        }
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
