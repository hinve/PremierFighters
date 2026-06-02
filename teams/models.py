from django.db import models
from django.conf import settings

# Definición del modelo Team que estructurará las franquicias/clubes del sistema
class Team(models.Model):
    
    # 1. ATRIBUTOS BÁSICOS DEL EQUIPO
    # Nombre oficial del club (ej: 'Fnatic', 'Sentinels'). Es único para evitar duplicados.
    name = models.CharField(max_length=100, unique=True)
    
    # Siglas o abreviatura competitiva (ej: 'FNC', 'SEN'). También único y vital para marcadores compactos.
    tag = models.CharField(max_length=10, unique=True)
    
    # Región competitiva a la que pertenece el club (ej: 'EMEA', 'Americas', 'Pacific', 'CN')
    region = models.CharField(max_length=50)
    
    # 2. VINCULACIÓN CON EL PERSONAL TÉCNICO (Cuerpo técnico y directiva)
    # Relación uno a uno con el modelo de usuario personalizado de Django.
    # Un usuario solo puede entrenar a un equipo, y un equipo solo puede tener un Head Coach.
    # Si el usuario es borrado, el equipo NO se borra; simplemente el puesto queda libre (SET_NULL).
    coach = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='coached_team'         # Permite consultar desde el usuario (ej: user.coached_team)
    )
    
    # Relación uno a uno para el Director General / Mánager del club.
    # Misma lógica de integridad: evita que un mánager controle dos clubes rivales simultáneamente.
    manager = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_team'         # Permite consultar desde el usuario (ej: user.managed_team)
    )
    
    # 3. METADATOS DE AUDITORÍA
    # Registra de forma automática el momento exacto en el que el club se da de alta en la plataforma
    created_at = models.DateTimeField(auto_now_add=True)
    
    # 4. MÉTODOS MÁGICOS
    def __str__(self):
        """
        Define cómo se verá el equipo en los desplegables de administración y formularios.
        Salida de ejemplo: "Fnatic (FNC)"
        """
        return f"{self.name} ({self.tag})"