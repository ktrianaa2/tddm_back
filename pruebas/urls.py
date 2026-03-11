from django.urls import path
from pruebas import views

urlpatterns = [
    # TIPOS DE PRUEBA
    path('tipos-prueba/listar/', views.listar_tipos_prueba, name='listar_tipos_prueba'),
    path('tipos-prueba/crear/', views.crear_tipo_prueba, name='crear_tipo_prueba'),
    path('tipos-prueba/obtener/<int:tipo_prueba_id>/', views.obtener_tipo_prueba, name='obtener_tipo_prueba'),
    path('tipos-prueba/editar/<int:tipo_prueba_id>/', views.editar_tipo_prueba, name='editar_tipo_prueba'),
    path('tipos-prueba/eliminar/<int:tipo_prueba_id>/', views.eliminar_tipo_prueba, name='eliminar_tipo_prueba'),
    
    # PRUEBAS
    path('listar/<int:proyecto_id>/', views.listar_pruebas, name='listar_pruebas'),
    path('crear/', views.crear_prueba, name='crear_prueba'),
    path('obtener/<int:prueba_id>/', views.obtener_prueba, name='obtener_prueba'),
    path('editar/<int:prueba_id>/', views.editar_prueba, name='editar_prueba'),
    path('eliminar/<int:prueba_id>/', views.eliminar_prueba, name='eliminar_prueba'),
    path('aprobar/<int:prueba_id>/', views.aprobar_prueba, name='aprobar_prueba'),
]