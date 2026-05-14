# esquemas_bd/views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.shortcuts import get_object_or_404
from esquemas_bd.models import EsquemasBd, TiposMotorBd
from proyectos.models import Proyectos
from usuarios.views import validar_token
import json


# --------------------------------
# Listar motores de BD disponibles
# --------------------------------
@csrf_exempt
@require_http_methods(["GET"])
def listar_motores_bd(request):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)
    # .only() aqui pon los motores del json, PORFAVOR USA ESTO 😄
    motores = TiposMotorBd.objects.filter(activo=True).only(
        'id', 'nombre', 'descripcion', 'extension_archivo', 'sintaxis_especifica', 'color'
    )
    
    data = [{
        'id': m.id,
        'nombre': m.nombre,
        'descripcion': m.descripcion or '',
        'color': m.color
    } for m in motores]
    
    return JsonResponse({'data': data, 'total': len(data)}, status=200)




# --------------------------------
# Obtener esquema específico
# --------------------------------
@require_http_methods(["GET"])
def obtener_esquema(request, esquema_id):
    """Obtiene un esquema específico con todos sus detalles"""
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        esquema = get_object_or_404(EsquemasBd, id=esquema_id, activo=True)
        
        tablas = list(esquema.esquema.get('tablas', {}).keys()) if esquema.esquema else []
        
        data = {
            'id': esquema.id,
            'proyecto_id': esquema.proyecto.id,
            'proyecto_nombre': esquema.proyecto.nombre,
            'motor_bd_id': esquema.tipo_motor_bd.id,
            'motor_bd_nombre': esquema.tipo_motor_bd.nombre,
            'motor_bd_extension': esquema.tipo_motor_bd.extension_archivo or '',
            'esquema': esquema.esquema,
            'tablas': tablas,
            'total_tablas': len(tablas),
            'fecha_creacion': esquema.fecha_creacion.isoformat(),
            'fecha_actualizacion': esquema.fecha_actualizacion.isoformat()
        }
        
        return JsonResponse(data, status=200)

    except Exception as e:
        return JsonResponse({
            'error': f'Error interno del servidor: {str(e)}',
            'tipo': type(e).__name__
        }, status=500)


# --------------------------------
# Listar esquemas de un proyecto
# --------------------------------
@require_http_methods(["GET"])
def listar_esquemas_proyecto(request, proyecto_id):
    """Lista esquemas de un proyecto específico"""
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        # Validar que el proyecto existe
        try:
            Proyectos.objects.get(id=proyecto_id, activo=True)
        except Proyectos.DoesNotExist:
            return JsonResponse({'error': 'El proyecto especificado no existe'}, status=404)

        esquemas = EsquemasBd.objects.filter(
            proyecto_id=proyecto_id,
            activo=True
        ).select_related('tipo_motor_bd')

        data = []
        for esquema in esquemas:
            tablas = esquema.esquema.get('tablas', {}) if esquema.esquema else {}
            
            data.append({
                'id': esquema.id,
                'proyecto_id': esquema.proyecto.id,
                'motor_bd_id': esquema.tipo_motor_bd.id,
                'motor_bd_nombre': esquema.tipo_motor_bd.nombre,
                'motor_bd_color': esquema.tipo_motor_bd.color,
                'esquema': esquema.esquema,
                'total_tablas': len(tablas),
                'tablas': list(tablas.keys()),
                'fecha_creacion': esquema.fecha_creacion.isoformat(),
                'fecha_actualizacion': esquema.fecha_actualizacion.isoformat()
            })

        return JsonResponse({
            'proyecto_id': proyecto_id,
            'data': data,
            'total': len(data)
        }, status=200)

    except Exception as e:
        return JsonResponse({
            'error': f'Error interno del servidor: {str(e)}',
            'tipo': type(e).__name__
        }, status=500)
    
# --------------------------------
# Crear esquema
# --------------------------------
@csrf_exempt
@require_http_methods(["POST"])
def crear_esquema(request):
    """
    Crea un nuevo esquema para un proyecto.
    Requiere: proyecto_id, tipo_motor_bd_id, esquema (JSON)
    """
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        data = json.loads(request.body.decode('utf-8'))
        
        proyecto_id = data.get('proyecto_id')
        tipo_motor_bd_id = data.get('tipo_motor_bd_id')
        esquema = data.get('esquema')
        
        # Validaciones
        errores = []
        
        if not proyecto_id:
            errores.append('El proyecto_id es obligatorio')
        
        if not tipo_motor_bd_id:
            errores.append('El tipo_motor_bd_id es obligatorio')
        
        if not esquema:
            errores.append('El esquema es obligatorio')
        elif not isinstance(esquema, dict):
            errores.append('El esquema debe ser un objeto JSON')
        elif not esquema.get('tablas') or not isinstance(esquema.get('tablas'), dict):
            errores.append('El esquema debe contener un objeto "tablas" con al menos una tabla')
        
        if errores:
            return JsonResponse({
                'error': 'Errores de validación',
                'detalles': errores
            }, status=400)

        # Validar que el proyecto existe
        try:
            proyecto = Proyectos.objects.get(id=proyecto_id, activo=True)
        except Proyectos.DoesNotExist:
            return JsonResponse({'error': 'El proyecto especificado no existe'}, status=404)

        # Validar que el tipo de motor BD existe
        try:
            tipo_motor_bd = TiposMotorBd.objects.get(id=tipo_motor_bd_id, activo=True)
        except TiposMotorBd.DoesNotExist:
            return JsonResponse({'error': 'El tipo de motor BD especificado no existe'}, status=404)

        # Validar que el proyecto no tiene esquema
        if EsquemasBd.objects.filter(proyecto_id=proyecto_id, activo=True).exists():
            return JsonResponse({
                'error': 'El proyecto ya tiene un esquema asignado'
            }, status=409)

        with transaction.atomic():
            esquema_nuevo = EsquemasBd.objects.create(
                proyecto=proyecto,
                tipo_motor_bd=tipo_motor_bd,
                esquema=esquema,
                activo=True
            )

        tablas = list(esquema.get('tablas', {}).keys())
        
        return JsonResponse({
            'mensaje': 'Esquema creado exitosamente',
            'esquema_id': esquema_nuevo.id,
            'proyecto_id': proyecto.id,
            'proyecto_nombre': proyecto.nombre,
            'motor_bd_nombre': tipo_motor_bd.nombre,
            'total_tablas': len(tablas),
            'tablas': tablas
        }, status=201)

    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'JSON inválido en el body'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': f'Error interno del servidor: {str(e)}',
            'tipo': type(e).__name__
        }, status=500)


# --------------------------------
# Actualizar esquema
# --------------------------------
@csrf_exempt
@require_http_methods(["PUT", "PATCH"])
def actualizar_esquema(request, esquema_id):
    """
    Actualiza un esquema existente.
    Puede actualizar: esquema (JSON), tipo_motor_bd_id
    """
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        esquema = get_object_or_404(EsquemasBd, id=esquema_id, activo=True)
        
        data = json.loads(request.body.decode('utf-8'))

        # Actualizar esquema JSON si viene en la petición
        if 'esquema' in data:
            esquema_nuevo = data.get('esquema')
            
            if not isinstance(esquema_nuevo, dict):
                return JsonResponse({
                    'error': 'El esquema debe ser un objeto JSON'
                }, status=400)
            
            if not esquema_nuevo.get('tablas') or not isinstance(esquema_nuevo.get('tablas'), dict):
                return JsonResponse({
                    'error': 'El esquema debe contener un objeto "tablas" con al menos una tabla'
                }, status=400)
            
            esquema.esquema = esquema_nuevo

        # Actualizar tipo de motor BD si viene en la petición
        if 'tipo_motor_bd_id' in data:
            tipo_motor_bd_id = data.get('tipo_motor_bd_id')
            
            if tipo_motor_bd_id:
                try:
                    tipo_motor_bd = TiposMotorBd.objects.get(id=tipo_motor_bd_id, activo=True)
                    esquema.tipo_motor_bd = tipo_motor_bd
                except TiposMotorBd.DoesNotExist:
                    return JsonResponse({
                        'error': 'El tipo de motor BD especificado no existe'
                    }, status=404)

        with transaction.atomic():
            esquema.save()

        tablas = list(esquema.esquema.get('tablas', {}).keys()) if esquema.esquema else []
        
        return JsonResponse({
            'mensaje': 'Esquema actualizado exitosamente',
            'esquema_id': esquema.id,
            'proyecto_id': esquema.proyecto.id,
            'motor_bd_nombre': esquema.tipo_motor_bd.nombre,
            'total_tablas': len(tablas),
            'tablas': tablas,
            'fecha_actualizacion': esquema.fecha_actualizacion.isoformat()
        }, status=200)

    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'JSON inválido en el body'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': f'Error interno del servidor: {str(e)}',
            'tipo': type(e).__name__
        }, status=500)


# --------------------------------
# Eliminar esquema (soft delete)
# --------------------------------
@csrf_exempt
@require_http_methods(["DELETE"])
def eliminar_esquema(request, esquema_id):
    """Desactiva un esquema (soft delete)"""
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        esquema = get_object_or_404(EsquemasBd, id=esquema_id, activo=True)

        with transaction.atomic():
            esquema.activo = False
            esquema.save()

        return JsonResponse({
            'mensaje': 'Esquema eliminado exitosamente',
            'esquema_id': esquema.id,
            'proyecto_id': esquema.proyecto.id
        }, status=200)

    except Exception as e:
        return JsonResponse({
            'error': f'Error interno del servidor: {str(e)}',
            'tipo': type(e).__name__
        }, status=500)


# --------------------------------
# Duplicar esquema
# --------------------------------
@csrf_exempt
@require_http_methods(["POST"])
def duplicar_esquema(request, esquema_id):
    """
    Crea una copia de un esquema para otro proyecto.
    Requiere: proyecto_destino_id en el body
    Permite múltiples esquemas por proyecto (diferentes motores).
    """
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        data = json.loads(request.body.decode('utf-8'))
        proyecto_destino_id = data.get('proyecto_destino_id')

        # Validaciones
        if not proyecto_destino_id:
            return JsonResponse({
                'error': 'El campo proyecto_destino_id es obligatorio'
            }, status=400)

        # Obtener esquema origen
        esquema_origen = get_object_or_404(EsquemasBd, id=esquema_id, activo=True)

        # Validar que el proyecto destino existe
        try:
            proyecto_destino = Proyectos.objects.get(id=proyecto_destino_id, activo=True)
        except Proyectos.DoesNotExist:
            return JsonResponse({
                'error': 'El proyecto destino especificado no existe'
            }, status=404)

        # Validar que el proyecto destino no tiene esquema para este motor
        if EsquemasBd.objects.filter(
            proyecto_id=proyecto_destino_id, 
            tipo_motor_bd_id=esquema_origen.tipo_motor_bd_id,
            activo=True
        ).exists():
            return JsonResponse({
                'error': f'El proyecto destino ya tiene un esquema para {esquema_origen.tipo_motor_bd.nombre}. Desactívalo primero'
            }, status=409)

        with transaction.atomic():
            esquema_nuevo = EsquemasBd.objects.create(
                proyecto=proyecto_destino,
                tipo_motor_bd=esquema_origen.tipo_motor_bd,
                esquema=esquema_origen.esquema,
                activo=True
            )

        tablas = list(esquema_nuevo.esquema.get('tablas', {}).keys()) if esquema_nuevo.esquema else []

        return JsonResponse({
            'mensaje': 'Esquema duplicado exitosamente',
            'esquema_id': esquema_nuevo.id,
            'proyecto_origen_id': esquema_origen.proyecto.id,
            'proyecto_origen_nombre': esquema_origen.proyecto.nombre,
            'proyecto_destino_id': proyecto_destino.id,
            'proyecto_destino_nombre': proyecto_destino.nombre,
            'motor_bd_nombre': esquema_nuevo.tipo_motor_bd.nombre,
            'total_tablas': len(tablas),
            'tablas': tablas
        }, status=201)

    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'JSON inválido en el body'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': f'Error interno del servidor: {str(e)}',
            'tipo': type(e).__name__
        }, status=500)