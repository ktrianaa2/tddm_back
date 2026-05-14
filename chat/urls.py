from django.urls import path
from . import views

urlpatterns = [
    # Pruebas Unitarias
    path('generar-pruebas/unitaria/<int:proyecto_id>/', views.generar_pruebas_unitarias, name='generar_pruebas_unitarias'),
    path('previsualizar-pruebas/unitaria/<int:proyecto_id>/', views.previsualizar_pruebas, name='previsualizar_pruebas'),

    # Pruebas de Componente
    path('generar-pruebas/componente/<int:proyecto_id>/', views.generar_pruebas_componente, name='generar_pruebas_componente'),
    path('previsualizar-pruebas/componente/<int:proyecto_id>/', views.previsualizar_pruebas_componente, name='previsualizar_pruebas_componente'),

    # Pruebas de Sistema
    path('generar-pruebas/sistema/<int:proyecto_id>/', views.generar_pruebas_sistema, name='generar_pruebas_sistema'),
    path('previsualizar-pruebas/sistema/<int:proyecto_id>/', views.previsualizar_pruebas_sistema, name='previsualizar_pruebas_sistema'),

    # Generación múltiple (todos los tipos)
    path('generar-pruebas/multiple/<int:proyecto_id>/', views.generar_pruebas_multiple, name='generar_pruebas_multiple'),

    # Esquema BD
    path('generar-esquema-bd/<int:proyecto_id>/', views.generar_esquema_bd, name='generar_esquema_bd'),
    path('previsualizar-esquema-bd/<int:proyecto_id>/', views.previsualizar_esquema_bd, name='previsualizar_esquema_bd'),

    path('generar-resumenes-documentacion/<int:proyecto_id>/', views.generar_resumenes_documentacion, name='generar_resumenes_documentacion'),
]