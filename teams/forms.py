from django import forms

from .models import Team

# Formulario basado en el modelo Team para la creación y edición de equipos/clubes
class TeamForm(forms.ModelForm):
    
    # Configuración de metadatos para enlazar el formulario con la base de datos
    class Meta:
        model = Team  # Vincula este formulario con el modelo Team
        
        # Campos del club que se expondrán y serán editables en la interfaz web
        fields = ["name", "tag", "region", "coach", "manager"]

    def clean(self):
        """
        Método de validación global/cruzada del formulario.
        Se ejecuta después de verificar los campos individuales y sirve para comparar 
        valores de diferentes inputs entre sí antes de dar el visto bueno al guardado.
        """
        # Invoca el método clean estándar de Django para obtener los datos ya limpios e individuales
        cleaned_data = super().clean()
        
        # Recupera los usuarios asignados a los roles de cuerpo técnico y directiva
        coach = cleaned_data.get("coach")
        manager = cleaned_data.get("manager")

        # ==============================================================================
        # REGLA DE NEGOCIO: CONTROL DE DUPLICIDAD DE ROLES
        # ==============================================================================
        # Si se han rellenado ambos campos, verifica si se ha seleccionado al mismo usuario
        if coach and manager and coach == manager:
            # Lanza un error de validación global que detiene el guardado y se muestra en el HTML
            raise forms.ValidationError("Coach y manager no pueden ser el mismo usuario.")

        # Si todo es correcto, devuelve el diccionario de datos listos para ser guardados en la BD
        return cleaned_data