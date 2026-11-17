/**
 * Ayudante ligero de skeletons para listas, tablas y tarjetas.
 */
(function (global) {
  "use strict";

  function tableRows(tbody, cols, rows) {
    if (!tbody) { return; }
    var colCount = Math.max(1, Number(cols || 5));
    var rowCount = Math.max(1, Number(rows || 4));
    var html = [];
    for (var r = 0; r < rowCount; r += 1) {
      var cells = [];
      for (var c = 0; c < colCount; c += 1) {
        cells.push('<td class="px-4 py-3"><div class="casagbi-skeleton h-4 w-full rounded"></div></td>');
      }
      html.push('<tr class="border-b border-slate-100">' + cells.join("") + "</tr>");
    }
    tbody.innerHTML = html.join("");
  }

  function cardGrid(container, count) {
    if (!container) { return; }
    var total = Math.max(1, Number(count || 3));
    var html = [];
    for (var i = 0; i < total; i += 1) {
      html.push(
        '<div class="rounded-2xl border border-slate-200 bg-white p-5 space-y-3">' +
        '<div class="casagbi-skeleton h-4 w-24 rounded"></div>' +
        '<div class="casagbi-skeleton h-5 w-3/4 rounded"></div>' +
        '<div class="casagbi-skeleton h-12 w-full rounded"></div>' +
        "</div>"
      );
    }
    container.innerHTML = html.join("");
  }

  global.CasagbiSkeleton = {
    tableRows: tableRows,
    cardGrid: cardGrid
  };
})(window);
