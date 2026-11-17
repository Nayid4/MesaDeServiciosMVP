"""Datos demo KB parte C: Equipos de cómputo, Aulas/videoproyectores y Software base."""

from __future__ import annotations

from typing import Any, Dict, List

KB_DATA_C: List[Dict[str, Any]] = [
    {
        "code": "KB-009",
        "title": "[DEMO] Diagnóstico cuando un computador no enciende o no responde al botón",
        "service_name": "Equipos de Cómputo e Impresoras",
        "category_topic": "Equipos de cómputo",
        "symptoms": "La computadora de escritorio o portátil no enciende, no giran ventiladores ni iluminan LEDs.",
        "probable_cause": "Regulador o toma de corriente apagada, cable de poder suelto o falla en fuente/batería.",
        "solution_steps": (
            "1. Confirme que el regulador, UPS o toma de pared tenga energía probando otro dispositivo.\n"
            "2. Verifique que el cable de poder esté firme en la fuente de la torre o cargador del portátil.\n"
            "3. Si emite pitidos continuos o presenta olor eléctrico, desconecte de inmediato y radique incidencia con número de inventario."
        ),
        "escalation_criteria": "Escalar a Soporte en Campo cuando el toma tenga corriente pero la torre o portátil siga sin encender.",
        "keywords": "computador computadora pc portatil no enciende no prende fuente hardware",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico4@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-024",
        "title": "[DEMO] Computador con pantalla negra tras encender (torre con luces encendidas)",
        "service_name": "Equipos de Cómputo e Impresoras",
        "category_topic": "Equipos de cómputo",
        "symptoms": "El equipo enciende ventiladores y luces frontales pero el monitor permanece en pantalla negra.",
        "probable_cause": "Monitor apagado/desconectado, cable DisplayPort/HDMI/VGA flojo o fallo de memoria/video.",
        "solution_steps": (
            "1. Confirme que el LED del monitor esté encendido y que el cable de video esté firme en el puerto correcto de la torre.\n"
            "2. Presione la tecla de selección de entrada del monitor (Input/Source) para verificar HDMI/VGA/DP.\n"
            "3. En Windows con sesión bloqueada, presione Ctrl + Shift + Win + B para reiniciar el controlador gráfico."
        ),
        "escalation_criteria": "Escalar a Soporte en Campo para inspección física interna de módulos de memoria o tarjeta de video.",
        "keywords": "pantalla negra monitor no da video computador encendido hdmi vga",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico4@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-025",
        "title": "[DEMO] Equipo de cómputo con lentitud extrema o disco al 100 %",
        "service_name": "Equipos de Cómputo e Impresoras",
        "category_topic": "Equipos de cómputo",
        "symptoms": "El computador tarda varios minutos en abrir aplicaciones, se congela el cursor o el ventilador suena al máximo.",
        "probable_cause": "Actualizaciones de sistema en segundo plano, exceso de programas al inicio o disco duro mecánico saturado.",
        "solution_steps": (
            "1. Guarde su trabajo y reinicie (no solo suspender) el equipo para aplicar actualizaciones pendientes.\n"
            "2. Presione Ctrl + Shift + Esc para abrir el Administrador de tareas y revise si hay procesos duplicados consumiendo CPU/RAM.\n"
            "3. Libere espacio en disco eliminando temporales de la papelera; evite usar al menos por encima del 90 % de capacidad."
        ),
        "escalation_criteria": "Escalar a Soporte en Campo para mantenimiento preventivo, limpieza térmica o evaluación de actualización de SSD/RAM [CONFIRMAR].",
        "keywords": "lentitud lento congelado disco 100 ram cpu rendimiento equipo",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico6@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-026",
        "title": "[DEMO] Fallas en teclado, mouse o puertos USB en estaciones de laboratorio",
        "service_name": "Equipos de Cómputo e Impresoras",
        "category_topic": "Equipos de cómputo",
        "symptoms": "El teclado no escribe caracteres o el ratón óptico no mueve el puntero en el escritorio.",
        "probable_cause": "Desconexión accidental de puertos traseros o deshabilitación temporal de controlador HID.",
        "solution_steps": (
            "1. Revise que el cable USB esté conectado firmemente; pruebe cambiar a otro puerto USB trasero disponible.\n"
            "2. En portátiles verifique que el panel táctil (touchpad) no esté bloqueado con tecla Fn + icono correspondiente.\n"
            "3. Si el periférico presenta cable partido o teclas dañadas, reporte el número de equipo en el laboratorio."
        ),
        "escalation_criteria": "Escalar a Soporte en Campo para sustitución de periférico con cargo al inventario del aula [CONFIRMAR].",
        "keywords": "teclado mouse usb puerto no funciona laboratorio periferico",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico4@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-027",
        "title": "[DEMO] Guía interna técnica: protocolo de diagnóstico de hardware en campo y trazabilidad",
        "service_name": "Equipos de Cómputo e Impresoras",
        "category_topic": "Equipos de cómputo",
        "symptoms": "Recepción de equipo administrativo o de laboratorio por falla recurrente de placa, disco o fuente.",
        "probable_cause": "Desgaste de componentes, picos eléctricos o sobrecalentamiento por polvo acumulado.",
        "solution_steps": (
            "1. Registre placa o serial institucional del equipo y estado físico previo antes de intervenir [CONFIRMAR].\n"
            "2. Ejecute pruebas de fuente, memoria y estado SMART de unidad de almacenamiento con herramientas autorizadas.\n"
            "3. Documente diagnóstico y categoría de cierre exacta antes de mover el equipo al taller."
        ),
        "escalation_criteria": "Escalar a Coordinación de Mesa cuando requiera repuesto o trámite de garantía con proveedor.",
        "keywords": "interno diagnostico hardware smart inventario garantia mantenimiento",
        "visibility": "Interna",
        "status": "Publicado",
        "author_email": "tecnico4@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-004",
        "title": "[DEMO] Videoproyector del aula muestra 'Sin Señal' por cable HDMI",
        "service_name": "Aulas Inteligentes y Videoproyectores",
        "category_topic": "Aulas y videoproyectores",
        "symptoms": "El docente conecta el portátil por HDMI al módulo del aula inteligente pero el proyector indica 'Sin Señal'.",
        "probable_cause": "Fuente de entrada HDMI incorrecta en el proyector, modo de proyección 'Solo pantalla PC' o cable flojo.",
        "solution_steps": (
            "1. Verifique que el cable HDMI esté firme en el portátil y en el módulo de pared/mesa del salón.\n"
            "2. Presione Windows + P (o Cmd + F1 en Mac) y seleccione 'Duplicar'.\n"
            "3. Con el control o panel del proyector pulse 'Source / Input' hasta elegir HDMI1 o HDMI2."
        ),
        "escalation_criteria": "Escalar con urgencia Alta a Soporte en Campo si la clase está en curso y continúa 'Sin Señal'.",
        "keywords": "videoproyector proyector hdmi sin señal aula inteligente pantalla salon",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico4@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-028",
        "title": "[DEMO] Conexión de portátil antiguo o adaptador por puerto VGA en videoproyector",
        "service_name": "Aulas Inteligentes y Videoproyectores",
        "category_topic": "Aulas y videoproyectores",
        "symptoms": "Imagen morada/amarillenta por VGA o ausencia total de señal al usar adaptador USB-C/HDMI a VGA.",
        "probable_cause": "Pines doblados en conector VGA de 15 pines, tornillos sin ajustar o adaptador pasivo incompatible.",
        "solution_steps": (
            "1. Revise que los pines del cable VGA azul no estén doblados antes de insertarlo suavemente.\n"
            "2. Ajuste ligeramente los tornillos laterales y cambie la entrada del proyector a 'Computer / VGA'.\n"
            "3. Reduzca la resolución de salida del portátil a 1280x720 o 1024x768 si parpadea la imagen."
        ),
        "escalation_criteria": "Escalar a Soporte en Campo para cambio de cable VGA o suministro de adaptador activo [CONFIRMAR].",
        "keywords": "vga proyector adaptador usbc imagen morada resolucion aula",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico4@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-029",
        "title": "[DEMO] Sin sonido en parlantes del aula inteligente al reproducir por HDMI",
        "service_name": "Aulas Inteligentes y Videoproyectores",
        "category_topic": "Aulas y videoproyectores",
        "symptoms": "Se proyecta video correctamente pero el audio sigue saliendo únicamente por el portátil.",
        "probable_cause": "Dispositivo predeterminado de reproducción en el sistema operativo apuntando al altavoz interno y no al HDMI/cable de audio.",
        "solution_steps": (
            "1. Haga clic en el icono de volumen de la barra de tareas y elija la salida de audio HDMI o 'Realtek Audio' según el cableado del salón.\n"
            "2. Confirme que el amplificador o barra de sonido del aula esté encendido y no esté en silencio (Mute).\n"
            "3. Si el aula utiliza plug de 3.5 mm independiente, conéctelo en la salida de auriculares del portátil."
        ),
        "escalation_criteria": "Escalar a Soporte en Campo si el amplificador no enciende o produce zumbido eléctrico constante.",
        "keywords": "audio sonido parlantes aula inteligente hdmi amplificador clase",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico6@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-030",
        "title": "[DEMO] Alerta de lámpara roja parpadeante o filtro sucio en videoproyector",
        "service_name": "Aulas Inteligentes y Videoproyectores",
        "category_topic": "Aulas y videoproyectores",
        "symptoms": "El proyector se apaga a los pocos minutos de encendido y parpadea LED rojo 'LAMP' o 'TEMP'.",
        "probable_cause": "Fin de vida útil de la lámpara, obstrucción de filtro de aire o falla en ventilador interno.",
        "solution_steps": (
            "1. No desconecte el proyector de golpe mientras el ventilador de enfriamiento siga girando.\n"
            "2. Anote el bloque y número de salón y si el equipo enciende brevemente o muestra aviso de filtro.\n"
            "3. Radique incidencia para reemplazo de módulo de lámpara o limpieza técnica."
        ),
        "escalation_criteria": "Escalar de inmediato a Soporte en Campo; no intentar abrir la carcasa en el aula.",
        "keywords": "lampara temp led rojo proyector se apaga filtro mantenimiento",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico4@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-031",
        "title": "[DEMO] Calibración táctil de pantallas interactivas y pizarras digitales de aula",
        "service_name": "Aulas Inteligentes y Videoproyectores",
        "category_topic": "Aulas y videoproyectores",
        "symptoms": "El puntero táctil en el tablero digital no coincide con el lugar donde se toca la pantalla o no responde el lápiz.",
        "probable_cause": "Cable USB-Touch desconectado entre la pantalla y el PC del aula o descalibración tras cambio de resolución.",
        "solution_steps": (
            "1. Verifique que tanto el cable HDMI como el cable USB cuadrado (Touch) estén conectados al equipo del docente.\n"
            "2. Ejecute la utilidad de calibración de puntos desde el menú de configuración de la pantalla [CONFIRMAR].\n"
            "3. Reinicie el módulo táctil apagando desde el interruptor lateral por 10 segundos."
        ),
        "escalation_criteria": "Escalar a Soporte en Campo si la función táctil falla en todos los equipos conectados.",
        "keywords": "pantalla interactiva pizarra tactil calibracion usb touch aula",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico6@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-006",
        "title": "[DEMO] Solicitud e instalación de software académico (SPSS, MATLAB, AutoCAD)",
        "service_name": "Software y Licenciamiento",
        "category_topic": "Software y licencias",
        "symptoms": "Docente o estudiante requiere software especializado instalado o renovado en salas de cómputo.",
        "probable_cause": "Laboratorio pendiente de despliegue de imagen semestral o vencimiento de archivo de licencia.",
        "solution_steps": (
            "1. Valide con la coordinación de programa que el software esté cubierto por el licenciamiento vigente [CONFIRMAR].\n"
            "2. Cree una solicitud seleccionando 'Software y Licenciamiento', indicando sede, laboratorio y versión requerida.\n"
            "3. Para licencias en red flotante verifique conectividad dentro del campus institucional [CONFIRMAR]."
        ),
        "escalation_criteria": "Escalar a Mesa de Software con al menos 5 días hábiles de anticipación para despliegues masivos [CONFIRMAR].",
        "keywords": "software spss matlab autocad licencia instalacion programas salas",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico5@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
]
