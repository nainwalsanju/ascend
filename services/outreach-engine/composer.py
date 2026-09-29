import os
import json
import requests

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()

def call_gemini_json(prompt: str) -> dict:
    """Calls Gemini API with JSON output mode."""
    if not GEMINI_API_KEY:
        return {}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "responseMimeType": "application/json"}
    }
    try:
        res = requests.post(url, json=payload, timeout=35)
        if res.status_code == 200:
            raw = res.json()["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(raw)
        else:
            print(f"[Composer Warning] Status {res.status_code}: {res.text}")
    except Exception as e:
        print(f"[Composer Error]: {e}")
    return {}

class OutreachComposer:
    def __init__(self, candidate_profile: dict = None):
        if candidate_profile:
            self.candidate = candidate_profile
        else:
            self.candidate = self._load_profile_from_resume_or_env()

    def _load_profile_from_resume_or_env(self) -> dict:
        """Loads candidate profile dynamically from local master_resume.yaml, example yaml, or env vars."""
        candidate_paths = [
            Path("/app/resume/master_resume.yaml"),
            Path("resume/master_resume.yaml"),
            Path("/app/resume/master_resume.example.yaml"),
            Path("resume/master_resume.example.yaml")
        ]
        chosen_path = next((p for p in candidate_paths if p.exists()), None)

        if chosen_path:
            try:
                import yaml
                with open(chosen_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    cv = data.get("cv", {})
                    name = cv.get("name", os.getenv("CANDIDATE_NAME", "Candidate Name"))
                    email = cv.get("email", os.getenv("CANDIDATE_EMAIL", "candidate@example.com"))
                    website = cv.get("website", os.getenv("CANDIDATE_PORTFOLIO", "https://portfolio.example.com"))
                    socials = cv.get("social_networks", [])
                    gh = next((s.get("username") for s in socials if s.get("network", "").lower() == "github"), "candidate")
                    li = next((s.get("username") for s in socials if s.get("network", "").lower() == "linkedin"), "candidate")
                    
                    achievements = []
                    for exp in cv.get("sections", {}).get("experience", []):
                        for hl in exp.get("highlights", []):
                            if hl and len(achievements) < 4:
                                achievements.append(hl)
                                
                    if not achievements:
                        achievements = [
                            "Architected high-throughput distributed systems and mission-critical cloud infrastructure.",
                            "Led zero-downtime database migrations with zero data loss using dual-write sync and CDC.",
                            "Engineered fault-tolerant event-driven pipelines handling 30,000+ QPS with sub-10ms response times.",
                            "Launched scalable full-stack applications and autonomous AI agent workflows."
                        ]

                    return {
                        "name": name,
                        "title": os.getenv("CANDIDATE_TITLE", "Senior Full-Stack & Distributed Systems Engineer"),
                        "email": email,
                        "linkedin": f"https://www.linkedin.com/in/{li}",
                        "portfolio": website,
                        "github": f"https://github.com/{gh}",
                        "top_achievements": achievements
                    }
            except Exception as e:
                print(f"[Composer Warning] Could not parse resume YAML: {e}")

        return {
            "name": os.getenv("CANDIDATE_NAME", "Candidate Name"),
            "title": os.getenv("CANDIDATE_TITLE", "Senior Software Engineer"),
            "email": os.getenv("CANDIDATE_EMAIL", "candidate@example.com"),
            "linkedin": os.getenv("CANDIDATE_LINKEDIN", "https://linkedin.com/in/candidate"),
            "portfolio": os.getenv("CANDIDATE_PORTFOLIO", "https://portfolio.example.com"),
            "github": os.getenv("CANDIDATE_GITHUB", "https://github.com/candidate"),
            "top_achievements": [
                "Led zero-downtime database migrations with automated consistency verification.",
                "Designed resilient event-driven microservices across Kafka and Redis.",
                "Built full-stack platforms and autonomous AI workflows from ground zero."
            ]
        }

    def compose_outreach_bundle(self, job: dict, contact: dict) -> dict:
        """
        Generates a 3-paragraph executive cold email and a 300-char LinkedIn connection note.
        """
        prompt = f"""
You are an elite Silicon Valley executive talent agent and copywriter drafting high-converting outreach for a top 1% Senior/Staff Systems & Backend Engineer.

Candidate:
- Name: {self.candidate['name']} ({self.candidate['title']})
- Portfolio: {self.candidate['portfolio']}
- GitHub: {self.candidate['github']}
- Top Wins: {json.dumps(self.candidate['top_achievements'])}

Target Company & Role:
- Company: {job.get('company')}
- Role: {job.get('title')}
- Tech Stack / Keywords: {job.get('matched_keywords', '')}
- Job Snippet: {job.get('description', '')[:500]}

Contact:
- Name: {contact.get('name', 'Hiring Team')}
- Title: {contact.get('title', 'Engineering Leadership')}

Instructions:
1. "cold_email_subject": Catchy, non-spammy, highly specific subject line (e.g., "10B+ Aurora migration -> scaling payments at [Company]" or "[Role] @ [Company] — [Candidate Name]").
2. "cold_email_body": Exactly 3 punchy paragraphs:
   - Paragraph 1: Direct hook acknowledging the company's engineering domain or scale.
   - Paragraph 2: Exactly 2 highly relevant bullet points showing quantifiable technical overlap from the candidate's background.
   - Paragraph 3: Friction-free call to action (brief 10-minute sync or link to portfolio).
3. "linkedin_connection_note": Maximum 280 characters. Polite, technical, high-signal connection request note.
4. "followup_email_body": A polite 2-sentence follow-up for 3 days later.

Output strictly valid JSON with keys:
"cold_email_subject", "cold_email_body", "linkedin_connection_note", "followup_email_body"
"""
        result = call_gemini_json(prompt)
        if not result or not result.get("cold_email_subject"):
            # Deterministic High-Converting Fallback Template
            company = job.get('company', 'your team')
            title = job.get('title', 'Senior Engineer')
            contact_first = contact.get('name', 'there').split()[0]
            achievements_text = "\n".join([f"• {a}" for a in self.candidate.get("top_achievements", [])[:2]])
            if not achievements_text:
                achievements_text = (
                    "• Led zero-downtime database migrations with automated consistency verification.\n"
                    "• Architected fault-tolerant event-driven microservices handling 30,000+ QPS."
                )
            result = {
                "cold_email_subject": f"{title} @ {company} — Scaling distributed systems & backend infrastructure",
                "cold_email_body": (
                    f"Hi {contact_first},\n\n"
                    f"I've been following {company}'s impressive engineering milestones and noticed you are hiring for a {title}. Given your focus on high-throughput reliability and clean system design, I wanted to reach out directly.\n\n"
                    f"Over the last 5+ years building and scaling production infrastructure:\n"
                    f"{achievements_text}\n\n"
                    f"You can explore my architecture deep-dives and live projects at {self.candidate['portfolio']}.\n\n"
                    f"Would you be open to a brief 10-minute conversation this week to discuss how I can contribute to {company}?\n\n"
                    f"Best regards,\n{self.candidate['name']}\n{self.candidate['email']} | {self.candidate['linkedin']}"
                ),
                "linkedin_connection_note": (
                    f"Hi {contact_first}, I saw {company} is scaling for {title}. I've architected large-scale distributed migrations and high-throughput microservices. Would love to connect!"
                )[:295],
                "followup_email_body": (
                    f"Hi {contact_first}, following up on my previous note regarding the {title} role at {company}. I'd love to share brief technical details on scaling high-throughput pipelines if you have 10 minutes this week."
                )
            }
        return result
