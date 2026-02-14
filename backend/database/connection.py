# backend/database/connection.py

import sqlite3
import os
from contextlib import suppress
from PyQt6.QtCore import QMutex, QMutexLocker
from backend.utils.paths import get_config_path

class DatabaseConnection:
    def __init__(self, db_name="kick_data.db"):
        self.db_path = os.path.join(get_config_path(), db_name)
        self.mutex = QMutex()
        
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
            self.conn.row_factory = sqlite3.Row 
            self._init_wal()
        except sqlite3.OperationalError as e:
            print(f"[DB_DEBUG] No se pudo abrir {self.db_path}: {e}")
            self.conn = sqlite3.connect(":memory:", check_same_thread=False)

    def _init_wal(self):
        with QMutexLocker(self.mutex), suppress(Exception):
            self.conn.execute("PRAGMA journal_mode=WAL;")
            self.conn.commit()

    def execute_query(self, sql, params=()):
        with QMutexLocker(self.mutex):
            try:
                # TRUCO 2: sqlite3 permite ejecutar directo desde la conexión sin crear un cursor manual
                self.conn.execute(sql, params)
                self.conn.commit()
                return True
            except Exception: 
                return False

    def fetch_one(self, sql, params=()):
        with QMutexLocker(self.mutex), suppress(Exception):
            return self.conn.execute(sql, params).fetchone()
        return None

    def fetch_all(self, sql, params=()):
        with QMutexLocker(self.mutex), suppress(Exception):
            return self.conn.execute(sql, params).fetchall()
        return []

    def close(self):
        with suppress(Exception):
            self.conn.close()