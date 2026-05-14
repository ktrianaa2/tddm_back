"""
generador_resumenes.py

Módulo para generar resúmenes contextuales usando IA.
Se utiliza en la generación de documentación PDF.

Genera en una sola llamada:
- Descripción general del proyecto
- Resumen de requisitos
- Resumen de historias de usuario
- Resumen de casos de uso
- Resumen de esquema de BD
- Resumen de pruebas aprobadas
"""

import json
import anthropic
from django.conf import settings

# Configurar cliente de Claude
api_key = getattr(settings, 'CLAUDE_API_KEY', None)
if not api_key:
    raise ValueError("CLAUDE_API_KEY no configurada en settings.py o variables de entorno")
client = anthropic.Anthropic(api_key=api_key)

MODEL_NAME = "claude-haiku-4-5-20251001"


def generar_resumenes_documentacion(proyecto, requisitos, historias_usuario, casos_uso, pruebas_aprobadas, esquema_bd=None):
    """
    Genera todos los resúmenes necesarios para la documentación PDF en una sola llamada a IA.
    
    Args:
        proyecto: Objeto Proyecto
        requisitos: Lista de requisitos
        historias_usuario: Lista de historias de usuario
        casos_uso: Lista de casos de uso
        pruebas_aprobadas: Lista de pruebas aprobadas
        esquema_bd: Esquema de base de datos (opcional)
    
    Returns:
        Dict con:
        - descripcion_general: Párrafo introductorio mejorado (inicia con "Con este proyecto se busca...")
        - requisitos_resumen: Resumen de requisitos
        - historias_resumen: Resumen de historias de usuario
        - casos_uso_resumen: Resumen de casos de uso
        - esquema_bd_resumen: Resumen del esquema de BD
        - pruebas_resumen: Resumen de pruebas aprobadas
    """
    
    try:
        # ─────────────────────────────────────────────────────────────
        # PREPARAR DATOS PARA EL PROMPT
        # ─────────────────────────────────────────────────────────────
        
        proyecto_nombre = proyecto.nombre if hasattr(proyecto, 'nombre') else 'No especificado'
        proyecto_descripcion = proyecto.descripcion if hasattr(proyecto, 'descripcion') else 'No especificada'
        
        # Información de requisitos
        info_requisitos = f"{len(requisitos)} requisitos" if requisitos else "0 requisitos"
        tipos_requisitos = {}
        if requisitos:
            for req in requisitos:
                tipo = req.get('tipo', 'Sin tipo') if isinstance(req, dict) else (req.tipo.nombre if hasattr(req, 'tipo') else 'Sin tipo')
                tipos_requisitos[tipo] = tipos_requisitos.get(tipo, 0) + 1
        
        # Información de historias
        info_historias = f"{len(historias_usuario)} historias de usuario" if historias_usuario else "0 historias de usuario"
        
        # Información de casos de uso
        info_casos = f"{len(casos_uso)} casos de uso" if casos_uso else "0 casos de uso"
        
        # Información de pruebas
        info_pruebas = f"{len(pruebas_aprobadas)} pruebas aprobadas" if pruebas_aprobadas else "0 pruebas aprobadas"
        
        # Conteo de especificaciones
        total_especificaciones = len(requisitos) + len(historias_usuario) + len(casos_uso)
        
        # Información de base de datos
        info_bd = ""
        if esquema_bd and isinstance(esquema_bd, dict):
            num_tablas = len(esquema_bd.get('tablas', []))
            info_bd = f"esquema con {num_tablas} tablas"
        
        # ─────────────────────────────────────────────────────────────
        # CONSTRUIR PROMPT PARA GENERAR TODOS LOS RESÚMENES
        # ─────────────────────────────────────────────────────────────
        
        prompt = f"""Eres un experto en documentación técnica y análisis de proyectos de software. 
Tu tarea es generar resúmenes contextuales profesionales para la documentación de un proyecto.

INFORMACIÓN DEL PROYECTO:
- Nombre: {proyecto_nombre}
- Descripción original: {proyecto_descripcion}

ESPECIFICACIONES IDENTIFICADAS:
- {info_requisitos}
- {info_historias}
- {info_casos}
- {info_pruebas}
{f'- {info_bd}' if info_bd else ''}

LISTADO DE REQUISITOS:
{_formatear_lista_requisitos(requisitos) if requisitos else 'No hay requisitos'}

LISTADO DE HISTORIAS DE USUARIO:
{_formatear_lista_historias(historias_usuario) if historias_usuario else 'No hay historias de usuario'}

LISTADO DE CASOS DE USO:
{_formatear_lista_casos_uso(casos_uso) if casos_uso else 'No hay casos de uso'}

INSTRUCCIONES:
Genera ÚNICAMENTE un JSON válido con los siguientes campos (sin texto adicional, sin comentarios):

1. "descripcion_general": Párrafo de 2-3 oraciones que:
   - Comience exactamente con "Con este proyecto se busca"
   - Describa el propósito general del proyecto
   - Mencione que el documento contiene {total_especificaciones} especificaciones y fue validado con {len(pruebas_aprobadas)} pruebas aprobadas generadas en TDD Machine
   - Tono: profesional, claro, accesible

2. "requisitos_resumen": Párrafo de 2-3 oraciones que resuma:
   - Naturaleza y propósito de los requisitos
   - Categorías principales identificadas
   - Cobertura de funcionalidad
   (Devuelve "" si no hay requisitos)

3. "historias_resumen": Párrafo de 2-3 oraciones que resuma:
   - Perspectiva del usuario
   - Tipos de funcionalidad requerida
   - Valor entregado al negocio
   (Devuelve "" si no hay historias)

4. "casos_uso_resumen": Párrafo de 2-3 oraciones que resuma:
   - Cobertura de interacciones del sistema
   - Actores principales involucrados
   - Complejidad de las operaciones
   (Devuelve "" si no hay casos de uso)

5. "esquema_bd_resumen": Párrafo de 2-3 oraciones que resuma:
   - Estructura general de datos
   - Número de entidades principales
   - Relaciones clave entre tablas
   (Devuelve "" si no hay esquema BD)

6. "pruebas_resumen": Párrafo de 2-3 oraciones que resuma:
   - Cantidad y tipos de pruebas realizadas
   - Cobertura de validación alcanzada
   - Confianza en la implementación basada en pruebas
   (Devuelve "" si no hay pruebas aprobadas)

FORMATO JSON REQUERIDO:
{{
  "descripcion_general": "Con este proyecto se busca...",
  "requisitos_resumen": "...",
  "historias_resumen": "...",
  "casos_uso_resumen": "...",
  "esquema_bd_resumen": "...",
  "pruebas_resumen": "..."
}}

IMPORTANTE:
- Responde SOLO con JSON válido
- Sin explicaciones, comentarios ni markdown
- Sin bloques de código
- Ningún otro texto antes o después del JSON
"""

        # ─────────────────────────────────────────────────────────────
        # LLAMAR A LA IA
        # ─────────────────────────────────────────────────────────────
        
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=2000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        respuesta_texto = response.content[0].text.strip()
        
        # ─────────────────────────────────────────────────────────────
        # PARSEAR RESPUESTA
        # ─────────────────────────────────────────────────────────────
        
        # Intentar parsear como JSON directo
        try:
            resumenes = json.loads(respuesta_texto)
        except json.JSONDecodeError:
            # Intentar extraer JSON de markdown o bloques
            import re
            match = re.search(r'```(?:json)?\s*(.*?)```', respuesta_texto, re.DOTALL)
            if match:
                resumenes = json.loads(match.group(1).strip())
            else:
                # Última opción: buscar el objeto JSON directamente
                inicio = respuesta_texto.find('{')
                fin = respuesta_texto.rfind('}') + 1
                if inicio != -1 and fin > inicio:
                    resumenes = json.loads(respuesta_texto[inicio:fin])
                else:
                    raise ValueError(f"No se pudo parsear como JSON: {respuesta_texto[:200]}")
        
        # Asegurar que todos los campos existen
        resumenes_limpios = {
            'descripcion_general': resumenes.get('descripcion_general', _generar_descripcion_default(proyecto_descripcion)),
            'requisitos_resumen': resumenes.get('requisitos_resumen', ''),
            'historias_resumen': resumenes.get('historias_resumen', ''),
            'casos_uso_resumen': resumenes.get('casos_uso_resumen', ''),
            'esquema_bd_resumen': resumenes.get('esquema_bd_resumen', ''),
            'pruebas_resumen': resumenes.get('pruebas_resumen', '')
        }
        
        return resumenes_limpios
        
    except Exception as e:
        print(f"[ERROR] Error generando resúmenes con IA: {str(e)}")
        # Retornar resúmenes por defecto si falla
        return {
            'descripcion_general': _generar_descripcion_default(proyecto_descripcion),
            'requisitos_resumen': '',
            'historias_resumen': '',
            'casos_uso_resumen': '',
            'esquema_bd_resumen': '',
            'pruebas_resumen': ''
        }


def _generar_descripcion_default(descripcion_proyecto):
    """Genera una descripción por defecto si la IA falla."""
    return f"Con este proyecto se busca implementar una solución que cumpla con los requisitos especificados. {descripcion_proyecto}"


def _formatear_lista_requisitos(requisitos):
    """Formatea los requisitos para el prompt."""
    if not requisitos:
        return "No hay requisitos"
    
    lineas = []
    for req in requisitos[:8]:  # Limitar a 8 primeros
        nombre = req.get('nombre', 'Sin nombre') if isinstance(req, dict) else (req.nombre if hasattr(req, 'nombre') else 'Sin nombre')
        tipo = req.get('tipo', '') if isinstance(req, dict) else (req.tipo.nombre if hasattr(req, 'tipo') else '')
        lineas.append(f"- {nombre} ({tipo})")
    
    return '\n'.join(lineas)


def _formatear_lista_historias(historias):
    """Formatea las historias de usuario para el prompt."""
    if not historias:
        return "No hay historias de usuario"
    
    lineas = []
    for historia in historias[:8]:  # Limitar a 8 primeras
        titulo = historia.get('titulo', 'Sin título') if isinstance(historia, dict) else (historia.titulo if hasattr(historia, 'titulo') else 'Sin título')
        actor = historia.get('actor_rol', '') if isinstance(historia, dict) else (historia.actor_rol if hasattr(historia, 'actor_rol') else '')
        lineas.append(f"- {titulo} (Actor: {actor})")
    
    return '\n'.join(lineas)


def _formatear_lista_casos_uso(casos_uso):
    """Formatea los casos de uso para el prompt."""
    if not casos_uso:
        return "No hay casos de uso"
    
    lineas = []
    for caso in casos_uso[:8]:  # Limitar a 8 primeros
        nombre = caso.get('nombre', 'Sin nombre') if isinstance(caso, dict) else (caso.nombre if hasattr(caso, 'nombre') else 'Sin nombre')
        actores = caso.get('actores', '') if isinstance(caso, dict) else (caso.actores if hasattr(caso, 'actores') else '')
        lineas.append(f"- {nombre} (Actores: {actores})")
    
    return '\n'.join(lineas)