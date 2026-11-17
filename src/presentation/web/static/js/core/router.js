/**
 * Enrutador cliente con guardas RBAC y gestión de ciclo de vida mount()/destroy() entre vistas.
 */
(function (root) {
  const ROLE_DEFAULT_TAB = {
    usuario: "kpis",
    tecnico: "kpis",
    coordinador: "kpis",
    director: "kpis",
    admin: "kpis",
  };

  function getAllowedTabs(role) {
    if (role === "usuario") {
      return ["kpis", "tickets", "create-ticket", "kb"];
    }
    if (role === "tecnico") {
      return ["kpis", "tickets", "create-ticket", "kb", "teams", "audit"];
    }
    if (role === "director") {
      return ["kpis", "tickets", "ml-lab", "kb", "teams", "audit"];
    }
    if (role === "coordinador" || role === "admin") {
      return ["kpis", "tickets", "create-ticket", "ml-lab", "kb", "teams", "audit"];
    }
    return ["kpis", "tickets"];
  }

  function isTabAllowed(role, tabId) {
    if (tabId === "profile" && Boolean(role)) {
      return true;
    }
    return getAllowedTabs(role).includes(tabId);
  }

  async function requireAuthOnDashboard() {
    const store = root.CasagbiAuthStore;
    if (store && store.isAuthenticated()) {
      return store.getUser();
    }
    if (root.CasagbiApi?.tryRefreshTokens) {
      const refreshed = await root.CasagbiApi.tryRefreshTokens();
      if (refreshed && store && store.isAuthenticated()) {
        return store.getUser();
      }
    }
    if (typeof window !== "undefined") {
      window.location.href = "/login";
    }
    return null;
  }

  function resolveInitialTab(role, hashStr = null) {
    const rawHash =
      hashStr !== null
        ? hashStr
        : typeof window !== "undefined" && window.location
          ? window.location.hash
          : "";
    const hash = String(rawHash || "").replace("#", "").trim();
    const allowed = getAllowedTabs(role);
    if (hash && allowed.includes(hash)) {
      return hash;
    }
    return ROLE_DEFAULT_TAB[role] || "kpis";
  }

  function createLifecycleManager() {
    const registry = new Map();
    let activeTab = null;
    let activeContainer = null;
    let mountCount = 0;
    let destroyCount = 0;

    function registerContainer(tabId, container) {
      registry.set(tabId, container);
    }

    function destroyActiveContainer() {
      if (activeContainer && typeof activeContainer.destroy === "function") {
        activeContainer.destroy();
        destroyCount += 1;
      }
      activeContainer = null;
      activeTab = null;
    }

    async function mountTab(tabId, role, context = {}) {
      if (!isTabAllowed(role, tabId)) {
        return { mounted: false, reason: "forbidden", tabId };
      }
      destroyActiveContainer();
      const target = registry.get(tabId);
      activeTab = tabId;
      if (target && typeof target.mount === "function") {
        activeContainer = target;
        mountCount += 1;
        await target.mount(context);
      }
      return { mounted: true, tabId };
    }

    function getLifecycleStats() {
      return {
        activeTab,
        mountedCount: mountCount,
        destroyedCount: destroyCount,
        registeredTabs: Array.from(registry.keys()),
      };
    }

    return {
      registerContainer,
      mountTab,
      destroyActiveContainer,
      getLifecycleStats,
    };
  }

  const defaultLifecycle = createLifecycleManager();

  const api = {
    getAllowedTabs,
    isTabAllowed,
    requireAuthOnDashboard,
    resolveInitialTab,
    createLifecycleManager,
    registerContainer: defaultLifecycle.registerContainer,
    mountTab: defaultLifecycle.mountTab,
    destroyActiveContainer: defaultLifecycle.destroyActiveContainer,
    getLifecycleStats: defaultLifecycle.getLifecycleStats,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
  root.CasagbiRouter = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
