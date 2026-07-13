-- =============================================================================
-- Usuarios (login / roles) + ampliación solicitudes_mantenimiento
-- Ejecutar después de 03_solicitudes_mantenimiento.sql
--   mysql -u admin -p mtto_equipos < 04_auth_usuarios.sql
--   o: python scripts/aplicar_migracion_04_auth.py
-- =============================================================================

USE mtto_equipos;

CREATE TABLE IF NOT EXISTS usuarios (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  username VARCHAR(80) NOT NULL COMMENT 'nombre.apellido en minúsculas',
  email VARCHAR(255) NOT NULL COMMENT 'Correo @colbeef.com',
  password_hash VARCHAR(255) NOT NULL,
  area VARCHAR(64) NOT NULL,
  role VARCHAR(20) NOT NULL DEFAULT 'user' COMMENT 'user | superadmin',
  activo TINYINT(1) NOT NULL DEFAULT 1,
  creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_usuarios_username (username),
  UNIQUE KEY uk_usuarios_email (email),
  KEY idx_usuarios_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE solicitudes_mantenimiento
  ADD COLUMN registrado_por_user_id BIGINT UNSIGNED NULL AFTER equipo_id,
  ADD COLUMN estado VARCHAR(20) NOT NULL DEFAULT 'pendiente' COMMENT 'pendiente | atendida' AFTER observaciones,
  ADD COLUMN atendido_en DATETIME NULL AFTER estado,
  ADD KEY idx_sol_estado (estado),
  ADD KEY idx_sol_reg_user (registrado_por_user_id),
  ADD CONSTRAINT fk_sol_reg_user FOREIGN KEY (registrado_por_user_id) REFERENCES usuarios (id) ON DELETE SET NULL;

-- Superadmin inicial (contraseña: Pricetag1** — cámbiela tras el primer acceso)
INSERT INTO usuarios (username, email, password_hash, area, role) VALUES (
  'brayan.gomez',
  'tecnologia@colbeef.com',
  'scrypt:32768:8:1$sKkoCyHLDvXz9neg$ddc6664bb36366e3eb974894d8acc0cbd7cf57231893f383bfb00456a27442e670a01646a06557f4c395139710e49f162004ddac541ee268690e47b711cf7e74',
  'TIC',
  'superadmin'
) ON DUPLICATE KEY UPDATE
  email = VALUES(email),
  password_hash = VALUES(password_hash),
  area = VALUES(area),
  role = VALUES(role);
