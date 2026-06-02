from django.db import models
from django.contrib.auth.models import AbstractUser

# ==============================================================================
# MODELO: CUSTOMUSER (Extensión del Sistema de Autenticación de Django)
# ==============================================================================
class CustomUser(AbstractUser):
    """
    Modelo de usuario personalizado que hereda de AbstractUser.
    Permite añadir campos clave como el 'role' o forzar el 'email' único sin perder
    las características nativas de Django (gestión de contraseñas, grupos, login, etc.).
    """

    # 1. ENUMERACIÓN DE ROLES (TextChoices)
    # Define de forma limpia y tipada los roles disponibles en el software de eSports
    class RoleChoices(models.TextChoices):
        ADMIN = 'admin', 'Admin'        # Control total de la plataforma (crea clubes, ve todo)
        COACH = 'coach', 'Coach'        # Gestiona la plantilla de su club y sube estadísticas
        PLAYER = 'player', 'Player'      # Acceso básico de consulta a su propio perfil
        MANAGER = 'manager', 'Manager'  # Gestión administrativa de la franquicia y staff

    # 2. CAMPOS ADICIONALES Y RESTRICCIONES
    # Forzamos que el correo electrónico sea único en la BD (útil si deseas implementar login por email)
    email = models.EmailField(unique=True)
    
    # Campo para almacenar el rol asignado al usuario con un desplegable controlado en el panel de administración
    role = models.CharField(
        max_length=20,
        choices=RoleChoices.choices,     # Vincula las opciones del enum anterior
        default=RoleChoices.PLAYER       # Por defecto, cualquier registro nuevo entra con el rol más básico
    )
    
    # 3. MÉTODOS MÁGICOS
    def __str__(self):
        """
        Representación en texto del usuario para el panel de administración de Django.
        Salida de ejemplo: "hector99 (admin)"
        """
        return f"{self.username} ({self.role})"