from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
import json
import os
from google import genai
from django.conf import settings

# Importar modelos necesarios
from pruebas.models import TiposPrueba, Pruebas
from proyectos.models import Proyectos
from usuarios.views import validar_token
from usuarios.models import Usuarios
from proyectos.views import cambiar_proyecto_a_generacion
from esquemas_bd.models import *
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
    """
    prefijo = PREFIJOS_TIPO_PRUEBA.get(
        tipo_prueba_nombre.lower(), 
        'TEST'
    )
    
    try:
        tipo_prueba = TiposPrueba.objects.get(nombre=tipo_prueba_nombre.lower())
    except TiposPrueba.DoesNotExist:
        tipo_prueba = None
    
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
    
    numero_prueba = count + 1
    codigo = f"{prefijo}-P{proyecto_id:03d}-{numero_prueba:03d}"
    
    return codigo


def obtener_especificaciones_proyecto(proyecto_id):
    """
    Obtiene todas las especificaciones de un proyecto
    """
    especificaciones = {
        'tiene_especificaciones': False,
        'requisitos': [],
        'historias_usuario': [],
        'casos_uso': []
    }

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

    especificaciones['tiene_especificaciones'] = (
        len(especificaciones['requisitos']) > 0 or
        len(especificaciones['historias_usuario']) > 0 or
        len(especificaciones['casos_uso']) > 0
    )

    return especificaciones


def cargar_template_prompt(especificaciones):
    """
    Carga el template del prompt desde el archivo pruebas_unitarias.txt
    y lo rellena con las especificaciones del proyecto.
    
    Args:
        especificaciones: Dict con proyecto, requisitos, historias y casos de uso
    
    Returns:
        String con el prompt completo listo para usar
    """
    try:
        # Construir la ruta al archivo dentro de la app 'chat'
        views_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.join(views_dir, 'prompts', 'pruebas_unitarias.txt')
        
        # Verificar si el archivo existe
        if not os.path.exists(prompt_path):
            raise FileNotFoundError(f"Archivo de prompt no encontrado en: {prompt_path}")
        
        # Leer el archivo
        with open(prompt_path, 'r', encoding='utf-8') as f:
            template = f.read()
        
        proyecto = especificaciones['proyecto']
        
        # Preparar las especificaciones formateadas
        especificaciones_requisitos = ""
        if especificaciones['requisitos']:
            especificaciones_requisitos = "REQUISITOS DEL SISTEMA:\n"
            for req in especificaciones['requisitos']:
                especificaciones_requisitos += f"\nID: {req['id']}\n"
                especificaciones_requisitos += f"Nombre: {req['nombre']}\n"
                especificaciones_requisitos += f"Descripción: {req['descripcion']}\n"
                especificaciones_requisitos += f"Tipo: {req['tipo']}\n"
                especificaciones_requisitos += f"Criterios de aceptación: {req['criterios']}\n"
                if req.get('condiciones_previas'):
                    especificaciones_requisitos += f"Condiciones previas: {req['condiciones_previas']}\n"
                especificaciones_requisitos += "---\n"
        
        especificaciones_historias = ""
        if especificaciones['historias_usuario']:
            especificaciones_historias = "\nHISTORIAS DE USUARIO:\n"
            for historia in especificaciones['historias_usuario']:
                especificaciones_historias += f"\nID: {historia['id']}\n"
                especificaciones_historias += f"Título: {historia['titulo']}\n"
                especificaciones_historias += f"Como {historia['actor_rol']}, quiero {historia['funcionalidad_accion']} para {historia['beneficio_razon']}\n"
                especificaciones_historias += f"Criterios de aceptación: {historia['criterios_aceptacion']}\n"
                especificaciones_historias += "---\n"
        
        especificaciones_casos = ""
        if especificaciones['casos_uso']:
            especificaciones_casos = "\nCASOS DE USO:\n"
            for caso in especificaciones['casos_uso']:
                especificaciones_casos += f"\nID: {caso['id']}\n"
                especificaciones_casos += f"Nombre: {caso['nombre']}\n"
                especificaciones_casos += f"Descripción: {caso['descripcion']}\n"
                especificaciones_casos += f"Actores: {caso['actores']}\n"
                especificaciones_casos += f"Precondiciones: {caso['precondiciones']}\n"
                especificaciones_casos += f"Flujo principal: {caso['flujo_principal']}\n"
                if caso.get('flujos_alternativos'):
                    especificaciones_casos += f"Flujos alternativos: {caso['flujos_alternativos']}\n"
                especificaciones_casos += f"Postcondiciones: {caso['postcondiciones']}\n"
                especificaciones_casos += "---\n"
        
        # Serializar correctamente los atributos del proyecto
        proyecto_nombre = proyecto.nombre if hasattr(proyecto, 'nombre') else 'No especificado'
        proyecto_descripcion = proyecto.descripcion if hasattr(proyecto, 'descripcion') else 'No especificada'
        
        # Reemplazar usando replace() para evitar conflictos con llaves {}
        prompt_completo = template.replace(
            '{proyecto_nombre}', proyecto_nombre
        ).replace(
            '{proyecto_descripcion}', proyecto_descripcion
        ).replace(
            '{especificaciones_requisitos}', especificaciones_requisitos
        ).replace(
            '{especificaciones_historias}', especificaciones_historias
        ).replace(
            '{especificaciones_casos_uso}', especificaciones_casos
        )
        
        return prompt_completo
    
    except FileNotFoundError as e:
        print(f"[ERROR] {str(e)}")
        raise
    except Exception as e:
        print(f"[ERROR] Error al cargar el template del prompt: {str(e)}")
        raise


def parsear_respuesta_ia(texto):
    """
    Parsea la respuesta de la IA de forma simple y directa.
    Primero intenta JSON directo, luego extrae del markdown si es necesario.
    """
    texto = texto.strip()
    
    # Intentar parsear directamente
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        pass
    
    # Si falla, limpiar markdown y extraer JSON
    # Remover bloques markdown
    if '```json' in texto:
        inicio = texto.find('```json') + 7
        fin = texto.find('```', inicio)
        if fin != -1:
            texto = texto[inicio:fin].strip()
    elif '```' in texto:
        inicio = texto.find('```') + 3
        fin = texto.find('```', inicio)
        if fin != -1:
            texto = texto[inicio:fin].strip()
    
    # Buscar el objeto JSON principal
    inicio = texto.find('{')
    fin = texto.rfind('}') + 1
    if inicio != -1 and fin > inicio:
        texto = texto[inicio:fin]
    
    # Intentar parsear nuevamente
    try:
        return json.loads(texto)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"No se pudo parsear JSON: {e.msg} en línea {e.lineno}, columna {e.colno}"
        )


@csrf_exempt
@require_http_methods(["POST"])
def generar_pruebas_unitarias(request, proyecto_id):
    """
    Genera pruebas unitarias automáticamente usando IA y las guarda en la BD.
    """
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        print("=" * 50)
        print(f"[DEBUG] Iniciando generación para proyecto {proyecto_id}")
        
        # Obtener proyecto
        try:
            proyecto = Proyectos.objects.get(id=proyecto_id, activo=True)
            print(f"[DEBUG] Proyecto encontrado: {proyecto.nombre}, Estado: {proyecto.estado}")
        except Proyectos.DoesNotExist:
            print(f"[ERROR] Proyecto {proyecto_id} no existe")
            return JsonResponse({'error': 'El proyecto especificado no existe'}, status=404)

        # Obtener especificaciones
        print("[DEBUG] Obteniendo especificaciones...")
        especificaciones = obtener_especificaciones_proyecto(proyecto_id)
        especificaciones['proyecto'] = proyecto
        print(f"[DEBUG] Especificaciones obtenidas: {especificaciones['tiene_especificaciones']}")
        
        if not especificaciones['tiene_especificaciones']:
            return JsonResponse({
                'error': 'No hay especificaciones en el proyecto para generar pruebas'
            }, status=400)

        # Cargar prompt
        print("[DEBUG] Cargando template del prompt...")
        prompt = cargar_template_prompt(especificaciones)
        print(f"[DEBUG] Prompt cargado, longitud: {len(prompt)} caracteres")

        # Llamar a IA
        print("[DEBUG] Llamando a Gemini API...")
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[prompt]
        )
        print("[DEBUG] Respuesta de IA recibida")
        
        pruebas_generadas = response.text
        print(f"[DEBUG] Texto generado, primeros 200 chars: {pruebas_generadas[:200]}")

        # Parsear respuesta
        print("[DEBUG] Parseando respuesta...")
        try:
            pruebas_json = parsear_respuesta_ia(pruebas_generadas)
            print(f"[DEBUG] JSON parseado correctamente, {len(pruebas_json.get('pruebas', []))} pruebas")
        except ValueError as e:
            print(f"[ERROR] Error al parsear: {e}")
            return JsonResponse({
                'error': 'No se pudo procesar la respuesta de la IA',
                'detalle': str(e),
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

        # Guardar pruebas en BD
        print("[DEBUG] Guardando pruebas en BD...")
        pruebas_creadas = []
        with transaction.atomic():
            for idx, prueba_data in enumerate(pruebas_json.get('pruebas', [])):
                print(f"[DEBUG] Procesando prueba {idx + 1}...")
                
                # Generar código único
                codigo_generado = generar_codigo_prueba(proyecto_id, tipo_prueba.nombre)
                print(f"[DEBUG] Código generado: {codigo_generado}")
                
                # Procesar detalles
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
                
                # Crear prueba
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
            
            # Cambiar estado del proyecto
            if pruebas_creadas:
                print("[DEBUG] Cambiando estado del proyecto...")
                cambio_exitoso, mensaje_cambio = cambiar_proyecto_a_generacion(proyecto_id)
                print(f"[DEBUG] Cambio de estado: {cambio_exitoso}, {mensaje_cambio}")
                estado_actualizado = cambio_exitoso
            else:
                estado_actualizado = False
                mensaje_cambio = "No se crearon pruebas"

        # Refrescar proyecto
        proyecto.refresh_from_db()
        print(f"[DEBUG] Proceso completado exitosamente")
        print("=" * 50)

        # Serializar estado correctamente
        proyecto_estado = proyecto.estado.nombre if hasattr(proyecto.estado, 'nombre') else str(proyecto.estado)

        return JsonResponse({
            'mensaje': f'Se generaron {len(pruebas_creadas)} pruebas unitarias exitosamente',
            'proyecto_id': proyecto_id,
            'proyecto_nombre': proyecto.nombre,
            'proyecto_estado': proyecto_estado,
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
    """
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        # Obtener proyecto
        try:
            proyecto = Proyectos.objects.get(id=proyecto_id, activo=True)
        except Proyectos.DoesNotExist:
            return JsonResponse({'error': 'El proyecto especificado no existe'}, status=404)

        # Obtener especificaciones
        especificaciones = obtener_especificaciones_proyecto(proyecto_id)
        especificaciones['proyecto'] = proyecto
        
        if not especificaciones['tiene_especificaciones']:
            return JsonResponse({
                'error': 'No hay especificaciones en el proyecto para generar pruebas'
            }, status=400)

        # Cargar prompt
        prompt = cargar_template_prompt(especificaciones)

        # Llamar a IA
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[prompt]
        )

        pruebas_generadas = response.text
        
        # Parsear respuesta
        try:
            pruebas_json = parsear_respuesta_ia(pruebas_generadas)
        except ValueError as e:
            return JsonResponse({
                'error': 'No se pudo procesar la respuesta de la IA',
                'detalle': str(e)
            }, status=500)

        # Obtener tipo de prueba
        tipo_prueba, _ = TiposPrueba.objects.get_or_create(
            nombre="unitaria",
            defaults={
                'descripcion': 'Pruebas unitarias generadas automáticamente',
                'activo': True
            }
        )

        # Generar códigos provisionales
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

        # Serializar estado correctamente
        proyecto_estado_actual = proyecto.estado.nombre if hasattr(proyecto.estado, 'nombre') else str(proyecto.estado)

        return JsonResponse({
            'mensaje': 'Pruebas generadas (sin guardar)',
            'proyecto_id': proyecto_id,
            'proyecto_nombre': proyecto.nombre,
            'proyecto_estado_actual': proyecto_estado_actual,
            'total_pruebas': len(pruebas_con_codigo),
            'pruebas': pruebas_con_codigo,
            'info': 'Los códigos mostrados son provisionales. Al guardar, el proyecto pasará a fase "Generación"'
        }, status=200)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'Error al generar pruebas: {str(e)}'}, status=500)


# ========================================
# GENERAR ESQUEMA DE BASE DE DATOS CON IA
# ========================================

def cargar_template_prompt_esquema_bd(proyecto, tipo_motor, especificaciones):
    """
    Carga el template del prompt desde esquema_bd.txt y lo rellena con datos.
    
    Args:
        proyecto: Instancia del modelo Proyectos
        tipo_motor: Instancia del modelo TiposMotorBd
        especificaciones: Dict con requisitos, historias y casos de uso
    
    Returns:
        String con el prompt completo listo para usar
    """
    try:
        # Construir la ruta al archivo
        views_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.join(views_dir, 'prompts', 'esquema_bd.txt')
        
        # Verificar si el archivo existe
        if not os.path.exists(prompt_path):
            raise FileNotFoundError(f"Archivo de prompt no encontrado en: {prompt_path}")
        
        # Leer el archivo
        with open(prompt_path, 'r', encoding='utf-8') as f:
            template = f.read()
        
        # Preparar especificaciones formateadas (reutilizando lógica similar)
        especificaciones_requisitos = ""
        if especificaciones['requisitos']:
            especificaciones_requisitos = "REQUISITOS DEL SISTEMA:\n"
            for req in especificaciones['requisitos']:
                especificaciones_requisitos += f"\n- {req['nombre']}: {req['descripcion']}\n"
                if req.get('criterios'):
                    especificaciones_requisitos += f"  Criterios: {req['criterios']}\n"
        
        especificaciones_historias = ""
        if especificaciones['historias_usuario']:
            especificaciones_historias = "\nHISTORIAS DE USUARIO:\n"
            for historia in especificaciones['historias_usuario']:
                especificaciones_historias += f"\n- {historia['titulo']}\n"
                especificaciones_historias += f"  Como {historia['actor_rol']}, quiero {historia['funcionalidad_accion']} para {historia['beneficio_razon']}\n"
                if historia.get('criterios_aceptacion'):
                    especificaciones_historias += f"  Criterios: {historia['criterios_aceptacion']}\n"
        
        especificaciones_casos = ""
        if especificaciones['casos_uso']:
            especificaciones_casos = "\nCASOS DE USO:\n"
            for caso in especificaciones['casos_uso']:
                especificaciones_casos += f"\n- {caso['nombre']}: {caso['descripcion']}\n"
                if caso.get('actores'):
                    especificaciones_casos += f"  Actores: {caso['actores']}\n"
                if caso.get('precondiciones'):
                    especificaciones_casos += f"  Precondiciones: {caso['precondiciones']}\n"
        
        # Extraer datos del proyecto y motor de forma segura
        proyecto_nombre = proyecto.nombre if hasattr(proyecto, 'nombre') else 'No especificado'
        proyecto_descripcion = proyecto.descripcion if hasattr(proyecto, 'descripcion') else 'No especificada'
        motor_nombre = tipo_motor.nombre if hasattr(tipo_motor, 'nombre') else 'No especificado'
        
        # Reemplazar placeholders
        prompt_completo = template.replace(
            '{motor_nombre}', motor_nombre
        ).replace(
            '{proyecto_nombre}', proyecto_nombre
        ).replace(
            '{proyecto_descripcion}', proyecto_descripcion
        ).replace(
            '{especificaciones_requisitos}', especificaciones_requisitos
        ).replace(
            '{especificaciones_historias}', especificaciones_historias
        ).replace(
            '{especificaciones_casos_uso}', especificaciones_casos
        )
        
        return prompt_completo
    
    except FileNotFoundError as e:
        print(f"[ERROR] {str(e)}")
        raise
    except Exception as e:
        print(f"[ERROR] Error al cargar el template del prompt de esquema BD: {str(e)}")
        raise


@csrf_exempt
@require_http_methods(["POST"])
def generar_esquema_bd(request, proyecto_id):
    """
    Genera un esquema de base de datos automáticamente basado en las 
    especificaciones del proyecto (requisitos, historias, casos de uso).
    Permite múltiples esquemas por proyecto (diferentes motores).
    """
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        body = json.loads(request.body)
        tipo_motor_id = body.get('tipo_motor_id')
        
        if not tipo_motor_id:
            return JsonResponse({
                'error': 'El campo tipo_motor_id es requerido'
            }, status=400)
        
        print("=" * 60)
        print(f"[DEBUG] Iniciando generación de esquema para proyecto {proyecto_id}")
        print(f"[DEBUG] Tipo de motor: {tipo_motor_id}")
        
        # Validar proyecto
        try:
            proyecto = Proyectos.objects.get(id=proyecto_id, activo=True)
            print(f"[DEBUG] Proyecto encontrado: {proyecto.nombre}")
        except Proyectos.DoesNotExist:
            print(f"[ERROR] Proyecto {proyecto_id} no existe")
            return JsonResponse({
                'error': 'El proyecto especificado no existe'
            }, status=404)
        
        # Validar tipo de motor
        try:
            tipo_motor = TiposMotorBd.objects.get(id=tipo_motor_id, activo=True)
            print(f"[DEBUG] Motor de BD: {tipo_motor.nombre}")
        except TiposMotorBd.DoesNotExist:
            print(f"[ERROR] Tipo de motor {tipo_motor_id} no existe")
            return JsonResponse({
                'error': 'El tipo de motor especificado no existe'
            }, status=404)
        
        # Obtener especificaciones (reutilizando función)
        print("[DEBUG] Obteniendo especificaciones del proyecto...")
        especificaciones = obtener_especificaciones_proyecto(proyecto_id)
        print(f"[DEBUG] Especificaciones obtenidas")
        
        if not especificaciones['tiene_especificaciones']:
            print("[ERROR] No hay especificaciones en el proyecto")
            return JsonResponse({
                'error': 'El proyecto debe tener al menos un requisito, historia de usuario o caso de uso para generar el esquema de BD'
            }, status=400)
        
        # Verificar que no exista esquema para este proyecto + motor específico
        if EsquemasBd.objects.filter(
            proyecto_id=proyecto_id, 
            tipo_motor_bd_id=tipo_motor_id,
            activo=True
        ).exists():
            print("[ADVERTENCIA] Ya existe un esquema para este proyecto + motor")
            return JsonResponse({
                'error': f'Ya existe un esquema activo para {tipo_motor.nombre}. Edita el existente o desactívalo primero'
            }, status=409)
        
        # Cargar prompt desde template
        print("[DEBUG] Cargando template del prompt...")
        prompt = cargar_template_prompt_esquema_bd(proyecto, tipo_motor, especificaciones)
        print(f"[DEBUG] Prompt cargado, longitud: {len(prompt)} caracteres")
        
        # Llamar a IA
        print("[DEBUG] Llamando a Gemini API...")
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[prompt]
        )
        print("[DEBUG] Respuesta de IA recibida")
        
        respuesta_ia = response.text
        print(f"[DEBUG] Primeros 300 caracteres: {respuesta_ia[:300]}")
        
        # Parsear respuesta (reutilizando lógica)
        print("[DEBUG] Parseando respuesta...")
        try:
            esquema_json = parsear_respuesta_ia(respuesta_ia)
            print("[DEBUG] JSON parseado correctamente")
        except ValueError as e:
            print(f"[ERROR] Error al parsear: {e}")
            return JsonResponse({
                'error': 'No se pudo procesar la respuesta de la IA',
                'detalle': str(e),
                'respuesta_ia': respuesta_ia[:500]
            }, status=500)
        
        # Validar estructura del esquema
        print("[DEBUG] Validando estructura del esquema...")
        if not esquema_json.get('tablas'):
            print("[ERROR] El esquema no contiene tablas")
            return JsonResponse({
                'error': 'El esquema generado no contiene tablas válidas'
            }, status=500)
        
        # Guardar esquema
        print("[DEBUG] Guardando esquema en BD...")
        try:
            with transaction.atomic():
                esquema = EsquemasBd.objects.create(
                    proyecto=proyecto,
                    tipo_motor_bd=tipo_motor,
                    esquema=esquema_json,
                    activo=True
                )
                print(f"[DEBUG] Esquema guardado con ID: {esquema.id}")
        except Exception as db_error:
            print(f"[ERROR] Error al guardar en BD: {db_error}")
            return JsonResponse({
                'error': f'Error al guardar el esquema: {str(db_error)}'
            }, status=500)
        
        print("[DEBUG] Proceso completado exitosamente")
        print("=" * 60)
        
        return JsonResponse({
            'mensaje': 'Esquema de BD generado exitosamente',
            'esquema_id': esquema.id,
            'proyecto_id': proyecto_id,
            'proyecto_nombre': proyecto.nombre,
            'motor_bd': tipo_motor.nombre,
            'tablas': list(esquema_json.get('tablas', {}).keys()),
            'total_tablas': len(esquema_json.get('tablas', {})),
            'esquema': esquema_json
        }, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'El body de la solicitud no es JSON válido'
        }, status=400)
    except Exception as e:
        import traceback
        print("=" * 60)
        print(f"[ERROR FATAL] {str(e)}")
        traceback.print_exc()
        print("=" * 60)
        return JsonResponse({
            'error': f'Error al generar esquema: {str(e)}'
        }, status=500)
    
@csrf_exempt
@require_http_methods(["POST"])
def previsualizar_esquema_bd(request, proyecto_id):
    """
    Genera un esquema de BD sin guardar, permite al usuario revisarlo primero.
    """
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        body = json.loads(request.body)
        tipo_motor_id = body.get('tipo_motor_id')
        
        if not tipo_motor_id:
            return JsonResponse({
                'error': 'El campo tipo_motor_id es requerido'
            }, status=400)
        
        # Validar proyecto
        try:
            proyecto = Proyectos.objects.get(id=proyecto_id, activo=True)
        except Proyectos.DoesNotExist:
            return JsonResponse({
                'error': 'El proyecto especificado no existe'
            }, status=404)
        
        # Validar tipo de motor
        try:
            tipo_motor = TiposMotorBd.objects.get(id=tipo_motor_id, activo=True)
        except TiposMotorBd.DoesNotExist:
            return JsonResponse({
                'error': 'El tipo de motor especificado no existe'
            }, status=404)
        
        # Obtener especificaciones (reutilizando función)
        especificaciones = obtener_especificaciones_proyecto(proyecto_id)
        
        if not especificaciones['tiene_especificaciones']:
            return JsonResponse({
                'error': 'El proyecto debe tener al menos una especificación'
            }, status=400)
        
        # Generar prompt desde template
        prompt = cargar_template_prompt_esquema_bd(proyecto, tipo_motor, especificaciones)
        
        # Llamar a IA
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[prompt]
        )
        
        respuesta_ia = response.text
        
        # Parsear respuesta (reutilizando función)
        try:
            esquema_json = parsear_respuesta_ia(respuesta_ia)
        except ValueError as e:
            return JsonResponse({
                'error': 'No se pudo procesar la respuesta de la IA',
                'detalle': str(e)
            }, status=500)
        
        return JsonResponse({
            'mensaje': 'Esquema generado (sin guardar)',
            'proyecto_id': proyecto_id,
            'proyecto_nombre': proyecto.nombre,
            'motor_bd': tipo_motor.nombre,
            'tablas': list(esquema_json.get('tablas', {}).keys()),
            'total_tablas': len(esquema_json.get('tablas', {})),
            'esquema': esquema_json,
            'info': 'Esta es una previsualización. Los datos no se guardarán hasta que confirmes'
        }, status=200)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'El body de la solicitud no es JSON válido'
        }, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'error': f'Error al generar esquema: {str(e)}'
        }, status=500)