from django import forms

from .models import Team


class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ["name", "tag", "region", "coach", "manager"]

    def clean(self):
        cleaned_data = super().clean()
        coach = cleaned_data.get("coach")
        manager = cleaned_data.get("manager")

        if coach and manager and coach == manager:
            raise forms.ValidationError("Coach y manager no pueden ser el mismo usuario.")

        return cleaned_data