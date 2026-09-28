import os
import sys
import glob
import json
import re
from pathlib import Path
import yaml
import requests
from refinement import audit_bullet_for_ai_phrases

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

RESUMES_DIR = Path(os.getenv("RESUMES_DIR", "/app/data/resumes"))
JOBS_DIR = Path(os.getenv("JOBS_DIR", "/app/data/jobs"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/app/data/reports"))

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434").strip()
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2").strip()

def load_resume_text() -> tuple[str, list[str]]:
    """Loads resume content and extracts bullet points."""
    bullets = []
    text_content = ""
    
    # Check for yaml resume first
    yaml_files = list(RESUMES_DIR.glob("*.yaml")) + list(RESUMES_DIR.glob("*.yml"))
    if yaml_files:
        with open(yaml_files[0], "r", encoding="utf-8") as f:
            try:
                data = yaml.safe_load(f)
                text_content += json.dumps(data)
                cv = data.get("cv", {})
                sections = cv.get("sections", {})
                for sec_name in ["experience", "projects"]:
                    items = sections.get(sec_name, [])
                    if isinstance(items, list):
                        for item in items:
                            if isinstance(item, dict):
                                highlights = item.get("highlights", [])
                                if isinstance(highlights, list):
                                    bullets.extend(highlights)
                                elif isinstance(highlights, str):
                                    bullets.append(highlights)
            except Exception as e:
                print(f"[Warning] Failed parsing YAML: {e}")

    # Also check PDF files if available
    pdf_files = list(RESUMES_DIR.glob("**/*.pdf"))
    if pdf_files and PdfReader:
        try:
            reader = PdfReader(str(pdf_files[0]))
            pdf_text = "\n".join([p.extract_text() or "" for p in reader.pages])
            if len(pdf_text) > len(text_content):
                text_content = pdf_text
        except Exception as e:
            print(f"[Warning] Failed parsing PDF: {e}")

    return text_content, bullets

def load_jobs() -> list[tuple[str, str]]:
    """Loads all target job descriptions."""
    jobs = []
    job_files = sorted(list(JOBS_DIR.glob("*.md")) + list(JOBS_DIR.glob("*.txt")))
    for jf in job_files:
        with open(jf, "r", encoding="utf-8") as f:
            jobs.append((jf.stem, f.read()))
    return jobs

def evaluate_xyz_formula(bullets: list[str]) -> dict:
    """
    Evaluates bullet points against Google X-Y-Z formula:
    Accomplished [X] as measured by [Y] by doing [Z].
    Looks for:
    - Action verbs (Designed, Architected, Reduced, Scaled, Spearheaded, Built, Optimized)
    - Quantitative metrics (% percentages, numbers, $ costs, ms/s latencies, QPS/RPS)
    - Technical implementation details (by doing Z / using technologies)
    """
    if not bullets:
        return {"score": 0.0, "details": [], "passed_count": 0, "total": 0}
    
    strong_action_verbs = {
        "architected", "designed", "engineered", "scaled", "reduced", "spearheaded",
        "optimized", "migrated", "built", "implemented", "developed", "orchestrated",
        "automated", "streamlined", "accelerated", "deployed", "overhauled", "refactored"
    }
    
    metric_pattern = re.compile(
        r'(\d+[\d,]*\s*(%|percent|qps|rps|ms|s|x|gb|tb|k|m|million|billion|\$|users|nodes|cores))|'
        r'(\$\s*\d+[\d,]*)|'
        r'(sub-\d+ms)|'
        r'(99\.\d+%)',
        re.IGNORECASE
    )
    
    passed = 0
    results = []
    
    for bullet in bullets:
        words = re.findall(r'\b\w+\b', bullet.lower())
        first_word = words[0] if words else ""
        has_action = first_word in strong_action_verbs or any(w in strong_action_verbs for w in words[:3])
        has_metric = bool(metric_pattern.search(bullet))
        has_mechanism = any(term in bullet.lower() for term in [
            "by", "using", "via", "leveraging", "through", "with", "implementing", "architecting"
        ])
        
        is_xyz = has_action and has_metric and has_mechanism
        if is_xyz:
            passed += 1
            
        results.append({
            "bullet": bullet,
            "has_action_verb": has_action,
            "has_metric": has_metric,
            "has_mechanism": has_mechanism,
            "is_valid_xyz": is_xyz
        })
        
    xyz_score = (passed / len(bullets)) * 100 if bullets else 0.0
    return {
        "score": round(xyz_score, 1),
        "passed_count": passed,
        "total": len(bullets),
        "details": results
    }

def extract_keywords(text: str) -> set[str]:
    """Extracts key engineering terms."""
    tech_lexicon = [
        "golang", "go", "python", "java", "c++", "rust", "typescript", "react", "next.js",
        "distributed systems", "microservices", "kafka", "rabbitmq", "redis", "postgresql",
        "cockroachdb", "dynamodb", "mongodb", "elasticsearch", "docker", "kubernetes", "k8s",
        "aws", "gcp", "azure", "terraform", "ci/cd", "rest", "grpc", "graphql", "websockets",
        "qps", "rps", "latency", "throughput", "concurrency", "caching", "idempotency",
        "scalability", "opentelemetry", "prometheus", "grafana", "datadog", "finops", "fault-tolerant"
    ]
    found = set()
    lower_text = text.lower()
    for term in tech_lexicon:
        if re.search(r'\b' + re.escape(term) + r'\b', lower_text):
            found.add(term)
    return found

def call_gemini(prompt: str) -> str:
    """Calls Google Gemini Free API if key is available."""
    if not GEMINI_API_KEY:
        return ""
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
    }
    try:
        res = requests.post(url, json=payload, timeout=35)
        if res.status_code == 200:
            data = res.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        else:
            print(f"[Gemini API Warning] Status {res.status_code}: {res.text}")
    except Exception as e:
        print(f"[Gemini API Error]: {e}")
    return ""

def call_ollama(prompt: str) -> str:
    """Calls local Ollama if available."""
    url = f"{OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }
    try:
        res = requests.post(url, json=payload, timeout=25)
        if res.status_code == 200:
            return res.json().get("response", "")
    except Exception as e:
        pass
    return ""

def analyze_job_match(resume_text: str, bullets: list[str], job_name: str, jd_text: str) -> dict:
    """Computes comprehensive ATS compatibility score and gap analysis."""
    # 1. Keyword overlap
    resume_keywords = extract_keywords(resume_text)
    jd_keywords = extract_keywords(jd_text)
    
    matched_keywords = resume_keywords.intersection(jd_keywords)
    missing_keywords = jd_keywords.difference(resume_keywords)
    
    keyword_score = (len(matched_keywords) / len(jd_keywords) * 100) if jd_keywords else 100.0
    
    # 2. X-Y-Z Formula Metric Density
    xyz_res = evaluate_xyz_formula(bullets)
    xyz_score = xyz_res["score"]
    
    # 3. LLM Semantic Evaluation (if available)
    llm_feedback = None
    llm_prompt = f"""
You are an expert Silicon Valley ATS and Technical Bar Raiser.
Evaluate this SWE Resume against the Job Description.

Job Title / JD:
{jd_text[:3000]}

Candidate Resume Text:
{resume_text[:4000]}

Return strict JSON:
{{
  "ats_match_percentage": <integer 0-100>,
  "seniority_fit": "<Junior|Mid|Senior|Staff>",
  "strong_alignment_points": ["point 1", "point 2"],
  "critical_missing_skills": ["missing 1", "missing 2"],
  "high_impact_recommendations": ["recommendation 1", "recommendation 2"]
}}
"""
    raw_llm = call_gemini(llm_prompt) or call_ollama(llm_prompt)
    if raw_llm:
        try:
            llm_feedback = json.loads(raw_llm)
        except Exception:
            pass

    # Weighted Overall ATS Score
    # Keyword overlap: 45%
    # X-Y-Z impact & metrics: 35%
    # System Design & Core Stack presence: 20%
    if llm_feedback and "ats_match_percentage" in llm_feedback:
        llm_score = float(llm_feedback["ats_match_percentage"])
        composite_score = round((keyword_score * 0.35) + (xyz_score * 0.25) + (llm_score * 0.40), 1)
    else:
        composite_score = round((keyword_score * 0.55) + (xyz_score * 0.45), 1)
        
    return {
        "job_name": job_name,
        "composite_score": composite_score,
        "keyword_score": round(keyword_score, 1),
        "xyz_score": xyz_score,
        "matched_keywords": sorted(list(matched_keywords)),
        "missing_keywords": sorted(list(missing_keywords)),
        "xyz_details": xyz_res,
        "llm_feedback": llm_feedback
    }

def main():
    print("==================================================================")
    print("      RESUME-MATCHER: DOCKERIZED ATS & SEMANTIC GAP ANALYZER      ")
    print("==================================================================")
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    resume_text, bullets = load_resume_text()
    if not resume_text:
        print("[Error] No resume found in /app/data/resumes. Place master_resume.yaml or a PDF there.")
        sys.exit(1)
        
    jobs = load_jobs()
    if not jobs:
        print("[Error] No target job descriptions found in /app/data/jobs.")
        sys.exit(1)
        
    print(f"[Info] Loaded resume with {len(bullets)} bullets and {len(resume_text)} characters.")
    print(f"[Info] Found {len(jobs)} target benchmark job descriptions.")
    
    total_score = 0.0
    reports = []
    
    for job_name, jd_text in jobs:
        print(f"\n---> Analyzing against: {job_name} ...")
        res = analyze_job_match(resume_text, bullets, job_name, jd_text)
        reports.append(res)
        total_score += res["composite_score"]
        
        status_symbol = "[PASS >= 85%]" if res["composite_score"] >= 85.0 else "[GAP DETECTED < 85%]"
        print(f"     Score: {res['composite_score']}% {status_symbol}")
        print(f"     Keyword Match: {res['keyword_score']}% | X-Y-Z Metric Density: {res['xyz_score']}%")
        if res["missing_keywords"]:
            print(f"     Missing key terms: {', '.join(res['missing_keywords'][:6])}")
            
    avg_score = round(total_score / len(jobs), 1)
    print("\n==================================================================")
    print(f"     OVERALL AVERAGE ATS COMPATIBILITY: {avg_score}%")
    if avg_score >= 85.0:
        print("     STATUS: VERIFIED >= 85% BENCHMARK ACHIEVED!")
    else:
        print("     STATUS: ACTION REQUIRED - REVIEW RECOMMENDATIONS IN AUDIT REPORT")
    print("==================================================================")
    
    # Generate Markdown Report
    report_path = OUTPUT_DIR / "ats_audit_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# ATS Semantic Gap Analysis & Audit Report\n\n")
        f.write(f"**Overall ATS Compatibility Score:** `{avg_score}%`  \n")
        f.write(f"**Target Threshold:** `85.0%`  \n")
        f.write(f"**Status:** `{'PASSED' if avg_score >= 85 else 'NEEDS ITERATION'}`\n\n")
        f.write("---\n\n")
        
        for r in reports:
            f.write(f"## Target Job: {r['job_name']}\n")
            f.write(f"- **Composite Match:** `{r['composite_score']}%`\n")
            f.write(f"- **Keyword Coverage:** `{r['keyword_score']}%`\n")
            f.write(f"- **Google X-Y-Z Formula Strength:** `{r['xyz_score']}%` ({r['xyz_details']['passed_count']}/{r['xyz_details']['total']} bullets compliant)\n\n")
            
            f.write("### Matched High-Signal Keywords\n")
            f.write(f"`{', '.join(r['matched_keywords']) if r['matched_keywords'] else 'None'}`\n\n")
            
            f.write("### Missing High-Signal Keywords\n")
            f.write(f"`{', '.join(r['missing_keywords']) if r['missing_keywords'] else 'None'}`\n\n")
            
            if r["llm_feedback"]:
                fb = r["llm_feedback"]
                f.write("### LLM Seniority & Gap Insights\n")
                f.write(f"- **Seniority Fit Assessment:** {fb.get('seniority_fit', 'N/A')}\n")
                if "strong_alignment_points" in fb:
                    f.write("- **Strong Points:**\n")
                    for p in fb["strong_alignment_points"]:
                        f.write(f"  - {p}\n")
                if "high_impact_recommendations" in fb:
                    f.write("- **Actionable YAML Improvements:**\n")
                    for rec in fb["high_impact_recommendations"]:
                        f.write(f"  - {rec}\n")

        # Global AI Buzzword & Phrasing Audit
        f.write("## Upstream AI-Phrase & Buzzword Audit (srbhr/Resume-Matcher Refiner)\n")
        f.write("Scans all resume bullets against the upstream `AI_PHRASE_BLACKLIST` to ensure 100% human-grade, high-signal engineering phrasing:\n\n")
        total_buzzwords = 0
        for b in bullets:
            flagged = audit_bullet_for_ai_phrases(b)
            if flagged:
                total_buzzwords += len(flagged)
                f.write(f"- **Bullet:** `{b[:85]}...`\n")
                for item in flagged:
                    f.write(f"  - Flagged: *\"{item['detected_phrase']}\"* -> Suggestion: *\"{item['suggested_replacement']}\"*\n")
        if total_buzzwords == 0:
            f.write("✅ **100% Clean!** Zero blacklisted AI buzzwords detected across all experience bullets.\n")
        f.write("\n---\n\n")

            
    print(f"\n[Success] Full ATS audit report saved to: {report_path}")

    # Generate Interview Defense Cheat-Sheet
    prep_path = OUTPUT_DIR / "interview_defense_prep.md"
    with open(prep_path, "w", encoding="utf-8") as pf:
        pf.write("# Tier-1 Technical Interview Defense & Architecture Cheat-Sheet\n\n")
        pf.write("This document prepares the candidate for high-intensity FAANG / Staff-level System Design and Architecture Defense interviews.\n\n")
        pf.write("---\n\n")
        pf.write("## 1. Core Architectural Stories\n\n")
        pf.write("### Story A: 10 Billion+ Zero-Downtime Aurora Database Migration (BharatPe)\n")
        pf.write("- **Challenge:** Migrate 10B+ transaction records from AWS RDS MySQL to Amazon Aurora without a single second of maintenance window or data loss.\n")
        pf.write("- **Implementation (Z):** Dual-write replication architecture with asynchronous change data capture (CDC), Kafka replay validation, and automated shadow consistency verification.\n")
        pf.write("- **Defense Q: What happened when network partitions occurred during dual writes?**\n")
        pf.write("  - *Defense Answer:* Implemented distributed idempotency keys in Redis with dual-write reconciliation workers comparing table checksums during low-traffic windows before flipping read traffic.\n\n")
        pf.write("### Story B: 35,000 QPS Payment Ingestion Pipeline (Kafka + Redis)\n")
        pf.write("- **Challenge:** Ingest 35k QPS with sub-10ms response times and 99.99% availability.\n")
        pf.write("- **Implementation (Z):** Asynchronous Kafka event partitioning keyed on merchant ID with Redis write-behind caching.\n")
        pf.write("- **Defense Q: How did you handle consumer group rebalancing under high lag?**\n")
        pf.write("  - *Defense Answer:* Configured static group membership (`group.instance.id`), tuned heartbeat timeouts, and isolated heavy batch consumers into separate topic partitions.\n\n")
        pf.write("### Story C: Autonomous AI SDR Engine (GrowFig AI)\n")
        pf.write("- **Challenge:** High-throughput prospect discovery across 29,000+ manufacturing contacts with zero prompt leakage.\n")
        pf.write("- **Implementation (Z):** SSRF-hardened web crawler waterfall, Cheerio DOM extraction, Supabase PostgreSQL multi-tenant isolation, and `/api/engine/tick` distributed lease workers.\n\n")
        pf.write("---\n\n")
        pf.write("## 2. Target Job Technical Defense Questions\n\n")
        for r in reports:
            pf.write(f"### Track: {r['job_name']}\n")
            pf.write("1. **System Design:** How would you architect this platform to survive a multi-region AWS outage?\n")
            pf.write("2. **Concurrency:** How do you guarantee exact-once payout semantics across distributed microservices?\n")
            pf.write("3. **Observability:** How do you distinguish between network degradation and downstream database connection pool exhaustion in p99 metrics?\n\n")

    print(f"[Success] Interview Defense guide saved to: {prep_path}")

if __name__ == "__main__":
    main()
