/**
 * Componente Dumb de Creación de Tickets (sugerencias KB, previsualización adjuntos, progreso y OR-03).
 */
(function (root) {
  function esc(val) {
    return root.CasagbiUtils?.escapeHtml ? root.CasagbiUtils.escapeHtml(val) : String(val ?? "");
  }

  function renderCreateKbSuggestions(articles, onOpenArticle) {
    const box = document.getElementById("ct-kb-suggestions");
    if (!box) return;
    if (!articles || !articles.length) {
      box.classList.add("hidden");
      box.innerHTML = "";
      return;
    }
    box.classList.remove("hidden");
    box.innerHTML = `
      <div class="flex items-center justify-between gap-2">
        <p class="font-bold text-blue-950">Guías sugeridas antes de enviar tu ticket</p>
        <span class="text-[11px] text-blue-800">Revisa si alguna resuelve tu caso de inmediato</span>
      </div>
      <div class="space-y-2">${articles.map((a) => `
        <div class="p-2.5 rounded-lg bg-white border border-blue-200 flex flex-wrap items-start justify-between gap-2">
          <div class="flex-1 min-w-[200px]">
            <p class="font-semibold text-slate-900"><span class="font-mono text-[#006837]">${esc(a.code)}</span> · ${esc(a.title)}</p>
            <p class="text-[11px] text-slate-600 mt-0.5 line-clamp-2">${esc(String(a.solution_steps || "").replace(/<[^>]+>/g, " "))}</p>
          </div>
          <button type="button" data-open-kb-suggestion="${esc(a.code)}" class="px-2.5 py-1 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-900 text-[11px] font-semibold cursor-pointer shrink-0">Ver guía completa</button>
        </div>`).join("")}</div>`;
    box.querySelectorAll("[data-open-kb-suggestion]").forEach((btn) => {
      btn.addEventListener("click", () => onOpenArticle?.(btn.getAttribute("data-open-kb-suggestion")));
    });
  }

  function renderCreateAttachmentsPreview(files, previewUrls, onRemove) {
    const box = document.getElementById("ct-attachments-preview");
    if (!box) return;
    if (!files || !files.length) {
      box.classList.add("hidden");
      box.innerHTML = "";
      return;
    }
    box.classList.remove("hidden");
    box.innerHTML = files.map((f, idx) => {
      const isImg = String(f.type || "").startsWith("image/") && previewUrls[idx];
      const thumb = isImg
        ? `<img src="${esc(previewUrls[idx])}" alt="${esc(f.name)}" class="w-10 h-10 object-cover rounded-lg border border-slate-200 shrink-0" />`
        : '<span class="w-10 h-10 rounded-lg bg-slate-200 text-slate-700 font-mono text-[10px] font-bold flex items-center justify-center shrink-0">FILE</span>';
      return `<div class="p-2 rounded-xl bg-white border border-slate-200 flex items-center gap-2 text-xs">
        ${thumb}
        <div class="min-w-0 max-w-[160px]"><p class="font-semibold text-slate-800 truncate">${esc(f.name)}</p><p class="text-[10px] text-slate-600">${Math.max(1, Math.round(f.size / 1024))} KB</p></div>
        <button type="button" data-remove-ct-att="${idx}" aria-label="Quitar adjunto" class="px-2 py-0.5 rounded text-red-700 hover:bg-red-50 font-bold cursor-pointer">x</button>
      </div>`;
    }).join("");
    box.querySelectorAll("[data-remove-ct-att]").forEach((btn) => {
      btn.addEventListener("click", () => onRemove?.(Number(btn.getAttribute("data-remove-ct-att"))));
    });
  }

  function setCreateUploadProgress(visible, pct = 0, label = "") {
    const wrap = document.getElementById("ct-upload-progress-wrap");
    const bar = document.getElementById("ct-upload-progress-bar");
    const lbl = document.getElementById("ct-upload-progress-label");
    if (!wrap) return;
    wrap.classList.toggle("hidden", !visible);
    if (bar) bar.style.width = `${Math.max(0, Math.min(100, pct))}%`;
    if (lbl) lbl.textContent = label;
  }

  function renderOr03LiveEstimate(serviceName, urgency) {
    const prioEl = document.getElementById("ct-or03-live-prio");
    const slaEl = document.getElementById("ct-or03-live-sla");
    if (!prioEl || !slaEl) return;

    let impact = "Bajo";
    if (serviceName === "Conectividad y Redes Wi-Fi" || serviceName === "Plataformas Académicas (Aula Web / Vortal)") impact = "Alto";
    else if (serviceName === "Correo Institucional y Cuentas" || serviceName === "Aulas Inteligentes y Videoproyectores") impact = "Medio";

    const matrix = {
      "Alto|Alta": { p: "P1 Crítica", resp: "0.5 h", res: "4 h" },
      "Alto|Media": { p: "P2 Alta", resp: "1 h", res: "8 h" },
      "Alto|Baja": { p: "P3 Media", resp: "4 h", res: "24 h" },
      "Medio|Alta": { p: "P2 Alta", resp: "1 h", res: "8 h" },
      "Medio|Media": { p: "P3 Media", resp: "4 h", res: "24 h" },
      "Medio|Baja": { p: "P4 Baja", resp: "8 h", res: "40 h" },
      "Bajo|Alta": { p: "P3 Media", resp: "4 h", res: "24 h" },
      "Bajo|Media": { p: "P4 Baja", resp: "8 h", res: "40 h" },
      "Bajo|Baja": { p: "P4 Baja", resp: "8 h", res: "40 h" },
    };
    const res = matrix[`${impact}|${urgency || "Media"}`] || matrix["Medio|Media"];
    prioEl.textContent = res.p;
    slaEl.textContent = `Impacto ${impact} x Urgencia ${urgency || "Media"} · Respuesta ${res.resp} · Resolución ${res.res}`;
  }

  const api = {
    renderCreateKbSuggestions,
    renderCreateAttachmentsPreview,
    setCreateUploadProgress,
    renderOr03LiveEstimate,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CasagbiTicketModalsView = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
