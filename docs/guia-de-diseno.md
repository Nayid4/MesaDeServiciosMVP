# Guía de Diseño y Accesibilidad — CASAGBI (Mesa de Servicios TIC UPC)

Este documento define el sistema de diseño oficial de **CASAGBI** sobre **Tailwind CSS v4 (`@theme`)**, su arquitectura modular *Screaming Architecture* (*Smart/Dumb*) en `src/presentation/web/`, las decisiones basadas en heurísticas de Nielsen y leyes de UX, y los criterios de accesibilidad WCAG 2.1 AA.

---

## 1. Tokens de Diseño (`@theme` en `base.html` e `input.css`)

### Paleta Institucional UPC y Contrastes Verificados (WCAG 2.1 AA $\ge 4,5:1$)

| Token | Valor HEX | Uso principal | Contraste sobre `#FFFFFF` / `#F8FAFC` |
|---|---|---|---|
| `--color-upc-primary` | `#006837` | Botones primarios, radicados, foco `:focus-visible` | `7,08:1` (AAA) con texto blanco |
| `--color-upc-dark` | `#004D28` | Hover primario, badges activos sobre verde claro | `9,87:1` (AAA) con texto blanco |
| `--color-upc-accent` | `#10B981` | Indicadores positivos, acentos en barra oscura | Reservado a decoradores / fondo oscuro |
| `--color-upc-surface` | `#F6F8FA` | Lienzo principal del workspace y portales | Base de alto contraste con texto `#0F172A` / `#475569` |
| `--color-upc-slate` | `#0F172A` | Títulos (`slate-900`), texto principal | `17,85:1` (AAA) |
| `--color-upc-navy` | `#0D1522` | Barra lateral institucional de navegación del workspace | Contraste `> 10:1` con texto `#CBD5E1` / `#FFFFFF` |
| Texto secundario | `#475569` (`slate-600`) | Etiquetas, subtítulos, metadatos (reemplaza `slate-400`/`500` sobre fondo claro) | `7,58:1` (AAA) sobre `#FFFFFF` |
| `--color-upc-danger` | `#B91C1C` | Alertas de error, SLA vencido (junto con etiqueta textual) | `6,47:1` (AA+) |
| `--color-upc-warning` | `#B45309` | Avisos de riesgo SLA / DEMO_MODE (junto con etiqueta) | `5,02:1` (AA) |
| `--color-upc-info` | `#1D4ED8` | Estado `En espera` (SLA pausado) | `6,70:1` (AA+) |

### Tipografía, Rejilla de 8 px, Radios, Sombras y Duraciones

- **Tipografía (`--font-sans` / `--font-mono`):** `Inter / Segoe UI / system-ui` para lectura y tablas con `tabular-nums`; `JetBrains Mono / monospace` para códigos `MS-<CAT>-AAAA-NNNNNN` e identificadores técnicos.
- **Rejilla espacial de 8 px:** Múltiplos consistentes (`0.5rem` = 8 px, `1rem` = 16 px, `1.5rem` = 24 px, `2rem` = 32 px) para márgenes entre tarjetas (`gap-4`, `gap-5`), rellenos (`p-4`, `p-5`, `p-6`) y alturas mínimas (`h-16` = 64 px).
- **Radios y elevación:** `--radius-card: 1rem` (`rounded-2xl`), `--radius-control: 0.75rem` (`rounded-xl`), `--shadow-card` sutil y `--shadow-float` para paneles flotantes.
- **Movimiento (`transform` y `opacity`, `150–300 ms`):**
  - `--duration-fast: 150ms`, `--duration-base: 240ms`, `--duration-slow: 300ms`.
  - Solo anima `transform` y `opacity` (`casagbi-reveal`, `casagbi-msg-enter`, transiciones de botón y drawer móvil).
  - `@media (prefers-reduced-motion: reduce)` desactiva transiciones, animaciones y contadores progresivos de inmediato.

---

## 2. Arquitectura Modular y Los 5 Estados por Pantalla

Bajo `src/presentation/web/static/js/`:
- **`core/`**: `utils.js` (debounce 350 ms, `America/Bogota`, URL params, reveal), `reactive_store.js` (sesión, tema, notificaciones, caché TTL), `auth_store.js`, `api_client.js` (`AbortController` por `requestKey`, CSRF/JWT, RFC 7807), `router.js` (guardas RBAC y ciclo `mount()` / `destroy()`).
- **`shared/`**: componentes *dumb* reutilizables (`icons.js`, `skeleton_loader.js`, `toast.js`, `modal.js`, `empty_error_state.js`).
- **`features/`**: módulos por dominio funcional (`landing/`, `auth/`, `analytics_home/`, `tickets/`, `chat/`, `knowledge_base/`, `ai_agent/`, `ml_laboratory/`). Todo archivo `*_view.js` es puro (*dumb*: no realiza `fetch` ni abre `WebSocket`) y todo `*_container.js` es inteligente (*smart*: expone `mount()` / `destroy()` y cancela peticiones/sockets/timers al salir).

Cada vista cubre los **5 estados obligatorios**:
1. **Cargando (Skeleton):** Altura mínima reservada (`min-h-[104px]`, `renderKpiSkeleton`, `renderTableSkeleton`, `renderKbSkeleton`) evitando saltos de diseño (`CLS < 0,1`).
2. **Vacío:** Mensaje descriptivo y sugerencia de acción (`CasagbiEmptyErrorState.renderEmptyState`).
3. **Error con salida clara:** Bloque `role="alert"` con el detalle RFC 7807 y botón explícito **Reintentar** (`renderErrorState`).
4. **Éxito:** Confirmación inmediata vía *toast* accesible (`role="status"` / `aria-live="polite"`) y actualización en sitio.
5. **Sin permisos (RBAC):** Rutas ocultas por rol en `CasagbiRouter`, rechazo HTTP `403` RFC 7807 en API y vista informativa `renderForbiddenState`.

---

## 3. Decisiones Basadas en Heurísticas de Nielsen y Leyes de UX

1. **Visibilidad del estado del sistema & Doherty (`< 400 ms` / feedback inmediato):** Skeletons previos, indicador `"Buscando..."` durante búsquedas con `debounce` de `350 ms`, estado WS (`En vivo WS` / `Reconectando`), contadores animados y reloj de grabación de voz.
2. **Ley de Hick:** Menú lateral filtrado estrictamente por rol RBAC; el Home del Dashboard presenta máximo 4 KPIs clave y filtros directos antes de profundizar. En el Hero de Landing se priorizan exactamente 3 acciones principales (*Reportar*, *Consultar Ticket*, *Asistente IA*).
3. **Ley de Fitts:** Botones primarios amplios (`px-5 py-3`, área táctil $\ge 44\text{ px}$), filas de tickets completas interactivas y botón flotante del Agente IA anclado en la esquina inferior derecha.
4. **Ley de Jakob:** Patrón estándar de *sidebar* colapsable izquierdo en escritorio + *drawer* superior izquierdo en móvil, *topbar* con breadcrumb + campana + cerrar sesión, y chat de doble burbuja derecha/izquierda.
5. **Prevención de errores y recuperación:** Botón **Radicar** deshabilitado durante el envío + `Idempotency-Key`, validación en vivo de correo `@unicesar.edu.co` antes del `POST /login`, confirmación explícita en borrado lógico y recarga automática ante `409 Conflict`.
6. **Ayuda y documentación:** Base de Conocimiento pública integrada en Landing y Workspace con búsqueda instantánea y FAQs en acordeón.

---

## 4. Checklist de Accesibilidad (WCAG 2.1 AA)

- Enlace `Saltar al contenido principal` (`.sr-only focus:not-sr-only`) al inicio de `base.html`.
- Foco visible global (`outline: 2px solid #006837; outline-offset: 2px`) y filas de tickets operables por teclado (`tabindex="0"`, `Enter` / `Space`).
- Contenedores dinámicos con `aria-live="polite"` (toasts, indicadores de búsqueda, panel de mensajes del chat y resultados de consulta pública).
- **No depender solo del color:** El semáforo SLA (`Verde`, `Amarillo`, `Rojo`, `Azul`) siempre renderiza punto de color + texto descriptivo + porcentaje (`slaBadgeHtml`), y todo gráfico `Chart.js` incluye su **tabla HTML equivalente** con `<caption>` y `<th scope="col">`.
- Cero emojis en la interfaz (`100%` iconos SVG con `aria-hidden="true"`).

## 5. Patrones UI/UX Consolidados (Sprints 4 y 5)

- **Registro guiado de incidentes:** Formulario en una columna con validación al salir del campo (`blur`), sugerencia instantánea de artículos KB antes de radicar, adjuntos con vista previa y barra de progreso, borrador local recuperable y selector explícito de urgencia (*«¿Puede seguir trabajando?»*).
- **Bandeja operativa y detalle de ticket:** Tablas y colas con número de radicado, asunto, solicitante, prioridad, estado, semáforo SLA textual (`slaBadgeHtml`), filtros, vistas guardadas y paginación; detalle en dos columnas en escritorio (datos + línea de tiempo a la izquierda, chat en tiempo real a la derecha) con pestañas en pantallas móviles.
- **Base de Conocimiento versionada:** Editor con flujos `Borrador` / `En revisión` / `Publicado` / `Retirado`, historial comparativo de versiones y vista previa HTML sanitizada (`sanitize_kb_html`).
- **Widget flotante `Asistente CASAGBI`:**
  - Píldora flotante `CASAGBI ASISTENTE`, cabecera `#006837` y sección inicial `PUNTO ÚNICO DE CONTACTO` con accesos rápidos (`Consultar radicado`, `Wi-Fi Eduroam`, `Crear solicitud`).
  - Presentación única como asistente de IA al iniciar la conversación.
  - Si la confianza del clasificador es `< 0.60`, muestra lista manual de servicios para aclaración en lugar de forzar una categoría.
  - Solicita explícitamente `sede`, `location` y urgencia antes de generar el borrador editable (`draft_card`).
  - Incluye acceso permanente al botón visible **«Hablar con una persona»** (`#floating-ai-human-btn`) y respaldo automático al formulario manual tras `15 s` (`AGENT_TIMEOUT_MS = 15000`).
- **Shell operativo y vistas agregadas:** Barra lateral `#0D1522` dividida en `ESPACIO DE TRABAJO` (`Resumen`, `Gestión de tickets`, `Crear ticket`, `Base de conocimiento`) y `GESTIÓN` (`Personas y equipos`, `Informes y auditoría`, `Laboratorio MLOps` según RBAC); vista `Resumen` con datos reales de `GetKpiMetricsQueryHandler` (`Recibidos vs. Resueltos`, `Tickets por prioridad` y `Tickets que requieren atención`). Verificado en Chrome (`1440×900` y `390×844`) con puntajes **Lighthouse `100`** en Accessibility, Best Practices, SEO y Agentic Browsing.
