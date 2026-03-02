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
        """Asigna puntos por actividad y detecta el rango (rol) en Kick."""
        # 1. Analizar los badges para determinar el rango real
        new_role = "user"
        
        if self.is_bot(user):
            new_role = "bot"
        elif badges:
            # Convertimos a minúsculas para evitar errores de mayúsculas
            badges_lower = [b.lower() for b in badges]
            
            # Orden de jerarquía (de mayor a menor importancia)
            if "broadcaster" in badges_lower or "creator" in badges_lower:
                new_role = "broadcaster"
            elif "moderator" in badges_lower:
                new_role = "moderator"
            elif "vip" in badges_lower:
                new_role = "vip"
            elif "subscriber" in badges_lower or "founder" in badges_lower:
                new_role = "subscriber"

        # 2. Guardar el rol en la base de datos
        self.db.update_user_role(user, new_role)
        
        # 3. Lógica de puntos (los bots y los comandos no dan puntos)
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
        final = message
        ctx = extra_context or {}
        
        # --- Variables de Usuario y Texto ---
        final = final.replace("{user}", user)
        final = final.replace("{input}", args)
        final = final.replace("{target}", args if args else user)
        
        first_arg = args.split(" ")[0] if args else user
        clean_target = first_arg.replace("@", "") # Nombre sin el @
        
        final = final.replace("{arg1}", first_arg)
        final = final.replace("{touser}", clean_target)
        
        # --- Variables de Economía ---
        if "{points}" in final: 
            final = final.replace("{points}", str(self.db.get_points(user)))           
        if "{target_points}" in final:
            # Obtiene los puntos del usuario que fue mencionado en el comando
            final = final.replace("{target_points}", str(self.db.get_points(clean_target)))

        # --- Variables del Canal ---
        if "{streamer}" in final: 
            final = final.replace("{streamer}", self.db.get("kick_username") or "Streamer")
            
        if "{followers}" in final:
            streamer = self.db.get("kick_username")
            followers = 0
            if streamer:
                streamer_data = self.db.get_kick_user(streamer)
                if streamer_data: 
                    followers = streamer_data.get("followers", 0)
            # Formatea con puntos de miles (ej: 1.500)
            final = final.replace("{followers}", "{:,}".format(followers).replace(',', '.'))
            
        # --- Variables de Azar y Juegos ---
        if "{random}" in final: final = final.replace("{random}", str(random.randint(1, 100)))
        if "{coin}" in final: final = final.replace("{coin}", random.choice(["Cara 🌕", "Cruz 🌑"]))
        if "{dice}" in final: final = final.replace("{dice}", str(random.randint(1, 6)))
        if "{8ball}" in final: 
            respuestas = ["Sí.", "No.", "Tal vez.", "Definitivamente.", "No cuentes con ello.", "Pregunta de nuevo más tarde."]
            final = final.replace("{8ball}", random.choice(respuestas))

        # --- Variables de Tiempo ---
        if "{time}" in final: final = final.replace("{time}", datetime.now().strftime("%H:%M"))
        if "{date}" in final: final = final.replace("{date}", datetime.now().strftime("%d/%m/%Y"))
        
        # --- Variables Externas ---
        if "{song}" in final:
            final = final.replace("{song}", ctx.get("song", "Música no disponible"))      
            
        return final