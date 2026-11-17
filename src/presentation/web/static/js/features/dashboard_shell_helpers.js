/**
 * Ayudantes modulares del shell Dashboard (sidebar RBAC, catálogo, notificaciones, equipos y auditoría).
 */
(function (root) {
  function getInitials(name) {
    const parts = String(name || "UPC").trim().split(/\s+/).filter(Boolean);
    if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
    return String(name || "UP").slice(0, 2).toUpperCase();
  }

  function formatGreetingDate() {
    try {
      return new Intl.DateTimeFormat("es-CO", { timeZone: "America/Bogota", weekday: "long", day: "numeric", month: "long" }).format(new Date());
    } catch {
      return "hoy";
    }
  }

  function syncUserIdentityDom(u) {
    if (!u) return;
    const ini = getInitials(u.full_name || u.email);
    const first = String(u.full_name || "Equipo").trim().split(/\s+/)[0];
    const setText = (id, text) => { const el = document.getElementById(id); if (el) el.textContent = text; };
    setText("sidebar-user-initials", ini);
    setText("sidebar-user-name", u.full_name);
    setText("sidebar-user-area", u.area || u.role_label || u.role);
    setText("sidebar-user-email", u.email);
    setText("topbar-user-initials", ini);
    setText("topbar-user-name", u.full_name);
    setText("topbar-role-badge", u.role_label || u.role);
    setText("topbar-sede-badge", u.sede || "UPC");
    setText("resumen-greeting", `Hola, ${first}`);
    setText("resumen-date-subtitle", `Este es el estado de la mesa de servicios hoy, ${formatGreetingDate()}.`);
  }

  function renderSidebarNav(nav, allowedTabs, tabMeta) {
    const esc = root.CasagbiApi.escapeHtml;
    const workspaceTabs = allowedTabs.filter((t) => tabMeta[t]?.group === "workspace");
    const managementTabs = allowedTabs.filter((t) => tabMeta[t]?.group === "management");
    const renderBtn = (tab) => {
      const m = tabMeta[tab];
      const iconHtml = root.CasagbiIcons ? root.CasagbiIcons.svg(m.icon, "w-4 h-4 shrink-0") : "";
      const badgeHtml = m.badgeId ? `<span id="${m.badgeId}" class="sidebar-label ml-auto px-2 py-0.5 rounded-full text-[11px] font-bold bg-white/10 text-slate-300 tabular-nums">0</span>` : "";
      return `<button type="button" data-tab="${tab}" class="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium text-slate-300 hover:bg-white/5 hover:text-white transition cursor-pointer">${iconHtml}<span class="sidebar-label truncate">${esc(m.label)}</span>${badgeHtml}</button>`;
    };
    let html = '<p class="sidebar-label px-3 pb-1 text-[10px] font-bold tracking-[0.12em] uppercase text-slate-300">ESPACIO DE TRABAJO</p>' + workspaceTabs.map(renderBtn).join("");
    if (managementTabs.length) html += '<p class="sidebar-label px-3 pt-4 pb-1 text-[10px] font-bold tracking-[0.12em] uppercase text-slate-300">GESTIÓN</p>' + managementTabs.map(renderBtn).join("");
    nav.innerHTML = html;
  }

  async function loadCatalog() {
    const esc = root.CasagbiApi.escapeHtml;
    const catalog = await root.CasagbiApi.get("/api/v1/tickets/catalog", { cacheTtlMs: 60000 });
    const fillSelect = (id, items, defaultLabel = null) => {
      const el = document.getElementById(id);
      if (!el || !items) return;
      const opts = defaultLabel ? [`<option value="">${esc(defaultLabel)}</option>`] : [];
      items.forEach((it) => { const v = typeof it === "string" ? it : it.service_name; opts.push(`<option value="${esc(v)}">${esc(v)}</option>`); });
      el.innerHTML = opts.join("");
    };
    fillSelect("filter-status", catalog.statuses, "Todos los estados");
    fillSelect("filter-priority", catalog.priorities, "Todas las prioridades");
    fillSelect("filter-sede", catalog.sedes, "Todas las sedes");
    fillSelect("filter-service", catalog.services, "Todos los servicios");
    fillSelect("ct-service", catalog.services);
    fillSelect("ct-sede", catalog.sedes);
    fillSelect("ct-location", catalog.locations);
    fillSelect("kpi-filter-sede", catalog.sedes, "Todas las sedes");
    fillSelect("kpi-filter-service", catalog.services, "Todos los servicios");
    fillSelect("kpi-filter-priority", catalog.priorities, "Todas las prioridades");
    fillSelect("kb-service", catalog.services);
    fillSelect("kb-filter-service", catalog.services, "Todos los servicios TIC");
    fillSelect("kb-category-topic", catalog.kb_categories || []);
    fillSelect("kb-filter-category", catalog.kb_categories || [], "Todas las categorías");
    fillSelect("kb-filter-status", catalog.kb_statuses || [], "Todos los estados");
    fillSelect("kb-filter-visibility", catalog.kb_visibilities || [], "Toda visibilidad");
    return catalog;
  }

  async function loadNotifications() {
    const esc = root.CasagbiApi.escapeHtml;
    try {
      const me = await root.CasagbiApi.get("/api/v1/auth/me");
      if (me.user) root.CasagbiAuthStore.setSession({ user: me.user });
      const badge = document.getElementById("notif-badge");
      if (badge) {
        badge.textContent = String(me.unread_count || 0);
        badge.classList.toggle("hidden", !(me.unread_count > 0));
      }
      const prefs = me.notification_preferences || {};
      [["pref-in-app", prefs.notify_in_app], ["pref-ticket-updates", prefs.notify_ticket_updates], ["pref-chat-messages", prefs.notify_chat_messages], ["pref-sla-alerts", prefs.notify_sla_alerts], ["pref-email-sim", prefs.notify_email_sim]].forEach(([id, v]) => {
        const el = document.getElementById(id);
        if (el) el.checked = v !== false;
      });
      const list = document.getElementById("notif-list");
      if (!list) return;
      list.innerHTML = (me.notifications || []).length
        ? me.notifications.slice(0, 15).map((n) => `<button type="button" data-notif-id="${n.id}" class="w-full text-left p-2.5 rounded-xl transition cursor-pointer ${n.is_read ? "bg-slate-50 hover:bg-slate-100" : "bg-emerald-50 border border-emerald-200 hover:bg-emerald-100/70"}"><div class="flex items-center justify-between gap-2"><p class="font-semibold text-slate-800">${esc(n.title)}</p>${n.is_read ? "" : '<span class="w-2 h-2 rounded-full bg-[#006837] shrink-0"></span>'}</div><p class="text-[11px] text-slate-600 mt-0.5">${esc(n.message)}</p></button>`).join("")
        : '<p class="text-slate-600 text-center py-3">Sin notificaciones nuevas.</p>';
      list.querySelectorAll("[data-notif-id]").forEach((btn) => btn.addEventListener("click", async () => {
        try { await root.CasagbiApi.post(`/api/v1/auth/notifications/${Number(btn.getAttribute("data-notif-id"))}/read`, {}); await loadNotifications(); } catch { /* ignore */ }
      }));
    } catch { /* ignore */ }
  }

  function createTeamsContainer({ getUser, onOpenTickets }) {
    let abortCtrl = null;
    let adminUsersCtrl = null;
    async function loadTeams() {
      const esc = root.CasagbiApi.escapeHtml;
      const grid = document.getElementById("teams-grid");
      const note = document.getElementById("teams-scope-note");
      if (grid && root.CasagbiSkeletons) grid.innerHTML = root.CasagbiSkeletons.renderKpiSkeleton(3);
      try {
        const res = await root.CasagbiApi.get("/api/v1/analytics/kpis", { requestKey: "teams:kpis", signal: abortCtrl?.signal });
        const workload = res.technician_workload || [];
        if (note) note.textContent = getUser().role === "tecnico" ? "Vista de técnicos activos. Nota: el conteo operativo en tu perfil refleja únicamente tus tickets asignados (RF-22)." : `${workload.length} técnico(s) activos registrados en la Mesa de Servicios TIC UPC.`;
        if (!grid) return;
        grid.innerHTML = workload.length
          ? workload.map((w) => `<article class="bg-white rounded-2xl border border-slate-200/80 p-5 casagbi-shadow-card space-y-4"><div class="flex items-start justify-between gap-3"><div class="flex items-center gap-3 min-w-0"><span class="w-10 h-10 rounded-full bg-emerald-50 border border-emerald-200 text-[#006837] text-xs font-bold flex items-center justify-center shrink-0">${esc(getInitials(w.full_name || w.email))}</span><div class="min-w-0"><h2 class="text-sm font-bold text-slate-900 truncate">${esc(w.full_name)}</h2><p class="text-[11px] font-mono text-slate-600 truncate">${esc(w.email)}</p></div></div><span class="px-2.5 py-0.5 rounded-full bg-emerald-50 text-[#006837] border border-emerald-200 text-[10px] font-semibold shrink-0">Activo</span></div><div class="grid grid-cols-2 gap-2 text-xs"><div class="p-2.5 rounded-xl bg-slate-50 border border-slate-100"><span class="block text-[11px] text-slate-600">Área técnica</span><span class="font-semibold text-slate-800 truncate block">${esc(w.area || "Mesa TIC")}</span></div><div class="p-2.5 rounded-xl bg-slate-50 border border-slate-100"><span class="block text-[11px] text-slate-600">Sede</span><span class="font-semibold text-slate-800 truncate block">${esc(w.sede || "UPC")}</span></div></div><div class="flex items-center justify-between pt-2 border-t border-slate-100 text-xs"><div class="flex items-center gap-4"><span><strong class="text-[#006837] tabular-nums">${Number(w.open_tickets || 0)}</strong> <span class="text-slate-600">abiertos</span></span><span><strong class="text-slate-900 tabular-nums">${Number(w.resolved_tickets || 0)}</strong> <span class="text-slate-600">resueltos</span></span></div><button type="button" data-teams-open-tickets="1" class="text-xs font-bold text-[#006837] hover:underline cursor-pointer">Ver tickets</button></div></article>`).join("")
          : `<div class="col-span-full">${root.CasagbiEmptyErrorState ? root.CasagbiEmptyErrorState.renderEmptyState({ title: "No hay técnicos activos registrados", detail: "No se encontraron cuentas técnicas activas en el alcance actual." }) : "Sin técnicos activos."}</div>`;
        grid.querySelectorAll("[data-teams-open-tickets]").forEach((btn) => btn.addEventListener("click", () => onOpenTickets?.()));
      } catch (err) {
        if (err?.name !== "AbortError") root.CasagbiApi.showToast(err.message, "error", "Personas y equipos");
      }
    }
    return {
      async mount() {
        abortCtrl = new AbortController();
        document.getElementById("teams-refresh-btn")?.addEventListener("click", loadTeams, { signal: abortCtrl.signal });
        await loadTeams();
        adminUsersCtrl = root.CasagbiProfileUsersController?.createAdminUsersController({ getUser });
        await adminUsersCtrl?.mount(abortCtrl.signal);
      },
      destroy() {
        abortCtrl?.abort();
        abortCtrl = null;
        adminUsersCtrl?.destroy();
        adminUsersCtrl = null;
        root.CasagbiApi?.abortRequestKey?.("teams:kpis");
      },
    };
  }

  function createAuditContainer({ getUser }) {
    let abortCtrl = null;
    async function exportReport(format) {
      try {
        const fname = await root.CasagbiApi.downloadFile(`/api/v1/analytics/export.${format}`, `informe_casagbi_riu10.${format}`);
        root.CasagbiApi.showToast(`Reporte ${fname} descargado (RIU-10).`, "success");
      } catch (err) { root.CasagbiApi.showToast(err.message, "error", "Error exportando informe"); }
    }
    async function loadLogs() {
      const esc = root.CasagbiApi.escapeHtml;
      const canView = ["coordinador", "admin"].includes(getUser().role);
      const notice = document.getElementById("audit-restricted-notice");
      const card = document.getElementById("audit-table-card");
      if (!canView) {
        if (notice) { notice.classList.remove("hidden"); notice.textContent = "La bitácora inmutable de auditoría del sistema está restringida por RBAC (RNF-09) a los roles Coordinador y Administrador. Desde aquí puedes descargar tus informes operativos oficiales RIU-10 en formato CSV o PDF."; }
        card?.classList.add("hidden");
        return;
      }
      notice?.classList.add("hidden");
      card?.classList.remove("hidden");
      const tbody = document.getElementById("audit-logs-tbody");
      if (tbody && root.CasagbiSkeletons) tbody.innerHTML = root.CasagbiSkeletons.renderTableSkeleton(5, 5);
      try {
        const res = await root.CasagbiApi.get("/api/v1/analytics/audit-logs?limit=150", { requestKey: "audit:logs", signal: abortCtrl?.signal });
        const rows = res.logs || [];
        if (tbody) {
          tbody.innerHTML = rows.length
            ? rows.map((r) => `<tr><td class="px-4 py-2 font-mono text-[11px] text-slate-600">${esc(root.CasagbiUtils?.formatBogotaDate ? root.CasagbiUtils.formatBogotaDate(r.timestamp) : String(r.timestamp).slice(0, 19))}</td><td class="px-4 py-2 font-mono">${esc(r.user_email)}</td><td class="px-4 py-2 font-semibold text-[#006837]">${esc(r.action)}</td><td class="px-4 py-2">${esc(r.entity)}:${esc(r.entity_id)}</td><td class="px-4 py-2 text-slate-600">${esc(r.new_value || r.old_value || "")}</td></tr>`).join("")
            : '<tr><td colspan="5" class="px-4 py-6 text-center text-slate-600">Sin eventos de auditoría.</td></tr>';
        }
      } catch (err) { if (err?.name !== "AbortError") root.CasagbiApi.showToast(err.message, "error", "Bitácora"); }
    }
    return {
      async mount() {
        abortCtrl = new AbortController();
        document.getElementById("audit-refresh-btn")?.addEventListener("click", loadLogs, { signal: abortCtrl.signal });
        document.getElementById("audit-export-csv-btn")?.addEventListener("click", () => exportReport("csv"), { signal: abortCtrl.signal });
        document.getElementById("audit-export-pdf-btn")?.addEventListener("click", () => exportReport("pdf"), { signal: abortCtrl.signal });
        await loadLogs();
      },
      destroy() { abortCtrl?.abort(); abortCtrl = null; root.CasagbiApi?.abortRequestKey?.("audit:logs"); },
    };
  }

  const api = { syncUserIdentityDom, renderSidebarNav, loadCatalog, loadNotifications, createTeamsContainer, createAuditContainer };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CasagbiDashboardHelpers = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
