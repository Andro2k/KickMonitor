# backend/utils/paths.py
import os
import sys

APP_NAME = "KickMonitor"

def get_base_folder():
    """
    Determina la carpeta raíz donde se guardarán los datos.
    - Modo EXE: %LOCALAPPDATA%/KickMonitor
    - Modo DEV: Carpeta raíz del proyecto
    """
    if getattr(sys, 'frozen', False):
        # Modo EXE (Instalado)
        base = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), APP_NAME)
    else:
        # Modo DEV (Código fuente)
        # Sube 2 niveles desde backend/utils/paths.py para llegar a la raíz
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    if not os.path.exists(base):
        os.makedirs(base, exist_ok=True)
        
    return base

def get_app_data_path():
    return get_base_folder()

def get_config_path():
    """Retorna la ruta a la carpeta /config (creándola si no existe)"""
    path = os.path.join(get_base_folder(), "config")
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    return path

def get_cache_path():
    """Retorna la ruta a la carpeta /cache (creándola si no existe)"""
    path = os.path.join(get_base_folder(), "cache")
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    return path

def get_resource_path(filename):
    """Ayuda a obtener rutas dentro del EXE para iconos/imágenes (lectura)"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.abspath("."), filename)