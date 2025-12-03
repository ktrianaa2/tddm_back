from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
import json
from google import genai
from django.conf import settings

# Importar modelos necesarios
from pruebas.models import TiposPrueba, Pruebas
from proyectos.models import Proyectos
from usuarios.views import validar_token
from usuarios.models import Usuarios

# Asumo que estos modelos existen en sus respectivas apps
from requisitos.models import Requisitos
from historiasdeusuario.models import HistoriasUsuario, HistoriasEstimaciones
from casosdeuso.models import CasosUso, RelacionesCasosUso

# Configurar cliente de Gemini
try:
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
except AttributeError:
    print("ADVERTENCIA: No se encontró GEMINI_API_KEY en settings.py")
    client = genai.Client()

MODEL_NAME = "gemini-2.5-flash"


# Mapeo de prefijos por tipo de prueba
PREFIJOS_TIPO_PRUEBA = {
    'unitaria': 'UNIT-TEST',
    'integracion': 'INT-TEST',
    'sistema': 'SYS-TEST',
}


def generar_codigo_prueba(proyecto_id, tipo_prueba_nombre):
    """
    Genera el siguiente código de prueba disponible para un proyecto y tipo específico.
    
    Args:
        proyecto_id: ID del proyecto
        tipo_prueba_nombre: Nombre del tipo de prueba (ej: 'unitaria', 'integracion')
    
    Returns:
        String con el código generado (ej: 'UNIT-TEST-P001-005')
    """
    # Obtener el prefijo según el tipo de prueba
    prefijo = PREFIJOS_TIPO_PRUEBA.get(
        tipo_prueba_nombre.lower(), 
        'TEST'
    )
    
    # Obtener el tipo de prueba
    try:
        tipo_prueba = TiposPrueba.objects.get(nombre=tipo_prueba_nombre.lower())
    except TiposPrueba.DoesNotExist:
        tipo_prueba = None
    
    # Contar pruebas existentes del mismo tipo en el proyecto
    if tipo_prueba:
        count = Pruebas.objects.filter(
            proyecto_id=proyecto_id,
            tipo_prueba=tipo_prueba,
            activo=True
        ).count()
    else:
        count = Pruebas.objects.filter(
            proyecto_id=proyecto_id,
            activo=True
        ).count()
    
    # Incrementar para el siguiente número
    numero_prueba = count + 1
    
    # Formatear: PREFIJO-P{proyecto_id}-{numero}
    # Ejemplo: UNIT-TEST-P001-005
    codigo = f"{prefijo}-P{proyecto_id:03d}-{numero_prueba:03d}"
    
    return codigo


# -----------------------------
# Generar pruebas unitarias con IA
# -----------------------------
@csrf_exempt
@require_http_methods(["POST"])
def generar_pruebas_unitarias(request, proyecto_id):
    """
    Genera pruebas unitarias basadas en las especificaciones del proyecto
    usando IA y las guarda en la base de datos.
    """
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        # Validar que el proyecto existe y está activo
        try:
            proyecto = Proyectos.objects.get(id=proyecto_id, activo=True)
        except Proyectos.DoesNotExist:
            return JsonResponse({'error': 'El proyecto especificado no existe'}, status=404)

        # 1. Obtener todas las especificaciones del proyecto
        especificaciones = obtener_especificaciones_proyecto(proyecto_id)
        
        if not especificaciones['tiene_especificaciones']:
            return JsonResponse({
                'error': 'No hay especificaciones en el proyecto para generar pruebas'
            }, status=400)

        # 2. Crear el prompt para la IA
        prompt = construir_prompt_pruebas(proyecto, especificaciones)

        # 3. Generar pruebas con IA
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[prompt]
        )

        pruebas_generadas = response.text
        
        # 4. Parsear la respuesta de la IA (debe devolver JSON)
        try:
            pruebas_json = json.loads(pruebas_generadas)
        except json.JSONDecodeError as e:
            # Si la IA devuelve texto con markdown, intentar extraer el JSON
            try:
                pruebas_json = extraer_json_de_respuesta(pruebas_generadas)
            except Exception as extract_error:
                # Si falla la extracción, devolver el error detallado
                return JsonResponse({
                    'error': 'No se pudo procesar la respuesta de la IA',
                    'detalle': str(extract_error),
                    'respuesta_ia': pruebas_generadas[:500]  # Primeros 500 chars para debug
                }, status=500)

        # 5. Obtener o crear el tipo de prueba "Unitaria"
        tipo_prueba, _ = TiposPrueba.objects.get_or_create(
            nombre="unitaria",
            defaults={
                'descripcion': 'Pruebas unitarias generadas automáticamente',
                'activo': True
            }
        )

        # 6. Guardar las pruebas en la base de datos
        pruebas_creadas = []
        with transaction.atomic():
            for prueba_data in pruebas_json.get('pruebas', []):
                # Generar código automático basado en el proyecto y tipo
                codigo_generado = generar_codigo_prueba(proyecto_id, tipo_prueba.nombre)
                
                # Obtener detalles completos
                detalles_completos = prueba_data.get('detalles', {})
                
                # Asegurarse de que sea un dict válido
                if isinstance(detalles_completos, str):
                    try:
                        detalles_completos = json.loads(detalles_completos)
                    except:
                        detalles_completos = {}
                
                if not isinstance(detalles_completos, dict):
                    detalles_completos = {}
                
                # Convertir a JSON string con comillas dobles
                prueba_json_str = json.dumps(detalles_completos, ensure_ascii=False)
                
                # Crear la prueba
                prueba = Pruebas.objects.create(
                    proyecto=proyecto,
                    tipo_prueba=tipo_prueba,
                    codigo=codigo_generado,  # ← Código auto-generado
                    nombre=prueba_data.get('nombre', f'Prueba {codigo_generado}'),
                    descripcion=prueba_data.get('descripcion', ''),
                    estado='Pendiente',
                    especificacion_relacionada=prueba_data.get('especificacion_relacionada', ''),
                    prueba=prueba_json_str,
                    activo=True
                )
                
                pruebas_creadas.append({
                    'id': prueba.id,
                    'codigo': prueba.codigo,
                    'nombre': prueba.nombre,
                    'descripcion': prueba.descripcion
                })

        return JsonResponse({
            'mensaje': f'Se generaron {len(pruebas_creadas)} pruebas unitarias exitosamente',
            'proyecto_id': proyecto_id,
            'proyecto_nombre': proyecto.nombre,
            'pruebas_creadas': pruebas_creadas,
            'total_pruebas': len(pruebas_creadas)
        }, status=201)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'Error al generar pruebas: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def previsualizar_pruebas(request, proyecto_id):
    """
    Genera las pruebas pero no las guarda, permite al usuario revisarlas primero.
    Muestra los códigos que se asignarían.
    """
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        # Validar que el proyecto existe y está activo
        try:
            proyecto = Proyectos.objects.get(id=proyecto_id, activo=True)
        except Proyectos.DoesNotExist:
            return JsonResponse({'error': 'El proyecto especificado no existe'}, status=404)

        especificaciones = obtener_especificaciones_proyecto(proyecto_id)
        
        if not especificaciones['tiene_especificaciones']:
            return JsonResponse({
                'error': 'No hay especificaciones en el proyecto para generar pruebas'
            }, status=400)

        prompt = construir_prompt_pruebas(proyecto, especificaciones)

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[prompt]
        )

        pruebas_generadas = response.text
        
        try:
            pruebas_json = json.loads(pruebas_generadas)
        except json.JSONDecodeError:
            pruebas_json = extraer_json_de_respuesta(pruebas_generadas)

        # Obtener o crear el tipo de prueba "Unitaria"
        tipo_prueba, _ = TiposPrueba.objects.get_or_create(
            nombre="unitaria",
            defaults={
                'descripcion': 'Pruebas unitarias generadas automáticamente',
                'activo': True
            }
        )

        # Agregar códigos provisionales a las pruebas para previsualización
        pruebas_con_codigo = []
        contador = Pruebas.objects.filter(
            proyecto_id=proyecto_id,
            tipo_prueba=tipo_prueba,
            activo=True
        ).count()
        
        for idx, prueba in enumerate(pruebas_json.get('pruebas', []), start=1):
            prefijo = PREFIJOS_TIPO_PRUEBA.get(tipo_prueba.nombre.lower(), 'TEST')
            codigo_provisional = f"{prefijo}-P{proyecto_id:03d}-{contador + idx:03d}"
            
            prueba['codigo_provisional'] = codigo_provisional
            pruebas_con_codigo.append(prueba)

        return JsonResponse({
            'mensaje': 'Pruebas generadas (sin guardar)',
            'proyecto_id': proyecto_id,
            'proyecto_nombre': proyecto.nombre,
            'total_pruebas': len(pruebas_con_codigo),
            'pruebas': pruebas_con_codigo,
            'info': 'Los códigos mostrados son provisionales y pueden cambiar al guardar'
        }, status=200)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'Error al generar pruebas: {str(e)}'}, status=500)


def obtener_especificaciones_proyecto(proyecto_id):
    """
    Obtiene todas las especificaciones de un proyecto (requisitos, historias, casos de uso)
    """
    especificaciones = {
        'tiene_especificaciones': False,
        'requisitos': [],
        'historias_usuario': [],
        'casos_uso': []
    }

    # Obtener requisitos
    try:
        requisitos = Requisitos.objects.filter(
            proyecto_id=proyecto_id,
            activo=True
        ).select_related('tipo', 'prioridad', 'estado')

        for req in requisitos:
            especificaciones['requisitos'].append({
                'id': req.id,
                'nombre': req.nombre,
                'descripcion': req.descripcion,
                'tipo': req.tipo.nombre if req.tipo else None,
                'criterios': req.criterios,
                'prioridad': req.prioridad.nombre if req.prioridad else None,
                'condiciones_previas': req.condiciones_previas
            })
    except Exception as e:
        print(f"Error al obtener requisitos: {e}")

    # Obtener historias de usuario
    try:
        historias = HistoriasUsuario.objects.filter(
            proyecto_id=proyecto_id,
            activo=True
        ).select_related('prioridad', 'estado')

        for historia in historias:
            especificaciones['historias_usuario'].append({
                'id': historia.id,
                'titulo': historia.titulo,
                'actor_rol': historia.actor_rol,
                'funcionalidad_accion': historia.funcionalidad_accion,
                'beneficio_razon': historia.beneficio_razon,
                'criterios_aceptacion': historia.criterios_aceptacion,
                'prioridad': historia.prioridad.nombre if historia.prioridad else None
            })
    except Exception as e:
        print(f"Error al obtener historias: {e}")

    # Obtener casos de uso
    try:
        casos = CasosUso.objects.filter(
            proyecto_id=proyecto_id,
            activo=True
        ).select_related('estado')

        for caso in casos:
            especificaciones['casos_uso'].append({
                'id': caso.id,
                'nombre': caso.nombre,
                'descripcion': caso.descripcion,
                'actores': caso.actores,
                'precondiciones': caso.precondiciones,
                'flujo_principal': caso.flujo_principal,
                'flujos_alternativos': caso.flujos_alternativos,
                'postcondiciones': caso.postcondiciones
            })
    except Exception as e:
        print(f"Error al obtener casos de uso: {e}")

    # Verificar si hay al menos una especificación
    especificaciones['tiene_especificaciones'] = (
        len(especificaciones['requisitos']) > 0 or
        len(especificaciones['historias_usuario']) > 0 or
        len(especificaciones['casos_uso']) > 0
    )

    return especificaciones


def construir_prompt_pruebas(proyecto, especificaciones):
    """
    Construye el prompt para que la IA genere las pruebas unitarias
    """
    prompt = f"""Eres un experto en TDD (Test-Driven Development) y generación de pruebas unitarias.

CONTEXTO DEL PROYECTO:
- Nombre: {proyecto.nombre}
- Descripción: {proyecto.descripcion if hasattr(proyecto, 'descripcion') else 'No especificada'}

Tu tarea es generar pruebas unitarias COMPLETAS Y DETALLADAS basadas en las siguientes especificaciones del proyecto.

ESPECIFICACIONES DEL PROYECTO:

"""

    # Agregar requisitos
    if especificaciones['requisitos']:
        prompt += "\n## REQUISITOS:\n"
        for req in especificaciones['requisitos']:
            prompt += f"\n### {req['nombre']}\n"
            prompt += f"- Descripción: {req['descripcion']}\n"
            prompt += f"- Tipo: {req['tipo']}\n"
            prompt += f"- Criterios de aceptación: {req['criterios']}\n"
            if req['condiciones_previas']:
                prompt += f"- Condiciones previas: {req['condiciones_previas']}\n"

    # Agregar historias de usuario
    if especificaciones['historias_usuario']:
        prompt += "\n## HISTORIAS DE USUARIO:\n"
        for historia in especificaciones['historias_usuario']:
            prompt += f"\n### {historia['titulo']}\n"
            prompt += f"- Como {historia['actor_rol']}\n"
            prompt += f"- Quiero {historia['funcionalidad_accion']}\n"
            prompt += f"- Para {historia['beneficio_razon']}\n"
            prompt += f"- Criterios de aceptación: {historia['criterios_aceptacion']}\n"

    # Agregar casos de uso
    if especificaciones['casos_uso']:
        prompt += "\n## CASOS DE USO:\n"
        for caso in especificaciones['casos_uso']:
            prompt += f"\n### {caso['nombre']}\n"
            prompt += f"- Descripción: {caso['descripcion']}\n"
            prompt += f"- Actores: {', '.join(caso['actores']) if caso['actores'] else 'No especificados'}\n"
            prompt += f"- Precondiciones: {caso['precondiciones']}\n"
            if caso['flujo_principal']:
                prompt += "- Flujo principal:\n"
                for paso in caso['flujo_principal']:
                    prompt += f"  {paso}\n"
            prompt += f"- Postcondiciones: {caso['postcondiciones']}\n"

    prompt += """

INSTRUCCIONES PARA GENERAR LAS PRUEBAS:

1. Crea pruebas unitarias DETALLADAS para cada funcionalidad identificada en las especificaciones
2. Cada prueba debe ser específica, clara y ejecutable
3. Incluye casos de prueba para:
   - Flujos normales (happy path)
   - Casos límite (boundary conditions)
   - Casos de error y validaciones
   - Condiciones previas y postcondiciones

4. FORMATO DE SALIDA REQUERIDO (JSON estricto, SIN caracteres de escape inválidos):

{
  "pruebas": [
    {
      "nombre": "Nombre descriptivo de la prueba",
      "descripcion": "Descripción detallada de qué valida esta prueba",
      "especificacion_relacionada": "Nombre del requisito/historia/caso de uso relacionado",
      "detalles": {
        "objetivo": "Qué se está probando",
        "precondiciones": ["Condición 1", "Condición 2"],
        "pasos": [
          {
            "paso": 1, 
            "accion": "Descripción de la acción", 
            "resultado_esperado": "Resultado esperado"
          }
        ],
        "datos_prueba": {
          "entrada": "Datos de entrada para la prueba",
          "salida_esperada": "Resultado esperado"
        },
        "criterios_aceptacion": ["Criterio 1", "Criterio 2"],
        "tipo_validacion": "funcional"
      }
    }
  ]
}

5. REGLAS IMPORTANTES: 
   - NO incluyas el campo "codigo" en el JSON - será generado automáticamente
   - Responde ÚNICAMENTE con el JSON válido, sin texto adicional ni markdown
   - NO uses bloques de código con ```
   - Usa SOLO comillas dobles (") en todo el JSON, NUNCA comillas simples (')
   - NO uses caracteres de escape inválidos (como \\d, \\s, \\w)
   - Solo usa escapes válidos en JSON: \\", \\\\, \\/, \\n, \\t
   - Genera al menos 2-3 pruebas por cada especificación relevante
   - Usa texto simple en español, sin caracteres especiales complejos

Genera SOLO el JSON de las pruebas, sin ningún texto adicional:"""

    return prompt


import re
def extraer_json_de_respuesta(texto):
    """
    Intenta extraer JSON de una respuesta que puede contener markdown o texto adicional.
    Limpia caracteres de escape inválidos y comillas simples.
    """
    try:
        # 1. Buscar JSON entre ```json y ```
        if '```json' in texto:
            inicio = texto.find('```json') + 7
            fin = texto.find('```', inicio)
            if fin == -1:
                fin = len(texto)
            json_str = texto[inicio:fin].strip()
        # 2. Buscar JSON entre ``` y ``` (sin especificar lenguaje)
        elif '```' in texto:
            inicio = texto.find('```') + 3
            fin = texto.find('```', inicio)
            if fin == -1:
                fin = len(texto)
            json_str = texto[inicio:fin].strip()
        # 3. Buscar JSON entre { y }
        else:
            inicio = texto.find('{')
            fin = texto.rfind('}') + 1
            if inicio != -1 and fin > inicio:
                json_str = texto[inicio:fin]
            else:
                # Intentar parsear directamente
                json_str = texto.strip()
        
        # 4. Reemplazar comillas simples por dobles (CRÍTICO para PostgreSQL JSON)
        json_str = json_str.replace("'", '"')
        
        # 5. Limpiar caracteres de escape inválidos
        json_str = json_str.replace('\\n', '\n')
        json_str = json_str.replace('\\t', '\t')
        json_str = json_str.replace('\\r', '\r')
        
        # Eliminar escapes inválidos
        json_str = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', json_str)
        
        # 6. Intentar parsear
        return json.loads(json_str)
        
    except json.JSONDecodeError as e:
        # Si aún falla, intentar una limpieza más agresiva
        try:
            json_str_limpio = json_str.encode('utf-8', 'ignore').decode('utf-8')
            return json.loads(json_str_limpio)
        except:
            raise ValueError(
                f"No se pudo extraer JSON válido de la respuesta de la IA. "
                f"Error: {str(e)}. "
                f"Fragmento problemático: {json_str[max(0, e.pos-50):min(len(json_str), e.pos+50)]}"
            )
    except Exception as e:
        raise ValueError(f"Error al procesar la respuesta de la IA: {str(e)}")