-- =============================================================================
-- Inventario de equipos + control mantenimiento preventivo 2026
-- MySQL 8.0+ (utf8mb4)
--
-- Uso sugerido (consola): mysql -u root -p < 01_crear_base_y_tabla.sql
--
-- Sobre "que siempre pida contraseña":
--   MySQL no muestra un cuadro de diálogo por sí solo; es el cliente (Workbench,
--   DBeaver, línea de comandos) quien guarda o no la contraseña.
--   - No cree un archivo .my.cnf con la clave en texto plano.
--   - En MySQL Workbench: conexión sin "Store in Keychain" / no guardar contraseña.
--   - En terminal: use siempre  mysql -u usuario -p  (el -p sin valor fuerza prompt).
--
-- Cree además un usuario de aplicación con clave obligatoria (ver 02_usuario_app.sql).
-- =============================================================================

CREATE DATABASE IF NOT EXISTS mtto_equipos
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE mtto_equipos;

CREATE TABLE IF NOT EXISTS equipos (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  numero_inventario VARCHAR(32) NOT NULL COMMENT 'Número de inventario del CSV',
  numero_contable VARCHAR(64) NULL,
  codigo_contable VARCHAR(64) NULL,
  departamento VARCHAR(255) NULL,
  area VARCHAR(255) NULL,
  usuario VARCHAR(512) NULL,
  cargo VARCHAR(255) NULL,
  descripcion VARCHAR(255) NULL,
  marca_referencia VARCHAR(512) NULL,
  service_tag VARCHAR(255) NULL COMMENT 'Service Tag Dell o Product Name',
  serial_cpu VARCHAR(255) NULL COMMENT 'Serial CPU o Express code',
  fecha_adquisicion DATE NULL,
  observaciones TEXT NULL COMMENT 'Campo OBSERVACIONES principal del inventario',
  mtto_realizado_1s_2026 TINYINT(1) NOT NULL DEFAULT 0 COMMENT 'Mantenimiento realizado 1er semestre 2026',
  mtto_realizado_2s_2026 TINYINT(1) NOT NULL DEFAULT 0 COMMENT 'Mantenimiento realizado 2do semestre 2026',
  creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_numero_inventario (numero_inventario),
  KEY idx_departamento (departamento(100)),
  KEY idx_usuario (usuario(100)),
  KEY idx_mtto_2026 (mtto_realizado_1s_2026, mtto_realizado_2s_2026)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
