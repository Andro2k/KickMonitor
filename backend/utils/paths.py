import os
import sys

APP_NAME = "KickMonitor"

def get_app_data_path():
    """
    Devuelve la ruta absoluta a %LOCALAPPDATA%/KickMonitor
    Asegura que la carpeta exista.
    """
    if getattr(sys, 'frozen', False):
        # Modo EXE (Instalado)
        base_path = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), APP_NAME)
    else:
        # Modo DEV (Código fuente)
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Opcional: Si quieres probar en DEV como si fuera PROD, usa la línea del EXE también.

    if not os.path.exists(base_path):
        os.makedirs(base_path, exist_ok=True)
        
    return base_path

def get_resource_path(filename):
    """Ayuda a obtener rutas dentro del EXE para iconos/imágenes (lectura)"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.abspath("."), filename)