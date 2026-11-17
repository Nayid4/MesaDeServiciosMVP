/**
 * Vista Dumb de Chat Multimedia del Ticket (edición ≤ 5 min, borrado lógico, respuestas citadas, adjuntos y XSS-safe).
 */
(function (root) {
  function esc(val) {
    return root.CasagbiUtils?.escapeHtml ? root.CasagbiUtils.escapeHtml(val) : String(val ?? "");
  }

  function renderLoading(chatBoxId = "ticket-chat-messages") {
    const box = document.getElementById(chatBoxId);
    if (box && root.CasagbiSkeletons) {
      box.innerHTML = root.CasagbiSkeletons.renderChatSkeleton();
    }
  }

  function renderMessageBubble(msg, ctx) {
    const {
      user,
      readOnly,
      messagesById,
      onReply,
      onEdit,
      onDelete,
    } = ctx;
    const msgId = Number(msg.id || msg.message_id);
    messagesById.set(msgId, msg);
    const isMe = Number(msg.sender_id) === Number(user.id) || msg.sender_email === user.email;
    const isDeleted = Boolean(msg.is_deleted);
    const createdMs = Date.parse(msg.created_at || "") || 0;
    const editRemainingMs = createdMs ? Math.max(0, 300000 - (Date.now() - createdMs)) : 0;
    const canEdit =
      isMe &&
      !isDeleted &&
      !readOnly &&
      (msg.message_type || "text") === "text" &&
      editRemainingMs > 0;
    const canDelete = (isMe || user.role === "admin") && !isDeleted && !readOnly;

    const replyParent = msg.reply_to_message_id
      ? messagesById.get(Number(msg.reply_to_message_id))
      : null;
    const replySnippet = replyParent
      ? `<div class="mb-1.5 px-2.5 py-1 rounded-lg text-[10px] ${
          isMe ? "bg-emerald-900/40 text-emerald-100" : "bg-slate-100 text-slate-600"
        } border-l-2 border-emerald-400 truncate">En respuesta a ${esc(replyParent.sender_email)}: ${esc(replyParent.message).slice(0, 70)}</div>`
      : "";

    const attachmentsHtml =
      !isDeleted && Array.isArray(msg.attachments) && msg.attachments.length
        ? `<div class="mt-2 space-y-1.5">${msg.attachments
            .map((att) => {
              const url = esc(att.signed_download_url || "");
              const name = esc(att.original_name || "adjunto");
              if (att.is_audio) {
                return `
                  <div class="p-2 rounded-xl ${isMe ? "bg-emerald-900/40" : "bg-slate-100"} space-y-1">
                    <audio controls preload="none" src="${url}" class="w-full max-w-[240px] h-8"></audio>
                    <a href="${url}" target="_blank" rel="noopener" class="inline-block text-[10px] underline">${name}</a>
                  </div>
                `;
              }
              return `
                <a href="${url}" target="_blank" rel="noopener" class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-medium ${
                  isMe ? "bg-emerald-900/50 text-white hover:bg-emerald-900/70" : "bg-slate-100 text-slate-800 hover:bg-slate-200"
                }">
                  <span>Descargar: ${name} (${Math.max(1, Math.round(Number(att.size_bytes || 0) / 1024))} KB)</span>
                </a>
              `;
            })
            .join("")}</div>`
        : "";

    const statusBadge = isMe
      ? `<span class="text-[10px] text-slate-600 ml-1">${msg.is_read || msg.read_at ? "Leído" : "Entregado"}</span>`
      : "";
    const editedBadge =
      msg.edited_at && !isDeleted
        ? `<span class="text-[10px] ${isMe ? "text-emerald-200" : "text-slate-600"} italic ml-1">(editado)</span>`
        : "";

    const box = document.createElement("div");
    box.setAttribute("data-message-id", String(msgId));
    box.className = (isMe ? "flex flex-col items-end gap-0.5" : "flex flex-col items-start gap-0.5") + " casagbi-msg-enter";
    box.innerHTML = `
      <span class="text-[10px] text-slate-600">${esc(msg.sender_email)} · ${esc(msg.sender_role)}</span>
      <div class="max-w-[85%] rounded-2xl px-3.5 py-2 text-xs leading-relaxed ${
        isDeleted
          ? "bg-slate-100 border border-slate-200 text-slate-600 italic"
          : isMe
            ? "bg-[#006837] text-white rounded-br-sm"
            : "bg-white border border-slate-200 text-slate-800 rounded-bl-sm"
      }">
        ${replySnippet}
        <div>${isDeleted ? "Este mensaje fue eliminado" : esc(msg.message).replaceAll("\n", "<br/>")}${editedBadge}</div>
        ${attachmentsHtml}
      </div>
      <div class="flex items-center gap-2 px-1">
        ${statusBadge}
        ${!isDeleted && !readOnly ? `<button type="button" data-reply-msg="${msgId}" class="text-[10px] text-slate-600 hover:text-[#006837] cursor-pointer">Responder</button>` : ""}
        ${canEdit ? `<button type="button" data-edit-msg="${msgId}" class="text-[10px] text-slate-600 hover:text-[#006837] cursor-pointer">Editar</button>` : ""}
        ${canDelete ? `<button type="button" data-delete-msg="${msgId}" class="text-[10px] text-red-700 hover:text-red-900 cursor-pointer">Eliminar</button>` : ""}
      </div>
    `;

    box.querySelector("[data-reply-msg]")?.addEventListener("click", () => onReply(msg));
    const editBtn = box.querySelector("[data-edit-msg]");
    if (editBtn) {
      editBtn.addEventListener("click", () => onEdit(msg, msgId));
      if (editRemainingMs > 0 && editRemainingMs < 360000) {
        ctx.scheduleEditButtonHide(editBtn, editRemainingMs);
      }
    }
    box.querySelector("[data-delete-msg]")?.addEventListener("click", () => onDelete(msgId));
    return box;
  }

  function renderAttachmentsPreview(files, onRemove) {
    const preview = document.getElementById("chat-attachments-preview");
    if (!preview) return;
    if (!files.length) {
      preview.classList.add("hidden");
      preview.innerHTML = "";
      return;
    }
    preview.classList.remove("hidden");
    preview.innerHTML = files
      .map(
        (f, idx) => `
        <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white border border-slate-300 text-slate-700">
          <span>${esc(f.name)} (${Math.max(1, Math.round(f.size / 1024))} KB)</span>
          <button type="button" data-remove-att="${idx}" aria-label="Quitar archivo" class="text-red-700 font-bold cursor-pointer">x</button>
        </span>
      `
      )
      .join("");
    preview.querySelectorAll("[data-remove-att]").forEach((btn) => {
      btn.addEventListener("click", () => onRemove(Number(btn.getAttribute("data-remove-att"))));
    });
  }

  const api = { renderLoading, renderMessageBubble, renderAttachmentsPreview };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.CasagbiChatView = api;
})(typeof globalThis !== "undefined" ? globalThis : window);
