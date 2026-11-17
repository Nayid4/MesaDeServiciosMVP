"""Datos demo KB parte D: Software y licencias, VPN y Seguridad básica."""

from __future__ import annotations

from typing import Any, Dict, List

KB_DATA_D: List[Dict[str, Any]] = [
    {
        "code": "KB-008",
        "title": "[DEMO] Activación de Microsoft 365 institucional con cuenta @unicesar.edu.co",
        "service_name": "Software y Licenciamiento",
        "category_topic": "Software y licencias",
        "symptoms": "Word, Excel o PowerPoint muestran aviso 'Producto sin licencia' o bloquean la edición de documentos.",
        "probable_cause": "Sesión de Office expirada o iniciada con cuenta personal diferente a la licencia institucional.",
        "solution_steps": (
            "1. Abra Word o Excel y seleccione Archivo > Cuenta > Cerrar sesión si figura una cuenta personal.\n"
            "2. Inicie sesión con su cuenta educativa institucional asignada [CONFIRMAR plan vigente].\n"
            "3. Reinicie la aplicación y verifique que aparezca el estado 'Producto de suscripción activado'."
        ),
        "escalation_criteria": "Escalar a Mesa de Software si indica que la cuenta no tiene licencia asignada.",
        "keywords": "office word excel powerpoint licencia microsoft 365 activacion",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico5@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-032",
        "title": "[DEMO] Instalación de paquetes Python, RStudio y entornos de desarrollo en salas",
        "service_name": "Software y Licenciamiento",
        "category_topic": "Software y licencias",
        "symptoms": "Faltan librerías científicas en RStudio/Python o el usuario no tiene privilegios de administrador en laboratorio.",
        "probable_cause": "Restricciones de seguridad de usuario estándar en equipos de uso compartido.",
        "solution_steps": (
            "1. En entornos Python utilice entornos virtuales en su carpeta de usuario cuando el equipo lo permita.\n"
            "2. Para librerías globales o actualización de IDE antes de parciales o talleres, radique solicitud indicando la lista exacta (requirements.txt).\n"
            "3. Indique el laboratorio específico y fecha programada de la práctica."
        ),
        "escalation_criteria": "Escalar a Mesa de Software para inclusión en la imagen oficial del laboratorio.",
        "keywords": "python rstudio vscode ide librerias laboratorio administrador instalacion",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico5@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-033",
        "title": "[DEMO] Error de servidor de licencias en AutoCAD o software de ingeniería",
        "service_name": "Software y Licenciamiento",
        "category_topic": "Software y licencias",
        "symptoms": "Al abrir AutoCAD o software CAD aparece mensaje 'No se pudo obtener una licencia del servidor'.",
        "probable_cause": "Equipo fuera de la subred autorizada, servicio de administrador de licencias detenido o límite de cupos simultáneos.",
        "solution_steps": (
            "1. Confirme que el computador esté conectado a la red institucional o VPN habilitada según corresponda [CONFIRMAR].\n"
            "2. Cierre el mensaje, espere 2 minutos si el laboratorio tiene muchos equipos abriendo al tiempo e intente de nuevo.\n"
            "3. Tome captura del código de error FlexNet o licencia de red mostrado en pantalla."
        ),
        "escalation_criteria": "Escalar a Mesa de Software y Redes si falla en todo un laboratorio simultáneamente.",
        "keywords": "autocad flexnet servidor licencias cad cupos red ingenieria",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico5@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-034",
        "title": "[DEMO] Guía interna técnica: actualización y verificación de agente antivirus institucional",
        "service_name": "Software y Licenciamiento",
        "category_topic": "Software y licencias",
        "symptoms": "Estación de trabajo administrativa reporta firmas antivirus desactualizadas o servicio detenido en consola.",
        "probable_cause": "Pérdida de conectividad con consola central de seguridad o corrupción tras apagado forzado.",
        "solution_steps": (
            "1. Verifique en la consola de protección de endpoints el último latido (heartbeat) del equipo [CONFIRMAR].\n"
            "2. Ejecute sincronización manual de firmas y compruebe que el firewall del sistema permanezca activo.\n"
            "3. Si el agente no reporta después de reiniciar, reinstale mediante paquete firmado institucional."
        ),
        "escalation_criteria": "Escalar a Seguridad TIC si se detecta intento de manipulación o desactivación no autorizada.",
        "keywords": "interno antivirus endpoint firmas consola seguridad software",
        "visibility": "Interna",
        "status": "Publicado",
        "author_email": "tecnico5@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-035",
        "title": "[DEMO] Solicitud de acceso y configuración inicial del cliente VPN institucional",
        "service_name": "Conectividad y Redes Wi-Fi",
        "category_topic": "VPN",
        "symptoms": "Personal administrativo o investigador necesita acceder desde fuera del campus a sistemas internos mediante VPN.",
        "probable_cause": "Perfil de usuario aún no autorizado en el grupo VPN o cliente VPN sin configurar [CONFIRMAR].",
        "solution_steps": (
            "1. Solicite autorización previa de su jefe de dependencia justificando los recursos internos requeridos [CONFIRMAR].\n"
            "2. Radique solicitud en Mesa de Servicios con el aval y el sistema operativo de su equipo.\n"
            "3. Descargue únicamente el instalador oficial y parámetros de portal suministrados por Redes TIC [CONFIRMAR]."
        ),
        "escalation_criteria": "Escalar a Redes e Infraestructura para aprobación en directorio y aprovisionamiento de perfil.",
        "keywords": "vpn acceso remoto cliente configuracion perfil campus fuera",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico1@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-036",
        "title": "[DEMO] Error de conexión o tiempo agotado en el túnel VPN desde el hogar",
        "service_name": "Conectividad y Redes Wi-Fi",
        "category_topic": "VPN",
        "symptoms": "El cliente VPN se queda en 'Conectando...' y falla con error de timeout o rechazo de segundo factor.",
        "probable_cause": "Bloqueo de puerto UDP/TCP por el operador de internet doméstico, reloj desincronizado o token MFA expirado.",
        "solution_steps": (
            "1. Compruebe su acceso general a internet antes de iniciar el cliente VPN.\n"
            "2. Asegúrese de que la fecha y hora de su sistema estén en sincronización automática (UTC-5 Bogotá).\n"
            "3. Apruebe oportunamente la notificación de verificación en dos pasos y reintente."
        ),
        "escalation_criteria": "Escalar a Redes e Infraestructura adjuntando captura de registro del cliente VPN y hora exacta.",
        "keywords": "vpn timeout conectando error mfa hogar puerto reloj",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico1@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-037",
        "title": "[DEMO] VPN conecta pero no resuelve nombres o aplicaciones internas",
        "service_name": "Conectividad y Redes Wi-Fi",
        "category_topic": "VPN",
        "symptoms": "El túnel VPN aparece conectado, sin embargo al abrir la URL interna muestra 'No se puede acceder al sitio'.",
        "probable_cause": "Conflicto de subred doméstica (ej. 192.168.1.x), DNS en caché o regla de split-tunnel faltante [CONFIRMAR].",
        "solution_steps": (
            "1. Cierre el navegador, ejecute en consola 'ipconfig /flushdns' y pruebe en ventana privada.\n"
            "2. Valide si otro equipo conectado con la misma red de internet logra resolver el recurso.\n"
            "3. Anote la IP asignada por la VPN y el recurso específico inaccesible al radicar el ticket."
        ),
        "escalation_criteria": "Escalar a Redes e Infraestructura para revisión de rutas DNS y listas de control de acceso.",
        "keywords": "vpn dns ruta split tunnel aplicacion interna no resuelve",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico1@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-038",
        "title": "[DEMO] Guía interna técnica: diagnóstico de túneles SSL/IPsec y revocación de VPN",
        "service_name": "Conectividad y Redes Wi-Fi",
        "category_topic": "VPN",
        "symptoms": "Revisión de sesiones VPN activas tras baja laboral o falla masiva de gateway VPN.",
        "probable_cause": "Cambio de certificado SSL en concentrador VPN o expiración de acceso temporal de contratista.",
        "solution_steps": (
            "1. Consulte en el concentrador VPN las sesiones activas y registro de autenticación de las últimas 24 horas [CONFIRMAR].\n"
            "2. Ante desvinculación de personal, retire el usuario del grupo VPN inmediatamente tras notificación de Talento Humano.\n"
            "3. Valide vigencia de certificados antes de ventanas de mantenimiento."
        ),
        "escalation_criteria": "Escalar a Ingeniería de Seguridad y Dirección TIC en incidentes de saturación o intrusión.",
        "keywords": "interno vpn gateway ssl ipsec revocacion concentrador",
        "visibility": "Interna",
        "status": "Publicado",
        "author_email": "coordinador@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-039",
        "title": "[DEMO] Cómo identificar y reportar correos sospechosos o phishing institucional",
        "service_name": "Correo Institucional y Cuentas",
        "category_topic": "Seguridad básica",
        "symptoms": "Llegó un correo urgente solicitando validar cuenta, pagar multa o abrir enlace externo sospechoso.",
        "probable_cause": "Campaña de ingeniería social / phishing suplantando identidad universitaria.",
        "solution_steps": (
            "1. No haga clic en enlaces ni descargue adjuntos; verifique siempre la dirección real del remitente.\n"
            "2. Recuerde que el equipo TIC nunca solicita contraseñas ni códigos MFA por correo o WhatsApp.\n"
            "3. Reporte el mensaje usando la opción 'Informar suplantación / phishing' [CONFIRMAR] o cree un ticket en Mesa de Servicios."
        ),
        "escalation_criteria": "Si ya ingresó su clave o abrió un archivo sospechoso, cambie la clave de inmediato y escale con prioridad Crítica.",
        "keywords": "phishing suplantacion correo sospechoso estafa enlace seguridad",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico3@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-040",
        "title": "[DEMO] Buenas prácticas de contraseñas robustas y bloqueo de sesión en aulas",
        "service_name": "Correo Institucional y Cuentas",
        "category_topic": "Seguridad básica",
        "symptoms": "Uso de equipos compartidos en salas o laboratorios sin cerrar sesión institucional al finalizar la clase.",
        "probable_cause": "Olvido de cierre de sesión en navegadores públicos o guardado automático de credenciales.",
        "solution_steps": (
            "1. En salas y aulas inteligentes utilice siempre ventanas de navegación privada (Incógnito) y pulse 'No guardar contraseña'.\n"
            "2. Antes de retirarse del puesto cierre completamente su sesión en Vortal, Aula Web y correo.\n"
            "3. Use frases clave únicas de mínimo 12 caracteres mezclando letras, números y símbolos [CONFIRMAR política UPC]."
        ),
        "escalation_criteria": "Si dejó abierta una sesión en equipo público, revoque sesiones desde su cuenta o solicite apoyo a Identidad y Accesos.",
        "keywords": "seguridad sesion abierta incognito sala computo clave robusta bloqueo",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico3@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-041",
        "title": "[DEMO] Respaldo seguro de información académica y laboral en almacenamiento institucional",
        "service_name": "Software y Licenciamiento",
        "category_topic": "Seguridad básica",
        "symptoms": "Pérdida potencial de documentos al guardar archivos únicamente en el Escritorio de equipos compartidos o USB.",
        "probable_cause": "Congelamiento de disco en salas de cómputo (Deep Freeze o similar [CONFIRMAR]) o falla física de memorias USB.",
        "solution_steps": (
            "1. Guarde trabajos y calificaciones en la nube institucional autorizada en lugar de carpetas locales temporales [CONFIRMAR].\n"
            "2. Realice copias periódicas de archivos críticos antes de mantenimiento de equipos.\n"
            "3. Analice memorias USB antes de abrir archivos desconocidos en estaciones de trabajo."
        ),
        "escalation_criteria": "Escalar a Soporte en Campo o Seguridad TIC ante comportamiento inusual o cifrado inesperado de archivos.",
        "keywords": "respaldo copia seguridad nube usb perdida archivos ransomware",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico5@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-042",
        "title": "[DEMO] Qué hacer ante sospecha de virus, ransomware o equipo comprometido",
        "service_name": "Software y Licenciamiento",
        "category_topic": "Seguridad básica",
        "symptoms": "Ventanas emergentes inusuales, extensiones cambiadas en archivos o consumo anómalo de red en estación de trabajo.",
        "probable_cause": "Ejecución de archivo malicioso o infección activa de malware/ransomware.",
        "solution_steps": (
            "1. Desconecte de inmediato el cable de red Ethernet y apague el Wi-Fi del equipo afectado para evitar propagación.\n"
            "2. NO apague por completo el sistema si observa cifrado activo, ni conecte memorias USB externas.\n"
            "3. Comunique el incidente urgente a través de otro equipo seleccionando prioridad Alta en Mesa de Servicios."
        ),
        "escalation_criteria": "Escalar de inmediato como incidente crítico a Seguridad TIC, Redes y Coordinación de Mesa.",
        "keywords": "virus malware ransomware equipo infectado desconectar incidente seguridad",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico6@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
]
