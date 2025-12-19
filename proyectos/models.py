# proyectos/models.py
from django.db import models
from usuarios.models import Usuarios
from catalogos.models import EstadosProyecto

class Proyectos(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    estado = models.ForeignKey(
        EstadosProyecto, 
        models.DO_NOTHING, 
        db_column='estado_id',
        blank=True, 
        null=True
    )
    fecha_creacion = models.DateField(auto_now_add=True)
    fecha_actualizacion = models.DateField(auto_now=True)
    usuario = models.ForeignKey(Usuarios, models.DO_NOTHING, db_column='usuario_id')
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'proyectos'

    def __str__(self):
        return f"{self.nombre} ({self.estado.nombre if self.estado else 'Sin estado'})"