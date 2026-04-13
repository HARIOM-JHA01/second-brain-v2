// Shared i18n (ES/EN) — included by all user-facing pages
// Default language: 'es' (Spanish)
(function () {
  const STORAGE_KEY = "sb-lang";

  const translations = {
    /* ─── SPANISH ─────────────────────────────────────── */
    es: {
      // Brand
      "brand.by": "por",

      // Common
      "common.loading": "Cargando…",
      "common.error": "Ocurrió un error. Por favor intenta de nuevo.",
      "common.active": "Activo",
      "common.inactive": "Inactivo",

      // Auth — shared
      "auth.back": "← Volver al inicio",
      "auth.swap.title": "Alternar entre Registro e Inicio de sesión",

      // Auth — sign-up form
      "auth.signup.page_title": "Registro — Second Brain",
      "auth.signup.heading": "Crea tu cuenta",
      "auth.signup.subtitle": "Todos los campos son obligatorios",
      "auth.signup.section.details": "Tus datos",
      "auth.signup.fullname": "Nombre completo",
      "auth.signup.fullname.ph": "María García",
      "auth.signup.jobtitle": "Cargo",
      "auth.signup.jobtitle.ph": "CEO",
      "auth.signup.email": "Correo electrónico",
      "auth.signup.email.ph": "tu@empresa.com",
      "auth.signup.whatsapp": "WhatsApp",
      "auth.signup.whatsapp.ph": "+1234567890",
      "auth.signup.section.org": "Organización",
      "auth.signup.org": "Nombre de la organización",
      "auth.signup.org.ph": "Acme S.A.",
      "auth.signup.section.security": "Seguridad",
      "auth.signup.password": "Contraseña",
      "auth.signup.password.ph": "Mín. 6 caracteres",
      "auth.signup.btn": "Crear cuenta",
      "auth.signup.btn.loading": "Creando cuenta…",
      "auth.signup.switch": "¿Ya tienes una cuenta?",
      "auth.signup.switch.link": "Inicia sesión →",

      // Auth — sign-in form
      "auth.login.page_title": "Iniciar sesión — Second Brain",
      "auth.login.heading": "Bienvenido de vuelta",
      "auth.login.subtitle": "Inicia sesión en tu espacio de trabajo",
      "auth.login.email": "Correo electrónico",
      "auth.login.email.ph": "tu@empresa.com",
      "auth.login.password": "Contraseña",
      "auth.login.password.ph": "••••••••",
      "auth.login.btn": "Iniciar sesión",
      "auth.login.btn.loading": "Iniciando sesión…",
      "auth.login.switch": "¿No tienes una cuenta?",
      "auth.login.switch.link": "Crear una →",
      "auth.login.error.invalid": "Credenciales incorrectas",
      "auth.login.error.conn": "Error de conexión. Por favor intenta de nuevo.",

      // Auth — image overlay quotes
      "auth.quote.signup":
        '"El conocimiento de tu empresa,<br/><em>siempre al alcance.</em>"',
      "auth.quote.login":
        '"Las decisiones son tan buenas<br/><em>como el conocimiento detrás de ellas.</em>"',

      // Navbar (base.html)
      "nav.by": "por",
      "nav.logout": "Cerrar sesión",
      "nav.login": "Iniciar sesión",
      "nav.signup": "Registrarse",

      // Sidebar
      "sidebar.main": "Principal",
      "sidebar.dashboard": "Panel",
      "sidebar.manage": "Gestionar",
      "sidebar.users": "Usuarios",
      "sidebar.documents": "Documentos",
      "sidebar.kb_chat": "KB Chat",
      "sidebar.scenarios": "Escenarios",
      "sidebar.config": "Config",
      "sidebar.settings": "Configuración",

      // Dashboard — static
      "dash.title": "Panel",
      "dash.loading": "Cargando tu espacio de trabajo…",
      "dash.add_user": "+ Agregar usuario",
      "dash.pill.users": "Usuarios",
      "dash.pill.active": "Activos",
      "dash.pill.messages": "Mensajes (7d)",
      "dash.pill.docs": "Docs en KB",
      "dash.pill.avg_resp": "Resp. promedio",
      "dash.chart.msg_activity": "Actividad de mensajes",
      "dash.chart.msg_per_day": "Mensajes por día en tu organización",
      "dash.chart.team_status": "Estado del equipo",
      "dash.chart.active_vs": "Activos vs Inactivos",
      "dash.lbl.active": "Activos",
      "dash.lbl.inactive": "Inactivos",
      "dash.chart.team_growth": "Crecimiento del equipo",
      "dash.chart.new_members": "Nuevos miembros por día (30d)",
      "dash.lbl.new_week": "nuevos esta semana",
      "dash.chart.msg_breakdown": "Desglose de mensajes",
      "dash.chart.by_type": "Por tipo, últimos 30 días",
      "dash.lbl.text": "Texto",
      "dash.lbl.audio": "Audio",
      "dash.lbl.images": "Imágenes",
      "dash.lbl.docs": "Docs",
      "dash.insights.title": "💬 Perspectivas de conversación",
      "dash.insights.meta_default": "Últimos 7 días · Generado por IA",
      "dash.insights.meta_updated": "Últimos 7 días · IA · Actualizado {ago} · {count} mensajes analizados",
      "dash.insights.just_now": "ahora mismo",
      "dash.insights.min_ago": "m atrás",
      "dash.insights.refresh": "↻ Actualizar",
      "dash.insights.empty": "Sin mensajes esta semana. Los análisis aparecerán una vez que los usuarios empiecen a chatear por WhatsApp.",
      "dash.insights.top5": "Top 5 Mensajes",
      "dash.insights.error": "No se pudieron cargar los análisis",
      "dash.team_members": "Miembros del equipo",
      "dash.view_all": "Ver todos →",
      "dash.col.name": "Nombre",
      "dash.col.whatsapp": "WhatsApp",
      "dash.col.jobtitle": "Cargo",
      "dash.col.role": "Rol",
      "dash.col.status": "Estado",
      "dash.col.joined": "Se unió",
      "dash.modal.add_title": "Agregar miembro",
      "dash.modal.fullname": "Nombre completo",
      "dash.modal.jobtitle": "Cargo",
      "dash.modal.jobtitle.ph": "Ingeniero",
      "dash.modal.whatsapp": "Número de WhatsApp",
      "dash.modal.role": "Rol",
      "dash.modal.role.ph": "Selecciona un rol…",
      "dash.modal.btn": "Agregar usuario",
      "dash.empty": "Aún no hay miembros. Agrega uno arriba.",
      "dash.error.add_user": "Error al agregar usuario",
      "dash.range.custom": "Personalizado",
      "dash.range.apply": "Aplicar",

      // Documents
      "docs.title": "Base de conocimiento",
      "docs.subtitle": "Documentos subidos por tu equipo vía WhatsApp",
      "docs.search.ph": "Buscar documentos…",
      "docs.filter.all": "Todos los tipos",
      "docs.filter.pdf": "PDF",
      "docs.filter.images": "Imágenes",
      "docs.filter.word": "Word",
      "docs.filter.excel": "Excel",
      "docs.filter.ppt": "PowerPoint",
      "docs.filter.other": "Otro",
      "docs.view.grid": "Vista de cuadrícula",
      "docs.view.list": "Vista de lista",
      "docs.col.file": "Archivo",
      "docs.col.type": "Tipo",
      "docs.col.size": "Tamaño",
      "docs.col.uploaded": "Subido",
      "docs.col.actions": "Acciones",
      "docs.btn.view": "Ver",
      "docs.btn.delete": "Eliminar",
      "docs.no_url": "Sin URL",
      "docs.empty":
        "No se encontraron documentos. Sube archivos vía WhatsApp para construir tu base de conocimiento.",
      "docs.empty.list": "No se encontraron documentos",
      "docs.error.load": "No se pudieron cargar los documentos.",
      "docs.confirm.delete":
        '¿Eliminar "{name}"? Esto lo elimina de Cloudinary y la base de conocimiento.',
      "docs.error.no_ref":
        "Este documento no tiene referencia de Cloudinary y no puede eliminarse desde aquí.",
      "docs.error.delete": "Error al eliminar: ",
      "docs.tab_datastore": "Almacén de Datos",
      "docs.tab_kb": "Base de Conocimiento",
      "docs.upload_btn": "↑ Subir archivo",
      "docs.move_to_kb": "→ Mover a KB",
      "docs.move_to_ds": "← Mover al Almacén",
      "docs.source_whatsapp": "WhatsApp",
      "docs.source_web": "Web",
      "docs.empty_ds":
        "Sin archivos. Los archivos de WhatsApp aparecerán aquí.",
      "docs.empty_kb":
        "Sin archivos indexados. Mueve archivos desde el Almacén.",
      "docs.promoting": "Indexando…",
      "docs.demoting": "Desindexando…",
      "chat.title": "Chat con KB",
      "chat.placeholder": "Pregunta sobre tu Knowledge Base…",
      "chat.send": "Enviar",
      "chat.sources": "Fuentes",
      "chat.empty": "Haz una pregunta para comenzar.",

      // Settings
      "settings.title": "Configuración",
      "settings.account.title": "Cuenta",
      "settings.account.email": "Correo electrónico",
      "settings.account.member_since": "Miembro desde",
      "settings.account.error": "No se pudo cargar la cuenta",
      "settings.roles.title": "Roles y permisos",
      "settings.roles.add": "+ Agregar rol",
      "settings.roles.loading": "Cargando…",
      "settings.roles.error": "No se pudieron cargar los roles",
      "settings.roles.empty": "Aún no hay roles",
      "settings.modal.title": "Nuevo rol",
      "settings.modal.name_label": "Nombre del rol",
      "settings.modal.name_ph": "ej. Analista",
      "settings.modal.perms_label": "Permisos",
      "settings.modal.create_btn": "Crear rol",
      "settings.btn.save": "Guardar",
      "settings.btn.delete": "Eliminar",
      "settings.msg.saved": "¡Guardado!",
      "settings.msg.error": "Error al guardar",
      "settings.delete.confirm":
        '¿Eliminar el rol "{name}"? Esta acción no se puede deshacer.',
      "settings.delete.error": "Error al eliminar el rol",
      "settings.create.error": "Error: ",

      // Permission descriptions
      "perm.query:financial":
        "Puede consultar al AI sobre datos financieros — ingresos, presupuestos, pronósticos e informes de costos.",
      "perm.query:strategic":
        "Puede consultar documentos estratégicos — hojas de ruta, análisis competitivo y planes confidenciales.",
      "perm.query:sensitive":
        "Puede acceder a información restringida como registros de RRHH, documentos legales o investigaciones internas.",
      "perm.document:read":
        "Puede navegar y ver documentos almacenados en la base de conocimiento de la organización.",
      "perm.document:upload":
        "Puede subir nuevos archivos a la base de conocimiento vía WhatsApp o el panel.",
      "perm.user:manage":
        "Puede agregar, editar, desactivar y asignar roles a miembros del equipo en la organización.",

      // Users
      "users.title": "Usuarios",
      "users.add_btn": "+ Agregar usuario",
      "users.col.name": "Nombre",
      "users.col.email": "Correo",
      "users.col.whatsapp": "WhatsApp",
      "users.col.jobtitle": "Cargo",
      "users.col.role": "Rol",
      "users.col.status": "Estado",
      "users.col.actions": "Acciones",
      "users.loading": "Cargando…",
      "users.empty": "No se encontraron usuarios",
      "users.modal.add_title": "Agregar usuario",
      "users.modal.edit_title": "Editar usuario",
      "users.modal.fullname": "Nombre completo",
      "users.modal.fullname.ph": "María García",
      "users.modal.jobtitle": "Cargo",
      "users.modal.jobtitle.ph": "Ingeniero",
      "users.modal.whatsapp": "Número de WhatsApp",
      "users.modal.role": "Rol",
      "users.modal.role.ph": "Selecciona un rol",
      "users.modal.add_btn": "Agregar usuario",
      "users.modal.save_btn": "Guardar cambios",
      "users.modal.delete_title": "Eliminar usuario",
      "users.modal.delete_body": "¿Eliminar este usuario de forma permanente?",
      "users.modal.delete_cancel": "Cancelar",
      "users.modal.delete_confirm": "Eliminar",
      "users.btn.edit": "Editar",
      "users.btn.revoke": "Revocar",
      "users.btn.reactivate": "Reactivar",
      "users.btn.delete": "Eliminar",
      "users.confirm.revoke": "¿Revocar acceso para este usuario?",
      "users.confirm.delete": "¿Eliminar este usuario de forma permanente?",
      "users.error.add": "Error al agregar usuario",
      "users.error.delete": "Error al eliminar usuario",

      // Scenarios
      "scenarios.title": "Escenarios de Coaching",
      "scenarios.col.name": "Nombre",
      "scenarios.col.description": "Descripción",
      "scenarios.col.status": "Estado",
      "scenarios.col.sessions": "Sesiones",
      "scenarios.col.created": "Creado",
      "scenarios.col.actions": "Acciones",
      "scenarios.empty": "No hay escenarios asignados a tu organización.",
      "scenarios.start_btn": "Iniciar",
      "scenarios.modal.start_title": "Cómo iniciar este escenario",
      "scenarios.modal.start_step1": "1. Abre WhatsApp",
      "scenarios.modal.start_step2": "2. Escribe a tu número de bot",
      "scenarios.modal.start_step3": '3. Envía "hola" y selecciona la opción 3',
      "scenarios.modal.start_step4": '4. Elige "{name}" de la lista',
      "scenarios.modal.start_close": "Cerrar",

      // Landing page (index.html)
      "lp.nav.features": "Características",
      "lp.nav.how": "Cómo funciona",
      "lp.nav.flow": "Flujo del proceso",
      "lp.nav.usecases": "Casos de uso",
      "lp.nav.start": "Comenzar",
      "lp.hero.badge": "Con IA · Creado por Rolplay",
      "lp.hero.h1":
        'El conocimiento de tu empresa,<br/><span class="grad-text">en WhatsApp.</span>',
      "lp.hero.sub":
        "Second Brain es un asistente de IA que vive en WhatsApp. Sube tus documentos, haz preguntas en lenguaje natural y obtén respuestas instantáneas — para todo tu equipo.",
      "lp.hero.cta.start": "Empieza gratis →",
      "lp.hero.cta.how": "Ver cómo funciona",
      "lp.hero.phone.status": "● En línea",
      "lp.hero.phone.bot1":
        "¡Hola! Soy tu Second Brain. Pregúntame cualquier cosa sobre los documentos de tu empresa.",
      "lp.hero.phone.user1": "¿Cuáles fueron nuestros ingresos del Q4?",
      "lp.hero.phone.bot2":
        "Según el informe Q4 que subiste: los ingresos fueron $2.4M, un 18% más que el año anterior. El margen bruto se mantuvo en 64%. Desglose completo en la diapositiva 7.",
      "lp.stat.1.val": "Última gen.",
      "lp.stat.1.lbl": "Modelo de IA",
      "lp.stat.2.val": "RAG",
      "lp.stat.2.lbl": "Búsqueda de docs",
      "lp.stat.3.val": "ES + EN",
      "lp.stat.3.lbl": "Bilingüe",
      "lp.stat.4.val": "Por roles",
      "lp.stat.4.lbl": "Control de acceso",
      "lp.feat.label": "Características",
      "lp.feat.title": "Todo lo que tu equipo necesita,<br/>en un chat.",
      "lp.feat.sub":
        "Sin nuevas apps que aprender. Si tu equipo usa WhatsApp, ya están listos.",
      "lp.feat.1.title": "Inteligencia de IA avanzada",
      "lp.feat.1.desc":
        "Impulsado por modelos de lenguaje de última generación. Comprende matices, contexto y consultas complejas en lenguaje natural.",
      "lp.feat.2.title": "Base de conocimiento documental",
      "lp.feat.2.desc":
        "Sube PDFs, documentos Word, PowerPoints, hojas de cálculo e imágenes directamente en WhatsApp. Se indexan y buscan de forma instantánea.",
      "lp.feat.3.title": "Búsqueda semántica (RAG)",
      "lp.feat.3.desc":
        "La Generación Aumentada por Recuperación encuentra el fragmento correcto en tus documentos y lo cita — para que siempre sepas de dónde viene la respuesta.",
      "lp.feat.4.title": "Gestión de equipo y roles",
      "lp.feat.4.desc":
        "Invita a miembros del equipo por número de WhatsApp. Asigna roles con permisos granulares para que cada persona vea solo lo que debe.",
      "lp.feat.5.title": "Permisos granulares",
      "lp.feat.5.desc":
        "Define quién puede consultar datos financieros, planes estratégicos o información sensible. Los roles se verifican al momento de la consulta.",
      "lp.feat.6.title": "Notas de voz y multimedia",
      "lp.feat.6.desc":
        "Envía una nota de voz y recibe una respuesta de texto. Comparte imágenes o documentos — el asistente los lee y procesa automáticamente.",
      "lp.feat.7.title": "Español e inglés",
      "lp.feat.7.desc":
        "El asistente detecta automáticamente el idioma de cada mensaje y responde en el mismo. Sin configuración necesaria.",
      "lp.feat.8.title": "Panel de administración",
      "lp.feat.8.desc":
        "Panel web para gestionar usuarios, subir documentos en masa, ver tu base de conocimiento y configurar ajustes desde cualquier navegador.",
      "lp.feat.9.title": "Siempre activo e instantáneo",
      "lp.feat.9.desc":
        "Sin tiempos de espera, sin citas. Tu equipo obtiene respuestas de inmediato, 24/7, desde cualquier dispositivo con WhatsApp.",
      "lp.how.label": "Cómo funciona",
      "lp.how.title": "Listo en minutos.",
      "lp.how.sub":
        "Sin integraciones, sin entrenamiento. Solo WhatsApp y tus documentos.",
      "lp.how.1.title": "Crea tu cuenta",
      "lp.how.1.desc":
        "Regístrate con tu correo, configura tu organización y agrega tu número de WhatsApp a tu perfil.",
      "lp.how.2.title": "Sube tus documentos",
      "lp.how.2.desc":
        "Envía archivos directamente al número de WhatsApp o sube en masa desde el panel. PDFs, documentos Word, hojas de cálculo — todos soportados.",
      "lp.how.3.title": "Invita a tu equipo",
      "lp.how.3.desc":
        "Agrega miembros por número de teléfono y asigna roles. Controla quién puede acceder a consultas financieras, estratégicas o sensibles.",
      "lp.how.4.title": "Pregunta lo que quieras",
      "lp.how.4.desc":
        "Tu equipo simplemente escribe al número en lenguaje natural — en inglés o español — y obtiene respuestas precisas y citadas al instante.",
      "lp.flow.label": "Arquitectura",
      "lp.flow.title": "Un paso por mensaje.",
      "lp.flow.sub":
        "Ve exactamente cómo Second Brain toma un mensaje de WhatsApp y devuelve una respuesta citada e inteligente en tiempo real.",
      "lp.flow.1.title": "Tu Equipo",
      "lp.flow.1.desc": "Hace una pregunta por WhatsApp, en cualquier momento",
      "lp.flow.2.title": "Pregunta Recibida",
      "lp.flow.2.desc": "Llega en tiempo real, en el momento en que se envía",
      "lp.flow.3.title": "Acceso Verificado",
      "lp.flow.3.desc":
        "Los permisos de rol se verifican antes de iniciar cualquier búsqueda",
      "lp.flow.4.title": "Docs Buscados",
      "lp.flow.4.desc":
        "La base de conocimiento se analiza solo para usuarios autorizados",
      "lp.flow.5.title": "Respuesta Creada",
      "lp.flow.5.desc": "Se genera una respuesta clara y citada en segundos",
      "lp.flow.6.title": "Respuesta Enviada",
      "lp.flow.6.desc": "La respuesta llega a WhatsApp, ciclo completo",
      "lp.flowm.1.title": "Tu Equipo Pregunta",
      "lp.flowm.1.desc":
        "Cualquier miembro del equipo envía una pregunta, nota de voz o archivo a Second Brain en WhatsApp — sin necesidad de una nueva app.",
      "lp.flowm.2.title": "Recepción Instantánea",
      "lp.flowm.2.desc":
        "La pregunta llega en tiempo real, en el momento en que se envía — sin demoras, sin colas.",
      "lp.flowm.3.title": "Acceso Verificado",
      "lp.flowm.3.desc":
        "Los permisos basados en roles se verifican de inmediato — si el usuario no está autorizado, la solicitud se detiene aquí, ahorrando tiempo y costo.",
      "lp.flowm.4.title": "Docs Buscados",
      "lp.flowm.4.desc":
        "Solo para usuarios autorizados — Second Brain escanea toda tu base de conocimiento para encontrar la información más relevante.",
      "lp.flowm.5.title": "Respuesta Creada",
      "lp.flowm.5.desc":
        "Se genera una respuesta en lenguaje claro en segundos, con fuentes citadas para que tu equipo sepa exactamente de dónde proviene.",
      "lp.flowm.6.title": "Respuesta Enviada",
      "lp.flowm.6.desc":
        "La respuesta llega directamente a WhatsApp — sin inicio de sesión, sin navegador, sin fricción. El ciclo está completo.",
      "lp.uc.label": "Casos de uso",
      "lp.uc.title": "Creado para equipos reales.",
      "lp.uc.sub":
        "Second Brain se adapta a cómo trabaja tu organización — no al revés.",
      "lp.uc.1.title": "Base de conocimiento interna",
      "lp.uc.1.desc":
        "SOPs, políticas de RRHH, documentos de incorporación. Los nuevos empleados obtienen respuestas al instante en lugar de molestar a un colega.",
      "lp.uc.2.title": "Equipos financieros",
      "lp.uc.2.desc":
        "Consulta informes, pronósticos y presupuestos en segundos. El acceso basado en roles mantiene los números sensibles alejados de usuarios no autorizados.",
      "lp.uc.3.title": "Ventas y marketing",
      "lp.uc.3.desc":
        "Especificaciones de producto, hojas de precios, tarjetas de batalla competitivas — tu equipo de ventas siempre tiene la respuesta correcta a mano.",
      "lp.uc.4.title": "Legal y cumplimiento",
      "lp.uc.4.desc":
        "Busca contratos, normativas y documentos de cumplimiento. Obtén extractos citados en lugar de leer cientos de páginas.",
      "lp.uc.5.title": "Operaciones",
      "lp.uc.5.desc":
        "Manuales técnicos, contactos de proveedores, resúmenes de proyectos. Los equipos de campo obtienen respuestas sin necesitar VPN ni portátil.",
      "lp.uc.6.title": "Formación y desarrollo",
      "lp.uc.6.desc":
        "Materiales de cursos y guías de formación accesibles vía WhatsApp. Los alumnos pueden autoevaluarse y obtener explicaciones bajo demanda.",
      "lp.uc.7.title": "Salud y clínicas",
      "lp.uc.7.desc":
        "Protocolos clínicos, referencias de medicamentos y formularios de ingreso de pacientes accesibles al personal al instante — sin tocar un escritorio.",
      "lp.uc.8.title": "Equipos de soporte al cliente",
      "lp.uc.8.desc":
        "FAQs de productos, políticas de devolución y guías de solución de problemas al alcance de los agentes. Resoluciones más rápidas, menos escalamientos.",
      "lp.sec.label": "Seguridad y permisos",
      "lp.sec.title": "Tus datos, tus reglas.",
      "lp.sec.sub":
        "Cada consulta es clasificada y verificada contra el rol del usuario antes de que el asistente responda. La información sensible permanece protegida — automáticamente.",
      "lp.sec.1.title": "Control de acceso basado en roles",
      "lp.sec.1.desc":
        "Define roles personalizados con indicadores de permisos específicos. Asigna uno o más roles por usuario.",
      "lp.sec.2.title": "Clasificación de consultas por IA",
      "lp.sec.2.desc":
        "Cada mensaje entrante se clasifica como financiero, estratégico o sensible antes de generar cualquier respuesta.",
      "lp.sec.3.title": "Denegación amigable",
      "lp.sec.3.desc":
        "Las consultas no autorizadas reciben una negativa clara y amigable — no un error. Los usuarios saben a quién contactar.",
      "lp.sec.4.title": "Verificación de identidad por WhatsApp",
      "lp.sec.4.desc":
        "Los usuarios son identificados por su número de WhatsApp verificado. Sin contraseñas que gestionar para los usuarios finales.",
      "lp.nav.privacy": "Privacidad",
      "lp.priv.label": "Privacidad de datos",
      "lp.priv.title": "Privacidad por defecto.",
      "lp.priv.sub":
        "Cada decisión técnica fue tomada pensando en la seguridad de tus datos. Sin sorpresas, sin compromisos.",
      "lp.priv.1.title": "Conversaciones que expiran en 10 minutos",
      "lp.priv.1.desc":
        "Las sesiones de chat se eliminan automáticamente tras 10 minutos de inactividad. Nunca acumulamos historial de conversaciones de tu equipo.",
      "lp.priv.2.title": "Máximo 12 mensajes en memoria",
      "lp.priv.2.desc":
        "El historial tiene un límite estricto de 12 intercambios por sesión. Nunca construimos perfiles de conversación a largo plazo de tus empleados.",
      "lp.priv.3.title": "Sin almacenamiento de mensajes en bruto",
      "lp.priv.3.desc":
        "Solo se conservan los documentos de tu base de conocimiento, accesibles únicamente por usuarios registrados de tu organización. Los archivos están cifrados de extremo a extremo — ni siquiera Rolplay puede acceder a su contenido.",
      "lp.priv.4.title": "Control de permisos por consulta",
      "lp.priv.4.desc":
        "Cada mensaje es clasificado por IA antes de acceder a cualquier documento. Los datos financieros, estratégicos y sensibles solo fluyen hacia roles autorizados.",
      "lp.priv.5.title": "Identidad verificada por WhatsApp",
      "lp.priv.5.desc":
        "Los usuarios son identificados por su número de WhatsApp verificado — sin contraseñas, sin cuentas que gestionar para los usuarios finales.",
      "lp.priv.6.title": "Infraestructura de grado empresarial",
      "lp.priv.6.desc":
        "Toda la infraestructura que sustenta Second Brain cumple con SOC 2 y está diseñada para entornos empresariales, con cifrado en reposo y en tránsito.",
      "lp.priv.trust.label":
        "Construido sobre infraestructura empresarial conforme con SOC 2",
      "lp.priv.trust.1": "Cifrado de extremo a extremo",
      "lp.priv.trust.2": "Conforme con SOC 2",
      "lp.priv.trust.3": "Cero retención de chats",
      "lp.priv.trust.4": "Acceso basado en roles",
      "lp.priv.trust.5": "Identidad verificada por WhatsApp",
      "lp.priv.quote":
        '"Tus conversaciones son efímeras — los mensajes expiran en 10 minutos y el historial está limitado a 12 intercambios. Los documentos que subes están cifrados de extremo a extremo y solo son accesibles para los usuarios registrados de tu organización. Ni siquiera Rolplay puede leer su contenido."',
      "lp.cta.h2":
        '¿Listo para darle a tu equipo un <span class="grad-text">segundo cerebro?</span>',
      "lp.cta.p":
        "Configura tu organización en minutos. Sin tarjeta de crédito. Tu equipo ya está en WhatsApp — este es el único paso que falta.",
      "lp.cta.btn": "Crear cuenta gratis →",
      "lp.footer.by": "un producto de",
      "lp.footer.copy": "© 2026 Rolplay. Todos los derechos reservados.",

      // ── Super Admin ────────────────────────────────────────
      "sadmin.console": "Consola SuperAdmin",
      "sadmin.badge": "Rolplay Admin",
      "sadmin.signout": "Cerrar sesión",
      "sadmin.platform_link": "← Plataforma",
      "sadmin.common.cancel": "Cancelar",
      "sadmin.common.delete": "Eliminar",
      "sadmin.common.deleting": "Eliminando…",
      "sadmin.common.loading": "Cargando…",
      "sadmin.common.actions": "Acciones",
      "sadmin.common.created": "Creado",
      "sadmin.common.status": "Estado",
      "sadmin.common.active": "Activo",
      "sadmin.common.inactive": "Inactivo",
      "sadmin.common.total": "total",
      "sadmin.common.view_all": "Ver todo →",
      "sadmin.common.delete_failed": "Error al eliminar",
      "sadmin.nav.overview": "Resumen",
      "sadmin.nav.dashboard": "Panel",
      "sadmin.nav.platform": "Plataforma",
      "sadmin.nav.orgs": "Organizaciones",
      "sadmin.nav.users": "Todos los usuarios",
      "sadmin.nav.scenarios": "Escenarios",
      "sadmin.login.console": "Super Admin Console",
      "sadmin.login.heading": "Acceso Super Admin",
      "sadmin.login.subtitle": "Solo uso interno de Rolplay",
      "sadmin.login.tier": "Nivel de privilegio máximo",
      "sadmin.login.warning": "Este portal otorga acceso sin restricciones a todas las organizaciones, usuarios y datos de la plataforma. El acceso no autorizado está prohibido.",
      "sadmin.login.email": "Correo del administrador",
      "sadmin.login.password": "Contraseña",
      "sadmin.login.btn": "Ingresar a Super Admin",
      "sadmin.login.btn.loading": "Autenticando…",
      "sadmin.login.back": "← Volver a la plataforma",
      "sadmin.login.security": "Todas las sesiones son registradas y monitoreadas",
      "sadmin.login.error.invalid": "Credenciales incorrectas",
      "sadmin.login.error.conn": "Error de conexión. Por favor intenta de nuevo.",
      "sadmin.dash.title": "Panel",
      "sadmin.dash.subtitle": "Salud de la plataforma en tiempo real y métricas de crecimiento",
      "sadmin.dash.period": "Período",
      "sadmin.dash.7d": "Últimos 7 días",
      "sadmin.dash.30d": "Últimos 30 días",
      "sadmin.dash.period_note_7": "Mostrando últimos 7 días",
      "sadmin.dash.period_note_30": "Mostrando últimos 30 días",
      "sadmin.dash.kpi.orgs": "Organizaciones",
      "sadmin.dash.kpi.new_orgs": "Nuevas orgs.",
      "sadmin.dash.kpi.new_users": "Nuevos usuarios",
      "sadmin.dash.kpi.active": "Usuarios activos",
      "sadmin.dash.kpi.messages": "Mensajes",
      "sadmin.dash.kpi.docs": "Documentos",
      "sadmin.dash.kpi.avg_resp": "Resp. promedio",
      "sadmin.dash.kpi.orgs_sub_period": "+{count} nuevas este período",
      "sadmin.dash.kpi.users_sub_signed": "+{count} registrados",
      "sadmin.dash.kpi.active_sub_pct": "{pct}% del total",
      "sadmin.dash.kpi.msg_sub_period": "mensajes en {days}d",
      "sadmin.dash.kpi.msg_label_period": "Mensajes ({days}d)",
      "sadmin.dash.kpi.docs_sub_uploaded": "+{count} subidos",
      "sadmin.dash.chart.messages": "Mensajes procesados",
      "sadmin.dash.chart.msg_sub": "Volumen diario",
      "sadmin.dash.chart.msg_sub_days": "Volumen diario — últimos {days} días",
      "sadmin.dash.chart.user_status": "Estado de usuarios",
      "sadmin.dash.chart.active_vs": "Activos vs inactivos",
      "sadmin.dash.lbl.active": "Activos",
      "sadmin.dash.lbl.inactive": "Inactivos",
      "sadmin.dash.lbl.total": "total",
      "sadmin.dash.chart.signups": "Nuevos registros",
      "sadmin.dash.chart.signup_sub": "Registros diarios",
      "sadmin.dash.chart.signup_sub_days": "Registros diarios — últimos {days} días",
      "sadmin.dash.chart.org_growth": "Crecimiento de orgs.",
      "sadmin.dash.chart.org_sub": "Nuevas orgs. y activación",
      "sadmin.dash.chart.org_sub_days": "Nuevas en últimos {days} días",
      "sadmin.dash.chart.org_new_label": "Nuevas ({days}d)",
      "sadmin.dash.chart.org_total_label": "Total",
      "sadmin.dash.chart.activation": "Tasa de activación",
      "sadmin.dash.chart.kb": "Base de conocimiento",
      "sadmin.dash.chart.kb_sub": "Estadísticas de uso e indexación",
      "sadmin.dash.chart.tip.messages": "{count} mensajes",
      "sadmin.dash.chart.tip.signups": "{count} registros",
      "sadmin.dash.kb.last_days": "Últimos {days} días",
      "sadmin.dash.table.no_orgs": "Aún no hay organizaciones",
      "sadmin.dash.load_failed": "Error al cargar",
      "sadmin.dash.metric.rag": "🔍 Consultas RAG",
      "sadmin.dash.metric.voice": "🎙️ Notas de voz",
      "sadmin.dash.metric.vectors": "📌 Vectores Pinecone",
      "sadmin.dash.metric.errors": "⚠️ Errores",
      "sadmin.dash.metric.roles": "🔑 Roles totales",
      "sadmin.dash.chart.top_orgs": "Principales organizaciones",
      "sadmin.dash.chart.top_orgs_sub": "Ordenadas por cantidad de usuarios",
      "sadmin.dash.col.org": "Organización",
      "sadmin.dash.col.owner": "Propietario",
      "sadmin.dash.col.users": "Usuarios",
      "sadmin.dash.col.active": "Activos",
      "sadmin.dash.col.docs": "Docs",
      "sadmin.dash.col.joined": "Registrado",
      "sadmin.orgs.title": "Organizaciones",
      "sadmin.orgs.subtitle": "Todas las organizaciones registradas en la plataforma",
      "sadmin.orgs.modal.delete_title": "⚠️ Eliminar organización",
      "sadmin.orgs.modal.delete_warning": "Estás a punto de eliminar permanentemente <strong>{name}</strong>. Esto eliminará todos sus usuarios, roles y documentos.",
      "sadmin.orgs.modal.delete_note": "Esta acción no se puede deshacer.",
      "sadmin.orgs.all": "Todas las organizaciones",
      "sadmin.orgs.search_ph": "Buscar por nombre o propietario…",
      "sadmin.orgs.sort.users_desc": "Más usuarios ↓",
      "sadmin.orgs.sort.users_asc": "Menos usuarios ↑",
      "sadmin.orgs.sort.date_desc": "Más recientes",
      "sadmin.orgs.sort.date_asc": "Más antiguos",
      "sadmin.orgs.sort.name_asc": "Nombre A→Z",
      "sadmin.orgs.col.org": "Organización",
      "sadmin.orgs.col.owner": "Correo del propietario",
      "sadmin.orgs.col.total": "Total de usuarios",
      "sadmin.orgs.col.active": "Activos",
      "sadmin.orgs.col.inactive": "Inactivos",
      "sadmin.orgs.col.docs": "Documentos",
      "sadmin.orgs.view_users": "Ver usuarios",
      "sadmin.orgs.empty": "No se encontraron organizaciones",
      "sadmin.users.title": "Todos los usuarios",
      "sadmin.users.subtitle": "Todos los usuarios de todas las organizaciones — gestiona accesos, contraseñas y más",
      "sadmin.users.modal.delete_title": "Eliminar usuario",
      "sadmin.users.modal.delete_warning": "Esto eliminará permanentemente al usuario y todos sus datos. Esta acción no se puede deshacer.",
      "sadmin.users.modal.delete_btn": "Eliminar usuario",
      "sadmin.users.modal.pw_title": "Cambiar contraseña",
      "sadmin.users.modal.pw_new": "Nueva contraseña",
      "sadmin.users.modal.pw_ph": "Mín. 6 caracteres",
      "sadmin.users.modal.pw_confirm": "Confirmar contraseña",
      "sadmin.users.modal.pw_confirm_ph": "Repetir contraseña",
      "sadmin.users.modal.pw_btn": "Establecer nueva contraseña",
      "sadmin.users.modal.pw_success": "✓ Contraseña actualizada correctamente.",
      "sadmin.users.sum.total": "Total de usuarios",
      "sadmin.users.sum.active": "Activos",
      "sadmin.users.sum.inactive": "Inactivos",
      "sadmin.users.sum.orgs": "Organizaciones",
      "sadmin.users.section": "Usuarios",
      "sadmin.users.search_ph": "Buscar nombre, correo, org., WhatsApp…",
      "sadmin.users.filter.all_orgs": "Todas las organizaciones",
      "sadmin.users.filter.all_statuses": "Todos los estados",
      "sadmin.users.col.user": "Usuario",
      "sadmin.users.col.whatsapp": "WhatsApp",
      "sadmin.users.col.jobtitle": "Cargo",
      "sadmin.users.col.org": "Organización",
      "sadmin.users.col.role": "Rol",
      "sadmin.users.col.joined": "Se unió",
      "sadmin.users.empty": "No se encontraron usuarios",
      "sadmin.scenarios.title": "Escenarios de coaching",
      "sadmin.scenarios.subtitle": "Gestiona escenarios de coaching en todas las organizaciones",
      "sadmin.scenarios.all": "Todos los escenarios",
      "sadmin.scenarios.new_btn": "+ Nuevo escenario",
      "sadmin.scenarios.search_ph": "Buscar por nombre u org.…",
      "sadmin.scenarios.all_orgs": "Todas las orgs.",
      "sadmin.scenarios.col.name": "Nombre",
      "sadmin.scenarios.col.org": "Organización",
      "sadmin.scenarios.col.desc": "Descripción",
      "sadmin.scenarios.col.prompt": "Instrucción del sistema",
      "sadmin.scenarios.col.file": "Archivo de referencia",
      "sadmin.scenarios.col.sessions": "Sesiones",
      "sadmin.scenarios.empty": "No se encontraron escenarios",
      "sadmin.scenarios.load_error": "Error al cargar escenarios",
      "sadmin.scenarios.modal.create_title": "Nuevo escenario",
      "sadmin.scenarios.modal.name": "Nombre *",
      "sadmin.scenarios.modal.name_ph": "Ej. Práctica de pitch de ventas",
      "sadmin.scenarios.modal.org": "Organización *",
      "sadmin.scenarios.modal.org_ph": "Selecciona una organización…",
      "sadmin.scenarios.modal.desc": "Descripción",
      "sadmin.scenarios.modal.desc_optional": "(opcional)",
      "sadmin.scenarios.modal.desc_ph": "Descripción breve del escenario",
      "sadmin.scenarios.modal.prompt": "Instrucción del sistema *",
      "sadmin.scenarios.modal.prompt_ph": "Eres un coach experto en ventas. El usuario practicará su pitch contigo...",
      "sadmin.scenarios.modal.file": "Archivo de referencia (opcional)",
      "sadmin.scenarios.modal.remove_file": "Eliminar archivo de referencia actual",
      "sadmin.scenarios.modal.active": "Activo",
      "sadmin.scenarios.modal.create_btn": "Crear escenario",
      "sadmin.scenarios.modal.edit_title": "Editar escenario",
      "sadmin.scenarios.modal.save_btn": "Guardar cambios",
    },

    /* ─── ENGLISH ──────────────────────────────────────── */
    en: {
      // Brand
      "brand.by": "by",

      // Common
      "common.loading": "Loading…",
      "common.error": "An error occurred. Please try again.",
      "common.active": "Active",
      "common.inactive": "Inactive",

      // Auth — shared
      "auth.back": "← Back to home",
      "auth.swap.title": "Switch between Sign Up and Sign In",

      // Auth — sign-up form
      "auth.signup.page_title": "Sign Up — Second Brain",
      "auth.signup.heading": "Create your account",
      "auth.signup.subtitle": "All fields are required to get started",
      "auth.signup.section.details": "Your details",
      "auth.signup.fullname": "Full Name",
      "auth.signup.fullname.ph": "Jane Smith",
      "auth.signup.jobtitle": "Job Title",
      "auth.signup.jobtitle.ph": "CEO",
      "auth.signup.email": "Email",
      "auth.signup.email.ph": "you@company.com",
      "auth.signup.whatsapp": "WhatsApp",
      "auth.signup.whatsapp.ph": "+1234567890",
      "auth.signup.section.org": "Organisation",
      "auth.signup.org": "Organisation Name",
      "auth.signup.org.ph": "Acme Inc.",
      "auth.signup.section.security": "Security",
      "auth.signup.password": "Password",
      "auth.signup.password.ph": "Min 6 characters",
      "auth.signup.btn": "Create Account",
      "auth.signup.btn.loading": "Creating account…",
      "auth.signup.switch": "Already have an account?",
      "auth.signup.switch.link": "Sign in →",

      // Auth — sign-in form
      "auth.login.page_title": "Sign In — Second Brain",
      "auth.login.heading": "Welcome back",
      "auth.login.subtitle": "Sign in to your workspace",
      "auth.login.email": "Email",
      "auth.login.email.ph": "you@company.com",
      "auth.login.password": "Password",
      "auth.login.password.ph": "••••••••",
      "auth.login.btn": "Sign In",
      "auth.login.btn.loading": "Signing in…",
      "auth.login.switch": "Don't have an account?",
      "auth.login.switch.link": "Create one →",
      "auth.login.error.invalid": "Invalid credentials",
      "auth.login.error.conn": "Connection error. Please try again.",

      // Auth — image overlay quotes
      "auth.quote.signup":
        '"Your company\'s knowledge,<br/><em>always within reach.</em>"',
      "auth.quote.login":
        '"Decisions are only as good<br/><em>as the knowledge behind them.</em>"',

      // Navbar (base.html)
      "nav.by": "by",
      "nav.logout": "Logout",
      "nav.login": "Login",
      "nav.signup": "Sign Up",

      // Sidebar
      "sidebar.main": "Main",
      "sidebar.dashboard": "Dashboard",
      "sidebar.manage": "Manage",
      "sidebar.users": "Users",
      "sidebar.documents": "Documents",
      "sidebar.kb_chat": "KB Chat",
      "sidebar.scenarios": "Scenarios",
      "sidebar.config": "Config",
      "sidebar.settings": "Settings",

      // Dashboard — static
      "dash.title": "Dashboard",
      "dash.loading": "Loading your workspace…",
      "dash.add_user": "+ Add User",
      "dash.pill.users": "Users",
      "dash.pill.active": "Active",
      "dash.pill.messages": "Messages (7d)",
      "dash.pill.docs": "Docs in KB",
      "dash.pill.avg_resp": "Avg Response",
      "dash.chart.msg_activity": "Message Activity",
      "dash.chart.msg_per_day": "Messages per day in your org",
      "dash.chart.team_status": "Team Status",
      "dash.chart.active_vs": "Active vs Inactive",
      "dash.lbl.active": "Active",
      "dash.lbl.inactive": "Inactive",
      "dash.chart.team_growth": "Team Growth",
      "dash.chart.new_members": "New members added per day (30d)",
      "dash.lbl.new_week": "new this week",
      "dash.chart.msg_breakdown": "Message Breakdown",
      "dash.chart.by_type": "By type, last 30 days",
      "dash.lbl.text": "Text",
      "dash.lbl.audio": "Audio",
      "dash.lbl.images": "Images",
      "dash.lbl.docs": "Docs",
      "dash.insights.title": "💬 Conversation Insights",
      "dash.insights.meta_default": "Last 7 days · AI generated",
      "dash.insights.meta_updated": "Last 7 days · AI generated · Updated {ago} · {count} messages analyzed",
      "dash.insights.just_now": "just now",
      "dash.insights.min_ago": "m ago",
      "dash.insights.refresh": "↻ Refresh",
      "dash.insights.empty": "No messages yet this week. Insights will appear once users start chatting on WhatsApp.",
      "dash.insights.top5": "Top 5 Messages",
      "dash.insights.error": "Could not load insights",
      "dash.team_members": "Team Members",
      "dash.view_all": "View all →",
      "dash.col.name": "Name",
      "dash.col.whatsapp": "WhatsApp",
      "dash.col.jobtitle": "Job Title",
      "dash.col.role": "Role",
      "dash.col.status": "Status",
      "dash.col.joined": "Joined",
      "dash.modal.add_title": "Add Team Member",
      "dash.modal.fullname": "Full Name",
      "dash.modal.jobtitle": "Job Title",
      "dash.modal.jobtitle.ph": "Engineer",
      "dash.modal.whatsapp": "WhatsApp Number",
      "dash.modal.role": "Role",
      "dash.modal.role.ph": "Select a role…",
      "dash.modal.btn": "Add User",
      "dash.empty": "No team members yet. Add one above.",
      "dash.error.add_user": "Error adding user",
      "dash.range.custom": "Custom",
      "dash.range.apply": "Apply",

      // Documents
      "docs.title": "Knowledge Base",
      "docs.subtitle": "Documents your team has uploaded via WhatsApp",
      "docs.search.ph": "Search documents…",
      "docs.filter.all": "All types",
      "docs.filter.pdf": "PDF",
      "docs.filter.images": "Images",
      "docs.filter.word": "Word",
      "docs.filter.excel": "Excel",
      "docs.filter.ppt": "PowerPoint",
      "docs.filter.other": "Other",
      "docs.view.grid": "Grid view",
      "docs.view.list": "List view",
      "docs.col.file": "File",
      "docs.col.type": "Type",
      "docs.col.size": "Size",
      "docs.col.uploaded": "Uploaded",
      "docs.col.actions": "Actions",
      "docs.btn.view": "View",
      "docs.btn.delete": "Delete",
      "docs.no_url": "No URL",
      "docs.empty":
        "No documents found. Upload files via WhatsApp to build your knowledge base.",
      "docs.empty.list": "No documents found",
      "docs.error.load": "Could not load documents.",
      "docs.confirm.delete":
        'Delete "{name}"? This removes it from Cloudinary and the knowledge base.',
      "docs.error.no_ref":
        "This document has no Cloudinary reference and cannot be deleted from here.",
      "docs.error.delete": "Delete failed: ",
      "docs.tab_datastore": "Data Store",
      "docs.tab_kb": "Knowledge Base",
      "docs.upload_btn": "↑ Upload file",
      "docs.move_to_kb": "→ Move to KB",
      "docs.move_to_ds": "← Move to Data Store",
      "docs.source_whatsapp": "WhatsApp",
      "docs.source_web": "Web",
      "docs.empty_ds": "No files yet. WhatsApp uploads appear here.",
      "docs.empty_kb": "No indexed files. Move files from Data Store.",
      "docs.promoting": "Indexing…",
      "docs.demoting": "Removing from KB…",
      "chat.title": "KB Chat",
      "chat.placeholder": "Ask about your Knowledge Base…",
      "chat.send": "Send",
      "chat.sources": "Sources",
      "chat.empty": "Ask a question to get started.",

      // Settings
      "settings.title": "Settings",
      "settings.account.title": "Account",
      "settings.account.email": "Email",
      "settings.account.member_since": "Member since",
      "settings.account.error": "Could not load account",
      "settings.roles.title": "Roles & Permissions",
      "settings.roles.add": "+ Add Role",
      "settings.roles.loading": "Loading…",
      "settings.roles.error": "Could not load roles",
      "settings.roles.empty": "No roles yet",
      "settings.modal.title": "New Role",
      "settings.modal.name_label": "Role Name",
      "settings.modal.name_ph": "e.g. Analyst",
      "settings.modal.perms_label": "Permissions",
      "settings.modal.create_btn": "Create Role",
      "settings.btn.save": "Save",
      "settings.btn.delete": "Delete",
      "settings.msg.saved": "Saved!",
      "settings.msg.error": "Error saving",
      "settings.delete.confirm": 'Delete role "{name}"? This cannot be undone.',
      "settings.delete.error": "Error deleting role",
      "settings.create.error": "Error: ",

      // Permission descriptions
      "perm.query:financial":
        "Can ask the AI about financial data — revenue, budgets, forecasts, and cost reports.",
      "perm.query:strategic":
        "Can query strategic documents — roadmaps, competitive analysis, and confidential plans.",
      "perm.query:sensitive":
        "Can access restricted information such as HR records, legal docs, or internal investigations.",
      "perm.document:read":
        "Can browse and view documents stored in the organization's knowledge base.",
      "perm.document:upload":
        "Can upload new files to the knowledge base via WhatsApp or the dashboard.",
      "perm.user:manage":
        "Can add, edit, deactivate, and assign roles to team members in the organization.",

      // Users
      "users.title": "Users",
      "users.add_btn": "+ Add User",
      "users.col.name": "Name",
      "users.col.email": "Email",
      "users.col.whatsapp": "WhatsApp",
      "users.col.jobtitle": "Job Title",
      "users.col.role": "Role",
      "users.col.status": "Status",
      "users.col.actions": "Actions",
      "users.loading": "Loading…",
      "users.empty": "No users found",
      "users.modal.add_title": "Add User",
      "users.modal.edit_title": "Edit User",
      "users.modal.fullname": "Full Name",
      "users.modal.fullname.ph": "Jane Smith",
      "users.modal.jobtitle": "Job Title",
      "users.modal.jobtitle.ph": "Engineer",
      "users.modal.whatsapp": "WhatsApp Number",
      "users.modal.role": "Role",
      "users.modal.role.ph": "Select a role",
      "users.modal.add_btn": "Add User",
      "users.modal.save_btn": "Save Changes",
      "users.modal.delete_title": "Delete User",
      "users.modal.delete_body": "Delete this user permanently?",
      "users.modal.delete_cancel": "Cancel",
      "users.modal.delete_confirm": "Delete",
      "users.btn.edit": "Edit",
      "users.btn.revoke": "Revoke",
      "users.btn.reactivate": "Reactivate",
      "users.btn.delete": "Delete",
      "users.confirm.revoke": "Revoke access for this user?",
      "users.confirm.delete": "Delete this user permanently?",
      "users.error.add": "Error adding user",
      "users.error.delete": "Error deleting user",

      // Scenarios
      "scenarios.title": "Coaching Scenarios",
      "scenarios.col.name": "Name",
      "scenarios.col.description": "Description",
      "scenarios.col.status": "Status",
      "scenarios.col.sessions": "Sessions",
      "scenarios.col.created": "Created",
      "scenarios.col.actions": "Actions",
      "scenarios.empty": "No scenarios assigned to your organization yet.",
      "scenarios.start_btn": "Start",
      "scenarios.modal.start_title": "How to start this scenario",
      "scenarios.modal.start_step1": "1. Open WhatsApp",
      "scenarios.modal.start_step2": "2. Message your bot number",
      "scenarios.modal.start_step3": '3. Send "hi" and select option 3',
      "scenarios.modal.start_step4": '4. Choose "{name}" from the list',
      "scenarios.modal.start_close": "Close",

      // Landing page (index.html)
      "lp.nav.features": "Features",
      "lp.nav.how": "How it works",
      "lp.nav.flow": "Process flow",
      "lp.nav.usecases": "Use cases",
      "lp.nav.start": "Get Started",
      "lp.hero.badge": "AI-powered · Built by Rolplay",
      "lp.hero.h1":
        'Your company\'s knowledge,<br/><span class="grad-text">on WhatsApp.</span>',
      "lp.hero.sub":
        "Second Brain is an AI assistant that lives in WhatsApp. Upload your documents, ask questions in plain language, and get instant answers — for your whole team.",
      "lp.hero.cta.start": "Start for free →",
      "lp.hero.cta.how": "See how it works",
      "lp.hero.phone.status": "● Online",
      "lp.hero.phone.bot1":
        "Hello! I'm your Second Brain. Ask me anything about your company documents.",
      "lp.hero.phone.user1": "What were our Q4 revenue figures?",
      "lp.hero.phone.bot2":
        "Based on the Q4 report you uploaded: revenue was $2.4M, up 18% YoY. Gross margin held at 64%. Full breakdown in slide 7.",
      "lp.stat.1.val": "State-of-art",
      "lp.stat.1.lbl": "AI model",
      "lp.stat.2.val": "RAG",
      "lp.stat.2.lbl": "Document search",
      "lp.stat.3.val": "ES + EN",
      "lp.stat.3.lbl": "Bilingual",
      "lp.stat.4.val": "Role-based",
      "lp.stat.4.lbl": "Access control",
      "lp.feat.label": "Features",
      "lp.feat.title": "Everything your team needs,<br/>in a chat.",
      "lp.feat.sub":
        "No new apps to learn. If your team uses WhatsApp, they're already ready.",
      "lp.feat.1.title": "Advanced AI intelligence",
      "lp.feat.1.desc":
        "Powered by state-of-the-art language models. Understands nuance, context, and complex queries in plain, natural language.",
      "lp.feat.2.title": "Document knowledge base",
      "lp.feat.2.desc":
        "Upload PDFs, Word docs, PowerPoints, spreadsheets, and images directly in WhatsApp. They're instantly indexed and searchable.",
      "lp.feat.3.title": "Semantic search (RAG)",
      "lp.feat.3.desc":
        "Retrieval-Augmented Generation finds the right passage in your documents and cites it — so you always know where the answer comes from.",
      "lp.feat.4.title": "Team & role management",
      "lp.feat.4.desc":
        "Invite team members by WhatsApp number. Assign roles with granular permissions so each person sees only what they should.",
      "lp.feat.5.title": "Granular permissions",
      "lp.feat.5.desc":
        "Define who can query financial data, strategic plans, or sensitive information. Roles are enforced at query time.",
      "lp.feat.6.title": "Voice notes & media",
      "lp.feat.6.desc":
        "Send a voice note and get a text reply. Share images or documents — the assistant reads and processes them automatically.",
      "lp.feat.7.title": "Spanish & English",
      "lp.feat.7.desc":
        "The assistant automatically detects the language of each message and responds in kind. No configuration needed.",
      "lp.feat.8.title": "Admin dashboard",
      "lp.feat.8.desc":
        "Web dashboard to manage users, upload documents in bulk, view your knowledge base, and configure settings from any browser.",
      "lp.feat.9.title": "Always-on & instant",
      "lp.feat.9.desc":
        "No wait times, no scheduling. Your team gets answers immediately, 24/7, from any device they have WhatsApp on.",
      "lp.how.label": "How it works",
      "lp.how.title": "Up and running in minutes.",
      "lp.how.sub":
        "No integrations, no training. Just WhatsApp and your documents.",
      "lp.how.1.title": "Create your account",
      "lp.how.1.desc":
        "Sign up with your email, set up your organization, and add your WhatsApp number to your profile.",
      "lp.how.2.title": "Upload your documents",
      "lp.how.2.desc":
        "Send files directly to the WhatsApp number or bulk-upload via the dashboard. PDFs, Word docs, spreadsheets — all supported.",
      "lp.how.3.title": "Invite your team",
      "lp.how.3.desc":
        "Add members by phone number and assign roles. Control who can access financial, strategic, or sensitive queries.",
      "lp.how.4.title": "Ask anything, anytime",
      "lp.how.4.desc":
        "Your team just messages the number in plain language — in English or Spanish — and gets accurate, cited answers instantly.",
      "lp.flow.label": "Architecture",
      "lp.flow.title": "Every message, every step.",
      "lp.flow.sub":
        "See exactly how Second Brain takes a WhatsApp message and returns a cited, intelligent answer in real-time.",
      "lp.flow.1.title": "Your Team",
      "lp.flow.1.desc": "Asks a question via WhatsApp, anytime",
      "lp.flow.2.title": "Question Received",
      "lp.flow.2.desc": "Arrives in real time, the moment it's sent",
      "lp.flow.3.title": "Access Verified",
      "lp.flow.3.desc": "Role permissions checked before any search begins",
      "lp.flow.4.title": "Docs Searched",
      "lp.flow.4.desc": "Knowledge base scanned only for authorised users",
      "lp.flow.5.title": "Answer Crafted",
      "lp.flow.5.desc": "A clear, sourced reply is generated in seconds",
      "lp.flow.6.title": "Reply Delivered",
      "lp.flow.6.desc": "Answer lands in WhatsApp, loop complete",
      "lp.flowm.1.title": "Your Team Asks",
      "lp.flowm.1.desc":
        "Anyone on the team sends a question, voice note, or file to Second Brain on WhatsApp — no new app needed.",
      "lp.flowm.2.title": "Instant Receipt",
      "lp.flowm.2.desc":
        "The question arrives in real time, the moment it's sent — no delays, no queues.",
      "lp.flowm.3.title": "Access Verified",
      "lp.flowm.3.desc":
        "Role-based permissions are checked immediately — if the user isn't authorised, the request stops here, saving time and cost.",
      "lp.flowm.4.title": "Docs Searched",
      "lp.flowm.4.desc":
        "Only for authorised users — Second Brain scans your entire knowledge base to find the most relevant information.",
      "lp.flowm.5.title": "Answer Crafted",
      "lp.flowm.5.desc":
        "A clear, plain-language answer is generated in seconds, with sources cited so your team knows exactly where it came from.",
      "lp.flowm.6.title": "Reply Delivered",
      "lp.flowm.6.desc":
        "The answer arrives directly in WhatsApp — no login, no browser, no friction. The loop is complete.",
      "lp.uc.label": "Use cases",
      "lp.uc.title": "Built for real teams.",
      "lp.uc.sub":
        "Second Brain adapts to how your organization works — not the other way around.",
      "lp.uc.1.title": "Internal knowledge base",
      "lp.uc.1.desc":
        "SOPs, HR policies, onboarding docs. New employees get answers instantly instead of pinging a colleague.",
      "lp.uc.2.title": "Financial teams",
      "lp.uc.2.desc":
        "Query reports, forecasts, and budgets in seconds. Role-based access keeps sensitive numbers away from unauthorized users.",
      "lp.uc.3.title": "Sales & marketing",
      "lp.uc.3.desc":
        "Product specs, pricing sheets, competitive battlecards — your sales team always has the right answer on hand.",
      "lp.uc.4.title": "Legal & compliance",
      "lp.uc.4.desc":
        "Search contracts, regulations, and compliance docs. Get cited excerpts instead of reading through hundreds of pages.",
      "lp.uc.5.title": "Operations",
      "lp.uc.5.desc":
        "Technical manuals, vendor contacts, project briefs. Field teams get answers without needing VPN or a laptop.",
      "lp.uc.6.title": "Training & L&D",
      "lp.uc.6.desc":
        "Course materials and training guides accessible via WhatsApp. Learners can quiz themselves and get explanations on demand.",
      "lp.uc.7.title": "Healthcare & clinics",
      "lp.uc.7.desc":
        "Clinical protocols, drug references, and patient intake forms instantly accessible to staff — without touching a desktop.",
      "lp.uc.8.title": "Customer support teams",
      "lp.uc.8.desc":
        "Product FAQs, return policies, and troubleshooting guides at agents' fingertips. Faster resolutions, fewer escalations.",
      "lp.sec.label": "Security & permissions",
      "lp.sec.title": "Your data, your rules.",
      "lp.sec.sub":
        "Every query is classified and checked against the user's role before the assistant answers. Sensitive information stays protected — automatically.",
      "lp.sec.1.title": "Role-based access control",
      "lp.sec.1.desc":
        "Define custom roles with specific permission flags. Assign one or more roles per user.",
      "lp.sec.2.title": "AI query classification",
      "lp.sec.2.desc":
        "Each incoming message is classified as financial, strategic, or sensitive before any answer is generated.",
      "lp.sec.3.title": "Graceful denial",
      "lp.sec.3.desc":
        "Unauthorized queries get a clear, friendly refusal — not an error. Users know to contact the right person.",
      "lp.sec.4.title": "WhatsApp identity verification",
      "lp.sec.4.desc":
        "Users are matched by their verified WhatsApp number. No passwords to manage for end users.",
      "lp.nav.privacy": "Privacy",
      "lp.priv.label": "Data Privacy",
      "lp.priv.title": "Built with privacy by default.",
      "lp.priv.sub":
        "Every technical decision was made with your data's safety in mind. No surprises, no trade-offs.",
      "lp.priv.1.title": "Conversations expire in 10 minutes",
      "lp.priv.1.desc":
        "Chat sessions automatically delete after 10 minutes of inactivity. We never accumulate conversation history on your team.",
      "lp.priv.2.title": "Max 12 messages in memory",
      "lp.priv.2.desc":
        "History is hard-capped at 12 exchanges per session. Long-term conversation profiles of your employees are never built.",
      "lp.priv.3.title": "No raw conversation storage",
      "lp.priv.3.desc":
        "Only your uploaded knowledge base documents are retained, accessible exclusively by registered users in your organization. All files are end-to-end encrypted — even Rolplay cannot access their contents.",
      "lp.priv.4.title": "Query-level permission gating",
      "lp.priv.4.desc":
        "Every message is classified by AI before touching any document. Financial, strategic, and sensitive data only flows to authorized roles.",
      "lp.priv.5.title": "WhatsApp-verified identity",
      "lp.priv.5.desc":
        "Users are matched by their verified WhatsApp number — no passwords, no accounts, no credentials for end users to manage.",
      "lp.priv.6.title": "Enterprise-grade infrastructure",
      "lp.priv.6.desc":
        "All infrastructure powering Second Brain is built to enterprise-grade security standards, with encryption at rest and in transit.",
      "lp.priv.trust.label":
        "Built on enterprise-grade, SOC 2 compliant infrastructure",
      "lp.priv.trust.1": "End-to-end encryption",
      "lp.priv.trust.2": "SOC 2 compliant",
      "lp.priv.trust.3": "Zero data retention on chats",
      "lp.priv.trust.4": "Role-based access",
      "lp.priv.trust.5": "WhatsApp-verified identity",
      "lp.priv.quote":
        '"Your conversations are ephemeral — messages expire in 10 minutes and history is capped at 12 exchanges. The documents you upload are end-to-end encrypted and accessible only to registered users in your organization. Not even Rolplay can read their contents."',
      "lp.cta.h2":
        'Ready to give your team a <span class="grad-text">second brain?</span>',
      "lp.cta.p":
        "Set up your organization in minutes. No credit card required. Your team is already on WhatsApp — this is the only step left.",
      "lp.cta.btn": "Create free account →",
      "lp.footer.by": "a product by",
      "lp.footer.copy": "© 2026 Rolplay. All rights reserved.",

      // ── Super Admin ────────────────────────────────────────
      "sadmin.console": "SuperAdmin Console",
      "sadmin.badge": "Rolplay Admin",
      "sadmin.signout": "Sign out",
      "sadmin.platform_link": "← Platform",
      "sadmin.common.cancel": "Cancel",
      "sadmin.common.delete": "Delete",
      "sadmin.common.deleting": "Deleting…",
      "sadmin.common.loading": "Loading…",
      "sadmin.common.actions": "Actions",
      "sadmin.common.created": "Created",
      "sadmin.common.status": "Status",
      "sadmin.common.active": "Active",
      "sadmin.common.inactive": "Inactive",
      "sadmin.common.total": "total",
      "sadmin.common.view_all": "View all →",
      "sadmin.common.delete_failed": "Delete failed",
      "sadmin.nav.overview": "Overview",
      "sadmin.nav.dashboard": "Dashboard",
      "sadmin.nav.platform": "Platform",
      "sadmin.nav.orgs": "Organizations",
      "sadmin.nav.users": "All Users",
      "sadmin.nav.scenarios": "Scenarios",
      "sadmin.login.console": "Super Admin Console",
      "sadmin.login.heading": "SuperAdmin Access",
      "sadmin.login.subtitle": "Rolplay internal use only",
      "sadmin.login.tier": "Highest Privilege Level",
      "sadmin.login.warning": "This portal grants unrestricted access to all organisations, users, and platform data. Unauthorised access is prohibited.",
      "sadmin.login.email": "Admin Email",
      "sadmin.login.password": "Password",
      "sadmin.login.btn": "Sign In to Super Admin",
      "sadmin.login.btn.loading": "Authenticating…",
      "sadmin.login.back": "← Back to platform",
      "sadmin.login.security": "All sessions are logged and monitored",
      "sadmin.login.error.invalid": "Invalid credentials",
      "sadmin.login.error.conn": "Connection error. Please try again.",
      "sadmin.dash.title": "Dashboard",
      "sadmin.dash.subtitle": "Real-time platform health & growth metrics",
      "sadmin.dash.period": "Period",
      "sadmin.dash.7d": "Last 7 days",
      "sadmin.dash.30d": "Last 30 days",
      "sadmin.dash.period_note_7": "Showing last 7 days",
      "sadmin.dash.period_note_30": "Showing last 30 days",
      "sadmin.dash.kpi.orgs": "Organizations",
      "sadmin.dash.kpi.new_orgs": "New Orgs",
      "sadmin.dash.kpi.new_users": "New Users",
      "sadmin.dash.kpi.active": "Active Users",
      "sadmin.dash.kpi.messages": "Messages",
      "sadmin.dash.kpi.docs": "Documents",
      "sadmin.dash.kpi.avg_resp": "Avg Response",
      "sadmin.dash.kpi.orgs_sub_period": "+{count} new this period",
      "sadmin.dash.kpi.users_sub_signed": "+{count} signed up",
      "sadmin.dash.kpi.active_sub_pct": "{pct}% of total",
      "sadmin.dash.kpi.msg_sub_period": "messages in {days}d",
      "sadmin.dash.kpi.msg_label_period": "Messages ({days}d)",
      "sadmin.dash.kpi.docs_sub_uploaded": "+{count} uploaded",
      "sadmin.dash.chart.messages": "Messages Processed",
      "sadmin.dash.chart.msg_sub": "Daily volume",
      "sadmin.dash.chart.msg_sub_days": "Daily volume — last {days} days",
      "sadmin.dash.chart.user_status": "User Status",
      "sadmin.dash.chart.active_vs": "Active vs inactive",
      "sadmin.dash.lbl.active": "Active",
      "sadmin.dash.lbl.inactive": "Inactive",
      "sadmin.dash.lbl.total": "total",
      "sadmin.dash.chart.signups": "New Signups",
      "sadmin.dash.chart.signup_sub": "Daily signups",
      "sadmin.dash.chart.signup_sub_days": "Daily signups — last {days} days",
      "sadmin.dash.chart.org_growth": "Organization Growth",
      "sadmin.dash.chart.org_sub": "New orgs & activation",
      "sadmin.dash.chart.org_sub_days": "New in last {days} days",
      "sadmin.dash.chart.org_new_label": "New ({days}d)",
      "sadmin.dash.chart.org_total_label": "Total",
      "sadmin.dash.chart.activation": "Activation rate",
      "sadmin.dash.chart.kb": "Knowledge Base",
      "sadmin.dash.chart.kb_sub": "Usage & indexing stats",
      "sadmin.dash.chart.tip.messages": "{count} messages",
      "sadmin.dash.chart.tip.signups": "{count} signups",
      "sadmin.dash.kb.last_days": "Last {days} days",
      "sadmin.dash.table.no_orgs": "No organizations yet",
      "sadmin.dash.load_failed": "Failed to load",
      "sadmin.dash.metric.rag": "🔍 RAG queries",
      "sadmin.dash.metric.voice": "🎙️ Voice notes",
      "sadmin.dash.metric.vectors": "📌 Pinecone vectors",
      "sadmin.dash.metric.errors": "⚠️ Errors",
      "sadmin.dash.metric.roles": "🔑 Total roles",
      "sadmin.dash.chart.top_orgs": "Top Organizations",
      "sadmin.dash.chart.top_orgs_sub": "Ranked by user count",
      "sadmin.dash.col.org": "Organization",
      "sadmin.dash.col.owner": "Owner",
      "sadmin.dash.col.users": "Users",
      "sadmin.dash.col.active": "Active",
      "sadmin.dash.col.docs": "Docs",
      "sadmin.dash.col.joined": "Joined",
      "sadmin.orgs.title": "Organizations",
      "sadmin.orgs.subtitle": "All organizations registered on the platform",
      "sadmin.orgs.modal.delete_title": "⚠️ Delete Organization",
      "sadmin.orgs.modal.delete_warning": "You are about to permanently delete <strong>{name}</strong>. This will remove all its users, roles, and documents.",
      "sadmin.orgs.modal.delete_note": "This cannot be undone.",
      "sadmin.orgs.all": "All Organizations",
      "sadmin.orgs.search_ph": "Search by name or owner…",
      "sadmin.orgs.sort.users_desc": "Most users ↓",
      "sadmin.orgs.sort.users_asc": "Fewest users ↑",
      "sadmin.orgs.sort.date_desc": "Newest first",
      "sadmin.orgs.sort.date_asc": "Oldest first",
      "sadmin.orgs.sort.name_asc": "Name A→Z",
      "sadmin.orgs.col.org": "Organization",
      "sadmin.orgs.col.owner": "Owner Email",
      "sadmin.orgs.col.total": "Total Users",
      "sadmin.orgs.col.active": "Active",
      "sadmin.orgs.col.inactive": "Inactive",
      "sadmin.orgs.col.docs": "Documents",
      "sadmin.orgs.view_users": "View Users",
      "sadmin.orgs.empty": "No organizations found",
      "sadmin.users.title": "All Users",
      "sadmin.users.subtitle": "Every user across all organizations — manage access, passwords & more",
      "sadmin.users.modal.delete_title": "Delete User",
      "sadmin.users.modal.delete_warning": "This will permanently remove the user and all their data. This cannot be undone.",
      "sadmin.users.modal.delete_btn": "Delete user",
      "sadmin.users.modal.pw_title": "Change Password",
      "sadmin.users.modal.pw_new": "New Password",
      "sadmin.users.modal.pw_ph": "Min 6 characters",
      "sadmin.users.modal.pw_confirm": "Confirm Password",
      "sadmin.users.modal.pw_confirm_ph": "Repeat password",
      "sadmin.users.modal.pw_btn": "Set new password",
      "sadmin.users.modal.pw_success": "✓ Password updated successfully.",
      "sadmin.users.sum.total": "Total Users",
      "sadmin.users.sum.active": "Active",
      "sadmin.users.sum.inactive": "Inactive",
      "sadmin.users.sum.orgs": "Organizations",
      "sadmin.users.section": "Users",
      "sadmin.users.search_ph": "Search name, email, org, WhatsApp…",
      "sadmin.users.filter.all_orgs": "All Organizations",
      "sadmin.users.filter.all_statuses": "All statuses",
      "sadmin.users.col.user": "User",
      "sadmin.users.col.whatsapp": "WhatsApp",
      "sadmin.users.col.jobtitle": "Job Title",
      "sadmin.users.col.org": "Organization",
      "sadmin.users.col.role": "Role",
      "sadmin.users.col.joined": "Joined",
      "sadmin.users.empty": "No users found",
      "sadmin.scenarios.title": "Coaching Scenarios",
      "sadmin.scenarios.subtitle": "Manage coaching scenarios across all organizations",
      "sadmin.scenarios.all": "All Scenarios",
      "sadmin.scenarios.new_btn": "+ New Scenario",
      "sadmin.scenarios.search_ph": "Search by name or org…",
      "sadmin.scenarios.all_orgs": "All orgs",
      "sadmin.scenarios.col.name": "Name",
      "sadmin.scenarios.col.org": "Organization",
      "sadmin.scenarios.col.desc": "Description",
      "sadmin.scenarios.col.prompt": "System Prompt",
      "sadmin.scenarios.col.file": "Reference File",
      "sadmin.scenarios.col.sessions": "Sessions",
      "sadmin.scenarios.empty": "No scenarios found",
      "sadmin.scenarios.load_error": "Failed to load scenarios",
      "sadmin.scenarios.modal.create_title": "New Scenario",
      "sadmin.scenarios.modal.name": "Name *",
      "sadmin.scenarios.modal.name_ph": "e.g. Sales Pitch Practice",
      "sadmin.scenarios.modal.org": "Organization *",
      "sadmin.scenarios.modal.org_ph": "Select organization…",
      "sadmin.scenarios.modal.desc": "Description",
      "sadmin.scenarios.modal.desc_optional": "(optional)",
      "sadmin.scenarios.modal.desc_ph": "Brief description of the scenario",
      "sadmin.scenarios.modal.prompt": "System Prompt *",
      "sadmin.scenarios.modal.prompt_ph": "You are an expert sales coach. The user will practice a sales pitch with you...",
      "sadmin.scenarios.modal.file": "Reference File (optional)",
      "sadmin.scenarios.modal.remove_file": "Remove current reference file",
      "sadmin.scenarios.modal.active": "Active",
      "sadmin.scenarios.modal.create_btn": "Create Scenario",
      "sadmin.scenarios.modal.edit_title": "Edit Scenario",
      "sadmin.scenarios.modal.save_btn": "Save Changes",
    },
  };

  // ── Core helpers ────────────────────────────────────────
  function getLang() {
    return localStorage.getItem(STORAGE_KEY) || "es";
  }

  // Translate a key, with optional template vars: t('docs.confirm.delete', {name: 'foo'})
  function t(key, vars) {
    const lang = getLang();
    const dict = translations[lang] || translations.es;
    let str = dict[key] || translations.es[key] || key;
    if (vars) {
      Object.keys(vars).forEach((k) => {
        str = str.replace(new RegExp("\\{" + k + "\\}", "g"), vars[k]);
      });
    }
    return str;
  }

  function applyLang(lang) {
    const dict = translations[lang] || translations.es;

    // text content
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.dataset.i18n;
      if (dict[key] !== undefined) el.textContent = dict[key];
    });

    // innerHTML (for strings that contain HTML tags like <em>)
    document.querySelectorAll("[data-i18n-html]").forEach((el) => {
      const key = el.dataset.i18nHtml;
      if (dict[key] !== undefined) el.innerHTML = dict[key];
    });

    // placeholder attribute
    document.querySelectorAll("[data-i18n-ph]").forEach((el) => {
      const key = el.dataset.i18nPh;
      if (dict[key] !== undefined) el.placeholder = dict[key];
    });

    // title attribute
    document.querySelectorAll("[data-i18n-title]").forEach((el) => {
      const key = el.dataset.i18nTitle;
      if (dict[key] !== undefined) el.title = dict[key];
    });

    // aria-label attribute
    document.querySelectorAll("[data-i18n-label]").forEach((el) => {
      const key = el.dataset.i18nLabel;
      if (dict[key] !== undefined) el.setAttribute("aria-label", dict[key]);
    });

    // radio toggle: mark active option
    const btnES = document.getElementById("langES");
    const btnEN = document.getElementById("langEN");
    if (btnES) btnES.classList.toggle("active", lang === "es");
    if (btnEN) btnEN.classList.toggle("active", lang === "en");

    // html lang attribute
    document.documentElement.lang = lang === "es" ? "es" : "en";

    // Persist
    localStorage.setItem(STORAGE_KEY, lang);

    // Notify page scripts that language changed (for dynamic re-renders)
    document.dispatchEvent(new CustomEvent("langchange", { detail: { lang } }));
  }

  // ── Public API ──────────────────────────────────────────
  window.t = t;
  window.getLang = getLang;

  window.toggleLang = function () {
    applyLang(getLang() === "es" ? "en" : "es");
  };

  window.setLang = function (lang) {
    applyLang(lang);
  };

  // Apply on DOMContentLoaded so data-i18n attrs are available
  // But also run immediately for title / html[lang]
  const _lang = getLang();
  document.documentElement.lang = _lang === "es" ? "es" : "en";

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => applyLang(_lang));
  } else {
    applyLang(_lang);
  }
})();
