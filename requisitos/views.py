# requisitos/views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.shortcuts import get_object_or_404
from requisitos.models import Requisitos, RelacionesRequisitos, TiposRequisito, Prioridades, EstadosElemento, TiposRelacionRequisito
from proyectos.models import Proyectos
from usuarios.models import Usuarios
from usuarios.views import validar_token
import json

# -----------------------------
# Crear requisito
# -----------------------------
@csrf_exempt
@require_http_methods(["POST"])
def crear_requisito(request):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        data = json.loads(request.body.decode('utf-8'))

        # Campos obligatorios
        nombre = data.get('nombre')
        descripcion = data.get('descripcion')
        tipo_id = data.get('tipo_id')
        criterios = data.get('criterios')
        proyecto_id = data.get('proyecto_id')
        
        # Campos opcionales
        prioridad_id = data.get('prioridad_id')
        estado_id = data.get('estado_id', 1)  # Por defecto "Pendiente"
        origen = data.get('origen', '')
        condiciones_previas = data.get('condiciones_previas', '')
        relaciones = data.get('relaciones_requisitos', [])

        # Validaciones
        if not (nombre and descripcion and tipo_id and criterios and proyecto_id):
            return JsonResponse({'error': 'Campos obligatorios faltantes'}, status=400)

        # Validar que el proyecto existe
        try:
            proyecto = Proyectos.objects.get(id=proyecto_id, activo=True)
        except Proyectos.DoesNotExist:
            return JsonResponse({'error': 'El proyecto especificado no existe'}, status=400)

        # Validar que el tipo existe
        try:
            tipo = TiposRequisito.objects.get(id=tipo_id)
        except TiposRequisito.DoesNotExist:
            return JsonResponse({'error': 'El tipo de requisito especificado no existe'}, status=400)

        # Validar prioridad si se proporciona
        if prioridad_id:
            try:
                Prioridades.objects.get(id=prioridad_id)
            except Prioridades.DoesNotExist:
                return JsonResponse({'error': 'La prioridad especificada no existe'}, status=400)

        # Validar estado si se proporciona
        if estado_id:
            try:
                EstadosElemento.objects.get(id=estado_id)
            except EstadosElemento.DoesNotExist:
                return JsonResponse({'error': 'El estado especificado no existe'}, status=400)

        with transaction.atomic():
            # Crear el requisito
            requisito = Requisitos.objects.create(
                nombre=nombre,
                descripcion=descripcion,
                tipo_id=tipo_id,  
                criterios=criterios,
                prioridad_id=prioridad_id,  
                estado_id=estado_id,
                origen=origen,
                condiciones_previas=condiciones_previas,
                proyecto_id=proyecto_id,  
                activo=True
            )

            # Guardar relaciones si vienen
            for rel in relaciones:
                requisito_destino_id = rel.get('requisito_id')
                tipo_relacion_id = rel.get('tipo_relacion_id')
                descripcion_relacion = rel.get('descripcion', '')

                if requisito_destino_id and tipo_relacion_id:
                    # Validar que el requisito destino existe
                    try:
                        Requisitos.objects.get(id=requisito_destino_id, activo=True)
                    except Requisitos.DoesNotExist:
                        continue  # Saltar esta relación si el requisito no existe

                    # Validar que el tipo de relación existe
                    try:
                        TiposRelacionRequisito.objects.get(id=tipo_relacion_id)
                    except TiposRelacionRequisito.DoesNotExist:
                        continue  # Saltar esta relación si el tipo no existe

                    # Crear la relación
                    RelacionesRequisitos.objects.create(
                        requisito_origen=requisito,
                        requisito_destino_id=requisito_destino_id,
                        tipo_relacion_id=tipo_relacion_id,
                        descripcion=descripcion_relacion
                    )

        return JsonResponse({
            'mensaje': 'Requisito creado exitosamente',
            'requisito_id': requisito.id
        }, status=201)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Error interno del servidor: {str(e)}'}, status=500)


# -----------------------------
# Obtener un requisito específico
# -----------------------------
@require_http_methods(["GET"])
def obtener_requisito(request, requisito_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        # Obtener el requisito
        requisito = get_object_or_404(Requisitos, id=requisito_id, activo=True)

        def safe_key_conversion(value):
            if not value:
                return None
            return value.lower().replace(' ', '-').replace('ó', 'o').replace('í', 'i')

        # Obtener las relaciones del requisito
        relaciones = RelacionesRequisitos.objects.filter(
            requisito_origen=requisito
        ).select_related('requisito_destino', 'tipo_relacion')

        relaciones_data = []
        for rel in relaciones:
            relaciones_data.append({
                'id': rel.id,
                'requisito_id': rel.requisito_destino.id,
                'tipo_relacion': str(rel.tipo_relacion.id),
                'descripcion': rel.descripcion or ''
            })

        data = {
            'id': requisito.id,
            'nombre': requisito.nombre,
            'descripcion': requisito.descripcion,
            'tipo': safe_key_conversion(requisito.tipo.nombre) if requisito.tipo else None,
            'criterios': requisito.criterios,
            'prioridad': safe_key_conversion(requisito.prioridad.nombre) if requisito.prioridad else None,
            'estado': safe_key_conversion(requisito.estado.nombre) if requisito.estado else None,
            'origen': requisito.origen,
            'condiciones_previas': requisito.condiciones_previas,
            'proyecto_id': requisito.proyecto_id,
            'fecha_creacion': requisito.fecha_creacion.isoformat() if requisito.fecha_creacion else None,
            'relaciones_requisitos': relaciones_data
        }

        return JsonResponse({'requisito': data}, status=200)

    except Exception as e:
        return JsonResponse({'error': f'Error interno del servidor: {str(e)}'}, status=500)


# -----------------------------
# Actualizar requisito
# -----------------------------
@csrf_exempt
@require_http_methods(["PUT", "PATCH"])
def actualizar_requisito(request, requisito_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        data = json.loads(request.body.decode('utf-8'))
        
        # Obtener el requisito existente
        requisito = get_object_or_404(Requisitos, id=requisito_id, activo=True)

        # Campos que se pueden actualizar
        if 'nombre' in data:
            if not data['nombre'] or len(data['nombre']) < 5:
                return JsonResponse({'error': 'El nombre debe tener al menos 5 caracteres'}, status=400)
            requisito.nombre = data['nombre']

        if 'descripcion' in data:
            if not data['descripcion'] or len(data['descripcion']) < 10:
                return JsonResponse({'error': 'La descripción debe tener al menos 10 caracteres'}, status=400)
            requisito.descripcion = data['descripcion']

        if 'criterios' in data:
            if not data['criterios'] or len(data['criterios']) < 10:
                return JsonResponse({'error': 'Los criterios deben tener al menos 10 caracteres'}, status=400)
            requisito.criterios = data['criterios']

        if 'tipo_id' in data and data['tipo_id']:
            try:
                TiposRequisito.objects.get(id=data['tipo_id'])
                requisito.tipo_id = data['tipo_id']
            except TiposRequisito.DoesNotExist:
                return JsonResponse({'error': 'El tipo de requisito especificado no existe'}, status=400)

        if 'prioridad_id' in data:
            if data['prioridad_id']:
                try:
                    Prioridades.objects.get(id=data['prioridad_id'])
                    requisito.prioridad_id = data['prioridad_id']
                except Prioridades.DoesNotExist:
                    return JsonResponse({'error': 'La prioridad especificada no existe'}, status=400)
            else:
                requisito.prioridad_id = None

        if 'estado_id' in data and data['estado_id']:
            try:
                EstadosElemento.objects.get(id=data['estado_id'])
                requisito.estado_id = data['estado_id']
            except EstadosElemento.DoesNotExist:
                return JsonResponse({'error': 'El estado especificado no existe'}, status=400)

        if 'origen' in data:
            requisito.origen = data['origen'] or ''

        if 'condiciones_previas' in data:
            requisito.condiciones_previas = data['condiciones_previas'] or ''

        with transaction.atomic():
            # Guardar los cambios del requisito
            requisito.save()

            # Actualizar relaciones si vienen en la petición
            if 'relaciones_requisitos' in data:
                # Eliminar todas las relaciones existentes
                RelacionesRequisitos.objects.filter(requisito_origen=requisito).delete()

                # Crear las nuevas relaciones
                relaciones = data['relaciones_requisitos']
                for rel in relaciones:
                    requisito_destino_id = rel.get('requisito_id')
                    tipo_relacion_id = rel.get('tipo_relacion_id')
                    descripcion_relacion = rel.get('descripcion', '')

                    if requisito_destino_id and tipo_relacion_id:
                        # Validar que el requisito destino existe
                        try:
                            Requisitos.objects.get(id=requisito_destino_id, activo=True)
                        except Requisitos.DoesNotExist:
                            continue  # Saltar esta relación

                        # Validar que el tipo de relación existe
                        try:
                            TiposRelacionRequisito.objects.get(id=tipo_relacion_id)
                        except TiposRelacionRequisito.DoesNotExist:
                            continue  # Saltar esta relación

                        # No permitir autorrelaciones
                        if int(requisito_destino_id) == requisito.id:
                            continue

                        # Crear la relación
                        RelacionesRequisitos.objects.create(
                            requisito_origen=requisito,
                            requisito_destino_id=requisito_destino_id,
                            tipo_relacion_id=tipo_relacion_id,
                            descripcion=descripcion_relacion
                        )

        return JsonResponse({
            'mensaje': 'Requisito actualizado exitosamente',
            'requisito_id': requisito.id
        }, status=200)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Error interno del servidor: {str(e)}'}, status=500)


# -----------------------------
# Eliminar requisito (soft delete)
# -----------------------------
@csrf_exempt
@require_http_methods(["DELETE"])
def eliminar_requisito(request, requisito_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        requisito = get_object_or_404(Requisitos, id=requisito_id, activo=True)

        with transaction.atomic():
            # Soft delete del requisito
            requisito.activo = False
            requisito.save()

            # Eliminar todas las relaciones donde este requisito aparece
            RelacionesRequisitos.objects.filter(
                requisito_origen=requisito
            ).delete()
            
            RelacionesRequisitos.objects.filter(
                requisito_destino=requisito
            ).delete()

        return JsonResponse({
            'mensaje': 'Requisito eliminado exitosamente'
        }, status=200)

    except Exception as e:
        return JsonResponse({'error': f'Error interno del servidor: {str(e)}'}, status=500)


# -----------------------------
# Listar requisitos de un proyecto
# -----------------------------
@require_http_methods(["GET"])
def listar_requisitos(request, proyecto_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        # Validar que el proyecto existe
        try:
            Proyectos.objects.get(id=proyecto_id, activo=True)
        except Proyectos.DoesNotExist:
            return JsonResponse({'error': 'El proyecto especificado no existe'}, status=404)

        # Obtener requisitos del proyecto
        requisitos = Requisitos.objects.filter(
            proyecto_id=proyecto_id, 
            activo=True
        ).select_related('tipo', 'prioridad', 'estado').order_by('-fecha_creacion')

        data = []
        for r in requisitos:
            def safe_key_conversion(value):
                if not value:
                    return None
                return value.lower().replace(' ', '-').replace('ó', 'o').replace('í', 'i')

            data.append({
                'id': r.id,
                'nombre': r.nombre,
                'descripcion': r.descripcion,
                'tipo': safe_key_conversion(r.tipo.nombre) if r.tipo else None,
                'criterios': r.criterios,
                'prioridad': safe_key_conversion(r.prioridad.nombre) if r.prioridad else None,
                'estado': safe_key_conversion(r.estado.nombre) if r.estado else None,
                'origen': r.origen,
                'condiciones_previas': r.condiciones_previas,
                'proyecto_id': r.proyecto_id,
                'fecha_creacion': r.fecha_creacion.isoformat() if r.fecha_creacion else None
            })

        return JsonResponse({'requisitos': data}, status=200)

    except Exception as e:
        return JsonResponse({'error': f'Error interno del servidor: {str(e)}'}, status=500)


# -----------------------------
# Obtener relaciones de un requisito específico
# -----------------------------
@require_http_methods(["GET"])
def obtener_relaciones_requisito(request, requisito_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        # Validar que el requisito existe
        requisito = get_object_or_404(Requisitos, id=requisito_id, activo=True)

        # Obtener relaciones donde este requisito es el origen
        relaciones = RelacionesRequisitos.objects.filter(
            requisito_origen=requisito
        ).select_related('requisito_destino', 'tipo_relacion')

        data = []
        for rel in relaciones:
            data.append({
                'id': rel.id,
                'requisito_id': rel.requisito_destino.id,
                'tipo_relacion': str(rel.tipo_relacion.id),
                'descripcion': rel.descripcion or ''
            })

        return JsonResponse({'relaciones': data}, status=200)

    except Exception as e:
        return JsonResponse({'error': f'Error interno del servidor: {str(e)}'}, status=500)


# -----------------------------
# Obtener catálogos para el formulario
# -----------------------------
@require_http_methods(["GET"])
def obtener_catalogos_requisitos(request):
    """
    Endpoint para obtener los catálogos de tipos, prioridades, estados y tipos de relación
    """
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        def safe_key_conversion(value):
            if not value:
                return ''
            return value.lower().replace(' ', '-').replace('ó', 'o').replace('í', 'i')

        # Obtener tipos de requisito
        tipos = []
        tipos_qs = TiposRequisito.objects.all().order_by('nombre')
        if hasattr(TiposRequisito, 'activo'):
            tipos_qs = tipos_qs.filter(activo=True)
            
        for tipo in tipos_qs:
            tipos.append({
                'id': tipo.id,
                'nombre': tipo.nombre,
                'key': safe_key_conversion(tipo.nombre)
            })

        # Obtener prioridades
        prioridades = []
        prioridades_qs = Prioridades.objects.all().order_by('id')
        if hasattr(Prioridades, 'activo'):
            prioridades_qs = prioridades_qs.filter(activo=True)
            
        for prioridad in prioridades_qs:
            prioridades.append({
                'id': prioridad.id,
                'nombre': prioridad.nombre,
                'key': safe_key_conversion(prioridad.nombre)
            })

        # Obtener estados (filtrar por tipo si es necesario)
        estados = []
        estados_qs = EstadosElemento.objects.all().order_by('id')
        if hasattr(EstadosElemento, 'activo'):
            estados_qs = estados_qs.filter(activo=True)
            
        for estado in estados_qs:
            estados.append({
                'id': estado.id,
                'nombre': estado.nombre,
                'key': safe_key_conversion(estado.nombre)
            })

        # Obtener tipos de relación
        tipos_relacion = []
        tipos_relacion_qs = TiposRelacionRequisito.objects.all().order_by('nombre')
        if hasattr(TiposRelacionRequisito, 'activo'):
            tipos_relacion_qs = tipos_relacion_qs.filter(activo=True)
            
        for tipo_rel in tipos_relacion_qs:
            tipos_relacion.append({
                'id': tipo_rel.id,
                'nombre': tipo_rel.nombre,
                'key': safe_key_conversion(tipo_rel.nombre),
                'descripcion': getattr(tipo_rel, 'descripcion', '') or ''
            })

        return JsonResponse({
            'tipos_requisito': tipos,
            'prioridades': prioridades,
            'estados': estados,
            'tipos_relacion': tipos_relacion
        }, status=200)

    except Exception as e:
        return JsonResponse({'error': f'Error interno del servidor: {str(e)}'}, status=500)