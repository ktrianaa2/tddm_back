from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from datetime import datetime
from usuarios.views import validar_token
from usuarios.models import Usuarios
from catalogos.models import *

# -----------------------------
# Crear Tipo de Requisito
# -----------------------------
@csrf_exempt
@require_http_methods(["POST"])
def crear_tipo_requisito(request):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion', '')

        if not nombre:
            return JsonResponse({'error': 'El campo nombre es requerido'}, status=400)

        usuario_obj = Usuarios.objects.get(id=payload['usuario_id'], activo=True)

        with transaction.atomic():
            tipo = TiposRequisito.objects.create(
                nombre=nombre,
                descripcion=descripcion,
                activo=True
            )

        return JsonResponse({
            'mensaje': 'Tipo de requisito creado exitosamente',
            'tipo_id': tipo.id,
            'nombre': tipo.nombre,
            'descripcion': tipo.descripcion,
        }, status=201)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# -----------------------------
# Listar todos los Tipos de Requisito activos
# -----------------------------
@require_http_methods(["GET"])
def listar_tipos_requisito(request):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        tipos = TiposRequisito.objects.filter(activo=True)
        tipos_data = []

        for t in tipos:
            tipos_data.append({
                'tipo_id': t.id,
                'nombre': t.nombre,
                'descripcion': t.descripcion,
            })

        return JsonResponse({'tipos_requisito': tipos_data}, status=200)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# -----------------------------
# Obtener un Tipo de Requisito por ID
# -----------------------------
@require_http_methods(["GET"])
def obtener_tipo_requisito(request, tipo_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        tipo = TiposRequisito.objects.get(id=tipo_id, activo=True)
        return JsonResponse({
            'tipo_id': tipo.id,
            'nombre': tipo.nombre,
            'descripcion': tipo.descripcion,
        }, status=200)

    except TiposRequisito.DoesNotExist:
        return JsonResponse({'error': 'Tipo de requisito no encontrado'}, status=404)


# -----------------------------
# Editar Tipo de Requisito
# -----------------------------
@csrf_exempt
@require_http_methods(["POST"])
def editar_tipo_requisito(request, tipo_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        tipo = TiposRequisito.objects.get(id=tipo_id, activo=True)
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion')

        with transaction.atomic():
            if nombre:
                tipo.nombre = nombre
            if descripcion is not None:
                tipo.descripcion = descripcion
            tipo.save()

        return JsonResponse({'mensaje': 'Tipo de requisito actualizado exitosamente'}, status=200)

    except TiposRequisito.DoesNotExist:
        return JsonResponse({'error': 'Tipo de requisito no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# -----------------------------
# Deshabilitar Tipo de Requisito
# -----------------------------
@csrf_exempt
@require_http_methods(["POST"])
def deshabilitar_tipo_requisito(request, tipo_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        tipo = TiposRequisito.objects.get(id=tipo_id, activo=True)
        tipo.activo = False
        tipo.save()
        return JsonResponse({'mensaje': 'Tipo de requisito deshabilitado exitosamente'}, status=200)

    except TiposRequisito.DoesNotExist:
        return JsonResponse({'error': 'Tipo de requisito no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# -----------------------------
# Crear Prioridad
# -----------------------------
@csrf_exempt
@require_http_methods(["POST"])
def crear_prioridad(request):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        nombre = request.POST.get('nombre')
        nivel = request.POST.get('nivel')
        descripcion = request.POST.get('descripcion', '')

        if not nombre or not nivel:
            return JsonResponse({'error': 'Los campos nombre y nivel son requeridos'}, status=400)

        nivel = int(nivel)

        with transaction.atomic():
            prioridad = Prioridades.objects.create(
                nombre=nombre,
                nivel=nivel,
                descripcion=descripcion,
                activo=True
            )

        return JsonResponse({
            'mensaje': 'Prioridad creada exitosamente',
            'prioridad_id': prioridad.id,
            'nombre': prioridad.nombre,
            'nivel': prioridad.nivel,
            'descripcion': prioridad.descripcion,
        }, status=201)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# -----------------------------
# Listar Prioridades activas
# -----------------------------
@require_http_methods(["GET"])
def listar_prioridades(request):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        prioridades = Prioridades.objects.filter(activo=True).order_by('nivel')
        prioridades_data = []

        for p in prioridades:
            prioridades_data.append({
                'prioridad_id': p.id,
                'nombre': p.nombre,
                'nivel': p.nivel,
                'descripcion': p.descripcion,
            })

        return JsonResponse({'prioridades': prioridades_data}, status=200)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# -----------------------------
# Obtener Prioridad por ID
# -----------------------------
@require_http_methods(["GET"])
def obtener_prioridad(request, prioridad_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        prioridad = Prioridades.objects.get(id=prioridad_id, activo=True)
        return JsonResponse({
            'prioridad_id': prioridad.id,
            'nombre': prioridad.nombre,
            'nivel': prioridad.nivel,
            'descripcion': prioridad.descripcion,
        }, status=200)

    except Prioridades.DoesNotExist:
        return JsonResponse({'error': 'Prioridad no encontrada'}, status=404)


# -----------------------------
# Editar Prioridad
# -----------------------------
@csrf_exempt
@require_http_methods(["POST"])
def editar_prioridad(request, prioridad_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        prioridad = Prioridades.objects.get(id=prioridad_id, activo=True)
        nombre = request.POST.get('nombre')
        nivel = request.POST.get('nivel')
        descripcion = request.POST.get('descripcion')

        with transaction.atomic():
            if nombre:
                prioridad.nombre = nombre
            if nivel:
                prioridad.nivel = int(nivel)
            if descripcion is not None:
                prioridad.descripcion = descripcion
            prioridad.save()

        return JsonResponse({'mensaje': 'Prioridad actualizada exitosamente'}, status=200)

    except Prioridades.DoesNotExist:
        return JsonResponse({'error': 'Prioridad no encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# -----------------------------
# Deshabilitar Prioridad
# -----------------------------
@csrf_exempt
@require_http_methods(["POST"])
def deshabilitar_prioridad(request, prioridad_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        prioridad = Prioridades.objects.get(id=prioridad_id, activo=True)
        prioridad.activo = False
        prioridad.save()
        return JsonResponse({'mensaje': 'Prioridad deshabilitada exitosamente'}, status=200)

    except Prioridades.DoesNotExist:
        return JsonResponse({'error': 'Prioridad no encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
# -----------------------------
# Crear Estado de Proyecto
# -----------------------------
@csrf_exempt
@require_http_methods(["POST"])
def crear_estado_proyecto(request):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        nombre = request.POST.get('nombre')
        orden = request.POST.get('orden')
        descripcion = request.POST.get('descripcion', '')

        if not nombre or not orden:
            return JsonResponse({'error': 'Los campos nombre y orden son requeridos'}, status=400)

        orden = int(orden)

        with transaction.atomic():
            estado = EstadosProyecto.objects.create(
                nombre=nombre,
                orden=orden,
                descripcion=descripcion,
                activo=True
            )

        return JsonResponse({
            'mensaje': 'Estado de proyecto creado exitosamente',
            'estado_id': estado.id,
            'nombre': estado.nombre,
            'orden': estado.orden,
            'descripcion': estado.descripcion,
        }, status=201)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# -----------------------------
# Listar Estados de Proyecto activos
# -----------------------------
@require_http_methods(["GET"])
def listar_estados_proyecto(request):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        estados = EstadosProyecto.objects.filter(activo=True).order_by('orden')
        estados_data = []

        for e in estados:
            estados_data.append({
                'estado_id': e.id,
                'nombre': e.nombre,
                'orden': e.orden,
                'descripcion': e.descripcion,
            })

        return JsonResponse({'estados_proyecto': estados_data}, status=200)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# -----------------------------
# Obtener Estado de Proyecto por ID
# -----------------------------
@require_http_methods(["GET"])
def obtener_estado_proyecto(request, estado_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        estado = EstadosProyecto.objects.get(id=estado_id, activo=True)
        return JsonResponse({
            'estado_id': estado.id,
            'nombre': estado.nombre,
            'orden': estado.orden,
            'descripcion': estado.descripcion,
        }, status=200)

    except EstadosProyecto.DoesNotExist:
        return JsonResponse({'error': 'Estado de proyecto no encontrado'}, status=404)


# -----------------------------
# Editar Estado de Proyecto
# -----------------------------
@csrf_exempt
@require_http_methods(["POST"])
def editar_estado_proyecto(request, estado_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        estado = EstadosProyecto.objects.get(id=estado_id, activo=True)
        nombre = request.POST.get('nombre')
        orden = request.POST.get('orden')
        descripcion = request.POST.get('descripcion')

        with transaction.atomic():
            if nombre:
                estado.nombre = nombre
            if orden:
                estado.orden = int(orden)
            if descripcion is not None:
                estado.descripcion = descripcion
            estado.save()

        return JsonResponse({'mensaje': 'Estado de proyecto actualizado exitosamente'}, status=200)

    except EstadosProyecto.DoesNotExist:
        return JsonResponse({'error': 'Estado de proyecto no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# -----------------------------
# Deshabilitar Estado de Proyecto
# -----------------------------
@csrf_exempt
@require_http_methods(["POST"])
def deshabilitar_estado_proyecto(request, estado_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        estado = EstadosProyecto.objects.get(id=estado_id, activo=True)
        estado.activo = False
        estado.save()
        return JsonResponse({'mensaje': 'Estado de proyecto deshabilitado exitosamente'}, status=200)

    except EstadosProyecto.DoesNotExist:
        return JsonResponse({'error': 'Estado de proyecto no encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
from catalogos.models import EstadosElemento, TiposRelacionCu, TiposRelacionRequisito

# -----------------------------
# CRUD para EstadosElemento
# -----------------------------
@csrf_exempt
@require_http_methods(["POST"])
def crear_estado_elemento(request):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        nombre = request.POST.get('nombre')
        tipo = request.POST.get('tipo')
        descripcion = request.POST.get('descripcion', '')

        if not nombre or not tipo:
            return JsonResponse({'error': 'Los campos nombre y tipo son requeridos'}, status=400)
        if tipo not in ['requisito', 'caso_uso', 'historia_usuario']:
            return JsonResponse({'error': 'Tipo inválido'}, status=400)

        with transaction.atomic():
            estado = EstadosElemento.objects.create(
                nombre=nombre,
                tipo=tipo,
                descripcion=descripcion,
                activo=True
            )

        return JsonResponse({
            'mensaje': 'Estado de elemento creado exitosamente',
            'id': estado.id,
            'nombre': estado.nombre,
            'tipo': estado.tipo,
            'descripcion': estado.descripcion
        }, status=201)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def listar_estados_elemento(request):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        estados = EstadosElemento.objects.filter(activo=True).order_by('tipo', 'nombre')
        data = [{'id': e.id, 'nombre': e.nombre, 'tipo': e.tipo, 'descripcion': e.descripcion} for e in estados]
        return JsonResponse({'estados_elemento': data}, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def obtener_estado_elemento(request, estado_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)
    try:
        e = EstadosElemento.objects.get(id=estado_id, activo=True)
        return JsonResponse({'id': e.id, 'nombre': e.nombre, 'tipo': e.tipo, 'descripcion': e.descripcion}, status=200)
    except EstadosElemento.DoesNotExist:
        return JsonResponse({'error': 'Estado de elemento no encontrado'}, status=404)


@csrf_exempt
@require_http_methods(["POST"])
def editar_estado_elemento(request, estado_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)
    try:
        e = EstadosElemento.objects.get(id=estado_id, activo=True)
        nombre = request.POST.get('nombre')
        tipo = request.POST.get('tipo')
        descripcion = request.POST.get('descripcion')

        with transaction.atomic():
            if nombre:
                e.nombre = nombre
            if tipo and tipo in ['requisito', 'caso_uso', 'historia_usuario']:
                e.tipo = tipo
            if descripcion is not None:
                e.descripcion = descripcion
            e.save()
        return JsonResponse({'mensaje': 'Estado de elemento actualizado exitosamente'}, status=200)
    except EstadosElemento.DoesNotExist:
        return JsonResponse({'error': 'Estado de elemento no encontrado'}, status=404)
    except Exception as ex:
        return JsonResponse({'error': str(ex)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def deshabilitar_estado_elemento(request, estado_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)
    try:
        e = EstadosElemento.objects.get(id=estado_id, activo=True)
        e.activo = False
        e.save()
        return JsonResponse({'mensaje': 'Estado de elemento deshabilitado exitosamente'}, status=200)
    except EstadosElemento.DoesNotExist:
        return JsonResponse({'error': 'Estado de elemento no encontrado'}, status=404)
    except Exception as ex:
        return JsonResponse({'error': str(ex)}, status=500)


# -----------------------------
# CRUD para TiposRelacionCu
# -----------------------------
@csrf_exempt
@require_http_methods(["POST"])
def crear_tipo_relacion_cu(request):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)
    try:
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion', '')

        if not nombre:
            return JsonResponse({'error': 'Nombre requerido'}, status=400)

        with transaction.atomic():
            tr = TiposRelacionCu.objects.create(nombre=nombre, descripcion=descripcion, activo=True)

        return JsonResponse({'mensaje': 'Tipo de relación CU creado', 'id': tr.id, 'nombre': tr.nombre}, status=201)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def listar_tipos_relacion_cu(request):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)
    try:
        trs = TiposRelacionCu.objects.filter(activo=True).order_by('nombre')
        data = [{'id': t.id, 'nombre': t.nombre, 'descripcion': t.descripcion} for t in trs]
        return JsonResponse({'tipos_relacion_cu': data}, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def editar_tipo_relacion_cu(request, tr_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)
    try:
        tr = TiposRelacionCu.objects.get(id=tr_id, activo=True)
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion')
        with transaction.atomic():
            if nombre:
                tr.nombre = nombre
            if descripcion is not None:
                tr.descripcion = descripcion
            tr.save()
        return JsonResponse({'mensaje': 'Tipo de relación CU actualizado'}, status=200)
    except TiposRelacionCu.DoesNotExist:
        return JsonResponse({'error': 'Tipo de relación CU no encontrado'}, status=404)


@csrf_exempt
@require_http_methods(["POST"])
def deshabilitar_tipo_relacion_cu(request, tr_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)
    try:
        tr = TiposRelacionCu.objects.get(id=tr_id, activo=True)
        tr.activo = False
        tr.save()
        return JsonResponse({'mensaje': 'Tipo de relación CU deshabilitado'}, status=200)
    except TiposRelacionCu.DoesNotExist:
        return JsonResponse({'error': 'Tipo de relación CU no encontrado'}, status=404)


# -----------------------------
# CRUD para TiposRelacionRequisito
# -----------------------------
@csrf_exempt
@require_http_methods(["POST"])
def crear_tipo_relacion_requisito(request):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)
    try:
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion', '')
        if not nombre:
            return JsonResponse({'error': 'Nombre requerido'}, status=400)
        with transaction.atomic():
            tr = TiposRelacionRequisito.objects.create(nombre=nombre, descripcion=descripcion, activo=True)
        return JsonResponse({'mensaje': 'Tipo de relación requisito creado', 'id': tr.id, 'nombre': tr.nombre}, status=201)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def listar_tipos_relacion_requisito(request):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)
    try:
        trs = TiposRelacionRequisito.objects.filter(activo=True).order_by('nombre')
        data = [{'id': t.id, 'nombre': t.nombre, 'descripcion': t.descripcion} for t in trs]
        return JsonResponse({'tipos_relacion_requisito': data}, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def editar_tipo_relacion_requisito(request, tr_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)
    try:
        tr = TiposRelacionRequisito.objects.get(id=tr_id, activo=True)
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion')
        with transaction.atomic():
            if nombre:
                tr.nombre = nombre
            if descripcion is not None:
                tr.descripcion = descripcion
            tr.save()
        return JsonResponse({'mensaje': 'Tipo de relación requisito actualizado'}, status=200)
    except TiposRelacionRequisito.DoesNotExist:
        return JsonResponse({'error': 'Tipo de relación requisito no encontrado'}, status=404)


@csrf_exempt
@require_http_methods(["POST"])
def deshabilitar_tipo_relacion_requisito(request, tr_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)
    try:
        tr = TiposRelacionRequisito.objects.get(id=tr_id, activo=True)
        tr.activo = False
        tr.save()
        return JsonResponse({'mensaje': 'Tipo de relación requisito deshabilitado'}, status=200)
    except TiposRelacionRequisito.DoesNotExist:
        return JsonResponse({'error': 'Tipo de relación requisito no encontrado'}, status=404)

# -----------------------------
# CRUD para TiposEstimacion
# -----------------------------

@csrf_exempt
@require_http_methods(["POST"])
def crear_tipo_estimacion(request):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)
    try:
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion', '')
        if not nombre:
            return JsonResponse({'error': 'Nombre requerido'}, status=400)

        with transaction.atomic():
            te = TiposEstimacion.objects.create(nombre=nombre, descripcion=descripcion, activo=True)

        return JsonResponse({
            'mensaje': 'Tipo de estimación creado',
            'id': te.id,
            'nombre': te.nombre
        }, status=201)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def listar_tipos_estimacion(request):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)
    try:
        tes = TiposEstimacion.objects.filter(activo=True).order_by('nombre')
        data = [{'id': t.id, 'nombre': t.nombre, 'descripcion': t.descripcion} for t in tes]
        return JsonResponse({'tipos_estimacion': data}, status=200)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def editar_tipo_estimacion(request, te_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)
    try:
        te = TiposEstimacion.objects.get(id=te_id, activo=True)
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion')

        with transaction.atomic():
            if nombre:
                te.nombre = nombre
            if descripcion is not None:
                te.descripcion = descripcion
            te.save()

        return JsonResponse({'mensaje': 'Tipo de estimación actualizado'}, status=200)

    except TiposEstimacion.DoesNotExist:
        return JsonResponse({'error': 'Tipo de estimación no encontrado'}, status=404)


@csrf_exempt
@require_http_methods(["POST"])
def deshabilitar_tipo_estimacion(request, te_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)
    try:
        te = TiposEstimacion.objects.get(id=te_id, activo=True)
        te.activo = False
        te.save()
        return JsonResponse({'mensaje': 'Tipo de estimación deshabilitado'}, status=200)
    except TiposEstimacion.DoesNotExist:
        return JsonResponse({'error': 'Tipo de estimación no encontrado'}, status=404)