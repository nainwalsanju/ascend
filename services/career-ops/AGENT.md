# Agent Specification: `market-scout` (`services/career-ops/AGENT.md`)
## Subagent Role: High-Compensation Market Scout & Pipeline Ingestor

---

## 1. Identity & Scope
The **`market-scout`** subagent is responsible for discovering, filtering, scoring, and cataloging high-compensation software engineering opportunities ($130,000 to $300,000+ base). It polls public ATS APIs (Greenhouse, Ashby), ingests verified top-tier tech feeds (Levels.fyi, Y Combinator), scores opportunities against a 1–5 engineering rubric, and maintains a persistent SQLite tracker.

- **Service Container:** `ascend-ops`
- **Source Directory:** `d:\Projects\ascend\services\career-ops\`
- **Bound Volumes:**
  - Database & Reports: `D:\Projects\ascend\tracker:/app/data`
- **Core Pipeline Scripts:**
  - Ingestion: `/app/scrapers.py`
  - Rubric Evaluator: `/app/evaluator.py`
  - Database & Tracker: `/app/tracker.py`
  - Main Orchestrator: `/app/pipeline.py`

---

## 2. Ingestion Sources & Filtering Engine

### A. High-Signal Sources
1. **Greenhouse Public Boards:** Direct REST API polling (`boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true`) for companies like Stripe, Databricks, Figma, Vercel, Ramp, and Scale AI.
2. **Ashby Public Boards:** API polling (`api.ashbyhq.com/posting-api/job-board/{company}`) for companies like OpenAI, Anthropic, Linear, and Replit.
3. **Lever Public Boards:** Direct REST API polling (`api.lever.co/v0/postings/{company}?mode=json`).
4. **Hiring Team & Decision-Maker Discovery:** Targeted search query generator building LinkedIn search patterns for Engineering Managers, Heads of Engineering, and Technical Recruiters.
5. **Levels.fyi & Y Combinator Feeds:** Verified high-equity / high-compensation senior SWE openings.

### B. Application Lifecycle State Machine (CRM)
Tracks candidates across 7 structured stages in SQLite:
`IDENTIFIED` $\rightarrow$ `TAILORED` $\rightarrow$ `APPLIED` $\rightarrow$ `OUTREACH_SENT` $\rightarrow$ `INTERVIEWING` $\rightarrow$ `OFFER` $\rightarrow$ `REJECTED`

---

## 3. The 1–5 Engineering Fit Scoring Rubric

$$\text{Final Score} = (\text{Comp} \times 0.40) + (\text{Tech} \times 0.35) + (\text{Prestige} \times 0.15) + (\text{Location} \times 0.10)$$

| Score | Category | Qualifications |
| :--- : | :--- | :--- |
| **5 (4.5–5.0)** | **Tier-1 Dream Role** | Base $\ge \$180\text{k} - \$370\text{k}+$, Tier-1 company (OpenAI, Stripe, Databricks), distributed systems/backend focus, tech overlap $\ge 45\%$. |
| **4 (3.8–4.4)** | **High-Growth Target** | Base $\$140\text{k} - \$180\text{k}$, solid tech stack alignment (Go/Python, Kafka, Postgres, Kubernetes). |
| **3 (3.0–3.7)** | **Solid Market Role** | Standard senior SWE role ($\$120\text{k} - \$140\text{k}$), acceptable tech stack. |
| **2 (2.0–2.9)** | **Low-Signal Role** | Non-transparent compensation or low technical alignment. |
| **1 (<2.0)** | **Filtered Out** | Non-SWE titles or below $\$130\text{k}$ floor. |

---

## 4. SQLite Persistence & Windows Docker Mount Optimization

Because this service persists data to a Windows host volume via Docker Desktop WSL2:
- **Lock Contention Mitigation:**
  ```python
  conn.execute("PRAGMA journal_mode = MEMORY;")
  conn.execute("PRAGMA synchronous = OFF;")
  ```
- **Batch Processing:** All row inserts are performed via `executemany` inside `tracker.save_all_evaluated()` to eliminate filesystem lock errors.
- **Outreach & Telemetry Interop:** Tables `outreach_contacts`, `outreach_logs`, and `followup_schedules` are initialized and shared with `outreach-dispatcher`.

---

## 5. Command Interface & Execution

```powershell
# Run the complete high-comp pipeline scan
docker compose run --rm career-ops

# Rebuild image after editing scrapers or evaluator
docker compose build career-ops
```

---

## 6. Input & Output Artifacts

| Type | Path | Purpose |
| :--- | :--- | :--- |
| **Configuration** | `/app/config.yaml` | Salary floors, target companies, keyword weights |
| **Database** | `/app/data/career_tracker.db` | Persistent SQLite database storing jobs, CRM states & scores |
| **Leaderboard** | `/app/data/reports/top_opportunities.md` | Markdown table ranking top roles $\ge 3.5$ score |

---

## 7. Safety & Operating Guardrails
1. **Zero Host Pollution:** All requests, scraping, and database drivers execute inside the container.
2. **Drive `D:\` strictly:** Persistent database and reports write solely to `./tracker` (`/app/data`).
3. **Respect Rate Limits:** Batch board requests with timeouts to avoid IP blocking from public ATS gateways.

