from django.db import models
from teams.models import Team
from tournaments.models import Tournament
from django.conf import settings

# Create your models here.
class Match(models.Model):
    class MatchType(models.TextChoices):
        SCRIM = 'Scrim', 'Scrim'
        OFFICIAL = 'Official', 'Official'
    
    class ResultType(models.TextChoices):
        WIN = 'Win', 'Win'
        LOSS = 'Loss', 'Loss'
    
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='matches'
    )
    opponent_name = models.CharField(max_length=100)
    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='matches'
    )
    match_type = models.CharField(
        max_length=20,
        choices=MatchType.choices,
        default=MatchType.SCRIM
    )
    date = models.DateTimeField()
    score_team = models.PositiveBigIntegerField(default=0)
    score_opponent = models.PositiveBigIntegerField(default=0)
    result = models.CharField(
        max_length=10,
        choices=ResultType.choices,
        default=ResultType.LOSS
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.team.name} vs {self.opponent_name} - {self.date.strftime('%Y-%m-%d %H:%M')} ({self.match_type})"