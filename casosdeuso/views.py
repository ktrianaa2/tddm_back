from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.shortcuts import get_object_or_404
from casosdeuso.models import CasosUso, RelacionesCasosUso, EstadosElemento, TiposRelacionCu, Prioridades
from proyectos.models import Proyectos
from usuarios.views import validar_token
import json

# -----------------------------
# Crear caso de uso
# -----------------------------
@csrf_exempt
@require_http_methods(["POST"])
def crear_caso_uso(request):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        data = json.loads(request.body.decode('utf-8'))
        
        # Campos obligatorios según DB
        nombre = data.get('nombre')
        proyecto_id = data.get('proyecto_id')
        descripcion = data.get('descripcion', '')
        precondiciones = data.get('precondiciones', '')
        flujo_principal = data.get('flujo_principal', [])
        
        # Procesar actores (puede venir como string o lista) - OBLIGATORIO según DB
        actores = data.get('actores', '')
        if isinstance(actores, list):
            actores = ', '.join(actores)
        
        # Campos opcionales según DB
        prioridad_id = data.get('prioridad_id')
        flujos_alternativos = data.get('flujos_alternativos', [])
        postcondiciones = data.get('postcondiciones', '')
        requisitos_especiales = data.get('requisitos_especiales', '')
        riesgos_consideraciones = data.get('riesgos_consideraciones', '')
        
        # Mapear estado_id correctamente
        estado_id = data.get('estado_id') or data.get('estado')
        if estado_id:
            try:
                estado_id = int(estado_id)
            except (ValueError, TypeError):
                estado_id = 1  # Valor por defecto
        else:
            estado_id = 1  # Valor por defecto si no viene
        
        # Procesar relaciones
        relaciones = data.get('relaciones', [])

        # VALIDACIONES según restricciones de DB
        errores = []
        
        if not nombre or len(str(nombre).strip()) == 0:
            errores.append('El nombre es obligatorio')
        elif len(str(nombre).strip()) > 100:
            errores.append('El nombre no puede exceder 100 caracteres')
            
        if not proyecto_id:
            errores.append('El proyecto_id es obligatorio')
        elif not isinstance(proyecto_id, (int, str)) or str(proyecto_id).strip() == '':
            errores.append('El proyecto_id debe ser un número válido')
            
        if not actores or len(str(actores).strip()) == 0:
            errores.append('Los actores son obligatorios')
            
        if not precondiciones or len(str(precondiciones).strip()) == 0:
            errores.append('Las precondiciones son obligatorias')

        if errores:
            return JsonResponse({
                'error': 'Errores de validación',
                'detalles': errores
            }, status=400)

        # Validar que el proyecto existe
        try:
            proyecto = Proyectos.objects.get(id=proyecto_id, activo=True)
        except Proyectos.DoesNotExist:
            return JsonResponse({'error': 'El proyecto especificado no existe'}, status=400)

        # Validar estado si se proporciona
        if estado_id:
            try:
                EstadosElemento.objects.get(id=estado_id, tipo='caso_uso')
            except EstadosElemento.DoesNotExist:
                estado_id = 1

        # Validar prioridad si se proporciona
        if prioridad_id:
            try:
                Prioridades.objects.get(id=prioridad_id)
            except Prioridades.DoesNotExist:
                return JsonResponse({'error': 'La prioridad especificada no existe'}, status=400)

        with transaction.atomic():
            # Crear el caso de uso según estructura DB
            caso_uso = CasosUso.objects.create(
                nombre=str(nombre).strip(),
                descripcion=descripcion or '',
                actores=actores,
                precondiciones=precondiciones,
                flujo_principal=flujo_principal,
                flujos_alternativos=flujos_alternativos,
                postcondiciones=postcondiciones or '',
                requisitos_especiales=requisitos_especiales or '',
                riesgos_consideraciones=riesgos_consideraciones or '',
                proyecto_id=proyecto_id,
                prioridad_id=prioridad_id,  
                estado_id=estado_id,
                activo=True
            )

            # Guardar relaciones
            relaciones_creadas = []
            for rel in relaciones:
                caso_uso_destino_id = rel.get('casoUsoRelacionado')
                tipo_relacion_id = rel.get('tipo')
                descripcion_relacion = rel.get('descripcion', '')

                if caso_uso_destino_id and tipo_relacion_id:
                    try:
                        # Convertir a enteros
                        caso_uso_destino_id = int(caso_uso_destino_id)
                        tipo_relacion_id = int(tipo_relacion_id)
                                                
                        # No permitir autorrelaciones
                        if caso_uso_destino_id == caso_uso.id:
                            continue

                        # Crear la relación
                        relacion_creada = RelacionesCasosUso.objects.create(
                            caso_uso_origen_id=caso_uso.id,
                            caso_uso_destino_id=caso_uso_destino_id,
                            tipo_relacion_id=tipo_relacion_id,
                            descripcion=descripcion_relacion or ''
                        )
                        relaciones_creadas.append(relacion_creada.id)
                        
                    except (ValueError, CasosUso.DoesNotExist, TiposRelacionCu.DoesNotExist):
                        continue
                    except Exception:
                        continue

        response_data = {
            'mensaje': 'Caso de uso creado exitosamente',
            'caso_uso_id': caso_uso.id,
            'relaciones_creadas': len(relaciones_creadas)
        }
        
        return JsonResponse(response_data, status=201)

    except json.JSONDecodeError as e:
        return JsonResponse({'error': 'JSON inválido', 'detalle': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({
            'error': f'Error interno del servidor: {str(e)}',
            'tipo': type(e).__name__
        }, status=500)
     
# -----------------------------
# Obtener un caso de uso específico
# -----------------------------
@require_http_methods(["GET"])
def obtener_caso_uso(request, caso_uso_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        # Obtener el caso de uso
        caso_uso = get_object_or_404(CasosUso, id=caso_uso_id, activo=True)

        # Obtener las relaciones del caso de uso (usar campo correcto)
        relaciones = RelacionesCasosUso.objects.filter(
            caso_uso_origen_id=caso_uso.id
        ).select_related('tipo_relacion')

        relaciones_data = []
        for rel in relaciones:
            # Obtener caso de uso destino
            try:
                caso_destino = CasosUso.objects.get(id=rel.caso_uso_destino_id, activo=True)
                relaciones_data.append({
                    'id': rel.id,
                    'casoUsoRelacionado': rel.caso_uso_destino_id,
                    'tipo': str(rel.tipo_relacion_id),
                    'descripcion': rel.descripcion or ''
                })
            except CasosUso.DoesNotExist:
                # Skip relaciones con casos de uso eliminados
                continue

        data = {
            'id': caso_uso.id,
            'nombre': caso_uso.nombre,
            'descripcion': caso_uso.descripcion or '',
            'actores': caso_uso.actores,
            'precondiciones': caso_uso.precondiciones,
            'flujo_principal': caso_uso.flujo_principal or [],
            'flujos_alternativos': caso_uso.flujos_alternativos or [],
            'postcondiciones': caso_uso.postcondiciones or '',
            'requisitos_especiales': caso_uso.requisitos_especiales or '',
            'riesgos_consideraciones': caso_uso.riesgos_consideraciones or '',
            'estado': caso_uso.estado.nombre.lower().replace(' ', '-') if caso_uso.estado else None,
            'proyecto_id': caso_uso.proyecto_id,
            'prioridad': caso_uso.prioridad.nombre if caso_uso.prioridad else None,
            'fecha_creacion': caso_uso.fecha_creacion.isoformat() if caso_uso.fecha_creacion else None,
            'relaciones': relaciones_data
        }

        return JsonResponse(data, status=200)

    except Exception as e:
        return JsonResponse({'error': f'Error interno del servidor: {str(e)}'}, status=500)

# -----------------------------
# Actualizar caso de uso
# -----------------------------
@csrf_exempt
@require_http_methods(["PUT", "PATCH"])
def actualizar_caso_uso(request, caso_uso_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        data = json.loads(request.body.decode('utf-8'))
        
        # Obtener el caso de uso existente
        caso_uso = get_object_or_404(CasosUso, id=caso_uso_id, activo=True)

        # Actualizar campos si vienen en la petición
        if 'nombre' in data:
            if not data['nombre'] or len(data['nombre'].strip()) == 0:
                return JsonResponse({'error': 'El nombre es obligatorio'}, status=400)
            if len(data['nombre'].strip()) > 100:
                return JsonResponse({'error': 'El nombre no puede exceder 100 caracteres'}, status=400)
            caso_uso.nombre = data['nombre'].strip()

        if 'descripcion' in data:
            caso_uso.descripcion = data['descripcion'] or ''

        if 'actores' in data:
            actores = data['actores']
            if isinstance(actores, list):
                actores = ', '.join(actores)
            if not actores or len(actores.strip()) == 0:
                return JsonResponse({'error': 'Los actores son obligatorios'}, status=400)
            caso_uso.actores = actores

        if 'precondiciones' in data:
            if not data['precondiciones'] or len(data['precondiciones'].strip()) == 0:
                return JsonResponse({'error': 'Las precondiciones son obligatorias'}, status=400)
            caso_uso.precondiciones = data['precondiciones']

        if 'flujo_principal' in data:
            caso_uso.flujo_principal = data['flujo_principal'] or []

        if 'flujos_alternativos' in data:
            caso_uso.flujos_alternativos = data['flujos_alternativos'] or []

        if 'postcondiciones' in data:
            caso_uso.postcondiciones = data['postcondiciones'] or ''

        if 'requisitos_especiales' in data:
            caso_uso.requisitos_especiales = data['requisitos_especiales'] or ''

        if 'riesgos_consideraciones' in data:
            caso_uso.riesgos_consideraciones = data['riesgos_consideraciones'] or ''

        if 'prioridad_id' in data:
            if data['prioridad_id']:
                try:
                    Prioridades.objects.get(id=data['prioridad_id'])
                    caso_uso.prioridad_id = data['prioridad_id']
                except Prioridades.DoesNotExist:
                    return JsonResponse({'error': 'La prioridad especificada no existe'}, status=400)
            else:
                caso_uso.prioridad_id = None

        # Manejar estado_id correctamente
        estado_id = data.get('estado_id') or data.get('estado')
        if estado_id:
            try:
                estado_id = int(estado_id)
                EstadosElemento.objects.get(id=estado_id, tipo='caso_uso')
                caso_uso.estado_id = estado_id
            except (ValueError, TypeError):
                pass  # si no es válido, simplemente no lo actualiza
            except EstadosElemento.DoesNotExist:
                return JsonResponse({'error': 'El estado especificado no existe'}, status=400)

        with transaction.atomic():
            # Guardar los cambios del caso de uso
            caso_uso.save()

            # Actualizar relaciones si vienen en la petición
            if 'relaciones' in data:
                # Eliminar todas las relaciones existentes
                RelacionesCasosUso.objects.filter(caso_uso_origen_id=caso_uso.id).delete()

                # Crear las nuevas relaciones
                relaciones = data['relaciones']
                for rel in relaciones:
                    caso_uso_destino_id = rel.get('casoUsoRelacionado')
                    tipo_relacion_id = rel.get('tipo')
                    descripcion_relacion = rel.get('descripcion', '')

                    if caso_uso_destino_id and tipo_relacion_id:
                        try:
                            caso_uso_destino_id = int(caso_uso_destino_id)
                            tipo_relacion_id = int(tipo_relacion_id)
                            
                            # Validar que el caso de uso destino existe
                            CasosUso.objects.get(id=caso_uso_destino_id, activo=True)
                            
                            # Validar que el tipo de relación existe
                            TiposRelacionCu.objects.get(id=tipo_relacion_id, activo=True)

                            # No permitir autorrelaciones
                            if caso_uso_destino_id == caso_uso.id:
                                continue

                            RelacionesCasosUso.objects.create(
                                caso_uso_origen_id=caso_uso.id,
                                caso_uso_destino_id=caso_uso_destino_id,
                                tipo_relacion_id=tipo_relacion_id,
                                descripcion=descripcion_relacion or ''
                            )
                        except (ValueError, TypeError, CasosUso.DoesNotExist, TiposRelacionCu.DoesNotExist):
                            continue

        return JsonResponse({
            'mensaje': 'Caso de uso actualizado exitosamente',
            'caso_uso_id': caso_uso.id
        }, status=200)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Error interno del servidor: {str(e)}'}, status=500)

# -----------------------------
# Eliminar caso de uso (soft delete)
# -----------------------------
@csrf_exempt
@require_http_methods(["DELETE"])
def eliminar_caso_uso(request, caso_uso_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        caso_uso = get_object_or_404(CasosUso, id=caso_uso_id, activo=True)

        with transaction.atomic():
            # Soft delete del caso de uso
            caso_uso.activo = False
            caso_uso.save()

            # Eliminar todas las relaciones donde este caso de uso aparece
            RelacionesCasosUso.objects.filter(
                caso_uso_origen_id=caso_uso.id
            ).delete()
            
            RelacionesCasosUso.objects.filter(
                caso_uso_destino_id=caso_uso.id
            ).delete()

        return JsonResponse({
            'mensaje': 'Caso de uso eliminado exitosamente'
        }, status=200)

    except Exception as e:
        return JsonResponse({'error': f'Error interno del servidor: {str(e)}'}, status=500)

# -----------------------------
# Listar casos de uso de un proyecto
# -----------------------------
@require_http_methods(["GET"])
def listar_casos_uso(request, proyecto_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        # Validar que el proyecto existe
        try:
            Proyectos.objects.get(id=proyecto_id, activo=True)
        except Proyectos.DoesNotExist:
            return JsonResponse({'error': 'El proyecto especificado no existe'}, status=404)

        # Obtener casos de uso del proyecto
        casos_uso = CasosUso.objects.filter(
            proyecto_id=proyecto_id, 
         activo=True
        ).select_related('estado').prefetch_related('prioridad').order_by('-fecha_creacion')
        
        # Obtener todas las relaciones para incluir el conteo
        relaciones_por_caso = {}
        relaciones = RelacionesCasosUso.objects.filter(
            caso_uso_origen_id__in=[cu.id for cu in casos_uso]
        ).select_related('tipo_relacion')
        
        for rel in relaciones:
            caso_id = rel.caso_uso_origen_id
            if caso_id not in relaciones_por_caso:
                relaciones_por_caso[caso_id] = []
            
            # Obtener info del caso de uso destino
            try:
                caso_destino = CasosUso.objects.get(id=rel.caso_uso_destino_id, activo=True)
                relaciones_por_caso[caso_id].append({
                    'id': rel.id,
                    'tipo': rel.tipo_relacion.nombre if rel.tipo_relacion else '',
                    'descripcion': rel.descripcion or '',
                    'caso_destino': caso_destino.nombre
                })
            except CasosUso.DoesNotExist:
                continue

        data = []
        for cu in casos_uso:
            caso_relaciones = relaciones_por_caso.get(cu.id, [])
            
            data.append({
                'id': cu.id,
                'nombre': cu.nombre,
                'descripcion': cu.descripcion or '',
                'actores': cu.actores,
                'precondiciones': cu.precondiciones,
                'flujo_principal': cu.flujo_principal or [],
                'flujos_alternativos': cu.flujos_alternativos or [],
                'postcondiciones': cu.postcondiciones or '',
                'requisitos_especiales': cu.requisitos_especiales or '',
                'riesgos_consideraciones': cu.riesgos_consideraciones or '',
                'estado': cu.estado.nombre.lower().replace(' ', '-') if cu.estado else None,
                'proyecto_id': cu.proyecto_id,
                'prioridad': cu.prioridad.nombre if cu.prioridad else None,
                'fecha_creacion': cu.fecha_creacion.isoformat() if cu.fecha_creacion else None,
                'relaciones': caso_relaciones
            })

        return JsonResponse({'data': data}, status=200)

    except Exception as e:
        return JsonResponse({'error': f'Error interno del servidor: {str(e)}'}, status=500)

# -----------------------------
# Obtener relaciones de un caso de uso específico
# -----------------------------
@require_http_methods(["GET"])
def obtener_relaciones_caso_uso(request, caso_uso_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        # Validar que el caso de uso existe
        caso_uso = get_object_or_404(CasosUso, id=caso_uso_id, activo=True)

        # Obtener relaciones donde este caso de uso es el origen
        relaciones = RelacionesCasosUso.objects.filter(
            caso_uso_origen_id=caso_uso.id
        ).select_related('tipo_relacion')

        data = []
        for rel in relaciones:
            # Verificar que el caso de uso destino existe
            try:
                caso_destino = CasosUso.objects.get(id=rel.caso_uso_destino_id, activo=True)
                data.append({
                    'id': rel.id,
                    'casoUsoRelacionado': rel.caso_uso_destino_id,
                    'tipo': str(rel.tipo_relacion_id),
                    'descripcion': rel.descripcion or ''
                })
            except CasosUso.DoesNotExist:
                continue

        return JsonResponse({'relaciones': data}, status=200)

    except Exception as e:
        return JsonResponse({'error': f'Error interno del servidor: {str(e)}'}, status=500)