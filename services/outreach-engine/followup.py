import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(os.getenv("DB_PATH", "/app/data/career_tracker.db"))

class FollowupManager:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path

    def get_connection(self):
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.execute("PRAGMA journal_mode = MEMORY;")
        conn.execute("PRAGMA synchronous = OFF;")
        return conn

    def schedule_cadence(self, outreach_log_id: int):
        """
        Schedules a 3-step follow-up sequence: Day 3, Day 7, Day 14.
        """
        now = datetime.utcnow()
        steps = [
            (outreach_log_id, 1, (now + timedelta(days=3)).strftime("%Y-%m-%d"), "Polite Check-in"),
            (outreach_log_id, 2, (now + timedelta(days=7)).strftime("%Y-%m-%d"), "Value-add Architecture Insight"),
            (outreach_log_id, 3, (now + timedelta(days=14)).strftime("%Y-%m-%d"), "Graceful Closeout")
        ]
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT INTO followup_schedules (outreach_log_id, step_number, due_date, step_label, status)
                VALUES (?, ?, ?, ?, 'pending')
            """, steps)
            conn.commit()
            print(f"[Followup] Scheduled 3-step cadence for outreach ID {outreach_log_id}")

    def get_due_followups(self) -> list[dict]:
        """
        Returns all follow-ups that are due on or before today and not yet processed.
        """
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    f.id as schedule_id,
                    f.step_number,
                    f.step_label,
                    f.due_date,
                    o.id as outreach_id,
                    o.channel,
                    o.recipient_name,
                    o.recipient_email,
                    o.job_title,
                    o.company,
                    o.status as outreach_status
                FROM followup_schedules f
                JOIN outreach_logs o ON f.outreach_log_id = o.id
                WHERE f.due_date <= ? AND f.status = 'pending' AND o.status != 'replied'
                ORDER BY f.due_date ASC
            """, (today_str,))
            return [dict(row) for row in cursor.fetchall()]

    def mark_completed(self, schedule_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE followup_schedules SET status = 'completed', completed_at = CURRENT_TIMESTAMP WHERE id = ?", (schedule_id,))
            conn.commit()
