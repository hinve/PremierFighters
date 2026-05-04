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
        PENDING = 'Pending', 'Pendiente'
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
        default=ResultType.PENDING
    )
    map_name = models.CharField(max_length=100, blank=True, default='')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        result_label = "Pendiente" if self.result == self.ResultType.PENDING else self.result
        return f"{self.team.name} vs {self.opponent_name} - {self.date.strftime('%Y-%m-%d %H:%M')} ({self.match_type}, {result_label})"

    def is_decided(self):
        return self.result in {self.ResultType.WIN, self.ResultType.LOSS}