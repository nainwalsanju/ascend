import re
from funding import get_company_funding_info

class EngineeringFitEvaluator:
    """
    1 to 5 Engineering Fit Scoring Rubric:
    5: Tier-1 Tech / Top YC, Base >= $180k, Distributed Systems / High Throughput Backend, Tech match >= 85%
    4: Strong Growth Tech, Base $140k - $180k, Modern stack, Clean architecture
    3: Standard Mid/Senior Market, Base $120k - $140k
    2: Low-signal / Non-transparent compensation
    1: Below threshold (<$130k or legacy enterprise stack)
    """
    
    TIER_1_COMPANIES = {
        "stripe", "databricks", "openai", "anthropic", "figma", "vercel",
        "ramp", "scaleai", "scale ai", "replit", "linear", "coinbase", "airbnb",
        "netflix", "apple", "google", "meta", "uber", "snowflake"
    }

    CORE_TECH_KEYWORDS = {
        "golang", "go", "python", "distributed systems", "kafka", "redis",
        "kubernetes", "k8s", "docker", "postgresql", "aws", "gcp",
        "grpc", "microservices", "latency", "throughput", "concurrency"
    }

    SWE_TITLE_KEYWORDS = {
        "engineer", "developer", "architect", "swe", "sre",
        "member of technical staff", "mts"
    }

    NON_SWE_EXCLUSIONS = {
        "designer", "account executive", "recruiter", "sales", "marketing", "legal",
        "communications", "people partner", "product manager", "customer success",
        "business development", "data analyst", "financial analyst", "partner development",
        "sales manager", "solutions architect, platforms (presales)"
    }

    def evaluate_fit(self, job: dict) -> dict:
        title = (job.get("title") or "").lower()
        company = (job.get("company") or "").lower()
        location = (job.get("location") or "").lower()
        desc = (job.get("description") or "").lower()
        salary_min = job.get("salary_min") or 0
        salary_max = job.get("salary_max") or 0

        # Startup Funding Radar
        funding_info = get_company_funding_info(company)

        # Strict SWE Title Verification
        is_swe = any(k in title for k in self.SWE_TITLE_KEYWORDS)
        is_excluded = any(ex in title for ex in self.NON_SWE_EXCLUSIONS)
        if not is_swe or is_excluded:
            return {
                "final_score": 1.0,
                "rating_label": "Filtered Out (Non-SWE Role)",
                "comp_score": 1,
                "tech_score": 1,
                "is_tier1": False,
                "matched_keywords": [],
                "funding": funding_info
            }
        
        # Check Tier-1 Prestige or High-Funding Backing
        is_tier1 = any(t in company for t in self.TIER_1_COMPANIES) or bool(funding_info) or job.get("is_tier1", False)
        
        # Check Compensation Alignment
        comp_score = 1
        effective_salary = salary_max if salary_max else salary_min
        if effective_salary >= 180000:
            comp_score = 5
        elif effective_salary >= 150000:
            comp_score = 4
        elif effective_salary >= 130000:
            comp_score = 3
        elif effective_salary > 0:
            comp_score = 1  # Below target $130k
        else:
            # Undisclosed compensation
            comp_score = 4 if is_tier1 else 2
            
        # Check Tech Stack Match
        combined_text = f"{title} {desc}"
        matched_tech = [k for k in self.CORE_TECH_KEYWORDS if k in combined_text]
        tech_overlap = len(matched_tech) / len(self.CORE_TECH_KEYWORDS)
        
        tech_score = 1
        if tech_overlap >= 0.45 or any(k in title for k in ["distributed", "backend", "staff", "infra", "platform"]):
            tech_score = 5 if tech_overlap >= 0.4 else 4
        elif tech_overlap >= 0.25:
            tech_score = 3
        else:
            tech_score = 2
            
        # Check Location Match
        is_remote = "remote" in location or "anywhere" in location or job.get("is_remote", False)
        is_us = any(loc in location for loc in ["united states", "us", "san francisco", "new york", "seattle", "austin"])
        loc_score = 5 if (is_remote or is_us) else 2
        
        # Calculate Final 1-5 Rubric Rating
        weighted_score = (comp_score * 0.40) + (tech_score * 0.35) + (5 if is_tier1 else 3) * 0.15 + (loc_score * 0.10)
        final_rating = round(weighted_score, 1)
        
        # Assign Grade
        if final_rating >= 4.5:
            label = "Tier-1 Dream Opportunity (Score 5)"
        elif final_rating >= 3.8:
            label = "High-Growth Target Role (Score 4)"
        elif final_rating >= 3.0:
            label = "Solid Market Role (Score 3)"
        elif final_rating >= 2.0:
            label = "Low Signal / Marginal Fit (Score 2)"
        else:
            label = "Filtered Out (Score 1)"
            
        return {
            "final_score": final_rating,
            "rating_label": label,
            "comp_score": comp_score,
            "tech_score": tech_score,
            "is_tier1": is_tier1,
            "matched_keywords": matched_tech,
            "funding": funding_info
        }
