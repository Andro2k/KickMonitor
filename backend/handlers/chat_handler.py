# backend/handlers/chat_handler.py

import ast
import re
import json
import random
from datetime import datetime
from typing import Tuple, List, Dict, Any

class ChatHandler:
    """
    Encargado de procesar, limpiar y formatear los mensajes de chat.
    No maneja conexiones, solo lógica de texto y datos.
    """
    def __init__(self, db_handler):
        self.db = db_handler        
        # Regex precompilados para rendimiento
        # Captura el nombre del emote: [emote:123:pepe] -> pepe
        self.re_emote = re.compile(r'\[emote:\d+:([^\]]+)\]')
        # Captura todo el bloque del emote para borrarlo
        self.re_emote_clean = re.compile(r'\[emote:\d+:[^\]]+\]')
        # Detectar URLs
        self.re_url = re.compile(r'http\S+|www\.\S+') 

    # =========================================================================
    # REGIÓN 1: PARSING Y ANÁLISIS DE ENTRADA
    # =========================================================================
    def parse_message(self, raw_msg: Any) -> Tuple[str, str, List[str]]:
        """
        Normaliza el mensaje entrante (que puede ser dict, json string o python string).
        Retorna: (username, content, badges)
        """
        data = {}
        
        # 1. Si ya es un diccionario (Ideal)
        if isinstance(raw_msg, dict):
            data = raw_msg
        # 2. Si es string, intentar decodificar
        elif isinstance(raw_msg, str):
            s_msg = raw_msg.strip()
            # Intento A: JSON Estándar
            try: 
                data = json.loads(s_msg)
            except json.JSONDecodeError:
                # Intento B: String de Python (ej: "{'key': 'val'}")
                try: 
                    if s_msg.startswith("{"): 
                        data = ast.literal_eval(s_msg)
                except: 
                    pass
        # 3. Extracción de datos normalizados
        if data:
            # Buscamos en varias llaves posibles por inconsistencias de API
            user = data.get("sender_username") or data.get("username") or "Desconocido"
            content = data.get("content") or data.get("message") or ""
            badges = data.get("badges", [])           
            # Normalizar badges (si vienen como lista de objetos, sacar solo el tipo)
            if badges and isinstance(badges, list) and len(badges) > 0 and isinstance(badges[0], dict):
                badges = [b.get('type', '') for b in badges if isinstance(b, dict)]           
            return user, content, badges
        # 4. Fallback (Formato antiguo separado por |||)
        s_msg = str(raw_msg)
        if "|||" in s_msg:
            parts = s_msg.split("|||", 1)
            return parts[0].strip(), parts[1].strip(), []
            
        return "Desconocido", s_msg, []

    def should_ignore_user(self, user: str) -> bool:
        """Verifica si el usuario está muteado localmente."""
        return self.db.is_muted(user)

    def is_bot(self, user: str) -> bool:
        """Detecta si es un bot del sistema (ej: @StreamElements o kicklet)."""
        return self._detect_role(user) == "bot"

    def _detect_role(self, user: str) -> str:
        """Determina rol basado en nomenclatura (@Bot)."""
        u_clean = user.lower().strip()
        if u_clean.startswith("@") or u_clean == "kicklet":
            return "bot"
        return "user"

    # =========================================================================
    # REGIÓN 2: LÓGICA DE NEGOCIO (PUNTOS Y ECONOMÍA)
    # =========================================================================
    def process_points(self, user: str, msg: str, badges: List[str] = None):
        """Asigna puntos por actividad en chat."""
        # 1. Actualizar rol en DB (Para saber que el usuario existe)
        new_role = self._detect_role(user)
        self.db.update_user_role(user, new_role)
        # 2. Reglas de Exclusión
        if new_role == "bot":
            return       
        # Comandos no ganan puntos
        if msg.startswith("!"):
            return
        # 3. Asignar Puntos
        points_to_add = self.db.get_int("points_per_msg", 10)
        self.db.add_points(user, points_to_add)

    def distribute_periodic_points(self):
        """Timer: Reparte puntos a usuarios activos recientemente."""
        amount = self.db.get_int("points_per_min", 0)
        if amount > 0:
            # Ventana de actividad: últimos 10 minutos
            self.db.add_points_to_active_users(amount, minutes=10)

    # =========================================================================
    # REGIÓN 3: FORMATO Y SALIDA DE TEXTO
    # =========================================================================
    def clean_for_tts(self, text: str) -> str:
        """Limpia el texto para que la voz robótica no lea basura."""
        # 1. Quitar emotes completos
        text = self.re_emote_clean.sub('', text)
        # 2. Quitar URLs (reemplazar por texto legible)
        text = self.re_url.sub('un enlace', text)
        return text.strip()

    def format_for_ui(self, content: str) -> str:
        """Convierte códigos de emotes a HTML para la UI."""
        # Transformar [emote:id:name] -> (name) en gris
        return self.re_emote.sub(r'<span style="color:#888;">(\1)</span>', content)

    def format_custom_message(self, message: str, user: str, args: str, extra_context: Dict[str, Any] = None) -> str:
        """Reemplaza variables {placeholders} en comandos personalizados."""
        final = message
        ctx = extra_context or {}
        # 1. Variables de Usuario e Input
        final = final.replace("{user}", user)
        final = final.replace("{input}", args)
        final = final.replace("{target}", args if args else user)       
        # 2. Argumentos específicos (ej: !abrazo @Pedro)
        first_arg = args.split(" ")[0] if args else user
        final = final.replace("{arg1}", first_arg)
        final = final.replace("{touser}", first_arg.replace("@", ""))
        # 3. Variables de Base de Datos
        if "{points}" in final: 
            final = final.replace("{points}", str(self.db.get_points(user)))           
        if "{streamer}" in final: 
            final = final.replace("{streamer}", self.db.get("kick_username") or "Streamer")
        # 4. Aleatoriedad y Tiempo
        if "{random}" in final: final = final.replace("{random}", str(random.randint(1, 100)))
        if "{coin}" in final: final = final.replace("{coin}", random.choice(["Cara 🌕", "Cruz 🌑"]))
        if "{dice}" in final: final = final.replace("{dice}", str(random.randint(1, 6)))
        if "{time}" in final: final = final.replace("{time}", datetime.now().strftime("%H:%M"))
        # 5. Contexto Externo (Spotify, YouTube, etc.)
        if "{song}" in final:
            final = final.replace("{song}", ctx.get("song", "Música no disponible"))      
        return final