# backend/services/triggers_service.py

import os
import cloudscraper
from urllib.parse import quote
from typing import List, Dict, Any, Tuple
from backend.utils.data_manager import DataManager

# --- IMPORTANTE: Importar el servicio de Rewards ---
from backend.services.rewards_service import RewardsService

# Endpoints de Kick
URL_REWARDS = "https://api.kick.com/public/v1/channels/rewards"

class TriggerService:
    """
    Servicio de Lógica para el Overlay Multimedia + Gestión de Recompensas de Kick.
    """
    def __init__(self, db_handler, server_worker):
        self.db = db_handler
        self.server = server_worker
        self.scraper = cloudscraper.create_scraper()
        
        self.rewards_api = RewardsService()
        
        self.VIDEO_EXTS = {'.mp4', '.webm'}
        self.AUDIO_EXTS = {'.mp3', '.wav', '.ogg'}

    # =========================================================================
    # REGIÓN 1: GESTIÓN DE API KICK (WRAPPER)
    # =========================================================================    
    def get_available_kick_rewards(self) -> list:
        return self.rewards_api.list_rewards()

    def sync_reward_to_kick(self, old_title: str, new_title: str, cost: int, color: str, description: str, is_active: bool) -> bool:
        """
        Sincroniza buscando primero por el nombre ANTIGUO para permitir renombrar.
        """
        rewards = self.rewards_api.list_rewards()
        target_id = None
        
        clean_old = old_title.strip().lower()
        clean_new = new_title.strip().lower()

        # 1. Buscar por nombre ANTIGUO
        if clean_old:
            for r in rewards:
                if r.get("title", "").strip().lower() == clean_old:
                    target_id = r.get("id")
                    break
        
        # 2. Si no, buscar por nombre NUEVO
        if not target_id:
            for r in rewards:
                if r.get("title", "").strip().lower() == clean_new:
                    target_id = r.get("id")
                    break
        
        # 3. Ejecutar pasando is_active
        if target_id:          
            return self.rewards_api.edit_reward(
                reward_id=target_id, 
                title=new_title, 
                cost=cost, 
                color=color, 
                description=description, 
                is_active=is_active # <--- IMPORTANTE: Pasa el estado (True/False)
            )
        else:
            return self.rewards_api.create_reward(
                title=new_title, 
                cost=cost, 
                color=color, 
                description=description, 
                is_active=is_active # <--- IMPORTANTE
            )

    def delete_reward_from_kick(self, title: str):
        self.rewards_api.delete_reward_by_title(title)

    # =========================================================================
    # REGIÓN 2: LÓGICA DE NEGOCIO "HIGHLANDER" (UNICIDAD)
    # =========================================================================
    def ensure_unique_assignment(self, current_filename: str, reward_title: str):
        if not reward_title: return

        clean_title = reward_title.strip().lower()
        triggers = self.db.get_all_triggers()
        
        for fname, config in triggers.items():
            if fname != current_filename:
                existing_cmd = config.get("cmd", "").strip().lower()
                
                if existing_cmd == clean_title:
                    # Desactivar el trigger conflictivo localmente
                    self.db.set_trigger(
                        cmd="", 
                        file=fname,
                        ftype=config.get("type", "audio"),
                        dur=config.get("dur", 0),
                        sc=config.get("scale", 1.0),
                        act=0, 
                        cost=config.get("cost", 0),
                        vol=config.get("volume", 100),
                        pos_x=config.get("pos_x", 0),
                        pos_y=config.get("pos_y", 0)
                    )

    # =========================================================================
    # REGIÓN 3: GESTIÓN DE ARCHIVOS Y DB
    # =========================================================================
    def get_local_ip_url(self) -> str:
        return "http://127.0.0.1:8081"

    def get_media_folder(self) -> str:
        return self.db.get("media_folder")

    def set_media_folder(self, path: str):
        self.db.set("media_folder", path)

    def is_overlay_active(self) -> bool:
        return self.db.get_bool("overlay_enabled")

    def set_overlay_active(self, active: bool):
        self.db.set("overlay_enabled", active)
        self.server.set_active(active)

    def set_random_pos(self, active: bool):
        self.db.set("random_pos", active)

    def get_media_files_with_config(self) -> List[Dict[str, Any]]:
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
                    config = triggers_map.get(f)
                    if not config:
                        config = {
                            "cmd": "", "active": 0,
                            "scale": 1.0, "volume": 100,
                            "dur": 0, "cost": 100
                        }
                    results.append({"filename": f, "type": ftype, "config": config})
        except Exception:
            return []
        return results

    def save_trigger(self, filename: str, ftype: str, data: Dict, sync_kick: bool = True) -> Tuple[bool, str]:
        """
        Guarda detectando cambio de nombre para actualizar Kick correctamente.
        """
        # --- PASO 1: RECUPERAR NOMBRE ANTERIOR ---
        # Antes de borrar, miramos qué nombre tenía este archivo en la DB
        old_config = self.db.get_all_triggers().get(filename, {})
        old_title = old_config.get("cmd", "")

        # --- PASO 2: LIMPIEZA DB ---
        self.db.delete_triggers_by_filename(filename) 

        # --- PASO 3: PREPARAR DATOS NUEVOS ---
        new_title = data.get("cmd", "").strip()
        cost = int(data.get("cost", 0))
        color = data.get("color", "#53fc18")
        desc = data.get("description", "Trigger KickMonitor")
        is_active = bool(data.get("active", 1))

        if not new_title:
            self.db.set_trigger(cmd="", file=filename, ftype=ftype, dur=0, sc=1.0, act=0, cost=0, vol=100, pos_x=0, pos_y=0)
            return True, "Trigger desactivado (sin nombre)"
            
        # --- PASO 4: GUARDAR LOCAL ---
        result = self.db.set_trigger(
            cmd=new_title.lower(),
            file=filename,
            ftype=ftype,
            dur=data.get("dur", 0),
            sc=data.get("scale", 1.0),
            act=data.get("active", 1),
            cost=cost,
            vol=data.get("volume", 100),
            pos_x=data.get("pos_x", 0),
            pos_y=data.get("pos_y", 0),
            color=color,         
            description=desc
        )

        # --- PASO 5: SINCRONIZAR CON KICK ---
        kick_msg = ""
        if sync_kick:
            # Pasamos old_title Y new_title
            success_kick = self.sync_reward_to_kick(old_title, new_title, cost, color, desc, is_active)
            if success_kick:
                kick_msg = " y sincronizada con Kick"
            else:
                kick_msg = " (Local OK, error en Kick)"

        if isinstance(result, tuple): return result
        return result, f"Recompensa configurada{kick_msg}"

    def delete_trigger_data(self, filename: str, reward_title: str):
        self.db.delete_triggers_by_filename(filename)
        if reward_title:
            self.delete_reward_from_kick(reward_title)

    def clear_all_data(self) -> bool:
        return self.db.clear_all_triggers()
    
    def sync_kick_states(self) -> int:
        """
        Descarga las recompensas de Kick y actualiza el estado (Activo/Inactivo)
        """
        try:
            # 1. Obtener lista real de Kick
            kick_rewards = self.rewards_api.list_rewards()
            if not kick_rewards:
                return 0

            # 2. Obtener configuración local
            local_triggers = self.db.get_all_triggers() # Esto devuelve un dict {filename: config}
            
            # 3. Crear mapa rápido de Kick: { 'nombre_comando': is_enabled }
            kick_map = {
                r.get("title", "").strip().lower(): r.get("is_enabled", False) 
                for r in kick_rewards
            }

            changes_count = 0

            # 4. Comparar y Sincronizar
            for filename, config in local_triggers.items():
                cmd = config.get("cmd", "").strip().lower()
                
                # Si el trigger local tiene un comando y ese comando existe en Kick
                if cmd and cmd in kick_map:
                    kick_is_active = kick_map[cmd]
                    local_is_active = bool(config.get("active", 0))

                    # SI HAY DISCREPANCIA: Gana Kick (La web es la verdad absoluta)
                    if kick_is_active != local_is_active:
                        self.db.update_active_state(filename, kick_is_active)
                        changes_count += 1
                        # print(f"[SYNC] Sincronizado {filename}: Local {local_is_active} -> Kick {kick_is_active}")

            return changes_count

        except Exception as e:
            # print(f"[ERROR SYNC] Falló la sincronización de estados: {e}")
            return 0
        
    def preview_media(self, filename: str, ftype: str, config: Dict):
        file_url = f"http://127.0.0.1:8081/media/{quote(filename)}"
        try:
            duration = int(float(config.get("dur", 0) or 0))
            scale = float(config.get("scale", 1.0) or 1.0)
            volume = int(float(config.get("volume", 100) or 100))
            pos_x = int(config.get("pos_x", 0))
            pos_y = int(config.get("pos_y", 0))

            payload = {
                "url": file_url,
                "type": ftype,
                "duration": duration * 1000,
                "scale": scale,
                "volume": volume,
                "pos_x": pos_x,
                "pos_y": pos_y,
                "random": self.db.get_bool("random_pos"),
                "user": "Streamer (Prueba)",
                "reward_name": config.get("cmd", "Test"),
                "input_text": ""
            }
            self.server.send_event("play_media", payload)
        except Exception as e: 
            print(f"Error Preview: {e}")

    def export_csv(self, path: str) -> bool:
        headers = ["Recompensa", "Archivo", "Tipo", "Duracion", "Escala", "Activo", "Costo", "Volumen"]
        data_rows = []
        triggers = self.db.get_all_triggers()
        for filename, cfg in triggers.items():
            ext = os.path.splitext(filename)[1].lower()
            ftype = "video" if ext in self.VIDEO_EXTS else "audio"
            data_rows.append([
                cfg.get("cmd", ""), filename, ftype,
                cfg.get("dur", 0), cfg.get("scale", 1.0),
                cfg.get("active", 1), cfg.get("cost", 0),
                cfg.get("volume", 100)
            ])
        return DataManager.export_csv(path, headers, data_rows)

    def import_csv(self, path: str) -> Tuple[int, int, List[str]]:
        required = ["recompensa", "archivo"]       
        rows, error_msg = DataManager.import_csv(path, required)       
        if rows is None: return 0, 0, [error_msg]
        
        count_ok, count_fail = 0, 0
        missing_files = []
        media_folder = self.get_media_folder()

        for row in rows:
            try:
                cmd = row.get("recompensa") or row.get("command")
                filename = row.get("archivo") or row.get("file")
                if not cmd or not filename:
                    count_fail += 1; continue

                dur = int(float(row.get("duracion", 0)))
                cost = int(float(row.get("costo", 0)))

                self.db.set_trigger(cmd.lower(), filename, "audio", dur, 1.0, 1, cost, 100, 0, 0)
                # Sincronizamos con defaults
                self.sync_reward_to_kick(cmd, cost, "#53fc18", "Importado", True)

                if media_folder and not os.path.exists(os.path.join(media_folder, filename)):
                    missing_files.append(filename)
                
                count_ok += 1
            except: count_fail += 1

        return count_ok, count_fail, missing_files