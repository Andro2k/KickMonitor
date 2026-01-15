# backend/utils/logger.py
from datetime import datetime

class Log:
    # --- NUEVA VARIABLE GLOBAL DE CONTROL ---
    enabled_debug = False 

    # Paleta de colores (estilo Terminal Dark)
    COLORS = {
        "INFO": "#29b6f6",    # Azul claro
        "SUCCESS": "#66bb6a", # Verde suave
        "WARNING": "#ffa726", # Naranja
        "ERROR": "#ef5350",   # Rojo suave
        "DEBUG": "#bdbdbd",   # Gris
        "SYSTEM": "#ab47bc"   # Morado
    }

    @staticmethod
    def _format(level, message):
        """Genera el string HTML con el formato [LEVEL] Mensaje"""
        color = Log.COLORS.get(level, "#ffffff")
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        return (
            f'<span style="color:#555;">{timestamp}</span> '
            f'<span style="color:{color}; font-weight:bold;">[{level}]</span> '
            f'<span style="color:#ddd;">{message}</span>'
        )

    # --- MÉTODOS ESTÁNDAR ---
    @staticmethod
    def info(msg): return Log._format("INFO", msg)

    @staticmethod
    def success(msg): return Log._format("SUCCESS", msg)

    @staticmethod
    def warning(msg): return Log._format("WARNING", msg)

    @staticmethod
    def error(msg): return Log._format("ERROR", msg)

    @staticmethod
    def system(msg): return Log._format("SYSTEM", msg)

    # --- MÉTODO DEBUG FILTRADO ---
    @staticmethod
    def debug(msg):
        if Log.enabled_debug:
            return Log._format("DEBUG", msg)
        return None