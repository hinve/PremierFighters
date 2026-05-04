from typing import Any, cast

from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
import os
from django.conf import settings
from django.core.exceptions import ValidationError

from matches.models import Match
from players.models import Player
from users.permissions import get_user_team

from .models import PlayerMatchStats


class MatchSelectionForm(forms.Form):
    match = forms.ModelChoiceField(queryset=Match.objects.none(), label="Partido")

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        if user and getattr(user, "role", "").lower() != "admin":
            team = get_user_team(user)
            if team:
                cast(Any, self.fields["match"]).queryset = Match.objects.select_related("team").filter(team=team).order_by("-date")
            else:
                cast(Any, self.fields["match"]).queryset = Match.objects.none()
        else:
            cast(Any, self.fields["match"]).queryset = Match.objects.select_related("team").all().order_by("-date")


class MapResultBatchForm(forms.Form):
    won = forms.ChoiceField(
        label="Resultado",
        choices=(("true", "Victoria"), ("false", "Derrota")),
        widget=forms.RadioSelect,
        initial="true",
    )


class MapResultPlayerRowForm(forms.Form):
    agent_name = forms.CharField(max_length=100, label="Agente", required=False)
    kills = forms.IntegerField(min_value=0, initial=0, label="Kills")
    deaths = forms.IntegerField(min_value=0, initial=0, label="Deaths")
    assists = forms.IntegerField(min_value=0, initial=0, label="Assists")

    # Build allowed agent names from assets/caracterIcon (filenames without extension)
    _ALLOWED_AGENTS = set()
    try:
        icons_path = os.path.join(settings.BASE_DIR, "assets", "caracterIcon")
        for fn in os.listdir(icons_path):
            if fn.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
                _ALLOWED_AGENTS.add(os.path.splitext(fn)[0])
    except Exception:
        # If assets folder not available, leave set empty (skip validation)
        _ALLOWED_AGENTS = set()

    def clean_agent_name(self):
        value = self.cleaned_data.get("agent_name") or ""
        if value:
            if self._ALLOWED_AGENTS and value not in self._ALLOWED_AGENTS:
                raise ValidationError("Agente no válido. Selecciona un agente existente.")
        return value


class PlayerMatchStatsForm(forms.ModelForm):
    class Meta:
        model = PlayerMatchStats
        fields = ["player", "match", "agent_name", "kills", "deaths", "assists", "won"]
        labels = {
            "map_name": "Mapa",
            "agent_name": "Agente",
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        if user and getattr(user, "role", "").lower() != "admin":
            team = get_user_team(user)
            if team:
                cast(Any, self.fields["player"]).queryset = Player.objects.select_related("team").filter(team=team)
                cast(Any, self.fields["match"]).queryset = Match.objects.select_related("team").filter(team=team)
            else:
                cast(Any, self.fields["player"]).queryset = Player.objects.none()
                cast(Any, self.fields["match"]).queryset = Match.objects.none()


class PlayerMatchStatsInlineForm(forms.ModelForm):
    """Formulario simplificado para usar en inlines (sin seleccionar match)."""
    class Meta:
        model = PlayerMatchStats
        fields = ["player", "agent_name", "kills", "deaths", "assists", "won"]
        labels = {
            "map_name": "Mapa",
            "agent_name": "Agente",
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        if user and getattr(user, "role", "").lower() != "admin":
            team = get_user_team(user)
            if team:
                cast(Any, self.fields["player"]).queryset = Player.objects.select_related("team").filter(team=team)
            else:
                cast(Any, self.fields["player"]).queryset = Player.objects.none()


class PlayerMatchStatsInlineFormSet(BaseInlineFormSet):
    """FormSet personalizado para pasar el user a cada formulario."""
    
    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs["user"] = self.user
        return kwargs


# Formset para múltiples estadísticas de jugadores por partido
PlayerMatchStatsFormSet: Any = inlineformset_factory(
    Match,
    PlayerMatchStats,
    form=PlayerMatchStatsInlineForm,
    formset=PlayerMatchStatsInlineFormSet,
    extra=5,
    can_delete=True
)