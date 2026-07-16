# Documentación técnica — Mtto equipos

| Campo | Valor |
|--------|--------|
| **Sistema** | Portal de mantenimiento preventivo de equipos de cómputo |
| **Organización** | Colbeef S.A.S. |
| **Repositorio** | https://github.com/brayang466/mtto-equipos |
| **Versión documentada** | Commit de línea `main` con usabilidad SUS, indicadores en vivo y optimización de latencia (`699cce6` y posteriores) |
| **Fecha del documento** | 16 de julio de 2026 |
| **Tipo** | Documentación técnica de principio a fin (arquitectura, dominio, APIs, BD, seguridad, despliegue) |

---

## 1. Propósito del sistema

Aplicación web interna para:

1. Consultar y gestionar el **inventario** de equipos de cómputo.
2. Registrar el cumplimiento del **mantenimiento preventivo 2026** (1.er y 2.do semestre).
3. Gestionar **solicitudes de mantenimiento** (usuario → TIC y TIC → usuario con aprobación).
4. Facilitar comunicación con **chat por área** y **susurros** privados.
5. Mostrar **presencia en línea** de usuarios del portal.
6. Medir **usabilidad** con encuesta SUS e indicadores operativos (KPIs).

No es un CRM ni un helpdesk genérico: está acotado al mantenimiento preventivo de equipos y al flujo TIC ↔ área laboral.

---

## 2. Stack tecnológico

| Capa | Tecnología |
|------|------------|
| Lenguaje | Python 3 |
| Framework web | Flask ≥ 3.0 |
| ORM | Flask-SQLAlchemy ≥ 3.1 |
| Formularios / CSRF | Flask-WTF ≥ 1.2 |
| Sesión de usuario | Flask-Login ≥ 0.6.3 |
| Base de datos | MySQL 8+ (`utf8mb4`), driver **PyMySQL** |
| Correo | `smtplib` (SMTP SSL/TLS) |
| Configuración | `python-dotenv` (archivo `.env`) |
| Zona horaria | `America/Bogota` (`tzdata`, `app/datetime_utils.py`) |
| Front-end | Jinja2, CSS propio (`app.css`), JavaScript vanilla (polling) |
| Tipografía UI | Plus Jakarta Sans |

Dependencias formales: `requirements.txt`.

---

## 3. Estructura del repositorio

```
mtto_equipos/
├── run.py                 # Arranque desarrollo
├── wsgi.py                # Entrada WSGI (producción)
├── requirements.txt
├── .env.example           # Plantilla de configuración (sin secretos reales)
├── .env                   # Config local (NO versionado)
├── app/
│   ├── __init__.py        # create_app, blueprints, presencia, globals
│   ├── config.py
│   ├── extensions.py      # db, csrf, login_manager
│   ├── models.py
│   ├── constants.py
│   ├── validators.py
│   ├── datetime_utils.py
│   ├── solicitud_service.py
│   ├── solicitud_export.py
│   ├── chat_service.py
│   ├── presence_service.py
│   ├── usabilidad_service.py
│   ├── mail.py / mail_templates.py
│   ├── auth/              # Blueprint autenticación
│   ├── main/              # Blueprint portal usuario + APIs JSON
│   ├── equipos/           # Blueprint superadmin (inventario/solicitudes)
│   ├── templates/
│   └── static/            # css/, js/, favicon.svg
├── database/              # Scripts SQL 01–09 + verificación
├── scripts/               # Migraciones Python, import CSV, tests MySQL
├── docs/                  # Documentación (este archivo)
└── instance/              # Runtime: uploads (no versionar contenido)
```

### Roles de módulos de dominio

| Módulo | Responsabilidad |
|--------|-----------------|
| `app/auth/` | Login, registro, logout, recuperar/restablecer contraseña |
| `app/main/` | Inicio, solicitud de usuario, aprobaciones, encuesta SUS, APIs `/api/*` |
| `app/equipos/` | Inventario, solicitudes TIC, usuarios admin, panel usabilidad (solo `superadmin`) |
| `*_service.py` | Lógica de negocio reutilizable fuera de las rutas |
| `mail*.py` | Notificaciones SMTP (texto + HTML) |

---

## 4. Arranque y configuración

### 4.1 Desarrollo (`run.py`)

1. Exige la presencia de `.env` en la raíz (no usa `.env.example` directamente).
2. `load_dotenv(..., override=True)` — el `.env` del proyecto tiene prioridad sobre variables globales de Windows.
3. `create_app()` → `app.run(host, port, debug)`.

### 4.2 Producción / WSGI (`wsgi.py`)

Carga `.env` y expone `app = create_app()` para Gunicorn, Waitress, IIS, etc.

### 4.3 Factory `create_app` (`app/__init__.py`)

- Carga `Config` desde variables de entorno.
- Genera `APP_BOOT_ID` (token por proceso) para detectar reinicio del servidor.
- Crea carpeta de uploads: `instance/<UPLOAD_RELATIVE>/`.
- Inicializa `db`, `csrf`, `login_manager`.
- `before_request`: actualiza presencia (`touch_presence`) salvo rutas `/static/`.
- `context_processor`: `app_url`, `app_name`, `app_boot_id`, `session_idle_ms`, `pending_approvals_count`.
- Registra blueprints: `auth`, `main`, `equipos`.

### 4.4 Variables de entorno (nombres; sin secretos)

| Variable | Uso |
|----------|-----|
| `SECRET_KEY` | Firmas de sesión y tokens |
| `FLASK_HOST`, `FLASK_PORT`, `FLASK_DEBUG` | Servidor de desarrollo |
| `APP_URL` | URL canónica (enlaces UI y correos) |
| `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE` | Conexión MySQL |
| `DATABASE_URL` | URI completa (prioridad sobre `MYSQL_*`) |
| `MAIL_ENABLED`, `MAIL_SERVER` / `MAIL_HOST`, `MAIL_PORT` | SMTP |
| `MAIL_USE_TLS`, `MAIL_USE_SSL`, `MAIL_SSL_VERIFY`, `MAIL_TIMEOUT` | Transporte seguro |
| `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_DEFAULT_SENDER` / `MAIL_FROM`, `MAIL_FROM_NAME` | Remitente |
| `MAIL_NOTIFY_TO` | Buzón TIC para nuevas solicitudes |
| `UPLOAD_RELATIVE`, `MAX_UPLOAD_FILES`, `MAX_UPLOAD_BYTES_PER_FILE` | Evidencias |
| `ALLOWED_IMAGE_EXTENSIONS`, `MAX_CONTENT_LENGTH` | Límites de subida |
| `SESSION_IDLE_MINUTES` | Aviso de inactividad (default 10) |

URI típica: `mysql+pymysql://usuario:clave@host:3306/mtto_equipos?charset=utf8mb4`.

---

## 5. Modelo de datos (SQLAlchemy)

Archivo: `app/models.py`.

### 5.1 `User` → tabla `usuarios`

| Campo | Notas |
|-------|--------|
| `id`, `username` (único), `email`, `password_hash` | Autenticación |
| `area`, `role` (`user` \| `superadmin`), `activo` | Autorización |
| `creado_en` | Auditoría |

Relaciones: solicitudes registradas / por aprobar, `UserPresence` 1:1, `UsabilidadEncuesta` 1:1.

### 5.2 `Equipo` → tabla `equipos`

Inventario: `numero_inventario` (único), datos contables, departamento, área, usuario asignado, cargo, descripción, marca/referencia, service tag, serial, fecha de adquisición, observaciones, flags `mtto_realizado_1s_2026` y `mtto_realizado_2s_2026`.

Relación: `solicitudes_mantenimiento` (cascade delete).

### 5.3 `SolicitudMantenimiento` → tabla `solicitudes_mantenimiento`

| Campo | Valores / notas |
|-------|-----------------|
| `equipo_id` | FK → `equipos` CASCADE |
| `registrado_por_user_id` | FK → `usuarios` SET NULL |
| `tipo_origen` | `usuario` \| `tic` |
| `usuario_aprobador_id` | Aprobador (flujo TIC → usuario) |
| `fecha_solicitud`, `fecha_mantenimiento` | |
| `fecha_respuesta_usuario`, `respuesta_usuario` | `aprobada` \| `denegada` |
| `comentario_respuesta`, `observaciones` | |
| `estado` | Ver sección 8 |
| `atendido_en`, `creado_en` | |

### 5.4 `SolicitudAdjunto` → `solicitudes_adjuntos`

`nombre_archivo` (en disco), `nombre_original`, `mime`, `tamano_bytes`.

### 5.5 `UserPresence` → `presencia_usuarios`

PK `user_id`, `last_seen`, `pagina_actual` (marcador `__offline__` = desconectado explícito).

### 5.6 `ChatMensaje` → `chat_mensajes`

`texto` (máx. 500), `tipo` (`area` \| `susurro`), `area`, `destinatario_id`, `user_id`, `creado_en`.

### 5.7 `UsabilidadEncuesta` → `usabilidad_encuestas`

`q1`…`q10` (Likert 1–5), `score` DECIMAL(5,2) 0–100, `user_id` UNIQUE.

### Diagrama de relaciones

```
usuarios ──< solicitudes_mantenimiento >── equipos
    │              │
    │              └──< solicitudes_adjuntos
    ├──1:1 presencia_usuarios
    ├──1:1 usabilidad_encuestas
    └──< chat_mensajes (autor / destinatario)
```

---

## 6. Constantes de dominio

Archivo: `app/constants.py`.

**Áreas laborales:** ADMINISTRACIÓN, CONTABILIDAD, COMPRAS, TESORERIA, PLANILLAJE, COMERCIAL, TIC, CALIDAD, OPERACIONES, DESPOSTE, SST, CALIDAD DESPOSTE.

**Roles:** `user`, `superadmin`.

**Estados de solicitud:**

| Código | Etiqueta |
|--------|----------|
| `pendiente` | Pendiente |
| `pendiente_aprobacion` | Pendiente aprobación |
| `aprobada` | Aprobada |
| `denegada` | Denegada |
| `atendida` | Atendida |

**Origen:** `usuario` | `tic`.  
**Chat:** `area` | `susurro`.  
**SUS:** 10 preguntas Likert estándar (System Usability Scale).

---

## 7. Blueprints y rutas HTTP

### 7.1 Auth — prefijo `/auth`

| Método | Ruta | Propósito |
|--------|------|-----------|
| GET/POST | `/auth/login` | Inicio de sesión (`remember=True`) |
| GET/POST | `/auth/logout` | Cierra sesión + marca offline |
| GET/POST | `/auth/registro` | Alta pública rol `user` |
| GET/POST | `/auth/recuperar` | Solicita reset (usuario + correo) |
| GET/POST | `/auth/restablecer/<token>` | Nueva contraseña (token temporizado) |

### 7.2 Main — sin prefijo

| Método | Ruta | Auth | Propósito |
|--------|------|------|-----------|
| GET | `/` | Público | Inicio; avisa SUS pendiente a no-admin |
| GET | `/login` | — | Alias → `/auth/login` |
| GET | `/favicon.ico` | — | Favicon SVG |
| GET/POST | `/registrar-solicitud` | Login (no superadmin) | Solicitud origen usuario + evidencias |
| GET/POST | `/mis-aprobaciones` | Login (no superadmin) | Aprobar/denegar solicitudes TIC |
| GET/POST | `/usabilidad/encuesta` | Login (no superadmin) | Encuesta SUS |

### 7.3 Equipos — prefijo `/equipos`

`before_request`: autenticación **y** `role == superadmin`.

| Método | Ruta | Propósito |
|--------|------|-----------|
| GET | `/equipos/` | Inventario (búsqueda, paginación) |
| GET/POST | `/equipos/<id>` | Detalle + flags mtto 2026 |
| GET/POST | `/equipos/<id>/editar` | Editar / eliminar equipo |
| GET/POST | `/equipos/<id>/solicitud-mantenimiento` | Solicitud en nombre de flujo usuario |
| GET/POST | `/equipos/<id>/solicitud-tic` | Solicitud TIC → aprobador |
| GET | `/equipos/solicitudes` | Panel de solicitudes |
| GET | `/equipos/solicitudes/exportar` | CSV o ZIP de evidencias |
| GET/POST | `/equipos/solicitudes/<id>/editar` | Edición admin |
| GET/POST | `/equipos/solicitudes/<id>/eliminar` | Baja + borrado de archivos |
| GET | `/equipos/solicitudes/<id>/resumen` | Fragmento HTML de detalle |
| POST | `/equipos/solicitudes/<id>/marcar-atendida` | Cierre + correo |
| GET | `/equipos/adjuntos/<id>` | Sirve imagen (anti path-traversal) |
| GET | `/equipos/usabilidad` | Panel SUS + KPIs |
| GET | `/equipos/api/usabilidad` | JSON refresco del panel |
| GET | `/equipos/usuarios` | Lista de usuarios |
| GET/POST | `/equipos/usuarios/nuevo` | Crear usuario |
| GET/POST | `/equipos/usuarios/<id>/editar` | Editar usuario |

---

## 8. APIs JSON

| Método | Endpoint | Auth | Respuesta / uso |
|--------|----------|------|-----------------|
| GET | `/api/session/ping` | Login | `{ok, boot_id}` — heartbeat de sesión |
| GET | `/api/indicators` | Login | `online_count`, `pending_approvals_count`, opcional `users` (`user_ids`) |
| GET | `/api/chat/estado` | Login | Mensajes + presencia opcional (`since_id`, `modo`, `peer_id`, `presence`) |
| POST | `/api/chat/enviar` | Login + CSRF | Envío área o susurro |
| POST | `/api/presence/offline` | Login + CSRF | Marca `__offline__` |
| GET | `/equipos/api/usabilidad` | Superadmin | Panel SUS/ops (`desde`, `hasta`) |

### Intervalos de polling en el cliente

| Script | Intervalo aproximado |
|--------|----------------------|
| `team-chat.js` | ~2,2 s (presencia cada 2 ticks ≈ 4,4 s) |
| `live-indicators.js` | ~8 s |
| `usabilidad-live.js` | ~12 s |
| `session-idle.js` | ping cada 15 s |

---

## 9. Servicios de dominio

| Archivo | Responsabilidad |
|---------|-----------------|
| `solicitud_service.py` | Equipos por área, evidencias, crear solicitud usuario/TIC, estados UI, editar/eliminar |
| `solicitud_export.py` | Export CSV; ZIP de evidencias por rango de fechas |
| `chat_service.py` | Mensajes área/susurro, historial (50), poll (40), serialización |
| `presence_service.py` | Touch con throttle ~18 s, ventana online 30 s, offline, conteos, payload portal |
| `usabilidad_service.py` | Score SUS, encuesta, agregados, KPIs, panel |
| `mail.py` / `mail_templates.py` | SMTP y plantillas |
| `equipos/inventario_service.py` | Choices de área, edición y baja de equipo |
| `validators.py` | Username `nombre.apellido`, email `@colbeef.com`, política de password, fechas |
| `datetime_utils.py` | Ahora Colombia, formatos de chat y último acceso |

### Correos disparados

- Nueva solicitud de usuario → TIC (`MAIL_NOTIFY_TO`) + confirmación al registrador.
- Solicitud TIC pendiente → correo del aprobador.
- Respuesta de aprobación/denegación → TIC.
- Solicitud marcada atendida → registrador.
- Recuperación de contraseña → usuario.

---

## 10. Flujo de solicitudes de mantenimiento

### 10.1 Flujo A — Usuario → TIC

1. Usuario autentica y abre `/registrar-solicitud`.
2. Solo ve equipos cuya `equipos.area` coincide con su `usuarios.area`.
3. Crea solicitud con `tipo_origen=usuario`, estado inicial `pendiente`.
4. Puede adjuntar imágenes (evidencias) en `instance/uploads_solicitudes/`.
5. Sistema envía correos (TIC + confirmación).
6. Superadmin atiende con `marcar-atendida` → estado `atendida`, `atendido_en`, correo.

### 10.2 Flujo B — TIC → Usuario

1. Superadmin en `/equipos/<id>/solicitud-tic` elige aprobador del área.
2. Estado `pendiente_aprobacion`; correo al aprobador.
3. En `/mis-aprobaciones` el usuario:
   - **Aprueba** → `aprobada` + fechas + correo a TIC.
   - **Deniega** → `denegada` con vigencia; permanece “abierta” mientras la fecha sea ≥ hoy (`denegada_sigue_abierta`).
4. TIC puede marcar atendida si está `pendiente`, `aprobada`, o denegada aún abierta.

### 10.3 Adjuntos

- Extensiones permitidas (configurables): `png,jpg,jpeg,webp,gif`.
- Nombre en disco: token aleatorio + extensión; original con `secure_filename`.
- Límites de cantidad y tamaño vía `.env`.

### 10.4 Exportación

`GET /equipos/solicitudes/exportar?formato=csv|zip&desde=&hasta=`

---

## 11. Autenticación y autorización

### Roles

| Rol | Capacidades |
|-----|-------------|
| `user` | Solicitud, aprobaciones, encuesta SUS, chat |
| `superadmin` | Inventario, solicitudes internas, usuarios, usabilidad admin. Método `User.is_superadmin()` |

### Registro

- Username formato `nombre.apellido`.
- Correo dominio `@colbeef.com`.
- Área de `AREAS_LABORALES`.
- Contraseña: mínimo 8, mayúscula + símbolo; lista de contraseñas débiles bloqueada.
- Rol forzado `user`.

### Login

- Username en minúsculas, `activo=True`, hash Werkzeug.
- `login_manager.login_view = "auth.login"`.

### Reset de contraseña

- Token: `itsdangerous.URLSafeTimedSerializer`, salt `pw-reset-mtto-equipos`, payload `{uid}`, vigencia 24 h.
- Archivo: `app/auth/tokens.py`.
- Requiere `MAIL_ENABLED=true`.

### Administración de usuarios

CRUD en `/equipos/usuarios/*`. Un superadmin no puede desactivarse ni quitarse el rol a sí mismo.

---

## 12. Chat y presencia

### Chat de área

Mensajes `tipo=area` filtrados por el área del usuario autenticado.

### Susurro

Mensajes privados `tipo=susurro` entre dos usuarios (consulta bidireccional). UI: botón en la lista de usuarios → canal privado → “Volver al área”.

### Presencia

- `touch_presence` en cada request autenticado (throttle ~18 s para no saturar MySQL).
- Online: `last_seen` dentro de 30 s y `pagina_actual != __offline__`.
- Logout y `sendBeacon` a `/api/presence/offline` al cerrar pestaña.

### Límites

Texto máx. 500 caracteres; historial reciente 50; mensajes por poll incremental 40.

---

## 13. Usabilidad (SUS + KPIs)

### Migración 09

- SQL: `database/09_usabilidad_sus.sql`
- Script: `scripts/aplicar_migracion_09_usabilidad.py`
- Tabla: `usabilidad_encuestas`

### Encuesta (usuario)

- Ruta: `/usabilidad/encuesta`
- Formulario: 10 ítems Likert.
- Fórmula SUS: ítems impares `(v−1)`, pares `(5−v)`, total × 2,5 → score 0–100.
- Una fila por usuario (upsert). Superadmin redirigido al panel.

### Panel (superadmin)

- HTML: `/equipos/usabilidad`
- API JSON: `/equipos/api/usabilidad`
- JS: `usabilidad-live.js` (refresco en vivo)

### Agregado SUS

Promedio, % de respuesta vs usuarios `role=user` activos. Bandas: ≥80 excelente, 68–79 aceptable, &lt;68 mejorar.

### KPIs operativos (IDs)

`adopcion_7`, `adopcion_30`, `online`, `ciclo`, `respuesta_usuario`, `cierre`, `aprobacion`, `backlog`, `evidencias`, `chat_area`, `susurro`, más distribución por estado, chat por área y cobertura área/usuarios.

### Indicadores globales en vivo

`live-indicators.js` consume `/api/indicators` para:

- Badge de aprobaciones pendientes en la navegación.
- Contador de conectados.
- Estado online en la tabla de usuarios (`data-user-presence`).

---

## 14. Front-end

### Templates principales

| Plantilla | Uso |
|-----------|-----|
| `base.html` | Layout, nav por rol, chat lateral, modal de sesión, scripts globales |
| `inicio.html` | Landing |
| `auth/*.html` | Login, registro, recuperar, restablecer |
| `main/registrar_solicitud.html` | Solicitud usuario |
| `main/mis_aprobaciones.html` | Aprobaciones |
| `main/usabilidad_encuesta.html` | SUS |
| `equipos/*.html` | Inventario, solicitudes, usuarios, usabilidad |
| `macros/nav.html` | Macro de enlace “atrás” |

### JavaScript

| Archivo | Función |
|---------|---------|
| `session-idle.js` | Inactividad, reinicio (`APP_BOOT_ID`), reconexión, heartbeat |
| `live-indicators.js` | Badges e indicadores globales |
| `team-chat.js` | Chat área/susurro, emojis, presencia |
| `usabilidad-live.js` | Refresco del panel KPIs/SUS |
| `solicitud-detalle.js` | Carga HTML de resumen |
| `aprobacion-draft.js` | Borrador de respuesta de aprobación |
| `password-toggle.js` | Mostrar/ocultar contraseña |

Estilos: `app/static/css/app.css`.

---

## 15. Base de datos y migraciones

### Scripts SQL (`database/`)

| Archivo | Contenido |
|---------|-----------|
| `01_crear_base_y_tabla.sql` | BD `mtto_equipos` + tabla `equipos` |
| `02_usuario_app.sql` | Plantilla GRANT usuario MySQL de aplicación |
| `03_solicitudes_mantenimiento.sql` | Solicitudes y adjuntos |
| `04_auth_usuarios.sql` | `usuarios` + columnas de estado/registrador + seed |
| `05_aprobacion_tic_presencia.sql` | Origen TIC, aprobador, respuesta; `presencia_usuarios` |
| `06_chat_mensajes.sql` | Chat base |
| `07_email_no_unico.sql` | Elimina UNIQUE de email |
| `08_chat_area_susurro.sql` | `tipo`, `area`, `destinatario_id` |
| `09_usabilidad_sus.sql` | `usabilidad_encuestas` |
| `verificar_datos.sql` | Consultas de verificación |

### Scripts Python (`scripts/`)

| Script | Función |
|--------|---------|
| `aplicar_migracion_03_solicitudes.py` … `09_usabilidad.py` | Aplican cada migración SQL |
| `import_inventario_csv.py` | Carga inventario CSV → `equipos` |
| `test_mysql_env.py` | Prueba de conexión con `.env` |

**Orden recomendado de despliegue BD:**  
`01` → (`02` opcional) → `03` → `04` → `05` → `06` → `07` → `08` → `09` → import CSV.

---

## 16. Seguridad

| Control | Implementación |
|---------|----------------|
| CSRF | `CSRFProtect` global; POST de APIs validan `X-CSRFToken` / form |
| Autenticación | `@login_required`; blueprint `equipos` restringido a superadmin |
| Sesión idle | Modal tras `SESSION_IDLE_MINUTES`; continuar o cerrar sesión |
| Boot ID | Detecta reinicio del proceso Flask |
| Uploads | Allowlist de extensiones, límites de tamaño, nombre aleatorio, chequeo `relative_to` anti path-traversal |
| Redirects | Helpers `_safe_next` / `_safe_*_return` contra open redirect |
| Contraseñas | Hash Werkzeug + política corporativa |
| Dominio de correo | Solo `@colbeef.com` en registro |
| Tokens reset | Firmados, 24 h, salt dedicado |
| Pool MySQL | `pool_pre_ping=True` |
| Presencia offline | Logout y cierre de pestaña |
| Rendimiento / abuso | Throttle de presencia; skip de COUNT de aprobaciones en `/api/*` y `/static/` |

**Nota operativa:** rotar credenciales de cualquier usuario seed de SQL en entornos reales; no versionar `.env`.

---

## 17. Actores y mapa operativo

| Actor | Entradas típicas |
|-------|------------------|
| Usuario de área | Registrar solicitud, Aprobaciones, Encuesta, Chat |
| Superadmin (TIC) | Inventario, Solicitudes, Usuarios, Usabilidad, Chat |
| Sistema | Polling, SMTP, presencia, cálculo SUS/KPIs |

### Arranque local rápido

1. Copiar `.env.example` → `.env` y completar MySQL/correo.
2. Aplicar migraciones SQL o scripts `aplicar_migracion_*`.
3. (Opcional) Importar inventario con `scripts/import_inventario_csv.py`.
4. Instalar dependencias: `pip install -r requirements.txt`.
5. Ejecutar: `python run.py` (puerto tipico de ejemplo: `5001`).

---

## 18. Optimizaciones de latencia implementadas

Resumen de mejoras para que la UI no “sienta” demora:

1. **Presencia con throttle** (~18 s) y sin tocar BD en `/static/`.
2. **Chat:** poll ~2,2 s; lista de presencia solo cada N ticks; `joinedload` autor/destinatario; historial acotado.
3. **Sesión:** heartbeat liviano `/api/session/ping` (no recarga el chat completo).
4. **Listado de solicitudes:** conteo de adjuntos en batch (evita N+1).
5. **Context processor:** no calcula aprobaciones pendientes en rutas `/api/*`.
6. **Indicadores en vivo** desacoplados (`/api/indicators`, `/equipos/api/usabilidad`).

---

## 19. Historial funcional (respaldo de entregables)

Este documento respalda el alcance construido en el portal, incluyendo:

1. Inventario MySQL + import CSV + mantenimiento 2026 por semestre.
2. Autenticación (login, registro, reset, roles).
3. Solicitudes usuario↔TIC, adjuntos, correos SMTP, exportación CSV/ZIP.
4. Gestión de usuarios (superadmin).
5. Chat por área + susurro + presencia.
6. Sesión con confirmación ante reinicio/inactividad/reconexión.
7. Usabilidad SUS (migración 09, encuesta, panel KPIs).
8. Indicadores en tiempo real (nav, chat, usabilidad, usuarios).
9. Optimización general de latencia (presencia, polling, N+1, ping).

---

## 20. Referencias de archivos clave

```
app/__init__.py
app/config.py
app/models.py
app/constants.py
app/auth/routes.py
app/main/routes.py
app/equipos/routes.py
app/solicitud_service.py
app/chat_service.py
app/presence_service.py
app/usabilidad_service.py
app/mail.py
run.py
wsgi.py
requirements.txt
.env.example
database/01_*.sql … 09_*.sql
scripts/aplicar_migracion_*.py
docs/DOCUMENTACION_TECNICA.md   ← este documento
```

---

*Documento generado para respaldo técnico del programa Mtto equipos. Actualizar este archivo cuando cambien rutas, modelos, migraciones o contratos de API.*
