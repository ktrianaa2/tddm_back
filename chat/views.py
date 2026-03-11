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
    'componente': 'COMP-TEST',
    'integracion': 'INT-TEST',
    'sistema': 'SYS-TEST',
}

# Mapeo de archivo de prompt por tipo
PROMPT_FILES = {
    'unitaria': 'pruebas_unitarias.txt',
    'componente': 'pruebas_componentes.txt',
    'sistema': 'pruebas_sistema.txt',
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


def _formatear_especificaciones_texto(especificaciones):
    """
    Formatea las especificaciones del proyecto como texto para el prompt.
    Retorna un dict con las secciones formateadas.
    """
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

    return {
        'requisitos': especificaciones_requisitos,
        'historias': especificaciones_historias,
        'casos_uso': especificaciones_casos,
    }


def cargar_template_prompt(especificaciones):
    """
    Carga el template del prompt para pruebas unitarias.
    """
    return _cargar_prompt_por_tipo(especificaciones, 'unitaria')


def _cargar_prompt_por_tipo(especificaciones, tipo_prueba):
    """
    Carga el template del prompt según el tipo de prueba y lo rellena con datos.

    Args:
        especificaciones: Dict con proyecto, requisitos, historias y casos de uso
        tipo_prueba: 'unitaria' | 'componente' | 'sistema'

    Returns:
        String con el prompt completo listo para usar
    """
    archivo_prompt = PROMPT_FILES.get(tipo_prueba, 'pruebas_unitarias.txt')

    try:
        views_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.join(views_dir, 'prompts', archivo_prompt)

        if not os.path.exists(prompt_path):
            raise FileNotFoundError(f"Archivo de prompt no encontrado en: {prompt_path}")

        with open(prompt_path, 'r', encoding='utf-8') as f:
            template = f.read()

        proyecto = especificaciones['proyecto']
        secciones = _formatear_especificaciones_texto(especificaciones)

        proyecto_nombre = proyecto.nombre if hasattr(proyecto, 'nombre') else 'No especificado'
        proyecto_descripcion = proyecto.descripcion if hasattr(proyecto, 'descripcion') else 'No especificada'

        prompt_completo = template.replace(
            '{proyecto_nombre}', proyecto_nombre
        ).replace(
            '{proyecto_descripcion}', proyecto_descripcion
        ).replace(
            '{especificaciones_requisitos}', secciones['requisitos']
        ).replace(
            '{especificaciones_historias}', secciones['historias']
        ).replace(
            '{especificaciones_casos_uso}', secciones['casos_uso']
        )

        return prompt_completo

    except FileNotFoundError as e:
        print(f"[ERROR] {str(e)}")
        raise
    except Exception as e:
        print(f"[ERROR] Error al cargar el template del prompt ({tipo_prueba}): {str(e)}")
        raise


def parsear_respuesta_ia(texto):
    """
    Parsea la respuesta de la IA de forma robusta.
    Maneja: bloques markdown, comillas simples, comas finales,
    texto previo/posterior al JSON y otras variantes de Gemini.
    """
    import re

    if not texto or not texto.strip():
        raise ValueError("La IA devolvió una respuesta vacía")

    texto = texto.strip()

    # --- Intento 1: JSON directo ---
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        pass

    # --- Intento 2: Extraer de bloque markdown ```json ... ``` o ``` ... ``` ---
    for patron in [r'```json\s*([\s\S]*?)```', r'```\s*([\s\S]*?)```']:
        match = re.search(patron, texto, re.DOTALL)
        if match:
            candidato = match.group(1).strip()
            try:
                return json.loads(candidato)
            except json.JSONDecodeError:
                texto = candidato  # Seguir procesando este candidato
                break

    # --- Intento 3: Extraer el bloque JSON más externo { ... } ---
    inicio = texto.find('{')
    fin = texto.rfind('}') + 1
    if inicio != -1 and fin > inicio:
        texto = texto[inicio:fin]

    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        pass

    # --- Intento 4: Limpiar comas finales antes de } o ] (JSON5 style) ---
    # Gemini a veces genera {"key": "val",} o ["a","b",]
    texto_limpio = re.sub(r',\s*([}\]])', r'\1', texto)
    try:
        return json.loads(texto_limpio)
    except json.JSONDecodeError:
        pass

    # --- Intento 5: Reemplazar comillas simples por dobles con cuidado ---
    # Solo si el JSON parece usar comillas simples como delimitador principal
    if texto_limpio.count("'") > texto_limpio.count('"'):
        try:
            # Escapar comillas dobles internas, luego reemplazar simples
            texto_comillas = texto_limpio.replace('"', '\\"')
            texto_comillas = texto_comillas.replace("'", '"')
            return json.loads(texto_comillas)
        except json.JSONDecodeError:
            pass

    # --- Intento 6: Usar ast.literal_eval como último recurso ---
    import ast
    try:
        resultado = ast.literal_eval(texto_limpio)
        if isinstance(resultado, dict):
            # Convertir a JSON y volver a parsear para normalizar
            return json.loads(json.dumps(resultado))
    except (ValueError, SyntaxError):
        pass

    # --- Sin solución: reportar error con contexto útil ---
    preview = texto[:300].replace('\n', ' ')
    raise ValueError(
        f"No se pudo parsear la respuesta de la IA como JSON válido. "
        f"Primeros 300 chars: {preview}"
    )


def _guardar_pruebas_en_bd(proyecto, tipo_prueba_nombre, pruebas_json):
    """
    Lógica reutilizable para guardar pruebas en BD.
    """
    # Asegurar que tipo_prueba_nombre sea string
    if not isinstance(tipo_prueba_nombre, str):
        tipo_prueba_nombre = str(tipo_prueba_nombre)

    tipo_prueba, _ = TiposPrueba.objects.get_or_create(
        nombre=tipo_prueba_nombre.lower(),
        defaults={
            'descripcion': f'Pruebas de {tipo_prueba_nombre} generadas automáticamente',
            'activo': True
        }
    )

    def _to_str(value, max_len=None):
        """Convierte cualquier valor a string de forma segura."""
        if value is None:
            return ''
        if isinstance(value, (dict, list)):
            result = json.dumps(value, ensure_ascii=False)
        else:
            result = str(value)
        if max_len:
            result = result[:max_len]
        return result

    pruebas_creadas = []
    with transaction.atomic():
        for idx, prueba_data in enumerate(pruebas_json.get('pruebas', [])):
            codigo_generado = generar_codigo_prueba(proyecto.id, tipo_prueba.nombre)

            # ── detalles ──────────────────────────────────────────────
            detalles_completos = prueba_data.get('detalles', {})
            if isinstance(detalles_completos, str):
                try:
                    detalles_completos = json.loads(detalles_completos)
                except Exception:
                    detalles_completos = {}
            if not isinstance(detalles_completos, dict):
                detalles_completos = {}

            # Si detalles está vacío, usar el resto de prueba_data
            if not detalles_completos:
                detalles_completos = {
                    k: v for k, v in prueba_data.items()
                    if k not in ('nombre', 'descripcion', 'especificacion_relacionada')
                }

            prueba_json_str = json.dumps(detalles_completos, ensure_ascii=False)

            # ── especificacion_relacionada ─────────────────────────────
            especificacion_relacionada = _to_str(
                prueba_data.get('especificacion_relacionada', ''), max_len=100
            )

            # ── nombre y descripcion ───────────────────────────────────
            nombre = _to_str(
                prueba_data.get('nombre', f'Prueba {codigo_generado}')
            )
            descripcion = _to_str(prueba_data.get('descripcion', ''))

            prueba = Pruebas.objects.create(
                proyecto=proyecto,
                tipo_prueba=tipo_prueba,
                codigo=codigo_generado,
                nombre=nombre,
                descripcion=descripcion,
                estado='Pendiente',
                especificacion_relacionada=especificacion_relacionada,
                prueba=prueba_json_str,
                activo=True
            )

            pruebas_creadas.append({
                'id': prueba.id,
                'codigo': prueba.codigo,
                'nombre': prueba.nombre,
                'descripcion': prueba.descripcion,
                'tipo': tipo_prueba_nombre
            })

    return pruebas_creadas, tipo_prueba

def _generar_pruebas_por_tipo(request, proyecto_id, tipo_prueba):
    """
    Lógica genérica reutilizable para generar pruebas de cualquier tipo.
    """
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        print("=" * 50)
        print(f"[DEBUG] Generando pruebas tipo '{tipo_prueba}' para proyecto {proyecto_id}")

        try:
            proyecto = Proyectos.objects.get(id=proyecto_id, activo=True)
        except Proyectos.DoesNotExist:
            return JsonResponse({'error': 'El proyecto especificado no existe'}, status=404)

        especificaciones = obtener_especificaciones_proyecto(proyecto_id)
        especificaciones['proyecto'] = proyecto

        if not especificaciones['tiene_especificaciones']:
            return JsonResponse({
                'error': 'No hay especificaciones en el proyecto para generar pruebas'
            }, status=400)

        prompt = _cargar_prompt_por_tipo(especificaciones, tipo_prueba)

        print(f"[DEBUG] Llamando a Gemini API para pruebas de {tipo_prueba}...")
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[prompt]
        )

        pruebas_generadas = response.text

        try:
            pruebas_json = parsear_respuesta_ia(pruebas_generadas)
        except ValueError as e:
            return JsonResponse({
                'error': 'No se pudo procesar la respuesta de la IA',
                'detalle': str(e),
                'respuesta_ia': pruebas_generadas[:500]
            }, status=500)

        pruebas_creadas, tipo_prueba_obj = _guardar_pruebas_en_bd(proyecto, tipo_prueba, pruebas_json)

        if pruebas_creadas:
            cambio_exitoso, mensaje_cambio = cambiar_proyecto_a_generacion(proyecto_id)
            estado_actualizado = cambio_exitoso
        else:
            estado_actualizado = False
            mensaje_cambio = "No se crearon pruebas"

        proyecto.refresh_from_db()
        proyecto_estado = proyecto.estado.nombre if hasattr(proyecto.estado, 'nombre') else str(proyecto.estado)

        print(f"[DEBUG] Generadas {len(pruebas_creadas)} pruebas de {tipo_prueba}")
        print("=" * 50)

        return JsonResponse({
            'mensaje': f'Se generaron {len(pruebas_creadas)} pruebas de {tipo_prueba} exitosamente',
            'proyecto_id': proyecto_id,
            'proyecto_nombre': proyecto.nombre,
            'proyecto_estado': proyecto_estado,
            'cambio_estado': estado_actualizado,
            'mensaje_cambio_estado': mensaje_cambio,
            'tipo_prueba': tipo_prueba,
            'pruebas_creadas': pruebas_creadas,
            'total_pruebas': len(pruebas_creadas)
        }, status=201)

    except Exception as e:
        import traceback
        print(f"[ERROR FATAL] {str(e)}")
        traceback.print_exc()
        return JsonResponse({'error': f'Error al generar pruebas: {str(e)}'}, status=500)


def _previsualizar_pruebas_por_tipo(request, proyecto_id, tipo_prueba):
    """
    Lógica genérica reutilizable para previsualizar pruebas de cualquier tipo (sin guardar).
    """
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        try:
            proyecto = Proyectos.objects.get(id=proyecto_id, activo=True)
        except Proyectos.DoesNotExist:
            return JsonResponse({'error': 'El proyecto especificado no existe'}, status=404)

        especificaciones = obtener_especificaciones_proyecto(proyecto_id)
        especificaciones['proyecto'] = proyecto

        if not especificaciones['tiene_especificaciones']:
            return JsonResponse({
                'error': 'No hay especificaciones en el proyecto para generar pruebas'
            }, status=400)

        prompt = _cargar_prompt_por_tipo(especificaciones, tipo_prueba)

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[prompt]
        )

        pruebas_generadas = response.text

        try:
            pruebas_json = parsear_respuesta_ia(pruebas_generadas)
        except ValueError as e:
            return JsonResponse({
                'error': 'No se pudo procesar la respuesta de la IA',
                'detalle': str(e)
            }, status=500)

        tipo_prueba_obj, _ = TiposPrueba.objects.get_or_create(
            nombre=tipo_prueba.lower(),
            defaults={
                'descripcion': f'Pruebas de {tipo_prueba} generadas automáticamente',
                'activo': True
            }
        )

        pruebas_con_codigo = []
        contador = Pruebas.objects.filter(
            proyecto_id=proyecto_id,
            tipo_prueba=tipo_prueba_obj,
            activo=True
        ).count()

        for idx, prueba in enumerate(pruebas_json.get('pruebas', []), start=1):
            prefijo = PREFIJOS_TIPO_PRUEBA.get(tipo_prueba_obj.nombre.lower(), 'TEST')
            codigo_provisional = f"{prefijo}-P{proyecto_id:03d}-{contador + idx:03d}"
            prueba['codigo_provisional'] = codigo_provisional
            prueba['tipo_prueba'] = tipo_prueba
            pruebas_con_codigo.append(prueba)

        proyecto_estado_actual = proyecto.estado.nombre if hasattr(proyecto.estado, 'nombre') else str(proyecto.estado)

        return JsonResponse({
            'mensaje': f'Pruebas de {tipo_prueba} generadas (sin guardar)',
            'proyecto_id': proyecto_id,
            'proyecto_nombre': proyecto.nombre,
            'proyecto_estado_actual': proyecto_estado_actual,
            'tipo_prueba': tipo_prueba,
            'total_pruebas': len(pruebas_con_codigo),
            'pruebas': pruebas_con_codigo,
            'info': f'Los códigos mostrados son provisionales. Al guardar, el proyecto pasará a fase "Generación"'
        }, status=200)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'Error al generar pruebas: {str(e)}'}, status=500)


# ============================================================
# ENDPOINTS PRUEBAS UNITARIAS
# ============================================================

@csrf_exempt
@require_http_methods(["POST"])
def generar_pruebas_unitarias(request, proyecto_id):
    """Genera pruebas unitarias automáticamente usando IA y las guarda en la BD."""
    return _generar_pruebas_por_tipo(request, proyecto_id, 'unitaria')


@csrf_exempt
@require_http_methods(["POST"])
def previsualizar_pruebas(request, proyecto_id):
    """Genera pruebas unitarias pero no las guarda."""
    return _previsualizar_pruebas_por_tipo(request, proyecto_id, 'unitaria')


# ============================================================
# ENDPOINTS PRUEBAS DE COMPONENTE
# ============================================================

@csrf_exempt
@require_http_methods(["POST"])
def generar_pruebas_componente(request, proyecto_id):
    """Genera pruebas de componente/integración automáticamente usando IA."""
    return _generar_pruebas_por_tipo(request, proyecto_id, 'componente')


@csrf_exempt
@require_http_methods(["POST"])
def previsualizar_pruebas_componente(request, proyecto_id):
    """Genera pruebas de componente pero no las guarda."""
    return _previsualizar_pruebas_por_tipo(request, proyecto_id, 'componente')


# ============================================================
# ENDPOINTS PRUEBAS DE SISTEMA
# ============================================================

@csrf_exempt
@require_http_methods(["POST"])
def generar_pruebas_sistema(request, proyecto_id):
    """Genera pruebas de sistema/end-to-end automáticamente usando IA."""
    return _generar_pruebas_por_tipo(request, proyecto_id, 'sistema')


@csrf_exempt
@require_http_methods(["POST"])
def previsualizar_pruebas_sistema(request, proyecto_id):
    """Genera pruebas de sistema pero no las guarda."""
    return _previsualizar_pruebas_por_tipo(request, proyecto_id, 'sistema')


# ============================================================
# ENDPOINT GENERACIÓN MÚLTIPLE
# ============================================================

@csrf_exempt
@require_http_methods(["POST"])
def generar_pruebas_multiple(request, proyecto_id):
    """
    Genera pruebas de múltiples tipos en una sola llamada.
    Body esperado: { "tipos": ["unitaria", "componente", "sistema"] }
    Si no se envía 'tipos', genera todos los tipos.
    """
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        body = json.loads(request.body) if request.body else {}
        tipos_solicitados = body.get('tipos', ['unitaria', 'componente', 'sistema'])

        tipos_validos = [t for t in tipos_solicitados if t in PROMPT_FILES]
        if not tipos_validos:
            return JsonResponse({
                'error': f'Tipos inválidos. Tipos válidos: {list(PROMPT_FILES.keys())}'
            }, status=400)

        try:
            proyecto = Proyectos.objects.get(id=proyecto_id, activo=True)
        except Proyectos.DoesNotExist:
            return JsonResponse({'error': 'El proyecto especificado no existe'}, status=404)

        especificaciones = obtener_especificaciones_proyecto(proyecto_id)
        especificaciones['proyecto'] = proyecto

        if not especificaciones['tiene_especificaciones']:
            return JsonResponse({
                'error': 'No hay especificaciones en el proyecto para generar pruebas'
            }, status=400)

        resultados = {}
        total_pruebas = 0
        errores = []

        # Obtener conteo de especificaciones para el log de progreso
        n_req = len(especificaciones.get('requisitos', []) or [])
        n_hist = len(especificaciones.get('historias_usuario', []) or [])
        n_cu = len(especificaciones.get('casos_uso', []) or [])
        total_specs = n_req + n_hist + n_cu

        print(f"[PROGRESO] Proyecto '{proyecto.nombre}' — {total_specs} especificaciones encontradas "
              f"({n_req} requisitos, {n_hist} historias, {n_cu} casos de uso)")

        for i, tipo in enumerate(tipos_validos, start=1):
            try:
                print(f"[PROGRESO] [{i}/{len(tipos_validos)}] Iniciando generación de pruebas de {tipo.upper()}...")
                print(f"[PROGRESO] [{i}/{len(tipos_validos)}] Cargando prompt para {tipo}...")
                prompt = _cargar_prompt_por_tipo(especificaciones, tipo)

                print(f"[PROGRESO] [{i}/{len(tipos_validos)}] Enviando {total_specs} especificaciones a Gemini para pruebas de {tipo}...")
                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=[prompt]
                )
                print(f"[PROGRESO] [{i}/{len(tipos_validos)}] Respuesta recibida de Gemini para {tipo}. Procesando JSON...")

                pruebas_json = parsear_respuesta_ia(response.text)
                n_pruebas = len(pruebas_json.get('pruebas', []))
                print(f"[PROGRESO] [{i}/{len(tipos_validos)}] {n_pruebas} pruebas de {tipo} parseadas. Guardando en BD...")

                pruebas_creadas, _ = _guardar_pruebas_en_bd(proyecto, tipo, pruebas_json)

                resultados[tipo] = {
                    'estado': 'ok',
                    'total': len(pruebas_creadas),
                    'pruebas': pruebas_creadas
                }
                total_pruebas += len(pruebas_creadas)
                print(f"[PROGRESO] [{i}/{len(tipos_validos)}] ✓ {len(pruebas_creadas)} pruebas de {tipo} guardadas exitosamente.")

            except ValueError as e:
                # Error de parseo JSON — respuesta de Gemini no procesable
                msg = f"Error al procesar respuesta de IA para {tipo}: {str(e)}"
                print(f"[ERROR] [{i}/{len(tipos_validos)}] {msg}")
                errores.append({'tipo': tipo, 'error': msg, 'categoria': 'parseo'})
                resultados[tipo] = {'estado': 'error', 'total': 0, 'pruebas': [], 'error': msg}
            except Exception as e:
                msg = str(e)
                print(f"[ERROR] [{i}/{len(tipos_validos)}] Error generando pruebas de {tipo}: {msg}")
                errores.append({'tipo': tipo, 'error': msg, 'categoria': 'general'})
                resultados[tipo] = {'estado': 'error', 'total': 0, 'pruebas': [], 'error': msg}

        if total_pruebas > 0:
            cambio_exitoso, mensaje_cambio = cambiar_proyecto_a_generacion(proyecto_id)
        else:
            cambio_exitoso = False
            mensaje_cambio = "No se crearon pruebas"

        proyecto.refresh_from_db()
        proyecto_estado = proyecto.estado.nombre if hasattr(proyecto.estado, 'nombre') else str(proyecto.estado)

        return JsonResponse({
            'mensaje': f'Se generaron {total_pruebas} pruebas en total',
            'proyecto_id': proyecto_id,
            'proyecto_nombre': proyecto.nombre,
            'proyecto_estado': proyecto_estado,
            'cambio_estado': cambio_exitoso,
            'mensaje_cambio_estado': mensaje_cambio,
            'tipos_generados': tipos_validos,
            'resultados_por_tipo': resultados,
            'total_pruebas': total_pruebas,
            'errores': errores
        }, status=201)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'El body de la solicitud no es JSON válido'}, status=400)
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
    """
    try:
        views_dir = os.path.dirname(os.path.abspath(__file__))
        prompt_path = os.path.join(views_dir, 'prompts', 'esquema_bd.txt')

        if not os.path.exists(prompt_path):
            raise FileNotFoundError(f"Archivo de prompt no encontrado en: {prompt_path}")

        with open(prompt_path, 'r', encoding='utf-8') as f:
            template = f.read()

        secciones = _formatear_especificaciones_texto(especificaciones)

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

        proyecto_nombre = proyecto.nombre if hasattr(proyecto, 'nombre') else 'No especificado'
        proyecto_descripcion = proyecto.descripcion if hasattr(proyecto, 'descripcion') else 'No especificada'
        motor_nombre = tipo_motor.nombre if hasattr(tipo_motor, 'nombre') else 'No especificado'

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
    especificaciones del proyecto.
    """
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        body = json.loads(request.body)
        tipo_motor_id = body.get('tipo_motor_id')

        if not tipo_motor_id:
            return JsonResponse({'error': 'El campo tipo_motor_id es requerido'}, status=400)

        print("=" * 60)
        print(f"[DEBUG] Iniciando generación de esquema para proyecto {proyecto_id}")

        try:
            proyecto = Proyectos.objects.get(id=proyecto_id, activo=True)
        except Proyectos.DoesNotExist:
            return JsonResponse({'error': 'El proyecto especificado no existe'}, status=404)

        try:
            tipo_motor = TiposMotorBd.objects.get(id=tipo_motor_id, activo=True)
        except TiposMotorBd.DoesNotExist:
            return JsonResponse({'error': 'El tipo de motor especificado no existe'}, status=404)

        especificaciones = obtener_especificaciones_proyecto(proyecto_id)

        if not especificaciones['tiene_especificaciones']:
            return JsonResponse({
                'error': 'El proyecto debe tener al menos un requisito, historia de usuario o caso de uso para generar el esquema de BD'
            }, status=400)

        if EsquemasBd.objects.filter(
            proyecto_id=proyecto_id,
            tipo_motor_bd_id=tipo_motor_id,
            activo=True
        ).exists():
            return JsonResponse({
                'error': f'Ya existe un esquema activo para {tipo_motor.nombre}. Edita el existente o desactívalo primero'
            }, status=409)

        prompt = cargar_template_prompt_esquema_bd(proyecto, tipo_motor, especificaciones)

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[prompt]
        )

        respuesta_ia = response.text

        try:
            esquema_json = parsear_respuesta_ia(respuesta_ia)
        except ValueError as e:
            return JsonResponse({
                'error': 'No se pudo procesar la respuesta de la IA',
                'detalle': str(e),
                'respuesta_ia': respuesta_ia[:500]
            }, status=500)

        if not esquema_json.get('tablas'):
            return JsonResponse({'error': 'El esquema generado no contiene tablas válidas'}, status=500)

        try:
            with transaction.atomic():
                esquema = EsquemasBd.objects.create(
                    proyecto=proyecto,
                    tipo_motor_bd=tipo_motor,
                    esquema=esquema_json,
                    activo=True
                )
        except Exception as db_error:
            return JsonResponse({'error': f'Error al guardar el esquema: {str(db_error)}'}, status=500)

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
        return JsonResponse({'error': 'El body de la solicitud no es JSON válido'}, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'Error al generar esquema: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def previsualizar_esquema_bd(request, proyecto_id):
    """
    Genera un esquema de BD sin guardar.
    """
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        body = json.loads(request.body)
        tipo_motor_id = body.get('tipo_motor_id')

        if not tipo_motor_id:
            return JsonResponse({'error': 'El campo tipo_motor_id es requerido'}, status=400)

        try:
            proyecto = Proyectos.objects.get(id=proyecto_id, activo=True)
        except Proyectos.DoesNotExist:
            return JsonResponse({'error': 'El proyecto especificado no existe'}, status=404)

        try:
            tipo_motor = TiposMotorBd.objects.get(id=tipo_motor_id, activo=True)
        except TiposMotorBd.DoesNotExist:
            return JsonResponse({'error': 'El tipo de motor especificado no existe'}, status=404)

        especificaciones = obtener_especificaciones_proyecto(proyecto_id)

        if not especificaciones['tiene_especificaciones']:
            return JsonResponse({'error': 'El proyecto debe tener al menos una especificación'}, status=400)

        prompt = cargar_template_prompt_esquema_bd(proyecto, tipo_motor, especificaciones)

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[prompt]
        )

        try:
            esquema_json = parsear_respuesta_ia(response.text)
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
        return JsonResponse({'error': 'El body de la solicitud no es JSON válido'}, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'Error al generar esquema: {str(e)}'}, status=500)