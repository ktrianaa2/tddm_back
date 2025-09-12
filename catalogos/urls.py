from django.urls import path
from catalogos import views

urlpatterns = [
    path('listar/', views.listar_tipos_requisito, name='listar_tipos_requisito'),
    path('crear/', views.crear_tipo_requisito, name='crear_tipo_requisito'),
    path('editar/<int:tipo_id>/', views.editar_tipo_requisito, name='editar_tipo_requisito'),
    path('obtener/<int:tipo_id>/', views.obtener_tipo_requisito, name='obtener_tipo_requisito'),
    path('deshabilitar/<int:tipo_id>/', views.deshabilitar_tipo_requisito, name='deshabilitar_tipo_requisito'),
]

# URLs de Prioridades
urlpatterns += [
    path('prioridades/listar/', views.listar_prioridades, name='listar_prioridades'),
    path('prioridades/crear/', views.crear_prioridad, name='crear_prioridad'),
    path('prioridades/editar/<int:prioridad_id>/', views.editar_prioridad, name='editar_prioridad'),
    path('prioridades/obtener/<int:prioridad_id>/', views.obtener_prioridad, name='obtener_prioridad'),
    path('prioridades/deshabilitar/<int:prioridad_id>/', views.deshabilitar_prioridad, name='deshabilitar_prioridad'),
]

# URLs de Estados de Proyecto
urlpatterns += [
    path('estados/listar/', views.listar_estados_proyecto, name='listar_estados_proyecto'),
    path('estados/crear/', views.crear_estado_proyecto, name='crear_estado_proyecto'),
    path('estados/editar/<int:estado_id>/', views.editar_estado_proyecto, name='editar_estado_proyecto'),
    path('estados/obtener/<int:estado_id>/', views.obtener_estado_proyecto, name='obtener_estado_proyecto'),
    path('estados/deshabilitar/<int:estado_id>/', views.deshabilitar_estado_proyecto, name='deshabilitar_estado_proyecto'),
]


# EstadosElemento
urlpatterns += [
    path('estados_elemento/listar/', views.listar_estados_elemento, name='listar_estados_elemento'),
    path('estados_elemento/crear/', views.crear_estado_elemento, name='crear_estado_elemento'),
    path('estados_elemento/editar/<int:estado_id>/', views.editar_estado_elemento, name='editar_estado_elemento'),
    path('estados_elemento/obtener/<int:estado_id>/', views.obtener_estado_elemento, name='obtener_estado_elemento'),
    path('estados_elemento/deshabilitar/<int:estado_id>/', views.deshabilitar_estado_elemento, name='deshabilitar_estado_elemento'),
]

# TiposRelacionCu
urlpatterns += [
    path('tipos_relacion_cu/listar/', views.listar_tipos_relacion_cu, name='listar_tipos_relacion_cu'),
    path('tipos_relacion_cu/crear/', views.crear_tipo_relacion_cu, name='crear_tipo_relacion_cu'),
    path('tipos_relacion_cu/editar/<int:tr_id>/', views.editar_tipo_relacion_cu, name='editar_tipo_relacion_cu'),
    path('tipos_relacion_cu/deshabilitar/<int:tr_id>/', views.deshabilitar_tipo_relacion_cu, name='deshabilitar_tipo_relacion_cu'),
]

# TiposRelacionRequisito
urlpatterns += [
    path('tipos_relacion_requisito/listar/', views.listar_tipos_relacion_requisito, name='listar_tipos_relacion_requisito'),
    path('tipos_relacion_requisito/crear/', views.crear_tipo_relacion_requisito, name='crear_tipo_relacion_requisito'),
    path('tipos_relacion_requisito/editar/<int:tr_id>/', views.editar_tipo_relacion_requisito, name='editar_tipo_relacion_requisito'),
    path('tipos_relacion_requisito/deshabilitar/<int:tr_id>/', views.deshabilitar_tipo_relacion_requisito, name='deshabilitar_tipo_relacion_requisito'),
]

