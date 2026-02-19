# backend/core/kick/api_manager.py

import cloudscraper
from backend.utils.logger_text import LoggerText

class KickAPIManager:
    def __init__(self, auth_manager, http_session, loop, db, config, log_callback, user_info_signal):
        self.auth = auth_manager
        self.session = http_session
        self.loop = loop
        self.db = db
        self.config = config
        self.log = log_callback
        self.user_info_signal = user_info_signal
        self.scraper = cloudscraper.create_scraper()
        
        self.chatroom_id = str(self.config.get('chatroom_id', ''))
        self.broadcaster_user_id = None

    async def detect_user_and_channel(self):
        target_user = self.config.get('kick_username') 
        
        if not target_user:
            self.log(LoggerText.info("Detectando usuario de Kick automáticamente..."))
            target_user = await self._get_authenticated_user()
            if not target_user:
                self.log(LoggerText.error("No se pudo detectar el usuario de Kick."))
                return False

        safe_slug = target_user.strip().replace(" ", "-").replace("_", "-")

        self.log(LoggerText.info(f"Cargando datos para el canal: {safe_slug}"))
        
        # Usamos el safe_slug para buscar la información
        if self._load_from_cache(safe_slug) or await self._fetch_channel_data(safe_slug):
            self.config['kick_username'] = safe_slug
            self.db.set("kick_username", safe_slug)
            return True
            
        return False

    async def _get_authenticated_user(self):
        headers = {"Authorization": f"Bearer {self.auth.access_token}", "Accept": "application/json"}
        try:
            async with self.session.get("https://api.kick.com/public/v1/users", headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    lista = data.get("data", [])
                    user = lista[0] if isinstance(lista, list) and lista else data
                    return user.get("slug") or user.get("name") or user.get("username")
                else:
                    self.log(LoggerText.warning(f"Fallo al autodetectar usuario. API Pública devolvió HTTP {resp.status}"))
        except Exception as e:
            self.log(LoggerText.error(f"Error detectando usuario: {e}"))
        return None

    async def _fetch_channel_data(self, target_user):
        try:
            headers = {"Authorization": f"Bearer {self.auth.access_token}"} if self.auth.access_token else {}
            resp = await self.loop.run_in_executor(
                None, lambda: self.scraper.get(f"https://kick.com/api/v1/channels/{target_user}", headers=headers)
            )
            if resp.status_code == 200:
                self._process_channel_response(resp.json(), target_user)
                return True
            else:
                self.log(LoggerText.error(f"Error API: Código {resp.status_code} al buscar {target_user}"))
                self.log(LoggerText.error(f"Respuesta de Kick: {resp.text[:100]}"))
                
        except Exception as e: 
            self.log(LoggerText.error(f"Error obteniendo datos del canal: {e}"))
        return False

    def _process_channel_response(self, data, target_user):
        if 'chatroom' in data and 'id' in data['chatroom']:
            self.chatroom_id = str(data['chatroom']['id'])
            self.db.set("chatroom_id", self.chatroom_id)
        else:
            self.log(LoggerText.warning("⚠️ La respuesta de Kick no incluyó un ID de sala de chat (chatroom_id)."))
        uid = data.get('user_id') or data.get('id') or data.get('user', {}).get('id')
        if uid: self.broadcaster_user_id = uid

        username = data.get('username') or data.get('user', {}).get('username') or target_user
        slug = data.get('slug') or target_user
        pic = data.get('profile_pic') or data.get('user', {}).get('profile_pic') or ""
        followers = data.get('followersCount') or data.get('followers_count') or 0

        self.db.save_kick_user(slug, username, followers, pic, self.chatroom_id, self.broadcaster_user_id)
        self.user_info_signal.emit(username, followers, pic)
        self.log(LoggerText.success(f"Datos actualizados para: {username}"))

    def _load_from_cache(self, target_user):
        cached = self.db.get_kick_user(target_user)
        if cached and cached.get('user_id'):
            self.broadcaster_user_id = cached['user_id']
            chat_id_db = self.db.get("chatroom_id")
            if chat_id_db:
                self.chatroom_id = chat_id_db
                self.log(LoggerText.success(f"Datos cargados rápidamente desde la base de datos para: {target_user}"))
                return True
        return False

    async def send_message(self, text, retry=True):
        if not self.auth.access_token: 
            self.log(LoggerText.warning("No se puede enviar el mensaje: Falta el token de acceso."))
            return
            
        if not self.broadcaster_user_id:
            self.log(LoggerText.error("No se puede enviar el mensaje: Falta el ID del canal (broadcaster_user_id)."))
            return
        headers = { "Authorization": f"Bearer {self.auth.access_token}", "Content-Type": "application/json" }
        payload = { "broadcaster_user_id": int(self.broadcaster_user_id), "content": text, "type": "bot" }
        try:
            async with self.session.post("https://api.kick.com/public/v1/chat", json=payload, headers=headers) as resp:
                if resp.status == 401 and retry:
                    self.log(LoggerText.warning("Token expirado al enviar. Renovando."))
                    if await self.auth.refresh_token_silently():
                        await self.send_message(text, retry=False)
                elif resp.status != 200:
                    self.log(LoggerText.error(f"Error enviando mensaje: Status {resp.status}"))
        except Exception as e:
            self.log(LoggerText.error(f"Excepción al enviar mensaje: {e}"))