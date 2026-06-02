from django import forms

from users.permissions import get_user_team
from teams.models import Team

from .models import Match

# Definición del formulario basado en el modelo Match
class MatchForm(forms.ModelForm):
    
    # La clase Meta define la configuración básica y el comportamiento del formulario
    class Meta:
        model = Match  # Vincula este formulario directamente con tu modelo de partidos
        
        # Lista de campos del modelo que se van a renderizar como inputs en el HTML
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
        
        # Modificación de los componentes HTML (widgets) para añadirles atributos o cambiar su tipo
        widgets = {
            # Convierte el input de fecha normal en un selector nativo de fecha y hora del navegador (HTML5)
            "date": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            # Añade un texto de sugerencia (placeholder) al campo del nombre del rival
            "opponent_name": forms.TextInput(attrs={"placeholder": "Equipo rival"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        """
        Constructor personalizado. Se ejecuta cada vez que la vista crea o edita un partido.
        Permite inyectar lógica dinámica antes de que el formulario se pinte en pantalla.
        """
        # Invoca el constructor original de Django para cargar los campos por defecto
        super().__init__(*args, **kwargs)

        # ==============================================================================
        # 1. GENERACIÓN DINÁMICA DE MAPAS DE VALORANT (Basado en archivos locales)
        # ==============================================================================
        try:
            import os
            from django.conf import settings
            
            # Construye la ruta absoluta hacia la carpeta donde guardas las imágenes de los mapas (ej: assets/maps)
            maps_dir = os.path.join(settings.BASE_DIR, 'assets', 'maps')
            
            # Lee el directorio y filtra solo archivos que sean imágenes (png, jpg, jpeg, webp) ordenados alfabéticamente
            files = sorted([f for f in os.listdir(maps_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))])
            
            # Crea las opciones del desplegable (Select). 
            # Convierte el nombre del archivo (ej: 'ascent.png') en una tupla limpia ('ascent', 'ascent') quitándole la extensión
            choices = [('', 'Sin mapa')] + [(os.path.splitext(f)[0], os.path.splitext(f)[0]) for f in files]
            
            # Transforma el campo 'map_name' de un input de texto normal a un campo desplegable (ChoiceField) con tus mapas reales
            self.fields['map_name'] = forms.ChoiceField(choices=choices, required=False, label='Mapa')
        
        except Exception:
            # Plan de respaldo (Fallback): Si la carpeta de imágenes no existe o da error, 
            # el formulario no se rompe; simplemente vuelve a dejar el campo como un texto normal (CharField)
            self.fields['map_name'] = forms.CharField(required=False, label='Mapa')

        # ==============================================================================
        # 2. SISTEMA DE SEGURIDAD Y CONTROL DE ACCESO (Filtrado por Rol)
        # ==============================================================================
        if "team" in self.fields:
            # Si el usuario logueado NO es administrador, restringimos sus opciones
            if user and getattr(user, "role", "").lower() != "admin":
                # Obtiene el equipo específico al que pertenece este Coach o Manager
                team = get_user_team(user)
                
                if team:
                    # En el desplegable del formulario, este usuario SOLO verá y podrá elegir su propio equipo
                    self.fields["team"].queryset = Team.objects.filter(id=team.id) # type: ignore
                else:
                    # Si no tiene equipo asignado, el desplegable se vacía por completo (evita que registre partidos a ciegas)
                    self.fields["team"].queryset = Team.objects.none() # type: ignore