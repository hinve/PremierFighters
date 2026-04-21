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
    
    map_name = models.CharField(max_length=100, blank=True)
    kills = models.PositiveIntegerField(default=0)
    deaths = models.PositiveIntegerField(default=0)
    assists = models.PositiveIntegerField(default=0)
    won = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('player', 'match', "map_name")
        
    def __str__(self):
        return f"Stats for {self.player.nickname} in match {self.match} on map {self.map_name}"