from django.urls import path
from . import views

urlpatterns = [
    path('generar-pruebas/<int:proyecto_id>/', views.generar_pruebas_unitarias, name='generar_pruebas_unitarias'),
    path('previsualizar-pruebas/<int:proyecto_id>/', views.previsualizar_pruebas, name='previsualizar_pruebas'),
]