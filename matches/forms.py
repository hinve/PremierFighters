from django import forms

from users.permissions import get_user_team
from teams.models import Team

from .models import Match


class MatchForm(forms.ModelForm):
    class Meta:
        model = Match
        fields = [
            "map_name",
            "team",
            "opponent_name",
            "tournament",
            "match_type",
            "date",
            "score_team",
            "score_opponent",
            "result",
        ]
        widgets = {
            "date": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "opponent_name": forms.TextInput(attrs={"placeholder": "Equipo rival"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Populate map choices from assets/maps
        try:
            import os
            from django.conf import settings
            maps_dir = os.path.join(settings.BASE_DIR, 'assets', 'maps')
            files = sorted([f for f in os.listdir(maps_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))])
            choices = [('', 'Sin mapa')] + [(os.path.splitext(f)[0], os.path.splitext(f)[0]) for f in files]
            self.fields['map_name'] = forms.ChoiceField(choices=choices, required=False, label='Mapa')
        except Exception:
            # fallback to a simple text field if assets not accessible
            self.fields['map_name'] = forms.CharField(required=False, label='Mapa')

        if "team" in self.fields:
            if user and getattr(user, "role", "").lower() != "admin":
                team = get_user_team(user)
                if team:
                    self.fields["team"].queryset = Team.objects.filter(id=team.id) # type: ignore
                else:
                    self.fields["team"].queryset = Team.objects.none() # type: ignore