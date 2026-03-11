# pruebas/views.py
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from datetime import datetime
import json
from pruebas.models import TiposPrueba, Pruebas
from proyectos.models import Proyectos
from usuarios.views import validar_token
from usuarios.models import Usuarios


# ─── Helper: normalizar campo prueba a dict ───────────────────────────────────
# El campo prueba puede llegar de la BD como:
#   - dict (JSONField ya deserializado por Django/psycopg2)
#   - str JSON simple:          '{"objetivo": "..."}'
#   - str doblemente escapado:  '"{\\"objetivo\\": \\"...\\"}"'
# Siempre devuelve un dict plano listo para usar.
def _normalizar_prueba(valor):
    if valor is None:
        return {}
    if isinstance(valor, dict):
        return valor
    if isinstance(valor, (list,)):
        return {}
    if isinstance(valor, str):
        parsed = valor
        for _ in range(3):
            try:
                parsed = json.loads(parsed)
                if isinstance(parsed, dict):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                return {}
        return {}
    return {}


# ─── Helper: serializar prueba a STRING JSON para guardar en BD ───────────────
# Siempre guardamos el campo prueba como string JSON en la BD.
# Esto evita el bug de Django JSONField donde psycopg2 devuelve un dict
# ya deserializado y Django intenta hacer json.loads(dict) → TypeError.
def _serializar_para_bd(valor_dict):
    """Recibe un dict y devuelve un string JSON para guardar en BD."""
    if not isinstance(valor_dict, dict):
        valor_dict = {}
    return json.dumps(valor_dict, ensure_ascii=False)


# ─── Helper: preparar datos de prueba para la respuesta HTTP ─────────────────
def _serializar_prueba(p):
    return {
        'id': p.id,
        'proyecto_id': p.proyecto.id,
        'tipo_prueba': {
            'id': p.tipo_prueba.id,
            'nombre': p.tipo_prueba.nombre,
            'color': p.tipo_prueba.color,
        },
        'codigo': p.codigo,
        'nombre': p.nombre,
        'descripcion': p.descripcion,
        'estado': p.estado,
        'especificacion_relacionada': p.especificacion_relacionada,
        'prueba': _normalizar_prueba(p.prueba),
        'fecha_creacion': p.fecha_creacion.isoformat() if p.fecha_creacion else None,
        'fecha_actualizacion': p.fecha_actualizacion.isoformat() if p.fecha_actualizacion else None,
    }


# ========================================
# CRUD TIPOS DE PRUEBA
# ========================================

@csrf_exempt
@require_http_methods(["POST"])
def crear_tipo_prueba(request):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion', '')
        color = request.POST.get('color', '#6B7280')

        if not nombre:
            return JsonResponse({'error': 'El campo nombre es requerido'}, status=400)

        with transaction.atomic():
            tipo_prueba = TiposPrueba.objects.create(
                nombre=nombre,
                descripcion=descripcion,
                color=color,
                activo=True,
            )

        return JsonResponse({
            'mensaje': 'Tipo de prueba creado exitosamente',
            'tipo_prueba_id': tipo_prueba.id,
            'nombre': tipo_prueba.nombre,
            'color': tipo_prueba.color,
        }, status=201)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def listar_tipos_prueba(request):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        tipos_data = list(
            TiposPrueba.objects.filter(activo=True).values('id', 'nombre', 'descripcion', 'color')
        )
        return JsonResponse({'tipos_prueba': tipos_data}, status=200)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def obtener_tipo_prueba(request, tipo_prueba_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        tp = TiposPrueba.objects.get(id=tipo_prueba_id, activo=True)
        return JsonResponse({
            'id': tp.id,
            'nombre': tp.nombre,
            'descripcion': tp.descripcion,
            'color': tp.color,
        }, status=200)

    except TiposPrueba.DoesNotExist:
        return JsonResponse({'error': 'Tipo de prueba no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def editar_tipo_prueba(request, tipo_prueba_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        tp = TiposPrueba.objects.get(id=tipo_prueba_id, activo=True)

        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion')
        color = request.POST.get('color')

        with transaction.atomic():
            if nombre:
                tp.nombre = nombre
            if descripcion is not None:
                tp.descripcion = descripcion
            if color:
                tp.color = color
            tp.save()

        return JsonResponse({
            'mensaje': 'Tipo de prueba actualizado exitosamente',
            'color': tp.color,
        }, status=200)

    except TiposPrueba.DoesNotExist:
        return JsonResponse({'error': 'Tipo de prueba no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def eliminar_tipo_prueba(request, tipo_prueba_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        tp = TiposPrueba.objects.get(id=tipo_prueba_id, activo=True)
        tp.activo = False
        tp.save()
        return JsonResponse({'mensaje': 'Tipo de prueba eliminado exitosamente'}, status=200)

    except TiposPrueba.DoesNotExist:
        return JsonResponse({'error': 'Tipo de prueba no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ========================================
# CRUD PRUEBAS
# ========================================

@csrf_exempt
@require_http_methods(["POST"])
def crear_prueba(request):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        data = json.loads(request.body.decode('utf-8'))

        proyecto_id = data.get('proyecto_id')
        tipo_prueba_id = data.get('tipo_prueba_id')
        codigo = data.get('codigo')
        nombre = data.get('nombre')
        descripcion = data.get('descripcion', '')
        estado = data.get('estado', 'Pendiente')
        especificacion_relacionada = data.get('especificacion_relacionada', '')
        prueba_data = data.get('prueba')

        if not all([proyecto_id, tipo_prueba_id, codigo, nombre, prueba_data]):
            return JsonResponse({
                'error': 'Los campos proyecto_id, tipo_prueba_id, codigo, nombre y prueba son requeridos'
            }, status=400)

        try:
            proyecto = Proyectos.objects.get(id=proyecto_id, activo=True)
        except Proyectos.DoesNotExist:
            return JsonResponse({'error': 'El proyecto especificado no existe'}, status=400)

        try:
            tipo_prueba = TiposPrueba.objects.get(id=tipo_prueba_id, activo=True)
        except TiposPrueba.DoesNotExist:
            return JsonResponse({'error': 'Tipo de prueba no encontrado'}, status=404)

        # Normalizar a dict y luego serializar a string JSON para BD
        prueba_dict = _normalizar_prueba(prueba_data)
        prueba_para_bd = _serializar_para_bd(prueba_dict)

        with transaction.atomic():
            prueba = Pruebas.objects.create(
                proyecto=proyecto,
                tipo_prueba=tipo_prueba,
                codigo=codigo,
                nombre=nombre,
                descripcion=descripcion,
                estado=estado,
                especificacion_relacionada=especificacion_relacionada,
                prueba=prueba_para_bd,
                activo=True,
            )

        return JsonResponse({
            'mensaje': 'Prueba creada exitosamente',
            'prueba_id': prueba.id,
            'codigo': prueba.codigo,
            'nombre': prueba.nombre,
            'tipo_prueba': {
                'id': tipo_prueba.id,
                'nombre': tipo_prueba.nombre,
                'color': tipo_prueba.color,
            },
        }, status=201)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido en el cuerpo de la petición'}, status=400)
    except Exception as e:
        print(f"Error en crear_prueba: {str(e)}")
        import traceback; traceback.print_exc()
        return JsonResponse({'error': f'Error interno del servidor: {str(e)}'}, status=500)


@require_http_methods(["GET"])
def listar_pruebas(request, proyecto_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        try:
            proyecto = Proyectos.objects.get(id=proyecto_id, activo=True)
        except Proyectos.DoesNotExist:
            return JsonResponse({'error': 'El proyecto especificado no existe'}, status=404)

        # Usar values() para obtener el campo prueba como string crudo desde la BD,
        # evitando que el JSONField de Django intente hacer json.loads() sobre
        # valores que ya son dict (bug con psycopg2 + JSONField en algunas versiones).
        pruebas_raw = (
            Pruebas.objects
            .filter(proyecto=proyecto, activo=True)
            .select_related('tipo_prueba')
            .order_by('-fecha_creacion')
        )

        pruebas_data = []
        for p in pruebas_raw:
            try:
                pruebas_data.append(_serializar_prueba(p))
            except Exception as e_inner:
                print(f"Error serializando prueba id={p.id}: {e_inner}")
                # Incluir la prueba con campo prueba vacío antes de omitirla
                pruebas_data.append({
                    'id': p.id,
                    'proyecto_id': p.proyecto.id,
                    'tipo_prueba': {
                        'id': p.tipo_prueba.id,
                        'nombre': p.tipo_prueba.nombre,
                        'color': p.tipo_prueba.color,
                    },
                    'codigo': p.codigo,
                    'nombre': p.nombre,
                    'descripcion': p.descripcion,
                    'estado': p.estado,
                    'especificacion_relacionada': p.especificacion_relacionada,
                    'prueba': {},
                    'fecha_creacion': p.fecha_creacion.isoformat() if p.fecha_creacion else None,
                    'fecha_actualizacion': p.fecha_actualizacion.isoformat() if p.fecha_actualizacion else None,
                })

        return JsonResponse({'pruebas': pruebas_data}, safe=False, status=200)

    except Exception as e:
        print(f"Error en listar_pruebas: {str(e)}")
        import traceback; traceback.print_exc()
        return JsonResponse({'error': f'Error interno del servidor: {str(e)}'}, status=500)


@require_http_methods(["GET"])
def obtener_prueba(request, prueba_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        prueba = get_object_or_404(
            Pruebas.objects.select_related('proyecto', 'tipo_prueba'),
            id=prueba_id,
            activo=True,
        )
        return JsonResponse(_serializar_prueba(prueba), status=200)

    except Exception as e:
        print(f"Error en obtener_prueba: {str(e)}")
        import traceback; traceback.print_exc()
        return JsonResponse({'error': f'Error interno del servidor: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["PUT", "PATCH"])
def editar_prueba(request, prueba_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        data = json.loads(request.body.decode('utf-8'))

        prueba = get_object_or_404(
            Pruebas.objects.select_related('proyecto', 'tipo_prueba'),
            id=prueba_id,
            activo=True,
        )

        with transaction.atomic():
            campos_a_guardar = ['fecha_actualizacion']

            if 'tipo_prueba_id' in data and data['tipo_prueba_id']:
                try:
                    prueba.tipo_prueba = TiposPrueba.objects.get(
                        id=data['tipo_prueba_id'], activo=True
                    )
                    campos_a_guardar.append('tipo_prueba')
                except TiposPrueba.DoesNotExist:
                    return JsonResponse({'error': 'Tipo de prueba no encontrado'}, status=404)

            if 'codigo' in data:
                prueba.codigo = data['codigo']
                campos_a_guardar.append('codigo')

            if 'nombre' in data:
                prueba.nombre = data['nombre']
                campos_a_guardar.append('nombre')

            if 'descripcion' in data:
                prueba.descripcion = data['descripcion'] or ''
                campos_a_guardar.append('descripcion')

            if 'estado' in data:
                prueba.estado = data['estado']
                campos_a_guardar.append('estado')

            if 'especificacion_relacionada' in data:
                prueba.especificacion_relacionada = data['especificacion_relacionada'] or ''
                campos_a_guardar.append('especificacion_relacionada')

            # ── Campo prueba: fusión segura ──────────────────────────────────
            # Solo se toca si 'prueba' viene explícitamente en el body.
            # Se normaliza el valor actual a dict (maneja string, doble-escape, dict),
            # se fusionan solo las claves nuevas, y se guarda SIEMPRE como string JSON.
            # Esto evita el bug de Django JSONField con psycopg2.
            if 'prueba' in data:
                nuevos_datos = _normalizar_prueba(data['prueba'])

                # Leer valor actual de la BD como string crudo para evitar el bug del JSONField
                # Usamos SQL directo para obtener el valor exactamente como está en la BD
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT prueba::text FROM pruebas WHERE id = %s",
                        [prueba_id]
                    )
                    row = cursor.fetchone()
                    prueba_raw = row[0] if row else None

                prueba_actual = _normalizar_prueba(prueba_raw)

                # Fusión: agregar/actualizar solo las claves nuevas
                prueba_actual.update(nuevos_datos)

                # SIEMPRE guardar como string JSON — nunca como dict
                # Esto evita el TypeError: json.loads(dict) en futuras lecturas
                prueba.prueba = _serializar_para_bd(prueba_actual)
                campos_a_guardar.append('prueba')

            prueba.fecha_actualizacion = datetime.now()
            prueba.save(update_fields=campos_a_guardar)

        return JsonResponse({
            'mensaje': 'Prueba actualizada exitosamente',
            'prueba_id': prueba.id,
            'tipo_prueba': {
                'id': prueba.tipo_prueba.id,
                'nombre': prueba.tipo_prueba.nombre,
                'color': prueba.tipo_prueba.color,
            },
        }, status=200)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido en el cuerpo de la petición'}, status=400)
    except Exception as e:
        print(f"Error en editar_prueba: {str(e)}")
        import traceback; traceback.print_exc()
        return JsonResponse({'error': f'Error interno del servidor: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST", "PUT", "PATCH"])
def aprobar_prueba(request, prueba_id):
    """
    Endpoint EXCLUSIVO para aprobar una prueba.
    Solo cambia estado → 'Aprobada'. No toca el campo prueba.
    """
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        prueba = get_object_or_404(
            Pruebas.objects.only('id', 'estado'),
            id=prueba_id,
            activo=True,
        )

        prueba.estado = 'Aprobada'
        prueba.save(update_fields=['estado'])

        return JsonResponse({
            'mensaje': 'Prueba aprobada exitosamente',
            'prueba_id': prueba_id,
            'estado': 'Aprobada',
        }, status=200)

    except Exception as e:
        print(f"Error en aprobar_prueba: {str(e)}")
        import traceback; traceback.print_exc()
        return JsonResponse({'error': f'Error interno del servidor: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def eliminar_prueba(request, prueba_id):
    """Soft-delete: marca activo=False."""
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        prueba = get_object_or_404(
            Pruebas.objects.select_related('proyecto'),
            id=prueba_id,
            activo=True,
        )

        with transaction.atomic():
            prueba.activo = False
            prueba.save()

        return JsonResponse({'mensaje': 'Prueba eliminada exitosamente'}, status=200)

    except Exception as e:
        print(f"Error en eliminar_prueba: {str(e)}")
        import traceback; traceback.print_exc()
        return JsonResponse({'error': f'Error interno del servidor: {str(e)}'}, status=500)


# ========================================
# MIGRACIÓN: limpiar datos corruptos en BD
# ========================================

@csrf_exempt
@require_http_methods(["POST"])
def reparar_pruebas_json(request):
    """
    Endpoint utilitario (solo admin) para corregir filas donde el campo
    'prueba' fue guardado como dict en vez de string JSON.
    Llamar una sola vez después de desplegar el fix.
    """
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        from django.db import connection

        corregidas = 0
        errores = 0

        with connection.cursor() as cursor:
            # Obtener todas las pruebas activas con su valor crudo
            cursor.execute("SELECT id, prueba::text FROM pruebas WHERE activo = TRUE")
            rows = cursor.fetchall()

        for prueba_id, prueba_raw in rows:
            try:
                # Normalizar a dict
                prueba_dict = _normalizar_prueba(prueba_raw)
                # Re-serializar a string JSON limpio
                prueba_str = _serializar_para_bd(prueba_dict)

                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE pruebas SET prueba = %s WHERE id = %s",
                        [prueba_str, prueba_id]
                    )
                corregidas += 1
            except Exception as e:
                print(f"Error reparando prueba id={prueba_id}: {e}")
                errores += 1

        return JsonResponse({
            'mensaje': f'Reparación completada: {corregidas} corregidas, {errores} errores',
            'corregidas': corregidas,
            'errores': errores,
        }, status=200)

    except Exception as e:
        print(f"Error en reparar_pruebas_json: {str(e)}")
        import traceback; traceback.print_exc()
        return JsonResponse({'error': f'Error interno del servidor: {str(e)}'}, status=500)