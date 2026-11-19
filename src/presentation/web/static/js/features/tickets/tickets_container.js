/**
 * Contenedor Smart de Bandeja, Carga del Equipo y Detalle Dedicado de Tickets.
 */
(function (root) {
  function createTicketsContainer({ getUser, getCatalog, chatContainer }) {
    let abortCtrl = null;
    let debouncedSearch = null;
    let selectedTicketId = null;
    let currentDetail = null;
    let activeDetailSubtab = "summary";
    let currentPage = 1;
    const pageSize = 10;
    let unassignedOnly = false;
    let slaRiskOnly = false;
    let activePreset = "all";
    let actionsCtrl = null;

    function setSearching(active) {
      document.getElementById("tickets-search-indicator")?.classList.toggle("hidden", !active);
    }

    function applyUrlFilters() {
      const urlParams = root.CasagbiUtils?.readUrlParams ? root.CasagbiUtils.readUrlParams() : {};
      [["filter-search", "q"], ["filter-status", "status"], ["filter-priority", "priority"], ["filter-sede", "sede"], ["filter-service", "service_name"], ["filter-sort", "sort_by"]].forEach(([id, key]) => {
        const el = document.getElementById(id);
        if (el && urlParams[key] !== undefined) el.value = urlParams[key];
      });
      if (urlParams.page && Number(urlParams.page) >= 1) currentPage = Number(urlParams.page);
    }

    function closeTicketDetail({ syncUrl = true } = {}) {
      selectedTicketId = null;
      currentDetail = null;
      activeDetailSubtab = "summary";
      root.CasagbiApi?.abortRequestKey?.("tickets:detail");
      chatContainer?.destroy?.();
      root.CasagbiTicketsView?.showListShell();
      if (syncUrl && typeof window !== "undefined") {
        if (window.location.pathname.startsWith("/tickets/")) {
          window.history.replaceState(null, "", "/dashboard#tickets");
        } else {
          root.CasagbiUtils?.syncUrlParams({ ticket_id: "" });
        }
      }
    }

    async function loadTickets(resetPage = false) {
      const view = root.CasagbiTicketsView;
      if (!view) return;
      if (resetPage) currentPage = 1;

      const q = (document.getElementById("filter-search")?.value || "").trim();
      const status = document.getElementById("filter-status")?.value || "";
      const priority = document.getElementById("filter-priority")?.value || "";
      const sede = document.getElementById("filter-sede")?.value || "";
      const serviceName = document.getElementById("filter-service")?.value || "";
      const sortBy = document.getElementById("filter-sort")?.value || "priority_asc_deadline_asc";

      root.CasagbiUtils?.syncUrlParams({ q, status, priority, sede, service_name: serviceName, sort_by: sortBy, page: currentPage });
      setSearching(true);
      view.renderTicketsLoading();

      const params = new URLSearchParams();
      if (q) params.set("q", q);
      if (status) params.set("status", status);
      if (priority) params.set("priority", priority);
      if (sede) params.set("sede", sede);
      if (serviceName) params.set("service_name", serviceName);
      if (unassignedOnly) params.set("unassigned_only", "true");
      if (slaRiskOnly) params.set("sla_risk_only", "true");
      params.set("sort_by", sortBy);
      params.set("page", String(currentPage));
      params.set("page_size", String(pageSize));

      try {
        const res = await root.CasagbiApi.get(`/api/v1/tickets?${params.toString()}`, {
          requestKey: "tickets:list",
          signal: abortCtrl?.signal,
        });
        view.renderSummaryBanner(res.summary || {});
        view.renderCoordinatorWorkload(res.technician_loads || []);
        view.renderTicketsTable(res.tickets || [], selectedTicketId, (tid) => openTicketDetail(tid));
        view.renderPagination(
          res.page || 1,
          res.total_pages || res.pages || 1,
          res.total || 0,
          res.page_size || pageSize,
          (nextPage) => { currentPage = nextPage; loadTickets(false); }
        );
      } catch (err) {
        if (err?.name === "AbortError") return;
        view.renderTicketsError(err.message, () => loadTickets(false));
        root.CasagbiApi.showToast(err.message, "error", "Error cargando tickets");
      } finally {
        setSearching(false);
      }
    }

    async function openTicketDetail(ticketId, opts = {}) {
      if (Number(selectedTicketId) !== Number(ticketId)) activeDetailSubtab = "summary";
      if (opts.subtab) activeDetailSubtab = opts.subtab;
      selectedTicketId = ticketId;
      const view = root.CasagbiTicketsView;
      view?.renderDetailLoading();
      root.CasagbiUtils?.syncUrlParams({ ticket_id: ticketId });
      document.getElementById("main-content")?.scrollTo({ top: 0, behavior: "auto" });

      try {
        const detail = await root.CasagbiApi.get(`/api/v1/tickets/${ticketId}`, {
          requestKey: "tickets:detail",
          signal: abortCtrl?.signal,
        });
        currentDetail = detail;
        view.renderTicketDetail(
          detail,
          getUser(),
          getCatalog(),
          {
            onTransition: (tid, body, o) => actionsCtrl.handleTransition(tid, body, o),
            onReassign: (tid, body, o) => actionsCtrl.handleReassign(tid, body, o),
            onAdjustPriority: (tid, body, o) => actionsCtrl.handleAdjustPriority(tid, body, o),
            onRateClose: (tid, body, o) => actionsCtrl.handleRateClose(tid, body, o),
            onProposeKbArticle: (t) => actionsCtrl.handleProposeKbArticle(t),
            onSubtabChange: (tab) => { activeDetailSubtab = tab; },
          },
          { subtab: activeDetailSubtab }
        );
        if (chatContainer) await chatContainer.mount(detail);
      } catch (err) {
        if (err?.name !== "AbortError") {
          root.CasagbiApi.showToast(err.message, "error", err.problem?.title || "Detalle de ticket");
          closeTicketDetail();
        }
      }
    }

    function applyPresetView(preset) {
      const setVal = (id, val) => { const el = document.getElementById(id); if (el) el.value = val; };
      unassignedOnly = false;
      slaRiskOnly = false;
      activePreset = preset;
      if (preset === "all") { setVal("filter-status", ""); setVal("filter-priority", ""); setVal("filter-search", ""); }
      else if (preset === "my-active") { setVal("filter-status", "En atención"); setVal("filter-priority", ""); }
      else if (preset === "unassigned") { setVal("filter-status", "Registrado"); unassignedOnly = true; }
      else if (preset === "sla-risk") { setVal("filter-status", ""); setVal("filter-priority", ""); slaRiskOnly = true; }
      else if (preset === "resolved") { setVal("filter-status", "Resuelto"); }
      actionsCtrl?.updateSavedViewChips(preset);
      loadTickets(true);
    }

    function resetAllFilters() {
      ["filter-search", "filter-status", "filter-priority", "filter-sede", "filter-service"].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.value = "";
      });
      const sortEl = document.getElementById("filter-sort");
      if (sortEl) sortEl.value = "priority_asc_deadline_asc";
      applyPresetView("all");
    }

    async function mount(ctx = {}) {
      destroy();
      abortCtrl = new AbortController();
      const sig = abortCtrl.signal;
      actionsCtrl = root.CasagbiTicketActionsController.createTicketActionsController({
        getCurrentDetail: () => currentDetail,
        onReloadAndOpen: async (tid, opts) => { await loadTickets(false); await openTicketDetail(tid, opts); },
      });
      applyUrlFilters();
      actionsCtrl.renderCustomSavedViewsSelect();

      debouncedSearch = root.CasagbiUtils.debounce(() => loadTickets(true), 350);
      document.getElementById("filter-search")?.addEventListener("input", () => { setSearching(true); debouncedSearch(); }, { signal: sig });
      document.getElementById("refresh-tickets-btn")?.addEventListener("click", () => loadTickets(false), { signal: sig });
      document.getElementById("tickets-reset-filters-btn")?.addEventListener("click", resetAllFilters, { signal: sig });
      document.getElementById("detail-back-top-btn")?.addEventListener("click", () => closeTicketDetail(), { signal: sig });
      document.getElementById("detail-back-bottom-btn")?.addEventListener("click", () => closeTicketDetail(), { signal: sig });

      ["filter-status", "filter-priority", "filter-sede", "filter-service", "filter-sort"].forEach((id) => {
        document.getElementById(id)?.addEventListener("change", () => loadTickets(true), { signal: sig });
      });
      document.querySelectorAll("#tickets-saved-views [data-saved-view]").forEach((btn) => {
        btn.addEventListener("click", () => applyPresetView(btn.getAttribute("data-saved-view")), { signal: sig });
      });
      document.getElementById("save-current-view-btn")?.addEventListener("click", () => {
        const name = window.prompt("Nombre para guardar esta vista:", "Mi filtro personalizado");
        if (!name || !name.trim()) return;
        actionsCtrl.saveCustomView({
          name: name.trim(),
          q: document.getElementById("filter-search")?.value || "",
          status: document.getElementById("filter-status")?.value || "",
          priority: document.getElementById("filter-priority")?.value || "",
          sede: document.getElementById("filter-sede")?.value || "",
          service_name: document.getElementById("filter-service")?.value || "",
          sort_by: document.getElementById("filter-sort")?.value || "priority_asc_deadline_asc",
          unassignedOnly,
          slaRiskOnly,
        });
        actionsCtrl.renderCustomSavedViewsSelect();
        root.CasagbiApi.showToast(`Vista '${name.trim()}' guardada.`, "success");
      }, { signal: sig });

      document.getElementById("custom-saved-views-select")?.addEventListener("change", (e) => {
        if (e.target.value === "") return;
        const chosen = actionsCtrl.readCustomSavedViews()[Number(e.target.value)];
        if (!chosen) return;
        [["filter-search", chosen.q], ["filter-status", chosen.status], ["filter-priority", chosen.priority], ["filter-sede", chosen.sede], ["filter-service", chosen.service_name], ["filter-sort", chosen.sort_by || "priority_asc_deadline_asc"]].forEach(([id, v]) => {
          const el = document.getElementById(id);
          if (el) el.value = v || "";
        });
        unassignedOnly = Boolean(chosen.unassignedOnly);
        slaRiskOnly = Boolean(chosen.slaRiskOnly);
        loadTickets(true);
      }, { signal: sig });

      document.querySelectorAll("#detail-mobile-tabs [data-detail-tab]").forEach((btn) => {
        btn.addEventListener("click", () => root.CasagbiTicketsView?.setDetailMobileTab(btn.getAttribute("data-detail-tab")), { signal: sig });
      });
      document.getElementById("tickets-create-btn")?.addEventListener("click", () => window.dispatchEvent(new CustomEvent("casagbi:navigate-tab", { detail: { tabId: "create-ticket" } })), { signal: sig });
      document.getElementById("tickets-more-filters-btn")?.addEventListener("click", (e) => {
        const panel = document.getElementById("tickets-extra-filters");
        if (panel) e.currentTarget?.setAttribute("aria-expanded", String(!panel.classList.toggle("hidden")));
      }, { signal: sig });

      if (ctx.clearFilters) {
        ["filter-search", "filter-status", "filter-priority", "filter-sede", "filter-service"].forEach((id) => {
          const el = document.getElementById(id);
          if (el) el.value = "";
        });
        unassignedOnly = false;
        slaRiskOnly = false;
        activePreset = "all";
        actionsCtrl.updateSavedViewChips("all");
      }

      if (!ctx.openTicketId) closeTicketDetail({ syncUrl: false });

      if (ctx.preset) applyPresetView(ctx.preset);
      else {
        if (ctx.searchQuery !== undefined) {
          const sEl = document.getElementById("filter-search");
          if (sEl) sEl.value = ctx.searchQuery;
        }
        await loadTickets(Boolean(ctx.clearFilters));
      }
      if (ctx.openTicketId) await openTicketDetail(ctx.openTicketId, { subtab: ctx.subtab });
    }

    function destroy() {
      if (debouncedSearch?.cancel) { debouncedSearch.cancel(); debouncedSearch = null; }
      if (abortCtrl) { abortCtrl.abort(); abortCtrl = null; }
      root.CasagbiApi?.abortRequestKey?.("tickets:list");
      root.CasagbiApi?.abortRequestKey?.("tickets:detail");
      chatContainer?.destroy?.();
      setSearching(false);
    }

    return { mount, destroy, refresh: () => loadTickets(false), openTicketDetail, closeTicketDetail, activePreset: () => activePreset };
  }

  function createTicketFormContainer(opts) {
    return root.CasagbiTicketCreateController.createTicketFormContainer(opts);
  }

  const api = { createTicketsContainer, createTicketFormContainer };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CasagbiTicketsContainer = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
