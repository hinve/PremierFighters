from django.db import models
from players.models import Player
from matches.models import Match

# Create your models here.

class PlayerMatchStats(models.Model):
    player = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
        related_name='stats'
    )
    
    match = models.ForeignKey(
        Match,
        on_delete=models.CASCADE,
        related_name='player_stats'
    )
    
    agent_name = models.CharField(max_length=100, blank=True)
    kills = models.PositiveIntegerField(default=0)
    deaths = models.PositiveIntegerField(default=0)
    assists = models.PositiveIntegerField(default=0)
    won = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('player', 'match')
        
    def __str__(self):
        agent_label = f" as {self.agent_name}" if self.agent_name else ""
        return f"Stats for {self.player.nickname} in match {self.match}{agent_label}"
    
    def kd_ratio(self):
        """Calcula el ratio K/D para este mapa."""
        if self.deaths == 0:
            return float(self.kills) if self.kills > 0 else 0.0
        return round(self.kills / self.deaths, 2)