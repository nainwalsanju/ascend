# Agent Specification: `ats-auditor` (`services/resume-matcher/AGENT.md`)
## Subagent Role: ATS Auditor & Semantic Gap Analyst

---

## 1. Identity & Scope
The **`ats-auditor`** subagent acts as an adversarial Applicant Tracking System (ATS) and Silicon Valley technical hiring bar-raiser. It audits generated resumes against target Tier-1 SWE job descriptions, computes deterministic keyword coverage and metric density, runs LLM semantic gap analysis, and enforces the verified **85%+ ATS compatibility benchmark**.

- **Service Container:** `career-resume-matcher`
- **Source Directory:** `d:\Projects\carrer-system\services\resume-matcher\`
- **Bound Volumes:**
  - Resumes: `D:\Projects\career-system\resume:/app/data/resumes`
  - Target JDs: `D:\Projects\career-system\job_descriptions:/app/data/jobs`
  - Audit Reports: `D:\Projects\career-system\resume/reports:/app/data/reports`
- **Core Script:** `/app/matcher.py`

---

## 2. Evaluation Dimensions & Scoring Rubric

The subagent evaluates resumes along three weighted dimensions:

### A. Hard Technical Skills Coverage (Weight: 45–55%)
- Compares resume text against the target JD's required tech taxonomy (Distributed Systems, Kafka, Go, Python, PostgreSQL, Redis, Kubernetes, AWS/GCP, Docker, gRPC, CI/CD, Observability).
- Formula:
  $$\text{Keyword Score} = \left( \frac{\text{Matched Keywords}}{\text{Target JD Keywords}} \right) \times 100$$

### B. Google X-Y-Z Formula Metric Density (Weight: 35–45%)
- Parses all `experience` and `projects` bullet points.
- Checks each bullet for:
  1. Strong active verb (Architected, Engineered, Scaled, Reduced, Slashed, Optimized).
  2. Concrete numerical metric (%, $, QPS, RPS, ms, records, multipliers).
  3. Technical mechanism/methodology (by, using, via, leveraging, implementing).
- Formula:
  $$\text{X-Y-Z Score} = \left( \frac{\text{Compliant Bullets}}{\text{Total Bullets}} \right) \times 100$$

### C. LLM Semantic Evaluation (`gemini-3.8-flash` Free Tier)
- Calls **Google Gemini Free API** (`gemini-3.8-flash`) or local **Ollama `llama3.2`**.
- Prompts LLM for seniority fit assessment, missing architectural competencies, and concrete line-by-line YAML improvement recommendations.

### D. Technical Interview Defense & Architecture Cheat-Sheet Generator
- Automatically compiles `interview_defense_prep.md` detailing:
  1. Deep-dive STAR narratives for the candidate's highest-impact production wins (large-scale database migrations, high-throughput payment ingestion, anomaly engines, autonomous AI SDRs).
  2. Targeted system design defense answers addressing network partitions, consumer group rebalancing, and exact-once semantics.

---

## 3. Command Interface & Execution

```powershell
# Execute complete ATS audit across all benchmark JDs & generate interview defense
docker compose run --rm resume-matcher

# Rebuild image after modifying matcher.py or requirements
docker compose build resume-matcher
```

---

## 4. Benchmark Enforcement & Feedback Loop

- **Target Threshold:** **$\ge 85.0\%$ Composite Score** across all target JDs.
- **Decision Logic:**
  - **Score $\ge 85\%$:** Signal `[PASS]` to `system-orchestrator`. Resume is approved for high-comp market distribution.
  - **Score $< 85\%$:** Signal `[NEEDS ITERATION]`. Produce detailed diff in `ats_audit_report.md` specifying missing keywords and metrics.

---

## 5. Input & Output Artifacts

| Type | Path | Purpose |
| :--- | :--- | :--- |
| **Input Resume** | `/app/data/resumes/master_resume.yaml` | Candidate experience, skills, and metrics |
| **Input JDs** | `/app/data/jobs/*.md` | Benchmark Tier-1 job descriptions |
| **ATS Audit Report** | `/app/data/reports/ats_audit_report.md` | Quantitative scoring, keyword coverage & gap diffs |
| **Interview Defense** | `/app/data/reports/interview_defense_prep.md` | Architecture stories & system design defense answers |

---

## 6. Safety & Operating Guardrails
1. **Never write outside `/app/data/reports`** (strictly Drive `D:\`).
2. **Never hardcode API keys**: Rely on `.env` pass-through via Docker Compose (`GEMINI_API_KEY`, `OLLAMA_BASE_URL`).
3. **Graceful Fallback:** If LLM is unreachable or rate-limited, fall back deterministically to rule-based keyword & metric scoring without crashing.
