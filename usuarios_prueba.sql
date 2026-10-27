-- =============================================================
--  usuarios_prueba.sql · Cuentas de prueba de Calidashboard
--  Contraseña de TODAS las cuentas: Prueba12345
--  Solo para practicar: no las uses en un sistema real.
--  INSERT IGNORE: se puede correr varias veces sin duplicar usuarios.
--  Requiere que la tabla "usuarios" ya tenga la columna "rol".
-- =============================================================
INSERT IGNORE INTO usuarios (nombre, usuario, correo, password_hash, rol, creado) VALUES
  ('Marta Flores', 'mflores', 'mflores@calidashboard.local',
   'pbkdf2:sha256:1000000$VD0kjX8Et38niG0A$5c52e7d6d8fa223f91bd2b04f937d02aa9dee84b4f122e28f0993c7ea1fd55f8',
   'supervisor', NOW()),
  ('Luis Ortiz', 'lortiz', 'lortiz@calidashboard.local',
   'pbkdf2:sha256:1000000$G3sr2sbMs3LCSoYG$4bac0941f938aacda6be228726fecce43e9f3f5b8f6787f914ede537db7bd307',
   'supervisor', NOW()),
  ('Ana López', 'alopez', 'alopez@calidashboard.local',
   'pbkdf2:sha256:1000000$LWFd9Ldtqv7QOio1$1a615987bbf33ec5c681ecb66609cf07632e3266ad9c68e5a08ba352cfa77e8b',
   'tecnico', NOW()),
  ('Carlos Méndez', 'cmendez', 'cmendez@calidashboard.local',
   'pbkdf2:sha256:1000000$Pw0H5CdlfjElcVkS$420d1588737abf654db1b64d23ecb94b868c82cab1e5587ebd5b1b29fcb23e88',
   'tecnico', NOW()),
  ('Sofía Ramírez', 'sramirez', 'sramirez@calidashboard.local',
   'pbkdf2:sha256:1000000$uRS9OYMoYYV6fpQt$67869da96036e687c446eeef306a2718aa5d684babe270147b473634c2325589',
   'tecnico', NOW());

-- Comprobar:
SELECT id, nombre, usuario, rol FROM usuarios ORDER BY rol, usuario;
