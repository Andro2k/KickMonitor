# backend/handlers/antibot_handler.py

import re
from typing import Callable
from backend.utils.logger_text import LoggerText

class AntibotHandler:
    """
    Escudo de protección contra ataques de bots.
    """
    def __init__(self, db_handler):
        self.db = db_handler
        self.bot_patterns = [
            re.compile(r"^[a-z]{8,}\d{3,}!$"),
            re.compile(r"^[a-z]{18,}\d*$")
        ]

    def check_user(self, username: str, 
                   ban_callback: Callable[[str], None], 
                   log_callback: Callable[[str], None]) -> bool:
        """
        Verifica el nombre de usuario. Si coincide con un patrón de bot, lo banea.
        """  
        if self.db.get("antibot_active") == "1":
            return False

        # Verificación de Patrones
        for pattern in self.bot_patterns:
            if pattern.match(username):
                try:
                    ban_callback(username)
                    log_callback(LoggerText.warning(f"🛡️ Antibot: {username} detectado y BANEADO."))
                    return True
                except Exception as e:
                    log_callback(LoggerText.error(f"🛡️ Error al banear bot {username}: {e}"))
                    
        return False