/**
 * Punto de entrada ligero de la Landing Page pública (delegado a features/landing).
 */
document.addEventListener("DOMContentLoaded", async () => {
  if (!window.CasagbiLandingContainer) return;
  const landing = window.CasagbiLandingContainer.createLandingContainer();
  await landing.mount();
  window.addEventListener("pagehide", () => landing.destroy(), { once: true });
});
