"""
github_integration/views.py
Endpoints para guardar, recuperar y eliminar la conexión GitHub del usuario.
Reutiliza la función validar_token() de la app usuarios.
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

from usuarios.views import validar_token       # reutiliza tu validador JWT existente
from .models import GitHubConexion


# ─────────────────────────────────────────────────────────────────────────────
# GUARDAR O ACTUALIZAR conexión GitHub
# POST /app/github/conexion/guardar/
# Body JSON: { token, github_usuario, github_avatar }
# ─────────────────────────────────────────────────────────────────────────────
@csrf_exempt
@require_http_methods(["POST"])
def guardar_conexion(request):
    payload = validar_token(request)
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    if 'error' in payload:
        return JsonResponse(payload, status=401)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)

    token_github   = data.get('token', '').strip()
    github_usuario = data.get('github_usuario', '').strip()
    github_avatar  = data.get('github_avatar', '').strip()

    if not token_github or not github_usuario:
        return JsonResponse({'error': 'token y github_usuario son requeridos'}, status=400)

    usuario_id = payload['usuario_id']

    # Upsert: actualizar si ya existe, crear si no
    conexion, creada = GitHubConexion.objects.get_or_create(
        usuario_id=usuario_id,
        defaults={'github_usuario': github_usuario, 'github_avatar': github_avatar}
    )

    # Siempre actualizar el token (puede haber rotado) y metadatos
    conexion.set_token(token_github)
    conexion.github_usuario = github_usuario
    conexion.github_avatar  = github_avatar
    conexion.activo = True
    conexion.save()

    return JsonResponse({
        'mensaje': 'Conexión GitHub guardada exitosamente',
        'github_usuario': conexion.github_usuario,
        'github_avatar':  conexion.github_avatar,
        'creada': creada,
    }, status=200)


# ─────────────────────────────────────────────────────────────────────────────
# OBTENER conexión activa del usuario
# GET /app/github/conexion/obtener/
# Retorna los metadatos + el token desencriptado (solo para el propio usuario)
# ─────────────────────────────────────────────────────────────────────────────
@require_http_methods(["GET"])
def obtener_conexion(request):
    payload = validar_token(request)
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    if 'error' in payload:
        return JsonResponse(payload, status=401)

    try:
        conexion = GitHubConexion.objects.get(
            usuario_id=payload['usuario_id'],
            activo=True
        )
    except GitHubConexion.DoesNotExist:
        # 404 sin mensaje de error alarmante — el frontend lo trata como "sin conexión"
        return JsonResponse({'conexion': None}, status=200)

    try:
        token_plano = conexion.get_token()
    except Exception:
        # Si la clave Fernet cambió o el token está corrupto, retornar sin conexión
        return JsonResponse({'conexion': None}, status=200)

    return JsonResponse({
        'conexion': {
            'token':          token_plano,
            'github_usuario': conexion.github_usuario,
            'github_avatar':  conexion.github_avatar,
            'fecha_guardado': conexion.fecha_actualizacion.isoformat(),
        }
    }, status=200)


# ─────────────────────────────────────────────────────────────────────────────
# ELIMINAR conexión GitHub (soft delete)
# DELETE /app/github/conexion/eliminar/
# ─────────────────────────────────────────────────────────────────────────────
@csrf_exempt
@require_http_methods(["DELETE"])
def eliminar_conexion(request):
    payload = validar_token(request)
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    if 'error' in payload:
        return JsonResponse(payload, status=401)

    try:
        conexion = GitHubConexion.objects.get(
            usuario_id=payload['usuario_id'],
            activo=True
        )
        conexion.activo = False
        conexion.save()
        return JsonResponse({'mensaje': 'Conexión GitHub eliminada'}, status=200)
    except GitHubConexion.DoesNotExist:
        return JsonResponse({'mensaje': 'No había conexión activa'}, status=200)