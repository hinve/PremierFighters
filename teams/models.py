from django.db import models
from django.conf import settings

# Create your models here.
class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    tag = models.CharField(max_length=10, unique=True)
    region = models.CharField(max_length=50)
    
    # relaciones con usuarios para roles de coach y manager, uso onetoonefield para asegurar que un usuario solo pueda ser coach o manager de un equipo a la vez, y que un equipo solo tenga un coach y un manager
    # si mas adelante quiero poder asignar un usuario a varios equipos como coach o manager, puedo cambiarlo a ForeignKey
    coach = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='coached_team'
    )
    
    manager = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_team'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.tag})"