/**
 * Servicio de grabación de notas de voz (MediaRecorder) para el chat de tickets.
 */
(function (root) {
  function pickSupportedAudioMime() {
    if (!window.MediaRecorder || typeof MediaRecorder.isTypeSupported !== "function") return "";
    const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg;codecs=opus", "audio/ogg"];
    return candidates.find((m) => MediaRecorder.isTypeSupported(m)) || "";
  }

  function createAudioRecorder({ onRecordedBlob, onWarning, onError }) {
    let mediaRecorder = null;
    let mediaStream = null;
    let recChunks = [];
    let recStartedAt = 0;
    let recTimer = null;

    function stopAndRelease() {
      if (recTimer) {
        clearInterval(recTimer);
        recTimer = null;
      }
      if (mediaRecorder && mediaRecorder.state === "recording") {
        try {
          mediaRecorder.stop();
        } catch {
          /* ignore */
        }
      }
      mediaRecorder = null;
      if (mediaStream) {
        mediaStream.getTracks().forEach((tr) => tr.stop());
        mediaStream = null;
      }
    }

    async function toggle(statusEl) {
      if (mediaRecorder && mediaRecorder.state === "recording") {
        mediaRecorder.stop();
        return;
      }
      if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
        onWarning?.("El micrófono requiere HTTPS (o localhost) y navegador compatible con MediaRecorder.", "Audio no disponible");
        return;
      }
      try {
        mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const chosenMime = pickSupportedAudioMime();
        const rec = chosenMime ? new MediaRecorder(mediaStream, { mimeType: chosenMime }) : new MediaRecorder(mediaStream);
        mediaRecorder = rec;
        recChunks = [];
        recStartedAt = Date.now();

        rec.ondataavailable = (ev) => {
          if (ev.data && ev.data.size > 0) recChunks.push(ev.data);
        };
        rec.onstop = async () => {
          if (mediaStream) {
            mediaStream.getTracks().forEach((tr) => tr.stop());
            mediaStream = null;
          }
          clearInterval(recTimer);
          recTimer = null;
          statusEl?.classList.add("hidden");
          const durationSec = Math.max(1, Math.round((Date.now() - recStartedAt) / 1000));
          const finalMime = rec.mimeType || chosenMime || "audio/webm";
          const ext = finalMime.includes("mp4") ? "mp4" : finalMime.includes("ogg") ? "ogg" : "webm";
          const blob = new Blob(recChunks, { type: finalMime });
          if (blob.size > 0) {
            const file = new File([blob], `nota_voz_${Date.now()}.${ext}`, { type: finalMime });
            await onRecordedBlob?.(file, durationSec);
          }
        };
        rec.start();
        if (statusEl) {
          statusEl.textContent = "Grabando nota de voz (0 s)... presiona el micrófono para enviar.";
          statusEl.classList.remove("hidden");
          recTimer = setInterval(() => {
            const sec = Math.floor((Date.now() - recStartedAt) / 1000);
            statusEl.textContent = `Grabando nota de voz (${sec} s / máx. 180 s)... presiona para enviar.`;
            if (sec >= 180 && rec.state === "recording") rec.stop();
          }, 500);
        }
      } catch (err) {
        onError?.(err.message || "Permiso de micrófono denegado.", "Grabación de audio");
      }
    }

    return { toggle, stopAndRelease };
  }

  const api = { createAudioRecorder };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CasagbiAudioRecorder = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
