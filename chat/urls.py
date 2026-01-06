from django.urls import path
from . import views

urlpatterns = [
    path('generar-pruebas/<int:proyecto_id>/', views.generar_pruebas_unitarias, name='generar_pruebas_unitarias'),
    path('previsualizar-pruebas/<int:proyecto_id>/', views.previsualizar_pruebas, name='previsualizar_pruebas'),
    path('generar-esquema-bd/<int:proyecto_id>/', views.generar_esquema_bd, name='generar_esquema_bd'),
    path('previsualizar-esquema-bd/<int:proyecto_id>/', views.previsualizar_esquema_bd, name='previsualizar_esquema_bd'),
]