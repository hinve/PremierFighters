from django.core.exceptions import PermissionDenied

def is_admin(user):
    return user.is_authenticated and user.role == 'admin'

def is_coach_or_manager(user):
    return user.is_authenticated and user.role in ['coach', 'manager']

def get_user_team(user):
    if hasattr(user, 'coached_team'):
        return user.coached_team
    elif hasattr(user, 'managed_team'):
        return user.managed_team
    return None

def ensure_can_view_team(user, team):
    if not user.is_authenticated:
        raise PermissionDenied("Necesitas iniciar sesion")
    if is_admin(user):
        return
    my_team = get_user_team(user)
    if my_team and team and my_team.id == team.id:
        return
    raise PermissionDenied("No puedes ver este equipo")


def ensure_can_manage_team(user, team):
    role = (user.role or "").lower()
    if not user.is_authenticated:
        raise PermissionDenied("Necesitas iniciar sesion")
    if is_admin(user):
        return
    if role not in ["coach", "manager"]:
        raise PermissionDenied("Rol sin permisos de gestion")
    my_team = get_user_team(user)
    if my_team and team and my_team.id == team.id:
        return
    raise PermissionDenied("No puedes modificar este equipo")