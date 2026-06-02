from django.db import models
from teams.models import Team

# Definición del modelo Player que representará a los jugadores en la base de datos
class Player(models.Model):
    
    # 1. CAMPOS DE DETALLE DEL JUGADOR
    # El Nickname/ID en juego del jugador (ej: 'Mixwell'). Es único para evitar duplicados en la plataforma
    nickname = models.CharField(max_length=50, unique=True)
    
    # Nombre real completo del jugador (ej: 'Oscar Cañellas')
    real_name = models.CharField(max_length=100, blank=True)
    
    # País de origen o nacionalidad del jugador (útil para estadísticas de región)
    country = models.CharField(max_length=50, blank=True)
    
    # Rol o posición táctica dentro de Valorant (ej: 'Duelista', 'IGL', 'Initiator', 'Sentinel')
    role_in_game = models.CharField(max_length=50, blank=True)
    
    # 2. RELACIONES ENTRE TABLAS (CLAVES FORÁNEAS)
    # Relación de muchos a uno con el modelo Team. Cada jugador pertenece a un único equipo.
    # Si el equipo se borra, el jugador se elimina automáticamente de la base de datos (CASCADE)
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='players'              # Permite consultar los jugadores desde el equipo (ej: team.players.all())
    )
    
    # Guarda la fecha y hora exacta de cuándo se dio de alta al jugador en el sistema de manera automática
    created_at = models.DateTimeField(auto_now_add=True)
    
    # 3. MÉTODOS MÁGICOS
    def __str__(self):
        """
        Define la representación en texto del objeto Jugador.
        Muestra el nickname acompañado del TAG/Siglas abreviadas del club si está asignado.
        Ejemplo de salida: "Mixwell (KOI)" o "Mixwell (No Team)"
        """
        return f"{self.nickname} ({self.team.tag if self.team else 'No Team'})"
    
    # 4. MÉTODOS DE LÓGICA DE NEGOCIO (Métricas de Rendimiento)
    def calculate_kd_ratio(self):
        """
        Calcula de forma dinámica el K/D Ratio total (Asesinatos / Muertes) 
        del jugador acumulado a lo largo de todas las partidas finalizadas.
        """
        # Importaciones locales (Lazy Imports) para evitar problemas de importación circular en Django
        from matches.models import Match
        from stats.models import PlayerMatchStats
        
        # Obtiene todas las estadísticas de este jugador correspondientes a partidos ya resueltos (Win o Loss)
        stats = PlayerMatchStats.objects.filter(
            player=self,
            match__result__in=[Match.ResultType.WIN, Match.ResultType.LOSS],
        )
        
        # Suma todos los asesinatos (kills) y muertes (deaths) registrados en esas filas
        total_kills = sum(s.kills for s in stats)
        total_deaths = sum(s.deaths for s in stats)
        
        # Control de seguridad: Evita errores informáticos al dividir por cero si el jugador no ha muerto
        if total_deaths == 0:
            # Si tiene bajas pero 0 muertes, su K/D equivale al número de bajas. Si no tiene nada, devuelve 0.0
            return float(total_kills) if total_kills > 0 else 0.0
        
        # Retorna el ratio matemático final redondeado a dos decimales
        return round(total_kills / total_deaths, 2)
    
    def calculate_winrate(self):
        """
        Calcula de forma dinámica el porcentaje de victoria (Winrate) del jugador, 
        basándose en la cantidad de mapas en los que ha participado y han terminado en victoria.
        """
        from matches.models import Match
        from stats.models import PlayerMatchStats
        
        # Obtiene el set de estadísticas del jugador de partidos resueltos
        stats = PlayerMatchStats.objects.filter(
            player=self,
            match__result__in=[Match.ResultType.WIN, Match.ResultType.LOSS],
        )
        # Cuenta la cantidad total de mapas/partidos disputados por el jugador
        total_maps = stats.count()
        
        # Control de seguridad: Si no ha jugado partidos todavía, su porcentaje de victoria es cero
        if total_maps == 0:
            return 0.0
        
        # Cuenta en cuántas de esas filas su respectivo partido terminó en Victoria
        wins = stats.filter(match__result=Match.ResultType.WIN).count()
        
        # Aplica la fórmula matemática del porcentaje: (Victorias / Partidos Totales) * 100
        return round((wins / total_maps) * 100, 1) if total_maps > 0 else 0.0