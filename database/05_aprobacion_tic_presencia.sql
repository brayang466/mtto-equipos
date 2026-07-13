-- Aprobación de mantenimiento iniciada por TIC + presencia de usuarios en línea
-- Ejecutar: python scripts/aplicar_migracion_05_aprobacion.py

USE mtto_equipos;

ALTER TABLE solicitudes_mantenimiento
  ADD COLUMN tipo_origen VARCHAR(20) NOT NULL DEFAULT 'usuario' COMMENT 'usuario | tic' AFTER registrado_por_user_id,
  ADD COLUMN usuario_aprobador_id BIGINT UNSIGNED NULL AFTER tipo_origen,
  ADD COLUMN fecha_respuesta_usuario DATE NULL AFTER fecha_mantenimiento,
  ADD COLUMN respuesta_usuario VARCHAR(20) NULL COMMENT 'aprobada | denegada' AFTER fecha_respuesta_usuario,
  ADD COLUMN comentario_respuesta TEXT NULL AFTER respuesta_usuario;

ALTER TABLE solicitudes_mantenimiento
  ADD KEY idx_sol_aprobador (usuario_aprobador_id),
  ADD CONSTRAINT fk_sol_aprobador FOREIGN KEY (usuario_aprobador_id) REFERENCES usuarios (id) ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS presencia_usuarios (
  user_id BIGINT UNSIGNED NOT NULL,
  last_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  pagina_actual VARCHAR(255) NULL,
  PRIMARY KEY (user_id),
  KEY idx_presencia_last_seen (last_seen),
  CONSTRAINT fk_presencia_user FOREIGN KEY (user_id) REFERENCES usuarios (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
