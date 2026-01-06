# esquemas_bd/models.py
from django.db import models
from proyectos.models import Proyectos
from django.utils import timezone

class TiposMotorBd(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    extension_archivo = models.CharField(max_length=10, blank=True, null=True)
    sintaxis_especifica = models.TextField(blank=True, null=True)
    color = models.CharField(max_length=7, default='#6B7280')
    activo = models.BooleanField(default=True)
    
    class Meta:
        managed = False
        db_table = 'tipos_motor_bd'
        verbose_name = 'Tipo de Motor BD'
        verbose_name_plural = 'Tipos de Motor BD'
    
    def __str__(self):
        return self.nombre


class EsquemasBd(models.Model):
    proyecto = models.ForeignKey(
        Proyectos, 
        on_delete=models.CASCADE, 
        related_name='esquemas_bd',
        db_column='proyecto_id'
    )
    tipo_motor_bd = models.ForeignKey(
        TiposMotorBd, 
        on_delete=models.PROTECT,
        db_column='tipo_motor_bd_id'
    )
    esquema = models.JSONField(help_text="Estructura JSON del esquema de BD")
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)
    
    class Meta:
        managed = False
        db_table = 'esquemas_bd'
        verbose_name = 'Esquema BD'
        verbose_name_plural = 'Esquemas BD'
        # Evitar duplicados: mismo proyecto + mismo motor = único
        constraints = [
            models.UniqueConstraint(
                fields=['proyecto', 'tipo_motor_bd'],
                condition=models.Q(activo=True),
                name='unique_active_schema_per_motor'
            )
        ]
    
    def __str__(self):
        return f"{self.proyecto.nombre} - {self.tipo_motor_bd.nombre}"