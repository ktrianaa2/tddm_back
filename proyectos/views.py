from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from datetime import datetime
from proyectos.models import Proyectos
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
        estado = request.POST.get('estado', 'Requisitos')  # Valor por defecto

        if not nombre:
            return JsonResponse({'error': 'El campo nombre es requerido'}, status=400)

        usuario_obj = Usuarios.objects.get(id=payload['usuario_id'], activo=True)

        with transaction.atomic():
            proyecto = Proyectos.objects.create(
                nombre=nombre,
                descripcion=descripcion,
                estado=estado,
                usuario=usuario_obj,
                activo=True
            )

        return JsonResponse({
            'mensaje': 'Proyecto creado exitosamente',
            'proyecto_id': proyecto.id,
            'nombre': proyecto.nombre,
            'estado': proyecto.estado
        }, status=201)

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
        proyectos = Proyectos.objects.filter(usuario=usuario_obj, activo=True)

        proyectos_data = []
        for p in proyectos:
            proyectos_data.append({
                'proyecto_id': p.id,
                'nombre': p.nombre,
                'descripcion': p.descripcion,
                'estado': p.estado,
                'fecha_creacion': p.fecha_creacion,
                'fecha_actualizacion': p.fecha_actualizacion
            })

        return JsonResponse({'proyectos': proyectos_data}, status=200)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
@require_http_methods(["GET"])
def obtener_proyecto(request, proyecto_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        usuario_obj = Usuarios.objects.get(id=payload['usuario_id'], activo=True)
        proyecto = Proyectos.objects.get(id=proyecto_id, usuario=usuario_obj, activo=True)

        return JsonResponse({
            'proyecto_id': proyecto.id,
            'nombre': proyecto.nombre,
            'descripcion': proyecto.descripcion,
            'estado': proyecto.estado,
            'fecha_creacion': proyecto.fecha_creacion,
            'fecha_actualizacion': proyecto.fecha_actualizacion,
        }, status=200)

    except Proyectos.DoesNotExist:
        return JsonResponse({'error': 'Proyecto no encontrado'}, status=404)



# -----------------------------
# Editar proyecto con FormData
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
        estado = request.POST.get('estado')

        with transaction.atomic():
            if nombre:
                proyecto.nombre = nombre
            if descripcion is not None:
                proyecto.descripcion = descripcion
            if estado:
                proyecto.estado = estado

            proyecto.fecha_actualizacion = datetime.now()
            proyecto.save()

        return JsonResponse({'mensaje': 'Proyecto actualizado exitosamente'}, status=200)

    except Proyectos.DoesNotExist:
        return JsonResponse({'error': 'Proyecto no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# -----------------------------
# Eliminar proyecto (FormData POST)
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