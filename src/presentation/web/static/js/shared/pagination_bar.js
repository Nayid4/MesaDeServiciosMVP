/**
 * Componente dumb reutilizable para barra de paginación SQL.
 */
(function (global) {
  "use strict";

  function buildPageNumbers(current, totalPages) {
    if (totalPages <= 7) {
      return Array.from({ length: totalPages }, function (_, idx) { return idx + 1; });
    }
    var pages = [1];
    var start = Math.max(2, current - 1);
    var end = Math.min(totalPages - 1, current + 1);
    if (start > 2) { pages.push("..."); }
    for (var p = start; p <= end; p += 1) { pages.push(p); }
    if (end < totalPages - 1) { pages.push("..."); }
    pages.push(totalPages);
    return pages;
  }

  function render(container, opts) {
    if (!container) { return; }
    var options = opts || {};
    var page = Math.max(1, Number(options.page || 1));
    var pageSize = Math.max(1, Number(options.pageSize || options.page_size || 10));
    var total = Math.max(0, Number(options.total || 0));
    var totalPages = Math.max(1, Number(options.pages || options.total_pages || Math.ceil(total / pageSize) || 1));
    var onPageChange = typeof options.onPageChange === "function" ? options.onPageChange : function () {};

    container.innerHTML = "";
    if (total === 0) {
      container.innerHTML = '<div class="casagbi-pagination-bar"><span>Sin registros para mostrar</span></div>';
      return;
    }

    var startItem = ((page - 1) * pageSize) + 1;
    var endItem = Math.min(total, page * pageSize);

    var bar = document.createElement("nav");
    bar.className = "casagbi-pagination-bar";
    bar.setAttribute("aria-label", options.ariaLabel || "Paginación de resultados");

    var summary = document.createElement("span");
    summary.textContent = "Mostrando " + startItem + "-" + endItem + " de " + total;
    bar.appendChild(summary);

    var controls = document.createElement("div");
    controls.className = "casagbi-pagination-controls";

    var prevBtn = document.createElement("button");
    prevBtn.type = "button";
    prevBtn.className = "casagbi-page-btn";
    prevBtn.textContent = "Anterior";
    prevBtn.disabled = page <= 1;
    prevBtn.addEventListener("click", function () { if (page > 1) { onPageChange(page - 1); } });
    controls.appendChild(prevBtn);

    buildPageNumbers(page, totalPages).forEach(function (item) {
      if (item === "...") {
        var dots = document.createElement("span");
        dots.className = "px-1 text-slate-400";
        dots.textContent = "...";
        controls.appendChild(dots);
        return;
      }
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "casagbi-page-btn" + (item === page ? " is-active" : "");
      btn.textContent = String(item);
      if (item === page) { btn.setAttribute("aria-current", "page"); }
      btn.addEventListener("click", function () { if (item !== page) { onPageChange(item); } });
      controls.appendChild(btn);
    });

    var nextBtn = document.createElement("button");
    nextBtn.type = "button";
    nextBtn.className = "casagbi-page-btn";
    nextBtn.textContent = "Siguiente";
    nextBtn.disabled = page >= totalPages;
    nextBtn.addEventListener("click", function () { if (page < totalPages) { onPageChange(page + 1); } });
    controls.appendChild(nextBtn);

    bar.appendChild(controls);
    container.appendChild(bar);
  }

  global.CasagbiPagination = { render: render };
})(window);
