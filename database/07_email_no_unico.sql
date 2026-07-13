-- Permite correos repetidos en usuarios (solo username sigue siendo único)
-- Ejecutar: python scripts/aplicar_migracion_07_email_duplicado.py

USE mtto_equipos;

ALTER TABLE usuarios DROP INDEX uk_usuarios_email;

-- Superadmin inicial (contraseña: Pricetag1** — cámbiela tras el primer acceso)
INSERT INTO usuarios (username, email, password_hash, area, role, activo) VALUES (
  'brayan.gomez',
  'tecnologia@colbeef.com',
  'scrypt:32768:8:1$sKkoCyHLDvXz9neg$ddc6664bb36366e3eb974894d8acc0cbd7cf57231893f383bfb00456a27442e670a01646a06557f4c395139710e49f162004ddac541ee268690e47b711cf7e74',
  'TIC',
  'superadmin',
  1
) ON DUPLICATE KEY UPDATE
  email = VALUES(email),
  password_hash = VALUES(password_hash),
  area = VALUES(area),
  role = VALUES(role),
  activo = VALUES(activo);
