# backend/controller.py

from datetime import datetime
import os
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread

# --- INFRAESTRUCTURA Y WORKERS ---
from backend.core.db_controller import DBHandler
from backend.handlers.antibot_handler import AntibotHandler
from backend.utils.logger_text import LoggerText
from backend.utils.paths import get_cache_path
from backend.workers.overlay_worker import OverlayServerWorker
from backend.core.kick_bot import KickBotWorker   
from backend.workers.redemption_worker import RedemptionWorker
from backend.workers.spotify_worker import SpotifyWorker
from backend.workers.tts_worker import TTSWorker   
from backend.workers.update_worker import UpdateCheckerWorker, UpdateDownloaderWorker
from backend.workers.kick_worker import FollowMonitorWorker

# --- LÓGICA DE NEGOCIO (SERVICIOS Y HANDLERS) ---
from backend.game.casino import CasinoSystem
from backend.services.commands_service import CommandsService
from backend.handlers.chat_handler import ChatHandler
from backend.handlers.music_handler import MusicHandler
from backend.handlers.game_handler import GameHandler
from backend.handlers.triggers_handler import TriggerHandler
from frontend.dialogs.update_modal import UpdateModal

class MainController(QObject):
    """
    Controlador Principal (Facade Pattern).
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
        
        # 3. Handlers de Lógica
        self.chat_handler = ChatHandler(self.db)
        self.music_handler = MusicHandler(self.db, self.spotify) 
        self.game_handler = GameHandler(self.db, self.casino_system)
        self.alert_handler = TriggerHandler(self.db, self.overlay_server)
        self.trigger_handler = TriggerHandler(self.db, self.overlay_server)
        self.antibot = AntibotHandler(self.db)
        
        # 4. Estado Interno
        self.worker: Optional[KickBotWorker] = None          
        self.monitor_worker: Optional[FollowMonitorWorker] = None
        self.redemption_worker: Optional[RedemptionWorker] = None
        self.tts_enabled = False
        self.command_only = False       
        
        # 5. Configuración
        self._setup_timers()
        self.debug_enabled = self.db.get_bool("debug_mode")
        LoggerText.enabled_debug = self.debug_enabled # Sincronizar clase Log
        
        # 6. Registro de Logs (Solo la señal principal)
        self.log_signal.connect(self._write_log_to_file)
        
        # 7. Actualizaciones
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
    def on_chat_received(self, user, content, badges, timestamp):
        """
        Recibe datos ya limpios desde KickBot.
        """
        msg_lower = content.strip().lower()
        # 0. ANTIBOT
        if self.antibot.check_user(user, self._ban_user, self.emit_log):
            return
        if self.chat_handler.is_bot(user):
            self._update_ui_chat(timestamp, user, content)
            return
        # 1. Filtros de seguridad
        if self.chat_handler.should_ignore_user(user): 
            self._update_ui_chat(timestamp, user, content)
            return           
        # 2. Economía
        self.chat_handler.process_points(user, msg_lower, badges)
        # 3. Delegación a Handlers (Cadena de Responsabilidad)
        # Música
        if self.music_handler.handle_command(user, content, msg_lower, self.send_msg, self.emit_log):
            self._finalize_message(timestamp, user, content)
            return           
        # Juegos
        if self.game_handler.handle_command(user, msg_lower, self.send_msg, self.gamble_result_signal.emit):
            self._finalize_message(timestamp, user, content)
            return
        # Comandos Custom
        if self._handle_custom_responses(user, msg_lower):
            self._finalize_message(timestamp, user, content)
            return
        # # Alertas / Overlay
        # if self.alert_handler.handle_trigger(user, msg_lower, self.send_msg, self.emit_log):
        #     self._finalize_message(timestamp, user, content)
        #     return
        # Consulta Puntos
        if self._handle_points_query(user, msg_lower):
            self._finalize_message(timestamp, user, content)
            return
        # 4. Procesamiento Final
        if self.tts_enabled: 
            self._process_tts(user, content)
            
        self.game_handler.analyze_outcome(user, content, self.gamble_result_signal.emit)
        self._update_ui_chat(timestamp, user, content)

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
        if not can_exec and message:
            self.send_msg(f"@{user} {message}")
            return True           
        # Caso: Ejecución permitida
        if can_exec and message:
            args = parts[1] if len(parts) > 1 else ""
            extra_context = {"song": self.music_handler.get_current_song_info()}
            final_msg = self.chat_handler.format_custom_message(message, user, args, extra_context)
            self.send_msg(final_msg)
            self.emit_log(LoggerText.info(f"Comando ejecutado: {trigger}"))
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
            # CONEXIÓN CLAVE: Del worker al nuevo método on_redemption
            self.redemption_worker.redemption_detected.connect(self.on_redemption_received)
            self.redemption_worker.start()

        if config["kick_username"]: 
            self._start_monitor(config["kick_username"])
            
        self.connection_changed.emit(True)
        self.toast_signal.emit("Conectado", "Bot en línea y escuchando.", "status_success")

    def stop_bot(self):
        """Detiene la conexión de forma segura."""
        if self.worker: 
            self.safe_disconnect(self.worker.chat_received)
            self.worker.stop()
            if not self.worker.wait(500): 
                self.emit_log(LoggerText.warning("Timeout: Forzando cierre de hilos."))
            self.worker = None             
        if self.monitor_worker: 
            self.monitor_worker.stop()
            self.monitor_worker.wait(500)
            self.monitor_worker = None           
        if self.redemption_worker:
            self.redemption_worker.stop()
            self.redemption_worker.wait()
            self.redemption_worker = None 
        self.status_signal.emit("Desconectado")
        self.connection_changed.emit(False)
        self.toast_signal.emit("Sistema", "Desconectado", "status_warning")

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
        self.toast_signal.emit("Configuración", f"Usuario '{username}' guardado.", "status_success")
        QTimer.singleShot(500, self.start_bot)

    def _start_monitor(self, username):
        if self.monitor_worker is None:
            self.monitor_worker = FollowMonitorWorker(username)
            self.monitor_worker.new_follower.connect(self.on_new_follower)
            self.monitor_worker.start()

    def on_new_follower(self, count, name):
        # 1. Notificación Visual
        self.toast_signal.emit("¡NUEVO!", f"{name} (+{count})", "status_success")
        self.emit_log(LoggerText.success(f"NUEVO SEGUIDOR: {name}"))
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
            self.toast_signal.emit("Reinicio", "Cambio usuario detectado", "status_warning")
        username = self.db.get("kick_username")
        if username: 
            data = self.db.get_kick_user(username)
            if data: 
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
            self.tts.immediate_stop()
            self.emit_log(LoggerText.info("Sistema TTS: Desactivado"))
    
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
                self.emit_log(LoggerText.system(f"Timer automático ejecutado: '{name}'"))
                self.db.update_timer_run(name, now)
    # =========================================================================
    # REGIÓN 5: ACTUALIZACIONES
    # =========================================================================
    def check_updates(self, manual=False):
        """
        Inicia el worker de comprobación.
        """
        self._manual_check = manual
        self._update_found = False

        if manual:
            self.toast_signal.emit("Sistema", "Buscando actualizaciones.", "info")

        self.updater = UpdateCheckerWorker()
        self.updater.update_available.connect(self.ask_user_to_update)
        self.updater.finished.connect(self._on_check_finished)
        self.updater.start()

    def ask_user_to_update(self, new_ver, url, notes):
        """Callback cuando SE ENCUENTRA una actualización."""
        self._update_found = True
        # Si es manual o automático, mostramos el modal igual
        modal = UpdateModal(new_ver, notes, parent=None) 
        
        if modal.exec():
            self.toast_signal.emit("Sistema", "Descargando actualización.", "status_success")
            self.start_download(url)
        else:
            self.emit_log(LoggerText.system("El usuario pospuso la actualización."))

    def _on_check_finished(self):
        """Se ejecuta siempre que el worker termina de buscar."""

        if self._manual_check and not self._update_found:
            self.toast_signal.emit("Sistema", "Ya tienes la última versión.", "status_success")
        
        # Limpieza
        self._manual_check = False
        try: self.updater.deleteLater()
        except: pass

    def start_download(self, url):
        self.downloader = UpdateDownloaderWorker(url)
        self.downloader.progress.connect(self._on_update_progress)
        self.downloader.error.connect(lambda e: self.toast_signal.emit("Error Update", str(e), "status_error"))
        self.downloader.start()

    def _on_update_progress(self, percent):
        if percent % 10 == 0:
            self.emit_log(LoggerText.system(f"Descargando actualización: {percent}%"))

    # =========================================================================
    # REGIÓN 6: LOGS & DEBUG
    # =========================================================================

    def _write_log_to_file(self, html_msg: str):
        """
        Escribe el log en un archivo de texto plano, limpiando las etiquetas HTML.
        """
        try:
            clean_msg = html_msg.replace("<b>", "").replace("</b>", "")
            if "<span" in clean_msg:
                import re
                clean_msg = re.sub(r'<[^>]+>', '', clean_msg)

            date_str = datetime.now().strftime("%Y-%m-%d")
            log_file = os.path.join(get_cache_path(), f"log_{date_str}.log")

            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"{clean_msg}\n")
                
        except Exception as e:
            self.emit_log(LoggerText.debug(f"Error crítico de disco: {e}"))

    def set_debug_mode(self, enabled: bool):
        """Sincroniza el estado global de la clase Log."""
        self.debug_enabled = enabled
        self.db.set("debug_mode", enabled)
        LoggerText.enabled_debug = enabled 
        
        status = "ACTIVADO" if enabled else "DESACTIVADO"
        self.emit_log(LoggerText.system(f"Modo Depuración: {status}"))

    def emit_log(self, text):
        """Emite logs a la UI, ignorando los None (Debug desactivado)."""
        if text:
            self.log_signal.emit(text)

    # =========================================================================
    # NUEVO MÉTODO: MANEJADOR DE CANJES
    # =========================================================================
    def on_redemption_received(self, user, reward_title, user_input):
        """
        Recibe el canje limpio del Worker y lo pasa al Handler.
        """
        # Pasamos directamente el Título (ej: "Susto")
        found = self.trigger_handler.handle_redemption(
            user, 
            reward_title, 
            user_input, 
            self.emit_log
        )
        
        if found:
            self.emit_log(LoggerText.success(f"Trigger disparado: {reward_title}"))
        else:
            self.emit_log(LoggerText.info(f"Canje sin acción: {reward_title}"))
            pass