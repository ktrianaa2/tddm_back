-- Tabla de roles
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    descripcion TEXT,
    activo BOOLEAN DEFAULT TRUE
);

-- Tabla de datos personales  
CREATE TABLE datos_personales (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    activo BOOLEAN DEFAULT TRUE
);

-- Tabla de usuarios (relacionada con las dos anteriores)
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    usuario VARCHAR(50) NOT NULL UNIQUE,
    contrasenia VARCHAR(255) NOT NULL,
    datos_personales_id INTEGER NOT NULL REFERENCES datos_personales(id),
    rol_id INTEGER NOT NULL REFERENCES roles(id),
    activo BOOLEAN DEFAULT TRUE
);

-- Tabla de tipos de requisitos
CREATE TABLE tipos_requisito (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    descripcion TEXT,
    activo BOOLEAN DEFAULT TRUE
);

-- Tabla de prioridades
CREATE TABLE prioridades (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    nivel INTEGER NOT NULL UNIQUE,
    descripcion TEXT,
    activo BOOLEAN DEFAULT TRUE
);

-- Tabla de estados de proyecto
CREATE TABLE estados_proyecto (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    descripcion TEXT,
    orden INTEGER NOT NULL UNIQUE,
    activo BOOLEAN DEFAULT TRUE
);

-- Tabla de estados de elementos (requisitos, casos de uso, historias)
-- MODIFICACIÓN: Se elimina la restricción UNIQUE del campo nombre
CREATE TABLE estados_elemento (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL,
    descripcion TEXT,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('requisito', 'caso_uso', 'historia_usuario')),
    activo BOOLEAN DEFAULT TRUE,
    -- restricción única compuesta
    UNIQUE(nombre, tipo)
);

-- Tabla de tipos de relación entre casos de uso
CREATE TABLE tipos_relacion_cu (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    descripcion TEXT,
    activo BOOLEAN DEFAULT TRUE
);

-- Tabla de tipos de relación entre requisitos
CREATE TABLE tipos_relacion_requisito (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    descripcion TEXT,
    activo BOOLEAN DEFAULT TRUE
);

-- Tabla de tipos de estimación
CREATE TABLE tipos_estimacion (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,  -- story-points, horas, días, costo
    descripcion TEXT,
    activo BOOLEAN DEFAULT TRUE
);

-- Tabla relación entre historia de usuario y estimaciones
CREATE TABLE historias_estimaciones (
    id SERIAL PRIMARY KEY,
    historia_id INTEGER NOT NULL REFERENCES historias_usuario(id) ON DELETE CASCADE,
    tipo_estimacion_id INTEGER NOT NULL REFERENCES tipos_estimacion(id),
    valor NUMERIC(10,2) NOT NULL, -- puede ser puntos, horas, días o costo en $
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activo BOOLEAN DEFAULT TRUE,
    UNIQUE(historia_id, tipo_estimacion_id) -- Evita duplicados para un mismo tipo en una historia
);

-- Tabla de proyectos
CREATE TABLE proyectos (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    estado VARCHAR(50) DEFAULT 'Requisitos',
    fecha_creacion DATE DEFAULT CURRENT_DATE,
    fecha_actualizacion DATE DEFAULT CURRENT_DATE,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    activo BOOLEAN DEFAULT TRUE
);

-- Tabla de casos de uso
CREATE TABLE casos_uso (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    actores TEXT NOT NULL,
    precondiciones TEXT NOT NULL,
    flujo_principal JSONB,
    flujos_alternativos JSONB,
    postcondiciones TEXT,
    requisitos_especiales TEXT,
    riesgos_consideraciones TEXT,
    proyecto_id INTEGER NOT NULL REFERENCES proyectos(id),
    prioridad_id INTEGER REFERENCES prioridades(id),
    estado_id INTEGER REFERENCES estados_elemento(id),
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activo BOOLEAN DEFAULT TRUE
);

-- Tabla de historias de usuario
CREATE TABLE historias_usuario (
    id SERIAL PRIMARY KEY,
    titulo VARCHAR(200) NOT NULL,
    descripcion TEXT,
    actor_rol VARCHAR(100),
    funcionalidad_accion VARCHAR(200),
    beneficio_razon VARCHAR(200),
    criterios_aceptacion TEXT NOT NULL,
    prioridad_id INTEGER REFERENCES prioridades(id),
    estado_id INTEGER REFERENCES estados_elemento(id),
    valor_negocio INTEGER CHECK (valor_negocio >= 1 AND valor_negocio <= 100),
    dependencias_relaciones TEXT,
    componentes_relacionados VARCHAR(200),
    notas_adicionales TEXT,
    proyecto_id INTEGER NOT NULL REFERENCES proyectos(id),
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activo BOOLEAN DEFAULT TRUE
);

-- Tabla de requisitos
CREATE TABLE requisitos (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    descripcion TEXT NOT NULL,
    tipo_id INTEGER NOT NULL REFERENCES tipos_requisito(id),
    criterios TEXT NOT NULL,
    prioridad_id INTEGER REFERENCES prioridades(id),
    estado_id INTEGER REFERENCES estados_elemento(id),
    origen VARCHAR(100),
    condiciones_previas TEXT,
    proyecto_id INTEGER NOT NULL REFERENCES proyectos(id),
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activo BOOLEAN DEFAULT TRUE
);

-- Tabla de relaciones entre casos de uso
CREATE TABLE relaciones_casos_uso (
    id SERIAL PRIMARY KEY,
    caso_uso_origen_id INTEGER NOT NULL REFERENCES casos_uso(id),
    caso_uso_destino_id INTEGER NOT NULL REFERENCES casos_uso(id),
    tipo_relacion_id INTEGER NOT NULL REFERENCES tipos_relacion_cu(id),
    descripcion TEXT,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activo BOOLEAN DEFAULT TRUE,
    CONSTRAINT check_different_cu CHECK (caso_uso_origen_id != caso_uso_destino_id)
);

-- Tabla de relaciones entre requisitos
CREATE TABLE relaciones_requisitos (
    id SERIAL PRIMARY KEY,
    requisito_origen_id INTEGER NOT NULL REFERENCES requisitos(id),
    requisito_destino_id INTEGER NOT NULL REFERENCES requisitos(id),
    tipo_relacion_id INTEGER NOT NULL REFERENCES tipos_relacion_requisito(id),
    descripcion TEXT,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activo BOOLEAN DEFAULT TRUE,
    CONSTRAINT check_different_requisitos CHECK (requisito_origen_id != requisito_destino_id)
);

-- Tabla de relación entre casos de uso y requisitos
CREATE TABLE casos_uso_requisitos (
    id SERIAL PRIMARY KEY,
    caso_uso_id INTEGER NOT NULL REFERENCES casos_uso(id),
    requisito_id INTEGER NOT NULL REFERENCES requisitos(id),
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activo BOOLEAN DEFAULT TRUE,
    UNIQUE(caso_uso_id, requisito_id)
);

-- Tabla de relación entre historias de usuario y requisitos
CREATE TABLE historias_requisitos (
    id SERIAL PRIMARY KEY,
    historia_id INTEGER NOT NULL REFERENCES historias_usuario(id),
    requisito_id INTEGER NOT NULL REFERENCES requisitos(id),
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activo BOOLEAN DEFAULT TRUE,
    UNIQUE(historia_id, requisito_id)
);


-- Insertar algunos roles básicos
INSERT INTO roles (nombre, descripcion) VALUES 
('admin', 'Administrador del sistema'),
('usuario', 'Usuario regular');

-- Insertar tipos de requisitos (con activo)
INSERT INTO tipos_requisito (nombre, descripcion, activo) VALUES 
('funcional', 'Requisitos que definen funciones específicas del sistema', TRUE),
('no-funcional', 'Requisitos relacionados con calidad, rendimiento, seguridad, etc.', TRUE),
('negocio', 'Requisitos relacionados con objetivos de negocio', TRUE),
('tecnico', 'Requisitos técnicos de implementación', TRUE),
('sistema', 'Requisitos generales del sistema', TRUE),
('interfaz', 'Requisitos de interfaz de usuario', TRUE);

-- Insertar prioridades (con activo)
INSERT INTO prioridades (nombre, nivel, descripcion, activo) VALUES 
('muy-alta', 1, 'Prioridad muy alta - Crítico para el proyecto', TRUE),
('alta', 2, 'Prioridad alta - Importante para el proyecto', TRUE),
('media', 3, 'Prioridad media - Necesario pero no urgente', TRUE),
('baja', 4, 'Prioridad baja - Deseable pero no esencial', TRUE),
('muy-baja', 5, 'Prioridad muy baja - Podría considerarse en el futuro', TRUE);

-- Insertar estados de proyecto (sin cambios porque no tiene campo activo)
INSERT INTO estados_proyecto (nombre, descripcion, orden) VALUES 
('requisitos', 'Fase de definición de requisitos', 1),
('analisis', 'Fase de análisis y diseño', 2),
('desarrollo', 'Fase de desarrollo', 3),
('pruebas', 'Fase de pruebas', 4),
('implementacion', 'Fase de implementación', 5),
('finalizado', 'Proyecto finalizado', 6),
('cancelado', 'Proyecto cancelado', 7);

-- Insertar tipos de relación entre casos de uso (sin cambios)
INSERT INTO tipos_relacion_cu (nombre, descripcion) VALUES 
('include', 'El CU incluye obligatoriamente otro CU'),
('extend', 'El CU puede extender otro CU bajo condiciones'),
('generalizacion', 'El CU es una especialización de otro CU padre'),
('dependencia', 'El CU depende de otro CU para su ejecución');

-- Insertar tipos de relación entre requisitos (con activo)
INSERT INTO tipos_relacion_requisito (nombre, descripcion, activo) VALUES 
('depende', 'Este requisito depende del requisito relacionado', TRUE),
('bloquea', 'Este requisito bloquea al requisito relacionado', TRUE),
('conflicto', 'Este requisito está en conflicto con el relacionado', TRUE),
('complementa', 'Este requisito complementa al requisito relacionado', TRUE),
('deriva', 'Este requisito deriva del requisito relacionado', TRUE),
('refina', 'Este requisito refina al requisito relacionado', TRUE);

-- Insertar estados para elementos (con activo)
-- Estados para requisitos
INSERT INTO estados_elemento (nombre, descripcion, tipo, activo) VALUES 
('pendiente', 'Requisito pendiente de revisión', 'requisito', TRUE),
('aprobado', 'Requisito aprobado para implementación', 'requisito', TRUE),
('en-desarrollo', 'Requisito en desarrollo', 'requisito', TRUE),
('implementado', 'Requisito implementado', 'requisito', TRUE),
('rechazado', 'Requisito rechazado', 'requisito', TRUE),
('postpuesto', 'Requisito postpuesto para una fase posterior', 'requisito', TRUE);

-- Estados para casos de uso
INSERT INTO estados_elemento (nombre, descripcion, tipo, activo) VALUES 
('pendiente', 'Caso de uso pendiente de revisión', 'caso_uso', TRUE),
('aprobado', 'Caso de uso aprobado', 'caso_uso', TRUE),
('en-analisis', 'Caso de uso en análisis', 'caso_uso', TRUE),
('desarrollado', 'Caso de uso desarrollado', 'caso_uso', TRUE),
('probado', 'Caso de uso probado', 'caso_uso', TRUE),
('rechazado', 'Caso de uso rechazado', 'caso_uso', TRUE);

-- Estados para historias de usuario
INSERT INTO estados_elemento (nombre, descripcion, tipo, activo) VALUES 
('pendiente', 'Historia de usuario pendiente', 'historia_usuario', TRUE),
('en-progreso', 'Historia de usuario en progreso', 'historia_usuario', TRUE),
('completada', 'Historia de usuario completada', 'historia_usuario', TRUE),
('bloqueada', 'Historia de usuario bloqueada', 'historia_usuario', TRUE),
('rechazada', 'Historia de usuario rechazada', 'historia_usuario', TRUE);

-- Insertar los tipos de estimación básicos
INSERT INTO tipos_estimacion (nombre, descripcion, activo) VALUES
('story-points', 'Estimación relativa en puntos de historia', TRUE),
('horas', 'Estimación en horas de esfuerzo', TRUE),
('dias', 'Estimación en días de esfuerzo', TRUE),
('costo', 'Estimación en costo monetario', TRUE);

-- Insertar datos personales
INSERT INTO datos_personales (nombre, apellido)
VALUES 
('Admin', 'Principal'),  -- id = 1
('Usuario', 'Regular');  -- id = 2

-- Insertar usuario ADMIN (rol_id = 1)
INSERT INTO usuarios (usuario, contrasenia, datos_personales_id, rol_id, activo)
VALUES (
    'admin',
    'pbkdf2_sha256$720000$nA1DBiCSy5A4HPTMAfMGDx$MmlhOsKKop+XKgi48HY1WYVShwtU6vD1/nsc8bnk2Zo=',
    1,
    1,
    TRUE
);

-- Insertar usuario REGULAR (rol_id = 2)
INSERT INTO usuarios (usuario, contrasenia, datos_personales_id, rol_id, activo)
VALUES (
    'usuario',
    'pbkdf2_sha256$720000$nA1DBiCSy5A4HPTMAfMGDx$MmlhOsKKop+XKgi48HY1WYVShwtU6vD1/nsc8bnk2Zo=',
    2,
    2,
    TRUE
);

-- Si tienen tablas en postgres y quieren traerlas al backend, pueden usar el siguiente comando:
-- python manage.py inspectdb > models.py


-- Crear un archivo de requerimientos para el proyecto
-- pip freeze > requirements.txt   