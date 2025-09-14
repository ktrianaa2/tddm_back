# casosdeuso/urls.py
from django.urls import path
from casosdeuso import views

urlpatterns = [
    # CRUD básico de casos de uso
    path('crear/', views.crear_caso_uso, name='crear_caso_uso'),
    path('listar/<int:proyecto_id>/', views.listar_casos_uso, name='listar_casos_uso'),
    path('obtener/<int:caso_uso_id>/', views.obtener_caso_uso, name='obtener_caso_uso'),
    path('actualizar/<int:caso_uso_id>/', views.actualizar_caso_uso, name='actualizar_caso_uso'),
    path('eliminar/<int:caso_uso_id>/', views.eliminar_caso_uso, name='eliminar_caso_uso'),
    
    # Relaciones entre casos de uso
    path('relaciones/<int:caso_uso_id>/', views.obtener_relaciones_caso_uso, name='obtener_relaciones_caso_uso'),
]