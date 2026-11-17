"""Evaluación sistemática del clasificador NLP y del Agente IA CASAGBI sobre 105 frases."""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from src.application.ai_agent import ProcessAgentTurnCommand, ProcessAgentTurnCommandHandler
from src.domain.ports import IUnitOfWork
from src.infrastructure.ml.ai_engine import LocalNLPEngine, extract_explicit_ticket_entities

# 105 frases etiquetadas: 55 sinónimos/uso real + 20 errores de escritura + 15 ambiguas + 15 fuera de alcance
EVALUATION_DATASET_105: List[Dict[str, str]] = [
    # --- 1. Equipos de Cómputo e Impresoras (10 frases) ---
    {"text": "tengo un problema con una computadora que no prende", "category": "in_domain", "expected": "Equipos de Cómputo e Impresoras"},
    {"text": "mi pc de escritorio tiene la pantalla negra al encender", "category": "in_domain", "expected": "Equipos de Cómputo e Impresoras"},
    {"text": "la torre del laboratorio no arranca ni enciende luces", "category": "in_domain", "expected": "Equipos de Cómputo e Impresoras"},
    {"text": "el computador portátil se congela con lentitud extrema", "category": "in_domain", "expected": "Equipos de Cómputo e Impresoras"},
    {"text": "la impresora de la oficina tiene atasco de papel en cola", "category": "in_domain", "expected": "Equipos de Cómputo e Impresoras"},
    {"text": "el monitor del equipo no da video y emite pitidos", "category": "in_domain", "expected": "Equipos de Cómputo e Impresoras"},
    {"text": "necesitamos cambio de tóner en la impresora multifuncional", "category": "in_domain", "expected": "Equipos de Cómputo e Impresoras"},
    {"text": "el escáner de registro no es reconocido por el pc", "category": "in_domain", "expected": "Equipos de Cómputo e Impresoras"},
    {"text": "el teclado y los puertos usb del equipo no responden", "category": "in_domain", "expected": "Equipos de Cómputo e Impresoras"},
    {"text": "mi laptop muestra pantallazo azul y se reinicia sola", "category": "in_domain", "expected": "Equipos de Cómputo e Impresoras"},
    # --- 2. Conectividad y Redes Wi-Fi (10 frases) ---
    {"text": "no me puedo conectar al wifi eduroam desde mi celular", "category": "in_domain", "expected": "Conectividad y Redes Wi-Fi"},
    {"text": "no hay internet en ningún computador del bloque b", "category": "in_domain", "expected": "Conectividad y Redes Wi-Fi"},
    {"text": "la red inalámbrica eduroam se cae cada cinco minutos", "category": "in_domain", "expected": "Conectividad y Redes Wi-Fi"},
    {"text": "el cable ethernet en el puerto rj45 aparece sin enlace lan", "category": "in_domain", "expected": "Conectividad y Redes Wi-Fi"},
    {"text": "el computador asigna ip 169 y no tiene salida a internet", "category": "in_domain", "expected": "Conectividad y Redes Wi-Fi"},
    {"text": "el túnel vpn institucional falla por timeout desde mi casa", "category": "in_domain", "expected": "Conectividad y Redes Wi-Fi"},
    {"text": "necesito solicitud de acceso al cliente vpn desde fuera del campus", "category": "in_domain", "expected": "Conectividad y Redes Wi-Fi"},
    {"text": "el switch del piso dejó sin internet todo el pasillo", "category": "in_domain", "expected": "Conectividad y Redes Wi-Fi"},
    {"text": "mi portátil dice conectado a wifi pero sin acceso a internet", "category": "in_domain", "expected": "Conectividad y Redes Wi-Fi"},
    {"text": "eduroam me pide certificado ca en android y rechaza el enlace", "category": "in_domain", "expected": "Conectividad y Redes Wi-Fi"},
    # --- 3. Aulas Inteligentes y Videoproyectores (9 frases) ---
    {"text": "el videoproyector del salón muestra sin señal al conectar hdmi", "category": "in_domain", "expected": "Aulas Inteligentes y Videoproyectores"},
    {"text": "el proyector del aula se apaga con luz roja de lámpara", "category": "in_domain", "expected": "Aulas Inteligentes y Videoproyectores"},
    {"text": "los parlantes del aula inteligente no tienen audio durante la clase", "category": "in_domain", "expected": "Aulas Inteligentes y Videoproyectores"},
    {"text": "el cable vga del proyector proyecta la imagen amarillenta", "category": "in_domain", "expected": "Aulas Inteligentes y Videoproyectores"},
    {"text": "la pantalla interactiva del aula no calibra el puntero táctil", "category": "in_domain", "expected": "Aulas Inteligentes y Videoproyectores"},
    {"text": "el videobeam del salón 203 no enciende antes de clase", "category": "in_domain", "expected": "Aulas Inteligentes y Videoproyectores"},
    {"text": "el puerto hdmi de la caja de piso del aula está suelto", "category": "in_domain", "expected": "Aulas Inteligentes y Videoproyectores"},
    {"text": "el amplificador de sonido del salón emite un zumbido fuerte", "category": "in_domain", "expected": "Aulas Inteligentes y Videoproyectores"},
    {"text": "el control remoto del videoproyector no cambia a entrada hdmi", "category": "in_domain", "expected": "Aulas Inteligentes y Videoproyectores"},
    # --- 4. Plataformas Académicas (Aula Web / Vortal) (9 frases) ---
    {"text": "aparece error 500 en vortal al guardar las notas parciales", "category": "in_domain", "expected": "Plataformas Académicas (Aula Web / Vortal)"},
    {"text": "no me cargan las materias matriculadas en aula web moodle", "category": "in_domain", "expected": "Plataformas Académicas (Aula Web / Vortal)"},
    {"text": "olvidé la contraseña para entrar al vortal académico", "category": "in_domain", "expected": "Plataformas Académicas (Aula Web / Vortal)"},
    {"text": "el portal de matrícula en línea del vortal se queda en blanco", "category": "in_domain", "expected": "Plataformas Académicas (Aula Web / Vortal)"},
    {"text": "no puedo subir la entrega pdf en aula web y cierra la sesión", "category": "in_domain", "expected": "Plataformas Académicas (Aula Web / Vortal)"},
    {"text": "el volante de pago del vortal no descarga el certificado pdf", "category": "in_domain", "expected": "Plataformas Académicas (Aula Web / Vortal)"},
    {"text": "hay diferencia entre mi horario del vortal y los cursos en aula web", "category": "in_domain", "expected": "Plataformas Académicas (Aula Web / Vortal)"},
    {"text": "caída del sistema académico al registrar calificaciones finales", "category": "in_domain", "expected": "Plataformas Académicas (Aula Web / Vortal)"},
    {"text": "los cuestionarios de moodle en aula web no guardan respuestas", "category": "in_domain", "expected": "Plataformas Académicas (Aula Web / Vortal)"},
    # --- 5. Correo Institucional y Cuentas (9 frases) ---
    {"text": "mi correo @unicesar.edu.co quedó bloqueado tras varios intentos", "category": "in_domain", "expected": "Correo Institucional y Cuentas"},
    {"text": "cambié de celular y no me llega el código mfa para abrir mi correo", "category": "in_domain", "expected": "Correo Institucional y Cuentas"},
    {"text": "solicito creación de cuenta institucional para docente recién vinculado", "category": "in_domain", "expected": "Correo Institucional y Cuentas"},
    {"text": "mi buzón de correo universitario está lleno y rebotan mensajes", "category": "in_domain", "expected": "Correo Institucional y Cuentas"},
    {"text": "llegó un correo sospechoso de phishing pidiendo mi clave", "category": "in_domain", "expected": "Correo Institucional y Cuentas"},
    {"text": "olvidé mi contraseña del correo institucional @unicesar.edu.co", "category": "in_domain", "expected": "Correo Institucional y Cuentas"},
    {"text": "necesito corregir mi apellido en el perfil del directorio de correo", "category": "in_domain", "expected": "Correo Institucional y Cuentas"},
    {"text": "la cuenta institucional de contratista aparece inactiva al entrar al webmail", "category": "in_domain", "expected": "Correo Institucional y Cuentas"},
    {"text": "no recibo correos externos en mi buzón @unicesar.edu.co", "category": "in_domain", "expected": "Correo Institucional y Cuentas"},
    # --- 6. Software y Licenciamiento (8 frases) ---
    {"text": "word y excel de microsoft 365 dicen producto sin licencia", "category": "in_domain", "expected": "Software y Licenciamiento"},
    {"text": "necesito instalar spss y rstudio en el laboratorio para talleres", "category": "in_domain", "expected": "Software y Licenciamiento"},
    {"text": "autocad arroja error de servidor de licencias en ingeniería", "category": "in_domain", "expected": "Software y Licenciamiento"},
    {"text": "matlab muestra licencia vencida en los computadores de la sala", "category": "in_domain", "expected": "Software y Licenciamiento"},
    {"text": "requiero instalar paquetes python sin permisos de administrador", "category": "in_domain", "expected": "Software y Licenciamiento"},
    {"text": "necesito actualización de antivirus corporativo en el equipo", "category": "in_domain", "expected": "Software y Licenciamiento"},
    {"text": "microsoft powerpoint quedó en modo solo lectura por licencia", "category": "in_domain", "expected": "Software y Licenciamiento"},
    {"text": "solicitud de activación de licenciamiento académico para oficinas", "category": "in_domain", "expected": "Software y Licenciamiento"},
    # --- 7. Frases con errores de escritura / typos (20 frases) ---
    {"text": "tengo una conputadora que no prene", "category": "typos", "expected": "Equipos de Cómputo e Impresoras"},
    {"text": "mi conputador tiene pantalla negra", "category": "typos", "expected": "Equipos de Cómputo e Impresoras"},
    {"text": "la inpresora atasco la hoja en la cola", "category": "typos", "expected": "Equipos de Cómputo e Impresoras"},
    {"text": "el escaner de oficina no funciona en el pc", "category": "typos", "expected": "Equipos de Cómputo e Impresoras"},
    {"text": "no hay wiffi ni interne en el salon", "category": "typos", "expected": "Conectividad y Redes Wi-Fi"},
    {"text": "faya de eduroan en mi portatil", "category": "typos", "expected": "Conectividad y Redes Wi-Fi"},
    {"text": "el cliente vpn no conesta desde casa", "category": "typos", "expected": "Conectividad y Redes Wi-Fi"},
    {"text": "el videobean no da señal hdmi", "category": "typos", "expected": "Aulas Inteligentes y Videoproyectores"},
    {"text": "proyector sin senal por vga en salon", "category": "typos", "expected": "Aulas Inteligentes y Videoproyectores"},
    {"text": "parlantes del aula inteligente sin sonido", "category": "typos", "expected": "Aulas Inteligentes y Videoproyectores"},
    {"text": "olbide mi clabe del bortal academico", "category": "typos", "expected": "Plataformas Académicas (Aula Web / Vortal)"},
    {"text": "error en aulaweb no cargan mis cursos", "category": "typos", "expected": "Plataformas Académicas (Aula Web / Vortal)"},
    {"text": "el bortal no deja subir notas parciales", "category": "typos", "expected": "Plataformas Académicas (Aula Web / Vortal)"},
    {"text": "mi cuenta de coreo institucional pide mfa", "category": "typos", "expected": "Correo Institucional y Cuentas"},
    {"text": "buzon institucional de correo blokiado", "category": "typos", "expected": "Correo Institucional y Cuentas"},
    {"text": "olbide mi clabe de correo unicesar", "category": "typos", "expected": "Correo Institucional y Cuentas"},
    {"text": "ofice 365 dice producto sin licensia", "category": "typos", "expected": "Software y Licenciamiento"},
    {"text": "necesito instalar autocat en la sala", "category": "typos", "expected": "Software y Licenciamiento"},
    {"text": "matla pide licensia vencida en laboratorio", "category": "typos", "expected": "Software y Licenciamiento"},
    {"text": "instalar rstudio y spss con licensia academica", "category": "typos", "expected": "Software y Licenciamiento"},
    # --- 8. Frases ambiguas o incompletas -> debe abstenerse (< 0.60, "no sé") (15 frases) ---
    {"text": "necesito ayuda urgente con un problema", "category": "ambiguous", "expected": "ABSTAIN"},
    {"text": "algo falló hoy en la mañana", "category": "ambiguous", "expected": "ABSTAIN"},
    {"text": "no sirve nada", "category": "ambiguous", "expected": "ABSTAIN"},
    {"text": "por favor envíen a alguien rápido", "category": "ambiguous", "expected": "ABSTAIN"},
    {"text": "tengo un daño urgente ayúdenme", "category": "ambiguous", "expected": "ABSTAIN"},
    {"text": "presento un inconveniente desde ayer", "category": "ambiguous", "expected": "ABSTAIN"},
    {"text": "necesito soporte técnico urgente", "category": "ambiguous", "expected": "ABSTAIN"},
    {"text": "hay una falla grave aquí", "category": "ambiguous", "expected": "ABSTAIN"},
    {"text": "no me funciona esto desde temprano", "category": "ambiguous", "expected": "ABSTAIN"},
    {"text": "qué pena me pueden colaborar con algo", "category": "ambiguous", "expected": "ABSTAIN"},
    {"text": "todo está fallando desde la mañana", "category": "ambiguous", "expected": "ABSTAIN"},
    {"text": "requiero asistencia técnica en el bloque", "category": "ambiguous", "expected": "ABSTAIN"},
    {"text": "no responde desde hace una hora", "category": "ambiguous", "expected": "ABSTAIN"},
    {"text": "tengo un error raro y no sé qué es", "category": "ambiguous", "expected": "ABSTAIN"},
    {"text": "ayuda por favor algo se dañó", "category": "ambiguous", "expected": "ABSTAIN"},
    # --- 9. Frases fuera de alcance -> guardrail RNF-13 (15 frases) ---
    {"text": "dame una receta de arroz con pollo", "category": "out_of_scope", "expected": "OUT_OF_SCOPE"},
    {"text": "cómo estuvo el partido de futbol de ayer", "category": "out_of_scope", "expected": "OUT_OF_SCOPE"},
    {"text": "cuál es mi horoscopo de hoy", "category": "out_of_scope", "expected": "OUT_OF_SCOPE"},
    {"text": "cuéntame un chiste corto", "category": "out_of_scope", "expected": "OUT_OF_SCOPE"},
    {"text": "cuál es el clima de hoy en valledupar", "category": "out_of_scope", "expected": "OUT_OF_SCOPE"},
    {"text": "qué novela recomiendas ver en netflix", "category": "out_of_scope", "expected": "OUT_OF_SCOPE"},
    {"text": "dime los números de la loteria", "category": "out_of_scope", "expected": "OUT_OF_SCOPE"},
    {"text": "quiero hacer una apuesta deportiva", "category": "out_of_scope", "expected": "OUT_OF_SCOPE"},
    {"text": "cuál es la capital de francia", "category": "out_of_scope", "expected": "OUT_OF_SCOPE"},
    {"text": "escríbeme un poema romántico", "category": "out_of_scope", "expected": "OUT_OF_SCOPE"},
    {"text": "qué pelicula ganó el oscar", "category": "out_of_scope", "expected": "OUT_OF_SCOPE"},
    {"text": "ponme una cancion famosa", "category": "out_of_scope", "expected": "OUT_OF_SCOPE"},
    {"text": "como puedo cocinar pasta en casa", "category": "out_of_scope", "expected": "OUT_OF_SCOPE"},
    {"text": "dime mi futuro segun la astrologia", "category": "out_of_scope", "expected": "OUT_OF_SCOPE"},
    {"text": "quien gano el mundial de futbol", "category": "out_of_scope", "expected": "OUT_OF_SCOPE"},
]


def run_agent_evaluation(
    uow_factory: Callable[[], IUnitOfWork],
    ai_engine: LocalNLPEngine,
) -> Dict[str, Any]:
    """Evalúa las 105 frases midiendo precisión en dominio/typos y tasa correcta de 'no sé'/fuera de alcance."""
    handler = ProcessAgentTurnCommandHandler(uow_factory, ai_engine)

    in_domain_total = 0
    in_domain_correct = 0
    typos_total = 0
    typos_correct = 0
    ambiguous_total = 0
    ambiguous_correct = 0
    oos_total = 0
    oos_correct = 0
    failures: List[Dict[str, Any]] = []

    for row in EVALUATION_DATASET_105:
        text = row["text"]
        cat = row["category"]
        expected = row["expected"]

        res = handler.handle(
            ProcessAgentTurnCommand(
                user=None,
                message=text,
                failed_attempts=1,
            )
        )
        pred = res.get("prediction") or {}
        pred_svc = pred.get("predicted_service")
        conf = float(pred.get("confidence", 0.0))
        status = res.get("status")

        if cat in ("in_domain", "typos"):
            ok = (pred_svc == expected) and (conf >= 0.60) and status not in ("needs_clarification", "out_of_scope")
            if cat == "in_domain":
                in_domain_total += 1
                if ok:
                    in_domain_correct += 1
            else:
                typos_total += 1
                if ok:
                    typos_correct += 1
            if not ok:
                failures.append({"text": text, "category": cat, "expected": expected, "got": pred_svc, "confidence": conf, "status": status})
        elif cat == "ambiguous":
            ambiguous_total += 1
            ok = status == "needs_clarification" and conf < 0.60
            if ok:
                ambiguous_correct += 1
            else:
                failures.append({"text": text, "category": cat, "expected": expected, "got": pred_svc, "confidence": conf, "status": status})
        else:
            oos_total += 1
            ok = status == "out_of_scope"
            if ok:
                oos_correct += 1
            else:
                failures.append({"text": text, "category": cat, "expected": expected, "got": status, "confidence": conf})

    domain_combined_total = in_domain_total + typos_total
    domain_combined_correct = in_domain_correct + typos_correct
    abstention_combined_total = ambiguous_total + oos_total
    abstention_combined_correct = ambiguous_correct + oos_correct

    # Caso de regresión del Sprint 0
    s0_text = "tengo un problema con una computadora que no prende"
    s0_entities = extract_explicit_ticket_entities(s0_text)
    s0_res = handler.handle(ProcessAgentTurnCommand(user=None, message=s0_text, failed_attempts=1))
    s0_pred = s0_res.get("prediction") or {}

    return {
        "total_phrases": len(EVALUATION_DATASET_105),
        "in_domain_total": domain_combined_total,
        "in_domain_correct": domain_combined_correct,
        "in_domain_accuracy_pct": round((domain_combined_correct / max(1, domain_combined_total)) * 100.0, 2),
        "typos_total": typos_total,
        "typos_correct": typos_correct,
        "typos_accuracy_pct": round((typos_correct / max(1, typos_total)) * 100.0, 2),
        "abstention_and_out_of_scope_total": abstention_combined_total,
        "abstention_correct": abstention_combined_correct,
        "abstention_accuracy_pct": round((abstention_combined_correct / max(1, abstention_combined_total)) * 100.0, 2),
        "ambiguous_total": ambiguous_total,
        "ambiguous_correct": ambiguous_correct,
        "out_of_scope_total": oos_total,
        "out_of_scope_correct": oos_correct,
        "failures": failures,
        "sprint0_regression_case": {
            "text": s0_text,
            "predicted_service": s0_pred.get("predicted_service"),
            "confidence": s0_pred.get("confidence"),
            "confidence_pct": s0_pred.get("confidence_pct"),
            "assumed_sede": s0_entities["sede"],
            "assumed_location": s0_entities["location"],
            "assumed_urgency": s0_entities["urgency"],
            "agent_status": s0_res.get("status"),
            "missing_fields": s0_res.get("missing_fields"),
        },
    }
