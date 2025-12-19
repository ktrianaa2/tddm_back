# pruebas/models.py
from django.db import models
from proyectos.models import Proyectos
import json

class TiposPrueba(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    color = models.CharField(max_length=7, default='#6B7280')
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'tipos_prueba'

    def __str__(self):
        return self.nombre


class Pruebas(models.Model):
    proyecto = models.ForeignKey(Proyectos, models.DO_NOTHING, db_column='proyecto_id')
    tipo_prueba = models.ForeignKey(TiposPrueba, models.DO_NOTHING, db_column='tipo_prueba_id')
    codigo = models.CharField(max_length=50)
    nombre = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, null=True)
    estado = models.CharField(max_length=50, blank=True, null=True)
    especificacion_relacionada = models.CharField(max_length=100, blank=True, null=True)  
    prueba = models.JSONField(default=dict)  # Cambiado a JSONField
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'pruebas'

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"