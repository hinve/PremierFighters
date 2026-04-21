from django.db import models
from django.contrib.auth.models import AbstractUser

# esto gestiona los usuarios para el acceso, no se relaciona con los jugadores, entrenadores, etc.

# Create your models here.
class CustomUser(AbstractUser):
    # diferentes opciones de rol para los usuarios
    class RoleChoices(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        COACH = 'coach', 'Coach'
        PLAYER = 'player', 'Player'
        MANAGER = 'manager', 'Manager'
    
    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=20,
        choices=RoleChoices.choices,
        default=RoleChoices.PLAYER
    )
    
    def __str__(self):
        return f"{self.username} ({self.role})"