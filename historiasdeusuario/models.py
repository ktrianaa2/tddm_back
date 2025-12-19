# historias/models.py
from django.db import models
from proyectos.models import Proyectos
from catalogos.models import EstadosElemento, Prioridades, TiposEstimacion
from django.utils import timezone

class HistoriasUsuario(models.Model):
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    actor_rol = models.CharField(max_length=100, blank=True, null=True)
    funcionalidad_accion = models.CharField(max_length=200, blank=True, null=True)
    beneficio_razon = models.CharField(max_length=200, blank=True, null=True)
    criterios_aceptacion = models.TextField()
    prioridad = models.ForeignKey(Prioridades, models.DO_NOTHING, db_column='prioridad_id', blank=True, null=True)
    estado = models.ForeignKey(EstadosElemento, models.DO_NOTHING, db_column='estado_id', blank=True, null=True)
    valor_negocio = models.IntegerField(blank=True, null=True)
    dependencias_relaciones = models.TextField(blank=True, null=True)
    componentes_relacionados = models.CharField(max_length=200, blank=True, null=True)
    notas_adicionales = models.TextField(blank=True, null=True)
    proyecto = models.ForeignKey(Proyectos, models.DO_NOTHING, db_column='proyecto_id')
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'historias_usuario'

    def __str__(self):
        return self.titulo


class HistoriasEstimaciones(models.Model):
    historia = models.ForeignKey(HistoriasUsuario, models.CASCADE, db_column='historia_id')
    tipo_estimacion = models.ForeignKey(TiposEstimacion, models.DO_NOTHING, db_column='tipo_estimacion_id')
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'historias_estimaciones'
        unique_together = (('historia', 'tipo_estimacion'),)

    def __str__(self):
        return f"{self.historia.titulo} - {self.tipo_estimacion.nombre}: {self.valor}"