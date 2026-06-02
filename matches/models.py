from django.db import models
from teams.models import Team
from tournaments.models import Tournament
from django.conf import settings

# Definición del modelo Match (Partidos) que se convertirá en una tabla de tu base de datos SQLite
class Match(models.Model):
    
    # 1. ENUMERACIONES (TEXTCHOICES) - Buenas prácticas de Django
    # Define los tipos de partidos disponibles en la aplicación para evitar errores de escritura
    class MatchType(models.TextChoices):
        SCRIM = 'Scrim', 'Scrim'            # Partidos de entrenamiento contra otros equipos
        OFFICIAL = 'Official', 'Official'    # Partidos oficiales de liga o torneo

    # Define los tres estados posibles en los que puede estar un partido
    class ResultType(models.TextChoices):
        PENDING = 'Pending', 'Pendiente'    # El partido está agendado pero no se ha jugado/registrado
        WIN = 'Win', 'Win'                  # Victoria para tu equipo
        LOSS = 'Loss', 'Loss'               # Derrota para tu equipo
    
    # 2. RELACIONES ENTRE TABLAS (CLAVES FORÁNEAS)
    # Relación de muchos a uno con el equipo de tu plataforma. 
    # Si el equipo se borra, se borran sus partidos en cascada (models.CASCADE)
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='matches'              # Permite hacer consultas inversas (ej: team.matches.all())
    )
    
    # Nombre del equipo rival (no hace falta que esté registrado en nuestra base de datos, basta con el texto)
    opponent_name = models.CharField(max_length=100)
    
    # Relación con la app de torneos. Si el torneo se borra, el partido NO se borra, 
    # simplemente el campo se pone en Null (on_delete=models.SET_NULL)
    tournament = models.ForeignKey(
        Tournament,
        on_delete=models.SET_NULL,
        null=True,                          # Permite que un partido no pertenezca a ningún torneo (ej: una scrim libre)
        blank=True,                         # Permite dejar el campo vacío en los formularios del frontend
        related_name='matches'
    )
    
    # 3. CAMPOS DE DETALLE DEL PARTIDO
    # Tipo de partido. Usa el enumerado MatchType y por defecto lo marca como entrenamiento (Scrim)
    match_type = models.CharField(
        max_length=20,
        choices=MatchType.choices,
        default=MatchType.SCRIM
    )
    
    # Fecha y hora exacta programada para el encuentro
    date = models.DateTimeField()
    
    # Puntuación (rondas de Valorant) obtenidas por tu equipo (ej: 13)
    score_team = models.PositiveBigIntegerField(default=0)
    
    # Puntuación (rondas de Valorant) obtenidas por el rival (ej: 9)
    score_opponent = models.PositiveBigIntegerField(default=0)
    
    # Estado del resultado. Usa el enumerado ResultType y por defecto es 'Pendiente'
    result = models.CharField(
        max_length=10,
        choices=ResultType.choices,
        default=ResultType.PENDING
    )
    
    # Nombre del mapa de Valorant donde se disputa este partido (ej: Fracture, Pearl, Lotus...)
    map_name = models.CharField(max_length=100, blank=True, default='')
    
    # Registro de qué usuario (Coach, Manager o Admin) subió este partido al sistema. 
    # Si el usuario se borra de la web, el historial del partido se mantiene (SET_NULL)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    
    # Sello de tiempo automático que guarda la fecha y hora exacta en la que se creó este registro en la base de datos
    created_at = models.DateTimeField(auto_now_add=True)
    
    # 4. MÉTODOS DEL MODELO
    def __str__(self):
        """
        Método mágico de Python. Define cómo se representará este objeto como texto plano 
        en el panel de administración de Django o en los selectores del frontend.
        Ejemplo de salida: "KPI Gaming vs KOI - 2026-06-02 18:00 (Official, Win)"
        """
        result_label = "Pendiente" if self.result == self.ResultType.PENDING else self.result
        return f"{self.team.name} vs {self.opponent_name} - {self.date.strftime('%Y-%m-%d %H:%M')} ({self.match_type}, {result_label})"

    def is_decided(self):
        """
        Función auxiliar de lógica de negocio. Retorna True si el partido ya se ha jugado 
        (es decir, es una Victoria o una Derrota) y False si todavía está Pendiente.
        Es súper útil para filtrar estadísticas en las vistas.
        """
        return self.result in {self.ResultType.WIN, self.ResultType.LOSS}