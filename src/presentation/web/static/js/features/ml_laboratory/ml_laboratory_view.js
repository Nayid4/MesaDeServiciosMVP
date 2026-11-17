/**
 * Vista Dumb del Laboratorio MLOps (tabla 5-Fold CV, tabla equivalente del gráfico y simulador).
 */
(function (root) {
  function esc(val) {
    return root.CasagbiUtils?.escapeHtml ? root.CasagbiUtils.escapeHtml(val) : String(val ?? "");
  }

  function renderLoading() {
    const tbody = document.getElementById("ml-models-tbody");
    if (tbody && root.CasagbiSkeletons) {
      tbody.innerHTML = root.CasagbiSkeletons.renderTableSkeleton(4, 8);
    }
  }

  function renderModelsData(reg, userRole) {
    const canTrain = ["coordinador", "admin"].includes(userRole);
    document.getElementById("ml-activate-btn")?.classList.toggle("hidden", !canTrain);
    document.getElementById("ml-retrain-btn")?.classList.toggle("hidden", !canTrain);
    document.getElementById("ml-activate-select")?.classList.toggle("hidden", !canTrain);

    const sub = document.getElementById("ml-summary-subtitle");
    if (sub) {
      sub.textContent = `Dataset limpio: ${reg.dataset_rows} filas | CV ${reg.cv_folds}-Fold | Ganancia vs Baseline: +${reg.f1_gain_vs_baseline_pct} pp`;
    }

    const sel = document.getElementById("ml-activate-select");
    if (sel) {
      sel.innerHTML = (reg.models || [])
        .map(
          (m) =>
            `<option value="${esc(m.model_id)}" ${m.model_id === reg.active_model_id ? "selected" : ""}>${esc(m.display_name)}</option>`
        )
        .join("");
    }

    const tbody = document.getElementById("ml-models-tbody");
    if (tbody) {
      tbody.innerHTML = (reg.models || [])
        .map(
          (m) => `
          <tr>
            <td class="px-4 py-3 font-semibold text-slate-900">${esc(m.display_name)}</td>
            <td class="px-4 py-3">${(m.cv_f1_mean * 100).toFixed(2)}% (±${(m.cv_f1_std * 100).toFixed(2)})</td>
            <td class="px-4 py-3">${(m.accuracy * 100).toFixed(2)}%</td>
            <td class="px-4 py-3">${(m.precision_macro * 100).toFixed(2)}%</td>
            <td class="px-4 py-3">${(m.recall_macro * 100).toFixed(2)}%</td>
            <td class="px-4 py-3 font-bold text-[#006837]">${(m.f1_macro * 100).toFixed(2)}%</td>
            <td class="px-4 py-3">${m.latency_ms} ms</td>
            <td class="px-4 py-3">
              ${
                m.model_id === reg.active_model_id
                  ? `<span class="px-2 py-0.5 rounded-full bg-emerald-100 text-[#004d28] font-semibold">Activo</span>`
                  : m.is_baseline
                    ? `<span class="px-2 py-0.5 rounded-full bg-slate-200 text-slate-700">Baseline</span>`
                    : `<span class="px-2 py-0.5 rounded-full bg-slate-100 text-slate-700">Candidato</span>`
              }
            </td>
          </tr>
        `
        )
        .join("");
    }
  }

  function renderSimulationResults(items) {
    const box = document.getElementById("ml-sim-results");
    if (!box) return;
    box.innerHTML = (items || [])
      .map(
        (r) => `
        <div class="p-3 rounded-xl border ${r.is_active ? "border-emerald-300 bg-emerald-50/70" : "border-slate-200 bg-slate-50"} flex items-center justify-between gap-2">
          <div>
            <p class="font-semibold text-slate-900">${esc(r.display_name)}</p>
            <p class="text-[11px] text-[#006837] font-semibold">${esc(r.predicted_service)}</p>
          </div>
          <span class="font-mono font-bold text-slate-800">${Number(r.confidence_pct).toFixed(1)}%</span>
        </div>
      `
      )
      .join("");
  }

  const api = { renderLoading, renderModelsData, renderSimulationResults };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CasagbiMlLabView = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
