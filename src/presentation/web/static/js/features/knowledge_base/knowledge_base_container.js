/**
 * Contenedor Smart de Base de Conocimiento (paginación SQL + búsqueda debounced, delegando CRUD a kb_editor_controller.js).
 */
(function (root) {
  function createKnowledgeBaseContainer({
    getUser = () => null,
    gridId = "kb-articles-grid",
    searchInputId = "kb-search-input",
    serviceSelectId = "kb-filter-service",
    indicatorId = "kb-search-indicator",
    syncUrl = true,
  } = {}) {
    let abortCtrl = null;
    let debouncedSearch = null;
    let editorOpen = false;
    let currentPage = 1;
    const pageSize = 9;
    let editorCtrl = null;

    function setSearching(flag) {
      const ind = document.getElementById(indicatorId);
      if (ind) ind.classList.toggle("hidden", !flag);
    }

    function resetPageAndLoad() {
      currentPage = 1;
      loadArticles();
    }

    async function loadArticles() {
      const view = root.CasagbiKnowledgeBaseView;
      if (!view) return;

      const q = (document.getElementById(searchInputId)?.value || "").trim();
      const svc = (document.getElementById(serviceSelectId)?.value || "").trim();
      const category = (document.getElementById("kb-filter-category")?.value || "").trim();
      const status = (document.getElementById("kb-filter-status")?.value || "").trim();
      const visibility = (document.getElementById("kb-filter-visibility")?.value || "").trim();

      if (syncUrl) {
        root.CasagbiUtils?.syncUrlParams({ kb_q: q, kb_service: svc, kb_cat: category, kb_status: status, kb_vis: visibility, kb_page: currentPage });
      }
      setSearching(true);
      view.renderLoading(gridId);

      const params = new URLSearchParams();
      if (svc) params.set("service_name", svc);
      if (category) params.set("category_topic", category);
      if (status) params.set("status", status);
      if (visibility) params.set("visibility", visibility);
      if (q) params.set("q", q);
      if (gridId === "kb-articles-grid") {
        params.set("page", String(currentPage));
        params.set("page_size", String(pageSize));
      }

      try {
        const res = await root.CasagbiApi.get(`/api/v1/analytics/kb?${params.toString()}`, {
          requestKey: `kb:list:${gridId}`,
          signal: abortCtrl?.signal,
        });
        const user = getUser();
        view.renderArticles(res.articles || [], {
          gridId,
          userRole: user?.role || "public",
          handlers: {
            onEdit: (art) => {
              editorOpen = true;
              view.toggleEditorVisibility(true);
              view.populateEditorForm(art, `Editando ${art.code} (v${art.version})`);
              document.getElementById("kb-create-card")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
            },
            onTransition: (idNum, action) => editorCtrl?.handleTransition(idNum, action),
            onReturnWithNotes: (idNum) => editorCtrl?.handleReturnWithNotes(idNum),
            onShowVersions: (idNum) => editorCtrl?.handleShowVersions(idNum),
          },
        });
        const pagEl = gridId === "kb-articles-grid" ? document.getElementById("kb-pagination") : null;
        if (pagEl && root.CasagbiPagination) {
          root.CasagbiPagination.render(pagEl, {
            page: res.page || currentPage,
            pages: res.pages || 1,
            total: res.total || (res.articles || []).length,
            pageSize: res.page_size || pageSize,
            onPageChange: (nextPage) => { currentPage = nextPage; loadArticles(); },
          });
        }
      } catch (err) {
        if (err?.name === "AbortError") return;
        const grid = document.getElementById(gridId);
        if (grid && root.CasagbiEmptyErrorState) {
          grid.innerHTML = `<div class="col-span-full">${root.CasagbiEmptyErrorState.renderErrorState({
            title: "Error cargando Base de Conocimiento",
            detail: err.message,
            retryAttr: 'data-kb-retry="1"',
          })}</div>`;
          grid.querySelector("[data-kb-retry]")?.addEventListener("click", loadArticles);
        }
      } finally {
        setSearching(false);
      }
    }

    async function mount(ctx = {}) {
      destroy();
      abortCtrl = new AbortController();
      const sig = abortCtrl.signal;
      const view = root.CasagbiKnowledgeBaseView;
      const user = getUser();
      currentPage = 1;

      editorCtrl = root.CasagbiKbEditorController?.createKbEditorController({
        getUser,
        getSignal: () => abortCtrl?.signal,
        onReload: loadArticles,
        onCloseEditor: () => {
          editorOpen = false;
          view?.toggleEditorVisibility(false);
        },
      });

      if (gridId === "kb-articles-grid") view?.configureRoleControls(user?.role || "public");

      if (syncUrl && root.CasagbiUtils?.readUrlParams) {
        const p = root.CasagbiUtils.readUrlParams();
        const setEl = (id, val) => {
          const el = document.getElementById(id);
          if (el && val !== undefined) el.value = val;
        };
        setEl(searchInputId, p.kb_q);
        setEl(serviceSelectId, p.kb_service);
        setEl("kb-filter-category", p.kb_cat);
        setEl("kb-filter-status", p.kb_status);
        setEl("kb-filter-visibility", p.kb_vis);
        if (p.kb_page && Number(p.kb_page) >= 1) currentPage = Number(p.kb_page);
      }

      if (ctx.searchCode) {
        const sEl = document.getElementById(searchInputId);
        if (sEl) sEl.value = ctx.searchCode;
      }

      if (ctx.prefillArticle && gridId === "kb-articles-grid") {
        editorOpen = true;
        view?.toggleEditorVisibility(true);
        view?.populateEditorForm(ctx.prefillArticle, "Propuesta desde Ticket Resuelto");
      } else if (gridId === "kb-articles-grid") {
        editorOpen = false;
        view?.toggleEditorVisibility(false);
      }

      debouncedSearch = root.CasagbiUtils.debounce(resetPageAndLoad, 350);
      document.getElementById(searchInputId)?.addEventListener("input", () => {
        setSearching(true);
        debouncedSearch();
      }, { signal: sig });

      [serviceSelectId, "kb-filter-category", "kb-filter-status", "kb-filter-visibility"].forEach((fid) => {
        document.getElementById(fid)?.addEventListener("change", resetPageAndLoad, { signal: sig });
      });

      document.getElementById("kb-toggle-editor-btn")?.addEventListener("click", () => {
        editorOpen = !editorOpen;
        if (editorOpen) view?.populateEditorForm(null, "Nuevo artículo");
        view?.toggleEditorVisibility(editorOpen);
      }, { signal: sig });

      document.getElementById("kb-cancel-edit-btn")?.addEventListener("click", () => {
        view?.populateEditorForm(null, "Nuevo artículo");
        editorOpen = false;
        view?.toggleEditorVisibility(false);
      }, { signal: sig });

      document.getElementById("kb-preview-btn")?.addEventListener("click", () => editorCtrl?.handlePreviewForm(), { signal: sig });
      document.getElementById("kb-save-draft-btn")?.addEventListener("click", () => editorCtrl?.saveArticle("Borrador"), { signal: sig });
      document.getElementById("kb-publish-btn")?.addEventListener("click", () => editorCtrl?.saveArticle("Publicado"), { signal: sig });
      document.getElementById("kb-form")?.addEventListener("submit", async (e) => {
        e.preventDefault();
        await editorCtrl?.saveArticle("En revisión");
      }, { signal: sig });

      if (gridId === "kb-articles-grid") {
        document.getElementById("kb-reset-filters-btn")?.addEventListener("click", () => {
          [searchInputId, serviceSelectId, "kb-filter-category", "kb-filter-status", "kb-filter-visibility"].forEach((id) => {
            const el = document.getElementById(id);
            if (el) el.value = "";
          });
          document.getElementById("kb-inspector-panel")?.classList.add("hidden");
          resetPageAndLoad();
        }, { signal: sig });

        document.getElementById("kb-contact-support-btn")?.addEventListener("click", () => {
          const role = getUser()?.role || "usuario";
          if (root.CasagbiRouter?.isTabAllowed?.(role, "create-ticket")) {
            window.dispatchEvent(new CustomEvent("casagbi:navigate-tab", { detail: { tabId: "create-ticket" } }));
          } else {
            root.CasagbiAiAgentView?.openPanel?.();
          }
        }, { signal: sig });
      }

      await loadArticles();
    }

    function destroy() {
      if (debouncedSearch?.cancel) { debouncedSearch.cancel(); debouncedSearch = null; }
      if (abortCtrl) { abortCtrl.abort(); abortCtrl = null; }
      editorCtrl = null;
      root.CasagbiApi?.abortRequestKey?.(`kb:list:${gridId}`);
      setSearching(false);
    }

    return { mount, destroy, refresh: loadArticles };
  }

  const api = { createKnowledgeBaseContainer };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CasagbiKnowledgeBaseContainer = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
