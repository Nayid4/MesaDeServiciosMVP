/**
 * Contenedor Smart del Laboratorio MLOps (ciclo de vida mount/destroy + AbortController).
 */
(function (root) {
  function createMlLaboratoryContainer({ getUser }) {
    let abortCtrl = null;
    let mlChart = null;

    function destroyChart() {
      if (mlChart) {
        mlChart.destroy();
        mlChart = null;
      }
    }

    async function loadMlLab() {
      const view = root.CasagbiMlLabView;
      if (!view) return;
      view.renderLoading();
      try {
        const data = await root.CasagbiApi.get("/api/v1/analytics/ml/models", {
          requestKey: "ml:models",
          signal: abortCtrl?.signal,
        });
        const reg = data.registry;
        const user = getUser();
        view.renderModelsData(reg, user?.role);

        if (root.Chart) {
          destroyChart();
          const canvas = document.getElementById("chart-ml-comparison");
          if (canvas) {
            mlChart = new root.Chart(canvas, {
              type: "bar",
              data: {
                labels: reg.models.map((m) => m.model_id),
                datasets: [
                  { label: "F1 Macro (%)", data: reg.models.map((m) => (m.f1_macro * 100).toFixed(2)), backgroundColor: "#006837", borderRadius: 6 },
                  { label: "CV 5-Fold F1 (%)", data: reg.models.map((m) => (m.cv_f1_mean * 100).toFixed(2)), backgroundColor: "#10b981", borderRadius: 6 },
                ],
              },
            });
          }
        }
      } catch (err) {
        if (err?.name === "AbortError") return;
        root.CasagbiApi.showToast(err.message, "error", "Error MLOps");
      }
    }

    async function mount() {
      destroy();
      abortCtrl = new AbortController();
      const sig = abortCtrl.signal;

      document.getElementById("ml-sim-btn")?.addEventListener(
        "click",
        async () => {
          try {
            const txt = document.getElementById("ml-sim-input")?.value || "";
            const res = await root.CasagbiApi.post(
              "/api/v1/analytics/ml/simulate",
              { text: txt },
              { requestKey: "ml:simulate", signal: sig }
            );
            root.CasagbiMlLabView.renderSimulationResults(res.side_by_side || []);
          } catch (err) {
            if (err?.name !== "AbortError") {
              root.CasagbiApi.showToast(err.message, "error", "Simulador MLOps");
            }
          }
        },
        { signal: sig }
      );

      document.getElementById("ml-activate-btn")?.addEventListener(
        "click",
        async () => {
          try {
            const modelId = document.getElementById("ml-activate-select").value;
            await root.CasagbiApi.post("/api/v1/analytics/ml/activate", { model_id: modelId }, { signal: sig });
            root.CasagbiApi.showToast(`Modelo ${modelId} activado en producción.`, "success");
            await loadMlLab();
          } catch (err) {
            if (err?.name !== "AbortError") {
              root.CasagbiApi.showToast(err.message, "error", err.problem?.title || "Error");
            }
          }
        },
        { signal: sig }
      );

      document.getElementById("ml-retrain-btn")?.addEventListener(
        "click",
        async () => {
          const btn = document.getElementById("ml-retrain-btn");
          if (btn) {
            btn.disabled = true;
            btn.textContent = "Reentrenando 18,000 registros...";
          }
          try {
            await root.CasagbiApi.post("/api/v1/analytics/ml/train", { n_rows: 18000 }, { signal: sig });
            root.CasagbiApi.showToast("Pipeline CRISP-DM y 4 modelos reentrenados.", "success");
            await loadMlLab();
          } catch (err) {
            if (err?.name !== "AbortError") {
              root.CasagbiApi.showToast(err.message, "error", err.problem?.title || "Error");
            }
          } finally {
            if (btn) {
              btn.disabled = false;
              btn.textContent = "Re-entrenar Pipeline (18k)";
            }
          }
        },
        { signal: sig }
      );

      await loadMlLab();
    }

    function destroy() {
      if (abortCtrl) {
        abortCtrl.abort();
        abortCtrl = null;
      }
      root.CasagbiApi?.abortRequestKey?.("ml:models");
      root.CasagbiApi?.abortRequestKey?.("ml:simulate");
      destroyChart();
    }

    return { mount, destroy };
  }

  const api = { createMlLaboratoryContainer };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CasagbiMlLaboratoryContainer = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
