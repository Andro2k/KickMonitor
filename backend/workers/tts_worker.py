# backend/workers/tts_worker.py

import os
import warnings
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"
warnings.filterwarnings("ignore", category=UserWarning, module="pygame.pkgdata")

import queue
import re
import time
import asyncio
import io 
from contextlib import suppress

import pyttsx3
import edge_tts
import pygame

from PyQt6.QtCore import QThread, pyqtSignal
from backend.utils.logger_text import LoggerText

class TTSWorker(QThread):
    error_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.queue = queue.Queue()
        self.is_running = True

        self.engine_type = "edge-tts"
        self.volume = 1.0 

        self.current_engine = None 
        self.selected_voice_id = None
        self.rate = 175

        self.edge_voice = "es-MX-JorgeNeural"
        self.loop = None 

        with suppress(Exception):
            pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=2048)

        self.re_html = re.compile(r'<[^>]+>')
        self.re_url = re.compile(r'http\S+|www\.\S+')

    # ==========================================
    # CONTROL Y CONFIGURACIÓN
    # ==========================================
    def add_message(self, text: str):
        if clean_text := self._clean_text(text): 
            self.queue.put(clean_text)

    def update_config(self, vid, rate, vol, engine_type="edge-tts", edge_voice="es-MX-JorgeNeural"):
        self.selected_voice_id = vid
        self.rate = int(rate)
        self.volume = float(vol)
        self.engine_type = engine_type
        self.edge_voice = edge_voice

    def stop(self):
        self.is_running = False
        self.immediate_stop()
        self.quit()
        self.wait(1500)

    def immediate_stop(self):
        with self.queue.mutex:
            self.queue.queue.clear()           
            
        if self.current_engine:
            with suppress(Exception):
                self.current_engine.stop()
                
        with suppress(Exception):
            if pygame.mixer.get_init() and pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()

    # ==========================================
    # LOOP PRINCIPAL Y LIMPIEZA
    # ==========================================
    def run(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        while self.is_running:
            try:
                text = self.queue.get(timeout=0.5) 
                self._speak(text)
                self.queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                self.error_signal.emit(LoggerText.error(f"TTS Error: {e}"))

        self._cleanup_loop()

    def _cleanup_loop(self):
        """Cierra conexiones de Edge-TTS y libera la tarjeta de sonido de Windows."""
        if self.loop and not self.loop.is_closed():
            try:
                tasks = asyncio.all_tasks(self.loop)
                for t in tasks: t.cancel()
                self.loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
                self.loop.close()
            except Exception as e:
                print(f"Error limpiando loop TTS: {e}")
                
        with suppress(Exception):
            if pygame.mixer.get_init():
                pygame.mixer.quit()

    # ==========================================
    # PROCESAMIENTO INTERNO (ENRUTADOR)
    # ==========================================
    def _clean_text(self, text: str) -> str:
        text_no_html = self.re_html.sub('', text)
        return self.re_url.sub('un enlace', text_no_html).strip()

    def _speak(self, text: str):
        if self.engine_type == "edge-tts":
            self._speak_edge(text)
        else:
            self._speak_pyttsx3(text)

    def _speak_edge(self, text: str):
        try:
            if not self.loop or self.loop.is_closed(): return
            
            audio_bytes = self.loop.run_until_complete(self._get_edge_bytes(text))
            
            if not audio_bytes:
                raise Exception("No se generó audio")

            audio_stream = io.BytesIO(audio_bytes)

            pygame.mixer.music.load(audio_stream)
            pygame.mixer.music.set_volume(self.volume)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy() and self.is_running:
                time.sleep(0.05)
                
        except Exception as e:
            self.error_signal.emit(LoggerText.error(f"Edge-TTS falló, usando voz local: {e}"))
            self._speak_pyttsx3(text)
            
        finally:
            with suppress(Exception):
                pygame.mixer.music.unload()

    async def _get_edge_bytes(self, text: str) -> bytes:
        """Descarga el audio pedacito por pedacito en RAM sin tocar el disco duro."""
        percent = int((self.rate - 175) / 1.5)
        percent = max(-50, min(80, percent)) 
        rate_str = f"{percent:+d}%"
        communicate = edge_tts.Communicate(text, self.edge_voice, rate=rate_str)
        audio_data = bytearray()
        
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.extend(chunk["data"])
                
        return bytes(audio_data)

    def _speak_pyttsx3(self, text: str):
        with suppress(Exception):
            self.current_engine = pyttsx3.init()
            if self.selected_voice_id:
                with suppress(Exception): 
                    self.current_engine.setProperty('voice', self.selected_voice_id)
            
            self.current_engine.setProperty('rate', self.rate)
            self.current_engine.setProperty('volume', self.volume)
            
            self.current_engine.say(text)
            self.current_engine.runAndWait()
            self.current_engine.stop()
                
        with suppress(Exception):
            if self.current_engine:
                del self.current_engine
        self.current_engine = None