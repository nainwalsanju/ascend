import os
import sqlite3
import base64
import urllib.parse
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response, RedirectResponse

DB_PATH = Path(os.getenv("DB_PATH", "/app/data/career_tracker.db"))
app = FastAPI(title="Ascend Outreach Telemetry Server", version="1.0.0")

# 1x1 transparent GIF bytes
TRANSPARENT_1X1_GIF = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")

def get_db():
    conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
    conn.execute("PRAGMA journal_mode = MEMORY;")
    conn.execute("PRAGMA synchronous = OFF;")
    return conn

@app.get("/health")
def health():
    return {"status": "healthy", "service": "ascend-outreach-engine"}

@app.get("/t/o/{tracking_id}")
def track_open(tracking_id: str, request: Request):
    """
    Serves a 1x1 transparent GIF and records open telemetry.
    """
    user_agent = request.headers.get("user-agent", "Unknown")
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE outreach_logs
                SET opened_at = COALESCE(opened_at, CURRENT_TIMESTAMP),
                    open_count = open_count + 1,
                    status = CASE WHEN status = 'sent' THEN 'opened' ELSE status END,
                    last_user_agent = ?
                WHERE tracking_id = ?
            """, (user_agent, tracking_id))
            conn.commit()
    except Exception as e:
        print(f"[Tracker Error on Open]: {e}")

    return Response(content=TRANSPARENT_1X1_GIF, media_type="image/gif")

@app.get("/t/c/{tracking_id}")
def track_click(tracking_id: str, url: str, request: Request):
    """
    Records click telemetry and redirects the candidate/recruiter to the destination link.
    """
    dest_url = urllib.parse.unquote(url)
    user_agent = request.headers.get("user-agent", "Unknown")
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE outreach_logs
                SET clicked_at = COALESCE(clicked_at, CURRENT_TIMESTAMP),
                    click_count = click_count + 1,
                    last_user_agent = ?
                WHERE tracking_id = ?
            """, (user_agent, tracking_id))
            conn.commit()
    except Exception as e:
        print(f"[Tracker Error on Click]: {e}")

    return RedirectResponse(url=dest_url, status_code=307)

@app.get("/api/stats")
def get_stats():
    """
    Returns outreach funnel metrics.
    """
    try:
        with get_db() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_outreach,
                    SUM(CASE WHEN open_count > 0 THEN 1 ELSE 0 END) as opened,
                    SUM(CASE WHEN click_count > 0 THEN 1 ELSE 0 END) as clicked,
                    SUM(CASE WHEN status = 'replied' THEN 1 ELSE 0 END) as replied
                FROM outreach_logs
            """)
            row = cursor.fetchone()
            total = row["total_outreach"] or 0
            opened = row["opened"] or 0
            clicked = row["clicked"] or 0
            replied = row["replied"] or 0
            return {
                "total_outreach": total,
                "opened": opened,
                "clicked": clicked,
                "replied": replied,
                "open_rate": f"{(opened / total * 100):.1f}%" if total > 0 else "0.0%",
                "click_rate": f"{(clicked / total * 100):.1f}%" if total > 0 else "0.0%",
                "reply_rate": f"{(replied / total * 100):.1f}%" if total > 0 else "0.0%"
            }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8085)
