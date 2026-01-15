# backend/tts.py

import queue
import re
import pyttsx3
from PyQt6.QtCore import QThread, pyqtSignal

from backend.utils.logger import Log

class TTSWorker(QThread):
    error_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.queue = queue.Queue()
        self.is_running = True
        
        # Referencia al motor actual para poder detenerlo
        self.current_engine = None 
        
        # Configuración por defecto
        self.selected_voice_id = None
        self.rate = 175
        self.volume = 1.0 
        
        self.re_html = re.compile(r'<[^>]+>')
        self.re_url = re.compile(r'http\S+|www\.\S+')

    # ==========================================
    # CONTROL Y CONFIGURACIÓN
    # ==========================================
    def add_message(self, text: str):
        clean_text = self._clean_text(text)
        if clean_text: 
            self.queue.put(clean_text)

    def update_config(self, vid, rate, vol):
        self.selected_voice_id = vid
        self.rate = int(rate)
        self.volume = float(vol)

    def stop(self):
        self.is_running = False
        self.immediate_stop() # Aseguramos que se calle al cerrar
        self.wait()

    def immediate_stop(self):
        """Vacía la cola y fuerza la detención del audio actual."""
        # 1. Vaciar la cola de mensajes pendientes (Thread-safe)
        with self.queue.mutex:
            self.queue.queue.clear()           
        # 2. Detener el motor si está hablando
        if self.current_engine:
            try:
                self.current_engine.stop()
            except Exception as e:
                self.log_received.emit(Log.error(f"TTS Stop Error: {e}"))

    # ==========================================
    # LOOP PRINCIPAL
    # ==========================================
    def run(self):
        while self.is_running:
            try:
                text = self.queue.get(timeout=1)
                self._speak(text)
                self.queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                self.error_signal.emit(f"TTS Error General: {e}")

    # ==========================================
    # PROCESAMIENTO INTERNO
    # ==========================================
    def _clean_text(self, text: str) -> str:
        text = self.re_html.sub('', text)
        text = self.re_url.sub('un enlace', text)
        return text.strip()

    def _speak(self, text: str):
        try:
            # Guardamos la referencia en self.current_engine
            self.current_engine = pyttsx3.init()
            
            if self.selected_voice_id:
                try: 
                    self.current_engine.setProperty('voice', self.selected_voice_id)
                except: pass
            
            self.current_engine.setProperty('rate', self.rate)
            self.current_engine.setProperty('volume', self.volume)
            
            self.current_engine.say(text)
            self.current_engine.runAndWait()
            self.current_engine.stop()
            
        except Exception as e:
            # Ignoramos errores si fue por una interrupción forzada
            pass 
        finally:
            # Limpieza crítica
            if self.current_engine:
                try:
                    del self.current_engine
                except: pass
                self.current_engine = None