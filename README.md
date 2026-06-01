# PremierFighters

Aplicación Django para gestionar equipos, jugadores y partidos (TFG).

---

## Resumen

PremierFighters es una pequeña plataforma para registrar equipos, jugadores, partidos y estadísticas (K/D, winrate, etc.). Este README explica cómo configurar el entorno, ejecutar la aplicación y ejecutar los tests automatizados para la entrega del TFG.

---

## Requisitos

- Python 3.12
- Virtual environment (venv)
- SQLite (incluido por defecto)

---

## Instalación y configuración (Windows - PowerShell)

1. Clonar el repositorio y situarse en la carpeta del proyecto:

```powershell
git clone <tu-repo-url> PremierFighters
cd PremierFighters
```

2. Crear y activar entorno virtual:

```powershell
python -m venv venv
venv\Scripts\activate
```

3. Instalar dependencias:

```powershell
pip install -r requirements.txt
```

Si no tienes `requirements.txt`, instálalo con:

```powershell
pip install Django
pip freeze > requirements.txt
```

4. Variables de entorno:

- Copia `.env.example` (si existe) o crea `.env` en la raíz del proyecto. Valores mínimos:

```
SECRET_KEY=tu_secret_key
DEBUG=True
# RIOT_API_KEY=...  # eliminar o comentar si no se usa
```

NO subas `.env` al repositorio.

5. Migraciones y superuser:

```powershell
python manage.py migrate
python manage.py createsuperuser
```

6. Ejecutar el servidor localmente:

```powershell
python manage.py runserver
```

Abrir `http://127.0.0.1:8000/` en el navegador.

---

## Documentación automática en `localhost/docs`

Se ha habilitado **Django Admin Docs** para tener documentación navegable desde el propio proyecto.

1. Aplica migraciones y crea un superusuario (si no lo tienes):

```powershell
python manage.py migrate
python manage.py createsuperuser
```

2. Arranca el servidor:

```powershell
python manage.py runserver
```

3. Abre:

- `http://127.0.0.1:8000/docs/` (documentación)
- `http://127.0.0.1:8000/admin/` (panel admin)

> La documentación de `/docs/` requiere iniciar sesión con un usuario con permisos de staff/admin.

---

## Despliegue de la web (resumen rápido)

Para desplegar la aplicación en un hosting (Render, Railway, VPS, etc.):

1. Configura variables de entorno en producción:
   - `DEBUG=False`
   - `SECRET_KEY=<valor-seguro>`
   - `ALLOWED_HOSTS=<tu-dominio>`
2. Ejecuta migraciones en el servidor:

```bash
python manage.py migrate
```

3. Lanza la app con un servidor WSGI (por ejemplo `gunicorn`) detrás de un proxy (Nginx o similar).

---

## Tests automatizados

Se han añadido tests básicos para `players` que cubren la vista `player_detail`.

Ejecutar todos los tests:

```powershell
python manage.py test
```

Ejecutar sólo los tests de `players`:

```powershell
python manage.py test players
```
