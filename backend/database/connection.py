# backend/database/connection.py
import sqlite3
import os
import sys
from PyQt6.QtCore import QMutex, QMutexLocker

from backend.utils.paths import get_app_data_path

class DatabaseConnection:
    def __init__(self, db_name="kick_data.db"):
        
        base_path = get_app_data_path()
        self.db_path = os.path.join(base_path, db_name)

        self.mutex = QMutex()
        
        # Conexión Segura
        try:
            # check_same_thread=False es necesario para PyQt
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
            self.conn.row_factory = sqlite3.Row 
            self._init_wal()
        except sqlite3.OperationalError as e:
            print(f"Error DB Crítico en ruta {self.db_path}: {e}")
            self.conn = sqlite3.connect(":memory:", check_same_thread=False)

    def _init_wal(self):
        with QMutexLocker(self.mutex):
            try:
                self.conn.execute("PRAGMA journal_mode=WAL;")
                self.conn.commit()
            except: pass

    def execute_query(self, sql, params=()):
        with QMutexLocker(self.mutex):
            try:
                c = self.conn.cursor(); c.execute(sql, params); self.conn.commit()
                return True
            except: return False

    def fetch_one(self, sql, params=()):
        with QMutexLocker(self.mutex):
            try:
                c = self.conn.cursor(); c.execute(sql, params); return c.fetchone()
            except: return None

    def fetch_all(self, sql, params=()):
        with QMutexLocker(self.mutex):
            try:
                c = self.conn.cursor(); c.execute(sql, params); return c.fetchall()
            except: return []

    def close(self):
        try: self.conn.close()
        except: pass