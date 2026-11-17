/**
 * Vista Dumb de Autenticación (validación visual de dominio @unicesar.edu.co y estados claros).
 */
(function (root) {
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

  function validateInstitutionalEmailHint(inputEl, hintEl) {
    if (!inputEl || !hintEl) return true;
    const val = (inputEl.value || "").trim().toLowerCase();
    if (!val) {
      hintEl.textContent = "Usa tu correo @unicesar.edu.co.";
      hintEl.className = "text-[11px] text-slate-600 mt-1";
      return true;
    }
    if (!val.endsWith("@unicesar.edu.co") || val.startsWith("@")) {
      hintEl.textContent = "Solo se admiten cuentas institucionales @unicesar.edu.co.";
      hintEl.className = "text-[11px] font-semibold text-red-700 mt-1";
      return false;
    }
    hintEl.textContent = "Dominio institucional UPC válido.";
    hintEl.className = "text-[11px] font-semibold text-[#006837] mt-1";
    return true;
  }

  function setSubmitting(formId, busy, idleLabel, busyLabel) {
    const btn = document.querySelector(`#${formId} button[type="submit"]`);
    if (!btn) return;
    btn.disabled = busy;
    btn.classList.toggle("opacity-60", busy);
    btn.textContent = busy ? busyLabel : idleLabel;
  }

  function renderDemoUsers(demoData, onQuickLogin) {
    const panel = document.getElementById("demo-users-panel");
    const grid = document.getElementById("demo-users-grid");
    if (!panel || !grid) return;

    if (!demoData?.demo_mode || !(demoData.users || []).length) {
      panel.classList.add("hidden");
      return;
    }
    panel.classList.remove("hidden");
    grid.innerHTML = demoData.users
      .map(
        (u) => `
        <button type="button" data-demo-email="${esc(u.email)}" class="text-left p-3 rounded-xl border border-slate-200 hover:border-[#006837] hover:bg-emerald-50/50 transition flex items-center justify-between gap-2 cursor-pointer">
          <div>
            <p class="text-xs font-bold text-slate-900">${esc(u.full_name)}</p>
            <p class="text-[11px] text-slate-600">Perfil demo · ${esc(u.role_label || u.role)}</p>
          </div>
          <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-[#004d28] uppercase">${esc(u.role)}</span>
        </button>
      `
      )
      .join("");

    grid.querySelectorAll("[data-demo-email]").forEach((btn) => {
      btn.addEventListener("click", () => onQuickLogin(btn.getAttribute("data-demo-email")));
    });
  }

  const api = {
    showAuthAlert,
    validateInstitutionalEmailHint,
    setSubmitting,
    renderDemoUsers,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CasagbiAuthView = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
