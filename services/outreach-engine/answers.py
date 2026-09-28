"""
Application Form Auto-Answers Generator.
Adapted from upstream santifer/career-ops (application-answers.mjs).
Generates high-converting, truthful answers to common application portal questions (Greenhouse, Lever, Ashby)
strictly adhering to the candidate's verified architectural wins (Source-of-Truth Boundary).
"""

import os
import json
import requests
from pathlib import Path

DEFAULT_QUESTIONS = [
    {
        "id": "why_company",
        "question": "Why are you interested in joining {company} and this specific role?",
        "instruction": "Explain why the candidate wants to join this company, referencing their specific engineering scale or product and how candidate's experience at BharatPe, AssetTrace, or GrowFig aligns."
    },
    {
        "id": "complex_system_challenge",
        "question": "Describe the most complex distributed systems or backend challenge you have solved.",
        "instruction": "Detail the 10 Billion+ record zero-downtime Aurora database migration or the 35,000 QPS Kafka payment ingestion pipeline with dual writes, CDC, and distributed Redis idempotency."
    },
    {
        "id": "fullstack_ai_experience",
        "question": "Describe your experience building modern full-stack web applications and AI agent workflows.",
        "instruction": "Detail founding AssetTrace from ground zero (Next.js, Spring Boot, 100k+ public records) and building the GrowFig AI SDR engine (Next.js, Python, Supabase, 29k+ contact enrichment with lease lock workers)."
    },
    {
        "id": "production_incident_defense",
        "question": "Describe a situation where you diagnosed and resolved a critical production incident or p99 latency spike.",
        "instruction": "Explain consumer group rebalancing under Kafka lag, DB connection pool starvation, or fraud leakages mitigated by Sherloc Plus (reducing losses by 42%)."
    },
    {
        "id": "compensation_availability",
        "question": "What are your compensation expectations, work authorization, and earliest start date?",
        "instruction": "Target: $180k - $260k+ base (depending on tier and equity upside). Availability: Immediate to 2 weeks notice. Location: Open to Remote or US hybrid/relocation."
    }
]

def _load_candidate_profile() -> dict:
    """Loads candidate profile dynamically from local master_resume.yaml or env vars."""
    resume_path = Path("/app/resume/master_resume.yaml")
    if not resume_path.exists():
        resume_path = Path("resume/master_resume.yaml")

    candidate_name = os.getenv("CANDIDATE_NAME", "the candidate")
    facts = []

    if resume_path.exists():
        try:
            import yaml
            with open(resume_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                cv = data.get("cv", {})
                candidate_name = cv.get("name", candidate_name)
                for exp in cv.get("sections", {}).get("experience", []):
                    comp = exp.get("company", "")
                    pos = exp.get("position", "")
                    highlights = exp.get("highlights", [])
                    facts.append(f"- {comp} ({pos}): " + "; ".join(highlights[:2]))
        except Exception:
            pass

    if not facts:
        facts = [
            "- Distributed Systems: High-throughput event-driven microservices across Kafka and Redis.",
            "- Database Migrations: Zero-downtime database migrations with automated consistency verification.",
            "- Full-Stack & AI: Autonomous AI workflows and enterprise web applications in TypeScript and Python."
        ]

    return {
        "name": candidate_name,
        "facts": "\n".join(facts)
    }

def generate_application_answers_bundle(company: str, role: str, api_key: str = None, model: str = "gemini-3.8-flash") -> dict:
    """Generates customized answers for a given company and role."""
    api_key = api_key or os.getenv("GEMINI_API_KEY")
    profile = _load_candidate_profile()
    answers = {}

    for q in DEFAULT_QUESTIONS:
        prompt = f"""You are drafting high-converting, authentic job application answers for senior software engineer {profile['name']}.

Candidate Profile & Facts (DO NOT FABRICATE):
{profile['facts']}

Target Company: {company}
Target Role: {role}
Question: {q['question'].format(company=company)}
Specific Instruction: {q['instruction']}

Write a concise, compelling, professional answer (1-2 paragraphs max, or direct concise bullets). Tone: senior engineering leader, humble, metric-driven, zero AI fluff. Do not invent facts."""

        if api_key:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.3}
            }
            try:
                res = requests.post(url, json=payload, timeout=20)
                if res.status_code == 200:
                    text = res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                    answers[q["id"]] = {
                        "question": q["question"].format(company=company),
                        "answer": text
                    }
                    continue
            except Exception as e:
                print(f"[Warning] Gemini API call failed for {q['id']}: {e}")

        # Fallback deterministic answer
        if q["id"] == "complex_system_challenge":
            ans = f"In my previous engineering roles, I led large-scale database migrations with zero downtime, architecting dual-write pipelines with Kafka, Change Data Capture (CDC), and distributed Redis idempotency keys to ensure 100% data consistency."
        elif q["id"] == "fullstack_ai_experience":
            ans = f"I have built autonomous AI agent engines and modern full-stack platforms from ground zero using Next.js, Python, and Supabase, implementing distributed worker loops and high-throughput data pipelines."
        elif q["id"] == "compensation_availability":
            ans = "Target base compensation is in the competitive market range for senior/staff engineering roles (flexible based on equity and total package). Available within standard notice period; open to Remote or hybrid hub locations."
        else:
            ans = f"My experience scaling high-throughput distributed systems and building modern full-stack platforms directly aligns with {company}'s engineering scale for the {role} role."

        answers[q["id"]] = {
            "question": q["question"].format(company=company),
            "answer": ans
        }

    return answers


def export_application_answers_report(companies: list[dict], output_path: Path):
    """Generates the Markdown cheat-sheet for fast copy-pasting during job applications."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Job Application Form Auto-Answers (Greenhouse / Ashby / Lever)\n\n")
        f.write("Pre-drafted, truthful answers to standard custom application fields for Tier-1 engineering opportunities.\n\n")
        f.write("---\n\n")

        for c in companies:
            f.write(f"## {c['company']} — {c['role']}\n\n")
            bundle = generate_application_answers_bundle(c['company'], c['role'])
            for item in bundle.values():
                f.write(f"### Q: {item['question']}\n")
                f.write(f"{item['answer']}\n\n")
            f.write("---\n\n")

if __name__ == "__main__":
    test_companies = [
        {"company": "Stripe", "role": "Staff Backend Engineer - Core Payments"},
        {"company": "Databricks", "role": "Senior Distributed Systems Engineer"},
        {"company": "Ramp", "role": "Senior Backend Engineer - Financial Infrastructure"}
    ]
    report_file = Path("/app/data/reports/application_answers.md")
    export_application_answers_report(test_companies, report_file)
    print(f"[Success] Generated application answers report at: {report_file}")
