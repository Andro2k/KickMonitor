# backend/controller.py

from datetime import datetime
import os
import re
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread

# --- INFRAESTRUCTURA Y WORKERS ---
from backend.core.db_controller import DBHandler
from backend.handlers.antibot_handler import AntibotHandler
from backend.utils.logger_text import LoggerText
from backend.utils.paths import get_cache_path
from backend.workers.trigger_worker import OverlayServerWorker
from backend.core.kick_bot import KickBotWorker   
from backend.workers.redemption_worker import RedemptionWorker
from backend.workers.spotify_worker import SpotifyWorker
from backend.workers.tts_worker import TTSWorker   
from backend.workers.update_worker import UpdateCheckerWorker, UpdateDownloaderWorker
from backend.workers.kick_worker import FollowMonitorWorker
from backend.workers.chat_worker import ChatOverlayWorker
# --- LÓGICA DE NEGOCIO (SERVICIOS Y HANDLERS) ---
from backend.game.casino import CasinoSystem
from backend.services.commands_service import CommandsService
from backend.handlers.chat_handler import ChatHandler
from backend.handlers.music_handler import MusicHandler
from backend.handlers.game_handler import GameHandler
from backend.handlers.triggers_handler import TriggerHandler
from frontend.dialogs.update_modal import UpdateModal

class MainController(QObject):
    """Controlador Principal (Facade Pattern)."""
    
    # --- SEÑALES UI ---
    log_signal = pyqtSignal(str)
    chat_signal = pyqtSignal(str, str, str)
    status_signal = pyqtSignal(str)
    connection_changed = pyqtSignal(bool)
    user_info_signal = pyqtSignal(str, int, str)
    toast_signal = pyqtSignal(str, str, str)
    gamble_result_signal = pyqtSignal(str, str, str, bool)
    username_needed = pyqtSignal()

    def __init__(self):
        super().__init__()       
        # 1. Persistencia y Servicios Core
        self.db = DBHandler()
        self.cmd_service = CommandsService(self.db)
        self.casino_system = CasinoSystem(self.db)       
        
        # 2. Inicialización de Workers
        self._init_spotify()
        self._init_tts()
        self._init_overlay()
        self._init_chat_overlay()     
        
        # 3. Handlers de Lógica
        self.chat_handler = ChatHandler(self.db)
        self.music_handler = MusicHandler(self.db, self.spotify) 
        self.game_handler = GameHandler(self.db, self.casino_system)
        self.trigger_handler = TriggerHandler(self.db, self.overlay_server)
        self.antibot = AntibotHandler(self.db)
        
        # 4. Estado Interno
        self.worker: Optional[KickBotWorker] = None          
        self.monitor_worker: Optional[FollowMonitorWorker] = None
        self.redemption_worker: Optional[RedemptionWorker] = None
        self.tts_enabled = False
        self.command_only = False       
        
        # 5. Configuración y Timers
        self._setup_timers()
        self.debug_enabled = self.db.get_bool("debug_mode")
        LoggerText.enabled_debug = self.debug_enabled
        self.log_signal.connect(self._write_log_to_file)
        
        # 6. Actualizaciones
        self._manual_check = False
        self._update_found = False
        self.check_updates(manual=False)
    
    def _setup_timers(self):
        self.points_timer = QTimer()
        self.points_timer.timeout.connect(self.chat_handler.distribute_periodic_points)
        self.points_timer.start(60000)

        self.msg_timer = QTimer()
        self.msg_timer.timeout.connect(self._check_timers_execution)
        self.msg_timer.start(60000)

    # =========================================================================
    # REGIÓN 1: PIPELINE DE PROCESAMIENTO DE CHAT
    # =========================================================================
    def on_chat_received(self, user, content, badges, timestamp):
        """Recibe datos limpios y los procesa a través de la cadena de responsabilidad."""
        msg_lower = content.strip().lower()
        
        # 0. ANTIBOT Y FILTROS BASE
        if self.antibot.check_user(user, self._ban_user, self.emit_log) or \
           self.chat_handler.is_bot(user) or \
           self.chat_handler.should_ignore_user(user):
            self._update_ui_chat(timestamp, user, content)
            return
            
        # 1. ECONOMÍA
        self.chat_handler.process_points(user, msg_lower, badges)
        
        # 2. EVALUACIÓN PEREZOSA (Lazy Evaluation) DE COMANDOS
        # En vez de múltiples IFs, evaluamos una lista hasta que uno retorne True
        command_handlers = [
            lambda: self.music_handler.handle_command(user, content, msg_lower, self.send_msg, self.emit_log),
            lambda: self.game_handler.handle_command(user, msg_lower, self.send_msg, self.gamble_result_signal.emit),
            lambda: self._handle_custom_responses(user, msg_lower),
            lambda: self._handle_points_query(user, msg_lower)
        ]
        
        if any(handler() for handler in command_handlers):
            self._update_ui_chat(timestamp, user, content)
            return
            
        # 3. PROCESAMIENTO MULTIMEDIA (TTS y Overlay)
        if self.tts_enabled: 
            self._process_tts(user, content)

        if self._should_send_to_overlay(user, content):
            is_streamer = user.lower() == (self.db.get("kick_username") or "").lower()
            
            self.chat_overlay.send_chat_message_to_overlay(
                sender=user, content=content, badges=badges,
                user_color="#53fc18" if is_streamer else "#ffffff",
                timestamp=timestamp
            )
            
        self.game_handler.analyze_outcome(user, content, self.gamble_result_signal.emit)
        self._update_ui_chat(timestamp, user, content)

    def _should_send_to_overlay(self, user, content) -> bool:
        """Filtro inteligente para enviar mensajes a OBS."""
        if self.db.get_bool("chat_hide_bots") and self.chat_handler.is_bot(user): return False
        if self.db.get_bool("chat_hide_cmds") and content.strip().startswith("!"): return False
        
        # Búsqueda O(1) usando Set Comprehension
        ignored_users = self.db.get("chat_ignored_users") or ""
        ignored_set = {u.strip().lower() for u in ignored_users.split(",") if u.strip()}
        
        return user.lower() not in ignored_set

    def _ban_user(self, username: str):
        if not self.worker: return
        if hasattr(self.worker, 'ban_user'):
            self.worker.ban_user(username)
        else:
            self.worker.send_chat_message(f"/ban {username}")

    def _update_ui_chat(self, timestamp, user, content):
        self.chat_signal.emit(timestamp, user, self.chat_handler.format_for_ui(content))

    # =========================================================================
    # REGIÓN 2: LÓGICA AUXILIAR DE CHAT
    # =========================================================================
    def _handle_custom_responses(self, user, msg_lower) -> bool:
        trigger, *rest = msg_lower.split(" ", 1)
        args = rest[0] if rest else ""
        
        can_exec, message = self.cmd_service.can_execute(trigger)  
        if not message: return False
        
        if not can_exec:
            self.send_msg(f"@{user} {message}")
            return True           
            
        extra_context = {"song": self.music_handler.get_current_song_info()}
        self.send_msg(self.chat_handler.format_custom_message(message, user, args, extra_context))
        self.emit_log(LoggerText.info(f"Comando ejecutado: {trigger}"))
        return True

    def _handle_points_query(self, user, msg_lower) -> bool:
        cmd = (self.db.get("points_command") or "!puntos").lower()
        if msg_lower.startswith(cmd):
            self.send_msg(f"@{user} tienes {self.db.get_points(user)} {self.db.get('points_name') or 'Puntos'}")
            return True
        return False

    def _process_tts(self, user, content):
        cmd = (self.db.get("tts_command") or "!voz").lower().strip()
        
        if self.command_only and content.lower().startswith(cmd):
            final_text = self.chat_handler.clean_for_tts(content[len(cmd):])
        elif not self.command_only and not content.startswith("!"):
            final_text = self.chat_handler.clean_for_tts(content)
        else:
            return
            
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
        self.tts = TTSWorker(); self.tts.start()

    def _init_overlay(self):
        self.overlay_server = OverlayServerWorker()
        self.overlay_server.log_signal.connect(self.emit_log); self.overlay_server.start()
        
    def _init_chat_overlay(self):
        self.chat_overlay = ChatOverlayWorker(port=6001)
        self.chat_overlay.error_occurred.connect(self.emit_log); self.chat_overlay.start()

    def start_bot(self):
        if self.worker: self.stop_bot()      
        
        config = {key: self.db.get(key) for key in ["client_id", "client_secret", "chatroom_id", "kick_username", "redirect_uri"]}
        
        if not config["client_id"] or not config["client_secret"]:
            self.toast_signal.emit("Error", "Faltan Client ID / Secret", "status_error")
            self.connection_changed.emit(False)
            return

        self.status_signal.emit("Conectando.")
        self.toast_signal.emit("Iniciando", "Autenticando.", "info")
        
        self.worker = KickBotWorker(config)
        self.worker.chat_received.connect(self.on_chat_received)
        self.worker.log_received.connect(self.emit_log)
        self.worker.disconnected_signal.connect(self.on_disconnected)
        self.worker.user_info_signal.connect(lambda u, f, p: (self.user_info_signal.emit(u, f, p), self.force_user_refresh_ui()))
        self.worker.username_required.connect(self.username_needed.emit)
        self.worker.start()
        
        if not self.redemption_worker:
            self.redemption_worker = RedemptionWorker(self.db)
            self.redemption_worker.log_signal.connect(self.emit_log)
            self.redemption_worker.redemption_detected.connect(self.on_redemption_received)
            self.redemption_worker.start()

        if config["kick_username"]: self._start_monitor(config["kick_username"])
            
        self.connection_changed.emit(True)
        self.toast_signal.emit("Conectado", "Bot en línea y escuchando.", "status_success")

    def stop_bot(self):
        """Detiene dinámicamente todos los workers de red (DRY Pattern)."""
        workers_to_stop = ['worker', 'monitor_worker', 'redemption_worker']
        
        for w_attr in workers_to_stop:
            w_instance = getattr(self, w_attr, None)
            if w_instance:
                if w_attr == 'worker': self.safe_disconnect(w_instance.chat_received)
                w_instance.stop()
                if not w_instance.wait(500) and w_attr == 'worker': 
                    self.emit_log(LoggerText.warning("Timeout: Forzando cierre de hilos."))
                setattr(self, w_attr, None)
                
        self.status_signal.emit("Desconectado")
        self.connection_changed.emit(False)
        self.toast_signal.emit("Sistema", "Desconectado", "status_warning")

    def shutdown(self):
        self.stop_bot()
        for server in filter(None, [self.tts, self.overlay_server, self.chat_overlay]): 
            server.stop()

        if hasattr(self, 'spotify_thread') and self.spotify_thread.isRunning():
            self.spotify.sig_do_disconnect.emit()
            self.spotify_thread.quit()
            self.spotify_thread.wait(1000)

    def on_disconnected(self): 
        if self.worker: self.worker.deleteLater(); self.worker = None
        self.status_signal.emit("Desconectado")
        self.connection_changed.emit(False)

    # =========================================================================
    # REGIÓN 4: UTILIDADES Y EVENTOS EXTERNOS
    # =========================================================================
    def set_manual_username(self, username):
        self.db.set("kick_username", username)
        self.toast_signal.emit("Configuración", f"Usuario '{username}' guardado.", "status_success")
        QTimer.singleShot(500, self.start_bot)

    def _start_monitor(self, username):
        if not self.monitor_worker:
            self.monitor_worker = FollowMonitorWorker(username)
            self.monitor_worker.new_follower.connect(self.on_new_follower)
            self.monitor_worker.start()

    def on_new_follower(self, count, name):
        self.toast_signal.emit("¡NUEVO!", f"{name} (+{count})", "status_success")
        self.emit_log(LoggerText.success(f"NUEVO SEGUIDOR: {name}"))
        if self.tts_enabled: self.tts.add_message(f"Gracias {name} por seguirme.")
        
        msg_tpl, is_active = self.db.get_text_alert("follow")
        if is_active and msg_tpl:
            self.send_msg(msg_tpl.replace("{user}", name).replace("{count}", str(count)))

    def force_user_refresh_ui(self):
        username = self.db.get("kick_username")
        if username:
            if not self.monitor_worker: self._start_monitor(username)
            self.user_info_signal.emit(username, 0, "")

    def force_user_refresh(self):
        if self.worker: 
            self.stop_bot()
            self.toast_signal.emit("Reinicio", "Cambio usuario detectado", "status_warning")
            
        username = self.db.get("kick_username")
        if username and (data := self.db.get_kick_user(username)):
            self.user_info_signal.emit(data["username"], data["followers"], data["profile_pic"])
        else:
            self.user_info_signal.emit("Streamer", 0, "")

    def send_msg(self, text): 
        if self.worker: self.worker.send_chat_message(text)
    
    def emit_log(self, text): self.log_signal.emit(text)
    
    def safe_disconnect(self, signal): 
        try: signal.disconnect()
        except: pass
    
    def set_tts_enabled(self, enabled): 
        self.tts_enabled = enabled
        if not enabled and self.tts: 
            self.tts.immediate_stop(); self.emit_log(LoggerText.info("Sistema TTS: Desactivado"))
    
    def set_command_only(self, enabled): self.command_only = enabled

    def _check_timers_execution(self):
        if not self.worker: return
        import time
        now = time.time()
        for name, msg in self.db.get_due_timers(now):
            if msg:
                self.send_msg(msg)
                self.emit_log(LoggerText.system(f"Timer automático: '{name}'"))
                self.db.update_timer_run(name, now)

    # =========================================================================
    # REGIÓN 5: ACTUALIZACIONES
    # =========================================================================
    def check_updates(self, manual=False):
        self._manual_check = manual
        self._update_found = False
        if manual: self.toast_signal.emit("Sistema", "Buscando actualizaciones.", "info")

        self.updater = UpdateCheckerWorker()
        self.updater.update_available.connect(self.ask_user_to_update)
        self.updater.finished.connect(self._on_check_finished)
        self.updater.start()

    def ask_user_to_update(self, new_ver, url, notes):
        self._update_found = True
        if UpdateModal(new_ver, notes, parent=None).exec():
            self.toast_signal.emit("Sistema", "Descargando actualización.", "status_success")
            self.start_download(url)
        else:
            self.emit_log(LoggerText.system("Usuario pospuso actualización."))

    def _on_check_finished(self):
        if self._manual_check and not self._update_found:
            self.toast_signal.emit("Sistema", "Ya tienes la última versión.", "status_success")
        self._manual_check = False
        try: self.updater.deleteLater()
        except: pass

    def start_download(self, url):
        self.downloader = UpdateDownloaderWorker(url)
        self.downloader.progress.connect(lambda p: self.emit_log(LoggerText.system(f"Descargando: {p}%")) if p % 10 == 0 else None)
        self.downloader.error.connect(lambda e: self.toast_signal.emit("Error Update", str(e), "status_error"))
        self.downloader.start()

    # =========================================================================
    # REGIÓN 6: LOGS & DEBUG
    # =========================================================================
    def _write_log_to_file(self, html_msg: str):
        try:
            clean_msg = re.sub(r'<[^>]+>', '', html_msg)
            date_str = datetime.now().strftime("%Y-%m-%d")
            with open(os.path.join(get_cache_path(), f"log_{date_str}.log"), "a", encoding="utf-8") as f:
                f.write(f"{clean_msg}\n")
        except: pass

    def set_debug_mode(self, enabled: bool):
        self.debug_enabled = enabled
        self.db.set("debug_mode", enabled)
        LoggerText.enabled_debug = enabled 
        self.emit_log(LoggerText.system(f"Modo Depuración: {'ACTIVADO' if enabled else 'DESACTIVADO'}"))

    # =========================================================================
    # REGIÓN 7: REDEMPTIONS
    # =========================================================================
    def on_redemption_received(self, user, reward_title, user_input):
        found = self.trigger_handler.handle_redemption(user, reward_title, user_input, self.emit_log)
        if found:
            self.emit_log(LoggerText.success(f"Trigger disparado: {reward_title}"))
        else:
            self.emit_log(LoggerText.info(f"Canje sin acción: {reward_title}"))