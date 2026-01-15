# services/overlay_service.py

import os
from urllib.parse import quote
from typing import List, Dict, Any, Tuple
from backend.utils.data_manager import DataManager

class OverlayService:
    """
    Servicio de Lógica para el Overlay Multimedia.
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
        local_ip = "127.0.0.1"
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
            print(f"[DEBUG_OVERLAY] Error escaneando carpeta: {e}")
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
        headers = ["Comando", "Archivo", "Tipo", "Duracion", "Escala", "Activo", "Costo", "Volumen"]
        data_rows = []
        
        triggers = self.db.get_all_triggers()
        for filename, cfg in triggers.items():
            ext = os.path.splitext(filename)[1].lower()
            if ext in self.VIDEO_EXTS: ftype = "video"
            elif ext in self.AUDIO_EXTS: ftype = "audio"
            else: ftype = cfg.get("type", "audio")

            data_rows.append([
                cfg.get("cmd", ""), filename, ftype,
                cfg.get("dur", 0), cfg.get("scale", 1.0),
                cfg.get("active", 1), cfg.get("cost", 0),
                cfg.get("volume", 100)
            ])
            
        return DataManager.export_csv(path, headers, data_rows)

    # --- NUEVA LÓGICA DE IMPORTAR ---
    def import_csv(self, path: str) -> Tuple[int, int, List[str]]:
        # 1. Definimos qué columnas SON OBLIGATORIAS para considerar este CSV válido
        required = ["comando", "archivo"]       
        # 2. Usamos el DataManager
        rows, error_msg = DataManager.import_csv(path, required)       
        if rows is None:
            return 0, 0, [error_msg]
        # 3. Procesamos los datos ya validados
        count_ok = 0
        count_fail = 0
        missing_files = []
        media_folder = self.get_media_folder()

        for row in rows:
            try:
                cmd = row.get("comando") or row.get("command")
                filename = row.get("archivo") or row.get("file")
                
                if not cmd or not filename:
                    count_fail += 1; continue

                try:
                    dur = int(float(row.get("duracion", 0)))
                    scale = float(row.get("escala", 1.0))
                    active = int(row.get("activo", 1))
                    cost = int(row.get("costo", 0))
                    vol = int(row.get("volumen", 100))
                except ValueError:
                    dur, scale, active, cost, vol = 0, 1.0, 1, 0, 100

                ext = os.path.splitext(filename)[1].lower()
                real_type = "video" if ext in self.VIDEO_EXTS else "audio"

                self.db.set_trigger(cmd, filename, real_type, dur, scale, active, cost, vol)

                if media_folder:
                    if not os.path.exists(os.path.join(media_folder, filename)):
                        missing_files.append(filename)
                
                count_ok += 1
            except Exception:
                count_fail += 1

        return count_ok, count_fail, missing_files

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