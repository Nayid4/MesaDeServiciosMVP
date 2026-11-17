/**
 * Generadores de esqueletos de carga (dumb) con reservas de altura fijas para minimizar CLS (< 0,1).
 */
(function (root) {
  function renderKpiSkeleton(count = 4) {
    return Array.from({ length: count })
      .map(
        () => `
        <div class="bg-white rounded-2xl border border-slate-200 p-5 casagbi-shadow-card min-h-[104px]" aria-hidden="true">
          <div class="casagbi-skeleton h-3 w-28 rounded mb-3"></div>
          <div class="casagbi-skeleton h-7 w-20 rounded mb-2"></div>
          <div class="casagbi-skeleton h-3 w-32 rounded"></div>
        </div>
      `
      )
      .join("");
  }

  function renderTableSkeleton(rows = 5, cols = 6) {
    const cells = Array.from({ length: cols })
      .map(() => `<td class="px-4 py-3"><div class="casagbi-skeleton h-3.5 w-full rounded"></div></td>`)
      .join("");
    return Array.from({ length: rows })
      .map(() => `<tr aria-hidden="true">${cells}</tr>`)
      .join("");
  }

  function renderTicketDetailSkeleton() {
    return `
      <div class="bg-white rounded-2xl border border-slate-200 p-5 casagbi-shadow-card space-y-4" aria-hidden="true">
        <div class="casagbi-skeleton h-4 w-36 rounded"></div>
        <div class="casagbi-skeleton h-5 w-3/4 rounded"></div>
        <div class="casagbi-skeleton h-20 w-full rounded-xl"></div>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div class="casagbi-skeleton h-10 rounded"></div>
          <div class="casagbi-skeleton h-10 rounded"></div>
          <div class="casagbi-skeleton h-10 rounded"></div>
          <div class="casagbi-skeleton h-10 rounded"></div>
        </div>
      </div>
    `;
  }

  function renderChatSkeleton() {
    return `
      <div class="space-y-3" aria-hidden="true">
        <div class="flex flex-col items-start gap-1">
          <div class="casagbi-skeleton h-3 w-24 rounded"></div>
          <div class="casagbi-skeleton h-12 w-3/4 rounded-2xl"></div>
        </div>
        <div class="flex flex-col items-end gap-1">
          <div class="casagbi-skeleton h-3 w-20 rounded"></div>
          <div class="casagbi-skeleton h-10 w-2/3 rounded-2xl"></div>
        </div>
      </div>
    `;
  }

  function renderKbSkeleton(cards = 4) {
    return Array.from({ length: cards })
      .map(
        () => `
        <div class="bg-white rounded-2xl border border-slate-200 p-5 casagbi-shadow-card space-y-2.5 min-h-[168px]" aria-hidden="true">
          <div class="flex justify-between">
            <div class="casagbi-skeleton h-4 w-20 rounded"></div>
            <div class="casagbi-skeleton h-4 w-24 rounded"></div>
          </div>
          <div class="casagbi-skeleton h-5 w-4/5 rounded"></div>
          <div class="casagbi-skeleton h-12 w-full rounded-xl"></div>
        </div>
      `
      )
      .join("");
  }

  function renderLandingCatalogSkeleton(cards = 6) {
    return Array.from({ length: cards })
      .map(
        () => `
        <div class="rounded-2xl bg-white border border-slate-200 p-5 casagbi-shadow-card min-h-[146px]" aria-hidden="true">
          <div class="flex justify-between mb-3">
            <div class="casagbi-skeleton h-5 w-28 rounded-full"></div>
            <div class="casagbi-skeleton h-4 w-20 rounded"></div>
          </div>
          <div class="casagbi-skeleton h-5 w-3/4 rounded mb-2"></div>
          <div class="casagbi-skeleton h-10 w-full rounded"></div>
        </div>
      `
      )
      .join("");
  }

  const api = {
    renderKpiSkeleton,
    renderTableSkeleton,
    renderTicketDetailSkeleton,
    renderChatSkeleton,
    renderKbSkeleton,
    renderLandingCatalogSkeleton,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CasagbiSkeletons = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
