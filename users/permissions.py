from django.core.exceptions import PermissionDenied

# ==============================================================================
# FUNCIONES BOOLEANAS DE VERIFICACIÓN (Predicados de Rol)
# ==============================================================================

def is_admin(user):
    """Comprueba de forma segura si el usuario está logueado y ostenta el rol de Administrador."""
    return user.is_authenticated and user.role == 'admin'


def is_coach_or_manager(user):
    """Comprueba si el usuario está logueado y pertenece al cuerpo técnico o directiva."""
    return user.is_authenticated and user.role in ['coach', 'manager']


# ==============================================================================
# FUNCIÓN DE EXTRACCIÓN DE CONTEXTO (Búsqueda por Relación Inversa)
# ==============================================================================
def get_user_team(user):
    """
    Inspecciona dinámicamente el perfil del usuario para localizar su club asignado.
    Utiliza las relaciones inversas (related_name) definidas en el modelo Team.
    """
    # Si el usuario está enlazado como Coach en algún equipo, lo devuelve
    if hasattr(user, 'coached_team'):
        return user.coached_team
    # Si no, comprueba si está enlazado como Mánager/Director
    elif hasattr(user, 'managed_team'):
        return user.managed_team
    # Si el usuario no tiene ningún club asignado todavía, retorna None
    return None


# ==============================================================================
# MIDDLEWARE/GUARDAS DE SEGURIDAD INTERNA (Disparadores de Excepciones)
# ==============================================================================

def ensure_can_view_team(user, team):
    """
    Guarda de seguridad para control de lectura. 
    Lanza una excepción HTTP 403 (PermissionDenied) si el usuario intenta espiar un club ajeno.
    """
    # 1. Control de Autenticación: Si es un usuario anónimo, rebota la petición
    if not user.is_authenticated:
        raise PermissionDenied("Necesitas iniciar sesion")
    
    # 2. Superusuario: Si es admin global, se salta los bloqueos y continúa la ejecución
    if is_admin(user):
        return
    
    # 3. Control de pertenencia: Extrae su equipo y verifica que coincida con el solicitado
    my_team = get_user_team(user)
    if my_team and team and my_team.id == team.id:
        return # Acceso permitido: El usuario pertenece al staff de este equipo
    
    # Si no cumple ninguna condición, bloquea el acceso de forma fulminante
    raise PermissionDenied("No puedes ver este equipo")


def ensure_can_manage_team(user, team):
    """
    Guarda de seguridad estricta para control de escritura (Creación, Edición y Borrado).
    Blinda el backend contra modificaciones ilegítimas de datos.
    """
    role = (user.role or "").lower()
    
    # 1. Control de Autenticación
    if not user.is_authenticated:
        raise PermissionDenied("Necesitas iniciar sesion")
    
    # 2. Superusuario: Permiso total garantizado para los administradores de la plataforma
    if is_admin(user):
        return
    
    # 3. Control de Rol Jerárquico: Aunque esté en su equipo, un usuario con rol 'player' no puede editar
    if role not in ["coach", "manager"]:
        raise PermissionDenied("Rol sin permisos de gestion")
    
    # 4. Control de pertenencia de Club: Evita que un Coach del Equipo A modifique datos del Equipo B
    my_team = get_user_team(user)
    if my_team and team and my_team.id == team.id:
        return # Acceso permitido: El usuario es personal autorizado del equipo
    
    raise PermissionDenied("No puedes modificar este equipo")