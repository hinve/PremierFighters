from django.db import models
from players.models import Player
from matches.models import Match

# Definición del modelo PlayerMatchStats que almacena el rendimiento individual por mapa/partido
class PlayerMatchStats(models.Model):
    
    # 1. RELACIONES ENTRE TABLAS (Claves Foráneas)
    # Vinculación con el jugador. Si el jugador se borra de la app, sus estadísticas se borran en cascada (CASCADE).
    player = models.ForeignKey(
        Player,
        on_delete=models.CASCADE,
        related_name='stats'                # Permite acceder a las estadísticas desde el jugador (ej: player.stats.all())
    )
    
    # Vinculación con el partido. Si el partido se elimina, su registro de estadísticas también desaparece.
    match = models.ForeignKey(
        Match,
        on_delete=models.CASCADE,
        related_name='player_stats'         # Permite al partido recuperar las notas de sus 5 jugadores
    )
    
    # 2. MÉTRICAS DEL JUGADOR EN EL MAPA
    # Nombre del agente de Valorant utilizado en este mapa específico (ej: 'Jett', 'Omen', 'Sova'...)
    agent_name = models.CharField(max_length=100, blank=True)
    
    # Cantidad de asesinatos/bajas logradas. Restringido a números positivos.
    kills = models.PositiveIntegerField(default=0)
    
    # Cantidad de veces que el jugador ha muerto en el mapa. Restringido a números positivos.
    deaths = models.PositiveIntegerField(default=0)
    
    # Cantidad de asistencias otorgadas a los compañeros de equipo. Restringido a números positivos.
    assists = models.PositiveIntegerField(default=0)
    
    # Estado booleano (True/False) que indica si este jugador ganó su mapa individual
    won = models.BooleanField(default=False)
    
    # 3. METADATOS Y RESTRICCIONES DE BASE DE DATOS
    class Meta:
        # REGLA DE INTEGRIDAD: Un jugador no puede tener más de un registro de estadísticas para el mismo partido.
        # Evita por completo que el sistema duplique el rendimiento de un jugador en la base de datos.
        unique_together = ('player', 'match')
        
    # 4. MÉTODOS MÁGICOS
    def __str__(self):
        """
        Representación en texto de la fila de estadísticas. Muy descriptiva para depuración.
        Ejemplo: "Stats for Mixwell in match KPI vs KOI... as Jett"
        """
        agent_label = f" as {self.agent_name}" if self.agent_name else ""
        return f"Stats for {self.player.nickname} in match {self.match}{agent_label}"
    
    # 5. LÓGICA DE NEGOCIO (Estadística de Partido)
    def kd_ratio(self):
        """
        Calcula de forma aislada el K/D Ratio del jugador en este mapa específico.
        A diferencia del método del modelo Player, este solo evalúa este encuentro concreto.
        """
        # Control de seguridad: Si el jugador completó el mapa sin morir (0 deaths), evitamos la división por cero.
        if self.deaths == 0:
            # Si tiene kills con 0 muertes, su K/D equivale a sus bajas totales. Si no hizo nada, devuelve 0.0
            return float(self.kills) if self.kills > 0 else 0.0
        
        # Retorna la división matemática estándar de bajas entre muertes redondeada a dos decimales
        return round(self.kills / self.deaths, 2)