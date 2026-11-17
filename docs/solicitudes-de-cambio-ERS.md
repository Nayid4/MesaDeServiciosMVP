# Solicitudes de Cambio a la Especificación de Requisitos de Software (ERS) — CASAGBI

Este documento registra formalmente los conflictos y ampliaciones detectadas entre la evolución solicitada del proyecto **CASAGBI (Mesa de Servicios TIC UPC — ITIL v4)** y la línea base aprobada en la ERS original (`Sistema_Web_de_Mesa_de_Servicios_Universidad_Popular_del_Cesar.docx`), conservando los identificadores originales (`RF`, `CU`, `HU`, `RNF`, `RIU`, `RIS`, `OR`).

---

## SCR-01 · Chat en tiempo real con edición (primeros 5 minutos) y borrado lógico auditable

- **Identificadores originales afectados:** `RF-12`, `CU-05`, `HU-11`, `RNF-09`, `OR-01`.
- **Estado:** Implementado en **Sprint 2** (`PATCH/DELETE /api/v1/tickets/{id}/messages/{message_id}`, eventos WebSocket `message_edited`/`message_deleted`, tabla inmutable `message_versions` y registro en `audit_logs`).
- **Redacción actual en la ERS (`RF-12` / `OR-01` / `RNF-09`):**
  > *RF-12:* "Los mensajes no pueden editarse ni eliminarse después de enviados."
  > *OR-01:* "Los tickets y los mensajes no se eliminarán físicamente; se marcarán con estado Anulado o se archivarán."
  > *RNF-09:* "Las acciones relevantes deben poder atribuirse con certeza a un usuario y no deben poder alterarse después de registradas."
- **Conflicto detectado:** El usuario solicita permitir corrección tipográfica inmediata y retiro visual de mensajes en el chat del ticket.
- **Nueva redacción propuesta y aplicada:**
  > *RF-12 (Actualizado — SCR-01):* El sistema permitirá al autor de un mensaje de texto en un ticket abierto (`status` distinto de `Cerrado` o `Anulado`):
  > 1. **Editar** el texto del mensaje únicamente cuando el servidor verifique en tiempo UTC que `ahora_servidor_UTC - created_at <= 300 s`; fuera de ese plazo responde HTTP `403` RFC 7807 con código `EDIT_WINDOW_EXPIRED`. Cada edición marca el mensaje como `(editado)`.
  > 2. **Eliminar de forma lógica (*soft delete*)** el mensaje (`is_deleted = True`), mostrando a los participantes `"Este mensaje fue eliminado"` y emitiendo `message_deleted` por WebSocket.
  > 3. **Preservación para auditoría (`RNF-09`, `OR-01`, `RF-25`):** Ninguna edición o borrado lógico destruye datos; la tabla `message_versions` y `audit_logs` conservan inmutablemente cada contenido previo, acción, autor y marca temporal UTC.

---

## SCR-02 · Acceso externo sin sesión institucional mediante consulta por radicado + correo

- **Identificadores originales afectados:** `RF-01`, `RF-09`, `CU-01`, `CU-03`, `HU-01`, `HU-08`, `RNF-07`.
- **Estado:** Implementado en **Sprint 2** (`POST /api/v1/tickets/public/lookup`, verificación en tiempo constante, limitación de intentos por IP y radicado, `ticket_guest_token` 2 h con correo enmascarado y bandera opcional `GUEST_OTP_ENABLED=false`).
- **Redacción actual en la ERS (`RF-01` / `CU-03` / `RNF-07`):**
  > *RNF-07:* "Solo usuarios autenticados con cuenta institucional pueden acceder, y cada uno únicamente a las funciones y datos que su rol permite."
  > *CU-03:* Precondición "El usuario inició sesión (CU-01)."
- **Conflicto detectado:** Se requiere permitir consulta rápida desde el exterior sin inicio de sesión completo, evitando a la vez la enumeración libre de radicados o la exposición de datos personales de terceros (`OR-05`, `RNF-08`).
- **Nueva redacción propuesta y aplicada:**
  > *RF-09 / RNF-07 (Actualizado — SCR-02):* Además del acceso autenticado completo (`CU-01`), `POST /api/v1/tickets/public/lookup` exige `{ticket_code, email}` comparando en tiempo constante sin distinguir mayúsculas y devolviendo respuestas indistinguibles ante radicado inexistente o correo incorrecto. El control de tasa por IP y por radicado (`public_lookup_attempts`) bloquea con HTTP `429` tras intentos fallidos y audita en `audit_logs`. Al validar, se emite `ticket_guest_token` (2 h, rol `invitado`) estrictamente acotado al ticket consultado, con correos enmascarados (`ka***@unicesar.edu.co`) y soporte opcional de segundo factor OTP vía `GUEST_OTP_ENABLED` (apagada por defecto).

---

## SCR-03 · Evolución de la nomenclatura del radicado de `MS-AAAA-NNNNNN` a código por categoría

- **Identificadores originales afectados:** `RF-04`, `CU-02`, `HU-04`.
- **Estado:** Implementado en **Sprint 1** con tabla de prefijos derivada del catálogo oficial y conservación de alias heredado `MS-AAAA-NNNNNN` en `legacy_ticket_number` (`[CONFIRMAR aprobación final de tabla con Dirección TIC UPC]`).
- **Redacción actual en la ERS (`RF-04`):**
  > "Al guardar, el sistema asigna un consecutivo con el formato `MS-AAAA-NNNNNN` y lo muestra al usuario."
- **Conflicto detectado:** Se migra el Value Object `TicketCode` (`MS-AAAA-NNNNNN`) hacia una nomenclatura que incorpora el código de categoría del servicio TIC para facilitar trazabilidad por área.
- **Tabla oficial de prefijos implementada (derivada de `UPC_SERVICE_CATALOG`):**

  | Prefijo | Servicio del Catálogo UPC | Área Técnica | Ejemplo |
  |---|---|---|---|
  | `MS-RED-` | Conectividad y Redes Wi-Fi | Redes e Infraestructura | `MS-RED-2026-000001` |
  | `MS-SIS-` | Plataformas Académicas (Aula Web / Vortal) | Sistemas de Información | `MS-SIS-2026-000001` |
  | `MS-ACC-` | Correo Institucional y Cuentas | Identidad y Accesos | `MS-ACC-2026-000001` |
  | `MS-AUL-` | Aulas Inteligentes y Videoproyectores | Soporte en Campo | `MS-AUL-2026-000001` |
  | `MS-SOP-` | Equipos de Cómputo e Impresoras | Soporte en Campo | `MS-SOP-2026-000001` |
  | `MS-SWL-` | Software y Licenciamiento | Mesa de Software | `MS-SWL-2026-000001` |
  | `MS-GEN-` | Servicios generales / personalizados | Según catálogo | `MS-GEN-2026-000001` |

- **Nueva redacción propuesta y aplicada:**
  > *RF-04 (Actualizado — SCR-03):* Al guardar un ticket, el sistema asignará un código único institucional generado atómicamente por `(category_prefix, ticket_year)` con formato `MS-<CAT>-AAAA-NNNNNN` (`TicketCode`). Los radicados existentes en formato `MS-AAAA-NNNNNN` se migran de forma idempotente y se conservan en el campo único `legacy_ticket_number` como alias retrocompatible para consulta pública, búsquedas en bandeja y herramienta `check_ticket` del agente IA.

---

## SCR-04 · Notas de voz (audios) y ampliación de formatos de archivos adjuntos

- **Identificadores originales afectados:** `RF-04`, `RF-13`, `CU-02`, `CU-05`, `HU-04`, `HU-11`, `RNF-08`, `RIH-02`.
- **Estado:** Implementado en **Sprint 2** (`POST /api/v1/tickets/{id}/attachments`, validación real por *magic bytes*, almacenamiento privado fuera de `static/`, descargas firmadas HMAC por 10 minutos con `Content-Disposition` y `X-Content-Type-Options: nosniff`, y grabadora web compatible con Chrome/Firefox y Safari).
- **Redacción actual en la ERS (`RF-04` / `RF-13` / `RNF-08`):**
  > *RF-04:* "Se aceptan adjuntos JPG, PNG, PDF, DOCX y XLSX de hasta 10 MB cada uno."
  > *RNF-08:* "Los adjuntos se almacenan fuera de la raíz pública y se descargan mediante enlaces firmados con vigencia de 10 minutos."
- **Conflicto detectado:** Se amplía la captura de evidencias para admitir notas de voz (archivos de audio) y nuevos formatos técnicos de soporte.
- **Nueva redacción propuesta y aplicada:**
  > *RF-13 / RNF-08 (Actualizado — SCR-04):* Se admiten imágenes (`JPG`, `PNG`, `WEBP`), documentos (`PDF`, `DOCX`, `XLSX`, `TXT`) y notas de voz (`WEBM`, `OGG`, `MP3`, `WAV`, `M4A`/`MP4`, duración máxima `180 s`), hasta **5 archivos por mensaje** y **10 MB por archivo**. Quedan prohibidos `ZIP`, `SVG`, `HTML` y ejecutables (`EXE`, `ELF`, scripts `#!`). Cada archivo se valida por **firma binaria real (*magic bytes*)**, se sanea el nombre, se guarda con UUID fuera del directorio estático y se descarga mediante enlace firmado HMAC de **10 minutos** con `Content-Disposition: attachment` y `X-Content-Type-Options: nosniff`.

---

## SCR-05 · Autenticación propia con JWT en el MVP frente a OpenID Connect (OIDC) institucional

- **Identificadores originales afectados:** `RF-01`, `CU-01`, `HU-01`, `RNF-07`, `RNF-16`, `RIU-01`, `RIS-01`.
- **Estado:** Decisión arquitectónica temporal de MVP implementada; pendiente integración con proveedor institucional `[CONFIRMAR endpoint OIDC / IdP UPC]`.
- **Redacción actual en la ERS (`RIU-01` / `RNF-07` / `RIS-01`):**
  > *RIU-01:* "La pantalla de inicio mostrará el nombre del sistema, el logo institucional y un único botón Ingresar con cuenta institucional; no habrá formulario propio de usuario y contraseña."
  > *RNF-07:* "La autenticación se delega al proveedor de identidad institucional mediante OpenID Connect; el sistema no almacena contraseñas."
- **Conflicto detectado / Decisión de MVP:** Dado que durante el desarrollo del proyecto académico no se dispone de acceso al proveedor de identidad OIDC real de la Universidad Popular del Cesar (`[CONFIRMAR]`), el MVP implementa autenticación propia con validación de dominio institucional `@unicesar.edu.co`, hashing `bcrypt`, `access_token` JWT (15 min) y `refresh_token` opaco rotativo en SQLite (7 días), manteniendo el botón/flujo rápido de pruebas estrictamente protegido detrás de la bandera `DEMO_MODE` apagada por defecto en producción (`DEMO_MODE=false`).
- **Nueva redacción propuesta (transición a producción):**
  > *RF-01 / RIS-01 / RNF-16 (Propuesto):* Durante la fase MVP se autoriza el adaptador local JWT/`bcrypt` aislado tras los puertos de aplicación (`src/application/auth/`). Para el paso a producción institucional, dicho adaptador se sustituirá sin modificar dominio ni casos de uso por el adaptador **OpenID Connect 1.0 sobre OAuth 2.0** conectado al directorio `@unicesar.edu.co`, ocultando el formulario local de usuario y contraseña conforme a `RIU-01` y cumpliendo el tiempo de expiración de sesión por inactividad de `30 minutos` (`RF-01`, `RNF-07`).

---

## SCR-06 · Gobernanza de IA Determinista, Umbral de Confianza 0.60 y Privacidad (Sprint 5)

- **Contexto:** En el diagnóstico del Sprint 0 se comprobó que el clasificador NLP asignaba erróneamente incidentes de cómputo (`"computadora que no prende"`) a videoproyectores por bigramas funcionales ruidosos (`"lo que no"`) y vocabulario TIC limitado, mientras el agente conversacional asumía sede (`Sede Sabanas`), ubicación (`Bloque A`) y prioridad (`P3`) sin consultar al usuario.
- **Cambio aplicado:**
  - **Prioridad y SLA estrictamente deterministas (`OR-03`):** El agente IA (`ProcessAgentTurnCommandHandler`) ya no infiere prioridad ni asume `sede`, `location` o `urgency`. Recoge explícitamente esos tres datos y calcula la prioridad (`P1`–`P4`) mediante `compute_priority_matrix` (`OR-03`).
  - **Calibración y abstención (`MIN_CONFIDENCE_THRESHOLD = 0.60`):** Por debajo de `0.60` o sin señales técnicas mínimas de dominio, el agente responde `needs_clarification` ofreciendo selección manual del catálogo de servicios.
  - **Saneado PII y contingencia (`RNF-06`):** `scrub_pii_for_model` anonimiza correos, teléfonos y cédulas antes de consultar el clasificador; la interfaz garantiza un botón permanente `"Hablar con una persona"` y respaldo automático al formulario manual si el servicio tarda más de `15 s`.

---

## Consolidado de Elementos Pendientes de Validación Institucional (`[CONFIRMAR]`)

| Código / Área | Elemento implementado en el MVP | Decisión requerida del dueño del producto (`UPC`) |
| --- | --- | --- |
| Identidad visual (`guia-de-diseno.md`) | Paleta `#006837` / `#10B981` y tipografía UI | Confirmar manual oficial de marca institucional UPC |
| Radicados (`SCR-03`) | Prefijos por categoría `MS-<CAT>-AAAA-NNNNNN` (`RED`, `SIS`, `ACC`, `AUL`, `SOP`, `SWL`) | Aprobar códigos definitivos y conservación de alias históricos `MS-AAAA-NNNNNN` |
| Autenticación (`RIS-01`, `SCR-04`) | JWT + `bcrypt` local y `DEMO_MODE=false` en producción | Conectar proveedor **OIDC / OAuth 2.0** `@unicesar.edu.co` real |
| Notificaciones y OTP (`RIS-04`) | Outbox local de desarrollo para `GUEST_OTP_ENABLED` | Definir servidor **SMTP** institucional y política final de OTP para invitados |
| Adjuntos y multimedia (`SCR-04`) | Límite de audio y formatos permitidos en chat por ticket | Confirmar lista blanca de extensiones y duración máxima |
| Catálogo y KB inicial (`kb_seed_data.py`) | `42` artículos de ejemplo `[DEMO]` y matriz SLA `OR-03` | Validar textos oficiales, sedes, bloques y tiempos SLA definitivos |

---

*Nota de gobierno de requisitos:* Ninguna cifra oficial de SLA modificado, URL productiva institucional, directorio OIDC o tabla definitiva de categorías se asume sin validación del dueño del producto (`[CONFIRMAR]`).
