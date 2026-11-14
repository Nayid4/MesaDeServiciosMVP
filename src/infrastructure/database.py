"""Gestión de base de datos SQLite (modo WAL), esquema relacional, inmutabilidad y seeders."""

from __future__ import annotations

import os
import sqlite3
from datetime import timedelta
from pathlib import Path
from typing import Optional

from src.domain.rules import (
    BOGOTA_TZ,
    SLA_BY_PRIORITY,
    UPC_SERVICE_CATALOG,
    add_business_hours,
    calculate_priority_or03,
    format_ticket_number,
    now_bogota,
)
from src.infrastructure.security import hash_password

DEFAULT_DB_PATH = Path("data/mesa_servicios_upc.db")


def get_db_path(custom_path: Optional[str | Path] = None) -> Path:
    """Resuelve la ruta de SQLite permitiendo aislar tickets_pruebas.db vs operación."""
    if custom_path is not None:
        return Path(custom_path)
    env_path = os.environ.get("CASAGBI_DB_PATH")
    if env_path:
        return Path(env_path)
    return DEFAULT_DB_PATH


def get_connection(db_path: Optional[str | Path] = None) -> sqlite3.Connection:
    """Abre conexión SQLite con modo WAL, claves foráneas activas y Row factory."""
    target = get_db_path(db_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target), check_same_thread=False, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn


def init_database(db_path: Optional[str | Path] = None, seed: bool = True) -> Path:
    """Crea tablas, índices, triggers de bitácora append-only y ejecuta seed idempotente."""
    target = get_db_path(db_path)
    conn = get_connection(target)
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                full_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                area TEXT,
                sede TEXT NOT NULL DEFAULT 'Sede Sabanas (Valledupar)',
                is_active INTEGER NOT NULL DEFAULT 1,
                privacy_accepted INTEGER NOT NULL DEFAULT 1,
                last_assigned_at TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS refresh_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                expires_at TEXT NOT NULL,
                revoked INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS service_catalog (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_name TEXT NOT NULL UNIQUE,
                area TEXT NOT NULL,
                base_impact TEXT NOT NULL,
                default_type TEXT NOT NULL,
                description TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS sla_config (
                priority TEXT PRIMARY KEY,
                sla_response_hours REAL NOT NULL,
                sla_resolution_hours REAL NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_number TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                ticket_type TEXT NOT NULL,
                service_name TEXT NOT NULL,
                area TEXT NOT NULL,
                sede TEXT NOT NULL,
                location TEXT NOT NULL,
                impact TEXT NOT NULL,
                urgency TEXT NOT NULL,
                priority TEXT NOT NULL,
                status TEXT NOT NULL,
                requester_id INTEGER NOT NULL,
                requester_email TEXT NOT NULL,
                requester_role TEXT NOT NULL,
                assigned_tech_id INTEGER,
                assigned_tech_email TEXT,
                sla_response_hours REAL NOT NULL,
                sla_resolution_hours REAL NOT NULL,
                response_deadline TEXT,
                resolution_deadline TEXT,
                first_response_at TEXT,
                paused_at TEXT,
                paused_seconds INTEGER NOT NULL DEFAULT 0,
                resolved_at TEXT,
                closed_at TEXT,
                diagnosis TEXT,
                solution TEXT,
                closing_category TEXT,
                csat_score INTEGER,
                csat_comment TEXT,
                ai_suggested_service TEXT,
                ai_confidence REAL,
                ai_human_validated INTEGER NOT NULL DEFAULT 0,
                priority_justification TEXT,
                sla_breached INTEGER NOT NULL DEFAULT 0,
                sla_alert_75_sent INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (requester_id) REFERENCES users(id),
                FOREIGN KEY (assigned_tech_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS ticket_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL,
                actor_email TEXT NOT NULL,
                action TEXT NOT NULL,
                old_status TEXT,
                new_status TEXT,
                comment TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS ticket_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL,
                sender_id INTEGER NOT NULL,
                sender_email TEXT NOT NULL,
                sender_role TEXT NOT NULL,
                message TEXT NOT NULL,
                attachment_name TEXT,
                attachment_path TEXT,
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE,
                FOREIGN KEY (sender_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS kb_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                service_name TEXT NOT NULL,
                symptoms TEXT NOT NULL,
                solution_steps TEXT NOT NULL,
                keywords TEXT NOT NULL,
                visibility TEXT NOT NULL DEFAULT 'Pública',
                status TEXT NOT NULL DEFAULT 'Publicado',
                version INTEGER NOT NULL DEFAULT 1,
                author_email TEXT NOT NULL,
                reviewer_email TEXT,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_email TEXT NOT NULL,
                ip_address TEXT NOT NULL DEFAULT '127.0.0.1',
                action TEXT NOT NULL,
                entity TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                old_value TEXT,
                new_value TEXT
            );

            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT NOT NULL,
                ticket_number TEXT,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
            CREATE INDEX IF NOT EXISTS idx_tickets_requester ON tickets(requester_id);
            CREATE INDEX IF NOT EXISTS idx_tickets_tech ON tickets(assigned_tech_id);
            CREATE INDEX IF NOT EXISTS idx_tickets_number ON tickets(ticket_number);
            CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp DESC);
            CREATE INDEX IF NOT EXISTS idx_notif_user ON notifications(user_email, is_read);

            -- Triggers para garantizar inmutabilidad estricta (append-only) de audit_logs (RNF-09)
            CREATE TRIGGER IF NOT EXISTS trg_audit_logs_no_update
            BEFORE UPDATE ON audit_logs
            BEGIN
                SELECT RAISE(ABORT, 'audit_logs es inmutable (append-only): no se permiten modificaciones');
            END;

            CREATE TRIGGER IF NOT EXISTS trg_audit_logs_no_delete
            BEFORE DELETE ON audit_logs
            BEGIN
                SELECT RAISE(ABORT, 'audit_logs es inmutable (append-only): no se permiten eliminaciones');
            END;
            """
        )
        conn.commit()
        if seed:
            seed_initial_data(conn)
        return target
    finally:
        conn.close()


def seed_initial_data(conn: sqlite3.Connection) -> None:
    """Precarga catálogo de servicios, SLA, usuarios por rol, 12 artículos KB y tickets demo."""
    now_iso = now_bogota().isoformat()

    # 1. Catálogo de servicios
    for svc_name, meta in UPC_SERVICE_CATALOG.items():
        conn.execute(
            """
            INSERT OR IGNORE INTO service_catalog
            (service_name, area, base_impact, default_type, description, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (svc_name, meta["area"], meta["base_impact"], meta["default_type"], meta["description"]),
        )

    # 2. Configuración SLA
    for prio, vals in SLA_BY_PRIORITY.items():
        conn.execute(
            """
            INSERT OR IGNORE INTO sla_config
            (priority, sla_response_hours, sla_resolution_hours, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (prio, vals["sla_response_hours"], vals["sla_resolution_hours"], now_iso),
        )

    # 3. Usuarios de prueba (idempotente)
    existing_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if existing_users == 0:
        seed_users = [
            ("admin@unicesar.edu.co", "Carlos Mendoza (Administrador)", "Admin2026*", "admin", "Oficina de Informática y Sistemas", "Sede Sabanas (Valledupar)"),
            ("coordinador@unicesar.edu.co", "Kathy Sagbini (Coordinadora Mesa)", "Coord2026*", "coordinador", "Oficina de Informática y Sistemas", "Sede Sabanas (Valledupar)"),
            ("director@unicesar.edu.co", "Nayid Castellar (Director TIC)", "Director2026*", "director", "Dirección TIC", "Sede Sabanas (Valledupar)"),
            ("tecnico1@unicesar.edu.co", "Andrés Martínez (Redes)", "Tecnico2026*", "tecnico", "Redes e Infraestructura", "Sede Sabanas (Valledupar)"),
            ("tecnico2@unicesar.edu.co", "Laura Gómez (Sistemas)", "Tecnico2026*", "tecnico", "Sistemas de Información", "Sede Sabanas (Valledupar)"),
            ("tecnico3@unicesar.edu.co", "Mateo Rojas (Identidad)", "Tecnico2026*", "tecnico", "Identidad y Accesos", "Sede Sabanas (Valledupar)"),
            ("tecnico4@unicesar.edu.co", "Valentina Díaz (Soporte Campo)", "Tecnico2026*", "tecnico", "Soporte en Campo", "Sede Hurtado (Valledupar)"),
            ("tecnico5@unicesar.edu.co", "Julián Torres (Mesa Software)", "Tecnico2026*", "tecnico", "Mesa de Software", "Seccional Aguachica"),
            ("tecnico6@unicesar.edu.co", "Camila Herrera (Soporte Campo)", "Tecnico2026*", "tecnico", "Soporte en Campo", "Sede Sabanas (Valledupar)"),
            ("estudiante@unicesar.edu.co", "Sofía Paternina (Estudiante)", "User2026*", "usuario", None, "Sede Sabanas (Valledupar)"),
            ("docente@unicesar.edu.co", "Prof. Maribel Romero (Docente)", "User2026*", "usuario", None, "Sede Sabanas (Valledupar)"),
        ]
        for email, name, pwd, role, area, sede in seed_users:
            conn.execute(
                """
                INSERT INTO users
                (email, full_name, password_hash, role, area, sede, is_active, privacy_accepted, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, 1, ?)
                """,
                (email, name, hash_password(pwd), role, area, sede, now_iso),
            )

    # 4. Base de Conocimiento (12 artículos reales UPC)
    existing_kb = conn.execute("SELECT COUNT(*) FROM kb_articles").fetchone()[0]
    if existing_kb == 0:
        kb_items = [
            (
                "KB-001",
                "Restablecimiento de contraseña en el Vortal Académico UPC",
                "Plataformas Académicas (Aula Web / Vortal)",
                "El estudiante o docente olvidó su clave del Vortal o el portal rechaza las credenciales.",
                "1. Ingrese a vortal.unicesar.edu.co y seleccione '¿Olvidó su contraseña?'.\n2. Digite su número de documento y correo institucional @unicesar.edu.co.\n3. Revise su bandeja de entrada o spam para abrir el enlace de recuperación válido por 15 minutos.\n4. Defina una clave de al menos 10 caracteres con mayúsculas, minúsculas y símbolo.",
                "vortal contraseña clave recuperar acceso matricula notas",
                "Pública",
            ),
            (
                "KB-002",
                "Configuración de la red inalámbrica institucional Wi-Fi Eduroam",
                "Conectividad y Redes Wi-Fi",
                "El portátil o celular no conecta a la red Wi-Fi Eduroam en bloques académicos o solicita certificado.",
                "1. Seleccione la red Wi-Fi 'eduroam' en su dispositivo.\n2. En método EAP seleccione PEAP y autenticación MSCHAPv2.\n3. En identidad anónima déjelo vacío y en certificado CA elija 'Usar certificados del sistema' o 'No validar' según equipo.\n4. Ingrese su usuario completo (@unicesar.edu.co) y su contraseña del correo institucional.",
                "wifi wi-fi eduroam red inalambrica internet conectar bloques",
                "Pública",
            ),
            (
                "KB-003",
                "Desbloqueo de correo institucional @unicesar.edu.co y verificación MFA",
                "Correo Institucional y Cuentas",
                "Cuenta de correo institucional bloqueada por intentos fallidos o cambio de teléfono para MFA.",
                "1. Espere 15 minutos si superó los 5 intentos fallidos de acceso.\n2. Ingrese a cuenta.unicesar.edu.co con su código de verificación alterno.\n3. Si cambió de celular para MFA, radique una solicitud en Mesa de Servicios indicando su documento para reiniciar el segundo factor.",
                "correo institucional cuenta bloqueada mfa clave unicesar",
                "Pública",
            ),
            (
                "KB-004",
                "Verificación rápida cuando el videoproyector del aula muestra 'Sin Señal'",
                "Aulas Inteligentes y Videoproyectores",
                "El docente conecta el portátil al proyector del aula inteligente pero no proyecta imagen.",
                "1. Verifique que el cable HDMI o VGA esté conectado en el puerto activo de la caja de mesa.\n2. Presione en su teclado Windows + P (o Cmd + F1 en Mac) y seleccione 'Duplicar'.\n3. En el control del proyector presione el botón 'Source / Input' hasta seleccionar HDMI1.\n4. Si la lámpara parpadea en rojo o no enciende, cree un ticket con prioridad de clase en curso.",
                "videoproyector proyector hdmi sin señal aula inteligente pantalla salon",
                "Pública",
            ),
            (
                "KB-005",
                "Cursos no visibles o error de carga en Aula Web UPC",
                "Plataformas Académicas (Aula Web / Vortal)",
                "El estudiante matriculó materias en Vortal pero aún no aparecen en la plataforma Aula Web.",
                "1. Verifique que su matrícula financiera y académica aparezca en estado 'Activo' en Vortal.\n2. La sincronización entre Vortal y Aula Web ocurre automáticamente cada 4 horas.\n3. Limpie caché del navegador o pruebe en ventana de incógnito.\n4. Si persiste tras 24 horas, reporte el ticket adjuntando captura de horario.",
                "aula web moodle cursos virtuales matricula asignaturas error 500",
                "Pública",
            ),
            (
                "KB-006",
                "Solicitud e instalación de software académico (SPSS, MATLAB, AutoCAD)",
                "Software y Licenciamiento",
                "Docente o estudiante requiere software especializado en salas de cómputo o equipo asignado.",
                "1. Valide que el software esté cubierto por el licenciamiento institucional vigente.\n2. Cree una solicitud seleccionando 'Software y Licenciamiento', indicando bloque, salón y número de equipos.\n3. Para licencias flotantes en red (AutoCAD/MATLAB), asegúrese de estar conectado a la red del campus.",
                "software spss matlab autocad licencia instalacion programas salas",
                "Pública",
            ),
            (
                "KB-007",
                "Solución a atascos y cola de impresión detenida en impresoras de red",
                "Equipos de Cómputo e Impresoras",
                "La impresora administrativa muestra documento en cola pendiente o luz naranja de error.",
                "1. Abra el panel lateral de la impresora y retire suavemente cualquier hoja atascada en dirección de salida.\n2. En Windows abra 'Impresoras y escáneres' -> Abrir cola -> Cancelar todos los documentos.\n3. Reinicie la impresora esperando 15 segundos antes de volver a encender.",
                "impresora imprimir atasco toner cola impresion escaner",
                "Pública",
            ),
            (
                "KB-008",
                "Activación de Microsoft 365 institucional con cuenta @unicesar.edu.co",
                "Software y Licenciamiento",
                "Word, Excel o PowerPoint muestran aviso de producto sin licencia o modo solo lectura.",
                "1. Abra cualquier aplicación de Office y haga clic en 'Iniciar sesión'.\n2. Ingrese su correo institucional completo @unicesar.edu.co.\n3. Acepte la opción 'Permitir que mi organización administre mi dispositivo' únicamente si es equipo institucional.\n4. Reinicie Word o Excel para refrescar la licencia educativa.",
                "office word excel powerpoint licencia microsoft 365 activacion",
                "Pública",
            ),
            (
                "KB-009",
                "Diagnóstico cuando un computador de laboratorio no enciende o no da video",
                "Equipos de Cómputo e Impresoras",
                "El PC de escritorio o estación de trabajo no responde al botón de encendido o el monitor queda negro.",
                "1. Confirme que el regulador o multitoma del puesto esté encendido.\n2. Verifique que el cable de poder de la torre y del monitor estén firmes.\n3. Si el equipo emite pitidos continuos o huele a quemado, desconéctelo y radique incidencia de hardware indicando el número de inventario.",
                "computador pc monitor no enciende hardware laboratorio equipo",
                "Pública",
            ),
            (
                "KB-010",
                "Problemas de red cableada LAN y obtención de IP en bloques académicos",
                "Conectividad y Redes Wi-Fi",
                "El icono de red en Windows muestra globo de 'Sin acceso a internet' o 'Red no identificada'.",
                "1. Verifique que la luz verde/ámbar del puerto RJ45 parpadee al conectar el cable de red.\n2. Ejecute en consola 'ipconfig /release' seguido de 'ipconfig /renew'.\n3. Si la dirección empieza por 169.254.x.x, existe caída del punto de red o switch de piso; reporte el número de toma de pared.",
                "red cableada lan ethernet ip dhcp switch sin internet puerto rj45",
                "Pública",
            ),
            (
                "KB-011",
                "Creación de cuentas institucionales para nuevos docentes y contratistas",
                "Correo Institucional y Cuentas",
                "Personal recién vinculado requiere creación de correo @unicesar.edu.co y acceso a sistemas.",
                "1. Adjunte el número de contrato u oficio de vinculación emitido por Talento Humano.\n2. Indique nombre completo, documento, facultad o dependencia y sede.\n3. La activación se realiza en un tiempo objetivo de 8 horas hábiles y las credenciales temporales llegan al correo alterno.",
                "cuenta nueva contratista docente correo creacion usuario",
                "Pública",
            ),
            (
                "KB-012",
                "Guía interna técnica: reinicio remoto de puntos de acceso Aruba y switches de piso",
                "Conectividad y Redes Wi-Fi",
                "Procedimiento interno para técnicos de Redes e Infraestructura ante saturación de AP en bloques.",
                "1. Ingrese a la consola de gestión Aruba Central con usuario de técnico autorizado.\n2. Verifique el estado de potencia PoE del puerto en el switch de distribución del bloque afectado.\n3. Aplique reinicio controlado únicamente fuera de horas pico si hay más de 40 clientes asociados.",
                "aruba switch ap poe tecnico red interno",
                "Interna",
            ),
        ]
        for code, title, svc, symp, steps, kw, vis in kb_items:
            conn.execute(
                """
                INSERT INTO kb_articles
                (code, title, service_name, symptoms, solution_steps, keywords, visibility, status, version, author_email, reviewer_email, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'Publicado', 1, 'coordinador@unicesar.edu.co', 'coordinador@unicesar.edu.co', ?)
                """,
                (code, title, svc, symp, steps, kw, vis, now_iso),
            )

    # 5. Tickets iniciales de operación demo
    existing_tickets = conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
    if existing_tickets == 0:
        users_map = {
            r["email"]: dict(r)
            for r in conn.execute("SELECT * FROM users").fetchall()
        }
        now_dt = now_bogota()

        sample_tickets = [
            {
                "seq": 1,
                "title": "Caída total de red Wi-Fi Eduroam en Bloque B",
                "description": "Ningún estudiante ni docente logra conectarse a Eduroam en el segundo piso del Bloque B. Impide clase práctica en curso.",
                "service_name": "Conectividad y Redes Wi-Fi",
                "sede": "Sede Sabanas (Valledupar)",
                "location": "Bloque B",
                "urgency": "Alta",
                "status": "En atención",
                "requester_email": "docente@unicesar.edu.co",
                "tech_email": "tecnico1@unicesar.edu.co",
                "hours_ago": 1.2,
                "first_resp_mins": 14,
                "diagnosis": None,
                "solution": None,
                "csat_score": None,
            },
            {
                "seq": 2,
                "title": "Error 500 al registrar notas parciales en Vortal",
                "description": "Al guardar las notas del grupo 02 en Vortal académico aparece error de servidor y cierra la sesión.",
                "service_name": "Plataformas Académicas (Aula Web / Vortal)",
                "sede": "Sede Sabanas (Valledupar)",
                "location": "Bloque A",
                "urgency": "Alta",
                "status": "Asignado",
                "requester_email": "docente@unicesar.edu.co",
                "tech_email": "tecnico2@unicesar.edu.co",
                "hours_ago": 0.6,
                "first_resp_mins": None,
                "diagnosis": None,
                "solution": None,
                "csat_score": None,
            },
            {
                "seq": 3,
                "title": "Videoproyector sin señal HDMI en aula 204",
                "description": "Al conectar el portátil al módulo de piso HDMI el proyector indica Sin Señal. Hay alternativa usando televisor auxiliar.",
                "service_name": "Aulas Inteligentes y Videoproyectores",
                "sede": "Sede Hurtado (Valledupar)",
                "location": "Bloque C",
                "urgency": "Media",
                "status": "En espera",
                "requester_email": "docente@unicesar.edu.co",
                "tech_email": "tecnico4@unicesar.edu.co",
                "hours_ago": 5.0,
                "first_resp_mins": 25,
                "diagnosis": None,
                "solution": None,
                "csat_score": None,
            },
            {
                "seq": 4,
                "title": "Desbloqueo de cuenta institucional @unicesar.edu.co",
                "description": "Mi correo quedó bloqueado después de cambiar el celular y no recibo el código MFA para ingresar.",
                "service_name": "Correo Institucional y Cuentas",
                "sede": "Sede Sabanas (Valledupar)",
                "location": "Biblioteca",
                "urgency": "Media",
                "status": "Resuelto",
                "requester_email": "estudiante@unicesar.edu.co",
                "tech_email": "tecnico3@unicesar.edu.co",
                "hours_ago": 10.0,
                "first_resp_mins": 18,
                "diagnosis": "Token MFA vinculado a dispositivo anterior extravíado por el estudiante.",
                "solution": "Se validó identidad institucional y se restableció el segundo factor MFA enviando enlace temporal al correo alterno.",
                "csat_score": None,
            },
            {
                "seq": 5,
                "title": "Instalación de SPSS y RStudio en Laboratorio 3",
                "description": "Se solicita instalar SPSS versión 29 y RStudio en 25 equipos para talleres de estadística de la próxima semana.",
                "service_name": "Software y Licenciamiento",
                "sede": "Seccional Aguachica",
                "location": "Laboratorios de Cómputo",
                "urgency": "Baja",
                "status": "Cerrado",
                "requester_email": "docente@unicesar.edu.co",
                "tech_email": "tecnico5@unicesar.edu.co",
                "hours_ago": 30.0,
                "first_resp_mins": 40,
                "diagnosis": "Equipos de laboratorio sin paquetes estadísticos actualizados para el semestre 2026-2.",
                "solution": "Se desplegó imagen institucional con SPSS 29 licenciado y RStudio 2026 en los 25 equipos y se probó ejecución.",
                "csat_score": 5,
            },
            {
                "seq": 6,
                "title": "Impresora administrativa con atasco recurrente",
                "description": "La impresora multifuncional de Registro y Control atascó hojas en el fusor y detuvo la cola de impresión.",
                "service_name": "Equipos de Cómputo e Impresoras",
                "sede": "Sede Sabanas (Valledupar)",
                "location": "Edificio Administrativo",
                "urgency": "Media",
                "status": "En atención",
                "requester_email": "estudiante@unicesar.edu.co",
                "tech_email": "tecnico6@unicesar.edu.co",
                "hours_ago": 3.2,
                "first_resp_mins": 32,
                "diagnosis": None,
                "solution": None,
                "csat_score": None,
            },
        ]

        for item in sample_tickets:
            svc = item["service_name"]
            meta = UPC_SERVICE_CATALOG[svc]
            prio = calculate_priority_or03(meta["base_impact"], item["urgency"])
            created_dt = now_dt - timedelta(hours=item["hours_ago"])
            resp_deadline = add_business_hours(created_dt, prio["sla_response_hours"])
            res_deadline = add_business_hours(created_dt, prio["sla_resolution_hours"])

            req_user = users_map[item["requester_email"]]
            tech_user = users_map[item["tech_email"]]
            t_num = format_ticket_number(item["seq"], year=2026)

            first_resp_iso = (
                (created_dt + timedelta(minutes=item["first_resp_mins"])).isoformat()
                if item["first_resp_mins"] is not None
                else None
            )
            paused_iso = (now_dt - timedelta(hours=1)).isoformat() if item["status"] == "En espera" else None
            resolved_iso = (
                (created_dt + timedelta(hours=3.5)).isoformat()
                if item["status"] in ("Resuelto", "Cerrado")
                else None
            )
            closed_iso = (
                (created_dt + timedelta(hours=6.0)).isoformat()
                if item["status"] == "Cerrado"
                else None
            )

            cur = conn.execute(
                """
                INSERT INTO tickets (
                    ticket_number, title, description, ticket_type, service_name, area,
                    sede, location, impact, urgency, priority, status,
                    requester_id, requester_email, requester_role,
                    assigned_tech_id, assigned_tech_email,
                    sla_response_hours, sla_resolution_hours,
                    response_deadline, resolution_deadline,
                    first_response_at, paused_at, paused_seconds,
                    resolved_at, closed_at, diagnosis, solution, closing_category,
                    csat_score, ai_suggested_service, ai_confidence, ai_human_validated,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    t_num,
                    item["title"],
                    item["description"],
                    meta["default_type"],
                    svc,
                    meta["area"],
                    item["sede"],
                    item["location"],
                    prio["impact"],
                    prio["urgency"],
                    prio["priority"],
                    item["status"],
                    req_user["id"],
                    req_user["email"],
                    req_user["role"],
                    tech_user["id"],
                    tech_user["email"],
                    prio["sla_response_hours"],
                    prio["sla_resolution_hours"],
                    resp_deadline.isoformat(),
                    res_deadline.isoformat(),
                    first_resp_iso,
                    paused_iso,
                    0,
                    resolved_iso,
                    closed_iso,
                    item["diagnosis"],
                    item["solution"],
                    "Solución definitiva en sitio" if item["solution"] else None,
                    item["csat_score"],
                    svc,
                    94.5,
                    1,
                    created_dt.isoformat(),
                    now_iso,
                ),
            )
            ticket_id = cur.lastrowid

            conn.execute(
                """
                UPDATE users SET last_assigned_at = ? WHERE id = ?
                """,
                (created_dt.isoformat(), tech_user["id"]),
            )
            conn.execute(
                """
                INSERT INTO ticket_history (ticket_id, actor_email, action, old_status, new_status, comment, created_at)
                VALUES (?, ?, 'Registro y asignación automática', NULL, 'Asignado', ?, ?)
                """,
                (ticket_id, req_user["email"], f"Asignado a {tech_user['email']} por menor carga.", created_dt.isoformat()),
            )
            if item["status"] != "Asignado":
                conn.execute(
                    """
                    INSERT INTO ticket_history (ticket_id, actor_email, action, old_status, new_status, comment, created_at)
                    VALUES (?, ?, 'Actualización operativa', 'Asignado', ?, ?, ?)
                    """,
                    (ticket_id, tech_user["email"], item["status"], "Atención iniciada por el técnico asignado.", now_iso),
                )
            conn.execute(
                """
                INSERT INTO ticket_messages (ticket_id, sender_id, sender_email, sender_role, message, is_read, created_at)
                VALUES (?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    ticket_id,
                    req_user["id"],
                    req_user["email"],
                    req_user["role"],
                    f"Buenos días, adjunto el detalle del caso: {item['description']}",
                    created_dt.isoformat(),
                ),
            )
            conn.execute(
                """
                INSERT INTO ticket_messages (ticket_id, sender_id, sender_email, sender_role, message, is_read, created_at)
                VALUES (?, ?, ?, 'tecnico', ?, 0, ?)
                """,
                (
                    ticket_id,
                    tech_user["id"],
                    tech_user["email"],
                    "Caso recibido en la mesa de servicios UPC. Iniciando verificación técnica.",
                    (created_dt + timedelta(minutes=12)).isoformat(),
                ),
            )

        conn.execute(
            """
            INSERT INTO audit_logs (timestamp, user_email, ip_address, action, entity, entity_id, old_value, new_value)
            VALUES (?, 'system@unicesar.edu.co', '127.0.0.1', 'SEED_INITIALIZATION', 'system', 'casagbi', NULL, 'Base inicial CASAGBI UPC cargada')
            """,
            (now_iso,),
        )

    conn.commit()
