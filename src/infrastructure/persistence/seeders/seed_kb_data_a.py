"""Datos demo KB parte A: Cuentas/correo y Wi-Fi/Eduroam."""

from __future__ import annotations

from typing import Any, Dict, List

KB_DATA_A: List[Dict[str, Any]] = [
    {
        "code": "KB-003",
        "title": "[DEMO] Desbloqueo de correo institucional @unicesar.edu.co y verificación MFA",
        "service_name": "Correo Institucional y Cuentas",
        "category_topic": "Cuentas y correo",
        "symptoms": "Cuenta de correo institucional @unicesar.edu.co bloqueada por intentos fallidos o cambio de teléfono para MFA, o contraseña olvidada.",
        "probable_cause": "Superación del límite de intentos fallidos de acceso, expiración de clave o pérdida del dispositivo asociado al segundo factor MFA [CONFIRMAR].",
        "solution_steps": (
            "1. Espere 15 minutos si superó los intentos fallidos de inicio de sesión [CONFIRMAR].\n"
            "2. Ingrese al portal de autogestión de cuenta UPC ([CONFIRMAR] URL oficial de identidad) usando su método de verificación alterno.\n"
            "3. Si cambió de teléfono para MFA o persiste el bloqueo, siga el procedimiento de restablecimiento de contraseña institucional."
        ),
        "escalation_criteria": "Escalar al área de Identidad y Accesos si el bloqueo supera 30 minutos o si no dispone de acceso al segundo factor MFA.",
        "keywords": "correo institucional cuenta bloqueada mfa contraseña clave unicesar @unicesar.edu.co",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico3@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-011",
        "title": "[DEMO] Creación de cuentas institucionales para nuevos docentes y contratistas",
        "service_name": "Correo Institucional y Cuentas",
        "category_topic": "Cuentas y correo",
        "symptoms": "Personal recién vinculado no cuenta aún con usuario institucional ni buzón habilitado para plataformas académicas.",
        "probable_cause": "Vinculación contractual reciente pendiente de alta en el directorio institucional [CONFIRMAR].",
        "solution_steps": (
            "1. Verifique con Talento Humano o decanatura que el acto de vinculación o contrato esté activo [CONFIRMAR].\n"
            "2. Radique una solicitud en Mesa de Servicios adjuntando documento de identidad y soporte de vinculación.\n"
            "3. Confirme en su correo alterno la recepción de credenciales temporales dentro del SLA vigente."
        ),
        "escalation_criteria": "Escalar a Identidad y Accesos cuando exista urgencia de inicio de clases o el alta administrativa supere el plazo hábil [CONFIRMAR].",
        "keywords": "cuenta nueva contratista docente creacion usuario vinculacion alta",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico3@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-013",
        "title": "[DEMO] Buzón de correo lleno o rechazo de mensajes adjuntos",
        "service_name": "Correo Institucional y Cuentas",
        "category_topic": "Cuentas y correo",
        "symptoms": "No ingresan correos nuevos o al enviar adjuntos pesados el sistema devuelve rebote por cuota o tamaño.",
        "probable_cause": "Cuota de almacenamiento del buzón cercana al 100 % o archivo adjunto superior al límite permitido [CONFIRMAR].",
        "solution_steps": (
            "1. Revise el porcentaje de uso de almacenamiento en la configuración del webmail institucional [CONFIRMAR].\n"
            "2. Vacíe carpetas de Elementos eliminados y Correo no deseado y archive mensajes antiguos con adjuntos pesados.\n"
            "3. Para archivos grandes, compártalos mediante enlace institucional en la nube en lugar de adjunto directo."
        ),
        "escalation_criteria": "Escalar a Identidad y Accesos si tras liberar más del 20 % del buzón continúan los rebotes.",
        "keywords": "buzon lleno cuota almacenamiento adjunto rebote webmail",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico3@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-014",
        "title": "[DEMO] Cambio de nombre mostrado o actualización de datos en perfil de identidad",
        "service_name": "Correo Institucional y Cuentas",
        "category_topic": "Cuentas y correo",
        "symptoms": "Apellidos, tildes o dependencia aparecen desactualizados en el directorio institucional o firmas electrónicas.",
        "probable_cause": "Desincronización entre la base académica/administrativa de origen y el directorio de cuentas [CONFIRMAR].",
        "solution_steps": (
            "1. Confirme que sus datos estén corregidos en Registro y Control o Talento Humano según su estamento [CONFIRMAR].\n"
            "2. Solicite en Mesa de Servicios la actualización indicando el texto exacto y documento de soporte."
        ),
        "escalation_criteria": "Escalar a Identidad y Accesos con soporte documental oficial para edición del directorio.",
        "keywords": "cambio nombre directorio perfil tildes actualizacion datos identidad",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico3@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-015",
        "title": "[DEMO] Guía interna técnica: reinicio de sesiones activas y tokens MFA de usuario",
        "service_name": "Correo Institucional y Cuentas",
        "category_topic": "Cuentas y correo",
        "symptoms": "Usuario reporta acceso no autorizado o cambio de dispositivo móvil sin respaldo de códigos.",
        "probable_cause": "Sesión OAuth vigente en equipo anterior o registro MFA vinculado a terminal extraviado.",
        "solution_steps": (
            "1. Valide la identidad del solicitante mediante verificación institucional establecida [CONFIRMAR].\n"
            "2. En la consola de administración de identidad revoque tokens de actualización activos y exija nuevo registro MFA [CONFIRMAR].\n"
            "3. Solicite al usuario definir nueva clave robusta al primer ingreso."
        ),
        "escalation_criteria": "Escalar de inmediato a Coordinación y Seguridad TIC si se observan accesos anómalos.",
        "keywords": "interno revocar sesiones tokens mfa identidad tecnico administracion",
        "visibility": "Interna",
        "status": "Publicado",
        "author_email": "coordinador@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-002",
        "title": "[DEMO] Configuración general de la red inalámbrica institucional Wi-Fi Eduroam",
        "service_name": "Conectividad y Redes Wi-Fi",
        "category_topic": "Wi-Fi y Eduroam",
        "symptoms": "El portátil o celular no conecta a la red Wi-Fi Eduroam en bloques académicos o solicita certificado.",
        "probable_cause": "Parámetros EAP/PEAP incorrectos, credenciales desactualizadas o perfil Wi-Fi antiguo guardado.",
        "solution_steps": (
            "1. Seleccione la red inalámbrica 'eduroam' y olvide configuraciones previas antes de reintentar.\n"
            "2. En método EAP elija PEAP y autenticación MSCHAPv2 [CONFIRMAR].\n"
            "3. Use su usuario completo institucional y valide certificados conforme a la guía de su sistema operativo."
        ),
        "escalation_criteria": "Escalar a Redes e Infraestructura indicando bloque, piso y dirección MAC si falla con credenciales válidas.",
        "keywords": "wifi wi-fi eduroam red inalambrica internet conectar bloques eap peap",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico1@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-016",
        "title": "[DEMO] Configuración paso a paso de Wi-Fi Eduroam en Windows 10 y Windows 11",
        "service_name": "Conectividad y Redes Wi-Fi",
        "category_topic": "Wi-Fi y Eduroam",
        "symptoms": "En Windows 10/11 aparece el mensaje 'No se puede conectar a esta red' al intentar conectarse a Eduroam.",
        "probable_cause": "Perfil automático de Windows con credenciales en caché o controlador de tarjeta Wi-Fi desactualizado.",
        "solution_steps": (
            "1. Abra Configuración > Red e Internet > Wi-Fi > Administrar redes conocidas y haga clic en 'Dejar de recordar' sobre eduroam.\n"
            "2. Cree conexión manual o conéctese a eduroam verificando EAP-PEAP / MSCHAPv2 ([CONFIRMAR] política de certificado CA UPC).\n"
            "3. Si usa instalador oficial CAT, descargue únicamente desde el enlace institucional vigente [CONFIRMAR]."
        ),
        "escalation_criteria": "Escalar a Redes e Infraestructura si ocurre en todos los bloques tras reiniciar adaptador de red.",
        "keywords": "eduroam windows 10 windows 11 wifi no se puede conectar perfil tarjeta",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico1@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-017",
        "title": "[DEMO] Configuración de Wi-Fi Eduroam en dispositivos móviles Android e iOS",
        "service_name": "Conectividad y Redes Wi-Fi",
        "category_topic": "Wi-Fi y Eduroam",
        "symptoms": "En Android o iPhone solicita 'Dominio' o certificado de CA al conectarse a Eduroam y rechaza la conexión.",
        "probable_cause": "Android 11+ e iOS exigen especificar dominio de servidor RADIUS o aceptar el certificado institucional [CONFIRMAR].",
        "solution_steps": (
            "1. En Android seleccione EAP: PEAP, Autenticación Fase 2: MSCHAPv2 y en Certificado CA 'Usar certificados del sistema' [CONFIRMAR].\n"
            "2. En el campo Dominio escriba el dominio institucional oficial indicado por Redes TIC ([CONFIRMAR] ej. unicesar.edu.co) y deje Identidad anónima vacía.\n"
            "3. En iOS/iPadOS toque 'Confiar' al visualizar el certificado del servidor RADIUS verificado [CONFIRMAR]."
        ),
        "escalation_criteria": "Escalar a Redes e Infraestructura si ningún usuario del aula logra autenticar en Eduroam.",
        "keywords": "eduroam android ios iphone celular movil certificado dominio radius",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico1@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-010",
        "title": "[DEMO] Problemas de red cableada LAN y obtención de IP en bloques académicos",
        "service_name": "Conectividad y Redes Wi-Fi",
        "category_topic": "Wi-Fi y Eduroam",
        "symptoms": "El icono de red en escritorio muestra 'Sin acceso a internet' o 'Red no identificada' con cable Ethernet.",
        "probable_cause": "Cable RJ45 defectuoso, dirección APIPA (169.254.x.x) por falla DHCP o puerto de switch inactivo.",
        "solution_steps": (
            "1. Verifique que los LEDs del puerto RJ45 parpadeen al conectar el cable de red.\n"
            "2. Ejecute en consola 'ipconfig /release' y luego 'ipconfig /renew'.\n"
            "3. Si asigna IP 169.254.x.x, registre el número de toma de pared para revisión física del punto."
        ),
        "escalation_criteria": "Escalar a Redes e Infraestructura cuando múltiples equipos del mismo bloque pierden DHCP o enlace.",
        "keywords": "red cableada lan ethernet ip dhcp switch sin internet puerto rj45",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico1@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-012",
        "title": "[DEMO] Guía interna técnica: reinicio remoto de puntos de acceso Aruba y switches de piso",
        "service_name": "Conectividad y Redes Wi-Fi",
        "category_topic": "Wi-Fi y Eduroam",
        "symptoms": "Saturación de clientes o pérdida de balizas inalámbricas en un bloque específico.",
        "probable_cause": "Bloqueo temporal del punto de acceso o caída PoE en puerto uplink de switch de acceso.",
        "solution_steps": (
            "1. Ingrese a la consola de gestión de red inalámbrica con usuario técnico autorizado [CONFIRMAR].\n"
            "2. Verifique el presupuesto PoE del puerto en el switch de distribución del bloque.\n"
            "3. Aplique reinicio controlado verificando impacto en aulas en sesión."
        ),
        "escalation_criteria": "Escalar a ingeniería de red si el AP no vuelve en línea tras restablecimiento PoE.",
        "keywords": "aruba switch ap poe tecnico red interno inalambrico",
        "visibility": "Interna",
        "status": "Publicado",
        "author_email": "tecnico1@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
]
