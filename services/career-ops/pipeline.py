import os
import sys
import yaml
from pathlib import Path
from scrapers import JobScraperAggregator
from evaluator import EngineeringFitEvaluator
from tracker import CareerTracker

DATA_DIR = Path(os.getenv("DATA_DIR", "/app/data"))
CONFIG_FILE = Path(__file__).parent / "config.yaml"

def main():
    print("==================================================================")
    print("        CAREER-OPS: HIGH-COMPENSATION SWE PIPELINE SCANNER        ")
    print("==================================================================")
    
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        
    db_path = DATA_DIR / "career_tracker.db"
    tracker = CareerTracker(db_path)
    evaluator = EngineeringFitEvaluator()
    aggregator = JobScraperAggregator(config)
    
    print("[Pipeline] Ingesting jobs from Greenhouse, Ashby, and high-comp feeds...")
    jobs = aggregator.collect_all_jobs()
    
    evaluated_items = []
    top_tier_count = 0
    
    for j in jobs:
        evaluation = evaluator.evaluate_fit(j)
        score = evaluation["final_score"]
        
        # We store all opportunities scoring >= 2.5 in persistent DB
        if score >= 2.5:
            evaluated_items.append((j, evaluation))
            if score >= 4.0:
                top_tier_count += 1
                
    tracker.save_all_evaluated(evaluated_items)
    saved_count = len(evaluated_items)
                
    report_file = DATA_DIR / "reports" / "top_opportunities.md"
    tracker.export_report(report_file)
    
    print("\n==================================================================")
    print(f"     SCAN COMPLETE!")
    print(f"     - Evaluated & Saved: {saved_count} vetted engineering jobs")
    print(f"     - High-Alignment Top Tier (Score >= 4.0): {top_tier_count} roles")
    print(f"     - Persistent SQLite Database: {db_path}")
    print(f"     - Formatted Opportunities Report: {report_file}")
    print("==================================================================")
    
    # Print Top 5 to standard output
    top_5 = tracker.get_top_jobs(min_score=4.0, limit=5)
    if top_5:
        print("\nTOP PRIORITY ENGINEERING ROLES ($170k - $370k+):")
        for idx, role in enumerate(top_5, 1):
            sal = role['salary_raw'] or f"${int(role['salary_min']):,} - ${int(role['salary_max']):,}"
            print(f" [{idx}] {role['company']} - {role['title']}")
            print(f"     Score: {role['final_score']} | Comp: {sal} | Loc: {role['location']}")
            print(f"     Apply: {role['url']}\n")

if __name__ == "__main__":
    main()
