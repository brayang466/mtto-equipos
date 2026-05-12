-- =============================================================================
-- Usuario dedicado para la aplicación (ejecutar con cuenta administradora)
--
-- 1) Elija una contraseña fuerte y reemplace CAMBIE_ESTA_CLAVE
-- 2) Ajuste el host: 'localhost' para app en el mismo servidor, o IP/% según política
-- =============================================================================

-- CREATE USER IF NOT EXISTS 'mtto_app'@'localhost' IDENTIFIED BY 'CAMBIE_ESTA_CLAVE';
-- GRANT SELECT, INSERT, UPDATE, DELETE ON mtto_equipos.* TO 'mtto_app'@'localhost';

-- Si la app Flask está en otro servidor y se conecta por red (valorar firewall/VPC):
-- CREATE USER IF NOT EXISTS 'mtto_app'@'%' IDENTIFIED BY 'CAMBIE_ESTA_CLAVE';
-- GRANT SELECT, INSERT, UPDATE, DELETE ON mtto_equipos.* TO 'mtto_app'@'%';

-- FLUSH PRIVILEGES;

-- Nota: descomente las líneas que correspondan a su despliegue y elimine las que no use.
