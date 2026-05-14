-- ============================================
-- TABLAS BASE
-- ============================================

-- Tabla de roles
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    descripcion TEXT,
    color VARCHAR(7) NOT NULL DEFAULT '#6B7280',
    activo BOOLEAN DEFAULT TRUE
);

-- Tabla de datos personales  
CREATE TABLE datos_personales (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    activo BOOLEAN DEFAULT TRUE
);

-- Tabla de tipos de requisitos
CREATE TABLE tipos_requisito (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    descripcion TEXT,
    color VARCHAR(7) NOT NULL DEFAULT '#6B7280',
    activo BOOLEAN DEFAULT TRUE
);

-- Tabla de prioridades
CREATE TABLE prioridades (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    nivel INTEGER NOT NULL UNIQUE,
    descripcion TEXT,
    color VARCHAR(7) NOT NULL DEFAULT '#6B7280',
    activo BOOLEAN DEFAULT TRUE
);

-- Tabla de estados de proyecto
CREATE TABLE estados_proyecto (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    descripcion TEXT,
    orden INTEGER NOT NULL UNIQUE,
    color VARCHAR(7) NOT NULL DEFAULT '#6B7280',
    activo BOOLEAN DEFAULT TRUE
);

-- Tabla de estados de elementos (requisitos, casos de uso, historias)
CREATE TABLE estados_elemento (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL,
    descripcion TEXT,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('requisito', 'caso_uso', 'historia_usuario')),
    color VARCHAR(7) NOT NULL DEFAULT '#6B7280',
    activo BOOLEAN DEFAULT TRUE,
    UNIQUE(nombre, tipo)
);

-- Tabla de tipos de relación entre casos de uso
CREATE TABLE tipos_relacion_cu (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    descripcion TEXT,
    color VARCHAR(7) NOT NULL DEFAULT '#6B7280',
    activo BOOLEAN DEFAULT TRUE
);

-- Tabla de tipos de relación entre requisitos
CREATE TABLE tipos_relacion_requisito (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    descripcion TEXT,
    color VARCHAR(7) NOT NULL DEFAULT '#6B7280',
    activo BOOLEAN DEFAULT TRUE
);

-- Tabla de tipos de estimación
CREATE TABLE tipos_estimacion (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    descripcion TEXT,
    color VARCHAR(7) NOT NULL DEFAULT '#6B7280',
    activo BOOLEAN DEFAULT TRUE
);

-- Tabla de tipos de pruebas
CREATE TABLE tipos_prueba (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    descripcion TEXT,
    color VARCHAR(7) NOT NULL DEFAULT '#6B7280',
    activo BOOLEAN DEFAULT TRUE
);

-- NUEVA: Tabla de tipos de motor de base de datos
CREATE TABLE tipos_motor_bd (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    descripcion TEXT,
    extension_archivo VARCHAR(10),
    sintaxis_especifica TEXT,
    color VARCHAR(7) NOT NULL DEFAULT '#6B7280',
    activo BOOLEAN DEFAULT TRUE
);

-- ============================================
-- TABLAS CON DEPENDENCIAS NIVEL 1
-- ============================================

-- Tabla de usuarios (depende de roles y datos_personales)
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    usuario VARCHAR(50) NOT NULL UNIQUE,
    contrasenia VARCHAR(255) NOT NULL,
    datos_personales_id INTEGER NOT NULL REFERENCES datos_personales(id),
    rol_id INTEGER NOT NULL REFERENCES roles(id),
    activo BOOLEAN DEFAULT TRUE
);

-- ============================================
-- NUEVA TABLA: CONEXIONES GITHUB
-- Depende de usuarios (nivel 1)
-- ============================================

CREATE TABLE github_conexiones (
    id SERIAL PRIMARY KEY,
    -- Referencia lógica al usuario (sin FK formal para evitar dependencia circular con Django)
    usuario_id INTEGER NOT NULL UNIQUE REFERENCES usuarios(id) ON DELETE CASCADE,
    -- Token GitHub encriptado con Fernet (nunca en texto plano)
    token_encriptado TEXT NOT NULL,
    -- Metadatos públicos del perfil GitHub
    github_usuario VARCHAR(100) NOT NULL,
    github_avatar VARCHAR(500) DEFAULT '',
    -- Auditoría
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activo BOOLEAN DEFAULT TRUE
);

-- Índice para búsquedas rápidas por usuario
CREATE INDEX idx_github_conexiones_usuario_id ON github_conexiones(usuario_id);


-- ============================================
-- TABLAS CON DEPENDENCIAS NIVEL 2
-- ============================================

-- Tabla de proyectos (depende de usuarios)
CREATE TABLE proyectos (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    estado_id INTEGER REFERENCES estados_proyecto(id),
    fecha_creacion DATE DEFAULT CURRENT_DATE,
    fecha_actualizacion DATE DEFAULT CURRENT_DATE,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    activo BOOLEAN DEFAULT TRUE
);

-- ============================================
-- ESQUEMAS DE BD
-- ============================================

-- Tabla para almacenar esquemas de bases de datos de proyectos
CREATE TABLE esquemas_bd (
    id SERIAL PRIMARY KEY,
    proyecto_id INTEGER NOT NULL REFERENCES proyectos(id) ON DELETE CASCADE,
    tipo_motor_bd_id INTEGER NOT NULL REFERENCES tipos_motor_bd(id),
    esquema JSONB NOT NULL,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activo BOOLEAN DEFAULT TRUE,
    UNIQUE(proyecto_id, tipo_motor_bd_id)
);

-- ============================================
-- TABLAS CON DEPENDENCIAS NIVEL 3
-- ============================================

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

-- Tabla de pruebas
CREATE TABLE pruebas (
    id SERIAL PRIMARY KEY,
    proyecto_id INTEGER NOT NULL REFERENCES proyectos(id),
    tipo_prueba_id INTEGER NOT NULL REFERENCES tipos_prueba(id),
    codigo VARCHAR(50) NOT NULL,    
    nombre VARCHAR(255) NOT NULL,          
    descripcion TEXT,                      
    estado VARCHAR(50),        
    especificacion_relacionada VARCHAR(100), 
    prueba JSON NOT NULL,           
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activo BOOLEAN DEFAULT TRUE
);

-- ============================================
-- TABLAS DE RELACIONES (NIVEL 4)
-- ============================================

-- Tabla relación entre historia de usuario y estimaciones
CREATE TABLE historias_estimaciones (
    id SERIAL PRIMARY KEY,
    historia_id INTEGER NOT NULL REFERENCES historias_usuario(id) ON DELETE CASCADE,
    tipo_estimacion_id INTEGER NOT NULL REFERENCES tipos_estimacion(id),
    valor NUMERIC(10,2) NOT NULL,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activo BOOLEAN DEFAULT TRUE,
    UNIQUE(historia_id, tipo_estimacion_id)
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

-- ============================================
-- INSERCIÓN DE DATOS INICIALES
-- ============================================

-- Insertar tipos de motor de base de datos
INSERT INTO tipos_motor_bd (nombre, descripcion, extension_archivo, color, activo) VALUES
('PostgreSQL', 'Sistema de gestión de bases de datos relacional de código abierto', '.sql', '#336791', TRUE),
('MySQL', 'Sistema de gestión de bases de datos relacional muy popular', '.sql', '#4479A1', TRUE),
('SQLite', 'Base de datos embebida ligera', '.sql', '#003B57', TRUE),
('SQL Server', 'Sistema de gestión de bases de datos de Microsoft', '.sql', '#CC2927', TRUE);

-- Insertar tipos de prueba
INSERT INTO tipos_prueba (nombre, descripcion, color, activo) VALUES
('integracion', 'Pruebas que verifican la integración entre módulos', '#8B5CF6', TRUE),
('sistema', 'Pruebas completas del sistema en su totalidad', '#6366F1', TRUE),
('unitaria', 'Pruebas individuales de funciones o métodos', '#A855F7', TRUE);

-- Insertar roles básicos
INSERT INTO roles (nombre, descripcion, color) VALUES 
('admin', 'Administrador del sistema', '#DC2626'),
('usuario', 'Usuario regular', '#3B82F6');

-- Insertar tipos de requisitos
INSERT INTO tipos_requisito (nombre, descripcion, color, activo) VALUES 
('funcional', 'Requisitos que definen funciones específicas del sistema', '#10B981', TRUE),
('tecnico', 'Requisitos técnicos de implementación', '#F59E0B', TRUE),
('sistema', 'Requisitos generales del sistema', '#3B82F6', TRUE);

-- Insertar prioridades (gradiente de rojo intenso a gris)
INSERT INTO prioridades (nombre, nivel, descripcion, color, activo) VALUES 
('muy-alta', 1, 'Prioridad muy alta - Crítico para el proyecto', '#DC2626', TRUE),
('alta', 2, 'Prioridad alta - Importante para el proyecto', '#F97316', TRUE),
('media', 3, 'Prioridad media - Necesario pero no urgente', '#EAB308', TRUE),
('baja', 4, 'Prioridad baja - Deseable pero no esencial', '#84CC16', TRUE),
('muy-baja', 5, 'Prioridad muy baja - Podría considerarse en el futuro', '#6B7280', TRUE);

-- Insertar estados de proyecto (flujo de proceso con colores progresivos)
INSERT INTO estados_proyecto (nombre, descripcion, orden, color, activo) VALUES 
('especificaciones', 'Fase de definición de especificaciones', 1, '#8B5CF6', TRUE),
('generacion', 'Fase de generacion de pruebas', 3, '#3B82F6', TRUE),
('seguimiento', 'Fase de seguimiento de pruebas', 5, '#10B981', TRUE),
('finalizado', 'Proyecto finalizado', 6, '#22C55E', TRUE),
('cancelado', 'Proyecto cancelado', 7, '#EF4444', TRUE);

-- Insertar tipos de relación entre casos de uso
INSERT INTO tipos_relacion_cu (nombre, descripcion, color) VALUES 
('include', 'El CU incluye obligatoriamente otro CU', '#3B82F6'),
('extend', 'El CU puede extender otro CU bajo condiciones', '#8B5CF6'),
('generalizacion', 'El CU es una especialización de otro CU padre', '#06B6D4'),
('dependencia', 'El CU depende de otro CU para su ejecución', '#F59E0B');

-- Insertar tipos de relación entre requisitos
INSERT INTO tipos_relacion_requisito (nombre, descripcion, color, activo) VALUES 
('depende', 'Este requisito depende del requisito relacionado', '#3B82F6', TRUE),
('bloquea', 'Este requisito bloquea al requisito relacionado', '#EF4444', TRUE),
('conflicto', 'Este requisito está en conflicto con el relacionado', '#DC2626', TRUE),
('complementa', 'Este requisito complementa al requisito relacionado', '#10B981', TRUE),
('deriva', 'Este requisito deriva del requisito relacionado', '#8B5CF6', TRUE),
('refina', 'Este requisito refina al requisito relacionado', '#06B6D4', TRUE);

-- Insertar estados para elementos - REQUISITOS
INSERT INTO estados_elemento (nombre, descripcion, tipo, color, activo) VALUES 
('pendiente', 'Requisito pendiente de revisión', 'requisito', '#6B7280', TRUE),
('aprobado', 'Requisito aprobado para implementación', 'requisito', '#10B981', TRUE),
('en-desarrollo', 'Requisito en desarrollo', 'requisito', '#3B82F6', TRUE),
('implementado', 'Requisito implementado', 'requisito', '#22C55E', TRUE),
('rechazado', 'Requisito rechazado', 'requisito', '#EF4444', TRUE),
('postpuesto', 'Requisito postpuesto para una fase posterior', 'requisito', '#F59E0B', TRUE);

-- Insertar estados para elementos - CASOS DE USO
INSERT INTO estados_elemento (nombre, descripcion, tipo, color, activo) VALUES 
('pendiente', 'Caso de uso pendiente de revisión', 'caso_uso', '#6B7280', TRUE),
('aprobado', 'Caso de uso aprobado', 'caso_uso', '#10B981', TRUE),
('en-analisis', 'Caso de uso en análisis', 'caso_uso', '#8B5CF6', TRUE),
('desarrollado', 'Caso de uso desarrollado', 'caso_uso', '#3B82F6', TRUE),
('probado', 'Caso de uso probado', 'caso_uso', '#22C55E', TRUE),
('rechazado', 'Caso de uso rechazado', 'caso_uso', '#EF4444', TRUE);

-- Insertar estados para elementos - HISTORIAS DE USUARIO
INSERT INTO estados_elemento (nombre, descripcion, tipo, color, activo) VALUES 
('pendiente', 'Historia de usuario pendiente', 'historia_usuario', '#6B7280', TRUE),
('en-progreso', 'Historia de usuario en progreso', 'historia_usuario', '#3B82F6', TRUE),
('completada', 'Historia de usuario completada', 'historia_usuario', '#22C55E', TRUE),
('bloqueada', 'Historia de usuario bloqueada', 'historia_usuario', '#EF4444', TRUE),
('rechazada', 'Historia de usuario rechazada', 'historia_usuario', '#DC2626', TRUE);

-- Insertar tipos de estimación
INSERT INTO tipos_estimacion (nombre, descripcion, color, activo) VALUES
('story-points', 'Estimación relativa en puntos de historia', '#8B5CF6', TRUE),
('horas', 'Estimación en horas de esfuerzo', '#3B82F6', TRUE),
('dias', 'Estimación en días de esfuerzo', '#06B6D4', TRUE),
('costo', 'Estimación en costo monetario', '#10B981', TRUE);

-- Insertar datos personales
INSERT INTO datos_personales (nombre, apellido)
VALUES 
('Admin', 'Principal'),
('Usuario', 'Regular');

-- Insertar usuario ADMIN
INSERT INTO usuarios (usuario, contrasenia, datos_personales_id, rol_id, activo)
VALUES (
    'admin',
    'pbkdf2_sha256$720000$nA1DBiCSy5A4HPTMAfMGDx$MmlhOsKKop+XKgi48HY1WYVShwtU6vD1/nsc8bnk2Zo=',
    1,
    1,
    TRUE
);

-- Insertar usuario REGULAR
INSERT INTO usuarios (usuario, contrasenia, datos_personales_id, rol_id, activo)
VALUES (
    'usuario',
    'pbkdf2_sha256$720000$nA1DBiCSy5A4HPTMAfMGDx$MmlhOsKKop+XKgi48HY1WYVShwtU6vD1/nsc8bnk2Zo=',
    2,
    2,
    TRUE
);