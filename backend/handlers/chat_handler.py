# backend/handlers/chat_handler.py

import re
import random
from datetime import datetime
from typing import List, Dict, Any

class ChatHandler:
    """
    Encargado de procesar, limpiar y formatear los mensajes de chat.
    """
    def __init__(self, db_handler):
        self.db = db_handler        
        self.re_emote = re.compile(r'\[emote:\d+:([^\]]+)\]')
        self.re_emote_clean = re.compile(r'\[emote:\d+:[^\]]+\]')
        self.re_url = re.compile(r'http\S+|www\.\S+') 

    # =========================================================================
    # REGIÓN 1: PARSING Y ANÁLISIS DE ENTRADA
    # =========================================================================
    def should_ignore_user(self, user: str) -> bool:
        """Verifica si el usuario está muteado localmente."""
        return self.db.is_muted(user)

    def is_bot(self, user: str) -> bool:
        u_clean = user.lower().strip()
        if u_clean.startswith("@"): return True         
        return False

    # =========================================================================
    # REGIÓN 2: LÓGICA DE NEGOCIO (PUNTOS Y ECONOMÍA)
    # =========================================================================
    def process_points(self, user: str, msg: str, badges: List[str] = None):
        """Asigna puntos por actividad."""
        # Detectar rol
        new_role = "bot" if self.is_bot(user) else "user"
        self.db.update_user_role(user, new_role)
        
        if new_role == "bot" or msg.startswith("!"):
            return
            
        points = self.db.get_int("points_per_msg", 10)
        self.db.add_points(user, points)

    def distribute_periodic_points(self):
        """Timer: Reparte puntos a usuarios activos recientemente."""
        amount = self.db.get_int("points_per_min", 0)
        if amount > 0:
            self.db.add_points_to_active_users(amount, minutes=10)

    # =========================================================================
    # REGIÓN 3: FORMATO Y SALIDA DE TEXTO
    # =========================================================================
    def clean_for_tts(self, text: str) -> str:
        text = self.re_emote_clean.sub('', text)
        text = self.re_url.sub('un enlace', text)
        return text.strip()

    def format_for_ui(self, content: str) -> str:
        return self.re_emote.sub(r'<span style="color:#888;">(\1)</span>', content)

    def format_custom_message(self, message: str, user: str, args: str, extra_context: Dict[str, Any] = None) -> str:
        # (Este método se mantiene igual que tu versión anterior)
        final = message
        ctx = extra_context or {}
        final = final.replace("{user}", user)
        final = final.replace("{input}", args)
        final = final.replace("{target}", args if args else user)
        
        first_arg = args.split(" ")[0] if args else user
        final = final.replace("{arg1}", first_arg)
        final = final.replace("{touser}", first_arg.replace("@", ""))
        
        if "{points}" in final: 
            final = final.replace("{points}", str(self.db.get_points(user)))           
        if "{streamer}" in final: 
            final = final.replace("{streamer}", self.db.get("kick_username") or "Streamer")
            
        if "{random}" in final: final = final.replace("{random}", str(random.randint(1, 100)))
        if "{coin}" in final: final = final.replace("{coin}", random.choice(["Cara 🌕", "Cruz 🌑"]))
        if "{dice}" in final: final = final.replace("{dice}", str(random.randint(1, 6)))
        if "{time}" in final: final = final.replace("{time}", datetime.now().strftime("%H:%M"))
        
        if "{song}" in final:
            final = final.replace("{song}", ctx.get("song", "Música no disponible"))      
            
        return final