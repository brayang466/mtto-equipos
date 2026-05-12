-- Ejecute esto en MySQL Workbench en la MISMA conexión (host/puerto) que usa el script Python.
-- Debe ver total > 0 después de una importación correcta.

USE mtto_equipos;

SELECT DATABASE() AS esquema_actual;
SELECT COUNT(*) AS total_filas_equipos FROM equipos;
SELECT numero_inventario, numero_contable, usuario, departamento
FROM equipos
ORDER BY CAST(numero_inventario AS UNSIGNED)
LIMIT 10;
