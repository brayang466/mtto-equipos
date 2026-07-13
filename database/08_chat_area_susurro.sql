-- Chat por área y mensajes privados (susurro)
-- Ejecutar: python scripts/aplicar_migracion_08_chat_area.py

USE mtto_equipos;

ALTER TABLE chat_mensajes
  ADD COLUMN tipo VARCHAR(20) NOT NULL DEFAULT 'area' COMMENT 'area | susurro' AFTER texto,
  ADD COLUMN area VARCHAR(64) NULL COMMENT 'Área laboral del canal' AFTER tipo,
  ADD COLUMN destinatario_id BIGINT UNSIGNED NULL COMMENT 'Usuario destino en susurro' AFTER area;

ALTER TABLE chat_mensajes
  ADD KEY idx_chat_area (tipo, area, id),
  ADD KEY idx_chat_susurro (tipo, destinatario_id, user_id, id),
  ADD CONSTRAINT fk_chat_destinatario FOREIGN KEY (destinatario_id) REFERENCES usuarios (id) ON DELETE CASCADE;

-- Mensajes existentes: asignar área del autor
UPDATE chat_mensajes cm
JOIN usuarios u ON u.id = cm.user_id
SET cm.tipo = 'area', cm.area = u.area
WHERE cm.area IS NULL;
