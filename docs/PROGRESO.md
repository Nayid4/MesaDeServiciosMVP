# Registro de Progreso — CASAGBI (Mesa de Servicios TIC UPC · ITIL v4)

> Documento vivo actualizado al cierre de cada sprint/bloque conforme a las reglas de trabajo del proyecto.

---

## Sprint 0 · Diagnóstico (Solo Lectura) — Completado

### Hecho
- Auditoría completa de solo lectura documentada en [docs/00-diagnostico.md](00-diagnostico.md):
  - Mapa real del repositorio, diagrama de flujo y **4 violaciones de Clean Architecture** localizadas por archivo y línea (`application/auth`, `application/analytics`, `application/ai_agent` importando infraestructura y `admin_dashboard.js` monolítico).
  - Matriz de brechas requisito por requisito frente a la ERS (`RF-01`–`RF-25`, `RNF-01`–`RNF-17`, `RIU-01`–`RIU-10`, `RIC-02`, `OR-01`–`OR-10`).
  - Evaluación de las **10 heurísticas de Nielsen**, problemas medidos de accesibilidad WCAG 2.1 AA (`18` usos de `text-slate-400` con contraste `< 4,5:1`, `aria-live = 0`, gráficos sin tabla equivalente) y rendimiento (`debounce = 0`, `AbortController = 0`, ausencia de *skeletons*).
  - **Reproducción y causa raíz empírica** del fallo `"tengo un problema con una computadora que no prende"` (`Aulas Inteligentes y Videoproyectores`, `Sede Sabanas (Valledupar)`, `Bloque A`, `P3 Media`): OOV de `computadora`/`prende` (`0` apariciones en `upc_tickets_clean.csv`), ausencia de `stop_words` en TF-IDF, sesgo de plantilla en el bigrama `"que no"` (`log_prob = -6,1693` vs `-10,2345`), sobreconfianza de `MultinomialNB` sin umbral `< 0,60`, y valores por defecto silenciosos en `extract_campus_entities()` / `_build_draft_card()`.
  - Inventario de **9 riesgos de seguridad y concurrencia** (consecutivo no atómico, condición de carrera en asignación, falta de concurrencia optimista `version`, ausencia de `Idempotency-Key`, JWT en URL WebSocket, enumeración en `/public/{code}` y falta de *magic bytes* / enlaces firmados en adjuntos).
  - Lista consolidada de supuestos, elementos `[CONFIRMAR]` y plan ajustado de Sprints 1 a 5 pendiente de confirmación del usuario.
- Verificación sin modificaciones de código fuente (`pytest`: 26 pruebas en verde).

---

## Bloque 0 · Línea Base, Solicitudes de Cambio y `DEMO_MODE` — Completado

### Hecho
- Documentados los 6 conflictos/evoluciones frente a la ERS en [docs/solicitudes-de-cambio-ERS.md](solicitudes-de-cambio-ERS.md) (`SCR-01` a `SCR-06`).
- Implementada y probada la bandera `DEMO_MODE` apagada por defecto (`false`), ocultando perfiles ficticios de demostración en producción y redactando correos de terceros en consultas públicas.

---

## Sprint 1 · Radicados por Categoría, Concurrencia e Idempotencia — Completado

### Hecho
- **Nomenclatura por categoría (`SCR-03`) y alias legado:** Actualizados `src/domain/rules.py` (`SERVICE_CATEGORY_PREFIXES`, `VALID_CATEGORY_PREFIXES`, `CATEGORY_TICKET_NUMBER_PATTERN`, `LEGACY_TICKET_NUMBER_PATTERN`, `get_service_prefix`), `src/domain/value_objects/__init__.py` (`TicketCode`) y `src/infrastructure/ml/ai_engine.py` (`TICKET_ID_REGEX`) para soportar `MS-<CAT>-AAAA-NNNNNN` (`RED`, `SIS`, `ACC`, `AUL`, `SOP`, `SWL`, `GEN`) y conservar compatibilidad con `MS-AAAA-NNNNNN` mediante `legacy_ticket_number`.
- **Consecutivo atómico y SQLite `BEGIN IMMEDIATE`:** Creada la tabla `ticket_counters` (`prefix`, `year`, `last_seq`), configurada explícitamente `isolation_level = None` + evento `begin` con `BEGIN IMMEDIATE` en `src/infrastructure/persistence/database.py`, añadido `begin_immediate()` en `SqlAlchemyUnitOfWork` / `IUnitOfWork`, y añadidas doble barreras únicas (`ticket_number` y `uq_tickets_prefix_year_seq`).
- **Migración idempotente + Seeder:** `_migrate_schema_and_legacy_tickets()` en `database.py` agrega columnas y migra radicados históricos guardando `legacy_ticket_number` y sincronizando `ticket_counters`; `seeder.py` precarga prefijos y los 6 tickets semilla con su alias legado.
- **Idempotencia y deduplicación exacta en 2 minutos:** Creada tabla `idempotency_keys` (`UNIQUE (user_id, idempotency_key)`), cabecera `Idempotency-Key` en `POST /api/v1/tickets` (devolviendo HTTP `200` en replay vs `201` en creación), hash SHA-256 exacto (`compute_content_dedup_hash`) sobre `(user_id, service_name, normalized_title)` dentro de 2 minutos sin similitud difusa, y bloqueo visual del botón de envío en `admin_dashboard.js`.
- **Asignación concurrente segura (`RF-06`) y cola del coordinador:** Cálculo de menor carga y actualización de `last_assigned_at` dentro de la misma transacción `BEGIN IMMEDIATE`; cuando no existen técnicos activos en el área, el ticket permanece en estado `Registrado` con evento de auditoría `"En cola del coordinador (sin técnicos activos)"` y notificación a coordinadores/administradores activos.
- **Concurrencia optimista (`version` -> HTTP 409):** Columna `version` en `tickets`, actualización atómica condicional `WHERE id = :tid AND version = :expected_version` en `SqlAlchemyTicketRepo.update()`, captura en transiciones/reasignaciones/calificación devolviendo RFC 7807 `409 Conflict`, y recarga automática en `admin_dashboard.js`.
- **Documentación actualizada:** `docs/solicitudes-de-cambio-ERS.md` (`SCR-03`), `docs/PROGRESO.md` y `README.md`.

## Sprint 2 · Chat Multimedia y Acceso Externo Seguro — Completado

### Hecho
- **Consulta externa segura y sesión invitado (`SCR-02`):** Implementado `POST /api/v1/tickets/public/lookup` con comparación en tiempo constante (`hmac.compare_digest` + SHA-256 sin distinguir mayúsculas), respuestas idénticas anti-enumeración, control de tasa por IP y radicado en `public_lookup_attempts` con bloqueo `429` y auditoría en `audit_logs`, emisión de `ticket_guest_token` (2 h, rol `invitado` restringido al ticket), correos enmascarados (`ka***@unicesar.edu.co`) y bandera `GUEST_OTP_ENABLED` (apagada por defecto, consola/outbox en demo).
- **Autenticación WebSocket segura:** Emitido `POST /api/v1/tickets/{id}/ws-ticket` (un solo uso y 60 s en `ws_connection_tickets`) y autenticación alternativa en el primer mensaje (`?auth=first_message` + `{"type": "auth", ...}` sin credenciales en URL), además de revalidación de pertenencia al ticket en cada evento entrante. Se mantiene `?token=` deprecado solo por retrocompatibilidad con clientes heredados.
- **Mensajería avanzada (`SCR-01`):** Ampliado `ticket_messages` con `client_message_id` (idempotencia por autor), `reply_to_message_id`, `created_at` UTC del servidor, `edited_at`, `is_deleted`, `delivered_at`, `read_at` y tabla `message_versions`. Edición validada en servidor `<= 300 s` (`EDIT_WINDOW_EXPIRED` `403` RFC 7807 si excede), borrado lógico con leyenda `"Este mensaje fue eliminado"` conservando el original en `message_versions`/`audit_logs`, eventos WS de lectura, `typing`, reconexión con cola pendiente y polling de respaldo cada `5 s` (`RIC-02`).
- **Adjuntos multimedia y audio (`SCR-04`, `RNF-08`):** `POST /api/v1/tickets/{id}/attachments` con límite de 5 archivos / 10 MB y duración máxima de audio `180 s`, validación estricta por *magic bytes* (`JPG`, `PNG`, `WEBP`, `PDF`, `DOCX`/`XLSX` OOXML, `TXT`, `WEBM`, `OGG`, `MP3`, `WAV`, `M4A`/`MP4`), bloqueo de ejecutables/`SVG`/`HTML`/`ZIP`, almacenamiento UUID fuera de `static/` y descarga por enlace firmado de 10 minutos (`GET .../download`) con `Content-Disposition` y `X-Content-Type-Options: nosniff`.
- **Cliente web e inactividad 30 min:** Actualizados `auth_store.js` (cierre tras 30 min de inactividad + sesiones invitado), `ticket_chat_ws.js`, `dashboard.html`, `admin_dashboard.js` (grabadora `MediaRecorder` compatible con Chrome/Safari, edición ≤ 5 min y borrado con escape XSS), `landing.html` y `landing.js`.
- **Documentación actualizada:** `docs/solicitudes-de-cambio-ERS.md` (`SCR-01`, `SCR-02`, `SCR-04`), `docs/PROGRESO.md` y `README.md`.

## Sprint 3 · Arquitectura del Front, Sistema de Diseño, Landing, Login y Shell del Dashboard — Completado

### Hecho
- **Screaming Architecture (`src/presentation/web/static/js/`):** Refactorización completa en `core/` (`utils.js`, `reactive_store.js`, `auth_store.js`, `api_client.js` con `AbortController` por `requestKey` y caché TTL, `router.js` con guardas RBAC y ciclo `mount()`/`destroy()`), `shared/` (`icons.js` 100% SVG, `skeleton_loader.js`, `toast.js`, `modal.js`, `empty_error_state.js`) y 8 módulos funcionales en `features/` (`landing/`, `auth/`, `analytics_home/`, `tickets/`, `chat/`, `knowledge_base/`, `ai_agent/`, `ml_laboratory/`), todos estrictamente separados en `*_view.js` (*dumb*, sin `fetch`/`WebSocket`) y `*_container.js` (*smart*).
- **Sistema de diseño y animaciones (`docs/guia-de-diseno.md`):** Documentados tokens `@theme`, ratios de contraste WCAG 2.1 AA ($\ge 4,5:1$), rejilla de 8 px, radios, sombras, transiciones sobre `transform`/`opacity` (`150–300 ms`), soporte `@media (prefers-reduced-motion: reduce)`, skeletons anti-CLS, los 5 estados por pantalla y las heurísticas de Nielsen / leyes de UX.
- **Landing completa (9 secciones + Ley 1581):** Cabecera fija con CTA, Hero con 3 acciones clave + métricas agregadas sin PII (`GetPublicSummaryQuery`), catálogo de servicios con prefijos y tiempos SLA, «Cómo funciona» en 4 pasos, consulta segura `{ticket_code, email}` + chat invitado, vista previa del Asistente IA, Base de Conocimiento pública con buscador (`debounce 350 ms` + `AbortController`), acordeón FAQ accesible, sedes/contacto `[CONFIRMAR]` y pie de privacidad Ley 1581 / `OR-05`.
- **Login y Dashboard (`RF-22` + `RIU-10`):** Login a dos paneles con validación en vivo de `@unicesar.edu.co`, mensajes claros de dominio/inactividad/error y `DEMO_MODE`. Dashboard con sidebar fijo colapsable en escritorio, drawer móvil con cierre por `Escape`, Home inicial `kpis` según alcance del rol, **tablas HTML equivalentes** para todos los gráficos, buscadores con `debounce 350 ms` + indicador `"Buscando..."` + sincronización en URL, y exportación oficial **`RIU-10` a CSV y PDF** (`GET /api/v1/analytics/export.csv` y `/export.pdf` con `pdf_generator.py`).
- **Capturas responsivas y verificación JS:** Generadas 9 capturas reales en `docs/screenshots/` (`landing`, `login` y `dashboard` a `360x800`, `768x1024` y `1440x900` px) con cero errores JS de runtime y cero desbordamiento horizontal; pruebas en Node.js y pytest en verde (`test_sprint3_frontend_architecture.py`).

## Sprint 4 · Gestión de Tickets (UI/UX) y Base de Conocimiento — Completado

### Hecho
- **Gestión de Tickets ITIL v4 (`RF-05`, `RF-08`, `RF-15`, `RF-16`, `RF-17`, `RIU-04`, `RIU-07`):**
  - Formulario de registro en una columna (`max-w-2xl`) con validación al salir de cada campo (`blur`), borrador automático en `localStorage`, pregunta clara de urgencia, sugerencia previa de artículos KB desde `POST /api/v1/tickets/classify-preview` y adjuntos con vista previa y barra de progreso.
  - Bandeja operativa y cola de coordinación con vistas guardadas (preestablecidas + personalizadas en `localStorage`), panel de carga de técnicos activos (`technician_loads`), filtros combinados, ordenamiento por prioridad y vencimiento SLA, paginación (`page`, `page_size`) y tabla con radicado, asunto/servicio, solicitante/sede, prioridad OR-03, estado, semáforo SLA en texto y técnico asignado.
  - Detalle en dos columnas en escritorio y pestañas móviles (`Ficha y Línea de Tiempo` / `Chat en Vivo`), ajuste de prioridad OR-03 con justificación obligatoria (`POST /api/v1/tickets/{id}/priority`), reasignación mostrando carga técnica, resolución técnica ($\ge 20$ caracteres), botón para proponer artículo KB desde el ticket, reapertura limitada a **3 días hábiles** (`OR-04` -> HTTP `409` al vencer) y calificación CSAT 1–5 con comentario obligatorio cuando es 1 o 2 (`422` si falta).
  - Notificaciones en plataforma con contador y preferencias configurables (`GET/PUT /api/v1/auth/notifications/preferences`, `POST /api/v1/auth/notifications/{id}/read`).
- **Base de Conocimiento Editorial (`RF-21`) y `42` Artículos de Demostración:**
  - Ampliado `src/infrastructure/persistence/kb_seed_data.py` y `seeder.py` con **42 artículos de demostración** marcados con `is_demo=True` y `[CONFIRMAR]` cubriendo las **9 categorías** (*Cuentas y correo*, *Wi-Fi y Eduroam* Windows/Android/iOS/LAN/Aruba, *Plataformas académicas*, *Impresión*, *Equipos de cómputo*, *Aulas y videoproyectores* HDMI/VGA, *Software y licencias*, *VPN* y *Seguridad básica*).
  - CRUD completo, flujo editorial por rol (`Borrador` $\rightarrow$ `En revisión` $\rightarrow$ `Publicado` / `devolver` con observaciones / `Retirado` / `restaurar`) restringiendo publicación/devolución/retiro/restauración a `coordinador`/`admin` (`403` para `tecnico`), saneado estricto HTML (`sanitize_kb_html`) contra XSS, historial versionado en `kb_article_versions` con comparación (`difflib`) y restauración a nueva versión.
  - Verificado que solo los artículos `Pública` + `Publicado` alimentan el buscador público y el asistente IA (los artículos en `Retirado` dejan de aparecer).
- **Documentación y pruebas:** Añadida suite `tests/test_sprint4_tickets_and_kb.py`; actualizados `docs/PROGRESO.md` y `README.md`.

## Sprint 5 · Agente IA, Verificación Final y Documentación — Completado

- **Corrección empírica del pipeline NLP (`src/infrastructure/ml/`):**
  - Actualizado `dataset_generator.py` ampliando sinónimos reales por servicio TIC y eliminando bigramas ruidosos (`"lo que no"`).
  - Añadidos `normalize_tic_synonyms`, `SPANISH_STOPWORDS`, `DOMAIN_SIGNAL_TERMS` y `MIN_CONFIDENCE_THRESHOLD = 0.60` en `model_trainer.py`, además de saneado de PII (`scrub_pii_for_model`) y extracción estricta de entidades explícitas (`extract_explicit_ticket_entities`) en `ai_engine.py`.
  - Ejecutado el pipeline CRISP-DM (`18,000` registros crudos -> `17,658` limpios, retención `98.1%`) y reentrenamiento 5-Fold CV (`keyword_baseline`: `cv_f1=0.8829`, `f1_macro=0.8847`, `acc=0.8785`; modelos entrenables `multinomial_nb` / `logistic_regression` / `linear_svc`: `cv_f1=0.9736`, `f1_macro=0.9708`, `acc=0.9731`, activo por menor latencia `0.2283 ms`: `linear_svc`, ganancia F1 vs baseline `+8.61%`).
- **Regresión Sprint 0 y evaluación de `105` frases (`agent_evaluator.py`, `docs/evaluacion-agente-ia.md`):**
  - Caso Sprint 0 (`"tengo un problema con una computadora que no prende"`): clasificado en `Equipos de Cómputo e Impresoras` con `97.68%` de confianza, sin suponer sede/ubicación/urgencia (`assumed_* = null`, `agent_status = "needs_missing_fields"`).
  - Resultados sobre `EVALUATION_DATASET_105`: `98.67%` en dominio (`74/75`), `100.0%` en frases con errores tipográficos (`20/20`) y `100.0%` en abstención/fuera de dominio (`30/30`).
- **Agente conversacional multi-turno y UI (`src/application/ai_agent/`, `src/presentation/web/`):**
  - Memoria de historial por sesión (`history`), presentación única como IA, despedidas y Q&A institucional (`OR-04`, sedes, `OR-03` y SLA), consulta de ticket como invitado con verificación `{ticket_code, email}` (`PublicTicketLookupCommandHandler`), borrador editable con cálculo determinista `OR-03`, botón permanente `"Hablar con una persona"` (`#floating-ai-human-btn`) y respaldo al formulario manual tras `15 s` (`AGENT_TIMEOUT_MS = 15000`).
- **Cierre técnico y auditoría:** Suite `tests/test_sprint5_ai_agent_and_closure.py`, verificación de credenciales demo aisladas en `src/infrastructure/persistence/seeder.py` bajo `DEMO_MODE`, pruebas de arranque `uvicorn` / configuración Docker Compose y actualización integral de `README.md`, `docs/evaluacion-agente-ia.md`, `docs/guia-de-diseno.md` y `docs/solicitudes-de-cambio-ERS.md`.

## Refactor Visual UI/UX y Verificación en Navegador — Completado

- **Shell institucional y vistas (`dashboard.html`, `base.html`, `admin_dashboard.js`):** Barra lateral azul marino `#0D1522` agrupada en `ESPACIO DE TRABAJO` y `GESTIÓN`, lienzo `#F6F8FA`, topbar operativo, nueva vista `Personas y equipos` (`#view-teams`), `Informes y auditoría` (`#view-audit` con exportación RIU-10 y aviso RBAC específico para roles sin acceso a `/audit-logs`) y rediseño de `Resumen`, `Gestión de tickets`, `Crear ticket`, `Base de conocimiento` y `Asistente CASAGBI`.
- **Datos reales en `Resumen` (`src/application/analytics/__init__.py`):** `GetKpiMetricsQueryHandler` expone `kpis.csat_count`, `open_by_priority`, `service_breakdown` (*Recibidos vs. Resueltos*) y `recent_attention_tickets` calculados sobre SQLite sin métricas simuladas.
- **Verificación real en Chrome (`1440×900` escritorio y `390×844` móvil) y Lighthouse:** Validada la autenticación real, navegación, vistas guardadas, filtros/búsqueda debounced, detalle 2 columnas/tabs móviles + WebSocket, creación de ticket con análisis IA (`MS-RED-2026-000002`), búsqueda/previsualización KB y chat del `Asistente CASAGBI`, corrigiendo en el ciclo final contraste WCAG AA (`>= 4,5:1`), nombres accesibles en `<select>` y controles, y formato de respuesta IA hasta alcanzar **Accessibility `100`, Best Practices `100`, SEO `100` y Agentic Browsing `100`** en escritorio y móvil.

### Decisiones Técnicas y Riesgos Vigentes
- Paleta verde `#006837` provisional (`[CONFIRMAR]` con manual de identidad visual UPC).
- Prefijos de categoría `SCR-03`, lista/duración de audios `SCR-04`, catálogo/artículos KB `[DEMO]`, endpoints OIDC/SMTP (`RIS-01`, `RIS-04`, `GUEST_OTP_ENABLED`) y datos de contacto de sedes marcados como `[CONFIRMAR]`.
- En entornos de demostración, mantener `DEMO_MODE=false` en producción garantiza que ningún acceso rápido de prueba se exponga desde la interfaz ni el endpoint público de demostración.
