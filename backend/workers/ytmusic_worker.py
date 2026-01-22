# backend/workers/ytmusic_worker.py

import vlc
import yt_dlp
from ytmusicapi import YTMusic
import time
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QMutex, QMutexLocker

# 1. IMPORTAMOS LA CLASE LOG
from backend.utils.logger import Log 

class YTMusicWorker(QObject):
    # Señales para comunicar con la UI y el Controller
    sig_log = pyqtSignal(str)              # Para logs
    sig_now_playing = pyqtSignal(str)      # Para actualizar UI con canción actual
    sig_queue_changed = pyqtSignal(list)   # Para mostrar la cola
    sig_error = pyqtSignal(str)            # Para errores

    def __init__(self):
        super().__init__()
        self._is_active = False
        self.queue = []
        self.current_song = None
        self.mutex = QMutex()
        
        # Instancia VLC
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        self.event_manager = self.player.event_manager()
        
        # Timer para chequear si la canción terminó
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self._check_playback_status)
        self.check_timer.setInterval(1000)

        # API Youtube
        try:
            self.yt = YTMusic("headers_auth.json") 
        except:
            self.yt = YTMusic() 

    def set_active(self, active: bool):
        """Activa o desactiva este sistema"""
        self._is_active = active
        if not active:
            self.stop()
        else:
            self.check_timer.start()

    def get_current_track_text(self) -> str:
        if self.current_song:
            return f"{self.current_song['title']} - {self.current_song['artist']}"
        return "Nada sonando (YTMusic)"

    def add_to_queue(self, query: str) -> str:
        """Busca y añade a la cola. Retorna el nombre de la canción o None."""
        try:
            results = self.yt.search(query, filter="songs", limit=1)
            if not results:
                return None

            track = results[0]
            info = {
                'videoId': track['videoId'],
                'title': track['title'],
                'artist': track['artists'][0]['name'] if track['artists'] else "Desconocido"
            }

            with QMutexLocker(self.mutex):
                self.queue.append(info)
                # Si no hay nada sonando, reproducir inmediatamente
                if not self.player.is_playing() and self.current_song is None:
                    QTimer.singleShot(100, self._play_next_in_queue)
            
            self.sig_queue_changed.emit(self.queue)
            return f"{info['title']} - {info['artist']}"

        except Exception as e:
            # USAMOS LOG.ERROR AQUÍ
            self.sig_log.emit(Log.error(f"YTMusic Search Error: {e}"))
            return None

    def _play_next_in_queue(self):
        with QMutexLocker(self.mutex):
            if not self.queue:
                self.current_song = None
                self.sig_now_playing.emit("Cola vacía")
                return

            next_song = self.queue.pop(0)
            self.current_song = next_song
            
        self.sig_queue_changed.emit(self.queue)
        self.sig_now_playing.emit(f"Cargando: {next_song['title']}...")
        
        # 2. CAMBIO PRINCIPAL: Usamos Log.info() para que salga con formato y color
        self.sig_log.emit(Log.info(f"🎵 YTMusic Cargando: {next_song['title']}"))

        # Extraer URL real
        url = self._extract_audio_url(next_song['videoId'])
        if url:
            media = self.instance.media_new(url)
            self.player.set_media(media)
            self.player.play()
            self.sig_now_playing.emit(f"▶️ {next_song['title']} - {next_song['artist']}")
        else:
            self.sig_log.emit(Log.error("No se pudo extraer audio de YTMusic."))
            self._play_next_in_queue() 

    def _extract_audio_url(self, video_id):
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'extract_flat': True
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                return info.get('url')
        except Exception as e:
            self.sig_log.emit(Log.error(f"Error yt-dlp: {e}"))
            return None

    def _check_playback_status(self):
        """Revisa cada segundo si la canción terminó."""
        if not self._is_active: return
        
        state = self.player.get_state()
        if state == vlc.State.Ended:
            self._play_next_in_queue()

    # --- CONTROLES ---
    def play_pause(self):
        if self.player.is_playing():
            self.player.set_pause(1)
            self.sig_log.emit(Log.info("YTMusic: Pausado"))
        else:
            self.player.set_pause(0)
            self.sig_log.emit(Log.info("YTMusic: Reanudado"))

    def skip(self):
        self.player.stop()
        self.sig_log.emit(Log.info("YTMusic: Saltando canción..."))
        self._play_next_in_queue()

    def set_volume(self, volume: int):
        self.player.audio_set_volume(volume)

    def stop(self):
        self.player.stop()
        with QMutexLocker(self.mutex):
            self.queue.clear()
            self.current_song = None
        self.sig_now_playing.emit("Detenido")