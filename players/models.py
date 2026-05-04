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
    
    def calculate_kd_ratio(self):
        """Calcula el K/D total del jugador en todos los partidos."""
        from matches.models import Match
        from stats.models import PlayerMatchStats
        stats = PlayerMatchStats.objects.filter(
            player=self,
            match__result__in=[Match.ResultType.WIN, Match.ResultType.LOSS],
        )
        total_kills = sum(s.kills for s in stats)
        total_deaths = sum(s.deaths for s in stats)
        
        if total_deaths == 0:
            return float(total_kills) if total_kills > 0 else 0.0
        return round(total_kills / total_deaths, 2)
    
    def calculate_winrate(self):
        """Calcula el winrate del jugador (porcentaje de mapas ganados)."""
        from matches.models import Match
        from stats.models import PlayerMatchStats
        stats = PlayerMatchStats.objects.filter(
            player=self,
            match__result__in=[Match.ResultType.WIN, Match.ResultType.LOSS],
        )
        total_maps = stats.count()
        
        if total_maps == 0:
            return 0.0
        
        wins = stats.filter(match__result=Match.ResultType.WIN).count()
        return round((wins / total_maps) * 100, 1) if total_maps > 0 else 0.0