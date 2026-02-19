# backend/core/kick/chat_manager.py

import json
import aiohttp
from datetime import datetime
from backend.utils.logger_text import LoggerText

class KickChatManager:
    def __init__(self, http_session, loop, log_callback, chat_callback):
        self.session = http_session
        self.loop = loop
        self.log = log_callback
        self.emit_chat = chat_callback
        self.ws_connection = None
        self.is_running = True
        
        self.pusher_key = "32cbd69e4b950bf97679"
        self.pusher_cluster = "us2"

    async def connect(self, chatroom_id, username):
        if not chatroom_id: 
            self.log(LoggerText.error("Error Fatal: Chatroom ID no encontrado."))
            return False
            
        self.log(LoggerText.debug(f"Conectando a sala de chat: {chatroom_id}"))
        pusher_url = f"wss://ws-{self.pusher_cluster}.pusher.com/app/{self.pusher_key}?protocol=7&client=js&version=7.6.0&flash=false"

        try:
            self.ws_connection = await self.session.ws_connect(pusher_url)
            subscribe_msg = {
                "event": "pusher:subscribe",
                "data": {"auth": "", "channel": f"chatrooms.{chatroom_id}.v2"}
            }
            await self.ws_connection.send_json(subscribe_msg)
            
            self.loop.create_task(self._listen())
            self.log(LoggerText.success(f"CHAT CONECTADO: {username}"))
            return True
        except Exception as e:
            self.log(LoggerText.error(f"Fallo conexión WebSocket nativa: {e}"))
            return False

    async def _listen(self):
        try:
            async for msg in self.ws_connection:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    # --- NUEVO: Manejar el ping de Pusher ---
                    if data.get("event") == "pusher:ping":
                        await self.ws_connection.send_json({
                            "event": "pusher:pong",
                            "data": {}
                        })
                        continue
                    # ----------------------------------------
                    if data.get("event") == "App\\Events\\ChatMessageEvent":
                        self._parse_message(json.loads(data.get("data", "{}")))
                elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                    break
        except Exception as e:
            if self.is_running:
                self.log(LoggerText.error(f"Error procesando WebSocket: {e}"))
        finally:
            self.log(LoggerText.warning("Conexión WebSocket cerrada."))

    def _parse_message(self, chat_data):
        try:
            content = chat_data.get('content', '')
            if not content: return
            
            sender_info = chat_data.get('sender', {})
            sender = sender_info.get('username', 'Desconocido')
            badges = [b.get('type') for b in sender_info.get('identity', {}).get('badges', []) if isinstance(b, dict)]
            timestamp = datetime.now().strftime("%H:%M:%S")

            self.emit_chat(sender, content, badges, timestamp)
        except Exception as e:
            self.log(LoggerText.error(f"Error parseando mensaje: {e}"))

    async def disconnect(self):
        self.is_running = False
        if self.ws_connection and not self.ws_connection.closed:
            await self.ws_connection.close()