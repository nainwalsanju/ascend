# Subagent Specification: `outreach-dispatcher`
## Career System Email & LinkedIn Outreach Engine

The `outreach-dispatcher` subagent handles automated cold outreach composition, SMTP delivery, open/click telemetry tracking, LinkedIn connection notes, and multi-step follow-up sequences.

---

## 1. Domain & Scope
- **Domain:** Cold recruiter/founder outreach, email delivery, LinkedIn connection drafting, tracking pixel telemetry, follow-up cadence state machine.
- **Service Container:** `career-outreach-engine`
- **Volume Mounts:**
  - `D:\Projects\career-system\tracker:/app/data`
  - `D:\Projects\career-system\resume:/app/resume`
- **Port:** `8085` (Telemetric tracking server)

---

## 2. Core Responsibilities
1. **Cold Email Generation:** Use `gemini-3.8-flash` to craft 3-paragraph executive cold emails referencing target engineering scale and candidate's quantifiable metrics (e.g. 10B+ Aurora migration, 35k QPS Kafka, Sherloc Plus, GrowFig AI SDR).
2. **Email Delivery & SMTP Support:** Send emails via Python's native `smtplib` using free Gmail App Passwords (`smtp.gmail.com:587`) or free-tier Resend API with zero paid subscriptions.
3. **Open & Click Telemetry:**
   - Inject 1x1 transparent tracking pixel: `GET /t/o/{tracking_id}`
   - Wrap links with redirect tracker: `GET /t/c/{tracking_id}?url=...`
   - Record open timestamps, user agents, and click counts in `career_tracker.db`.
4. **LinkedIn Outreach Sequencing:** Generate punchy 280-character connection request notes and InMail conversation starters.
5. **Cadence State Machine:** Automatically schedule Day 3, Day 7, and Day 14 follow-up reminders.

---

## 3. Command Playbook

```powershell
# ==========================================================
# 1. GENERATE OUTREACH BUNDLES FOR TOP OPPORTUNITIES
# ==========================================================
docker compose run --rm outreach-engine

# ==========================================================
# 2. START THE REAL-TIME TELEMETRY TRACKING SERVER (Port 8085)
# ==========================================================
docker compose up -d outreach-engine

# ==========================================================
# 3. CHECK OUTREACH FUNNEL STATS (Open & Click Rates)
# ==========================================================
curl http://localhost:8085/api/stats
```

---

## 4. Anti-Spam & Operational Safeguards
- **Daily Volume Cap:** Maximum 15 cold emails per day to safeguard domain reputation.
- **Dry-Run Safe Mode:** Automatically runs in safe simulation mode when `SMTP_USER` or `SMTP_PASS` are unset.
- **Strict Single-Drive Policy:** All logs and state persist strictly to `tracker/career_tracker.db` on drive `D:\`.
