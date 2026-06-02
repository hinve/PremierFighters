from django import forms
from django.forms import ModelChoiceField
from users.permissions import get_user_team
from .models import Player

# Definición del formulario basado en el modelo Player para gestionar los fichajes/perfiles
class PlayerForm(forms.ModelForm):
    
    # La clase Meta se encarga de vincular el formulario con la estructura de la base de datos
    class Meta:
        model = Player  # Conecta este formulario directamente con el modelo Player
        
        # Campos específicos que se le pedirán al usuario en la interfaz web
        fields = ["nickname", "real_name", "country", "role_in_game", "team"]

    def __init__(self, *args, user=None, **kwargs):
        """
        Constructor personalizado del formulario.
        Se ejecuta antes de pintar los inputs en el HTML para aplicar reglas de seguridad
        basadas en quién está usando la aplicación (Admin vs Coach/Manager).
        """
        # Invoca el constructor base de Django para inicializar los campos por defecto
        super().__init__(*args, **kwargs)

        # ==============================================================================
        # SISTEMA DE CAPADO Y SEGURIDAD (Control de asignación de equipos)
        # ==============================================================================
        # Comprueba si el campo 'team' existe en el formulario y si es un desplegable válido (ModelChoiceField)
        if "team" in self.fields and isinstance(self.fields["team"], ModelChoiceField):
            
            # Almacena el QuerySet original (por defecto, Django trae TODOS los equipos de la base de datos)
            qs = self.fields["team"].queryset
            
            # Filtro estricto: Si el usuario actual NO es un Administrador global del sitio...
            if user and getattr(user, "role", "").lower() != "admin":
                # Obtiene mediante la función auxiliar el equipo al que pertenece este usuario
                team = get_user_team(user)
                
                # Si tiene equipo asignado, reduce la lista para que SOLO pueda seleccionarse ese ID.
                # Si el usuario no tiene ningún equipo asignado, se le devuelve un QuerySet vacío (.none())
                qs = qs.filter(id=team.id) if team else qs.none()
            
            # Aplica el QuerySet filtrado (y seguro) al desplegable del formulario en el HTML
            self.fields["team"].queryset = qs