"""Plantillas lingüísticas y distribuciones sintéticas por servicio TIC UPC."""

from __future__ import annotations

from typing import Dict, List

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

SERVICE_TEMPLATES: Dict[str, Dict[str, List[str]]] = {
    "Conectividad y Redes Wi-Fi": {
        "subjects": [
            "Sin conexión a red Wi-Fi Eduroam en {ubicacion}",
            "Caída de internet cableado y Wi-Fi en {ubicacion}",
            "Falla de acceso a Wi-Fi o VPN institucional en {sede}",
            "Punto de acceso inalámbrico sin internet en {ubicacion}",
            "Falla de conectividad LAN, Ethernet y DHCP en {ubicacion}",
            "No asigna dirección IP ni conecta a internet en {ubicacion}",
        ],
        "symptoms": [
            "Desde temprano varios equipos en el bloque pierden paquetes y no abren páginas ni tienen internet.",
            "El Wi-Fi Eduroam aparece conectado sin internet o rechaza la autenticación en la red inalámbrica del bloque.",
            "El cable Ethernet en el puerto RJ45 muestra enlace caído y deja sin conexión LAN al computador.",
            "La señal inalámbrica Wi-Fi se desconecta cada pocos minutos y el cliente VPN marca error de conexión.",
            "Los estudiantes intentan conectarse a Eduroam desde portátil o celular pero la red inalámbrica falla.",
            "El switch de piso presenta alerta de puerto y dejó sin internet al corredor de {ubicacion}.",
        ],
    },
    "Plataformas Académicas (Aula Web / Vortal)": {
        "subjects": [
            "Error 500 al ingresar al Vortal académico",
            "No cargan los cursos virtuales en Aula Web",
            "Falla en módulo de matrícula y registro de notas en Vortal",
            "Sesión expirada constantemente en plataforma Aula Web",
            "No permite subir calificaciones finales en Vortal académico",
            "Caída del portal académico institucional durante inscripción",
        ],
        "symptoms": [
            "Al autenticar en el Vortal académico aparece página en blanco, error HTTP 500 y no carga el horario.",
            "La plataforma Aula Web (Moodle) no muestra las asignaturas matriculadas este semestre.",
            "Al intentar guardar notas parciales el Vortal arroja error de servidor y cierra la sesión del docente.",
            "Los docentes no pueden subir material PDF ni activar cuestionarios en Aula Web desde ningún navegador.",
            "El módulo de matrícula académica en línea se queda cargando indefinidamente en el portal.",
            "Se presenta inconsistencia entre las materias registradas en Vortal y los cursos visibles en Aula Web.",
        ],
    },
    "Correo Institucional y Cuentas": {
        "subjects": [
            "Restablecimiento de contraseña correo @unicesar.edu.co",
            "Cuenta institucional bloqueada tras intentos de ingreso",
            "Solicitud de creación de buzón institucional para nuevo integrante",
            "No llegan mensajes ni código MFA al correo universitario",
            "Error de autenticación de cuenta @unicesar.edu.co",
            "Reactivación de usuario y buzón institucional UPC",
        ],
        "symptoms": [
            "Olvidé la contraseña del correo institucional @unicesar.edu.co y no puedo acceder a mi buzón.",
            "Al entrar al correo universitario aparece aviso de cuenta bloqueada por intentos fallidos.",
            "Se requiere crear cuenta institucional @unicesar.edu.co para docente recién vinculado.",
            "Los correos enviados desde mi buzón institucional rebotan por buzón lleno o error de cuota.",
            "El código de verificación en dos pasos MFA no llega al celular y bloquea el acceso a la cuenta.",
            "La credencial institucional aparece inactiva y no deja iniciar sesión en el webmail.",
        ],
    },
    "Aulas Inteligentes y Videoproyectores": {
        "subjects": [
            "Videoproyector del salón sin señal en {ubicacion}",
            "Cable HDMI o VGA dañado en videoproyector del aula",
            "Pantalla interactiva sin respuesta táctil en {ubicacion}",
            "Sin audio en parlantes del aula inteligente",
            "Videobeam desconfigurado y sin imagen en {sede}",
            "Alerta de lámpara agotada o parpadeo rojo en proyector",
        ],
        "symptoms": [
            "Al conectar el portátil al proyector del aula inteligente muestra Sin Señal por cable HDMI y VGA.",
            "El videoproyector o videobeam del salón se apaga a los pocos minutos con LED rojo de lámpara.",
            "Los parlantes y amplificador de sonido del aula inteligente emiten zumbido y no reproducen audio.",
            "La caja de piso HDMI del salón tiene el conector suelto y el proyector no proyecta imagen.",
            "La pizarra o pantalla interactiva del aula no calibra el puntero táctil durante la exposición.",
            "El videoproyector del salón proyecta imagen borrosa o amarillenta por fallo en puerto VGA/HDMI.",
        ],
    },
    "Equipos de Cómputo e Impresoras": {
        "subjects": [
            "Computador o computadora no prende en {ubicacion}",
            "PC de escritorio con pantalla negra y sin video en {ubicacion}",
            "Portátil o torre de computador no enciende ni arranca",
            "Impresora institucional con atasco de papel o sin conexión",
            "Lentitud extrema y pantallazo azul en equipo de cómputo",
            "Cambio de tóner o escáner sin reconocimiento en oficina",
        ],
        "symptoms": [
            "Tengo un problema con una computadora que no prende ni enciende luces en la torre.",
            "La PC de escritorio tiene el monitor en pantalla negra, emite pitidos y no da video al arrancar.",
            "El portátil o computador de la sala se queda congelado con lentitud extrema y disco al 100 por ciento.",
            "La impresora compartida de la oficina tiene atasco de papel en el fusor y detuvo la cola de impresión.",
            "Al presionar el botón de encendido la torre o CPU del computador no responde ni arranca el sistema.",
            "Los puertos USB, teclado, mouse o escáner multifuncional dejaron de funcionar en este computador.",
        ],
    },
    "Software y Licenciamiento": {
        "subjects": [
            "Solicitud de instalación de SPSS y RStudio en laboratorio",
            "Licencia vencida de MATLAB o AutoCAD en {ubicacion}",
            "Activación de paquete ofimático Microsoft 365 institucional",
            "Actualización de antivirus y permisos de software académico",
            "Requerimiento de Python y entornos de desarrollo en salas",
            "Error de servidor de licencias FlexNet en software de ingeniería",
        ],
        "symptoms": [
            "Al abrir AutoCAD o MATLAB en la sala solicita clave de licencia vencida y cierra el programa.",
            "Para las prácticas académicas se solicita instalar SPSS, RStudio y librerías de Python en los equipos.",
            "Microsoft Word, Excel y PowerPoint muestran aviso de producto sin licencia activada de Office 365.",
            "El sistema solicita clave de administrador para instalar software autorizado en el laboratorio.",
            "El servidor de licencias de software de ingeniería arroja error de activación de cupos.",
            "Se requiere renovar licenciamiento institucional y actualizar antivirus en las estaciones.",
        ],
    },
}

CROSS_SERVICE_CONTEXT: Dict[str, List[str]] = {
    "Conectividad y Redes Wi-Fi": [
        "Otros equipos del mismo bloque tampoco tienen internet ni alcanzan a abrir páginas.",
        "El computador enciende correctamente pero ni el Wi-Fi Eduroam ni el cable LAN conectan.",
        "En la red inalámbrica aparece sin acceso a internet o falla el cliente VPN.",
    ],
    "Plataformas Académicas (Aula Web / Vortal)": [
        "El internet funciona normal en el equipo pero únicamente falla Vortal y Aula Web.",
        "Ya probé en dos navegadores distintos pero la plataforma académica sigue arrojando error.",
        "Mi correo institucional abre bien, el inconveniente ocurre solamente al entrar a Aula Web.",
    ],
    "Correo Institucional y Cuentas": [
        "Tengo internet estable en el campus pero mi cuenta institucional rechaza la clave y pide MFA.",
        "El portal general carga normal pero mi usuario @unicesar.edu.co aparece bloqueado.",
        "Necesito desbloquear credenciales del buzón institucional y verificar acceso único.",
    ],
    "Aulas Inteligentes y Videoproyectores": [
        "El portátil del docente enciende normal pero el videoproyector o videobeam del salón marca sin señal.",
        "La red Wi-Fi funciona bien, la falla está únicamente en el cable HDMI/VGA y sonido del aula.",
        "El proyector y los parlantes del aula inteligente requieren revisión antes de iniciar clase.",
    ],
    "Equipos de Cómputo e Impresoras": [
        "La red del área funciona en los demás puestos pero esta computadora no prende y tiene pantalla negra.",
        "No se puede imprimir ni trabajar porque la torre del PC no arranca y la impresora marca atasco.",
        "Necesitamos revisión física del computador portátil, fuente de poder o impresora multifuncional.",
    ],
    "Software y Licenciamiento": [
        "El computador enciende bien y conecta a Wi-Fi pero AutoCAD, MATLAB y SPSS piden activación.",
        "Tengo red y correo activos, sin embargo Microsoft 365 muestra aviso de licencia vencida.",
        "Falta instalar y licenciar el paquete estadístico y herramientas académicas antes del taller.",
    ],
}

COLOQUIAL_NOISE = [
    "La falla se presentó durante la jornada de hoy.",
    "Ya intentamos reiniciar una vez sin éxito.",
    "Agradezco orientación o soporte técnico del área encargada.",
    "Varios compañeros del área reportan el mismo comportamiento.",
    "Quedo atento a la confirmación técnica en la mesa de servicios.",
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
