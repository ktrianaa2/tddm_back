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

# ========================================
# CRUD TIPOS DE PRUEBA
# ========================================

# -----------------------------
# Crear tipo de prueba
# -----------------------------
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
                activo=True
            )

        return JsonResponse({
            'mensaje': 'Tipo de prueba creado exitosamente',
            'tipo_prueba_id': tipo_prueba.id,
            'nombre': tipo_prueba.nombre,
            'color': tipo_prueba.color
        }, status=201)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# -----------------------------
# Listar tipos de prueba
# -----------------------------
@require_http_methods(["GET"])
def listar_tipos_prueba(request):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        tipos_prueba = TiposPrueba.objects.filter(activo=True)

        tipos_data = []
        for tp in tipos_prueba:
            tipos_data.append({
                'id': tp.id,
                'nombre': tp.nombre,
                'descripcion': tp.descripcion,
                'color': tp.color
            })

        return JsonResponse({'tipos_prueba': tipos_data}, status=200)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# -----------------------------
# Obtener tipo de prueba
# -----------------------------
@require_http_methods(["GET"])
def obtener_tipo_prueba(request, tipo_prueba_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        tipo_prueba = TiposPrueba.objects.get(id=tipo_prueba_id, activo=True)

        return JsonResponse({
            'id': tipo_prueba.id,
            'nombre': tipo_prueba.nombre,
            'descripcion': tipo_prueba.descripcion,
            'color': tipo_prueba.color
        }, status=200)

    except TiposPrueba.DoesNotExist:
        return JsonResponse({'error': 'Tipo de prueba no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# -----------------------------
# Editar tipo de prueba
# -----------------------------
@csrf_exempt
@require_http_methods(["POST"])
def editar_tipo_prueba(request, tipo_prueba_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        tipo_prueba = TiposPrueba.objects.get(id=tipo_prueba_id, activo=True)

        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion')
        color = request.POST.get('color')

        with transaction.atomic():
            if nombre:
                tipo_prueba.nombre = nombre
            if descripcion is not None:
                tipo_prueba.descripcion = descripcion
            if color:
                tipo_prueba.color = color

            tipo_prueba.save()

        return JsonResponse({
            'mensaje': 'Tipo de prueba actualizado exitosamente',
            'color': tipo_prueba.color
        }, status=200)

    except TiposPrueba.DoesNotExist:
        return JsonResponse({'error': 'Tipo de prueba no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# -----------------------------
# Eliminar tipo de prueba
# -----------------------------
@csrf_exempt
@require_http_methods(["POST"])
def eliminar_tipo_prueba(request, tipo_prueba_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        tipo_prueba = TiposPrueba.objects.get(id=tipo_prueba_id, activo=True)

        tipo_prueba.activo = False
        tipo_prueba.save()

        return JsonResponse({'mensaje': 'Tipo de prueba eliminado exitosamente'}, status=200)

    except TiposPrueba.DoesNotExist:
        return JsonResponse({'error': 'Tipo de prueba no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ========================================
# CRUD PRUEBAS
# ========================================

# -----------------------------
# Crear prueba
# -----------------------------
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

        if not isinstance(prueba_data, (dict, list)):
            return JsonResponse({'error': 'El campo prueba debe ser un objeto o array JSON válido'}, status=400)

        with transaction.atomic():
            prueba = Pruebas.objects.create(
                proyecto=proyecto,
                tipo_prueba=tipo_prueba,
                codigo=codigo,
                nombre=nombre,
                descripcion=descripcion,
                estado=estado,
                especificacion_relacionada=especificacion_relacionada,
                prueba=prueba_data,
                activo=True
            )

        return JsonResponse({
            'mensaje': 'Prueba creada exitosamente',
            'prueba_id': prueba.id,
            'codigo': prueba.codigo,
            'nombre': prueba.nombre,
            'tipo_prueba': {
                'id': tipo_prueba.id,
                'nombre': tipo_prueba.nombre,
                'color': tipo_prueba.color
            }
        }, status=201)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except Exception as e:
        print(f"Error en crear_prueba: {str(e)}")
        return JsonResponse({'error': f'Error interno del servidor: {str(e)}'}, status=500)


# -----------------------------
# Listar pruebas por proyecto
# -----------------------------
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
        
        pruebas = Pruebas.objects.filter(
            proyecto=proyecto, 
            activo=True
        ).select_related('tipo_prueba').order_by('-fecha_creacion')

        pruebas_data = []
        for p in pruebas:
            pruebas_data.append({
                'id': p.id,
                'proyecto_id': p.proyecto.id,
                'tipo_prueba': {
                    'id': p.tipo_prueba.id,
                    'nombre': p.tipo_prueba.nombre,
                    'color': p.tipo_prueba.color
                },
                'codigo': p.codigo,
                'nombre': p.nombre,
                'descripcion': p.descripcion,
                'estado': p.estado,
                'especificacion_relacionada': p.especificacion_relacionada,
                'prueba': p.prueba,
                'fecha_creacion': p.fecha_creacion.isoformat() if p.fecha_creacion else None,
                'fecha_actualizacion': p.fecha_actualizacion.isoformat() if p.fecha_actualizacion else None
            })

        return JsonResponse({'pruebas': pruebas_data}, safe=False, status=200)

    except Exception as e:
        print(f"Error en listar_pruebas: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'Error interno del servidor: {str(e)}'}, status=500)


# -----------------------------
# Obtener prueba
# -----------------------------
@require_http_methods(["GET"])
def obtener_prueba(request, prueba_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        prueba = get_object_or_404(
            Pruebas.objects.select_related('proyecto', 'tipo_prueba'),
            id=prueba_id,
            activo=True
        )

        data = {
            'id': prueba.id,
            'proyecto_id': prueba.proyecto.id,
            'tipo_prueba': {
                'id': prueba.tipo_prueba.id,
                'nombre': prueba.tipo_prueba.nombre,
                'color': prueba.tipo_prueba.color
            },
            'codigo': prueba.codigo,
            'nombre': prueba.nombre,
            'descripcion': prueba.descripcion,
            'estado': prueba.estado,
            'especificacion_relacionada': prueba.especificacion_relacionada,
            'prueba': prueba.prueba,
            'fecha_creacion': prueba.fecha_creacion.isoformat() if prueba.fecha_creacion else None,
            'fecha_actualizacion': prueba.fecha_actualizacion.isoformat() if prueba.fecha_actualizacion else None
        }

        return JsonResponse(data, status=200)

    except Exception as e:
        print(f"Error en obtener_prueba: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'Error interno del servidor: {str(e)}'}, status=500)


# -----------------------------
# Editar prueba
# -----------------------------
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
            activo=True
        )

        with transaction.atomic():
            if 'tipo_prueba_id' in data and data['tipo_prueba_id']:
                try:
                    tipo_prueba = TiposPrueba.objects.get(id=data['tipo_prueba_id'], activo=True)
                    prueba.tipo_prueba = tipo_prueba
                except TiposPrueba.DoesNotExist:
                    return JsonResponse({'error': 'Tipo de prueba no encontrado'}, status=404)
            
            if 'codigo' in data:
                prueba.codigo = data['codigo']
            
            if 'nombre' in data:
                prueba.nombre = data['nombre']
            
            if 'descripcion' in data:
                prueba.descripcion = data['descripcion'] or ''
            
            if 'estado' in data:
                prueba.estado = data['estado']
            
            if 'especificacion_relacionada' in data:
                prueba.especificacion_relacionada = data['especificacion_relacionada'] or ''
            
            if 'prueba' in data:
                prueba_nueva = data['prueba']
                if not isinstance(prueba_nueva, (dict, list)):
                    return JsonResponse({'error': 'El campo prueba debe ser un objeto o array JSON válido'}, status=400)
                prueba.prueba = prueba_nueva

            prueba.fecha_actualizacion = datetime.now()
            prueba.save()

        return JsonResponse({
            'mensaje': 'Prueba actualizada exitosamente',
            'prueba_id': prueba.id,
            'tipo_prueba': {
                'id': prueba.tipo_prueba.id,
                'nombre': prueba.tipo_prueba.nombre,
                'color': prueba.tipo_prueba.color
            }
        }, status=200)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except Exception as e:
        print(f"Error en editar_prueba: {str(e)}")
        return JsonResponse({'error': f'Error interno del servidor: {str(e)}'}, status=500)


# -----------------------------
# Eliminar prueba
# -----------------------------
@csrf_exempt
@require_http_methods(["DELETE"])
def eliminar_prueba(request, prueba_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        prueba = get_object_or_404(
            Pruebas.objects.select_related('proyecto'),
            id=prueba_id,
            activo=True
        )

        with transaction.atomic():
            prueba.activo = False
            prueba.save()

        return JsonResponse({
            'mensaje': 'Prueba eliminada exitosamente'
        }, status=200)

    except Exception as e:
        print(f"Error en eliminar_prueba: {str(e)}")
        return JsonResponse({'error': f'Error interno del servidor: {str(e)}'}, status=500)