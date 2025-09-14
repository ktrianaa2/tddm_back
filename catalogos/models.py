# catalogos/models.py
from django.db import models
from django.utils import timezone

class TiposRequisito(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'tipos_requisito'

    def __str__(self):
        return self.nombre


class Prioridades(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    nivel = models.IntegerField(unique=True)
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'prioridades'

    def __str__(self):
        return self.nombre


class EstadosProyecto(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    orden = models.IntegerField(unique=True)
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'estados_proyecto'

    def __str__(self):
        return self.nombre

class EstadosElemento(models.Model):
    nombre = models.CharField(max_length=50)
    descripcion = models.TextField(blank=True, null=True)
    tipo = models.CharField(max_length=20)  # 'requisito', 'caso_uso', 'historia_usuario'
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'estados_elemento'
        unique_together = ('nombre', 'tipo')

    def __str__(self):
        return f"{self.nombre} ({self.tipo})"


class TiposRelacionCu(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'tipos_relacion_cu'

    def __str__(self):
        return self.nombre


class TiposRelacionRequisito(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'tipos_relacion_requisito'

    def __str__(self):
        return self.nombre

class TiposEstimacion(models.Model):
    nombre = models.CharField(max_length=50, unique=True)  # story-points, horas, días, costo
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        managed = False
        db_table = 'tipos_estimacion'

    def __str__(self):
        return self.nombre