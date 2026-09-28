"""
AI Phrase Blacklist and Refinement Engine.
Adapted from upstream srbhr/Resume-Matcher (apps/backend/app/prompts/refinement.py).
Identifies overused AI buzzwords and provides authentic high-signal engineering replacements.
"""

AI_PHRASE_BLACKLIST: set[str] = {
    # Action verbs overused by LLMs
    "spearheaded", "orchestrated", "championed", "synergized", "leveraged",
    "revolutionized", "pioneered", "catalyzed", "operationalized", "architected",
    "envisioned", "effectuated", "endeavored", "facilitated", "utilized",
    # Corporate buzzwords
    "synergy", "synergies", "paradigm", "paradigm shift", "best-in-class",
    "world-class", "cutting-edge", "bleeding-edge", "game-changer", "game-changing",
    "disruptive", "disruptor", "holistic", "robust", "scalable", "actionable",
    "impactful", "proactive", "proactively", "deliverables", "bandwidth",
    "move the needle", "low-hanging fruit", "touch base", "value-add",
    # Filler phrases
    "in order to", "for the purpose of", "at the end of the day",
    "moving forward", "going forward", "on a daily basis", "in a timely manner"
}

AI_PHRASE_REPLACEMENTS: dict[str, str] = {
    "spearheaded": "led",
    "orchestrated": "directed / coordinated",
    "championed": "advocated for",
    "synergized": "collaborated",
    "leveraged": "used / deployed",
    "revolutionized": "transformed",
    "pioneered": "introduced",
    "catalyzed": "accelerated",
    "operationalized": "implemented",
    "architected": "designed / built",
    "envisioned": "planned",
    "utilized": "used",
    "best-in-class": "high-performance",
    "world-class": "production-grade",
    "cutting-edge": "modern",
    "bleeding-edge": "state-of-the-art",
    "game-changer": "major milestone",
    "game-changing": "innovative",
    "holistic": "comprehensive",
    "robust": "resilient / fault-tolerant",
    "scalable": "high-throughput",
    "in order to": "to",
    "for the purpose of": "to"
}

def audit_bullet_for_ai_phrases(bullet: str) -> list[dict]:
    """
    Scans a resume bullet for AI-generated buzzwords and provides suggested alternatives.
    """
    findings = []
    bullet_lower = bullet.lower()
    for phrase in sorted(AI_PHRASE_BLACKLIST, key=len, reverse=True):
        if phrase in bullet_lower:
            replacement = AI_PHRASE_REPLACEMENTS.get(phrase, "rephrase to specific technical action")
            findings.append({
                "detected_phrase": phrase,
                "suggested_replacement": replacement
            })
    return findings
