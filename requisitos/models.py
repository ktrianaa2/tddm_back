# requisitos/models.py
from django.db import models
from proyectos.models import Proyectos
from django.utils import timezone

class TiposRequisito(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)  # Added missing field

    class Meta:
        managed = False
        db_table = 'tipos_requisito'

    def __str__(self):
        return self.nombre


class Prioridades(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    nivel = models.IntegerField(unique=True)
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)  # Added missing field

    class Meta:
        managed = False
        db_table = 'prioridades'

    def __str__(self):
        return self.nombre


class EstadosElemento(models.Model):
    nombre = models.CharField(max_length=50)
    descripcion = models.TextField(blank=True, null=True)
    tipo = models.CharField(max_length=20)
    activo = models.BooleanField(default=True)  # Added missing field

    class Meta:
        managed = False
        db_table = 'estados_elemento'
        unique_together = (('nombre', 'tipo'),)

    def __str__(self):
        return f"{self.nombre} ({self.tipo})"


class Requisitos(models.Model):
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField()
    tipo = models.ForeignKey(TiposRequisito, models.DO_NOTHING, db_column='tipo_id')
    criterios = models.TextField()
    prioridad = models.ForeignKey(Prioridades, models.DO_NOTHING, db_column='prioridad_id', blank=True, null=True)
    estado = models.ForeignKey(EstadosElemento, models.DO_NOTHING, db_column='estado_id', blank=True, null=True)
    origen = models.CharField(max_length=100, blank=True, null=True)
    condiciones_previas = models.TextField(blank=True, null=True)
    proyecto = models.ForeignKey(Proyectos, models.DO_NOTHING, db_column='proyecto_id')
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'requisitos'

    def __str__(self):
        return self.nombre


class TiposRelacionRequisito(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)  # Added missing field

    class Meta:
        managed = False
        db_table = 'tipos_relacion_requisito'

    def __str__(self):
        return self.nombre


class RelacionesRequisitos(models.Model):
    requisito_origen = models.ForeignKey(Requisitos, related_name="relaciones_origen", on_delete=models.CASCADE, db_column='requisito_origen_id')
    requisito_destino = models.ForeignKey(Requisitos, related_name="relaciones_destino", on_delete=models.CASCADE, db_column='requisito_destino_id')
    tipo_relacion = models.ForeignKey(TiposRelacionRequisito, models.DO_NOTHING, db_column='tipo_relacion_id')
    descripcion = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'relaciones_requisitos'

    def __str__(self):
        return f"{self.requisito_origen.nombre} -> {self.requisito_destino.nombre}"