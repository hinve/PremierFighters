from django import forms

from .models import Player


class PlayerForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = ["nickname", "real_name", "country", "role_in_game", "team"]