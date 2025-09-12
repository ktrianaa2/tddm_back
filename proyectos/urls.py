from django.urls import path
from proyectos import views

urlpatterns = [
    path('listar/', views.listar_proyectos, name='listar_proyectos'),
    path('crear/', views.crear_proyecto, name='crear_proyecto'),
    path('editar/<int:proyecto_id>/', views.editar_proyecto, name='editar_proyecto'),
    path('obtener_proyecto/<int:proyecto_id>/', views.obtener_proyecto, name='obtener_proyecto'),
    path('eliminar/<int:proyecto_id>/', views.eliminar_proyecto, name='eliminar_proyecto'),
]