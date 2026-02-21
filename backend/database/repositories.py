# backend/database/repositories.py

from typing import Dict, List, Optional, Tuple, Any

class SettingsRepository:
    def __init__(self, conn): self.conn = conn

    def get(self, key: str, default="") -> str:
        row = self.conn.fetch_one("SELECT value FROM settings WHERE key=?", (key,))
        return row['value'] if row else default

    def set(self, key: str, value: Any):
        # TRUCO 3: Evaluamos el booleano en una sola línea (True=1, False=0)
        val_str = "1" if value is True else "0" if value is False else str(value)
        self.conn.execute_query("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, val_str))

class UsersRepository:
    def __init__(self, conn): self.conn = conn

    def get_user(self, slug: str) -> Optional[Dict]:
        # TRUCO 4: Usamos 'AS followers' en SQL para que coincida exactamente con el diccionario esperado
        query = "SELECT username, followers_count AS followers, profile_pic, user_id FROM kick_streamer WHERE slug=?"
        row = self.conn.fetch_one(query, (slug.lower(),))
        return dict(row) if row else None # Transformación automática

    def save_user(self, slug, username, followers, pic, chat_id, user_id=None):
        slug = slug.lower()
        # TRUCO 5: Usamos COALESCE puro en SQL en lugar de ensuciar Python concatenando strings
        query = """
            INSERT OR REPLACE INTO kick_streamer 
            (slug, username, followers_count, profile_pic, chatroom_id, is_banned, playback_url, user_id) 
            VALUES (?, ?, ?, ?, ?, 
                COALESCE((SELECT is_banned FROM kick_streamer WHERE slug=?), 0), 
                COALESCE((SELECT playback_url FROM kick_streamer WHERE slug=?), ''), 
                COALESCE(?, (SELECT user_id FROM kick_streamer WHERE slug=?))
            )
        """
        return self.conn.execute_query(query, (slug, username, followers, pic, chat_id, slug, slug, user_id, slug))

class EconomyRepository:
    def __init__(self, conn): self.conn = conn

    def add_points(self, username: str, amount: int) -> int:
        user = username.lower()
        self.conn.execute_query("INSERT OR IGNORE INTO data_users (username) VALUES (?)", (user,))
        self.conn.execute_query("UPDATE data_users SET points = points + ?, last_seen = CURRENT_TIMESTAMP WHERE username = ? AND is_paused = 0", (amount, user))
        return self.get_points(user)

    def spend_points(self, username: str, cost: int) -> bool:
        if cost <= 0: return True
        user = username.lower()
        if self.get_points(user) >= cost:
            self.conn.execute_query("UPDATE data_users SET points = points - ? WHERE username = ?", (cost, user))
            return True
        return False

    def get_points(self, username: str) -> int:
        res = self.conn.fetch_one("SELECT points FROM data_users WHERE username=?", (username.lower(),))
        return res['points'] if res else 0

    def get_all_users_points(self) -> List: 
        return self.conn.fetch_all("SELECT username, points, last_seen, is_paused, is_muted, role FROM data_users ORDER BY points DESC")

    def add_points_periodic(self, amount: int, minutes_window=10):
        query = f"UPDATE data_users SET points = points + ? WHERE last_seen >= datetime('now', '-{minutes_window} minutes') AND is_paused = 0"
        return self.conn.execute_query(query, (amount,))

    def set_paused(self, username: str, is_paused: bool): 
        return self.conn.execute_query("UPDATE data_users SET is_paused = ? WHERE username = ?", (int(is_paused), username.lower()))

    def set_muted(self, username: str, is_muted: bool):
        user = username.lower()
        self.conn.execute_query("INSERT OR IGNORE INTO data_users (username) VALUES (?)", (user,))
        return self.conn.execute_query("UPDATE data_users SET is_muted = ? WHERE username = ?", (int(is_muted), user))

    def is_muted(self, username: str) -> bool:
        res = self.conn.fetch_one("SELECT is_muted FROM data_users WHERE username=?", (username.lower(),))
        return bool(res and res['is_muted'])

    def update_role(self, username: str, role: str):
        user = username.lower()
        self.conn.execute_query("INSERT OR IGNORE INTO data_users (username) VALUES (?)", (user,))
        self.conn.execute_query("UPDATE data_users SET role = ? WHERE username = ?", (role, user))

    def delete_user(self, username: str): return self.conn.execute_query("DELETE FROM data_users WHERE username=?", (username,))
    
    def add_gamble_entry(self, username, game, result, profit, is_win):
        query = "INSERT INTO gamble_history (username, game_type, result_text, profit, is_win) VALUES (?, ?, ?, ?, ?)"
        return self.conn.execute_query(query, (username, game, result, profit, int(is_win)))

    def get_gamble_history(self, limit=50):
        return self.conn.fetch_all("SELECT timestamp, username, game_type, result_text, is_win FROM gamble_history ORDER BY id DESC LIMIT ?", (limit,))

    def clear_gamble_history(self): return self.conn.execute_query("DELETE FROM gamble_history")

class TriggersRepository:
    def __init__(self, conn): self.conn = conn

    def save_trigger(self, command, filename, ftype, duration=0, scale=1.0, is_active=1, cost=0, volume=100, pos_x=0, pos_y=0, color="#53fc18", description="Trigger KickMonitor", path="", random_pos=0):
        query = """
            INSERT OR REPLACE INTO triggers 
            (command, filename, type, duration, scale, is_active, cost, volume, pos_x, pos_y, color, description, path, random_pos) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        return self.conn.execute_query(query, (command.lower().strip(), filename, ftype, duration, scale, int(is_active), cost, volume, pos_x, pos_y, color, description, path, int(random_pos)))

    def get_trigger(self, command: str) -> Optional[Tuple]:
        return self.conn.fetch_one("SELECT filename, type, duration, scale, is_active, cost, volume, pos_x, pos_y, path, random_pos FROM triggers WHERE command=?", (command.lower(),))

    def get_all(self) -> Dict:
        data = {}
        for row in self.conn.fetch_all("SELECT * FROM triggers"):
            # TRUCO 6: Convertimos la fila entera en un diccionario y usamos '.get()' para procesar los nulos
            r = dict(row)
            data[r.pop('filename')] = {
                "cmd": r.get('command', ''),
                "dur": r.get('duration') or 0,
                "scale": r.get('scale') or 1.0,
                "active": r.get('is_active') if r.get('is_active') is not None else 1,
                "cost": r.get('cost') or 0,
                "volume": r.get('volume') if r.get('volume') is not None else 100,
                "type": r.get('type') or "audio",
                "pos_x": r.get('pos_x') or 0,
                "pos_y": r.get('pos_y') or 0,
                "color": r.get('color') or "#53fc18",
                "description": r.get('description') or "Trigger KickMonitor",
                "path": r.get('path') or "",           # <--- NUEVO
                "random_pos": r.get('random_pos') or 0 # <--- NUEVO
            }
        return data

    def delete_triggers_by_filename(self, filename: str): return self.conn.execute_query("DELETE FROM triggers WHERE filename=?", (filename,))
    def clear_all(self): return self.conn.execute_query("DELETE FROM triggers")
    def get_shop_items(self) -> List[Tuple[str, int]]: return self.conn.fetch_all("SELECT command, cost FROM triggers WHERE is_active = 1 ORDER BY cost ASC")
    def update_active_state(self, filename: str, is_active: bool): return self.conn.execute_query("UPDATE triggers SET is_active = ? WHERE filename = ?", (int(is_active), filename))

class ChatCommandsRepository:
    def __init__(self, conn): self.conn = conn

    def add_command(self, trigger, response, cooldown=5):
        trig = trigger.lower().strip()
        trig = trig if trig.startswith("!") else f"!{trig}"
        return self.conn.execute_query("INSERT OR REPLACE INTO custom_commands (trigger, response, is_active, cooldown) VALUES (?, ?, 1, ?)", (trig, response, cooldown))

    def get_response(self, trigger):
        res = self.conn.fetch_one("SELECT response FROM custom_commands WHERE trigger = ? AND is_active = 1", (trigger.lower(),))
        return res['response'] if res else None

    def get_details(self, trigger): return self.conn.fetch_one("SELECT response, is_active, cooldown FROM custom_commands WHERE trigger = ?", (trigger.lower(),))
    def get_all(self): return self.conn.fetch_all("SELECT trigger, response, is_active, cooldown FROM custom_commands")
    def delete(self, trigger): return self.conn.execute_query("DELETE FROM custom_commands WHERE trigger = ?", (trigger,))
    def toggle_active(self, trigger, is_active): return self.conn.execute_query("UPDATE custom_commands SET is_active = ? WHERE trigger = ?", (int(is_active), trigger))

class AutomationsRepository:
    def __init__(self, conn): self.conn = conn

    def set_text_alert(self, event_type, message, is_active):
        return self.conn.execute_query("INSERT OR REPLACE INTO text_alerts (event_type, message_template, is_active) VALUES (?, ?, ?)",(event_type, message, int(is_active)))

    def get_text_alert(self, event_type):
        row = self.conn.fetch_one("SELECT message_template, is_active FROM text_alerts WHERE event_type=?", (event_type,))
        return (row['message_template'], bool(row['is_active'])) if row else ("", False)

    def set_timer(self, name, message, interval, is_active):
        query = "INSERT OR REPLACE INTO timers (name, message, interval, is_active, last_run) VALUES (?, ?, ?, ?, COALESCE((SELECT last_run FROM timers WHERE name=?), 0))"
        return self.conn.execute_query(query, (name, message, interval, int(is_active), name))

    def get_timer(self, name):
        row = self.conn.fetch_one("SELECT message, interval, is_active FROM timers WHERE name=?", (name,))
        return (row['message'], row['interval'], bool(row['is_active'])) if row else ("", 15, False)

    def get_due_timers(self, current_time):
        rows = self.conn.fetch_all("SELECT name, message, interval, last_run FROM timers WHERE is_active = 1")
        # TRUCO 7: List Comprehension para crear y filtrar la lista en una sola línea
        return [(r['name'], r['message']) for r in rows if (r['last_run'] + (r['interval'] * 60)) <= current_time]

    def update_timer_run(self, name, timestamp):
        return self.conn.execute_query("UPDATE timers SET last_run = ? WHERE name = ?", (timestamp, name))