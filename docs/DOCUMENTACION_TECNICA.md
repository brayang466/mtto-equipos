# Documentación técnica del código — Mtto equipos

| Metadato | Valor |
|----------|--------|
| **Producto** | Portal web de mantenimiento preventivo de equipos de cómputo |
| **Organización** | Colbeef S.A.S. |
| **Repositorio** | https://github.com/brayang466/mtto-equipos |
| **Audiencia** | Desarrolladores, TIC, auditores técnicos |
| **Nivel** | Documentación de código estilo senior (arquitectura, lenguajes, lógica y extensión) |
| **Fecha** | Julio 2026 |

---

## Tabla de contenidos

1. [Visión del sistema](#1-visión-del-sistema)
2. [Lenguajes y tecnologías](#2-lenguajes-y-tecnologías)
3. [Arquitectura del software](#3-arquitectura-del-software)
4. [Estructura del repositorio](#4-estructura-del-repositorio)
5. [Ciclo de vida de la aplicación](#5-ciclo-de-vida-de-la-aplicación)
6. [Configuración y entorno](#6-configuración-y-entorno)
7. [Capa de datos (ORM y MySQL)](#7-capa-de-datos-orm-y-mysql)
8. [Constantes y dominio de negocio](#8-constantes-y-dominio-de-negocio)
9. [Blueprints y mapa de rutas](#9-blueprints-y-mapa-de-rutas)
10. [Servicios: lógica de negocio documentada](#10-servicios-lógica-de-negocio-documentada)
11. [Flujos end-to-end](#11-flujos-end-to-end)
12. [Capa de presentación (HTML/Jinja, CSS, JS)](#12-capa-de-presentación-htmljinja-css-js)
13. [APIs JSON y tiempo real (polling)](#13-apis-json-y-tiempo-real-polling)
14. [Correo electrónico](#14-correo-electrónico)
15. [Seguridad](#15-seguridad)
16. [Rendimiento y optimizaciones](#16-rendimiento-y-optimizaciones)
17. [Migraciones y despliegue de base de datos](#17-migraciones-y-despliegue-de-base-de-datos)
18. [Convenciones de código](#18-convenciones-de-código)
19. [Guía para extender el sistema](#19-guía-para-extender-el-sistema)
20. [Glosario](#20-glosario)

---

## 1. Visión del sistema

**Mtto equipos** es una aplicación web interna que centraliza:

| Capacidad | Descripción |
|-----------|-------------|
| Inventario | Consulta y edición del parque de equipos de cómputo |
| Mantenimiento 2026 | Marcado de cumplimiento por semestre (1.er / 2.do) |
| Solicitudes | Flujo usuario → TIC y TIC → usuario (con aprobación) |
| Evidencias | Adjuntos de imagen asociados a solicitudes |
| Chat | Canal por área laboral + mensajes privados (“susurro”) |
| Presencia | Quién está conectado en el portal |
| Usabilidad | Encuesta SUS + panel de KPIs operativos |
| Notificaciones | Correos SMTP ante eventos clave |

No pretende ser un helpdesk genérico: el dominio está acotado al **mantenimiento preventivo** y a la coordinación TIC ↔ áreas laborales.

### Actores

| Actor | Rol técnico | Capacidades |
|-------|-------------|-------------|
| Usuario de área | `role = user` | Solicitudes, aprobaciones, encuesta SUS, chat |
| Superadmin (TIC) | `role = superadmin` | Inventario, panel de solicitudes, usuarios, usabilidad, chat |
| Sistema | Proceso Flask + MySQL + SMTP | Presencia, polling, correos, cálculos SUS/KPI |

---

## 2. Lenguajes y tecnologías

El sistema es **políglota por capas**. Cada lenguaje tiene un rol claro; no hay TypeScript, React ni framework JS de SPA.

### 2.1 Matriz de lenguajes

| Lenguaje / tecnología | Dónde vive | Para qué se usa |
|----------------------|------------|-----------------|
| **Python 3** | `app/`, `run.py`, `wsgi.py`, `scripts/` | Backend: rutas, ORM, servicios, validación, SMTP, migraciones |
| **SQL (MySQL 8+)** | `database/*.sql` | Esquema, índices, FKs, seeds; charset `utf8mb4` |
| **Jinja2** | `app/templates/` | Render server-side de HTML; herencia, macros, bloques |
| **HTML5** | Plantillas Jinja | Semántica de páginas, formularios, diálogos, chat |
| **CSS3** | `app/static/css/app.css` | Diseño visual (variables, layout, componentes BEM-ish) |
| **JavaScript (ES5-style)** | `app/static/js/*.js` | UX en cliente: polling, modales, chat, idle de sesión |
| **Markdown** | `docs/` | Documentación técnica (este documento) |
| **dotenv / env** | `.env`, `.env.example` | Configuración por entorno (no código) |

### 2.2 Stack Python (dependencias)

Definidas en `requirements.txt`:

| Paquete | Rol en el código |
|---------|------------------|
| `Flask` ≥ 3.0 | Framework HTTP, blueprints, plantillas |
| `Flask-SQLAlchemy` ≥ 3.1 | ORM sobre SQLAlchemy |
| `Flask-WTF` ≥ 1.2 | Formularios + CSRF |
| `Flask-Login` ≥ 0.6.3 | Sesión de usuario (`UserMixin`, `@login_required`) |
| `PyMySQL` | Driver MySQL |
| `cryptography` | Soporte TLS/crypto del ecosistema |
| `email-validator` | Validación de correos en WTForms |
| `python-dotenv` | Carga de `.env` |
| `tzdata` | Zona horaria `America/Bogota` en Windows/Linux |

### 2.3 Qué **no** se usa (decisión consciente)

- Sin npm/webpack/Vite: el JS es vanilla y se sirve estático.
- Sin WebSockets/SSE: el “tiempo real” es **polling HTTP** controlado.
- Sin microservicios: monolito modular por blueprints y servicios.
- Sin ORM migrations tipo Alembic en runtime: evoluciones vía SQL versionado + scripts Python.

---

## 3. Arquitectura del software

### 3.1 Estilo arquitectónico

**Monolito modular Flask** con separación clara:

```
 Cliente (navegador)
        │  HTML + JSON
        ▼
 ┌──────────────────────────────────────┐
 │  Blueprints (capa HTTP / orquestación)│
 │  auth │ main │ equipos               │
 └───────────────┬──────────────────────┘
                 │ llama
                 ▼
 ┌──────────────────────────────────────┐
 │  Servicios de dominio                 │
 │  solicitud │ chat │ presence │ mail │ │
 │  usabilidad │ inventario │ export     │
 └───────────────┬──────────────────────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
   SQLAlchemy ORM      smtplib / disco
        ▼
      MySQL
```

**Principio senior:** las rutas deben ser delgadas (validar entrada, llamar servicio, responder). La lógica de negocio vive en `*_service.py`.

### 3.2 Patrones aplicados

| Patrón | Implementación |
|--------|----------------|
| **Application Factory** | `create_app()` en `app/__init__.py` |
| **Blueprint** | Tres paquetes: `auth`, `main`, `equipos` |
| **Extension objects** | `db`, `csrf`, `login_manager` en `extensions.py` (init diferido) |
| **Service layer** | Módulos `*_service.py` sin dependencia de plantillas |
| **Context processor** | Variables globales de plantilla (`pending_approvals_count`, `app_boot_id`, …) |
| **before_request hooks** | Presencia global; gate superadmin en `/equipos` |
| **Form Object** | WTForms por feature (`auth/forms`, `main/forms`, `equipos/forms`) |
| **Constants as single source of truth** | `app/constants.py` |
| **Signed tokens** | `itsdangerous` para reset de contraseña |

### 3.3 Diagrama de blueprints

```
create_app()
   ├── Blueprint auth     url_prefix=/auth
   ├── Blueprint main     (sin prefijo; incluye /api/*)
   └── Blueprint equipos  url_prefix=/equipos  [solo superadmin]
```

---

## 4. Estructura del repositorio

```
mtto_equipos/
├── run.py                      # Entrada desarrollo
├── wsgi.py                     # Entrada producción (WSGI)
├── requirements.txt
├── .env.example                # Plantilla de configuración
├── .env                        # Secretos locales (NO versionar)
├── app/
│   ├── __init__.py             # Factory + hooks globales
│   ├── config.py               # Clase Config desde entorno
│   ├── extensions.py           # db, csrf, login_manager
│   ├── models.py               # Modelos SQLAlchemy
│   ├── constants.py            # Dominio: roles, estados, SUS, áreas
│   ├── validators.py           # Validadores reutilizables WTForms
│   ├── datetime_utils.py       # Zona Colombia / formatos
│   ├── solicitud_service.py    # Núcleo de solicitudes
│   ├── solicitud_export.py     # CSV / ZIP
│   ├── chat_service.py
│   ├── presence_service.py
│   ├── usabilidad_service.py
│   ├── mail.py
│   ├── mail_templates.py
│   ├── auth/                   # Login, registro, reset
│   ├── main/                   # Portal usuario + APIs
│   ├── equipos/                # Inventario y admin TIC
│   ├── templates/              # Jinja2
│   └── static/                 # css/, js/, favicon
├── database/                   # SQL 01–09 + verificación
├── scripts/                    # Migraciones Python, import CSV
├── docs/                       # Documentación (este archivo)
└── instance/                   # Runtime (uploads); no versionar contenido
```

---

## 5. Ciclo de vida de la aplicación

### 5.1 Desarrollo — `run.py`

1. Verifica que exista `.env` en la raíz.
2. `load_dotenv(..., override=True)` — el `.env` del proyecto gana sobre variables globales de Windows.
3. Importa `create_app()` y arranca `app.run(host, port, debug)`.

### 5.2 Producción — `wsgi.py`

Carga `.env` y expone `app = create_app()` para el servidor WSGI (Gunicorn, Waitress, IIS, etc.).

### 5.3 Factory — `create_app()` (lógica paso a paso)

Archivo: `app/__init__.py`.

| Paso | Qué hace | Por qué |
|------|----------|---------|
| 1 | `Flask(__name__, instance_relative_config=True)` | Aísla `instance/` para uploads |
| 2 | `app.config.from_object(Config)` | Centraliza env |
| 3 | Genera `APP_BOOT_ID` | Detectar reinicio del proceso en el front |
| 4 | Crea carpeta de uploads | Evitar fallos al guardar evidencias |
| 5 | `db.init_app`, `csrf.init_app`, `login_manager.init_app` | Extensiones enlazadas a la app |
| 6 | `before_request` → `touch_presence` | Actualizar “último visto” (con throttle) |
| 7 | `context_processor` → globals Jinja | Badges y config de sesión en todas las páginas |
| 8 | `register_blueprint` × 3 | Montar rutas |

**Detalle de presencia en cada request autenticado:** se omite `/static/` para no abrir conexión a MySQL por cada CSS/JS/imagen.

**Detalle del context processor:** el `COUNT` de aprobaciones pendientes **no** se ejecuta en rutas `/api/*` ni `/static/`, para no encarecer el polling.

---

## 6. Configuración y entorno

Archivo: `app/config.py` — clase `Config`.

### 6.1 Categorías de variables

| Categoría | Variables (nombres) | Efecto en código |
|-----------|---------------------|------------------|
| Seguridad | `SECRET_KEY` | Sesión Flask + firma de tokens |
| Servidor | `FLASK_HOST`, `FLASK_PORT`, `FLASK_DEBUG` | Solo `run.py` |
| Pública | `APP_URL` | Enlaces canónicos y correos |
| MySQL | `MYSQL_*` o `DATABASE_URL` | `SQLALCHEMY_DATABASE_URI` |
| Sesión UI | `SESSION_IDLE_MINUTES` | Modal de inactividad |
| Uploads | `UPLOAD_RELATIVE`, `MAX_UPLOAD_*`, `ALLOWED_IMAGE_EXTENSIONS`, `MAX_CONTENT_LENGTH` | Evidencias |
| SMTP | `MAIL_ENABLED`, `MAIL_SERVER`/`MAIL_HOST`, puerto, TLS/SSL, credenciales, `MAIL_NOTIFY_TO` | Notificaciones |

### 6.2 Decisiones de diseño en `Config`

- Passwords de MySQL/SMTP se limpian de comillas accidentales (`_strip_env_quotes`).
- Usuario/clave se escapan con `quote_plus` al armar la URI.
- `SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}` evita conexiones MySQL “muertas”.
- CSRF siempre habilitado (`WTF_CSRF_ENABLED = True`).

---

## 7. Capa de datos (ORM y MySQL)

Archivo: `app/models.py`.

### 7.1 Modelo conceptual

```
usuarios ──1:1── presencia_usuarios
    │
    ├──1:1── usabilidad_encuestas
    │
    ├──<── solicitudes_mantenimiento ──>── equipos
    │              │
    │              └──<── solicitudes_adjuntos
    │
    └──<── chat_mensajes (como autor o destinatario)
```

### 7.2 Entidades (lógica)

#### `User` → `usuarios`

- Implementa `UserMixin` (Flask-Login).
- `is_superadmin()`: `role == superadmin` **y** `activo`.
- `is_active`: respeta desactivación administrativa.
- Relaciones tipadas con `foreign_keys` porque un usuario puede ser **registrador** o **aprobador**.

#### `Equipo` → `equipos`

- Identidad operativa: `numero_inventario` (único).
- Flags de negocio 2026: `mtto_realizado_1s_2026`, `mtto_realizado_2s_2026`.
- Cascade delete hacia solicitudes (borrar equipo implica limpiar historial asociado en BD).

#### `SolicitudMantenimiento` → `solicitudes_mantenimiento`

Núcleo del flujo:

| Campo | Significado |
|-------|-------------|
| `tipo_origen` | Quién inicia: `usuario` o `tic` |
| `estado` | Máquina de estados del ticket |
| `usuario_aprobador_id` | Destinatario cuando TIC pide aprobación |
| `respuesta_usuario` / fechas | Resultado de `/mis-aprobaciones` |
| `atendido_en` | Cierre operativo por TIC |

#### `SolicitudAdjunto` → `solicitudes_adjuntos`

Metadatos del archivo en disco (`nombre_archivo` aleatorio vs `nombre_original` legible).

#### `UserPresence` → `presencia_usuarios`

- PK = `user_id`.
- `pagina_actual = "__offline__"` marca desconexión explícita (logout / cierre de pestaña).

#### `ChatMensaje` → `chat_mensajes`

- `tipo=area`: visible al área.
- `tipo=susurro`: hilo privado entre dos usuarios.
- Relaciones `autor` / `destinatario`.

#### `UsabilidadEncuesta` → `usabilidad_encuestas`

- Una encuesta por usuario (`user_id` UNIQUE).
- `q1`…`q10` Likert; `score` 0–100.

### 7.3 Loader de sesión

En `extensions.py`, `load_user(user_id)`:

- Valida que el id sea numérico.
- Usa `db.session.get(User, id)`.
- Ante `OperationalError` hace rollback y retorna `None` (sesión inválida sin tumbar la app).

---

## 8. Constantes y dominio de negocio

Archivo: `app/constants.py` — **única fuente de verdad** para strings de negocio.

| Grupo | Ejemplos | Uso |
|-------|----------|-----|
| Áreas | `AREAS_LABORALES` | Registro, filtros, match inventario |
| Roles | `ROLE_USER`, `ROLE_SUPERADMIN` | Autorización |
| Estados solicitud | `ESTADO_SOL_PENDIENTE`, `…_APROBACION`, `…_APROBADA`, `…_DENEGADA`, `…_ATENDIDA` | Máquina de estados |
| Origen | `TIPO_ORIGEN_USUARIO`, `TIPO_ORIGEN_TIC` | Quién creó la solicitud |
| Chat | `CHAT_TIPO_AREA`, `CHAT_TIPO_SUSURRO` | Canales |
| SUS | `SUS_QUESTIONS`, `SUS_LIKERT_CHOICES` | Encuesta |

**Regla:** no hardcodear `"pendiente"` o `"superadmin"` en servicios/rutas si ya existe constante.

### 8.1 Máquina de estados de solicitud

```
                    ┌──────────────┐
   (usuario crea) → │  pendiente   │ ──marcar atendida──► atendida
                    └──────────────┘
                            ▲
                    ┌───────┴────────┐
   (TIC crea)  →    │ pendiente_     │
                    │ aprobacion     │
                    └───────┬────────┘
                 aprobar / denegar
                    ┌───────┴────────┐
                    ▼                ▼
               aprobada          denegada
                    │                │
                    └────┬───────────┘
                         │ (reglas de cierre)
                         ▼
                      atendida
```

- **Denegada “abierta”:** puede seguir visible/accionable hasta la fecha de vigencia (`denegada_sigue_abierta` en `solicitud_service`).

---

## 9. Blueprints y mapa de rutas

### 9.1 `auth` — autenticación

Prefijo: `/auth`. Archivos: `app/auth/routes.py`, `forms.py`, `tokens.py`.

| Método | Ruta | Lógica resumida |
|--------|------|-----------------|
| GET/POST | `/auth/login` | Valida usuario activo + hash; `login_user(remember=True)`; redirect seguro |
| GET/POST | `/auth/logout` | Marca offline + `logout_user` |
| GET/POST | `/auth/registro` | Alta forzada como `user` con validadores corporativos |
| GET/POST | `/auth/recuperar` | Emite token firmado y envía correo (si mail activo) |
| GET/POST | `/auth/restablecer/<token>` | Valida token (24 h) y cambia password |

### 9.2 `main` — portal de usuario + APIs

Sin prefijo. Archivo: `app/main/routes.py`.

| Método | Ruta | Lógica |
|--------|------|--------|
| GET | `/` | Landing; indica SUS pendiente a no-admin |
| GET | `/login` | Alias → auth.login |
| GET/POST | `/registrar-solicitud` | Solo `user`; equipos de su área; crea solicitud + mails |
| GET/POST | `/mis-aprobaciones` | Aprobar/denegar solicitudes TIC pendientes |
| GET/POST | `/usabilidad/encuesta` | Guarda SUS (upsert) |
| GET | `/api/session/ping` | Heartbeat liviano `{ok, boot_id}` |
| GET | `/api/indicators` | Online count + aprobaciones + presencia opcional por IDs |
| GET | `/api/chat/estado` | Historial o delta de mensajes; presencia opcional |
| POST | `/api/chat/enviar` | Crea mensaje área/susurro (CSRF) |
| POST | `/api/presence/offline` | Marca `__offline__` (CSRF / beacon) |

### 9.3 `equipos` — administración TIC

Prefijo: `/equipos`. Gate en `before_request`: autenticado **y** `ROLE_SUPERADMIN`.

| Área | Rutas principales | Lógica |
|------|-------------------|--------|
| Inventario | `/`, `/<id>`, `/<id>/editar` | Listado, detalle mtto 2026, edición/baja |
| Solicitudes | `/solicitudes`, editar/eliminar/resumen/marcar-atendida | Panel operativo TIC |
| Origen TIC | `/<id>/solicitud-tic` | Crea `pendiente_aprobacion` + mail aprobador |
| Export | `/solicitudes/exportar` | CSV o ZIP evidencias |
| Adjuntos | `/adjuntos/<id>` | Sirve archivo con chequeo de path |
| Usuarios | `/usuarios`, `/nuevo`, `/<id>/editar` | CRUD de cuentas |
| Usabilidad | `/usabilidad`, `/api/usabilidad` | Panel HTML + JSON live |

---

## 10. Servicios: lógica de negocio documentada

### 10.1 `solicitud_service.py`

| Función | Responsabilidad |
|---------|-----------------|
| `listar_equipos_por_area_laboral` | Filtra inventario por área del usuario |
| `preparar_evidencias` | Valida extensión/tamaño; genera nombres seguros en disco |
| `crear_solicitud_con_adjuntos` | Persistencia atómica solicitud + adjuntos |
| `crear_solicitud_tic` | Flujo TIC → asigna aprobador y estado |
| `puede_marcar_atendida` | Reglas de cierre según estado/vigencia |
| `etiqueta_estado_solicitud` | Label + clase CSS para badges |
| `denegada_sigue_abierta` | Denegada aún vigente por fecha |
| `aplicar_edicion_admin_solicitud` | Edición forzada por superadmin |
| `eliminar_solicitud_completa` | BD + archivos en disco |

**Lógica clave de área:** un usuario solo puede solicitar mantenimiento sobre equipos cuyo campo `equipos.area` coincide con `usuarios.area`. Eso evita cruces entre departamentos.

### 10.2 `chat_service.py`

| Función | Responsabilidad |
|---------|-----------------|
| `normalizar_area` | Normaliza string de área (fallback “Sin área”) |
| `crear_mensaje_area` / `crear_mensaje_susurro` | Persistencia + commit |
| `historial_reciente` | Últimos N mensajes (límite 50), con `joinedload` |
| `mensajes_desde` | Delta incremental por `id > since_id` (límite 40) |
| `mensaje_a_dict` | Serialización JSON para el front |
| `portal_usuarios_chat_payload` | Delegación a presencia |

**Por qué `joinedload`:** evita N+1 al serializar `autor`/`destinatario` en cada mensaje del poll.

### 10.3 `presence_service.py`

| Función | Responsabilidad |
|---------|-----------------|
| `touch_presence` | UPDATE/INSERT de `last_seen` con **throttle ~18 s** |
| `mark_user_offline` | Marca `__offline__` |
| `count_online_users` | COUNT liviano (ventana ~30 s) |
| `all_portal_users_payload` | Lista completa para panel del chat |
| `users_presence_snapshot` | Estado por IDs (tabla Usuarios) |
| `count_pending_approvals` | Badge de navegación |

**Lógica de “online”:** `last_seen` reciente **y** no marcado offline explícitamente.

### 10.4 `usabilidad_service.py`

| Función | Responsabilidad |
|---------|-----------------|
| `calcular_score_sus` | Fórmula clásica SUS → 0–100 |
| `guardar_encuesta_sus` | Upsert por `user_id` |
| `agregar_sus` | Promedio, bandas, % respuesta |
| `kpis_operativos` | KPIs del día a día + series por estado/área |
| `panel_usabilidad` | Empaqueta SUS + ops + filtros fecha |

**Fórmula SUS (documentada en código):**

- Ítems impares (1,3,5,7,9): contribución = `valor − 1`
- Ítems pares (2,4,6,8,10): contribución = `5 − valor`
- Score = suma × 2.5

### 10.5 `mail.py` + `mail_templates.py`

- Gate global: si `MAIL_ENABLED` es falso, no envía (útil en desarrollo).
- Cuerpos multipart (texto plano + HTML) para clientes corporativos.
- Eventos: nueva solicitud, pendiente aprobación, respuesta usuario, atendida, reset password.

### 10.6 `equipos/inventario_service.py`

- Choices de áreas desde inventario.
- Aplicar formulario de edición.
- Eliminar equipo y limpiar adjuntos en disco.

### 10.7 `validators.py`

Validadores reutilizables:

- Username `nombre.apellido`
- Email dominio `@colbeef.com`
- Política de password (longitud, mayúscula, símbolo, denylist)
- Fechas coherentes
- `flash_form_errors` para UX uniforme

### 10.8 `datetime_utils.py`

- `now_colombia_naive()` para DATETIME MySQL sin tz.
- Formatos humanos de chat y “último acceso”.

---

## 11. Flujos end-to-end

### 11.1 Login

```
Browser → GET/POST /auth/login
       → LoginForm + User(activo) + check_password_hash
       → login_user(remember=True)
       → redirect seguro (_safe_next)
       → siguientes requests: touch_presence (throttle)
```

### 11.2 Usuario registra solicitud

```
GET  /registrar-solicitud  → equipos del área del usuario
POST /registrar-solicitud
   → validar form + evidencias
   → crear_solicitud_con_adjuntos (estado=pendiente, origen=usuario)
   → enviar_correos_nueva_solicitud
   → redirect /
```

### 11.3 TIC solicita aprobación al usuario

```
POST /equipos/<equipo_id>/solicitud-tic
   → crear_solicitud_tic (estado=pendiente_aprobacion)
   → mail al aprobador
Usuario en /mis-aprobaciones
   → aprobar → aprobada (+ fechas) + mail TIC
   → denegar → denegada (vigencia) + mail TIC
TIC puede marcar_atendida según reglas
```

### 11.4 Polling del chat

```
Cada ~2.2 s:
  GET /api/chat/estado?since_id=&modo=&peer_id=&presence=
     → mensajes nuevos (o historial si since_id=0)
     → usuarios online solo si presence=1
POST /api/chat/enviar  (CSRF) → mensaje + force touch presencia
```

### 11.5 Sesión idle / reinicio servidor

```
session-idle.js
  → ping /api/session/ping cada 15 s
  → compara boot_id / detecta caída
  → modal: Continuar | Cerrar sesión
```

### 11.6 Usabilidad

```
Usuario:  POST /usabilidad/encuesta → score SUS guardado
Admin:    GET  /equipos/usabilidad (+ poll /equipos/api/usabilidad)
```

---

## 12. Capa de presentación (HTML/Jinja, CSS, JS)

### 12.1 Jinja2 — herencia

Casi todas las páginas:

```jinja
{% extends "base.html" %}
{% block title %}...{% endblock %}
{% block content %}...{% endblock %}
{% block scripts %}...{% endblock %}
```

`base.html` concentra:

- Nav condicional por rol
- Flash messages
- Chat lateral (si autenticado)
- Modal de sesión
- Scripts globales (`session-idle`, `live-indicators`, `team-chat`)

Macro reutilizable: `macros/nav.html` → `back_link`.

Parcial AJAX: `equipos/_solicitud_resumen.html` (HTML embebido en modal).

### 12.2 CSS

- Archivo único: `app/static/css/app.css`.
- Enfoque: variables CSS (`:root`), componentes con prefijos (`site-nav__*`, `team-chat__*`, `usa-kpi__*`).
- Tipografía: Plus Jakarta Sans.
- Accesibilidad: respeto a `prefers-reduced-motion` donde aplica.

### 12.3 JavaScript — módulos por responsabilidad

Estilo: **IIFE** + `var` + `data-*` inyectados desde Jinja. Sin bundler.

| Archivo | Responsabilidad | Endpoint(s) que consume |
|---------|-----------------|-------------------------|
| `password-toggle.js` | Mostrar/ocultar password | — |
| `session-idle.js` | Idle, reboot, reconnect | `/api/session/ping` |
| `live-indicators.js` | Badge aprobaciones + online + tabla usuarios | `/api/indicators` |
| `team-chat.js` | Chat área/susurro, emojis, presencia | `/api/chat/*`, offline |
| `aprobacion-draft.js` | Borrador en `localStorage` | — |
| `solicitud-detalle.js` | Modal de resumen | `/equipos/solicitudes/<id>/resumen` |
| `usabilidad-live.js` | Refresco panel KPIs/SUS | `/equipos/api/usabilidad` |

**Contrato front↔back:** el HTML declara URLs en atributos (`data-estado-url`, `data-indicators-url`, `data-api-url`). El JS no hardcodea rutas relativas frágiles.

---

## 13. APIs JSON y tiempo real (polling)

El sistema simula tiempo real con **polling** afinado (no WebSocket), priorizando carga baja en MySQL.

| Endpoint | Payload típico | Intervalo cliente |
|----------|----------------|-------------------|
| `/api/session/ping` | `{ok, boot_id}` | 15 s |
| `/api/indicators` | online, pendientes, users? | 8 s |
| `/api/chat/estado` | messages, usuarios?, online_count? | 2.2 s |
| `/equipos/api/usabilidad` | sus + ops | 12 s |

Parámetros relevantes de chat:

- `since_id=0` → historial completo acotado.
- `since_id>0` → solo mensajes nuevos.
- `presence=0|1` → incluir o no el listado pesado de usuarios.
- `modo=area|susurro` + `peer_id` para DM.

---

## 14. Correo electrónico

| Evento | Destinatario | Disparador |
|--------|--------------|------------|
| Nueva solicitud usuario | TIC (`MAIL_NOTIFY_TO`) + confirmación al usuario | `crear_solicitud_con_adjuntos` |
| Solicitud TIC pendiente | Aprobador | `crear_solicitud_tic` |
| Respuesta aprobación/denegación | TIC | `/mis-aprobaciones` |
| Atendida | Registrador | `marcar-atendida` |
| Reset password | Usuario | `/auth/recuperar` |

Diseño: plantillas en `mail_templates.py`; transporte en `mail.py`; desactivable con `MAIL_ENABLED=false`.

---

## 15. Seguridad

| Control | Implementación en código |
|---------|--------------------------|
| CSRF | `CSRFProtect`; POST JSON exige `X-CSRFToken` |
| Autenticación | Flask-Login + `@login_required` |
| Autorización | Blueprint `equipos` exige superadmin |
| Passwords | Hash Werkzeug + `password_policy` |
| Email corporativo | Validador `@colbeef.com` |
| Open redirect | Helpers `_safe_next` / `_safe_*_return` |
| Uploads | Allowlist, tamaño, nombre aleatorio, `relative_to` anti path-traversal |
| Reset | Token firmado, salt dedicado, 24 h |
| Sesión | Idle modal + `APP_BOOT_ID` + heartbeat |
| Offline | Logout + `sendBeacon` a `/api/presence/offline` |
| DB | `pool_pre_ping` |

**Buenas prácticas operativas:** no versionar `.env`; rotar seeds SQL de superadmin en producción; usar `SECRET_KEY` fuerte.

---

## 16. Rendimiento y optimizaciones

| Problema | Solución implementada |
|----------|----------------------|
| UPDATE presencia en cada request | Throttle ~18 s en `touch_presence` |
| Poll de sesión golpeando chat completo | Endpoint `/api/session/ping` liviano |
| N+1 en chat | `joinedload` autor/destinatario |
| N+1 adjuntos en listado | `GROUP BY` batch en `solicitudes_lista` |
| COUNT aprobaciones en cada poll | Skip en context processor para `/api/*` |
| Re-render innecesario del chat | Firma de presencia en JS; presencia cada N ticks |
| Panel usabilidad pesado | API JSON + poll solo en esa página |

---

## 17. Migraciones y despliegue de base de datos

### Orden obligatorio

| # | Archivo SQL | Efecto |
|---|-------------|--------|
| 01 | `01_crear_base_y_tabla.sql` | BD + `equipos` |
| 02 | `02_usuario_app.sql` | GRANT usuario app (opcional) |
| 03 | `03_solicitudes_mantenimiento.sql` | Solicitudes + adjuntos |
| 04 | `04_auth_usuarios.sql` | `usuarios` + seed |
| 05 | `05_aprobacion_tic_presencia.sql` | Flujo TIC + presencia |
| 06 | `06_chat_mensajes.sql` | Chat base |
| 07 | `07_email_no_unico.sql` | Email sin UNIQUE |
| 08 | `08_chat_area_susurro.sql` | Área + susurro |
| 09 | `09_usabilidad_sus.sql` | Encuestas SUS |

Scripts espejo: `scripts/aplicar_migracion_03.py` … `09_usabilidad.py`.  
Import inventario: `scripts/import_inventario_csv.py`.  
Chequeo: `database/verificar_datos.sql`.

### Arranque local recomendado

1. Copiar `.env.example` → `.env` y completar.
2. Aplicar migraciones en orden.
3. (Opcional) Importar CSV de inventario.
4. `pip install -r requirements.txt`
5. `python run.py`

---

## 18. Convenciones de código

| Área | Convención |
|------|------------|
| Python | `snake_case` funciones/vars; `PascalCase` clases; type hints donde aporta |
| Rutas | Verbos claros (`solicitud_marcar_atendida`, `api_indicators`) |
| Dominio | Strings solo vía `constants.py` |
| Errores de form | `flash_form_errors(form)` |
| Servicios | Retornos `(resultado, error)` cuando hay fallo recuperable |
| Templates | Español UI; bloques estándar de `base.html` |
| JS | IIFE aisladas; sin contaminar `window` salvo necesidad |
| CSS | Prefijos de componente; evitar estilos inline salvo dinámicos (barras KPI) |
| Commits | Mensajes en español orientados al *porqué* |

---

## 19. Guía para extender el sistema

| Necesidad | Dónde tocar |
|-----------|-------------|
| Nueva pantalla de usuario | `main/routes.py` + template + form opcional |
| Nueva pantalla solo TIC | `equipos/routes.py` (ya gated) |
| Nueva regla de negocio | Servicio de dominio (no la ruta) |
| Nuevo estado / área / rol | `constants.py` → migración SQL → modelo → forms/UI |
| Nueva tabla | `database/10_*.sql` + script aplicar + modelo ORM |
| Nuevo correo | `mail_templates.py` + función en `mail.py` |
| Nuevo indicador live | Extender `/api/indicators` + `live-indicators.js` |
| Nueva config | `.env.example` + `Config` |
| Nuevo blueprint | Paquete Flask + `register_blueprint` en `create_app` |

**Checklist senior antes de merge:**

1. ¿La lógica quedó en servicio y no en la ruta?
2. ¿Hay constante de dominio en lugar de string mágico?
3. ¿CSRF / auth / rol cubiertos?
4. ¿Evita N+1 y trabajo en cada poll?
5. ¿Documentó migración SQL si cambia el esquema?

---

## 20. Glosario

| Término | Significado en este proyecto |
|---------|------------------------------|
| **SUS** | System Usability Scale (encuesta 10 ítems → score 0–100) |
| **Susurro** | Mensaje privado entre dos usuarios del chat |
| **Origen TIC** | Solicitud iniciada por superadmin hacia un aprobador de área |
| **Boot ID** | Identificador por arranque del proceso Flask |
| **Throttle de presencia** | No escribir `last_seen` en cada HTTP; mínimo ~18 s |
| **Denegada abierta** | Denegación aún vigente por fecha; sigue requiriendo seguimiento |
| **Application Factory** | Función `create_app()` que construye la app Flask configurable |

---

## Anexo A — Inventario de archivos de código fuente

### Python de aplicación

`app/__init__.py`, `config.py`, `extensions.py`, `models.py`, `constants.py`, `validators.py`, `datetime_utils.py`, `solicitud_service.py`, `solicitud_export.py`, `chat_service.py`, `presence_service.py`, `usabilidad_service.py`, `mail.py`, `mail_templates.py`, `auth/*`, `main/*`, `equipos/*`, `run.py`, `wsgi.py`

### Front

Templates bajo `app/templates/**`, estilos `app/static/css/app.css`, scripts `app/static/js/*.js`

### Datos

`database/01`…`09`, `verificar_datos.sql`, `scripts/aplicar_migracion_*.py`, `import_inventario_csv.py`

---

## Anexo B — Resumen ejecutivo (una página)

Mtto equipos es un **monolito Flask** sobre **MySQL** que combina inventario, solicitudes de mantenimiento (doble flujo), chat interno, presencia y usabilidad SUS. El código se organiza por **blueprints** (HTTP) y **servicios** (negocio). El front es **Jinja + CSS + JS vanilla** con polling. La seguridad se apoya en CSRF, roles, validadores corporativos y uploads controlados. La evolución del esquema es **SQL versionado (01–09)**. Este documento es la referencia senior para entender, auditar y extender el sistema.

---

*Documento de código — Mtto equipos. Reemplaza la versión anterior de `docs/DOCUMENTACION_TECNICA.md`. Mantener alineado con `main` cuando cambien rutas, modelos o contratos de API.*
