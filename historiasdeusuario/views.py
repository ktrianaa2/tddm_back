# historias/views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.shortcuts import get_object_or_404
from historiasdeusuario.models import (
    HistoriasUsuario, 
    EstadosElemento, 
    Prioridades, 
    TiposEstimacion, 
    HistoriasEstimaciones
)
from proyectos.models import Proyectos
from usuarios.views import validar_token
import json
from decimal import Decimal, InvalidOperation

# -----------------------------
# Crear historia de usuario
# -----------------------------
@csrf_exempt
@require_http_methods(["POST"])
def crear_historia_usuario(request):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        data = json.loads(request.body.decode('utf-8'))
        
        # Campos obligatorios
        titulo = data.get('titulo')
        proyecto_id = data.get('proyecto_id')
        criterios_aceptacion = data.get('criterios_aceptacion')
        
        # Campos opcionales
        descripcion = data.get('descripcion', '')
        actor_rol = data.get('actor_rol', '')
        funcionalidad_accion = data.get('funcionalidad_accion', '')
        beneficio_razon = data.get('beneficio_razon', '')
        dependencias_relaciones = data.get('dependencias_relaciones', '')
        componentes_relacionados = data.get('componentes_relacionados', '')
        notas_adicionales = data.get('notas_adicionales', '')
        prioridad_id = data.get('prioridad_id')
        estado_id = data.get('estado_id', 1)  # Por defecto estado pendiente
        valor_negocio = data.get('valor_negocio')
        estimaciones = data.get('estimaciones', [])

        # Validaciones básicas
        if not (titulo and proyecto_id and criterios_aceptacion):
            return JsonResponse({'error': 'Campos obligatorios faltantes'}, status=400)

        # Validar que el proyecto existe
        try:
            proyecto = Proyectos.objects.get(id=proyecto_id, activo=True)
        except Proyectos.DoesNotExist:
            return JsonResponse({'error': 'El proyecto especificado no existe'}, status=400)

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

        # Validar valor_negocio
        if valor_negocio is not None:
            try:
                valor_negocio = int(valor_negocio)
                if valor_negocio < 1 or valor_negocio > 100:
                    return JsonResponse({'error': 'El valor de negocio debe estar entre 1 y 100'}, status=400)
            except (ValueError, TypeError):
                return JsonResponse({'error': 'El valor de negocio debe ser un número entero'}, status=400)

        with transaction.atomic():
            # Crear la historia de usuario
            historia = HistoriasUsuario.objects.create(
                titulo=titulo,
                descripcion=descripcion,
                actor_rol=actor_rol,
                funcionalidad_accion=funcionalidad_accion,
                beneficio_razon=beneficio_razon,
                criterios_aceptacion=criterios_aceptacion,
                prioridad_id=prioridad_id,
                estado_id=estado_id,
                valor_negocio=valor_negocio,
                dependencias_relaciones=dependencias_relaciones,
                componentes_relacionados=componentes_relacionados,
                notas_adicionales=notas_adicionales,
                proyecto_id=proyecto_id,
                activo=True
            )

            # CORRECCIÓN: Procesar estimaciones correctamente
            estimaciones_creadas = []
            if estimaciones and isinstance(estimaciones, list):
                print(f"Procesando {len(estimaciones)} estimaciones")
                
                for i, est in enumerate(estimaciones):
                    tipo_estimacion_id = est.get('tipo_estimacion_id')
                    valor = est.get('valor')

                    print(f"Estimación {i}: tipo_id={tipo_estimacion_id}, valor={valor}")

                    if tipo_estimacion_id and valor is not None:
                        try:
                            # Validar que el tipo de estimación existe
                            tipo_estimacion = TiposEstimacion.objects.get(id=tipo_estimacion_id, activo=True)
                            
                            # Convertir y validar valor
                            valor_decimal = Decimal(str(valor))
                            if valor_decimal <= 0:
                                print(f"Valor inválido para estimación {i}: {valor}")
                                continue
                                
                            # Crear la estimación
                            estimacion_obj = HistoriasEstimaciones.objects.create(
                                historia=historia,
                                tipo_estimacion=tipo_estimacion,
                                valor=valor_decimal,
                                activo=True
                            )
                            
                            estimaciones_creadas.append({
                                'id': estimacion_obj.id,
                                'tipo_estimacion_id': tipo_estimacion.id,
                                'tipo_estimacion_nombre': tipo_estimacion.nombre,
                                'valor': float(valor_decimal)
                            })
                            
                            print(f"Estimación creada exitosamente: {estimacion_obj.id}")
                            
                        except TiposEstimacion.DoesNotExist:
                            print(f"Tipo de estimación {tipo_estimacion_id} no existe o está inactivo")
                            continue
                        except (InvalidOperation, ValueError) as e:
                            print(f"Error al convertir valor de estimación: {e}")
                            continue
                        except Exception as e:
                            print(f"Error inesperado al crear estimación: {e}")
                            continue

        print(f"Historia creada con ID: {historia.id}")
        print(f"Estimaciones creadas: {len(estimaciones_creadas)}")

        return JsonResponse({
            'mensaje': 'Historia de usuario creada exitosamente',
            'historia_id': historia.id,
            'estimaciones_creadas': estimaciones_creadas
        }, status=201)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except Exception as e:
        print(f"Error en crear_historia_usuario: {str(e)}")
        return JsonResponse({'error': f'Error interno del servidor: {str(e)}'}, status=500)

# -----------------------------
# Obtener una historia de usuario específica
# -----------------------------
@require_http_methods(["GET"])
def obtener_historia_usuario(request, historia_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        # Obtener la historia de usuario
        historia = get_object_or_404(HistoriasUsuario, id=historia_id, activo=True)

        def safe_key_conversion(value):
            if not value:
                return None
            return value.lower().replace(' ', '-').replace('ó', 'o').replace('í', 'i')

        # CORRECCIÓN: Obtener estimaciones con información completa
        estimaciones = HistoriasEstimaciones.objects.filter(
            historia=historia,
            activo=True
        ).select_related('tipo_estimacion')

        estimaciones_data = []
        for est in estimaciones:
            estimaciones_data.append({
                'id': est.id,
                'tipo_estimacion_id': est.tipo_estimacion.id,
                'tipo_estimacion_nombre': est.tipo_estimacion.nombre,
                'valor': float(est.valor)
            })

        data = {
            'id': historia.id,
            'titulo': historia.titulo,
            'descripcion': historia.descripcion,
            'actor_rol': historia.actor_rol,
            'funcionalidad_accion': historia.funcionalidad_accion,
            'beneficio_razon': historia.beneficio_razon,
            'criterios_aceptacion': historia.criterios_aceptacion,
            'prioridad': safe_key_conversion(historia.prioridad.nombre) if historia.prioridad else None,
            'estado': safe_key_conversion(historia.estado.nombre) if historia.estado else None,
            'valor_negocio': historia.valor_negocio,
            'dependencias_relaciones': historia.dependencias_relaciones,
            'componentes_relacionados': historia.componentes_relacionados,
            'notas_adicionales': historia.notas_adicionales,
            'proyecto_id': historia.proyecto_id,
            'fecha_creacion': historia.fecha_creacion.isoformat() if historia.fecha_creacion else None,
            'estimaciones': estimaciones_data,
            # MANTENER COMPATIBILIDAD: Para historias con una sola estimación
            'estimacion_valor': estimaciones_data[0]['valor'] if len(estimaciones_data) == 1 else None,
            'unidad_estimacion': estimaciones_data[0]['tipo_estimacion_nombre'] if len(estimaciones_data) == 1 else None
        }

        print(f"Historia obtenida: ID={historia.id}, Estimaciones={len(estimaciones_data)}")
        for est in estimaciones_data:
            print(f"  - Estimación: {est['tipo_estimacion_nombre']} = {est['valor']}")

        return JsonResponse({'historia': data}, status=200)

    except Exception as e:
        print(f"Error en obtener_historia_usuario: {str(e)}")
        return JsonResponse({'error': f'Error interno del servidor: {str(e)}'}, status=500)

# -----------------------------
# Actualizar historia de usuario
# -----------------------------
@csrf_exempt
@require_http_methods(["PUT", "PATCH"])
def actualizar_historia_usuario(request, historia_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        data = json.loads(request.body.decode('utf-8'))
        
        # Obtener la historia existente
        historia = get_object_or_404(HistoriasUsuario, id=historia_id, activo=True)

        # Campos que se pueden actualizar
        if 'titulo' in data:
            if not data['titulo'] or len(data['titulo']) < 5:
                return JsonResponse({'error': 'El título debe tener al menos 5 caracteres'}, status=400)
            historia.titulo = data['titulo']

        if 'descripcion' in data:
            historia.descripcion = data['descripcion'] or ''

        if 'actor_rol' in data:
            historia.actor_rol = data['actor_rol'] or ''

        if 'funcionalidad_accion' in data:
            historia.funcionalidad_accion = data['funcionalidad_accion'] or ''

        if 'beneficio_razon' in data:
            historia.beneficio_razon = data['beneficio_razon'] or ''

        if 'criterios_aceptacion' in data:
            if not data['criterios_aceptacion'] or len(data['criterios_aceptacion']) < 10:
                return JsonResponse({'error': 'Los criterios de aceptación deben tener al menos 10 caracteres'}, status=400)
            historia.criterios_aceptacion = data['criterios_aceptacion']

        if 'dependencias_relaciones' in data:
            historia.dependencias_relaciones = data['dependencias_relaciones'] or ''

        if 'componentes_relacionados' in data:
            historia.componentes_relacionados = data['componentes_relacionados'] or ''

        if 'notas_adicionales' in data:
            historia.notas_adicionales = data['notas_adicionales'] or ''

        if 'prioridad_id' in data:
            if data['prioridad_id']:
                try:
                    Prioridades.objects.get(id=data['prioridad_id'])
                    historia.prioridad_id = data['prioridad_id']
                except Prioridades.DoesNotExist:
                    return JsonResponse({'error': 'La prioridad especificada no existe'}, status=400)
            else:
                historia.prioridad_id = None

        if 'estado_id' in data and data['estado_id']:
            try:
                EstadosElemento.objects.get(id=data['estado_id'])
                historia.estado_id = data['estado_id']
            except EstadosElemento.DoesNotExist:
                return JsonResponse({'error': 'El estado especificado no existe'}, status=400)

        if 'valor_negocio' in data:
            valor_negocio = data['valor_negocio']
            if valor_negocio is not None:
                try:
                    valor_negocio = int(valor_negocio)
                    if valor_negocio < 1 or valor_negocio > 100:
                        return JsonResponse({'error': 'El valor de negocio debe estar entre 1 y 100'}, status=400)
                    historia.valor_negocio = valor_negocio
                except (ValueError, TypeError):
                    return JsonResponse({'error': 'El valor de negocio debe ser un número entero'}, status=400)
            else:
                historia.valor_negocio = None

        with transaction.atomic():
            # Guardar los cambios de la historia
            historia.save()
            
            # CORRECCIÓN: Actualizar estimaciones correctamente
            estimaciones_actualizadas = 0
            
            if 'estimaciones' in data:
                estimaciones = data['estimaciones']
                print(f"Actualizando estimaciones: recibidas {len(estimaciones) if estimaciones else 0}")
                
                # Marcar todas las estimaciones existentes como inactivas
                estimaciones_previas = HistoriasEstimaciones.objects.filter(historia=historia, activo=True).count()
                HistoriasEstimaciones.objects.filter(historia=historia).update(activo=False)
                print(f"Marcadas como inactivas: {estimaciones_previas} estimaciones previas")

                # Procesar las nuevas estimaciones
                if estimaciones and isinstance(estimaciones, list):
                    for i, est in enumerate(estimaciones):
                        tipo_estimacion_id = est.get('tipo_estimacion_id')
                        valor = est.get('valor')

                        print(f"Procesando estimación {i}: tipo_id={tipo_estimacion_id}, valor={valor}")

                        if tipo_estimacion_id and valor is not None:
                            try:
                                # Validar que el tipo de estimación existe
                                tipo_estimacion = TiposEstimacion.objects.get(id=tipo_estimacion_id, activo=True)
                                
                                # Convertir y validar valor
                                valor_decimal = Decimal(str(valor))
                                if valor_decimal <= 0:
                                    print(f"Valor inválido: {valor}")
                                    continue

                                # Buscar si ya existe una estimación para este tipo
                                estimacion_existente = HistoriasEstimaciones.objects.filter(
                                    historia=historia,
                                    tipo_estimacion=tipo_estimacion
                                ).first()

                                if estimacion_existente:
                                    # Actualizar la existente
                                    estimacion_existente.valor = valor_decimal
                                    estimacion_existente.activo = True
                                    estimacion_existente.save()
                                    print(f"Estimación actualizada: ID={estimacion_existente.id}")
                                else:
                                    # Crear nueva
                                    estimacion_existente = HistoriasEstimaciones.objects.create(
                                        historia=historia,
                                        tipo_estimacion=tipo_estimacion,
                                        valor=valor_decimal,
                                        activo=True
                                    )
                                    print(f"Nueva estimación creada: ID={estimacion_existente.id}")

                                estimaciones_actualizadas += 1

                            except TiposEstimacion.DoesNotExist:
                                print(f"Tipo de estimación {tipo_estimacion_id} no existe")
                                continue
                            except (InvalidOperation, ValueError) as e:
                                print(f"Error al procesar estimación: {e}")
                                continue
                            except Exception as e:
                                print(f"Error inesperado al procesar estimación: {e}")
                                continue

        print(f"Historia actualizada: ID={historia.id}, Estimaciones actualizadas: {estimaciones_actualizadas}")

        return JsonResponse({
            'mensaje': 'Historia de usuario actualizada exitosamente',
            'historia_id': historia.id,
            'estimaciones_actualizadas': estimaciones_actualizadas
        }, status=200)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except Exception as e:
        print(f"Error en actualizar_historia_usuario: {str(e)}")
        return JsonResponse({'error': f'Error interno del servidor: {str(e)}'}, status=500)

# -----------------------------
# Eliminar historia de usuario (soft delete)
# -----------------------------
@csrf_exempt
@require_http_methods(["DELETE"])
def eliminar_historia_usuario(request, historia_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        historia = get_object_or_404(HistoriasUsuario, id=historia_id, activo=True)

        with transaction.atomic():
            # Soft delete de la historia
            historia.activo = False
            historia.save()

            # Eliminar todas las estimaciones relacionadas (hard delete)
            HistoriasEstimaciones.objects.filter(historia=historia).delete()

        return JsonResponse({
            'mensaje': 'Historia de usuario eliminada exitosamente'
        }, status=200)

    except Exception as e:
        return JsonResponse({'error': f'Error interno del servidor: {str(e)}'}, status=500)

# -----------------------------
# Listar historias de usuario de un proyecto
# -----------------------------
@require_http_methods(["GET"])
def listar_historias_usuario(request, proyecto_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        # Validar que el proyecto existe
        try:
            Proyectos.objects.get(id=proyecto_id, activo=True)
        except Proyectos.DoesNotExist:
            return JsonResponse({'error': 'El proyecto especificado no existe'}, status=404)

        # Obtener historias de usuario del proyecto
        historias = HistoriasUsuario.objects.filter(
            proyecto_id=proyecto_id, 
            activo=True
        ).select_related('prioridad', 'estado').order_by('-fecha_creacion')

        data = []
        for h in historias:
            def safe_key_conversion(value):
                if not value:
                    return None
                return value.lower().replace(' ', '-').replace('ó', 'o').replace('í', 'i')

            # CORRECCIÓN: Obtener estimaciones para la lista
            estimaciones = HistoriasEstimaciones.objects.filter(
                historia=h,
                activo=True
            ).select_related('tipo_estimacion')

            estimaciones_data = []
            for est in estimaciones:
                estimaciones_data.append({
                    'id': est.id,
                    'tipo_estimacion_id': est.tipo_estimacion.id,
                    'tipo_estimacion_nombre': est.tipo_estimacion.nombre,
                    'valor': float(est.valor)
                })

            historia_data = {
                'id': h.id,
                'titulo': h.titulo,
                'descripcion': h.descripcion,
                'actor_rol': h.actor_rol,
                'funcionalidad_accion': h.funcionalidad_accion,
                'beneficio_razon': h.beneficio_razon,
                'criterios_aceptacion': h.criterios_aceptacion,
                'prioridad': safe_key_conversion(h.prioridad.nombre) if h.prioridad else None,
                'estado': safe_key_conversion(h.estado.nombre) if h.estado else None,
                'valor_negocio': h.valor_negocio,
                'dependencias_relaciones': h.dependencias_relaciones,
                'componentes_relacionados': h.componentes_relacionados,
                'notas_adicionales': h.notas_adicionales,
                'proyecto_id': h.proyecto_id,
                'fecha_creacion': h.fecha_creacion.isoformat() if h.fecha_creacion else None,
                'estimaciones': estimaciones_data,
                # MANTENER COMPATIBILIDAD: Para historias con una sola estimación
                'estimacion_valor': estimaciones_data[0]['valor'] if len(estimaciones_data) == 1 else None,
                'unidad_estimacion': estimaciones_data[0]['tipo_estimacion_nombre'] if len(estimaciones_data) == 1 else None
            }
            
            data.append(historia_data)

        return JsonResponse({'historias': data}, status=200)

    except Exception as e:
        return JsonResponse({'error': f'Error interno del servidor: {str(e)}'}, status=500)

# -----------------------------
# Obtener estimaciones de una historia específica
# -----------------------------
@require_http_methods(["GET"])
def obtener_estimaciones_historia(request, historia_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        # Validar que la historia existe
        historia = get_object_or_404(HistoriasUsuario, id=historia_id, activo=True)

        # Obtener estimaciones de la historia
        estimaciones = HistoriasEstimaciones.objects.filter(
            historia=historia,
            activo=True
        ).select_related('tipo_estimacion')

        data = []
        for est in estimaciones:
            data.append({
                'id': est.id,
                'tipo_estimacion_id': est.tipo_estimacion.id,
                'tipo_estimacion_nombre': est.tipo_estimacion.nombre,
                'valor': float(est.valor)
            })

        return JsonResponse({'estimaciones': data}, status=200)

    except Exception as e:
        return JsonResponse({'error': f'Error interno del servidor: {str(e)}'}, status=500)