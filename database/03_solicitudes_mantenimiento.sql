-- =============================================================================
-- Solicitudes de mantenimiento (usuario informa necesidad + fechas + evidencias)
-- Ejecutar después de 01_crear_base_y_tabla.sql:
--   mysql -u admin -p mtto_equipos < 03_solicitudes_mantenimiento.sql
-- =============================================================================

USE mtto_equipos;

CREATE TABLE IF NOT EXISTS solicitudes_mantenimiento (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  equipo_id BIGINT UNSIGNED NOT NULL,
  fecha_solicitud DATE NOT NULL COMMENT 'Cuando el usuario registra la solicitud',
  fecha_mantenimiento DATE NULL COMMENT 'Fecha prevista o posible para ejecutar el mantenimiento',
  observaciones TEXT NULL,
  creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_equipo (equipo_id),
  KEY idx_creado (creado_en),
  CONSTRAINT fk_sol_equipo FOREIGN KEY (equipo_id) REFERENCES equipos (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS solicitudes_adjuntos (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  solicitud_id BIGINT UNSIGNED NOT NULL,
  nombre_archivo VARCHAR(255) NOT NULL COMMENT 'Nombre único en disco',
  nombre_original VARCHAR(512) NOT NULL,
  mime VARCHAR(128) NULL,
  tamano_bytes BIGINT UNSIGNED NULL,
  creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_solicitud (solicitud_id),
  CONSTRAINT fk_adj_sol FOREIGN KEY (solicitud_id) REFERENCES solicitudes_mantenimiento (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
