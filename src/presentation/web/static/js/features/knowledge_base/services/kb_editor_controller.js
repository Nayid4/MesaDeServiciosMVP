/**
 * Servicio controlador de Edición, Previsualización y Versionamiento de Base de Conocimiento.
 */
(function (root) {
  function readFormPayload(targetStatus) {
    const articleIdRaw = (document.getElementById("kb-article-id")?.value || "").trim();
    const sourceTicketRaw = (document.getElementById("kb-source-ticket-id")?.value || "").trim();
    return {
      article_id: articleIdRaw ? Number(articleIdRaw) : null,
      source_ticket_id: sourceTicketRaw ? Number(sourceTicketRaw) : null,
      code: document.getElementById("kb-code")?.value || "",
      title: document.getElementById("kb-title")?.value || "",
      service_name: document.getElementById("kb-service")?.value || "",
      category_topic: document.getElementById("kb-category-topic")?.value || "General",
      visibility: document.getElementById("kb-visibility")?.value || "Pública",
      keywords: document.getElementById("kb-keywords")?.value || "",
      symptoms: document.getElementById("kb-symptoms")?.value || "",
      probable_cause: document.getElementById("kb-probable-cause")?.value || "",
      solution_steps: document.getElementById("kb-steps")?.value || "",
      escalation_criteria: document.getElementById("kb-escalation")?.value || "",
      change_summary: document.getElementById("kb-change-summary")?.value || "",
      status: targetStatus,
    };
  }

  function createKbEditorController({ getUser, getSignal, onReload, onCloseEditor }) {
    async function saveArticle(targetStatus) {
      const form = document.getElementById("kb-form");
      if (form && !form.reportValidity()) return;
      const payload = readFormPayload(targetStatus);
      try {
        const res = payload.article_id
          ? await root.CasagbiApi.put(`/api/v1/analytics/kb/${payload.article_id}`, payload, { signal: getSignal() })
          : await root.CasagbiApi.post("/api/v1/analytics/kb", payload, { signal: getSignal() });
        const art = res.article || {};
        root.CasagbiApi.showToast(`Artículo ${art.code || ""} guardado (v${art.version || 1} · ${art.status || targetStatus}).`, "success");
        root.CasagbiKnowledgeBaseView?.populateEditorForm(null, "Nuevo artículo");
        onCloseEditor?.();
        await onReload?.();
      } catch (err) {
        if (err?.name !== "AbortError") {
          root.CasagbiApi.showToast(err.message, "error", err.problem?.title || "Error guardando artículo KB");
        }
      }
    }

    async function handlePreviewForm() {
      const payload = readFormPayload("Borrador");
      try {
        const clean = await root.CasagbiApi.post("/api/v1/analytics/kb/preview-sanitize", {
          symptoms: payload.symptoms,
          probable_cause: payload.probable_cause,
          solution_steps: payload.solution_steps,
          escalation_criteria: payload.escalation_criteria,
        }, { signal: getSignal() });
        root.CasagbiKnowledgeBaseView?.renderArticlePreview(payload, clean);
      } catch (err) {
        if (err?.name !== "AbortError") root.CasagbiApi.showToast(err.message, "error", "Previsualización KB");
      }
    }

    async function handleTransition(articleId, action, reviewNotes = null) {
      try {
        const res = await root.CasagbiApi.post(`/api/v1/analytics/kb/${articleId}/transition`, {
          action,
          review_notes: reviewNotes,
        }, { signal: getSignal() });
        const art = res.article || {};
        root.CasagbiApi.showToast(`Artículo ${art.code || ""} actualizado a '${art.status}' (v${art.version || 1}).`, "success");
        await onReload?.();
      } catch (err) {
        if (err?.name !== "AbortError") root.CasagbiApi.showToast(err.message, "error", err.problem?.title || "Transición KB");
      }
    }

    async function handleReturnWithNotes(articleId) {
      const notes = window.prompt("Indica las observaciones obligatorias para devolver el artículo al autor (mínimo 5 caracteres):", "");
      if (notes === null) return;
      await handleTransition(articleId, "devolver", notes.trim());
    }

    async function handleShowVersions(articleId) {
      try {
        const data = await root.CasagbiApi.get(`/api/v1/analytics/kb/${articleId}/versions`, {
          requestKey: `kb:versions:${articleId}`,
          signal: getSignal(),
        });
        const user = getUser();
        root.CasagbiKnowledgeBaseView?.renderVersionsPanel(data.article, data.versions || [], user?.role || "public", {
          onCompare: async (artId, fromV, toV) => {
            try {
              const cmp = await root.CasagbiApi.get(
                `/api/v1/analytics/kb/${artId}/versions/compare?from_version=${fromV}&to_version=${toV}`,
                { signal: getSignal() }
              );
              root.CasagbiKnowledgeBaseView?.renderComparisonDiff(cmp);
            } catch (err) {
              if (err?.name !== "AbortError") root.CasagbiApi.showToast(err.message, "error", "Comparar versiones");
            }
          },
          onRestore: async (artId, verNum) => {
            if (!window.confirm(`¿Restaurar el contenido de la versión v${verNum} como una nueva versión?`)) return;
            try {
              const res = await root.CasagbiApi.post(`/api/v1/analytics/kb/${artId}/versions/${verNum}/restore`, {}, { signal: getSignal() });
              const restored = res.article || {};
              root.CasagbiApi.showToast(`Versión v${verNum} restaurada como v${restored.version} (${restored.status}).`, "success");
              await onReload?.();
              await handleShowVersions(artId);
            } catch (err) {
              if (err?.name !== "AbortError") root.CasagbiApi.showToast(err.message, "error", err.problem?.title || "Restaurar versión");
            }
          },
        });
      } catch (err) {
        if (err?.name !== "AbortError") root.CasagbiApi.showToast(err.message, "error", "Historial de versiones");
      }
    }

    return { saveArticle, handlePreviewForm, handleTransition, handleReturnWithNotes, handleShowVersions };
  }

  const api = { createKbEditorController };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CasagbiKbEditorController = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
