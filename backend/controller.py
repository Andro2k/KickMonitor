# backend/controller.py

import time
from datetime import datetime
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread

# --- INFRAESTRUCTURA Y WORKERS ---
from backend.db_controller import DBHandler
from backend.handlers.antibot_handler import AntibotHandler
from backend.logger import Log
from backend.overlay_server import OverlayServerWorker
from backend.kick_bot import KickBotWorker   
from backend.spotify_worker import SpotifyWorker
from backend.tts import TTSWorker   
from backend.updater import CURRENT_VERSION, UpdateCheckerWorker, UpdateDownloaderWorker
from backend.workers import FollowMonitorWorker

# --- LÓGICA DE NEGOCIO (SERVICIOS Y HANDLERS) ---
from backend.casino import CasinoSystem
from backend.services.commands_service import CommandsService
from backend.handlers.chat_handler import ChatHandler
from backend.handlers.music_handler import MusicHandler
from backend.handlers.game_handler import GameHandler
from backend.handlers.alert_handler import AlertHandler
from ui.dialogs.update_modal import UpdateModal

class MainController(QObject):
    """
    Controlador Principal (Facade Pattern).
    Coordina la comunicación entre la UI, la Base de Datos y los Workers en segundo plano.
    """
    # --- SEÑALES UI ---
    log_signal = pyqtSignal(str)
    chat_signal = pyqtSignal(str, str, str)
    status_signal = pyqtSignal(str)
    connection_changed = pyqtSignal(bool)
    user_info_signal = pyqtSignal(str, int, str)
    toast_signal = pyqtSignal(str, str, str)
    gamble_result_signal = pyqtSignal(str, str, str, bool)
    username_needed = pyqtSignal()
    VERSION = CURRENT_VERSION

    def __init__(self):
        super().__init__()       
        # 1. Persistencia y Servicios Core
        self.db = DBHandler()
        self.cmd_service = CommandsService(self.db)
        self.casino_system = CasinoSystem(self.db)       
        # 2. Inicialización de Workers (Hilos secundarios)
        self._init_spotify()
        self._init_tts()
        self._init_overlay()        
        # 3. Handlers de Lógica (Estrategias)
        self.chat_handler = ChatHandler(self.db)
        self.music_handler = MusicHandler(self.db, self.spotify) 
        self.game_handler = GameHandler(self.db, self.casino_system)
        self.alert_handler = AlertHandler(self.db, self.overlay_server)
        self.antibot = AntibotHandler(self.db) # <--- YA ESTABA AQUÍ
        # 4. Estado Interno
        self.worker: Optional[KickBotWorker] = None          
        self.monitor_worker: Optional[FollowMonitorWorker] = None  
        self.tts_enabled = False
        self.command_only = False       
        # 5. Timers Recurrentes
        self._setup_timers()
        # 6. Actualizaciones
        self._manual_check = False
        self._update_found = False
        self.check_updates(manual=False)
    def _setup_timers(self):
        # Timer Puntos: Distribuye puntos cada minuto
        self.points_timer = QTimer()
        self.points_timer.timeout.connect(self.chat_handler.distribute_periodic_points)
        self.points_timer.start(60000)
        # Timer Automatización: Mensajes automáticos cada 60s
        self.msg_timer = QTimer()
        self.msg_timer.timeout.connect(self._check_timers_execution)
        self.msg_timer.start(60000)

    # =========================================================================
    # REGIÓN 1: PIPELINE DE PROCESAMIENTO DE CHAT
    # =========================================================================
    def on_chat_received(self, html_content, raw_msg):
        """
        Punto central de entrada de mensajes.
        Decide qué handler debe procesar el mensaje.
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        user, content, badges = self.chat_handler.parse_message(raw_msg)
        msg_lower = content.strip().lower()

        # -----------------------------------------------------------
        # 0. ANTIBOT (Seguridad Prioritaria)
        # -----------------------------------------------------------
        # Verificamos si es un bot raid antes de procesar nada más
        if self.antibot.check_user(user, self._ban_user, self.emit_log):
            # Si retorna True, el usuario fue detectado como bot y baneado.
            # No actualizamos UI ni procesamos comandos.
            return 
        # -----------------------------------------------------------

        # 1. Filtros de seguridad (Mute / Ignore Bots)
        if self.chat_handler.should_ignore_user(user): 
            self.emit_log(Log.warning(f"Usuario ignorado (Mute): {user}"))
            self._update_ui_chat(timestamp, user, content)
            return
        if self.chat_handler.is_bot(user):
            self.emit_log(Log.debug(f"Mensaje de Bot ignorado: {user}"))
            self._update_ui_chat(timestamp, user, content)
            return

        # 2. Economía (Dar puntos por actividad)
        self.chat_handler.process_points(user, msg_lower, badges)

        # 3. Delegación a Handlers (Cadena de Responsabilidad)
        # Si un handler retorna True, significa que manejó el mensaje y terminamos.       
        
        # A) Música (!song, !sr)
        if self.music_handler.handle_command(user, content, msg_lower, self.send_msg, self.emit_log):
            self._finalize_message(timestamp, user, content)
            return
        # B) Juegos (!gamble, !slots)
        if self.game_handler.handle_command(user, msg_lower, self.send_msg, self.gamble_result_signal.emit):
            self._finalize_message(timestamp, user, content)
            return
        # C) Comandos Personalizados (DB)
        if self._handle_custom_responses(user, msg_lower):
            self._finalize_message(timestamp, user, content)
            return
        # D) Alertas Multimedia (Overlay)
        if self.alert_handler.handle_trigger(user, msg_lower, self.send_msg, self.emit_log):
            self._finalize_message(timestamp, user, content)
            return
        # E) Consultas Simples (!puntos)
        if self._handle_points_query(user, msg_lower):
            self._finalize_message(timestamp, user, content)
            return

        # 4. Procesamiento Final (TTS y Resultados de Juegos pasivos)
        if self.tts_enabled: 
            self._process_tts(user, content)
            
        self.game_handler.analyze_outcome(user, content, self.gamble_result_signal.emit)
        self._update_ui_chat(timestamp, user, content)

    # =========================================================================
    # AUXILIAR: ACCIÓN DE BANEO
    # =========================================================================
    def _ban_user(self, username: str):
        """Callback que ejecuta el baneo real a través del worker."""
        if self.worker:
            # Opción A: Si el worker tiene método específico (recomendado)
            if hasattr(self.worker, 'ban_user'):
                self.worker.ban_user(username)
            # Opción B: Fallback vía comando de chat (si el bot es mod)
            else:
                self.worker.send_chat_message(f"/ban {username}")

    def _finalize_message(self, timestamp, user, content):
        """Actualiza la UI después de procesar un comando exitoso."""
        self._update_ui_chat(timestamp, user, content)

    def _update_ui_chat(self, timestamp, user, content):
        formatted = self.chat_handler.format_for_ui(content)
        self.chat_signal.emit(timestamp, user, formatted)

    # =========================================================================
    # REGIÓN 2: LÓGICA AUXILIAR DE CHAT
    # =========================================================================
    def _handle_custom_responses(self, user, msg_lower) -> bool:
        parts = msg_lower.split(" ", 1) 
        trigger = parts[0]
        can_exec, message = self.cmd_service.can_execute(trigger)  
        # Caso: Cooldown activo
        if not can_exec and message:
            self.send_msg(f"@{user} {message}")
            return True           
        # Caso: Ejecución permitida
        if can_exec and message:
            args = parts[1] if len(parts) > 1 else ""
            extra_context = {"song": self.music_handler.get_current_song_info()}
            final_msg = self.chat_handler.format_custom_message(message, user, args, extra_context)
            self.send_msg(final_msg)
            self.emit_log(Log.info(f"Comando ejecutado: {trigger}"))
            return True
        return False

    def _handle_points_query(self, user, msg_lower) -> bool:
        cmd = (self.db.get("points_command") or "!puntos").lower()
        if msg_lower.split(" ")[0] == cmd:
            pts = self.db.get_points(user)
            name = self.db.get('points_name') or 'Puntos'
            self.send_msg(f"@{user} tienes {pts} {name}")
            return True
        return False

    def _process_tts(self, user, content):
        cmd = (self.db.get("tts_command") or "!voz").lower().strip()
        final_text = ""       
        if self.command_only:
            if content.lower().startswith(cmd):
                raw = content[len(cmd):]
                final_text = self.chat_handler.clean_for_tts(raw)
        elif not content.startswith("!"):
            final_text = self.chat_handler.clean_for_tts(content)           
        if final_text: 
            self.tts.add_message(f"{user} dice: {final_text}")

    # =========================================================================
    # REGIÓN 3: GESTIÓN DE WORKERS Y CONEXIÓN
    # =========================================================================
    def _init_spotify(self):
        self.spotify_thread = QThread()
        self.spotify = SpotifyWorker(self.db)
        self.spotify.moveToThread(self.spotify_thread)
        self.spotify_thread.finished.connect(self.spotify_thread.deleteLater)
        self.spotify_thread.start()

    def _init_tts(self):
        self.tts = TTSWorker()
        self.tts.start()

    def _init_overlay(self):
        self.overlay_server = OverlayServerWorker()
        self.overlay_server.log_signal.connect(self.emit_log)
        self.overlay_server.start()

    def start_bot(self):
        """Inicia la conexión principal con Kick."""
        if self.worker: self.stop_bot()      
        config = { 
            "client_id": self.db.get("client_id"), 
            "client_secret": self.db.get("client_secret"), 
            "chatroom_id": self.db.get("chatroom_id"), 
            "kick_username": self.db.get("kick_username"), 
            "redirect_uri": self.db.get("redirect_uri") 
        }        
        if not all([config["client_id"], config["client_secret"]]):
            self.toast_signal.emit("Error", "Faltan Client ID / Secret", "Status_Red")
            self.connection_changed.emit(False)
            return

        self.status_signal.emit("Conectando...")
        self.toast_signal.emit("Iniciando", "Autenticando...", "info")
        
        self.worker = KickBotWorker(config)
        self.worker.chat_received.connect(self.on_chat_received)
        self.worker.log_received.connect(self.emit_log)
        self.worker.disconnected_signal.connect(self.on_disconnected)
        self.worker.user_info_signal.connect(lambda u, f, p: (self.user_info_signal.emit(u, f, p), self.force_user_refresh_ui()))
        self.worker.username_required.connect(self.username_needed.emit)
        
        self.worker.start()
        
        if config["kick_username"]: 
            self._start_monitor(config["kick_username"])
            
        self.connection_changed.emit(True)

    def stop_bot(self):
        """Detiene la conexión de forma segura."""
        if self.worker: 
            self.safe_disconnect(self.worker.chat_received)
            self.worker.stop()
            if not self.worker.wait(500): 
                self.emit_log(Log.warning("Timeout: Forzando cierre de hilos..."))
            self.worker = None             
        if self.monitor_worker: 
            self.monitor_worker.stop()
            self.monitor_worker.wait(500)
            self.monitor_worker = None            
        self.status_signal.emit("Desconectado")
        self.connection_changed.emit(False)
        self.toast_signal.emit("Sistema", "Desconectado", "Status_Yellow")

    def shutdown(self):
        """Cierre total de la aplicación (Cleanup)."""
        self.stop_bot()
        if self.tts: self.tts.stop()
        if self.overlay_server: self.overlay_server.stop()
        if self.spotify_thread.isRunning():
            self.spotify.sig_do_disconnect.emit()
            self.spotify_thread.quit()
            self.spotify_thread.wait()

    def on_disconnected(self): 
        if self.worker: 
            self.worker.deleteLater()
            self.worker = None
        self.status_signal.emit("Desconectado")
        self.connection_changed.emit(False)

    # =========================================================================
    # REGIÓN 4: UTILIDADES Y SETTERS
    # =========================================================================
    def set_manual_username(self, username):
        self.db.set("kick_username", username)
        self.toast_signal.emit("Configuración", f"Usuario '{username}' guardado.", "Status_Green")
        QTimer.singleShot(500, self.start_bot)

    def _start_monitor(self, username):
        if self.monitor_worker is None:
            self.monitor_worker = FollowMonitorWorker(username)
            self.monitor_worker.new_follower.connect(self.on_new_follower)
            self.monitor_worker.start()

    def on_new_follower(self, target, count, name):
        # 1. Notificación Visual
        self.toast_signal.emit("¡NUEVO!", f"{name} (+{count})", "Status_Green")
        self.emit_log(Log.success(f"NUEVO SEGUIDOR: {name}"))
        # 2. Voz
        if self.tts_enabled: 
            self.tts.add_message(f"Gracias {name} por seguirme.")
        # 3. Chat Alerta
        msg_tpl, is_active = self.db.get_text_alert("follow")
        if is_active and msg_tpl:
            final_msg = msg_tpl.replace("{user}", name).replace("{count}", str(count))
            self.send_msg(final_msg)

    def force_user_refresh_ui(self):
        username = self.db.get("kick_username")
        if username:
            if not self.monitor_worker: self._start_monitor(username)
            self.user_info_signal.emit(username, 0, "")

    def force_user_refresh(self):
        if self.worker: 
            self.stop_bot()
            self.toast_signal.emit("Reinicio", "Cambio usuario detectado", "Status_Yellow")
        username = self.db.get("kick_username")
        if username: 
            data = self.db.get_kick_user(username)
            if data: 
                self.user_info_signal.emit(data["username"], data["followers"], data["profile_pic"])

    def send_msg(self, text): 
        if self.worker: self.worker.send_chat_message(text)
    
    def emit_log(self, text): self.log_signal.emit(text)
    
    def safe_disconnect(self, signal): 
        try: signal.disconnect()
        except: pass
    
    def set_tts_enabled(self, enabled): 
        self.tts_enabled = enabled
        if not enabled and self.tts: 
            self.tts.immediate_stop()
            self.emit_log(Log.info("Sistema TTS: Desactivado"))
    
    def set_command_only(self, enabled): self.command_only = enabled

    def _check_timers_execution(self):
        """Ejecuta mensajes programados (Timers)."""
        if not self.worker: return
        import time
        now = time.time()
        due_list = self.db.get_due_timers(now)
        
        for name, msg in due_list:
            if msg:
                self.send_msg(msg)
                self.emit_log(Log.system(f"Timer automático ejecutado: '{name}'"))
                self.db.update_timer_run(name, now)
    # =========================================================================
    # REGIÓN 5: ACTUALIZACIONES (MODIFICADO)
    # =========================================================================
    def check_updates(self, manual=False):
        """
        Inicia el worker de comprobación.
        :param manual: True si fue invocado por el botón de Settings, False si es automático.
        """
        self._manual_check = manual
        self._update_found = False # Reiniciamos la bandera

        if manual:
            self.toast_signal.emit("Sistema", "Buscando actualizaciones...", "info")

        self.updater = UpdateCheckerWorker()
        self.updater.update_available.connect(self.ask_user_to_update)
        # Conectamos la señal 'finished' para saber cuándo termina el proceso, haya encontrado algo o no
        self.updater.finished.connect(self._on_check_finished)
        self.updater.start()

    def ask_user_to_update(self, new_ver, url, notes):
        """Callback cuando SE ENCUENTRA una actualización."""
        self._update_found = True # Marcamos que encontramos algo
        
        # Si es manual o automático, mostramos el modal igual
        modal = UpdateModal(new_ver, notes, parent=None) 
        
        if modal.exec():
            self.toast_signal.emit("Sistema", "Descargando actualización...", "Status_Green")
            self.start_download(url)
        else:
            self.emit_log(Log.system("El usuario pospuso la actualización."))

    def _on_check_finished(self):
        """Se ejecuta siempre que el worker termina de buscar."""
        # Solo notificamos "Sin novedades" si fue una búsqueda manual y no se encontró nada
        if self._manual_check and not self._update_found:
            self.toast_signal.emit("Sistema", "Ya tienes la última versión.", "Status_Green")
        
        # Limpieza
        self._manual_check = False
        # Es buena práctica limpiar el worker, aunque deleteLater lo maneje Qt
        try: self.updater.deleteLater()
        except: pass

    def start_download(self, url):
        self.downloader = UpdateDownloaderWorker(url)
        
        # Conexiones
        self.downloader.progress.connect(self._on_update_progress) # <--- NUEVO
        self.downloader.error.connect(lambda e: self.toast_signal.emit("Error Update", str(e), "Status_Red"))
        self.downloader.start()

    def _on_update_progress(self, percent):
        if percent % 10 == 0: # Para no saturar el log
            self.emit_log(Log.system(f"Descargando actualización: {percent}%"))