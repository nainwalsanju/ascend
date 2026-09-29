import os
import sys
import uuid
import sqlite3
from pathlib import Path
from composer import OutreachComposer
from dispatcher import EmailDispatcher
from followup import FollowupManager

DB_PATH = Path(os.getenv("DB_PATH", "/app/data/career_tracker.db"))
REPORTS_DIR = Path(os.getenv("REPORTS_DIR", "/app/data/reports"))

def init_outreach_schema():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
    conn.execute("PRAGMA journal_mode = MEMORY;")
    conn.execute("PRAGMA synchronous = OFF;")
    with conn:
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
                channel TEXT NOT NULL, -- 'email' or 'linkedin'
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
                status TEXT DEFAULT 'drafted', -- 'drafted', 'sent', 'opened', 'clicked', 'replied'
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

def run_outreach_generation():
    print("=" * 66)
    print("   OUTREACH-DISPATCHER: EXECUTIVE OUTREACH & TELEMETRY ENGINE   ")
    print("=" * 66)
    init_outreach_schema()

    conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT j.id, j.title, j.company, j.location, j.url, j.salary_raw, e.final_score, e.matched_keywords, j.description
        FROM jobs j
        JOIN job_evaluations e ON j.id = e.job_id
        WHERE e.final_score >= 4.0
        ORDER BY e.final_score DESC
        LIMIT 10
    """)
    top_jobs = [dict(row) for row in cursor.fetchall()]

    if not top_jobs:
        print("[Info] No evaluated jobs found in database. Auto-seeding top-tier benchmark opportunities...")
        seed_jobs = [
            {
                "id": "seed-stripe-payments",
                "title": "Staff Backend Engineer - Core Payments",
                "company": "Stripe",
                "location": "Remote / Seattle, WA / San Francisco, CA",
                "salary_raw": "$220,000 - $315,000 + Equity",
                "url": "https://stripe.com/jobs",
                "description": "Architect high-availability payment routing, distributed ledger idempotency, and low-latency database backends. Go, Java, distributed systems, Kafka, AWS.",
                "final_score": 4.9,
                "matched_keywords": "go, java, distributed systems, kafka, aws, idempotency, latency, throughput"
            },
            {
                "id": "seed-databricks-distributed",
                "title": "Senior Distributed Systems Infrastructure Engineer",
                "company": "Databricks",
                "location": "Remote / Mountain View, CA",
                "salary_raw": "$200,000 - $290,000 + Equity",
                "url": "https://databricks.com/company/careers",
                "description": "Design core storage engine, fault-tolerant consensus protocols, and unified analytical metastore. Python, Go, Kubernetes, Raft, distributed caching.",
                "final_score": 4.8,
                "matched_keywords": "python, go, kubernetes, distributed systems, caching, concurrency, scalability"
            },
            {
                "id": "seed-openai-platforms",
                "title": "Senior Systems Engineer - AI Inference Platform",
                "company": "OpenAI",
                "location": "San Francisco, CA (Hybrid / Remote)",
                "salary_raw": "$230,000 - $370,000 + Equity",
                "url": "https://openai.com/careers",
                "description": "Scale GPU clusters, low-latency model inference servers, and distributed queue backends. Python, Rust, Kubernetes, Redis, high throughput.",
                "final_score": 4.9,
                "matched_keywords": "python, rust, kubernetes, redis, throughput, latency, microservices"
            },
            {
                "id": "seed-anthropic-infra",
                "title": "Staff Infrastructure & Reliability Engineer",
                "company": "Anthropic",
                "location": "San Francisco, CA / Remote",
                "salary_raw": "$210,000 - $320,000 + Equity",
                "url": "https://anthropic.com/careers",
                "description": "Orchestrate large-scale model training clusters and automated reliability monitoring. Python, Go, Docker, Terraform, Prometheus, AWS.",
                "final_score": 4.7,
                "matched_keywords": "python, go, docker, terraform, prometheus, aws, observability, reliability"
            },
            {
                "id": "seed-ramp-fintech",
                "title": "Senior Backend Engineer - Financial Infrastructure",
                "company": "Ramp",
                "location": "New York, NY / Remote",
                "salary_raw": "$185,000 - $250,000 + Equity",
                "url": "https://ramp.com/careers",
                "description": "Build high-throughput card transaction rails, automated accounting workflows, and zero-downtime database pipelines. Python, PostgreSQL, AWS, Kafka.",
                "final_score": 4.6,
                "matched_keywords": "python, postgresql, aws, kafka, microservices, idempotency, rest"
            }
        ]
        with conn:
            c = conn.cursor()
            for s in seed_jobs:
                c.execute("""
                    INSERT OR REPLACE INTO jobs (id, title, company, location, salary_raw, url, source, description)
                    VALUES (?, ?, ?, ?, ?, ?, 'Tier-1 Seed', ?)
                """, (s["id"], s["title"], s["company"], s["location"], s["salary_raw"], s["url"], s["description"]))
                c.execute("""
                    INSERT OR REPLACE INTO job_evaluations (job_id, final_score, rating_label, matched_keywords)
                    VALUES (?, ?, 'Top-Tier Match', ?)
                """, (s["id"], s["final_score"], s["matched_keywords"]))
            conn.commit()

        cursor.execute("""
            SELECT j.id, j.title, j.company, j.location, j.url, j.salary_raw, e.final_score, e.matched_keywords, j.description
            FROM jobs j
            JOIN job_evaluations e ON j.id = e.job_id
            WHERE e.final_score >= 4.0
            ORDER BY e.final_score DESC
            LIMIT 10
        """)
        top_jobs = [dict(row) for row in cursor.fetchall()]

    print(f"[Info] Found {len(top_jobs)} tier-1 opportunities for executive outreach.")

    composer = OutreachComposer()
    dispatcher = EmailDispatcher()
    followup_mgr = FollowupManager()

    outreach_records = []

    for job in top_jobs:
        job_id = job["id"]
        company = job["company"]
        role = job["title"]

        # Synthesize targeted contact pattern for the role
        contact = {
            "name": f"Head of Engineering ({company})",
            "title": f"VP / Director of Engineering, {role.split(' - ')[0]}",
            "email": f"engineering-recruiting@{company.lower().replace(' ', '')}.com",
            "linkedin": f"https://www.linkedin.com/company/{company.lower().replace(' ', '-')}/people/"
        }

        # Compose hyper-personalized pitch bundle
        bundle = composer.compose_outreach_bundle(job, contact)
        tracking_id = str(uuid.uuid4())

        # Inject tracking into email
        plain_body, html_body = dispatcher.inject_tracking(bundle["cold_email_body"], tracking_id)

        # Insert or update outreach log
        with conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO outreach_logs (
                    job_id, company, job_title, recipient_name, recipient_email,
                    channel, subject, plain_body, html_body, linkedin_note,
                    tracking_id, status
                ) VALUES (?, ?, ?, ?, ?, 'email', ?, ?, ?, ?, ?, 'drafted')
            """, (
                job_id, company, role, contact["name"], contact["email"],
                bundle["cold_email_subject"], plain_body, html_body,
                bundle["linkedin_connection_note"], tracking_id
            ))
            outreach_log_id = c.lastrowid
            conn.commit()

        # Schedule follow-up cadence
        followup_mgr.schedule_cadence(outreach_log_id)

        outreach_records.append({
            "company": company,
            "role": role,
            "score": job["final_score"],
            "subject": bundle["cold_email_subject"],
            "contact": contact["name"],
            "linkedin_note": bundle["linkedin_connection_note"],
            "tracking_id": tracking_id
        })

    # Generate Markdown summary report
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / "outreach_pipeline.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Executive Outreach & Follow-up Telemetry Pipeline\n\n")
        f.write(f"**Generated Outreach Sequences:** `{len(outreach_records)}` | **Model:** `{os.getenv('GEMINI_MODEL', 'gemini-3.8-flash')}`\n\n")
        f.write("---\n\n")
        for rec in outreach_records:
            f.write(f"## {rec['company']} — {rec['role']} (Fit Score: `{rec['score']}`)\n")
            f.write(f"- **Target Contact:** {rec['contact']}\n")
            f.write(f"- **Email Subject:** `{rec['subject']}`\n")
            f.write(f"- **Tracking ID:** `{rec['tracking_id']}`\n")
            f.write(f"- **LinkedIn Connection Note (280 chars):**\n")
            f.write(f"> {rec['linkedin_note']}\n\n")
            f.write("---\n\n")

    print(f"\n[Success] Generated {len(outreach_records)} outreach bundles with tracking.")
    print(f"[Success] Executive outreach report saved to: {report_path}")

    # Generate Application Answers for Top Roles (from upstream career-ops application-answers.mjs)
    from answers import export_application_answers_report
    answers_report_path = REPORTS_DIR / "application_answers.md"
    export_application_answers_report(outreach_records, answers_report_path)
    print(f"[Success] Application form auto-answers saved to: {answers_report_path}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--serve":
        init_outreach_schema()
        import uvicorn
        from tracker_server import app
        uvicorn.run(app, host="0.0.0.0", port=8085)
    elif len(sys.argv) > 1 and sys.argv[1] == "--all":
        run_outreach_generation()
        import uvicorn
        from tracker_server import app
        print("\n[Outreach-Dispatcher] Launching live telemetry tracking daemon on port 8085...")
        uvicorn.run(app, host="0.0.0.0", port=8085)
    else:
        run_outreach_generation()
