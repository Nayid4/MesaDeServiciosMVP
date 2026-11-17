/**
 * Contenedor Smart de Analítica KPI / Resumen (RF-22, gráficos reales + tablas equivalentes,
 * filtros en URL, accesos directos a bandeja/creación y exportación CSV/PDF RIU-10).
 */
(function (root) {
  function createAnalyticsHomeContainer() {
    let abortCtrl = null;
    const charts = { svc: null, tech: null };

    function getFilterValues() {
      return {
        kpi_sede: document.getElementById("kpi-filter-sede")?.value || "",
        kpi_service: document.getElementById("kpi-filter-service")?.value || "",
        kpi_priority: document.getElementById("kpi-filter-priority")?.value || "",
      };
    }

    function applyUrlFilters() {
      const urlParams = root.CasagbiUtils?.readUrlParams ? root.CasagbiUtils.readUrlParams() : {};
      const setVal = (id, key) => {
        const el = document.getElementById(id);
        if (el && urlParams[key] !== undefined) el.value = urlParams[key];
      };
      setVal("kpi-filter-sede", "kpi_sede");
      setVal("kpi-filter-service", "kpi_service");
      setVal("kpi-filter-priority", "kpi_priority");
    }

    function buildQueryString() {
      const f = getFilterValues();
      root.CasagbiUtils?.syncUrlParams(f);
      const params = new URLSearchParams();
      if (f.kpi_sede) params.set("sede", f.kpi_sede);
      if (f.kpi_service) params.set("service_name", f.kpi_service);
      if (f.kpi_priority) params.set("priority", f.kpi_priority);
      return params.toString();
    }

    function destroyCharts() {
      if (charts.svc) {
        charts.svc.destroy();
        charts.svc = null;
      }
      if (charts.tech) {
        charts.tech.destroy();
        charts.tech = null;
      }
    }

    function shortenServiceLabel(label) {
      const raw = String(label || "");
      if (raw.includes("Redes")) return "Redes Wi-Fi";
      if (raw.includes("Plataformas")) return "Aula Web / Vortal";
      if (raw.includes("Correo")) return "Correo y Cuentas";
      if (raw.includes("Aulas")) return "Aulas y Proyectores";
      if (raw.includes("Cómputo")) return "Cómputo e Impresoras";
      if (raw.includes("Software")) return "Software y Licencias";
      return raw.length > 20 ? `${raw.slice(0, 18)}...` : raw;
    }

    async function loadKpis() {
      const view = root.CasagbiAnalyticsHomeView;
      if (!view) return;
      view.renderLoadingState();
      const qs = buildQueryString();
      try {
        const data = await root.CasagbiApi.get(`/api/v1/analytics/kpis?${qs}`, {
          requestKey: "analytics:kpis",
          signal: abortCtrl?.signal,
        });

        const sidebarBadge = document.getElementById("sidebar-tickets-count-badge");
        if (sidebarBadge) {
          sidebarBadge.textContent = String(Number(data.kpis?.open_tickets || 0));
        }

        view.renderKpisData(data, {
          onOpenTicket: (ticketId) => {
            window.dispatchEvent(
              new CustomEvent("casagbi:navigate-tab", {
                detail: { tabId: "tickets", context: { openTicketId: ticketId } },
              })
            );
          },
        });

        if (root.Chart) {
          destroyCharts();
          const c1 = document.getElementById("chart-by-service");
          if (c1) {
            const breakdown =
              Array.isArray(data.service_breakdown) && data.service_breakdown.length
                ? data.service_breakdown
                : Object.entries(data.by_service || {}).map(([service_name, received]) => ({
                    service_name,
                    received,
                    resolved: 0,
                  }));

            charts.svc = new root.Chart(c1, {
              type: "bar",
              data: {
                labels: breakdown.map((item) => shortenServiceLabel(item.service_name)),
                datasets: [
                  {
                    label: "Recibidos",
                    data: breakdown.map((item) => Number(item.received || 0)),
                    backgroundColor: "#006837",
                    borderRadius: 6,
                    barPercentage: 0.72,
                    categoryPercentage: 0.68,
                  },
                  {
                    label: "Resueltos",
                    data: breakdown.map((item) => Number(item.resolved || 0)),
                    backgroundColor: "#6ee7b7",
                    borderRadius: 6,
                    barPercentage: 0.72,
                    categoryPercentage: 0.68,
                  },
                ],
              },
              options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: { display: false },
                },
                scales: {
                  x: {
                    grid: { display: false },
                    ticks: { font: { size: 11 }, color: "#64748b" },
                  },
                  y: {
                    beginAtZero: true,
                    ticks: { precision: 0, font: { size: 11 }, color: "#64748b" },
                    grid: { color: "#f1f5f9" },
                  },
                },
              },
            });
          }

          const c2 = document.getElementById("chart-tech-workload");
          if (c2) {
            const wl = data.technician_workload || [];
            charts.tech = new root.Chart(c2, {
              type: "bar",
              data: {
                labels: wl.map((w) => String(w.full_name || w.email).split(" ").slice(0, 2).join(" ")),
                datasets: [
                  {
                    label: "Abiertos",
                    data: wl.map((w) => Number(w.open_tickets || 0)),
                    backgroundColor: "#006837",
                    borderRadius: 6,
                  },
                  {
                    label: "Resueltos",
                    data: wl.map((w) => Number(w.resolved_tickets || 0)),
                    backgroundColor: "#a7f3d0",
                    borderRadius: 6,
                  },
                ],
              },
              options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: true, position: "bottom", labels: { boxWidth: 10, font: { size: 11 } } } },
                scales: {
                  x: { grid: { display: false }, ticks: { font: { size: 10 }, color: "#64748b" } },
                  y: { beginAtZero: true, ticks: { precision: 0, font: { size: 10 }, color: "#64748b" } },
                },
              },
            });
          }
        }
      } catch (err) {
        if (err?.name === "AbortError") return;
        view.renderErrorState(err.message, loadKpis);
        root.CasagbiApi?.showToast(err.message, "error", "Error cargando KPIs");
      }
    }

    async function handleExport(format) {
      const qs = buildQueryString();
      try {
        const fname = await root.CasagbiApi.downloadFile(
          `/api/v1/analytics/export.${format}?${qs}`,
          `informe_casagbi_riu10.${format}`
        );
        root.CasagbiApi.showToast(`Reporte ${fname} descargado (RIU-10).`, "success", "Exportación completada");
      } catch (err) {
        root.CasagbiApi.showToast(err.message, "error", "Error exportando reporte");
      }
    }

    async function mount() {
      destroy();
      abortCtrl = new AbortController();
      const sig = abortCtrl.signal;
      applyUrlFilters();

      document.getElementById("kpi-refresh-btn")?.addEventListener("click", loadKpis, { signal: sig });
      ["kpi-filter-sede", "kpi-filter-service", "kpi-filter-priority"].forEach((id) => {
        document.getElementById(id)?.addEventListener("change", loadKpis, { signal: sig });
      });
      document.getElementById("kpi-export-csv-btn")?.addEventListener("click", () => handleExport("csv"), { signal: sig });
      document.getElementById("kpi-export-pdf-btn")?.addEventListener("click", () => handleExport("pdf"), { signal: sig });

      document.getElementById("resumen-create-btn")?.addEventListener(
        "click",
        () => window.dispatchEvent(new CustomEvent("casagbi:navigate-tab", { detail: { tabId: "create-ticket" } })),
        { signal: sig }
      );
      document.getElementById("resumen-priority-queue-link")?.addEventListener(
        "click",
        () => window.dispatchEvent(new CustomEvent("casagbi:navigate-tab", { detail: { tabId: "tickets" } })),
        { signal: sig }
      );
      document.getElementById("resumen-view-all-tickets-btn")?.addEventListener(
        "click",
        () => window.dispatchEvent(new CustomEvent("casagbi:navigate-tab", { detail: { tabId: "tickets" } })),
        { signal: sig }
      );
      document.getElementById("resumen-sla-alert-btn")?.addEventListener(
        "click",
        () =>
          window.dispatchEvent(
            new CustomEvent("casagbi:navigate-tab", {
              detail: { tabId: "tickets", context: { preset: "sla-risk" } },
            })
          ),
        { signal: sig }
      );

      await loadKpis();
    }

    function destroy() {
      if (abortCtrl) {
        abortCtrl.abort();
        abortCtrl = null;
      }
      root.CasagbiApi?.abortRequestKey?.("analytics:kpis");
      destroyCharts();
    }

    return { mount, destroy, refresh: loadKpis };
  }

  const api = { createAnalyticsHomeContainer };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CasagbiAnalyticsHomeContainer = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
