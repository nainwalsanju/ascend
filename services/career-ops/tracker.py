import sqlite3
from pathlib import Path
from datetime import datetime

class CareerTracker:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.execute("PRAGMA journal_mode = MEMORY;")
        conn.execute("PRAGMA synchronous = OFF;")
        return conn

    def init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    location TEXT,
                    salary_min REAL,
                    salary_max REAL,
                    salary_raw TEXT,
                    url TEXT,
                    source TEXT,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS job_evaluations (
                    job_id TEXT PRIMARY KEY,
                    final_score REAL,
                    rating_label TEXT,
                    comp_score INTEGER,
                    tech_score INTEGER,
                    is_tier1 INTEGER,
                    matched_keywords TEXT,
                    evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(job_id) REFERENCES jobs(id)
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT UNIQUE,
                    status TEXT DEFAULT 'IDENTIFIED', -- 'IDENTIFIED', 'TAILORED', 'APPLIED', 'OUTREACH_SENT', 'INTERVIEWING', 'OFFER', 'REJECTED'
                    notes TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(job_id) REFERENCES jobs(id)
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS outreach_contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT,
                    company TEXT NOT NULL,
                    name TEXT NOT NULL,
                    title TEXT,
                    email TEXT,
                    linkedin_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(job_id) REFERENCES jobs(id)
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS outreach_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT,
                    company TEXT NOT NULL,
                    job_title TEXT NOT NULL,
                    recipient_name TEXT NOT NULL,
                    recipient_email TEXT,
                    channel TEXT NOT NULL,
                    subject TEXT,
                    plain_body TEXT,
                    html_body TEXT,
                    linkedin_note TEXT,
                    tracking_id TEXT UNIQUE,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    opened_at TIMESTAMP,
                    open_count INTEGER DEFAULT 0,
                    clicked_at TIMESTAMP,
                    click_count INTEGER DEFAULT 0,
                    last_user_agent TEXT,
                    status TEXT DEFAULT 'drafted',
                    FOREIGN KEY(job_id) REFERENCES jobs(id)
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS followup_schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    outreach_log_id INTEGER,
                    step_number INTEGER,
                    due_date DATE,
                    step_label TEXT,
                    status TEXT DEFAULT 'pending',
                    completed_at TIMESTAMP,
                    FOREIGN KEY(outreach_log_id) REFERENCES outreach_logs(id)
                );
            """)
            conn.commit()

    def update_application_status(self, job_id: str, new_status: str, notes: str = None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO applications (job_id, status, notes, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(job_id) DO UPDATE SET
                    status = excluded.status,
                    notes = COALESCE(excluded.notes, applications.notes),
                    updated_at = CURRENT_TIMESTAMP;
            """, (job_id, new_status, notes))
            conn.commit()

    def save_all_evaluated(self, items: list[tuple[dict, dict]]):
        """Batch save to minimize filesystem lock contention on Docker bind mount."""
        if not items:
            return
        with self.get_connection() as conn:
            cursor = conn.cursor()
            job_rows = []
            eval_rows = []
            
            for job, eval_res in items:
                job_id = f"{job.get('company', '')}_{job.get('title', '')}_{job.get('source', '')}".lower().replace(" ", "_")[:80]
                job_rows.append((
                    job_id,
                    job.get("title", ""),
                    job.get("company", ""),
                    job.get("location", ""),
                    job.get("salary_min", 0),
                    job.get("salary_max", 0),
                    job.get("salary_raw", ""),
                    job.get("url", ""),
                    job.get("source", ""),
                    job.get("description", "")
                ))
                eval_rows.append((
                    job_id,
                    eval_res.get("final_score", 0),
                    eval_res.get("rating_label", ""),
                    eval_res.get("comp_score", 0),
                    eval_res.get("tech_score", 0),
                    1 if eval_res.get("is_tier1") else 0,
                    ", ".join(eval_res.get("matched_keywords", []))
                ))
                
            cursor.executemany("""
                INSERT OR REPLACE INTO jobs (id, title, company, location, salary_min, salary_max, salary_raw, url, source, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, job_rows)
            
            cursor.executemany("""
                INSERT OR REPLACE INTO job_evaluations (job_id, final_score, rating_label, comp_score, tech_score, is_tier1, matched_keywords)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, eval_rows)
            
            conn.commit()

    def get_top_jobs(self, min_score: float = 3.0, limit: int = 50):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT j.title, j.company, j.location, j.salary_min, j.salary_max, j.salary_raw, j.url, j.source,
                       e.final_score, e.rating_label, e.matched_keywords
                FROM jobs j
                JOIN job_evaluations e ON j.id = e.job_id
                WHERE e.final_score >= ?
                ORDER BY e.final_score DESC, j.salary_max DESC
                LIMIT ?
            """, (min_score, limit))
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def export_report(self, output_path: Path):
        from funding import get_company_funding_info
        top_jobs = self.get_top_jobs(min_score=3.5)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# High-Compensation Engineering Opportunities ($130k–$300k+)\n\n")
            f.write(f"*Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
            f.write("| Score | Company | Role | Target Comp | Funding Radar | Location | Apply Link |\n")
            f.write("| :---: | :--- | :--- | :--- | :--- | :--- | :--- |\n")
            for j in top_jobs:
                comp_display = j['salary_raw'] if j['salary_raw'] else f"${int(j['salary_min']):,} - ${int(j['salary_max']):,}"
                apply_link = f"[Apply / JD]({j['url']})" if j['url'] else "Company Portal"
                funding_info = get_company_funding_info(j['company'])
                if funding_info:
                    funding_badge = f"`{funding_info['round']} ({funding_info['raised']})`"
                else:
                    funding_badge = "`Enterprise / Public`"
                f.write(f"| **{j['final_score']}** | **{j['company']}** | {j['title']} | `{comp_display}` | {funding_badge} | {j['location']} | {apply_link} |\n")
