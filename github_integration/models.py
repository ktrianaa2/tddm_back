"""
app: github_integration
Crea una nueva app Django: python manage.py startapp github_integration
Agrega 'github_integration' a INSTALLED_APPS en settings.py

Requiere instalar: pip install cryptography
Y agregar en settings.py:
    import os
    GITHUB_TOKEN_KEY = os.environ.get('GITHUB_TOKEN_KEY', '')
    # Para generar la clave la primera vez ejecuta en una consola Python:
    # from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())
    # Guarda ese valor en tu .env como GITHUB_TOKEN_KEY=<valor>
"""

from django.db import models
from django.conf import settings
from cryptography.fernet import Fernet


def _fernet():
    key = settings.GITHUB_TOKEN_KEY
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


class GitHubConexion(models.Model):
    """
    Guarda la conexión GitHub de un usuario.
    El token se encripta con Fernet antes de guardarse en BD.
    Un usuario solo puede tener UNA conexión activa (unique en usuario).
    """
    # FK al modelo Usuarios existente (managed=False, tabla 'usuarios')
    # Usamos IntegerField + db_column para no depender de importar el modelo
    # de otra app y evitar migraciones circulares. Aun así funciona como FK lógica.
    usuario_id = models.IntegerField(
        unique=True,
        db_index=True,
        help_text="ID del usuario de la tabla 'usuarios'"
    )

    # Token encriptado con Fernet — nunca se guarda en texto plano
    token_encriptado = models.TextField(
        help_text="GitHub PAT encriptado con Fernet"
    )

    # Metadatos de la conexión (no sensibles, en texto plano)
    github_usuario = models.CharField(
        max_length=100,
        help_text="Login de GitHub del usuario (@username)"
    )
    github_avatar = models.URLField(
        blank=True,
        default='',
        help_text="URL del avatar de GitHub"
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'github_conexiones'

    def __str__(self):
        return f"GitHubConexion(usuario_id={self.usuario_id}, github={self.github_usuario})"

    # ── Métodos para manejar el token encriptado ──────────────────────────

    def set_token(self, token_plano: str):
        """Encripta y guarda el token."""
        f = _fernet()
        self.token_encriptado = f.encrypt(token_plano.encode()).decode()

    def get_token(self) -> str:
        """Desencripta y retorna el token en texto plano."""
        f = _fernet()
        return f.decrypt(self.token_encriptado.encode()).decode()