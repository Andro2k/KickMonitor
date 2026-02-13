# backend/database/repositories.py

from typing import Dict, List, Optional, Tuple, Any

# ==========================================
# 1. REPOSITORIO DE CONFIGURACIÓN
# ==========================================
class SettingsRepository:
    def __init__(self, conn):
        self.conn = conn

    def get(self, key: str, default="") -> str:
        row = self.conn.fetch_one("SELECT value FROM settings WHERE key=?", (key,))
        return row[0] if row else default

    def set(self, key: str, value: Any):
        if isinstance(value, bool): 
            value = "1" if value else "0"
        self.conn.execute_query("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))

# ==========================================
# 2. REPOSITORIO DE USUARIOS KICK
# ==========================================
class UsersRepository:
    def __init__(self, conn):
        self.conn = conn

    def get_user(self, slug: str) -> Optional[Dict]:
        query = "SELECT username, followers_count, profile_pic, user_id FROM kick_streamer WHERE slug=?"
        row = self.conn.fetch_one(query, (slug.lower(),))
        if row: 
            return {
                "username": row[0], "followers": row[1], 
                "profile_pic": row[2], "user_id": row[3]
            }
        return None

    def save_user(self, slug, username, followers, pic, chat_id, user_id=None):
        slug = slug.lower()
        user_id_clause = "?" if user_id else "COALESCE((SELECT user_id FROM kick_streamer WHERE slug=?), NULL)"
        
        params = [slug, username, followers, pic, chat_id]
        params.extend([slug, slug])
        params.append(user_id if user_id else slug)
        
        query = f"""
            INSERT OR REPLACE INTO kick_streamer 
            (slug, username, followers_count, profile_pic, chatroom_id, is_banned, playback_url, user_id) 
            VALUES (
                ?, ?, ?, ?, ?, 
                COALESCE((SELECT is_banned FROM kick_streamer WHERE slug=?), 0), 
                COALESCE((SELECT playback_url FROM kick_streamer WHERE slug=?), ''), 
                {user_id_clause}
            )
        """
        return self.conn.execute_query(query, tuple(params))

# ==========================================
# 3. REPOSITORIO DE ECONOMÍA (Puntos y Casino)
# ==========================================
class EconomyRepository:
    def __init__(self, conn):
        self.conn = conn

    # --- PUNTOS ---
    def add_points(self, username: str, amount: int) -> int:
        user = username.lower()
        self.conn.execute_query("INSERT OR IGNORE INTO data_users (username, points, is_paused, is_muted, role) VALUES (?, 0, 0, 0, 'user')", (user,))
        self.conn.execute_query("""
            UPDATE data_users 
            SET points = points + ?, last_seen = CURRENT_TIMESTAMP 
            WHERE username = ? AND is_paused = 0
        """, (amount, user))
        return self.get_points(user)

    def spend_points(self, username: str, cost: int) -> bool:
        if cost <= 0: return True
        user = username.lower()
        current = self.get_points(user)
        if current >= cost:
            self.conn.execute_query("UPDATE data_users SET points = points - ? WHERE username = ?", (cost, user))
            return True
        return False

    def get_points(self, username: str) -> int:
        res = self.conn.fetch_one("SELECT points FROM data_users WHERE username=?", (username.lower(),))
        return res[0] if res else 0

    def get_all_users_points(self) -> List: 
        return self.conn.fetch_all("SELECT username, points, last_seen, is_paused, is_muted, role FROM data_users ORDER BY points DESC")

    def add_points_periodic(self, amount: int, minutes_window=10):
        query = f"""
            UPDATE data_users 
            SET points = points + ? 
            WHERE last_seen >= datetime('now', '-{minutes_window} minutes') AND is_paused = 0
        """
        return self.conn.execute_query(query, (amount,))

    # --- ESTADO DE USUARIO (Mute/Pause/Role) ---
    def set_paused(self, username: str, is_paused: bool): 
        val = 1 if is_paused else 0
        return self.conn.execute_query("UPDATE data_users SET is_paused = ? WHERE username = ?", (val, username.lower()))

    def set_muted(self, username: str, is_muted: bool):
        user = username.lower()
        val = 1 if is_muted else 0
        # Aseguramos que exista antes de mutear
        self.conn.execute_query("INSERT OR IGNORE INTO data_users (username, points, is_paused, is_muted) VALUES (?, 0, 0, 0)", (user,))
        return self.conn.execute_query("UPDATE data_users SET is_muted = ? WHERE username = ?", (val, user))

    def is_muted(self, username: str) -> bool:
        res = self.conn.fetch_one("SELECT is_muted FROM data_users WHERE username=?", (username.lower(),))
        return res[0] == 1 if res else False

    def update_role(self, username: str, role: str):
        user = username.lower()
        self.conn.execute_query("INSERT OR IGNORE INTO data_users (username, points, is_paused, is_muted) VALUES (?, 0, 0, 0)", (user,))
        self.conn.execute_query("UPDATE data_users SET role = ? WHERE username = ?", (role, user))

    def delete_user(self, username: str): 
        return self.conn.execute_query("DELETE FROM data_users WHERE username=?", (username,))

    # --- HISTORIAL CASINO ---
    def add_gamble_entry(self, username, game, result, profit, is_win):
        query = "INSERT INTO gamble_history (username, game_type, result_text, profit, is_win) VALUES (?, ?, ?, ?, ?)"
        return self.conn.execute_query(query, (username, game, result, profit, 1 if is_win else 0))

    def get_gamble_history(self, limit=50):
        return self.conn.fetch_all("SELECT timestamp, username, game_type, result_text, is_win FROM gamble_history ORDER BY id DESC LIMIT ?", (limit,))

    def clear_gamble_history(self):
        return self.conn.execute_query("DELETE FROM gamble_history")

# ==========================================
# 4. REPOSITORIO DE TRIGGERS (Overlay Multimedia)
# ==========================================
class TriggersRepository:
    def __init__(self, conn):
        self.conn = conn

    # 1. MODIFICAMOS SAVE_TRIGGER PARA INCLUIR COLOR Y DESCRIPCION
    def save_trigger(self, command, filename, ftype, duration=0, scale=1.0, is_active=1, 
                     cost=0, volume=100, pos_x=0, pos_y=0, 
                     color="#53fc18", description="Trigger KickMonitor"): # <--- Nuevos argumentos
        cmd = command.lower().strip()

        query = """
            INSERT OR REPLACE INTO triggers 
            (command, filename, type, duration, scale, is_active, cost, volume, pos_x, pos_y, color, description) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        return self.conn.execute_query(query, (
            cmd, filename, ftype, duration, scale, 1 if is_active else 0, 
            cost, volume, pos_x, pos_y, color, description
        ))

    def get_trigger(self, command: str) -> Optional[Tuple]:
        query = "SELECT filename, type, duration, scale, is_active, cost, volume, pos_x, pos_y FROM triggers WHERE command=?"
        return self.conn.fetch_one(query, (command.lower(),))

    def get_all(self) -> Dict:
        # Aseguramos traer todas las columnas, incluidas color y descripcion
        query = "SELECT filename, command, duration, scale, is_active, cost, volume, type, pos_x, pos_y, color, description FROM triggers"
        rows = self.conn.fetch_all(query)
        data = {}
        
        for r in rows:
            # Manejo seguro de valores nulos
            vol = r['volume'] if r['volume'] is not None else 100
            ftype = r['type'] if 'type' in r.keys() and r['type'] else "audio"
            px = r['pos_x'] if 'pos_x' in r.keys() and r['pos_x'] is not None else 0
            py = r['pos_y'] if 'pos_y' in r.keys() and r['pos_y'] is not None else 0

            act = r['is_active']
            if act is None: act = 1
            
            # Nuevos campos
            col = r['color'] if 'color' in r.keys() and r['color'] else "#53fc18"
            desc = r['description'] if 'description' in r.keys() and r['description'] else "Trigger KickMonitor"

            data[r['filename']] = {
                "cmd": r['command'], 
                "dur": r['duration'] or 0, 
                "scale": r['scale'] or 1.0, 
                "active": act,
                "cost": r['cost'] or 0, 
                "volume": vol,
                "type": ftype,
                "pos_x": px,
                "pos_y": py,
                "color": col,
                "description": desc
            }
        return data

    def delete_triggers_by_filename(self, filename: str): 
        return self.conn.execute_query("DELETE FROM triggers WHERE filename=?", (filename,))

    def clear_all(self): 
        return self.conn.execute_query("DELETE FROM triggers")

    def get_shop_items(self) -> List[Tuple[str, int]]:
        query = "SELECT command, cost FROM triggers WHERE is_active = 1 ORDER BY cost ASC"
        return self.conn.fetch_all(query)
    
    def update_active_state(self, filename: str, is_active: bool):
        """Actualiza solo el estado activo/inactivo de un archivo específico."""
        val = 1 if is_active else 0
        query = "UPDATE triggers SET is_active = ? WHERE filename = ?"
        return self.conn.execute_query(query, (val, filename))

# ==========================================
# 5. REPOSITORIO DE COMANDOS DE TEXTO
# ==========================================
class ChatCommandsRepository:
    def __init__(self, conn):
        self.conn = conn

    def add_command(self, trigger, response, cooldown=5):
        trig = trigger.lower().strip()
        if not trig.startswith("!"): trig = "!" + trig
        query = "INSERT OR REPLACE INTO custom_commands (trigger, response, is_active, cooldown) VALUES (?, ?, 1, ?)"
        return self.conn.execute_query(query, (trig, response, cooldown))

    def get_response(self, trigger):
        query = "SELECT response FROM custom_commands WHERE trigger = ? AND is_active = 1"
        res = self.conn.fetch_one(query, (trigger.lower(),))
        return res[0] if res else None

    def get_details(self, trigger):
        return self.conn.fetch_one("SELECT response, is_active, cooldown FROM custom_commands WHERE trigger = ?", (trigger.lower(),))

    def get_all(self): 
        return self.conn.fetch_all("SELECT trigger, response, is_active, cooldown FROM custom_commands")
    
    def delete(self, trigger): 
        return self.conn.execute_query("DELETE FROM custom_commands WHERE trigger = ?", (trigger,))

    def toggle_active(self, trigger, is_active):
        val = 1 if is_active else 0
        return self.conn.execute_query("UPDATE custom_commands SET is_active = ? WHERE trigger = ?", (val, trigger))

# ==========================================
# 6. REPOSITORIO DE AUTOMATIZACIONES (Alertas & Timers)
# ==========================================
class AutomationsRepository:
    def __init__(self, conn):
        self.conn = conn

    # --- TEXT ALERTS ---
    def set_text_alert(self, event_type, message, is_active):
        val = 1 if is_active else 0
        return self.conn.execute_query(
            "INSERT OR REPLACE INTO text_alerts (event_type, message_template, is_active) VALUES (?, ?, ?)",
            (event_type, message, val)
        )

    def get_text_alert(self, event_type):
        row = self.conn.fetch_one("SELECT message_template, is_active FROM text_alerts WHERE event_type=?", (event_type,))
        if row: return row[0], bool(row[1])
        return "", False

    # --- TIMERS ---
    def set_timer(self, name, message, interval, is_active):
        val = 1 if is_active else 0
        query = """
            INSERT OR REPLACE INTO timers 
            (name, message, interval, is_active, last_run) 
            VALUES (?, ?, ?, ?, COALESCE((SELECT last_run FROM timers WHERE name=?), 0))
        """
        return self.conn.execute_query(query, (name, message, interval, val, name))

    def get_timer(self, name):
        row = self.conn.fetch_one("SELECT message, interval, is_active FROM timers WHERE name=?", (name,))
        if row: return row[0], row[1], bool(row[2])
        return "", 15, False

    def get_due_timers(self, current_time):
        rows = self.conn.fetch_all("SELECT name, message, interval, last_run FROM timers WHERE is_active = 1")
        due = []
        for r in rows:
            name, msg, interval, last_run = r[0], r[1], r[2], r[3]
            if (last_run + (interval * 60)) <= current_time:
                due.append((name, msg))
        return due

    def update_timer_run(self, name, timestamp):
        self.conn.execute_query("UPDATE timers SET last_run = ? WHERE name = ?", (timestamp, name))