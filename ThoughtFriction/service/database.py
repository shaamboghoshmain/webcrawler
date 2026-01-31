import sqlite3
from datetime import datetime
from .config import settings
from .models import SessionLog

class Database:
    def __init__(self):
        self.db_path = settings.DB_PATH
        self._init_db()

    def _get_conn(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                mode TEXT,
                duration_seconds INTEGER,
                word_count INTEGER,
                reflection TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def save_session(self, session: SessionLog):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO sessions (timestamp, mode, duration_seconds, word_count, reflection)
            VALUES (?, ?, ?, ?, ?)
        ''', (session.timestamp.isoformat(), session.mode, session.duration_seconds, session.word_count, session.reflection))
        conn.commit()
        conn.close()

    def get_stats(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*), mode FROM sessions GROUP BY mode')
        counts = cursor.fetchall()
        
        cursor.execute('SELECT AVG(duration_seconds) FROM sessions WHERE mode="blank"')
        avg_blank_duration = cursor.fetchone()[0] or 0
        
        total_sessions = sum(c[0] for c in counts)
        blank_sessions = next((c[0] for c in counts if c[1] == 'blank'), 0)
        ai_sessions = next((c[0] for c in counts if c[1] == 'ai'), 0)
        
        conn.close()
        
        return {
            "total_sessions": total_sessions,
            "blank_sessions": blank_sessions,
            "ai_sessions": ai_sessions,
            "avg_blank_duration": avg_blank_duration
        }

db = Database()
