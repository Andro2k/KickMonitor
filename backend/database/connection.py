# backend/database/connection.py

import sqlite3
import os
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
            print(f"[DB_CRITICAL] No se pudo abrir {self.db_path}: {e}")
            self.conn = sqlite3.connect(":memory:", check_same_thread=False)

    def _init_wal(self):
        with QMutexLocker(self.mutex):
            try:
                self.conn.execute("PRAGMA journal_mode=WAL;")
                self.conn.commit()
            except Exception as e:
                print(f"[DB_ERROR] Fallo al iniciar WAL: {e}")

    def execute_query(self, sql, params=()):
        with QMutexLocker(self.mutex):
            try:
                self.conn.execute(sql, params)
                self.conn.commit()
                return True
            except Exception as e: 
                print(f"[DB_ERROR] Fallo en execute_query: {e} | SQL: {sql}")
                return False

    def execute_transaction(self, queries_and_params):
        """NUEVO: Ejecuta múltiples consultas en un solo acceso a disco (Rendimiento Extremo)"""
        with QMutexLocker(self.mutex):
            try:
                for sql, params in queries_and_params:
                    self.conn.execute(sql, params)
                self.conn.commit()
                return True
            except Exception as e:
                print(f"[DB_ERROR] Fallo en transacción, revirtiendo: {e}")
                self.conn.rollback()
                return False

    def fetch_one(self, sql, params=()):
        with QMutexLocker(self.mutex):
            try:
                return self.conn.execute(sql, params).fetchone()
            except Exception as e:
                print(f"[DB_ERROR] Fallo en fetch_one: {e} | SQL: {sql}")
                return None

    def fetch_all(self, sql, params=()):
        with QMutexLocker(self.mutex):
            try:
                return self.conn.execute(sql, params).fetchall()
            except Exception as e:
                print(f"[DB_ERROR] Fallo en fetch_all: {e} | SQL: {sql}")
                return []

    def close(self):
        try:
            self.conn.close()
        except Exception as e:
            print(f"[DB_ERROR] Fallo al cerrar conexión: {e}")