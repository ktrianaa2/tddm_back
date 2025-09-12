# requisitos/urls.py
from django.urls import path
from requisitos import views

urlpatterns = [
    # CRUD básico de requisitos
    path('crear/', views.crear_requisito, name='crear_requisito'),
    path('listar/<int:proyecto_id>/', views.listar_requisitos, name='listar_requisitos'),
    path('obtener/<int:requisito_id>/', views.obtener_requisito, name='obtener_requisito'),
    path('actualizar/<int:requisito_id>/', views.actualizar_requisito, name='actualizar_requisito'),
    path('eliminar/<int:requisito_id>/', views.eliminar_requisito, name='eliminar_requisito'),
    
    # Relaciones entre requisitos
    path('relaciones/<int:requisito_id>/', views.obtener_relaciones_requisito, name='obtener_relaciones_requisito'),
    
    # Catálogos
    path('catalogos/', views.obtener_catalogos_requisitos, name='catalogos_requisitos'),
]