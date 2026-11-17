/**
 * Shell orquestador del Workspace CASAGBI (/dashboard).
 * Gestiona sidebar colapsable, drawer móvil, navegación RBAC, perfil y ciclo de vida mount()/destroy().
 */
document.addEventListener("DOMContentLoaded", async () => {
  let user = await window.CasagbiRouter.requireAuthOnDashboard();
  if (!user) return;

  const helpers = window.CasagbiDashboardHelpers;
  let catalog = null;

  const TAB_META = {
    kpis: { label: "Resumen", group: "workspace", icon: "grid" },
    tickets: {
      label: user.role === "usuario" ? "Mis tickets" : "Gestión de tickets",
      group: "workspace",
      icon: "tickets",
      badgeId: "sidebar-tickets-count-badge",
    },
    "create-ticket": { label: "Crear ticket", group: "workspace", icon: "create" },
    kb: { label: "Base de conocimiento", group: "workspace", icon: "kb" },
    teams: { label: "Personas y equipos", group: "management", icon: "users" },
    audit: { label: "Informes y auditoría", group: "management", icon: "activity" },
    "ml-lab": { label: "Laboratorio MLOps", group: "management", icon: "ml" },
  };
  const ALL_VIEW_IDS = [...Object.keys(TAB_META), "profile"];

  helpers.syncUserIdentityDom(user);

  const allowedTabs = window.CasagbiRouter.getAllowedTabs(user.role);
  const canCreate = allowedTabs.includes("create-ticket");
  document.getElementById("resumen-create-btn")?.classList.toggle("hidden", !canCreate);
  document.getElementById("tickets-create-btn")?.classList.toggle("hidden", !canCreate);

  const sidebar = document.getElementById("workspace-sidebar");
  const drawerBackdrop = document.getElementById("mobile-drawer-backdrop");
  const mobileMenuBtn = document.getElementById("mobile-menu-btn");

  function setMobileDrawer(open) {
    if (!sidebar || !drawerBackdrop) return;
    sidebar.classList.toggle("-translate-x-full", !open);
    drawerBackdrop.classList.toggle("hidden", !open);
    mobileMenuBtn?.setAttribute("aria-expanded", String(open));
  }

  mobileMenuBtn?.addEventListener("click", () => setMobileDrawer(Boolean(sidebar?.classList.contains("-translate-x-full"))));
  drawerBackdrop?.addEventListener("click", () => setMobileDrawer(false));
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && sidebar && !sidebar.classList.contains("-translate-x-full")) setMobileDrawer(false);
  });

  document.getElementById("toggle-sidebar-btn")?.addEventListener("click", () => {
    if (!sidebar) return;
    const collapsing = sidebar.classList.contains("w-64");
    sidebar.classList.toggle("w-64");
    sidebar.classList.toggle("w-16");
    sidebar.querySelectorAll(".sidebar-label").forEach((el) => el.classList.toggle("hidden"));
    document.getElementById("toggle-sidebar-btn")?.setAttribute("aria-expanded", String(!collapsing));
  });

  const nav = document.getElementById("sidebar-nav");
  helpers.renderSidebarNav(nav, allowedTabs, TAB_META);

  async function refreshSidebarOpenBadge() {
    try {
      const kpisRes = await window.CasagbiApi.get("/api/v1/analytics/kpis");
      const el = document.getElementById("sidebar-tickets-count-badge");
      if (el) el.textContent = String(Number(kpisRes.kpis?.open_tickets || 0));
    } catch { /* ignore */ }
  }

  const chatContainer = window.CasagbiChatContainer.createChatContainer({ getUser: () => user });
  const ticketsContainer = window.CasagbiTicketsContainer.createTicketsContainer({ getUser: () => user, getCatalog: () => catalog, chatContainer });
  const createTicketContainer = window.CasagbiTicketsContainer.createTicketFormContainer({
    onCreated: async (created) => {
      await refreshSidebarOpenBadge();
      await switchTab("tickets", { openTicketId: created.id, clearFilters: true });
    },
  });
  const analyticsHomeContainer = window.CasagbiAnalyticsHomeContainer.createAnalyticsHomeContainer();
  const mlLabContainer = window.CasagbiMlLaboratoryContainer.createMlLaboratoryContainer({ getUser: () => user });
  const kbContainer = window.CasagbiKnowledgeBaseContainer.createKnowledgeBaseContainer({
    getUser: () => user,
    gridId: "kb-articles-grid",
    searchInputId: "kb-search-input",
    serviceSelectId: "kb-filter-service",
    indicatorId: "kb-search-indicator",
    syncUrl: true,
  });
  const teamsContainer = helpers.createTeamsContainer({ getUser: () => user, onOpenTickets: () => switchTab("tickets") });
  const auditContainer = helpers.createAuditContainer({ getUser: () => user });
  const profileContainer = window.CasagbiProfileUsersController.createProfileContainer({
    getUser: () => user,
    onProfileUpdated: (updated) => {
      user = { ...user, ...updated };
      window.CasagbiAuthStore.setSession({ user });
      helpers.syncUserIdentityDom(user);
    },
  });

  window.CasagbiRouter.registerContainer("kpis", analyticsHomeContainer);
  window.CasagbiRouter.registerContainer("tickets", ticketsContainer);
  window.CasagbiRouter.registerContainer("create-ticket", createTicketContainer);
  window.CasagbiRouter.registerContainer("ml-lab", mlLabContainer);
  window.CasagbiRouter.registerContainer("kb", kbContainer);
  window.CasagbiRouter.registerContainer("teams", teamsContainer);
  window.CasagbiRouter.registerContainer("audit", auditContainer);
  window.CasagbiRouter.registerContainer("profile", profileContainer);

  async function switchTab(tabId, context = {}) {
    if (!window.CasagbiRouter.isTabAllowed(user.role, tabId)) return;
    window.location.hash = tabId;
    document.getElementById("topbar-breadcrumb").textContent = TAB_META[tabId]?.label || "Mi perfil";

    nav.querySelectorAll("[data-tab]").forEach((btn) => {
      const isActive = btn.getAttribute("data-tab") === tabId;
      btn.setAttribute("aria-current", isActive ? "page" : "false");
      btn.className = isActive
        ? "w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold bg-[#007A3D] text-white shadow-xs transition cursor-pointer"
        : "w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium text-slate-300 hover:bg-white/5 hover:text-white transition cursor-pointer";
      const badge = btn.querySelector("#sidebar-tickets-count-badge");
      if (badge) {
        badge.className = isActive
          ? "sidebar-label ml-auto px-2 py-0.5 rounded-full text-[11px] font-bold bg-white/20 text-white tabular-nums"
          : "sidebar-label ml-auto px-2 py-0.5 rounded-full text-[11px] font-bold bg-white/10 text-slate-300 tabular-nums";
      }
    });

    ALL_VIEW_IDS.forEach((t) => document.getElementById(`view-${t}`)?.classList.toggle("hidden", t !== tabId));
    setMobileDrawer(false);
    await window.CasagbiRouter.mountTab(tabId, user.role, context);
  }

  nav.querySelectorAll("[data-tab]").forEach((btn) => btn.addEventListener("click", () => switchTab(btn.getAttribute("data-tab"))));
  document.getElementById("topbar-profile-btn")?.addEventListener("click", () => switchTab("profile"));
  document.getElementById("sidebar-profile-btn")?.addEventListener("click", () => switchTab("profile"));
  document.getElementById("sidebar-help-btn")?.addEventListener("click", () => {
    if (allowedTabs.includes("kb")) switchTab("kb");
    else window.CasagbiAiAgentView?.openPanel?.();
  });

  document.getElementById("logout-btn")?.addEventListener("click", async () => {
    try { await window.CasagbiApi.post("/api/v1/auth/logout", { refresh_token: window.CasagbiAuthStore.getRefreshToken() || null }); } catch { /* ignore */ }
    window.CasagbiRouter.destroyActiveContainer();
    window.CasagbiApi.abortAllRequests();
    window.CasagbiAuthStore.clearSession();
    window.location.href = "/";
  });

  document.getElementById("notif-bell-btn")?.addEventListener("click", () => document.getElementById("notif-dropdown")?.classList.toggle("hidden"));
  document.getElementById("notif-prefs-toggle-btn")?.addEventListener("click", () => document.getElementById("notif-prefs-panel")?.classList.toggle("hidden"));
  document.getElementById("notif-prefs-save-btn")?.addEventListener("click", async () => {
    try {
      await window.CasagbiApi.put("/api/v1/auth/notifications/preferences", {
        notify_in_app: Boolean(document.getElementById("pref-in-app")?.checked),
        notify_ticket_updates: Boolean(document.getElementById("pref-ticket-updates")?.checked),
        notify_chat_messages: Boolean(document.getElementById("pref-chat-messages")?.checked),
        notify_sla_alerts: Boolean(document.getElementById("pref-sla-alerts")?.checked),
        notify_email_sim: Boolean(document.getElementById("pref-email-sim")?.checked),
      });
      window.CasagbiApi.showToast("Preferencias de notificación actualizadas.", "success");
      document.getElementById("notif-prefs-panel")?.classList.add("hidden");
    } catch (err) { window.CasagbiApi.showToast(err.message, "error", "Preferencias"); }
  });
  document.getElementById("notif-read-all-btn")?.addEventListener("click", async () => {
    await window.CasagbiApi.post("/api/v1/auth/notifications/read-all", {});
    await helpers.loadNotifications();
  });

  window.addEventListener("casagbi:navigate-tab", async (e) => {
    const tabId = e.detail?.tabId;
    if (tabId && window.CasagbiRouter.isTabAllowed(user.role, tabId)) await switchTab(tabId, e.detail?.context || {});
  });
  window.addEventListener("casagbi:ticket-created", async (e) => {
    await refreshSidebarOpenBadge();
    if (e.detail?.id) await switchTab("tickets", { openTicketId: e.detail.id, clearFilters: true });
  });
  window.addEventListener("casagbi:ticket-status-changed", () => refreshSidebarOpenBadge());
  window.addEventListener("casagbi:propose-kb", async (e) => {
    const t = e.detail?.ticket;
    if (!t || !allowedTabs.includes("kb")) return;
    await switchTab("kb", {
      prefillArticle: {
        source_ticket_id: t.id, title: `Guía sobre: ${t.title}`, service_name: t.service_name, symptoms: t.description || "",
        probable_cause: t.diagnosis || "Por confirmar según diagnóstico técnico.",
        solution_steps: t.solution || "1. Documentar pasos verificados en atención técnica.",
        escalation_criteria: `Escalar al área ${t.area || "técnica correspondiente"} si el síntoma persiste.`,
        keywords: `${String(t.service_name || "").toLowerCase()} ${String(t.title || "").toLowerCase()}`.slice(0, 120),
        visibility: "Pública",
      },
    });
  });
  window.addEventListener("casagbi:open-kb-search", async (e) => { if (allowedTabs.includes("kb")) await switchTab("kb", { searchCode: e.detail?.code || "" }); });
  window.addEventListener("casagbi:open-create-with-draft", async (e) => { if (allowedTabs.includes("create-ticket")) await switchTab("create-ticket", { pendingDraft: e.detail?.draft || null }); });
  window.addEventListener("pagehide", () => { window.CasagbiRouter.destroyActiveContainer(); window.CasagbiApi.abortAllRequests(); });

  catalog = await helpers.loadCatalog();
  await helpers.loadNotifications();
  const pendingDraft = window.CasagbiAuthStore.popPendingDraft();
  if (pendingDraft && allowedTabs.includes("create-ticket")) await switchTab("create-ticket", { pendingDraft });
  else await switchTab(window.CasagbiRouter.resolveInitialTab(user.role));
});
