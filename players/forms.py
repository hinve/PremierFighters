from django import forms
from django.forms import ModelChoiceField
from users.permissions import get_user_team
from .models import Player


class PlayerForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = ["nickname", "real_name", "country", "role_in_game", "team"]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar equipos según el rol del usuario
        if "team" in self.fields and isinstance(self.fields["team"], ModelChoiceField):
            qs = self.fields["team"].queryset
            if user and getattr(user, "role", "").lower() != "admin":
                team = get_user_team(user)
                qs = qs.filter(id=team.id) if team else qs.none()
            self.fields["team"].queryset = qs