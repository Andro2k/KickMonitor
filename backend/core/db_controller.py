# backend/core/db_controller.py

import os
from typing import List, Optional, Any, Dict
from contextlib import suppress
from PyQt6.QtCore import QMutexLocker 

# --- INFRAESTRUCTURA ---
from backend.database.connection import DatabaseConnection
from backend.database.repositories import (
    SettingsRepository, UsersRepository, 
    EconomyRepository, TriggersRepository,
    ChatCommandsRepository, AutomationsRepository)

class DBHandler:
    # =========================================================================
    # REGIÓN 1: ESQUEMAS Y DEFAULTS
    # =========================================================================
    TABLE_SCHEMAS = {
        "settings": "key TEXT PRIMARY KEY, value TEXT",
        "kick_streamer": """
            slug TEXT PRIMARY KEY, username TEXT, followers_count INTEGER, 
            profile_pic TEXT, kick_id INTEGER, user_id INTEGER, chatroom_id TEXT, 
            is_banned INTEGER DEFAULT 0, playback_url TEXT DEFAULT '', 
            vod_enabled INTEGER DEFAULT 0, subscription_enabled INTEGER DEFAULT 0, 
            verified INTEGER DEFAULT 0, can_host INTEGER DEFAULT 0, bio TEXT DEFAULT ''
        """,
        "triggers": """
            command TEXT PRIMARY KEY, filename TEXT, type TEXT, 
            duration INTEGER DEFAULT 0, scale REAL DEFAULT 1.0, 
            is_active INTEGER DEFAULT 1, cost INTEGER DEFAULT 0, volume INTEGER DEFAULT 100,
            pos_x INTEGER DEFAULT 0, pos_y INTEGER DEFAULT 0,
            color TEXT DEFAULT '#53fc18', description TEXT DEFAULT 'Trigger KickMonitor',
            path TEXT DEFAULT '', random_pos INTEGER DEFAULT 0
        """,
        "data_users": """
            username TEXT PRIMARY KEY, points INTEGER DEFAULT 0, 
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
            is_paused INTEGER DEFAULT 0, is_muted INTEGER DEFAULT 0,
            role TEXT DEFAULT ''
        """,
        "custom_commands": "trigger TEXT PRIMARY KEY, response TEXT, is_active INTEGER DEFAULT 1, cooldown INTEGER DEFAULT 5",
        "gamble_history": """
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            username TEXT, game_type TEXT, result_text TEXT, 
            profit INTEGER, is_win INTEGER
        """,
        "text_alerts": "event_type TEXT PRIMARY KEY, message_template TEXT, is_active INTEGER DEFAULT 1",
        "timers": "name TEXT PRIMARY KEY, message TEXT, interval INTEGER DEFAULT 15, is_active INTEGER DEFAULT 0, last_run REAL DEFAULT 0",
    }
    
    DEFAULT_SETTINGS = {
        "overlay_enabled": "1", "random_pos": "0", "media_folder": "", "filter_enabled": "0", 
        "client_id": "", "client_secret": "", "redirect_uri": "http://127.0.0.1:8080/callback",
        "kick_username": "", "chatroom_id": "", "tts_command": "!voz", "voice_id": "", "voice_rate": "175", "voice_vol": "100",
        "points_name": "Créditos", "points_per_msg": "10", "points_per_min": "20", "points_command": "!puntos",
        "spotify_enabled": "0", "spotify_client_id": "", "spotify_secret": "", "spotify_redirect_uri": "http://127.0.0.1:8888",
        "music_cmd_song": "!song", "music_cmd_skip": "!skip", "music_cmd_pause": "!pause", "music_cmd_request": "!sr",
        "gamble_enabled": "1", "gamble_win_rate": "45", "gamble_multiplier": "2.0", "gamble_min": "10", "gamble_max": "1000", "slots_jackpot_x": "10",
        "roulette_multi_num": "35.0", "roulette_multi_col": "2.0", "highcard_multiplier": "2.0", 
        "auto_connect": "0", "minimize_to_tray": "0","app_language": "es", "date_format": "24h", "debug_mode": "0",
    }

    # =========================================================================
    # REGIÓN 2: CICLO DE VIDA E INICIALIZACIÓN
    # =========================================================================
    def __init__(self, db_name: str = "kick_data.db"):
        self.conn_handler = DatabaseConnection(db_name)     
        
        self.settings = SettingsRepository(self.conn_handler)
        self.users = UsersRepository(self.conn_handler)
        self.economy = EconomyRepository(self.conn_handler)
        self.triggers = TriggersRepository(self.conn_handler)
        self.commands = ChatCommandsRepository(self.conn_handler)
        self.automations = AutomationsRepository(self.conn_handler)
        self._settings_cache = {}
        
        self._init_db()
        self._run_migrations()

    def _init_db(self):
        """Crea tablas y configuración por defecto."""
        with QMutexLocker(self.conn_handler.mutex):
            try:
                for table, schema in self.TABLE_SCHEMAS.items():
                    self.conn_handler.conn.execute(f"CREATE TABLE IF NOT EXISTS {table} ({schema})")                
                
                self.conn_handler.conn.executemany(
                    "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", 
                    self.DEFAULT_SETTINGS.items()
                )
                self.conn_handler.conn.commit()
            except Exception as e:
                print(f"[DB_DEBUG] Error Init: {e}")

    def _run_migrations(self):
        """Verifica y crea columnas faltantes en DB existente."""
        migrations = {
            "kick_streamer": [
                ("bio", "TEXT DEFAULT ''"), ("can_host", "INTEGER DEFAULT 0"),
                ("verified", "INTEGER DEFAULT 0"), ("subscription_enabled", "INTEGER DEFAULT 0"),
                ("vod_enabled", "INTEGER DEFAULT 0"), ("is_banned", "INTEGER DEFAULT 0"),
                ("user_id", "INTEGER")
            ],
            "triggers": [
                ("duration", "INTEGER DEFAULT 0"), ("scale", "REAL DEFAULT 1.0"),
                ("is_active", "INTEGER DEFAULT 1"), ("cost", "INTEGER DEFAULT 0"),
                ("volume", "INTEGER DEFAULT 100"), ("pos_x", "INTEGER DEFAULT 0"), 
                ("pos_y", "INTEGER DEFAULT 0"), ("color", "TEXT DEFAULT '#53fc18'"),
                ("description", "TEXT DEFAULT 'Trigger KickMonitor'"),
                ("path", "TEXT DEFAULT ''"), ("random_pos", "INTEGER DEFAULT 0")
            ],
            "data_users": [("is_paused", "INTEGER DEFAULT 0"), ("is_muted", "INTEGER DEFAULT 0"), ("role", "TEXT DEFAULT ''")],
            "custom_commands": [("cooldown", "INTEGER DEFAULT 5")],
            "timers": [("interval", "INTEGER DEFAULT 15"), ("last_run", "REAL DEFAULT 0")]
        }
        
        with QMutexLocker(self.conn_handler.mutex):
            cursor = self.conn_handler.conn.cursor()
            for table, cols in migrations.items():
                try:
                    cursor.execute(f"PRAGMA table_info({table})")
                    existing_cols = {row['name'] for row in cursor.fetchall()}                  
                    missing_cols = [col for col in cols if col[0] not in existing_cols]
                    
                    for col_name, col_def in missing_cols:
                        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}")
                        
                except Exception as e:
                    print(f"[DB_DEBUG] Error migrando {table}: {e}")
            self.conn_handler.conn.commit()

    # =========================================================================
    # REGIÓN 3: FACHADA - CONFIGURACIÓN (SETTINGS)
    # =========================================================================
    def get(self, key: str, default: str = "") -> str: 
        if key not in self._settings_cache:
            self._settings_cache[key] = self.settings.get(key, default)
            
        return self._settings_cache[key]

    def set(self, key: str, val: Any): 
        self.settings.set(key, val)
        self._settings_cache[key] = str(val)
        
    def get_bool(self, key: str) -> bool: 
        return self.get(key) == "1"       
    
    def get_int(self, key: str, default: int = 0) -> int: 
        with suppress(ValueError, TypeError):
            return int(self.get(key, str(default)))
        return default

    # =========================================================================
    # REGIÓN 4: FACHADA - USUARIOS KICK
    # =========================================================================
    def save_kick_user(self, slug, username, followers, pic, chat_id, user_id=None):
        return self.users.save_user(slug, username, followers, pic, chat_id, user_id)    
    def get_kick_user(self, slug: str) -> Optional[Dict]:
        return self.users.get_user(slug)

    # =========================================================================
    # REGIÓN 5: FACHADA - ECONOMÍA (PUNTOS & CASINO)
    # =========================================================================
    def add_points(self, user: str, amount: int) -> int: return self.economy.add_points(user, amount)
    def spend_points(self, user: str, cost: int) -> bool: return self.economy.spend_points(user, cost)
    def get_points(self, user: str) -> int: return self.economy.get_points(user)
    
    def get_all_points(self) -> List: return self.economy.get_all_users_points()
    def delete_user_points(self, user: str): return self.economy.delete_user(user)
    def add_points_to_active_users(self, amount: int, minutes: int = 10): return self.economy.add_points_periodic(amount, minutes)
    
    def set_user_paused(self, user: str, paused: bool): return self.economy.set_paused(user, paused)
    def set_user_muted(self, user: str, muted: bool): return self.economy.set_muted(user, muted)
    def is_muted(self, user: str) -> bool: return self.economy.is_muted(user)
    def update_user_role(self, user: str, role: str): return self.economy.update_role(user, role)
    
    def add_gamble_entry(self, user, game, res, profit, win): return self.economy.add_gamble_entry(user, game, res, profit, win)
    def get_gamble_history(self, limit=50): return self.economy.get_gamble_history(limit)
    def clear_gamble_history(self): return self.economy.clear_gamble_history()

    # =========================================================================
    # REGIÓN 6: FACHADA - CARACTERÍSTICAS (COMMANDS, OVERLAY, ALERTS)
    # =========================================================================
    def set_trigger(self, cmd, file, ftype, dur=0, sc=1.0, act=1, cost=0, vol=100, pos_x=0, pos_y=0, color="#53fc18", description="Trigger KickMonitor", path="", random_pos=0):
        return self.triggers.save_trigger(cmd, file, ftype, dur, sc, act, cost, vol, pos_x, pos_y, color, description, path, random_pos)
    def update_active_state(self, filename: str, is_active: bool): return self.triggers.update_active_state(filename, is_active)    
    def get_trigger_file(self, cmd: str): return self.triggers.get_trigger(cmd)
    def delete_triggers_by_filename(self, fname: str): return self.triggers.delete_triggers_by_filename(fname)
    def get_all_triggers(self) -> Dict: return self.triggers.get_all()
    def clear_all_triggers(self): return self.triggers.clear_all()
    def get_active_shop_items(self) -> List: return self.triggers.get_shop_items()

    def add_command(self, trig, resp, cd=5): return self.commands.add_command(trig, resp, cd)
    def get_custom_response(self, trig: str) -> Optional[str]: return self.commands.get_response(trig)
    def get_command_details(self, trig: str): return self.commands.get_details(trig)
    def get_all_commands(self) -> List: return self.commands.get_all()
    def delete_command(self, trig: str): return self.commands.delete(trig)
    def toggle_command_active(self, trig: str, active: bool): return self.commands.toggle_active(trig, active)

    def set_text_alert(self, type, msg, active): return self.automations.set_text_alert(type, msg, active)
    def get_text_alert(self, type): return self.automations.get_text_alert(type)
    
    def set_timer(self, name, msg, interval, active): return self.automations.set_timer(name, msg, interval, active)
    def get_timer(self, name): return self.automations.get_timer(name)
    def get_due_timers(self, current_time): return self.automations.get_due_timers(current_time)
    def update_timer_run(self, name, ts): return self.automations.update_timer_run(name, ts)

    # =========================================================================
    # REGIÓN 7: GESTIÓN DE DATOS Y MANTENIMIENTO
    # =========================================================================
    def get_db_path(self) -> str:
        return os.path.abspath(self.conn_handler.db_path)

    def factory_reset_user(self):
        keys_to_wipe = [
            ("kick_username",), ("chatroom_id",), ("client_id",), ("client_secret",), 
            ("spotify_client_id",), ("spotify_secret",), ("spotify_enabled",)
        ]
        with QMutexLocker(self.conn_handler.mutex):
            self.conn_handler.conn.executemany("UPDATE settings SET value='' WHERE key=?", keys_to_wipe)
            self.conn_handler.conn.execute("DELETE FROM kick_streamer")
            self.conn_handler.conn.commit()
        self._settings_cache.clear()

    def wipe_economy_data(self):
        with QMutexLocker(self.conn_handler.mutex):
            self.conn_handler.conn.execute("UPDATE data_users SET points = 0")
            self.conn_handler.conn.execute("DELETE FROM gamble_history")
            self.conn_handler.conn.commit()