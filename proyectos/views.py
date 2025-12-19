# proyectos/views.py
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from datetime import datetime
from proyectos.models import Proyectos
from catalogos.models import EstadosProyecto
from usuarios.views import validar_token
from usuarios.models import Usuarios

# -----------------------------
# Crear proyecto
# -----------------------------
@csrf_exempt
@require_http_methods(["POST"])
def crear_proyecto(request):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion', '')

        if not nombre:
            return JsonResponse({'error': 'El campo nombre es requerido'}, status=400)

        usuario_obj = Usuarios.objects.get(id=payload['usuario_id'], activo=True)
        
        # Obtener el estado inicial "especificaciones"
        estado_especificaciones = EstadosProyecto.objects.get(
            nombre='especificaciones', 
            activo=True
        )

        with transaction.atomic():
            proyecto = Proyectos.objects.create(
                nombre=nombre,
                descripcion=descripcion,
                estado=estado_especificaciones,
                usuario=usuario_obj,
                activo=True
            )

        return JsonResponse({
            'mensaje': 'Proyecto creado exitosamente',
            'proyecto_id': proyecto.id,
            'nombre': proyecto.nombre,
            'estado': proyecto.estado.nombre,
            'color_estado': proyecto.estado.color
        }, status=201)

    except EstadosProyecto.DoesNotExist:
        return JsonResponse({'error': 'Estado inicial no encontrado en el sistema'}, status=500)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# -----------------------------
# Listar proyectos del usuario
# -----------------------------
@require_http_methods(["GET"])
def listar_proyectos(request):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        usuario_obj = Usuarios.objects.get(id=payload['usuario_id'], activo=True)
        proyectos = Proyectos.objects.filter(
            usuario=usuario_obj, 
            activo=True
        ).select_related('estado')

        proyectos_data = []
        for p in proyectos:
            proyectos_data.append({
                'proyecto_id': p.id,
                'nombre': p.nombre,
                'descripcion': p.descripcion,
                'estado': {
                    'id': p.estado.id if p.estado else None,
                    'nombre': p.estado.nombre if p.estado else None,
                    'color': p.estado.color if p.estado else '#6B7280',
                    'orden': p.estado.orden if p.estado else None
                },
                'fecha_creacion': p.fecha_creacion,
                'fecha_actualizacion': p.fecha_actualizacion
            })

        return JsonResponse({'proyectos': proyectos_data}, status=200)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# -----------------------------
# Obtener proyecto individual
# -----------------------------
@require_http_methods(["GET"])
def obtener_proyecto(request, proyecto_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        usuario_obj = Usuarios.objects.get(id=payload['usuario_id'], activo=True)
        proyecto = Proyectos.objects.select_related('estado').get(
            id=proyecto_id, 
            usuario=usuario_obj, 
            activo=True
        )

        return JsonResponse({
            'proyecto_id': proyecto.id,
            'nombre': proyecto.nombre,
            'descripcion': proyecto.descripcion,
            'estado': {
                'id': proyecto.estado.id if proyecto.estado else None,
                'nombre': proyecto.estado.nombre if proyecto.estado else None,
                'color': proyecto.estado.color if proyecto.estado else '#6B7280',
                'orden': proyecto.estado.orden if proyecto.estado else None
            },
            'fecha_creacion': proyecto.fecha_creacion,
            'fecha_actualizacion': proyecto.fecha_actualizacion,
        }, status=200)

    except Proyectos.DoesNotExist:
        return JsonResponse({'error': 'Proyecto no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# -----------------------------
# Editar proyecto (solo nombre y descripción)
# -----------------------------
@csrf_exempt
@require_http_methods(["POST"])
def editar_proyecto(request, proyecto_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        usuario_obj = Usuarios.objects.get(id=payload['usuario_id'], activo=True)
        proyecto = Proyectos.objects.get(id=proyecto_id, usuario=usuario_obj, activo=True)

        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion')

        with transaction.atomic():
            if nombre:
                proyecto.nombre = nombre
            if descripcion is not None:
                proyecto.descripcion = descripcion

            proyecto.fecha_actualizacion = datetime.now()
            proyecto.save()

        return JsonResponse({'mensaje': 'Proyecto actualizado exitosamente'}, status=200)

    except Proyectos.DoesNotExist:
        return JsonResponse({'error': 'Proyecto no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# -----------------------------
# Cambiar estado del proyecto (bidireccional)
# -----------------------------
@csrf_exempt
@require_http_methods(["POST"])
def cambiar_estado_proyecto(request, proyecto_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        usuario_obj = Usuarios.objects.get(id=payload['usuario_id'], activo=True)
        proyecto = Proyectos.objects.select_related('estado').get(
            id=proyecto_id, 
            usuario=usuario_obj, 
            activo=True
        )

        estado_nombre = request.POST.get('estado')
        
        if not estado_nombre:
            return JsonResponse({'error': 'El campo estado es requerido'}, status=400)
        
        # Buscar el nuevo estado por nombre
        try:
            nuevo_estado = EstadosProyecto.objects.get(
                nombre=estado_nombre.lower(), 
                activo=True
            )
        except EstadosProyecto.DoesNotExist:
            estados_disponibles = list(
                EstadosProyecto.objects.filter(activo=True)
                .values_list('nombre', flat=True)
                .order_by('orden')
            )
            return JsonResponse({
                'error': f'Estado inválido. Los estados válidos son: {", ".join(estados_disponibles)}'
            }, status=400)

        estado_actual = proyecto.estado
        
        # Si el estado es el mismo, no hacer nada
        if estado_actual and estado_actual.id == nuevo_estado.id:
            return JsonResponse({
                'mensaje': 'El proyecto ya está en ese estado',
                'estado': {
                    'nombre': estado_actual.nombre,
                    'color': estado_actual.color
                }
            }, status=200)

        # Definir transiciones válidas basadas en el orden
        transiciones_validas = {
            'especificaciones': ['generacion'],
            'generacion': ['especificaciones', 'ejecucion'],
            'ejecucion': ['generacion', 'finalizado'],
            'finalizado': [],
            'cancelado': []
        }
        
        estado_actual_nombre = estado_actual.nombre if estado_actual else None
        
        # Validar que la transición sea válida
        if estado_actual_nombre and nuevo_estado.nombre not in transiciones_validas.get(estado_actual_nombre, []):
            transiciones_permitidas = transiciones_validas.get(estado_actual_nombre, [])
            mensaje_error = f'Transición no válida desde "{estado_actual_nombre}" a "{nuevo_estado.nombre}". '
            
            if transiciones_permitidas:
                mensaje_error += f'Las transiciones permitidas desde "{estado_actual_nombre}" son: {", ".join(transiciones_permitidas)}'
            else:
                mensaje_error += f'No hay transiciones permitidas desde "{estado_actual_nombre}"'
            
            return JsonResponse({'error': mensaje_error}, status=400)

        with transaction.atomic():
            proyecto.estado = nuevo_estado
            proyecto.fecha_actualizacion = datetime.now()
            proyecto.save()

        # Mensaje descriptivo de la transición
        direccion = 'avanzó' if nuevo_estado.orden > estado_actual.orden else 'retrocedió'
        
        return JsonResponse({
            'mensaje': f'El proyecto {direccion} de "{estado_actual.nombre}" a "{nuevo_estado.nombre}" exitosamente',
            'estado_anterior': {
                'nombre': estado_actual.nombre,
                'color': estado_actual.color
            },
            'estado_actual': {
                'nombre': nuevo_estado.nombre,
                'color': nuevo_estado.color
            }
        }, status=200)

    except Proyectos.DoesNotExist:
        return JsonResponse({'error': 'Proyecto no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# -----------------------------
# Función helper: Cambiar proyecto a fase "Generación"
# -----------------------------
def cambiar_proyecto_a_generacion(proyecto_id):
    """
    Cambia un proyecto de la fase "Especificaciones" a "Generación" 
    cuando se crean casos de prueba.
    
    Esta función es llamada automáticamente al crear pruebas.
    """
    try:
        proyecto = Proyectos.objects.select_related('estado').get(
            id=proyecto_id, 
            activo=True
        )
        
        # Solo cambiar si está en fase de Especificaciones
        if proyecto.estado and proyecto.estado.nombre == 'especificaciones':
            estado_generacion = EstadosProyecto.objects.get(
                nombre='generacion', 
                activo=True
            )
            
            proyecto.estado = estado_generacion
            proyecto.fecha_actualizacion = datetime.now()
            proyecto.save()
            
            return True, f"Proyecto '{proyecto.nombre}' pasó a fase de Generación"
        
        return False, f"Proyecto ya está en fase '{proyecto.estado.nombre if proyecto.estado else 'sin estado'}'"
        
    except Proyectos.DoesNotExist:
        return False, "Proyecto no encontrado"
    except EstadosProyecto.DoesNotExist:
        return False, "Estado 'generacion' no encontrado en el sistema"
    except Exception as e:
        return False, f"Error al cambiar estado: {str(e)}"


# -----------------------------
# Eliminar proyecto (soft delete)
# -----------------------------
@csrf_exempt
@require_http_methods(["POST"])
def eliminar_proyecto(request, proyecto_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        usuario_obj = Usuarios.objects.get(id=payload['usuario_id'], activo=True)
        proyecto = Proyectos.objects.get(id=proyecto_id, usuario=usuario_obj, activo=True)

        proyecto.activo = False
        proyecto.save()

        return JsonResponse({'mensaje': 'Proyecto eliminado exitosamente'}, status=200)

    except Proyectos.DoesNotExist:
        return JsonResponse({'error': 'Proyecto no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# -----------------------------
# Listar estados de proyecto disponibles
# -----------------------------
@require_http_methods(["GET"])
def listar_estados_proyecto(request):
    """Endpoint para obtener todos los estados de proyecto disponibles"""
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        estados = EstadosProyecto.objects.filter(activo=True).order_by('orden')
        
        estados_data = [{
            'id': e.id,
            'nombre': e.nombre,
            'descripcion': e.descripcion,
            'orden': e.orden,
            'color': e.color
        } for e in estados]

        return JsonResponse({'estados': estados_data}, status=200)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)