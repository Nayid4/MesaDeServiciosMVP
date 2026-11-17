/**
 * Controladores de Perfil Propio (#view-profile) y Directorio Paginado de Usuarios (RBAC Admin/Coordinador).
 */
(function (root) {
  function computeStrength(pw) {
    let score = 0;
    if (pw.length >= 8) score += 25;
    if (/[A-Z]/.test(pw)) score += 25;
    if (/[0-9]/.test(pw)) score += 25;
    if (/[^A-Za-z0-9]/.test(pw)) score += 25;
    return score;
  }

  function createProfileContainer({ getUser, onProfileUpdated }) {
    let abortCtrl = null;

    function fillFields(u) {
      if (!u) return;
      const setVal = (id, v) => { const el = document.getElementById(id); if (el) el.value = v || ""; };
      setVal("profile-full-name", u.full_name);
      setVal("profile-email", u.email);
      setVal("profile-role", u.role_label || u.role);
      setVal("profile-sede", u.sede);
      setVal("profile-area", u.area || "General");
    }

    async function mount() {
      destroy();
      abortCtrl = new AbortController();
      const sig = abortCtrl.signal;
      fillFields(getUser());

      try {
        const res = await root.CasagbiApi.get("/api/v1/users/me", { requestKey: "users:me", signal: sig });
        const profile = res?.user || res;
        if (profile?.email) {
          fillFields(profile);
          onProfileUpdated?.(profile);
        }
      } catch (err) {
        if (err?.name !== "AbortError") root.CasagbiApi.showToast(err.message, "warning", "Perfil");
      }

      document.getElementById("profile-new-password")?.addEventListener("input", (e) => {
        const bar = document.getElementById("profile-strength-fill");
        if (!bar) return;
        const pct = computeStrength(e.target.value || "");
        bar.style.width = `${pct}%`;
        bar.className = "casagbi-strength-fill " + (pct >= 75 ? "bg-[#006837]" : pct >= 50 ? "bg-amber-500" : "bg-red-500");
      }, { signal: sig });

      document.getElementById("profile-form")?.addEventListener("submit", async (e) => {
        e.preventDefault();
        try {
          const res = await root.CasagbiApi.request("/api/v1/users/me/profile", {
            method: "PATCH",
            body: {
              full_name: document.getElementById("profile-full-name")?.value?.trim(),
              sede: document.getElementById("profile-sede")?.value,
            },
            signal: sig,
          });
          const updated = res?.user || res;
          if (updated?.email) onProfileUpdated?.(updated);
          root.CasagbiApi.showToast("Datos institucionales actualizados.", "success");
        } catch (err) {
          if (err?.name !== "AbortError") root.CasagbiApi.showToast(err.message, "error", "Actualizar perfil");
        }
      }, { signal: sig });

      document.getElementById("profile-password-form")?.addEventListener("submit", async (e) => {
        e.preventDefault();
        const cur = document.getElementById("profile-current-password")?.value || "";
        const nw = document.getElementById("profile-new-password")?.value || "";
        const cf = document.getElementById("profile-new-password-confirm")?.value || "";
        if (nw !== cf) {
          root.CasagbiApi.showToast("Las contraseñas nuevas no coinciden.", "error", "Validación");
          return;
        }
        try {
          await root.CasagbiApi.post("/api/v1/users/me/password", { current_password: cur, new_password: nw }, { signal: sig });
          root.CasagbiApi.showToast("Contraseña actualizada correctamente.", "success");
          e.target.reset();
          const bar = document.getElementById("profile-strength-fill");
          if (bar) bar.style.width = "0%";
        } catch (err) {
          if (err?.name !== "AbortError") root.CasagbiApi.showToast(err.message, "error", "Cambio de contraseña");
        }
      }, { signal: sig });
    }

    function destroy() {
      abortCtrl?.abort();
      abortCtrl = null;
      root.CasagbiApi?.abortRequestKey?.("users:me");
    }

    return { mount, destroy };
  }

  function createAdminUsersController({ getUser }) {
    let page = 1;
    const pageSize = 10;
    let debounced = null;

    async function loadUsers(sig) {
      const user = getUser();
      const section = document.getElementById("admin-users-section");
      const tbody = document.getElementById("admin-users-tbody");
      if (!section || !tbody) return;
      const canView = ["admin", "coordinador", "director"].includes(user?.role);
      const isAdmin = user?.role === "admin";
      section.classList.toggle("hidden", !canView);
      if (!canView) return;

      const q = (document.getElementById("admin-users-search")?.value || "").trim();
      const role = (document.getElementById("admin-users-role")?.value || "").trim();
      const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
      if (q) params.set("q", q);
      if (role) params.set("role", role);

      root.CasagbiSkeleton?.tableRows(tbody, 5, 4);
      try {
        const res = await root.CasagbiApi.get(`/api/v1/users?${params.toString()}`, { requestKey: "admin:users", signal: sig });
        const rows = res.items || [];
        const esc = root.CasagbiApi.escapeHtml;
        tbody.innerHTML = rows.length
          ? rows.map((u) => {
              const roles = ["usuario", "tecnico", "coordinador", "director", "admin"]
                .map((r) => `<option value="${r}" ${u.role === r ? "selected" : ""}>${esc(r)}</option>`)
                .join("");
              return `<tr>
                <td class="px-4 py-2.5"><p class="font-semibold text-slate-900">${esc(u.full_name)}</p><p class="text-[11px] font-mono text-slate-600">${esc(u.email)}</p></td>
                <td class="px-4 py-2.5 text-slate-700">${esc(u.sede || "--")}</td>
                <td class="px-4 py-2.5"><select data-user-role-id="${u.id}" ${isAdmin ? "" : "disabled"} aria-label="Rol de ${esc(u.email)}" class="px-2 py-1 rounded-lg border border-slate-200 bg-white text-xs disabled:opacity-60">${roles}</select></td>
                <td class="px-4 py-2.5"><span class="casagbi-status-pill ${u.is_active ? "casagbi-status-pill--ok" : "casagbi-status-pill--danger"}">${u.is_active ? "Activo" : "Inactivo"}</span></td>
                <td class="px-4 py-2.5 text-right">${isAdmin ? `<button type="button" data-user-toggle-id="${u.id}" data-user-active="${u.is_active ? "1" : "0"}" class="px-2.5 py-1 rounded-lg border border-slate-200 hover:bg-slate-100 text-[11px] font-semibold cursor-pointer">${u.is_active ? "Desactivar" : "Activar"}</button>` : '<span class="text-[11px] text-slate-500">Solo lectura</span>'}</td>
              </tr>`;
            }).join("")
          : '<tr><td colspan="5" class="px-4 py-6 text-center text-slate-600">Sin cuentas coincidentes.</td></tr>';

        tbody.querySelectorAll("[data-user-role-id]").forEach((sel) => {
          sel.addEventListener("change", async () => {
            const uid = Number(sel.getAttribute("data-user-role-id"));
            try {
              await root.CasagbiApi.request(`/api/v1/users/${uid}`, { method: "PATCH", body: { role: sel.value }, signal: sig });
              root.CasagbiApi.showToast("Rol actualizado en bitácora.", "success");
              await loadUsers(sig);
            } catch (err) {
              if (err?.name !== "AbortError") { root.CasagbiApi.showToast(err.message, "error", "Actualizar rol"); await loadUsers(sig); }
            }
          }, { signal: sig });
        });

        tbody.querySelectorAll("[data-user-toggle-id]").forEach((btn) => {
          btn.addEventListener("click", async () => {
            const uid = Number(btn.getAttribute("data-user-toggle-id"));
            const active = btn.getAttribute("data-user-active") === "1";
            try {
              await root.CasagbiApi.request(`/api/v1/users/${uid}`, { method: "PATCH", body: { is_active: !active }, signal: sig });
              root.CasagbiApi.showToast("Estado de usuario actualizado.", "success");
              await loadUsers(sig);
            } catch (err) {
              if (err?.name !== "AbortError") root.CasagbiApi.showToast(err.message, "error", "Actualizar usuario");
            }
          }, { signal: sig });
        });

        const pagEl = document.getElementById("admin-users-pagination");
        if (pagEl && root.CasagbiPagination) {
          root.CasagbiPagination.render(pagEl, {
            page: res.page || 1,
            pages: res.pages || 1,
            total: res.total || 0,
            pageSize: res.page_size || pageSize,
            onPageChange: (next) => { page = next; loadUsers(sig); },
          });
        }
      } catch (err) {
        if (err?.name !== "AbortError") root.CasagbiApi.showToast(err.message, "error", "Directorio de usuarios");
      }
    }

    async function mount(sig) {
      page = 1;
      debounced = root.CasagbiUtils.debounce(() => { page = 1; loadUsers(sig); }, 300);
      document.getElementById("admin-users-search")?.addEventListener("input", () => debounced(), { signal: sig });
      document.getElementById("admin-users-role")?.addEventListener("change", () => { page = 1; loadUsers(sig); }, { signal: sig });
      await loadUsers(sig);
    }

    function destroy() {
      debounced?.cancel?.();
      debounced = null;
      root.CasagbiApi?.abortRequestKey?.("admin:users");
    }

    return { mount, destroy };
  }

  const api = { createProfileContainer, createAdminUsersController };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CasagbiProfileUsersController = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
