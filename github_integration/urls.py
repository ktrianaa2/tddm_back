"""
github_integration/urls.py

Agregar en tu urls.py principal:
    path('app/github/', include('github_integration.urls')),
"""

from django.urls import path
from . import views

urlpatterns = [
    path('conexion/guardar/',   views.guardar_conexion,  name='github_guardar_conexion'),
    path('conexion/obtener/',   views.obtener_conexion,  name='github_obtener_conexion'),
    path('conexion/eliminar/',  views.eliminar_conexion, name='github_eliminar_conexion'),
]