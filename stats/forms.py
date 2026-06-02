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

# ==============================================================================
# FORMULARIO 1: SELECCIÓN DE PARTIDO
# ==============================================================================
class MatchSelectionForm(forms.Form):
    """Formulario simple para elegir un partido antes de cargar el reporte de estadísticas."""
    match = forms.ModelChoiceField(queryset=Match.objects.none(), label="Partido")

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        # SEGURIDAD: Los admins ven todos los partidos; los coaches solo los de su club
        if user and getattr(user, "role", "").lower() != "admin":
            team = get_user_team(user)
            if team:
                # select_related optimiza la consulta SQL evitando problemas de N+1 queries
                cast(Any, self.fields["match"]).queryset = Match.objects.select_related("team").filter(team=team).order_by("-date")
            else:
                cast(Any, self.fields["match"]).queryset = Match.objects.none()
        else:
            cast(Any, self.fields["match"]).queryset = Match.objects.select_related("team").all().order_by("-date")


# ==============================================================================
# FORMULARIO 2: CONFIGURACIÓN POR LOTES (Batch)
# ==============================================================================
class MapResultBatchForm(forms.Form):
    """Permite definir con botones de radio si el mapa global fue Victoria o Derrota."""
    won = forms.ChoiceField(
        label="Resultado",
        choices=(("true", "Victoria"), ("false", "Derrota")),
        widget=forms.RadioSelect, # Lo renderiza como botones circulares en lugar de un menú desplegable
        initial="true",
    )


# ==============================================================================
# FORMULARIO 3: FILA DE JUGADOR INDIVIDUAL (Económico / Sin ORM)
# ==============================================================================
class MapResultPlayerRowForm(forms.Form):
    """Formulario básico de entrada de texto/números para la puntuación de un jugador."""
    agent_name = forms.CharField(max_length=100, label="Agente", required=False)
    kills = forms.IntegerField(min_value=0, initial=0, label="Kills")
    deaths = forms.IntegerField(min_value=0, initial=0, label="Deaths")
    assists = forms.IntegerField(min_value=0, initial=0, label="Assists")

    # Sistema dinámico de validación de Agentes de Valorant basándose en los iconos del proyecto
    _ALLOWED_AGENTS = set()
    try:
        # Construye la ruta hacia la carpeta de iconos de agentes (ej: assets/caracterIcon)
        icons_path = os.path.join(settings.BASE_DIR, "assets", "caracterIcon")
        for fn in os.listdir(icons_path):
            # Filtra solo los archivos de imagen
            if fn.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".gif")):
                # Añade el nombre del archivo sin la extensión (ej: 'jett', 'raze') al set de permitidos
                _ALLOWED_AGENTS.add(os.path.splitext(fn)[0])
    except Exception:
        # Si la carpeta no se encuentra, el set queda vacío y se salta esta validación por seguridad
        _ALLOWED_AGENTS = set()

    def clean_agent_name(self):
        """Método de limpieza y validación del campo agent_name."""
        value = self.cleaned_data.get("agent_name") or ""
        if value:
            # Si el set contiene agentes y el texto introducido no coincide con ninguno, lanza un error de formulario
            if self._ALLOWED_AGENTS and value not in self._ALLOWED_AGENTS:
                raise ValidationError("Agente no válido. Selecciona un agente existente.")
        return value


# ==============================================================================
# FORMULARIO 4: MODELFORM ESTÁNDAR PARA ESTADÍSTICAS
# ==============================================================================
class PlayerMatchStatsForm(forms.ModelForm):
    """Formulario mapeado directamente a la BD para gestionar estadísticas individuales."""
    class Meta:
        model = PlayerMatchStats
        fields = ["player", "match", "agent_name", "kills", "deaths", "assists", "won"]
        labels = {
            "map_name": "Mapa",
            "agent_name": "Agente",
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        # SEGURIDAD: Capado estricto de jugadores y partidos según el club del usuario
        if user and getattr(user, "role", "").lower() != "admin":
            team = get_user_team(user)
            if team:
                cast(Any, self.fields["player"]).queryset = Player.objects.select_related("team").filter(team=team)
                cast(Any, self.fields["match"]).queryset = Match.objects.select_related("team").filter(team=team)
            else:
                cast(Any, self.fields["player"]).queryset = Player.objects.none()
                cast(Any, self.fields["match"]).queryset = Match.objects.none()


# ==============================================================================
# FORMULARIO 5: MODELFORM PARA COMPONENTES INLINE (Formsets)
# ==============================================================================
class PlayerMatchStatsInlineForm(forms.ModelForm):
    """Formulario optimizado para rejillas de datos. Omitimos el campo 'match' porque lo hereda del padre."""
    class Meta:
        model = PlayerMatchStats
        fields = ["player", "agent_name", "kills", "deaths", "assists", "won"]
        labels = {
            "map_name": "Mapa",
            "agent_name": "Agente",
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        # SEGURIDAD: Limita los jugadores del desplegable a los del equipo del Coach
        if user and getattr(user, "role", "").lower() != "admin":
            team = get_user_team(user)
            if team:
                cast(Any, self.fields["player"]).queryset = Player.objects.select_related("team").filter(team=team)
            else:
                cast(Any, self.fields["player"]).queryset = Player.objects.none()


# ==============================================================================
# FORMSET PERSONALIZADO: CONECTOR MULTIFORMULARIO
# ==============================================================================
class PlayerMatchStatsInlineFormSet(BaseInlineFormSet):
    """
    Clase puente. Por defecto, los FormSets de Django no transmiten el parámetro 'user'
    a los formularios que contienen. Esta clase intercepta la creación de cada fila para inyectarlo.
    """
    def __init__(self, *args, user=None, **kwargs):
        self.user = user # Captura el usuario enviado desde la vista
        super().__init__(*args, **kwargs)
    
    def get_form_kwargs(self, index):
        """Inyecta el usuario como un argumento clave para el __init__ de cada formulario individual."""
        kwargs = super().get_form_kwargs(index)
        kwargs["user"] = self.user
        return kwargs


# Fábrica empaquetadora (InlineFormSet): Vincula un Partido (Match) con múltiples filas de Estadísticas
PlayerMatchStatsFormSet: Any = inlineformset_factory(
    Match,                          # Modelo Padre
    PlayerMatchStats,               # Modelo Hijo (Línea de detalle)
    form=PlayerMatchStatsInlineForm, # Estructura de cada fila
    formset=PlayerMatchStatsInlineFormSet, # Gestor supervisor personalizado
    extra=5,                        # Genera automáticamente 5 filas vacías en la interfaz (los 5 jugadores de Valorant)
    can_delete=True                 # Permite añadir casillas de verificación para eliminar filas existentes
)