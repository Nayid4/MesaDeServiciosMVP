/**
 * Punto de entrada ligero del Widget Flotante de Agente IA CASAGBI (delegado a features/ai_agent).
 */
window.CasagbiFloatingAgent = (() => {
  let instance = null;

  function ensureInstance() {
    if (!instance && window.CasagbiAiAgentContainer) {
      instance = window.CasagbiAiAgentContainer.createAiAgentContainer();
    }
    return instance;
  }

  document.addEventListener("DOMContentLoaded", () => {
    ensureInstance()?.mount();
  });

  window.addEventListener("pagehide", () => {
    instance?.destroy();
  });

  return {
    openPanel: () => ensureInstance()?.openPanel(),
    sendTurn: (txt) => ensureInstance()?.sendTurn(txt),
  };
})();
