# casosdeuso/models.py
from django.db import models
from proyectos.models import Proyectos
from catalogos.models import EstadosElemento, TiposRelacionCu, Prioridades
from django.utils import timezone

class CasosUso(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    actores = models.TextField()
    precondiciones = models.TextField()
    flujo_principal = models.JSONField(default=list) #REALIZAR CAMBIOS
    flujos_alternativos = models.JSONField(blank=True, null=True)
    postcondiciones = models.TextField(blank=True, null=True)
    requisitos_especiales = models.TextField(blank=True, null=True)
    riesgos_consideraciones = models.TextField(blank=True, null=True)
    proyecto = models.ForeignKey(Proyectos, models.DO_NOTHING, db_column='proyecto_id')
    prioridad = models.ForeignKey(Prioridades, models.DO_NOTHING, db_column='prioridad_id', blank=True, null=True)
    estado = models.ForeignKey(EstadosElemento, models.DO_NOTHING, db_column='estado_id', blank=True, null=True)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'casos_uso'

    def __str__(self):
        return self.nombre


class RelacionesCasosUso(models.Model):
    caso_uso_origen = models.ForeignKey(CasosUso, related_name="relaciones_origen", on_delete=models.CASCADE, db_column='caso_uso_origen_id')
    caso_uso_destino = models.ForeignKey(CasosUso, related_name="relaciones_destino", on_delete=models.CASCADE, db_column='caso_uso_destino_id')
    tipo_relacion = models.ForeignKey(TiposRelacionCu, models.DO_NOTHING, db_column='tipo_relacion_id')
    descripcion = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'relaciones_casos_uso'

    def __str__(self):
        return f"{self.caso_uso_origen.nombre} -> {self.caso_uso_destino.nombre}"