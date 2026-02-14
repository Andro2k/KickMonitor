# backend/workers/chat_overlay_worker.py

import os
import json
import asyncio
from aiohttp import web, WSMsgType
from PyQt6.QtCore import QObject, pyqtSignal, QThread

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML_CHAT_PATH = os.path.join(BASE_DIR, "overlays", "chat_overlay.html")

class ChatOverlayWorker(QObject):
    service_started = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, port=6001):
        super().__init__()
        self.port = port
        self.app = web.Application()
        
        self.app.router.add_get('/chat', self.chat_overlay_handler)
        self.app.router.add_get('/ws', self.websocket_handler)

        self.runner = None
        self.site = None
        self.clients = set()
        self.loop = None
        self.thread = None
        
        # --- NUEVO: Memoria para guardar la última configuración ---
        self.latest_config = {} 

    def start(self):
        self.thread = QThread()
        self.moveToThread(self.thread)
        self.thread.started.connect(self._run_server)
        self.thread.start()

    def _run_server(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._start_aiohttp())
            self.loop.run_forever()
        except Exception as e:
            self.error_occurred.emit(f"Error en servidor Chat Overlay: {e}")
        finally:
            self.loop.run_until_complete(self._stop_aiohttp())
            self.loop.close()

    async def _start_aiohttp(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, '127.0.0.1', self.port)
        await self.site.start()
        self.service_started.emit(f"Servidor Chat Overlay iniciado en http://localhost:{self.port}/chat")

    async def _stop_aiohttp(self):
        if self.site: await self.site.stop()
        if self.runner: await self.runner.cleanup()

    def stop(self):
        if self.loop: self.loop.call_soon_threadsafe(self.loop.stop)
        if self.thread: self.thread.quit(); self.thread.wait()

    async def chat_overlay_handler(self, request):
        try:
            with open(HTML_CHAT_PATH, 'r', encoding='utf-8') as f:
                return web.Response(text=f.read(), content_type='text/html')
        except FileNotFoundError:
            return web.Response(text=f"Error: No se encontró el archivo {HTML_CHAT_PATH}", status=404)

    async def websocket_handler(self, request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.clients.add(ws)
        
        # --- NUEVO: Si OBS se recarga, le enviamos la configuración al instante ---
        if self.latest_config:
            payload = {
                "type": "update_chat_styles",
                "payload": self.latest_config
            }
            await ws.send_str(json.dumps(payload))
        # -------------------------------------------------------------------------
            
        try:
            async for msg in ws:
                if msg.type == WSMsgType.ERROR:
                    print(f'WS cerrado con excepción: {ws.exception()}')
        finally:
            self.clients.remove(ws)
        return ws

    async def broadcast_data(self, data_dict):
        if not self.clients: return
        message = json.dumps(data_dict)
        tasks = [asyncio.create_task(ws.send_str(message)) for ws in self.clients if not ws.closed]
        if tasks: await asyncio.wait(tasks)

    def send_chat_message_to_overlay(self, sender, content, badges=None, user_color=None, timestamp=""):
        if not self.loop: return
        payload = {
            "type": "new_message",
            "payload": {
                "sender": sender, "content": content,
                "badges": badges or [], "color": user_color, "timestamp": timestamp
            }
        }
        asyncio.run_coroutine_threadsafe(self.broadcast_data(payload), self.loop)

    def update_chat_styles(self, style_dict):
        if not self.loop: return
        
        # --- NUEVO: Actualizar la memoria con la última configuración ---
        self.latest_config.update(style_dict)
        
        payload = {
            "type": "update_chat_styles",
            "payload": style_dict
        }
        asyncio.run_coroutine_threadsafe(self.broadcast_data(payload), self.loop)