"""Datos demo KB parte B: Plataformas académicas e Impresión."""

from __future__ import annotations

from typing import Any, Dict, List

KB_DATA_B: List[Dict[str, Any]] = [
    {
        "code": "KB-001",
        "title": "[DEMO] Restablecimiento de contraseña en el Vortal Académico UPC",
        "service_name": "Plataformas Académicas (Aula Web / Vortal)",
        "category_topic": "Plataformas académicas",
        "symptoms": "El estudiante o docente olvidó su clave del Vortal o el portal académico rechaza sus credenciales.",
        "probable_cause": "Clave vencida, bloqueo por intentos múltiples o error de digitación del documento.",
        "solution_steps": (
            "1. Ingrese al portal Vortal institucional ([CONFIRMAR] URL oficial Vortal UPC) y seleccione recuperación de acceso.\n"
            "2. Digite su número de documento y dirección alterna o institucional registrada [CONFIRMAR].\n"
            "3. Revise la carpeta de correo no deseado para abrir el enlace de recuperación y defina nueva contraseña."
        ),
        "escalation_criteria": "Escalar a Sistemas de Información si no llega el mensaje de recuperación o el documento figura inactivo.",
        "keywords": "vortal contraseña clave recuperar acceso matricula notas",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico2@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-005",
        "title": "[DEMO] Cursos no visibles o error de sincronización en Aula Web UPC",
        "service_name": "Plataformas Académicas (Aula Web / Vortal)",
        "category_topic": "Plataformas académicas",
        "symptoms": "El estudiante matriculó materias en Vortal pero aún no aparecen en la plataforma Aula Web.",
        "probable_cause": "Ventana de sincronización automática entre matrícula académica y LMS o caché del navegador.",
        "solution_steps": (
            "1. Confirme que su matrícula financiera y académica figure activa en Vortal [CONFIRMAR].\n"
            "2. Espere el ciclo de sincronización programado hacia Aula Web [CONFIRMAR periodicidad exacta].\n"
            "3. Limpie caché del navegador o pruebe en ventana privada antes de reportar falla."
        ),
        "escalation_criteria": "Escalar a Sistemas de Información adjuntando horario de matrícula si persiste después de 24 horas [CONFIRMAR].",
        "keywords": "aula web moodle cursos virtuales matricula asignaturas sincronizacion",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico2@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-018",
        "title": "[DEMO] Error 500 o cierre inesperado de sesión al digitar notas parciales en Vortal",
        "service_name": "Plataformas Académicas (Aula Web / Vortal)",
        "category_topic": "Plataformas académicas",
        "symptoms": "Docente ingresa notas y al presionar Guardar aparece error 500 o sesión expirada.",
        "probable_cause": "Tiempo de sesión expirado mientras se cargaban registros o pico de concurrencia en cierre de corte [CONFIRMAR].",
        "solution_steps": (
            "1. Exporte previamente un respaldo temporal de sus calificaciones en hoja local antes de cargar lotes extensos.\n"
            "2. Guarde cada 5 o 10 estudiantes para evitar vencimiento de sesión de inactividad [CONFIRMAR].\n"
            "3. Si el error 500 se repite en un grupo específico, tome captura con fecha y hora exacta y código de grupo."
        ),
        "escalation_criteria": "Escalar como prioridad Alta a Sistemas de Información cuando ocurra durante fechas oficiales de cierre de notas.",
        "keywords": "error 500 notas vortal docente guardar sesion expirada corte",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico2@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-019",
        "title": "[DEMO] Error al subir archivos o tareas en Aula Web por tamaño o formato",
        "service_name": "Plataformas Académicas (Aula Web / Vortal)",
        "category_topic": "Plataformas académicas",
        "symptoms": "La plataforma LMS rechaza la entrega del estudiante o la barra de carga se detiene.",
        "probable_cause": "Archivo supera el límite máximo configurado en la actividad docente o extensión no permitida.",
        "solution_steps": (
            "1. Verifique en la actividad el peso máximo permitido y los formatos aceptados (ej. PDF) [CONFIRMAR].\n"
            "2. Comprima imágenes internas si el PDF excede el tamaño límite antes de subirlo.\n"
            "3. Evite caracteres especiales (#, %, &) en el nombre del archivo."
        ),
        "escalation_criteria": "Escalar al docente o Sistemas de Información si falla con archivos pequeños en varios navegadores.",
        "keywords": "subir archivo tarea aula web limite formato pdf entrega moodle",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico2@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-020",
        "title": "[DEMO] Descarga de volantes de pago y certificados académicos sin visualización PDF",
        "service_name": "Plataformas Académicas (Aula Web / Vortal)",
        "category_topic": "Plataformas académicas",
        "symptoms": "Al pulsar Generar Volante o Certificado en Vortal no se abre la pestaña emergente del PDF.",
        "probable_cause": "Bloqueador de ventanas emergentes (pop-ups) activo en el navegador o sesión con caché antigua.",
        "solution_steps": (
            "1. Habilite ventanas emergentes específicamente para el dominio institucional del Vortal [CONFIRMAR].\n"
            "2. Desactive temporalmente bloqueadores de scripts en el navegador para el dominio académico.\n"
            "3. Descargue el documento e imprímalo con visor PDF actualizado."
        ),
        "escalation_criteria": "Escalar a Sistemas de Información si el portal arroja mensaje de inconsistencia financiera o de registro.",
        "keywords": "volante pago certificado pdf popup ventanas emergentes vortal",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico2@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-007",
        "title": "[DEMO] Solución a atascos y cola de impresión detenida en impresoras de red",
        "service_name": "Equipos de Cómputo e Impresoras",
        "category_topic": "Impresión",
        "symptoms": "La impresora administrativa muestra documento atascado en cola o luz naranja de error.",
        "probable_cause": "Hoja atascada en rodillos/fusor o trabajo corrupto bloqueando el servicio Spooler.",
        "solution_steps": (
            "1. Abra la compuerta señalada en el panel y retire la hoja suavemente en dirección del recorrido sin rasgarla.\n"
            "2. En Windows abra 'Impresoras y escáneres' > Abrir cola > Cancelar todos los documentos.\n"
            "3. Reinicie la impresora esperando 15 segundos antes de volver a encender."
        ),
        "escalation_criteria": "Escalar a Soporte en Campo si persiste luz de error sin papel visible o hay atascos continuos por rodillos desgastados.",
        "keywords": "impresora imprimir atasco toner cola impresion escaner spooler",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico6@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-021",
        "title": "[DEMO] Impresora institucional aparece 'Sin conexión' en equipo de oficina",
        "service_name": "Equipos de Cómputo e Impresoras",
        "category_topic": "Impresión",
        "symptoms": "Los documentos quedan en espera indicando que la impresora de red está desconectada.",
        "probable_cause": "Cable de red o USB desconectado, cambio de IP en impresora sin reserva o modo ahorro profundo [CONFIRMAR].",
        "solution_steps": (
            "1. Verifique en la pantalla del equipo que la impresora esté encendida y con dirección IP de red válida.\n"
            "2. Confirme que el cable Ethernet trasero tenga luz de enlace activa.\n"
            "3. En la cola de Windows desactive la casilla 'Usar impresora sin conexión' si aparece marcada."
        ),
        "escalation_criteria": "Escalar a Soporte en Campo para reconfigurar puerto TCP/IP estándar o reemplazar patch cord.",
        "keywords": "impresora sin conexion offline ip red oficina windows",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico6@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-022",
        "title": "[DEMO] Solicitud de cambio de tóner, fusor o escáner con rayas en hojas",
        "service_name": "Equipos de Cómputo e Impresoras",
        "category_topic": "Impresión",
        "symptoms": "Las impresiones salen pálidas, con franjas negras verticales o mensaje de reemplazo de consumible.",
        "probable_cause": "Agotamiento de cartucho de tóner/tambor de imagen o suciedad en el cristal del escáner.",
        "solution_steps": (
            "1. Anote el modelo exacto de la impresora y código de inventario institucional visible en la etiqueta.\n"
            "2. Limpie suavemente el cristal del alimentador automático (ADF) con paño seco sin pelusa si las rayas ocurren al copiar.\n"
            "3. Radique solicitud indicando dependencia, edificio y porcentaje de tóner mostrado en panel."
        ),
        "escalation_criteria": "Escalar a Soporte en Campo para entrega e instalación controlada de consumibles [CONFIRMAR procedimiento almacén].",
        "keywords": "toner consumible rayas escaneo palido tambor inventario impresora",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico6@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
    {
        "code": "KB-023",
        "title": "[DEMO] Digitalización hacia carpeta compartida o correo en multifuncional",
        "service_name": "Equipos de Cómputo e Impresoras",
        "category_topic": "Impresión",
        "symptoms": "Al escanear documentos desde la multifuncional aparece error de envío SMB o autenticación fallida.",
        "probable_cause": "Cambio de credenciales en cuenta de servicio, ruta compartida modificada o firewall bloqueando SMB.",
        "solution_steps": (
            "1. Confirme que el equipo receptor esté encendido dentro de la red institucional correspondiente [CONFIRMAR].\n"
            "2. Pruebe escanear por USB directo si requiere entrega inmediata mientras se verifica la ruta de red.\n"
            "3. Reporte el código de error mostrado en la pantalla del escáner multifuncional."
        ),
        "escalation_criteria": "Escalar a Soporte en Campo para actualizar perfil SMB/SMTP en el equipo multifuncional [CONFIRMAR].",
        "keywords": "escaner smb digitalizar carpeta red multifuncional error envio",
        "visibility": "Pública",
        "status": "Publicado",
        "author_email": "tecnico4@unicesar.edu.co",
        "reviewer_email": "coordinador@unicesar.edu.co",
    },
]
