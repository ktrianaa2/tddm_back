# historias/urls.py
from django.urls import path
from historiasdeusuario import views

urlpatterns = [
    # CRUD básico de historias de usuario
    path('crear/', views.crear_historia_usuario, name='crear_historia_usuario'),
    path('listar/<int:proyecto_id>/', views.listar_historias_usuario, name='listar_historias_usuario'),
    path('obtener/<int:historia_id>/', views.obtener_historia_usuario, name='obtener_historia_usuario'),
    path('actualizar/<int:historia_id>/', views.actualizar_historia_usuario, name='actualizar_historia_usuario'),
    path('eliminar/<int:historia_id>/', views.eliminar_historia_usuario, name='eliminar_historia_usuario'),
]