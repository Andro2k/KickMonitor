# backend/workers/spotify_worker.py

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict
from contextlib import suppress
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread, QUrl
from PyQt6.QtGui import QDesktopServices
import spotipy
from spotipy.oauth2 import SpotifyOAuth

from backend.utils.logger_text import LoggerText
from backend.utils.paths import get_cache_path

# ==========================================
# CONFIGURACIÓN
# ==========================================
SPOTIFY_SCOPES = "user-read-playback-state user-read-currently-playing user-modify-playback-state"
DEFAULT_PORT = 8888
POLL_INTERVAL_MS = 3000

# =========================================================================
# REGIÓN 1: SERVIDOR LOCAL OAUTH (EJECUTADO EN HILO APARTE)
# =========================================================================
class SpotifyAuthHandler(BaseHTTPRequestHandler):
    """Maneja el callback de Spotify (ej: http://localhost:8888/?code=...)"""   
    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)  
        
        if "code" in params:
            self.server.auth_code = params["code"][0]
            self._respond(AuthTemplates.SUCCESS)          
        elif "error" in params:
            self.server.error_msg = params["error"][0]
            self._respond(AuthTemplates.ERROR)            
        else:
            self.send_error(400, "Solicitud inválida")

    def _respond(self, html_content):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html_content.encode("utf-8"))

class SpotifyLoginThread(QThread):
    """Hilo que levanta el servidor HTTP temporalmente para esperar el login."""
    code_received = pyqtSignal(str)
    error_received = pyqtSignal(str)
    
    def __init__(self, port: int):
        super().__init__()
        self.port = port
        self.server: Optional[HTTPServer] = None
        self._is_running = True

    def run(self):
        try:
            self.server = HTTPServer(('127.0.0.1', self.port), SpotifyAuthHandler)
            self.server.auth_code = None
            self.server.error_msg = None

            self.server.timeout = 1.0 

            while self._is_running and not self.server.auth_code and not self.server.error_msg:
                self.server.handle_request() 
            
            if self.server.auth_code:
                self.code_received.emit(self.server.auth_code)
            elif self.server.error_msg:
                self.error_received.emit(self.server.error_msg)
                
        except Exception as e:
            self.error_received.emit(f"Server Error: {str(e)}")
        finally:
            if self.server: self.server.server_close()

    def stop(self):
        """TRUCO 3: Detención segura de hilos"""
        self._is_running = False
        self.quit()
        self.wait(1000)

# =========================================================================
# REGIÓN 2: WORKER PRINCIPAL (LÓGICA DE NEGOCIO)
# =========================================================================
class SpotifyWorker(QObject):
    track_changed = pyqtSignal(str, str, str, int, int, bool)
    status_msg = pyqtSignal(str)                              
    sig_do_auth = pyqtSignal()
    sig_do_disconnect = pyqtSignal()

    def __init__(self, db_handler):
        super().__init__()
        self.db = db_handler
        self.sp: Optional[spotipy.Spotify] = None
        self.auth_manager: Optional[SpotifyOAuth] = None
        self.is_active = False
        self.login_thread: Optional[SpotifyLoginThread] = None
        
        self.timer = QTimer()
        self.timer.setInterval(POLL_INTERVAL_MS)
        self.timer.timeout.connect(self._poll_current_song)
        
        self.sig_do_auth.connect(self.authenticate)
        self.sig_do_disconnect.connect(self.disconnect)

    # =========================================================================
    # REGIÓN 3: AUTENTICACIÓN Y GESTIÓN DE SESIÓN
    # =========================================================================
    def authenticate(self):
        cid = self.db.get("spotify_client_id")
        secret = self.db.get("spotify_secret")
        uri = self.db.get("spotify_redirect_uri")

        if not cid or not secret:
            self.status_msg.emit(LoggerText.error("Faltan credenciales de Spotify en Ajustes."))
            return

        cache_path = str(Path(get_cache_path()) / ".spotify_cache")

        try:
            self.auth_manager = SpotifyOAuth(
                client_id=cid, client_secret=secret, redirect_uri=uri, 
                scope=SPOTIFY_SCOPES, open_browser=False, cache_path=cache_path 
            )
            if self.auth_manager.get_cached_token():
                self.status_msg.emit(LoggerText.info("Recuperando sesión guardada."))
                self._init_client()
            else:
                self._start_browser_flow(uri)
                
        except Exception as e:
            self.is_active = False
            self.status_msg.emit(LoggerText.error(f"Error Configuración: {e}"))

    def _start_browser_flow(self, uri: str):
        try:
            parsed = urlparse(uri)
            port = parsed.port if parsed.port else DEFAULT_PORT
            
            self.login_thread = SpotifyLoginThread(port)
            self.login_thread.code_received.connect(self._finish_browser_flow)
            self.login_thread.error_received.connect(self._on_auth_error)
            self.login_thread.start()
            
            QDesktopServices.openUrl(QUrl(self.auth_manager.get_authorize_url()))
            self.status_msg.emit(LoggerText.warning("Esperando autorización en el navegador."))
            
        except Exception as e:
            self.status_msg.emit(LoggerText.error(f"Fallo al iniciar flujo web: {e}"))

    def _finish_browser_flow(self, code: str):
        try:
            self.auth_manager.get_access_token(code)
            self._init_client()
        except Exception as e:
            self.status_msg.emit(LoggerText.error(f"Error obteniendo token: {e}"))

    def _on_auth_error(self, error_msg):
        self.is_active = False
        self.status_msg.emit(LoggerText.error(f"Login cancelado o fallido: {error_msg}"))

    def _init_client(self):
        try:
            self.sp = spotipy.Spotify(auth_manager=self.auth_manager)
            user = self.sp.current_user()
            
            self.is_active = True
            self.status_msg.emit(LoggerText.success(f"Spotify Vinculado: {user.get('display_name', 'Usuario')}"))
            
            self.timer.start()
            self._poll_current_song()
            
        except Exception as e:
            self.status_msg.emit(LoggerText.error(f"Error inicializando cliente: {e}"))

    def disconnect(self):
        self.timer.stop()
        self.is_active = False
        self.sp = None
        self.track_changed.emit("Spotify Desconectado", "", "", 0, 100, False)
        self.status_msg.emit(LoggerText.info("Spotify: Sesión cerrada."))

        if self.login_thread: 
            self.login_thread.stop()

    # =========================================================================
    # REGIÓN 4: MONITOREO (POLLING)
    # =========================================================================
    def _poll_current_song(self):
        if not self.sp: return
        try:
            current = self.sp.current_playback()
            if not current:
                self.track_changed.emit("No reproduciendo", "", "", 0, 100, False)
                return

            data = self._parse_track_data(current)
            if data:
                self.track_changed.emit(
                    data['title'], data['artist'], data['art'], 
                    data['progress'], data['duration'], data['is_playing']
                )
        except Exception as e:
            print(f"[DEBUG_SPOTIFY] Error en polling: {e}")

    def _parse_track_data(self, playback_json: Dict) -> Optional[Dict]:
        """Extrae datos limpios del JSON crudo de Spotify."""
        track = (playback_json or {}).get('item')
        if not track: return None
            
        with suppress(Exception):
            artists = ", ".join([a.get('name', '') for a in track.get('artists', [])])
            images = track.get('album', {}).get('images', [])
            
            return {
                'title': track.get('name', 'Desconocido'),
                'artist': artists,
                'art': images[0]['url'] if images else "",
                'progress': playback_json.get('progress_ms', 0),
                'duration': track.get('duration_ms') or 100, 
                'is_playing': playback_json.get('is_playing', False)
            }
        return None

    def get_current_track_text(self) -> str:
        """Devuelve string formateado para uso en chat (Comando !song)."""
        if not self.sp: return "Spotify no conectado."
        with suppress(Exception):
            data = self._parse_track_data(self.sp.current_playback())
            if data and data['is_playing']:
                return f"🎵 Sonando: {data['title']} - {data['artist']}"
        return "🔇 No está sonando nada ahora mismo."

    # =========================================================================
    # REGIÓN 5: CONTROLES DE REPRODUCCIÓN
    # =========================================================================
    def add_to_queue(self, query: str) -> Optional[str]:
        if not self.sp: return None
        try:
            items = self.sp.search(q=query, limit=1, type='track').get('tracks', {}).get('items', [])
            if items:
                track = items[0]
                self.sp.add_to_queue(track['uri'])
                return f"{track.get('name')} - {track['artists'][0]['name']}"
        except Exception as e:
            self.status_msg.emit(LoggerText.warning(f"Error añadiendo a cola: {e}"))
        return None

    def next_track(self):
        with suppress(Exception): self.sp.next_track()
    
    def prev_track(self):
        with suppress(Exception): self.sp.previous_track()

    def play_pause(self):
        with suppress(Exception):
            cur = self.sp.current_playback()
            self.sp.pause_playback() if cur and cur.get('is_playing') else self.sp.start_playback()

# =========================================================================
# REGIÓN 6: RECURSOS ESTÁTICOS (HTML TEMPLATES)
# =========================================================================
class AuthTemplates:
    _CSS = """
        body { background-color: #0b0e0f; color: white; font-family: sans-serif; display: flex; 
               justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .card { background: #1a1d1e; padding: 40px; border-radius: 16px; border: 1px solid #333; 
                text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.5); width: 300px; }
        .btn { background-color: #1DB954; color: black; border: none; padding: 12px 30px; 
               border-radius: 50px; font-weight: bold; cursor: pointer; margin-top: 20px;}
    """
    SUCCESS = f"""
    <!DOCTYPE html><html><head><title>Conectado</title><style>{_CSS}</style></head>
    <body>
        <div class="card">
            <svg width="64" height="64" fill="#1DB954" viewBox="0 0 16 16">
                <path d="M8 0a8 8 0 1 0 0 16A8 8 0 0 0 8 0m3.669 11.538a.5.5 0 0 1-.686.165c-1.879-1.147-4.243-1.407-7.028-.77a.499.499 0 0 1-.222-.973c3.048-.696 5.662-.397 7.77.892a.5.5 0 0 1 .166.686m.979-2.178a.624.624 0 0 1-.858.205c-2.15-1.321-5.428-1.704-7.972-.932a.625.625 0 0 1-.362-1.194c2.905-.881 6.517-.454 8.986 1.063a.624.624 0 0 1 .206.858m.084-2.268C10.154 5.56 5.9 5.419 3.438 6.166a.748.748 0 1 1-.434-1.432c2.825-.857 7.523-.692 10.492 1.07a.747.747 0 1 1-.764 1.288"/>
            </svg>
            <h2 style="color:#1DB954">Conectado</h2>
            <p style="color:#aaa">Spotify vinculado correctamente.</p>
            <button class="btn" onclick="window.close()">CERRAR</button>
            <script>setTimeout(function(){{window.close()}}, 3000);</script>
        </div>
    </body></html>
    """
    ERROR = f"""
    <!DOCTYPE html><html><head><title>Error</title><style>{_CSS}</style></head>
    <body>
        <div class="card">
            <h2 style="color:#ff453a">Error</h2>
            <p style="color:#aaa">No se pudo conectar o acceso denegado.</p>
            <button class="btn" style="background:#ff453a; color:white" onclick="window.close()">CERRAR</button>
        </div>
    </body></html>
    """