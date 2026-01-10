# services/overlay_service.py

import csv
import os
import socket
from urllib.parse import quote
from typing import List, Dict, Any, Tuple

class OverlayService:
    """
    Servicio de Lógica para el Overlay Multimedia.
    Gestiona archivos locales, triggers en DB, importación CSV y comunicación con el servidor.
    """
    def __init__(self, db_handler, server_worker):
        self.db = db_handler
        self.server = server_worker
        
        # Extensiones soportadas
        self.VIDEO_EXTS = {'.mp4', '.webm'}
        self.AUDIO_EXTS = {'.mp3', '.wav', '.ogg'}

    # =========================================================================
    # REGIÓN 1: CONFIGURACIÓN GENERAL Y ESTADO
    # =========================================================================
    def get_local_ip_url(self) -> str:
        """
        Detecta la IP local de la máquina para mostrar la URL que se debe poner en OBS.
        """
        local_ip = "127.0.0.1"
        try:
            # Usamos socket UDP para obtener la IP real de la interfaz (no envía datos)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80)) 
            local_ip = s.getsockname()[0]
            s.close()
        except Exception: 
            pass # Fallback a localhost si no hay red
            
        return f"http://{local_ip}:8081"

    def get_media_folder(self) -> str:
        return self.db.get("media_folder")

    def set_media_folder(self, path: str):
        self.db.set("media_folder", path)

    def is_overlay_active(self) -> bool:
        return self.db.get_bool("overlay_enabled")

    def set_overlay_active(self, active: bool):
        """Activa/Desactiva el servidor y guarda la preferencia."""
        self.db.set("overlay_enabled", active)
        self.server.set_active(active)

    def set_random_pos(self, active: bool):
        self.db.set("random_pos", active)

    # =========================================================================
    # REGIÓN 2: GESTIÓN DE ARCHIVOS MULTIMEDIA
    # =========================================================================
    def get_media_files_with_config(self) -> List[Dict[str, Any]]:
        """
        Escanea la carpeta de medios y fusiona los archivos encontrados con la DB.
        Los archivos nuevos aparecen desactivados por defecto.
        """
        folder = self.get_media_folder()
        if not folder or not os.path.exists(folder):
            return []

        triggers_map = self.db.get_all_triggers()
        results = []
        
        try:
            all_files = os.listdir(folder)
            
            for f in sorted(all_files):
                ext = os.path.splitext(f)[1].lower()
                
                ftype = None
                if ext in self.VIDEO_EXTS: ftype = "video"
                elif ext in self.AUDIO_EXTS: ftype = "audio"
                
                if ftype:
                    # Buscamos config previa en DB
                    config = triggers_map.get(f)
                    
                    if not config:
                        # Si es archivo nuevo, creamos config default (APAGADA)
                        config = {
                            "cmd": "", "active": 0,
                            "scale": 1.0, "volume": 100,
                            "dur": 0, "cost": 0
                        }
                    
                    results.append({
                        "filename": f,
                        "type": ftype,
                        "config": config 
                    })
        except Exception as e:
            print(f"[OverlayService] Error escaneando carpeta: {e}")
            return []
            
        return results

    def save_trigger(self, filename: str, ftype: str, data: Dict) -> Tuple[bool, str]:
        """
        Guarda o actualiza la configuración de una alerta específica.
        """
        # 1. Limpieza previa para evitar duplicados
        self.db.delete_triggers_by_filename(filename)
        
        # 2. Validación de comando
        cmd = data.get("cmd", "").strip()
        if not cmd:
            return False, "El comando es obligatorio"
            
        if not cmd.startswith("!"): 
            cmd = "!" + cmd
        
        # 3. Guardado en DB (Usando kwargs correctos para el Facade)
        result = self.db.set_trigger(
            cmd=cmd,
            file=filename,
            ftype=ftype,
            dur=data.get("dur", 0),
            sc=data.get("scale", 1.0),
            act=data.get("active", 1),
            cost=data.get("cost", 0),
            vol=data.get("volume", 100)
        )
        
        # Manejo robusto de respuesta (puede ser bool o tupla)
        if isinstance(result, tuple):
            return result
        return result, "Guardado correctamente" if result else "Error al guardar en DB"

    def clear_all_data(self) -> bool:
        """Elimina TODOS los triggers configurados."""
        result = self.db.clear_all_triggers()
        if isinstance(result, tuple):
            return result[0]
        return result

    # =========================================================================
    # REGIÓN 3: PERSISTENCIA CSV (IMPORTAR / EXPORTAR)
    # =========================================================================
    def export_csv(self, path: str) -> bool:
        """Exporta la configuración a CSV calculando el tipo de archivo real."""
        try:
            data_map = self.db.get_all_triggers()
            
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Comando", "Archivo", "Tipo", "Duracion", "Escala", "Activo", "Costo", "Volumen"])
                
                for filename, cfg in data_map.items():
                    # Recalcular tipo basado en extensión para consistencia
                    ext = os.path.splitext(filename)[1].lower()
                    
                    if ext in self.VIDEO_EXTS: ftype = "video"
                    elif ext in self.AUDIO_EXTS: ftype = "audio"
                    else: ftype = cfg.get("type", "audio")
                    
                    writer.writerow([
                        cfg.get("cmd", ""), filename, ftype,
                        cfg.get("dur", 0), cfg.get("scale", 1.0),
                        cfg.get("active", 1), cfg.get("cost", 0),
                        cfg.get("volume", 100)
                    ])
            return True
        except Exception as e:
            print(f"[Export Error] {e}")
            return False

    def import_csv(self, path: str) -> Tuple[int, int, List[str]]:
        """Importa triggers forzando la detección del tipo de archivo real."""
        count_ok = 0
        count_fail = 0
        missing_files = []
        media_folder = self.get_media_folder()

        try:
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader, [])
                
                # Validación básica de cabeceras
                h_lower = [h.lower() for h in headers]
                valid_overlay = ("comando" in h_lower or "command" in h_lower) and \
                                ("archivo" in h_lower or "file" in h_lower)
                
                if not valid_overlay:
                    return 0, 0, ["El archivo no es un CSV de Alertas válido."]

                # Detección de formato (columnas nuevas vs viejas)
                is_new_format = "tipo" in h_lower or "type" in h_lower or len(headers) >= 8

                for row in reader:
                    if len(row) < 2:
                        count_fail += 1; continue
                        
                    try:
                        cmd = row[0]
                        filename = row[1]
                        
                        # Valores Default
                        dur, scale, active, cost, vol = 0, 1.0, 1, 0, 100

                        try:
                            if is_new_format and len(row) >= 8:
                                dur = int(float(row[3]))
                                scale = float(row[4])
                                active = int(row[5])
                                cost = int(row[6])
                                vol = int(row[7])
                            else:
                                # Fallback formato legacy
                                dur = int(float(row[2])) if len(row) > 2 else 0
                                scale = float(row[3]) if len(row) > 3 else 1.0
                                active = int(row[4]) if len(row) > 4 else 1
                                cost = int(row[5]) if len(row) > 5 else 0
                                vol = int(row[6]) if len(row) > 6 else 100
                        except ValueError:
                            pass # Usamos defaults si falla el parseo numérico

                        # --- CORRECCIÓN DE TIPO ---
                        # Ignoramos la columna 'tipo' del CSV y confiamos en la extensión real
                        ext = os.path.splitext(filename)[1].lower()
                        real_type = "video" if ext in self.VIDEO_EXTS else "audio"
                        
                        # Guardamos en DB con argumentos posicionales (orden del Facade)
                        # Facade: set_trigger(cmd, file, ftype, dur, sc, act, cost, vol)
                        self.db.set_trigger(cmd, filename, real_type, dur, scale, active, cost, vol)
                        
                        # Verificación de existencia física (para reporte de errores)
                        if media_folder:
                            full_path = os.path.join(media_folder, filename)
                            if not os.path.exists(full_path):
                                missing_files.append(filename)
                        
                        count_ok += 1
                    except Exception:
                        count_fail += 1
                        
            return count_ok, count_fail, missing_files
            
        except Exception as e:
            print(f"[Import Error] {e}")
            return 0, 0, [str(e)]

    # =========================================================================
    # REGIÓN 4: PREVISUALIZACIÓN (TEST)
    # =========================================================================
    def preview_media(self, filename: str, ftype: str, config: Dict):
        """
        Envía un evento inmediato al Overlay Server para probar la alerta.
        """
        file_url = f"http://127.0.0.1:8081/media/{quote(filename)}"
        
        payload = {
            "url": file_url,
            "type": ftype,
            "duration": config.get("dur", 0),
            "scale": config.get("scale", 1.0),
            "volume": config.get("volume", 100),
            "random": self.db.get_bool("random_pos")
        }
        
        self.server.send_event("play_media", payload)