from django.db import models
from teams.models import Team

# Create your models here.

class Player(models.Model):
    nickname = models.CharField(max_length=50, unique=True)
    real_name = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=50, blank=True )
    role_in_game = models.CharField(max_length=50, blank=True)
    
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='players'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.nickname} ({self.team.tag if self.team else 'No Team'})"