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
from proyectos.views import cambiar_proyecto_a_generacion

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
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        print("=" * 50)
        print(f"[DEBUG] Iniciando generación para proyecto {proyecto_id}")
        
        # Validar proyecto
        try:
            proyecto = Proyectos.objects.get(id=proyecto_id, activo=True)
            print(f"[DEBUG] Proyecto encontrado: {proyecto.nombre}, Estado: {proyecto.estado}")
        except Proyectos.DoesNotExist:
            print(f"[ERROR] Proyecto {proyecto_id} no existe")
            return JsonResponse({'error': 'El proyecto especificado no existe'}, status=404)

        # Obtener especificaciones
        print("[DEBUG] Obteniendo especificaciones...")
        especificaciones = obtener_especificaciones_proyecto(proyecto_id)
        print(f"[DEBUG] Especificaciones obtenidas: {especificaciones['tiene_especificaciones']}")
        
        if not especificaciones['tiene_especificaciones']:
            return JsonResponse({
                'error': 'No hay especificaciones en el proyecto para generar pruebas'
            }, status=400)

        # Construir prompt
        print("[DEBUG] Construyendo prompt...")
        prompt = construir_prompt_pruebas(proyecto, especificaciones)
        print(f"[DEBUG] Prompt creado, longitud: {len(prompt)} caracteres")

        # Llamar a IA
        print("[DEBUG] Llamando a Gemini API...")
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[prompt]
        )
        print("[DEBUG] Respuesta de IA recibida")
        
        # En tu función generar_pruebas_unitarias:

        pruebas_generadas = response.text
        print(f"[DEBUG] Texto generado, primeros 200 chars: {pruebas_generadas[:200]}")

        # AGREGAR LIMPIEZA PREVIA
        print("[DEBUG] Limpiando formato de IA...")
        pruebas_generadas = limpiar_json_ia(pruebas_generadas)
        print(f"[DEBUG] Texto limpiado, primeros 200 chars: {pruebas_generadas[:200]}")

        # Parsear respuesta
        print("[DEBUG] Parseando JSON...")
        try:
            pruebas_json = json.loads(pruebas_generadas)
            print(f"[DEBUG] JSON parseado correctamente, {len(pruebas_json.get('pruebas', []))} pruebas")
        except json.JSONDecodeError as e:
            print(f"[DEBUG] Error parseando JSON directo, intentando extraer... Error: {e}")
            try:
                pruebas_json = extraer_json_de_respuesta(pruebas_generadas)
                print(f"[DEBUG] JSON extraído correctamente")
            except Exception as extract_error:
                print(f"[ERROR] Fallo total al parsear: {extract_error}")
                return JsonResponse({
                    'error': 'No se pudo procesar la respuesta de la IA',
                    'detalle': str(extract_error),
                    'respuesta_ia': pruebas_generadas[:500]
                }, status=500)

        # Obtener tipo de prueba
        print("[DEBUG] Obteniendo tipo de prueba...")
        tipo_prueba, _ = TiposPrueba.objects.get_or_create(
            nombre="unitaria",
            defaults={
                'descripcion': 'Pruebas unitarias generadas automáticamente',
                'activo': True
            }
        )
        print(f"[DEBUG] Tipo de prueba: {tipo_prueba.id}")

        # Guardar pruebas
        print("[DEBUG] Guardando pruebas en BD...")
        pruebas_creadas = []
        with transaction.atomic():
            for idx, prueba_data in enumerate(pruebas_json.get('pruebas', [])):
                print(f"[DEBUG] Procesando prueba {idx + 1}...")
                
                codigo_generado = generar_codigo_prueba(proyecto_id, tipo_prueba.nombre)
                print(f"[DEBUG] Código generado: {codigo_generado}")
                
                detalles_completos = prueba_data.get('detalles', {})
                
                if isinstance(detalles_completos, str):
                    try:
                        detalles_completos = json.loads(detalles_completos)
                    except:
                        detalles_completos = {}
                
                if not isinstance(detalles_completos, dict):
                    detalles_completos = {}
                
                prueba_json_str = json.dumps(detalles_completos, ensure_ascii=False)
                print(f"[DEBUG] JSON detalles longitud: {len(prueba_json_str)}")
                
                try:
                    prueba = Pruebas.objects.create(
                        proyecto=proyecto,
                        tipo_prueba=tipo_prueba,
                        codigo=codigo_generado,
                        nombre=prueba_data.get('nombre', f'Prueba {codigo_generado}'),
                        descripcion=prueba_data.get('descripcion', ''),
                        estado='Pendiente',
                        especificacion_relacionada=prueba_data.get('especificacion_relacionada', ''),
                        prueba=prueba_json_str,
                        activo=True
                    )
                    print(f"[DEBUG] Prueba creada: {prueba.id}")
                    
                    pruebas_creadas.append({
                        'id': prueba.id,
                        'codigo': prueba.codigo,
                        'nombre': prueba.nombre,
                        'descripcion': prueba.descripcion
                    })
                except Exception as db_error:
                    print(f"[ERROR] Error al crear prueba en BD: {db_error}")
                    raise
            
            # Cambio de estado
            if pruebas_creadas:
                print("[DEBUG] Cambiando estado del proyecto...")
                cambio_exitoso, mensaje_cambio = cambiar_proyecto_a_generacion(proyecto_id)
                print(f"[DEBUG] Cambio de estado: {cambio_exitoso}, {mensaje_cambio}")
                estado_actualizado = cambio_exitoso
            else:
                estado_actualizado = False
                mensaje_cambio = "No se crearon pruebas"

        proyecto.refresh_from_db()
        print(f"[DEBUG] Proceso completado exitosamente")
        print("=" * 50)

        return JsonResponse({
            'mensaje': f'Se generaron {len(pruebas_creadas)} pruebas unitarias exitosamente',
            'proyecto_id': proyecto_id,
            'proyecto_nombre': proyecto.nombre,
            'proyecto_estado': proyecto.estado,
            'cambio_estado': estado_actualizado,
            'mensaje_cambio_estado': mensaje_cambio,
            'pruebas_creadas': pruebas_creadas,
            'total_pruebas': len(pruebas_creadas)
        }, status=201)

    except Exception as e:
        import traceback
        print("=" * 50)
        print(f"[ERROR FATAL] {str(e)}")
        traceback.print_exc()
        print("=" * 50)
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
            'proyecto_estado_actual': proyecto.estado,
            'total_pruebas': len(pruebas_con_codigo),
            'pruebas': pruebas_con_codigo,
            'info': 'Los códigos mostrados son provisionales. Al guardar, el proyecto pasará a fase "Generación"'
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
    Construye un prompt optimizado para generar pruebas unitarias ejecutables en pytest
    con cobertura completa y sin redundancias.
    """
    prompt = f"""Eres un ingeniero de pruebas experto en pytest y TDD. Tu tarea es generar pruebas unitarias ejecutables en Python/pytest basadas en las especificaciones del proyecto.

INFORMACIÓN DEL PROYECTO:
Nombre: {proyecto.nombre}
Descripción: {proyecto.descripcion if hasattr(proyecto, 'descripcion') else 'No especificada'}

"""

    # Agregar especificaciones del proyecto
    if especificaciones['requisitos']:
        prompt += "REQUISITOS DEL SISTEMA:\n"
        for req in especificaciones['requisitos']:
            prompt += f"\nID: {req['id']}\n"
            prompt += f"Nombre: {req['nombre']}\n"
            prompt += f"Descripción: {req['descripcion']}\n"
            prompt += f"Tipo: {req['tipo']}\n"
            prompt += f"Criterios de aceptación: {req['criterios']}\n"
            if req.get('condiciones_previas'):
                prompt += f"Condiciones previas: {req['condiciones_previas']}\n"
            prompt += "---\n"

    if especificaciones['historias_usuario']:
        prompt += "\nHISTORIAS DE USUARIO:\n"
        for historia in especificaciones['historias_usuario']:
            prompt += f"\nID: {historia['id']}\n"
            prompt += f"Título: {historia['titulo']}\n"
            prompt += f"Como {historia['actor_rol']}, quiero {historia['funcionalidad_accion']} para {historia['beneficio_razon']}\n"
            prompt += f"Criterios de aceptación: {historia['criterios_aceptacion']}\n"
            prompt += "---\n"

    if especificaciones['casos_uso']:
        prompt += "\nCASOS DE USO:\n"
        for caso in especificaciones['casos_uso']:
            prompt += f"\nID: {caso['id']}\n"
            prompt += f"Nombre: {caso['nombre']}\n"
            prompt += f"Descripción: {caso['descripcion']}\n"
            prompt += f"Actores: {caso['actores']}\n"
            prompt += f"Precondiciones: {caso['precondiciones']}\n"
            prompt += f"Flujo principal: {caso['flujo_principal']}\n"
            if caso.get('flujos_alternativos'):
                prompt += f"Flujos alternativos: {caso['flujos_alternativos']}\n"
            prompt += f"Postcondiciones: {caso['postcondiciones']}\n"
            prompt += "---\n"

    prompt += """
REGLAS CRÍTICAS PARA EL FORMATO JSON:

1. NUNCA uses comillas dobles dentro de valores de texto en el JSON
2. Si necesitas citas o términos especiales, usa comillas simples o guiones
3. Ejemplo CORRECTO: "El usuario debe tener el rol de administrador"
4. Ejemplo INCORRECTO: "El usuario debe tener el rol de "administrador""
5. NO incluyas bloques de código markdown
6. NO incluyas texto explicativo antes o después del JSON
7. Responde ÚNICAMENTE con el JSON válido

INSTRUCCIONES PARA GENERACIÓN DE PRUEBAS:

1. ANÁLISIS DE ESPECIFICACIONES
Antes de generar pruebas, identifica funcionalidades que aparecen en múltiples especificaciones. Si una funcionalidad está documentada en varios lugares, genera un conjunto único de pruebas que cubra todos los aspectos relacionados.

2. COBERTURA DE PRUEBAS REQUERIDA
Para cada funcionalidad identificada, debes cubrir obligatoriamente:
- Caso exitoso con datos válidos y completos
- Casos de validación de datos obligatorios
- Casos de validación de tipos de datos incorrectos
- Casos de validación de formatos inválidos
- Casos de validación de reglas de negocio
- Casos de valores límite
- Casos de condiciones previas no cumplidas
- Casos de estados inconsistentes o datos duplicados

3. CÓDIGO EJECUTABLE EN PYTEST
Cada paso debe contener código Python real que se pueda ejecutar en pytest. No uses pseudocódigo ni descripciones textuales.

EJEMPLO DE PASO CORRECTO:
{
  "paso": 1,
  "accion": "producto = {'codigo': 'PRD001', 'nombre': 'Laptop HP', 'precio': 899.99, 'stock': 0}",
  "resultado_esperado": "Diccionario con producto creado con stock en 0"
}

EJEMPLO DE PASO INCORRECTO:
{
  "paso": 1,
  "accion": "Crear objeto producto",
  "resultado_esperado": "Producto creado"
}

4. ESTRUCTURA DE PASOS
Los pasos deben seguir esta secuencia lógica:
- Preparación: Configurar mocks, fixtures y datos de entrada
- Ejecución: Invocar la función o método bajo prueba
- Verificación: Usar asserts de pytest para validar resultados
- Limpieza: Si es necesario, resetear estados o mocks

5. NOMENCLATURA DE PRUEBAS
Los nombres de las pruebas deben seguir el formato:
test_[accion]_[condicion]_[resultado_esperado]

EJEMPLOS CORRECTOS:
- test_registrar_producto_con_datos_validos_retorna_producto_guardado
- test_registrar_producto_con_precio_negativo_lanza_excepcion
- test_registrar_producto_con_codigo_duplicado_retorna_error
- test_buscar_producto_inexistente_retorna_none
- test_actualizar_stock_con_cantidad_negativa_lanza_value_error

6. DATOS DE PRUEBA
El campo entrada debe contener un diccionario Python literal válido, no una descripción textual.

CORRECTO:
"entrada": "{'codigo': 'PRD001', 'nombre': 'Laptop', 'precio': 999.99, 'stock': 5}"

INCORRECTO:
"entrada": "Datos válidos de producto"

7. FORMATO DE RESPUESTA JSON
Debes responder únicamente con un objeto JSON válido. NO incluyas:
- Bloques de código markdown
- Texto explicativo antes o después del JSON
- Comillas dobles dentro de valores de texto
- Caracteres de escape inválidos

ESTRUCTURA EXACTA DEL JSON:
{
  "pruebas": [
    {
      "nombre": "test_[accion]_[condicion]_[resultado]",
      "descripcion": "Descripción clara sin usar comillas dobles internas",
      "especificacion_relacionada": "ID o nombre de la especificación que cubre",
      "detalles": {
        "objetivo": "Objetivo específico de la prueba",
        "precondiciones": [
          "Lista de condiciones sin comillas dobles internas"
        ],
        "pasos": [
          {
            "paso": 1,
            "accion": "código Python ejecutable",
            "resultado_esperado": "Descripción del resultado esperado"
          }
        ],
        "datos_prueba": {
          "entrada": "diccionario Python literal con datos de entrada",
          "salida_esperada": "diccionario Python literal con resultado esperado"
        },
        "criterios_aceptacion": [
          "Lista de condiciones que deben cumplirse para que la prueba pase"
        ],
        "tipo_validacion": "funcional"
      }
    }
  ]
}

8. CONSIDERACIONES TÉCNICAS
- Usa fixtures de pytest cuando sea apropiado
- Utiliza mocks para dependencias externas
- Implementa parametrize para casos similares con diferentes datos
- Usa asserts específicos de pytest
- Considera el uso de markers para categorizar pruebas

9. CALIDAD Y MANTENIBILIDAD
- Cada prueba debe ser independiente y poder ejecutarse aisladamente
- Los nombres deben ser descriptivos y auto-explicativos
- El código debe ser limpio y seguir PEP 8
- Las aserciones deben incluir mensajes descriptivos cuando sea relevante
- Evita lógica compleja dentro de las pruebas

GENERA AHORA EL JSON CON LAS PRUEBAS. Responde ÚNICAMENTE con el JSON, sin bloques de código markdown ni texto adicional:"""

    return prompt

import re
import re
import json

def extraer_json_de_respuesta(texto):
    """
    Extrae y limpia JSON de la respuesta de la IA, manejando múltiples problemas comunes.
    """
    try:
        # Paso 1: Extraer el contenido JSON
        json_str = texto.strip()
        
        # Remover bloques de código markdown
        if '```json' in json_str:
            inicio = json_str.find('```json') + 7
            fin = json_str.find('```', inicio)
            if fin == -1:
                fin = len(json_str)
            json_str = json_str[inicio:fin].strip()
        elif '```' in json_str:
            inicio = json_str.find('```') + 3
            fin = json_str.find('```', inicio)
            if fin == -1:
                fin = len(json_str)
            json_str = json_str[inicio:fin].strip()
        
        # Buscar entre llaves si no se encontró markdown
        if not json_str.startswith('{'):
            inicio = json_str.find('{')
            fin = json_str.rfind('}') + 1
            if inicio != -1 and fin > inicio:
                json_str = json_str[inicio:fin]
        
        # Paso 2: Limpiar saltos de línea literales dentro de strings
        # Esto es CRÍTICO para evitar "Invalid control character"
        def limpiar_strings(match):
            """Limpia el contenido de un string JSON"""
            content = match.group(1)
            # Reemplazar saltos de línea literales por espacios
            content = content.replace('\n', ' ')
            content = content.replace('\r', ' ')
            content = content.replace('\t', ' ')
            # Reemplazar múltiples espacios por uno solo
            content = re.sub(r'\s+', ' ', content)
            # Escapar comillas dobles internas
            content = content.replace('"', '\\"')
            return f'"{content}"'
        
        # Aplicar limpieza a todos los valores de string
        # Este patrón captura: "cualquier contenido" después de :
        json_str = re.sub(
            r':\s*"([^"\\]*(?:\\.[^"\\]*)*)"',
            lambda m: ': "' + m.group(1).replace('\n', ' ').replace('\r', ' ').replace('\t', ' ') + '"',
            json_str,
            flags=re.DOTALL
        )
        
        # Paso 3: Intentar parsear
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"[DEBUG] Error en primer intento: {e}")
            print(f"[DEBUG] Posición del error: línea {e.lineno}, columna {e.colno}")
            
            # Paso 4: Limpieza más agresiva
            # Dividir en líneas y limpiar cada una
            lines = json_str.split('\n')
            cleaned_lines = []
            
            for line in lines:
                # Si la línea contiene un valor de string con saltos de línea
                if '": "' in line or "': '" in line:
                    # Encontrar todas las posiciones de comillas
                    parts = line.split('": "', 1)
                    if len(parts) == 2:
                        key_part = parts[0]
                        value_part = parts[1]
                        
                        # Limpiar la parte del valor
                        # Encontrar el final del string (última comilla antes de , o } o ])
                        end_markers = [',', '}', ']']
                        end_pos = len(value_part)
                        
                        for marker in end_markers:
                            pos = value_part.rfind('"')
                            if pos != -1:
                                end_pos = pos
                                break
                        
                        if end_pos < len(value_part):
                            value_content = value_part[:end_pos]
                            value_rest = value_part[end_pos:]
                            
                            # Limpiar saltos de línea y tabs
                            value_content = value_content.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
                            value_content = re.sub(r'\s+', ' ', value_content)
                            
                            line = key_part + '": "' + value_content + value_rest
                
                cleaned_lines.append(line)
            
            json_str_cleaned = '\n'.join(cleaned_lines)
            
            try:
                return json.loads(json_str_cleaned)
            except json.JSONDecodeError as e2:
                print(f"[DEBUG] Error en segundo intento: {e2}")
                
                # Paso 5: Método más agresivo - procesar carácter por carácter
                result = []
                in_string = False
                escape_next = False
                
                for i, char in enumerate(json_str_cleaned):
                    if escape_next:
                        result.append(char)
                        escape_next = False
                        continue
                    
                    if char == '\\':
                        result.append(char)
                        escape_next = True
                        continue
                    
                    if char == '"':
                        in_string = not in_string
                        result.append(char)
                        continue
                    
                    # Si estamos dentro de un string y encontramos caracteres de control
                    if in_string:
                        if char in ['\n', '\r', '\t']:
                            result.append(' ')  # Reemplazar por espacio
                        elif ord(char) < 32:  # Otros caracteres de control
                            result.append(' ')
                        else:
                            result.append(char)
                    else:
                        result.append(char)
                
                json_str_final = ''.join(result)
                return json.loads(json_str_final)
        
    except json.JSONDecodeError as e:
        # Guardar información detallada del error
        error_pos = getattr(e, 'pos', 0)
        start = max(0, error_pos - 100)
        end = min(len(json_str), error_pos + 100)
        context = json_str[start:end]
        
        print(f"[ERROR] JSON problemático (contexto):")
        print(f"[ERROR] ...{context}...")
        print(f"[ERROR] Posición del error: {error_pos}")
        
        raise ValueError(
            f"No se pudo extraer JSON válido de la respuesta de la IA. "
            f"Error: {str(e)}. "
            f"Línea: {getattr(e, 'lineno', '?')}, Columna: {getattr(e, 'colno', '?')}. "
            f"Contexto: ...{context}..."
        )
    
    except Exception as e:
        raise ValueError(f"Error inesperado al procesar la respuesta de la IA: {str(e)}")


def limpiar_json_ia(json_str):
    """
    Función auxiliar para pre-limpiar el JSON antes del parseo principal.
    Maneja casos específicos de formato de código Python multi-línea.
    """
    # Remover bloques markdown
    json_str = re.sub(r'```json\s*', '', json_str)
    json_str = re.sub(r'```\s*', '', json_str)
    
    # Encontrar el JSON real
    inicio = json_str.find('{')
    fin = json_str.rfind('}') + 1
    if inicio != -1 and fin > inicio:
        json_str = json_str[inicio:fin]
    
    # Reemplazar saltos de línea literales en valores de string
    # Patrón para capturar: "accion": "código con\nsaltos\nde línea"
    def fix_multiline_code(match):
        key = match.group(1)
        value = match.group(2)
        # Convertir saltos de línea a espacios y limpiar
        value_clean = value.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        value_clean = re.sub(r'\s+', ' ', value_clean).strip()
        return f'"{key}": "{value_clean}"'
    
    # Aplicar fix a campos que típicamente contienen código
    json_str = re.sub(
        r'"(accion|codigo|entrada|salida_esperada)":\s*"([^"]*(?:\n[^"]*)*)"',
        fix_multiline_code,
        json_str,
        flags=re.DOTALL
    )
    
    return json_str