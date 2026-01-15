# backend/handlers/antibot_handler.py

import re
from typing import Callable
from backend.utils.logger import Log

class AntibotHandler:
    """
    Escudo de protección contra ataques de bots.
    """
    
    def __init__(self, db_handler):
        self.db = db_handler
        self.bot_patterns = [
            # CASO 1: Ataque específico reportado (Ej: qedngkmjqgppmk7201!)
            # ^[a-z]{8,}  -> Empieza con 8 o más letras minúsculas
            # \d{3,}      -> Sigue con 3 o más números
            # !$          -> Termina estrictamente con un signo de exclamación
            re.compile(r"^[a-z]{8,}\d{3,}!$"),
            re.compile(r"^[a-z]{18,}\d*$")
        ]

    def check_user(self, username: str, 
                   ban_callback: Callable[[str], None], 
                   log_callback: Callable[[str], None]) -> bool:
        """
        Verifica el nombre de usuario. Si coincide con un patrón de bot, lo banea.
        """  
        # Permitimos apagar el antibot desde ajustes si fuera necesario (por defecto "1")
        if self.db.get("antibot_active") == "1":
            return False

        # Verificación de Patrones
        for pattern in self.bot_patterns:
            if pattern.match(username):
                try:
                    # 1. Ejecutar el Ban (Usando la función que pasa el Controller)
                    ban_callback(username)              
                    # 2. Registrar el evento
                    log_callback(Log.warning(f"🛡️ Antibot: {username} detectado y BANEADO."))
                    return True
                except Exception as e:
                    log_callback(Log.error(f"🛡️ Error al banear bot {username}: {e}"))
                    
        return False