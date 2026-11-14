"""Generador de dataset sintético realista de tickets TIC para la UPC (18,000 registros)."""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

from src.domain.rules import (
    SLA_BY_PRIORITY,
    UPC_LOCATIONS,
    UPC_SEDES,
    UPC_SERVICE_CATALOG,
    calculate_priority_or03,
    format_ticket_number,
)

DEFAULT_RAW_PATH = Path("data/raw/upc_tickets_raw.csv")

REQUESTER_ROLES = ["Estudiante", "Docente", "Administrativo"]
REQUESTER_WEIGHTS = [0.55, 0.25, 0.20]
SEDE_WEIGHTS = [0.58, 0.24, 0.18]

TECHNICIANS_BY_AREA: Dict[str, List[str]] = {
    "Redes e Infraestructura": ["tecnico1@unicesar.edu.co", "tecnico6@unicesar.edu.co"],
    "Sistemas de Información": ["tecnico2@unicesar.edu.co"],
    "Identidad y Accesos": ["tecnico3@unicesar.edu.co"],
    "Soporte en Campo": ["tecnico4@unicesar.edu.co", "tecnico5@unicesar.edu.co"],
    "Mesa de Software": ["tecnico5@unicesar.edu.co", "tecnico2@unicesar.edu.co"],
}

# Plantillas realistas con vocabulario compartido de campus (aula, sistema, red, equipo, correo)
# para exigir modelado discriminativo de bigramas frente a un baseline simple.
SERVICE_TEMPLATES: Dict[str, Dict[str, List[str]]] = {
    "Conectividad y Redes Wi-Fi": {
        "subjects": [
            "Sin conexión a red Wi-Fi Eduroam en {ubicacion}",
            "Caída de internet cableado en {ubicacion}",
            "No carga el Vortal ni el correo por caída de red en {sede}",
            "Punto de acceso sin señal inalámbrica en {ubicacion}",
            "Falla de conectividad LAN y DHCP en equipos de {ubicacion}",
            "No asigna dirección IP al conectar portátil en aula de {ubicacion}",
        ],
        "symptoms": [
            "Desde temprano varios equipos en el aula pierden paquetes y no abren páginas ni plataformas académicas.",
            "El Wi-Fi aparece conectado pero no permite acceder al correo institucional ni al Vortal desde la red del bloque.",
            "El cable de red del computador de escritorio muestra enlace caído y deja sin acceso al sistema.",
            "La señal inalámbrica se desconecta cada pocos minutos en el aula afectando la clase con software en línea.",
            "Los estudiantes intentan conectarse a Eduroam con su cuenta institucional pero el portal rechaza el enlace.",
            "El switch de piso presenta luces en ámbar y dejó sin internet a todo el corredor de {ubicacion}.",
        ],
    },
    "Plataformas Académicas (Aula Web / Vortal)": {
        "subjects": [
            "Error 500 al ingresar al Vortal académico",
            "No cargan los cursos virtuales en Aula Web",
            "Falla en módulo de matrícula y registro de notas en Vortal",
            "Sesión expirada constantemente en plataforma Aula Web",
            "No permite subir calificaciones finales en el sistema académico",
            "Caída del portal académico institucional durante inscripción",
        ],
        "symptoms": [
            "Aunque la red Wi-Fi funciona normal en el equipo, al autenticar en el Vortal aparece página en blanco y error de servidor.",
            "El módulo de Aula Web no muestra las asignaturas matriculadas tras ingresar con la cuenta institucional.",
            "Al intentar guardar notas parciales el sistema arroja error HTTP 500 y cierra la sesión del docente.",
            "Los docentes no pueden cargar material en PDF ni activar cuestionarios en Aula Web desde ningún navegador.",
            "El formulario de matrícula en línea se queda cargando indefinidamente aun conectado por red cableada o datos.",
            "Se presenta inconsistencia entre el horario asignado en Vortal y los grupos visibles en Aula Web.",
        ],
    },
    "Correo Institucional y Cuentas": {
        "subjects": [
            "Restablecimiento de contraseña correo @unicesar.edu.co",
            "Cuenta institucional bloqueada tras intentos de ingreso",
            "Solicitud de creación de buzón institucional para nuevo integrante",
            "No llegan mensajes externos al correo universitario",
            "Error de autenticación MFA en cuenta institucional",
            "Reactivación de acceso único para correo y plataformas UPC",
        ],
        "symptoms": [
            "El usuario olvidó su clave del correo institucional y no puede ingresar ni al buzón ni al Vortal.",
            "Al ingresar al correo @unicesar.edu.co muestra aviso de cuenta bloqueada por intentos fallidos.",
            "Se requiere habilitar cuenta institucional y permisos de acceso para docente vinculado este semestre.",
            "Los correos enviados desde cuentas institucionales rebotan con error de cuota o autenticación SMTP.",
            "El código de verificación en dos pasos MFA no llega al celular y bloquea el ingreso al correo oficial.",
            "Después del cambio de semestre la credencial aparece inactiva en el directorio institucional.",
        ],
    },
    "Aulas Inteligentes y Videoproyectores": {
        "subjects": [
            "Videoproyector no enciende en aula de {ubicacion}",
            "Cable HDMI dañado o sin señal de video en salón",
            "Pantalla interactiva sin respuesta táctil en {ubicacion}",
            "Sin audio en parlantes del aula inteligente",
            "Control remoto y proyector desconfigurados en {sede}",
            "Imagen borrosa o lámpara agotada en videoproyector de clase",
        ],
        "symptoms": [
            "Al conectar el computador portátil al proyector del aula aparece mensaje Sin Señal en la pantalla.",
            "El equipo de proyección del salón se apaga solo a los cinco minutos por sobrecalentamiento.",
            "La consola de sonido del aula inteligente emite zumbido y no reproduce el audio durante la clase.",
            "El puerto HDMI de la caja de piso está suelto y no transmite imagen hacia el telón del salón.",
            "El tablero digital interactivo del aula no calibra el lápiz ni responde al tacto en la presentación.",
            "El videoproyector muestra alerta de lámpara agotada y baja luminosidad en {ubicacion}.",
        ],
    },
    "Equipos de Cómputo e Impresoras": {
        "subjects": [
            "Computador de escritorio no enciende en {ubicacion}",
            "Impresora institucional con atasco frecuente de papel",
            "Escáner de oficina no es reconocido por el equipo",
            "Lentitud extrema y pantallazo azul en PC administrativo",
            "Cambio de tóner y calibración de impresora en red",
            "Teclado, mouse o monitor sin video en laboratorio de {ubicacion}",
        ],
        "symptoms": [
            "El computador de escritorio emite pitidos al presionar encendido y no muestra imagen en el monitor.",
            "La impresora compartida marca error de fusor y deja la cola de impresión detenida en la dependencia.",
            "El equipo de la sala de cómputo se reinicia con pantallazo azul al abrir programas de clase.",
            "La impresora multifuncional imprime con manchas negras de tóner y no escanea documentos.",
            "El disco del PC presenta fallas físicas de lectura y tarda más de diez minutos en arrancar Windows.",
            "Los puertos USB y la fuente de poder del equipo no responden en el puesto administrativo.",
        ],
    },
    "Software y Licenciamiento": {
        "subjects": [
            "Solicitud de instalación de SPSS y RStudio en laboratorio",
            "Licencia vencida de MATLAB / AutoCAD en {ubicacion}",
            "Activación de paquete ofimático Microsoft 365 institucional",
            "Actualización de antivirus y permisos de software académico",
            "Requerimiento de compilador y entorno Python en salas",
            "Error de servidor de licencias en software de ingeniería",
        ],
        "symptoms": [
            "Al abrir el programa especializado en el computador solicita clave de licencia y cierra la aplicación.",
            "Para la práctica de la asignatura se requiere instalar la versión actualizada de SPSS y RStudio.",
            "Microsoft Word y Excel muestran barra roja de producto sin licencia activada en el equipo.",
            "El usuario no tiene permisos de administrador para instalar complementos académicos en el equipo.",
            "El servidor de licencias de AutoCAD y MATLAB arroja error de activación en los equipos del laboratorio.",
            "Se necesita paquete estadístico y actualización de software antes del inicio de los talleres.",
        ],
    },
}

# Contextos realistas cruzados donde el usuario menciona otros servicios en el mismo texto
# (tal como ocurre en la UPC: "el wifi funciona pero Vortal da error", "en el computador no proyecta", etc.)
CROSS_SERVICE_CONTEXT: Dict[str, List[str]] = {
    "Conectividad y Redes Wi-Fi": [
        "Intenté abrir el correo institucional y Aula Web pero no hay enlace de red ni dirección IP.",
        "El equipo del laboratorio enciende bien y el software abre, pero la red LAN y Eduroam no conectan.",
        "Al conectar el portátil al proyector del salón no pude cargar la presentación en línea porque cayó el Wi-Fi.",
    ],
    "Plataformas Académicas (Aula Web / Vortal)": [
        "La red Wi-Fi y el correo institucional funcionan bien en el computador, pero el Vortal y Aula Web fallan.",
        "Probé desde dos computadores y con el proyector del aula listo, pero la plataforma académica sigue caída.",
        "El software del navegador está actualizado y tengo acceso al correo, el problema es únicamente en Vortal.",
    ],
    "Correo Institucional y Cuentas": [
        "El internet del bloque funciona normal, pero mi cuenta @unicesar.edu.co rechaza la contraseña para correo y Vortal.",
        "No puedo activar Microsoft 365 ni entrar a Aula Web porque mi usuario institucional aparece bloqueado.",
        "Desde el computador de la oficina tengo red, pero la autenticación MFA de la cuenta no permite iniciar sesión.",
    ],
    "Aulas Inteligentes y Videoproyectores": [
        "El computador portátil funciona y carga Aula Web y el correo, pero el videoproyector del salón marca sin señal.",
        "El software de presentación abre normal en el PC del docente, la falla está en el cable HDMI y sonido del aula.",
        "Ya validamos la red Wi-Fi del salón; lo que no enciende ni proyecta es la pantalla interactiva.",
    ],
    "Equipos de Cómputo e Impresoras": [
        "No puedo abrir el correo ni imprimir guías de Aula Web porque el computador y la impresora presentan falla física.",
        "La red del área funciona en otros puestos, pero este PC no da video y la impresora tiene atasco de papel.",
        "Necesito usar SPSS y el navegador, pero la torre del computador no enciende y emite pitidos.",
    ],
    "Software y Licenciamiento": [
        "El computador enciende bien y conecta a la red Wi-Fi del laboratorio, pero MATLAB y SPSS piden licencia vencida.",
        "Tengo acceso normal al correo @unicesar.edu.co y al Vortal, pero Office y AutoCAD muestran producto sin activar.",
        "El proyector del aula funciona correcto; lo que falta instalar y activar en los equipos es el paquete estadístico.",
    ],
}

# Frases coloquiales ambiguas que aparecen en múltiples servicios reales
COLOQUIAL_NOISE = [
    "Por favor ayuda rápida, ya reinicié el computador y sigue igual.",
    "Lo reporté primero por llamada pero me pidieron radicar ticket aquí.",
    "El semestre pasado pasó algo parecido en este mismo bloque.",
    "Necesito usar el sistema y el correo para subir evidencias hoy.",
    "No sé si es falla del equipo o de la red del salón, agradezco soporte.",
    "Varios compañeros del programa presentan el mismo error desde la mañana.",
    "Se requiere validación técnica en horario de clase por favor.",
    "Gracias por la pronta gestión de la Mesa de Servicios UPC.",
]

URGENCY_CONTEXT: Dict[str, List[str]] = {
    "Alta": [
        "Urgente: impide completamente trabajar y no existe alternativa disponible.",
        "Clase o trámite en curso detenido en este momento, se requiere atención inmediata.",
        "Actividad crítica bloqueada sin forma temporal de continuar.",
    ],
    "Media": [
        "Existe una alternativa temporal pero retrasa el trabajo de la jornada.",
        "Afecta parcialmente la actividad, podemos usar otro equipo mientras se atiende.",
        "Impacto moderado, se requiere solución hoy aunque hay plan de contingencia.",
    ],
    "Baja": [
        "No impide la actividad diaria, puede programarse en horario regular.",
        "Consulta preventiva o requerimiento planificado para esta semana.",
        "Solicitud sin bloqueo operativo inmediato.",
    ],
}


def generate_synthetic_dataset(
    n_rows: int = 18000,
    output_path: Path | str = DEFAULT_RAW_PATH,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Genera exactamente `n_rows` registros sintéticos realistas del soporte TIC UPC,
    incluyendo ~3 % de anomalías controladas para demostrar la fase CRISP-DM de limpieza.
    """
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    n_duplicates = max(1, int(round(n_rows * 0.008)))
    n_base = n_rows - n_duplicates

    services = list(UPC_SERVICE_CATALOG.keys())
    # Desbalance realista propio de una mesa universitaria
    service_weights = [0.24, 0.22, 0.19, 0.13, 0.13, 0.09]

    start_date = datetime(2025, 1, 15, 7, 0, 0)
    records: List[Dict[str, object]] = []

    for idx in range(1, n_base + 1):
        service = rng.choices(services, weights=service_weights, k=1)[0]
        svc_meta = UPC_SERVICE_CATALOG[service]
        area = svc_meta["area"]
        base_impact = svc_meta["base_impact"]

        impact = base_impact if rng.random() < 0.84 else rng.choice(["Alto", "Medio", "Bajo"])
        urgency = rng.choices(["Alta", "Media", "Baja"], weights=[0.28, 0.44, 0.28], k=1)[0]
        prio_info = calculate_priority_or03(impact, urgency)
        priority = prio_info["priority"]
        sla_res_h = prio_info["sla_resolution_hours"]

        sede = rng.choices(UPC_SEDES, weights=SEDE_WEIGHTS, k=1)[0]
        ubicacion = rng.choice(UPC_LOCATIONS)
        rol_solicitante = rng.choices(REQUESTER_ROLES, weights=REQUESTER_WEIGHTS, k=1)[0]

        tipo_caso = svc_meta["default_type"]
        if service == "Software y Licenciamiento" and rng.random() < 0.25:
            tipo_caso = "Incidencia"
        elif service == "Correo Institucional y Cuentas" and rng.random() < 0.42:
            tipo_caso = "Incidencia"

        tpl = SERVICE_TEMPLATES[service]
        asunto = rng.choice(tpl["subjects"]).format(ubicacion=ubicacion, sede=sede)
        sintoma = rng.choice(tpl["symptoms"]).format(ubicacion=ubicacion, sede=sede)

        # Inyectar contexto cruzado realista en ~45% de tickets (vocabulario compartido entre clases)
        if rng.random() < 0.45:
            sintoma = f"{sintoma} {rng.choice(CROSS_SERVICE_CONTEXT[service])}"

        text_urgency = urgency
        if rng.random() < 0.05:
            text_urgency = rng.choice(["Alta", "Media", "Baja"])

        urg_nota = rng.choice(URGENCY_CONTEXT[text_urgency])
        colloquial = rng.choice(COLOQUIAL_NOISE) if rng.random() < 0.40 else ""

        # En ~22% de casos el asunto es genérico (el contexto real está en la descripción)
        if rng.random() < 0.22:
            asunto = rng.choice(
                [
                    f"Solicitud de soporte técnico urgente en {ubicacion}",
                    f"Problema tecnológico reportado en {sede}",
                    f"Inconveniente con servicio institucional en {ubicacion}",
                    f"Falla reportada por {rol_solicitante.lower()} en {ubicacion}",
                ]
            )

        descripcion = (
            f"{sintoma} Reportado por {rol_solicitante.lower()} en {ubicacion} ({sede}). "
            f"{urg_nota} {colloquial}".strip()
        )

        # ~2.5% de ruido de etiquetado realista (ticket mal categorizado manualmente en origen)
        reported_service = service
        if rng.random() < 0.025:
            reported_service = rng.choice([s for s in services if s != service])

        day_offset = int(np_rng.integers(0, 600))
        hour = int(rng.choices(range(7, 20), weights=[2, 4, 6, 7, 7, 5, 4, 6, 6, 5, 4, 3, 2], k=1)[0])
        minute = int(np_rng.integers(0, 60))
        fecha_creacion = (start_date + timedelta(days=day_offset, hours=hour - 7, minutes=minute)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        tech = rng.choice(TECHNICIANS_BY_AREA[UPC_SERVICE_CATALOG[reported_service]["area"]])

        sede_factor = 1.0 if "Sabanas" in sede else (1.12 if "Hurtado" in sede else 1.25)
        resp_target_min = SLA_BY_PRIORITY[priority]["sla_response_hours"] * 60.0
        tiempo_resp_min = round(
            float(np.clip(np_rng.gamma(shape=2.2, scale=resp_target_min * 0.28 * sede_factor), 2.0, resp_target_min * 1.9)),
            1,
        )

        res_scale = sla_res_h * 0.36 * sede_factor
        tiempo_res_horas = round(
            float(np.clip(np_rng.gamma(shape=2.4, scale=res_scale), 0.25, sla_res_h * 1.65)),
            2,
        )
        cumple_sla = bool(tiempo_res_horas <= sla_res_h)

        base_csat = 4.5 if cumple_sla else 2.9
        csat = int(np.clip(round(float(np_rng.normal(loc=base_csat, scale=0.7))), 1, 5))

        records.append(
            {
                "ticket_id": format_ticket_number(idx, year=2026),
                "fecha_creacion": fecha_creacion,
                "rol_solicitante": rol_solicitante,
                "sede": sede,
                "ubicacion": ubicacion,
                "asunto": asunto,
                "descripcion": descripcion,
                "tipo_caso": tipo_caso,
                "servicio_real": reported_service,
                "impacto": impact,
                "urgencia": urgency,
                "prioridad": priority,
                "tecnico_asignado": tech,
                "tiempo_respuesta_min": tiempo_resp_min,
                "tiempo_resolucion_horas": tiempo_res_horas,
                "cumple_sla": cumple_sla,
                "satisfaccion": csat,
            }
        )

    df = pd.DataFrame(records)

    n_null_loc = int(round(n_rows * 0.011))
    n_short_txt = int(round(n_rows * 0.005))
    n_neg_outliers = int(round(n_rows * 0.006))

    all_indices = list(range(len(df)))
    rng.shuffle(all_indices)

    null_indices = all_indices[:n_null_loc]
    short_indices = all_indices[n_null_loc : n_null_loc + n_short_txt]
    outlier_indices = all_indices[
        n_null_loc + n_short_txt : n_null_loc + n_short_txt + n_neg_outliers
    ]
    dup_source_indices = all_indices[
        n_null_loc + n_short_txt + n_neg_outliers : n_null_loc + n_short_txt + n_neg_outliers + n_duplicates
    ]

    df.loc[null_indices, "ubicacion"] = np.nan

    for i in short_indices:
        df.loc[i, "asunto"] = rng.choice(["ayuda", "mal", "ok", "??"])
        df.loc[i, "descripcion"] = rng.choice(["hola", "no", "x", "malo"])

    for i in outlier_indices:
        if rng.random() < 0.5:
            df.loc[i, "tiempo_respuesta_min"] = -round(rng.uniform(5.0, 60.0), 1)
        else:
            df.loc[i, "tiempo_resolucion_horas"] = -round(rng.uniform(1.0, 15.0), 2)

    dup_rows = df.iloc[dup_source_indices].copy()
    df_final = pd.concat([df, dup_rows], ignore_index=True)

    df_final.to_csv(output_file, index=False, encoding="utf-8")
    return df_final


if __name__ == "__main__":
    generated = generate_synthetic_dataset()
    print(f"Dataset sintético generado: {len(generated)} registros en {DEFAULT_RAW_PATH}")
