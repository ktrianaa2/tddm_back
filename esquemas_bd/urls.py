# esquemas_bd/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Listar motores de BD disponibles
    path('motores/', views.listar_motores_bd, name='listar_motores'),
    
    # CRUD de Esquemas
    path('crear/', views.crear_esquema, name='crear_esquema'),
    path('obtener/<int:esquema_id>/', views.obtener_esquema, name='obtener_esquema'),
    path('actualizar/<int:esquema_id>/', views.actualizar_esquema, name='actualizar_esquema'),
    path('eliminar/<int:esquema_id>/', views.eliminar_esquema, name='eliminar_esquema'),
    
    # Operaciones especiales
    path('duplicar/<int:esquema_id>/', views.duplicar_esquema, name='duplicar_esquema'),
    path('proyecto/<int:proyecto_id>/', views.listar_esquemas_proyecto, name='listar_esquemas_proyecto'),
]