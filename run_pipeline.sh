#!/usr/bin/env bash
# ==============================================================================
# End-to-End SWE Career System - Autonomous Pipeline Runner (Bash)
# Usage:
#   ./run_pipeline.sh                # Run full end-to-end automated pipeline
#   ./run_pipeline.sh --serve-only   # Only start/restart the background telemetry server
# ==============================================================================

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "=================================================================="
echo "      ASCEND: AUTONOMOUS SWE CAREER ACCELERATION ENGINE          "
echo "=================================================================="
echo ""

# 1. Pre-Flight Checks
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "[Setup] .env file missing. Initializing from .env.example..."
        cp .env.example .env
        echo "[Action Required] Please update .env with your GEMINI_API_KEY before running live."
    else
        echo "[Error] Missing .env and .env.example. Exiting."
        exit 1
    fi
fi

if ! docker info > /dev/null 2>&1; then
    echo "[Error] Docker daemon is not running. Please start Docker and retry."
    exit 1
fi

if [ "$1" == "--serve-only" ]; then
    echo "[Telemetry] Starting background telemetry server on port 8085..."
    docker compose up -d outreach-engine
    echo "[Success] Telemetry server live at http://localhost:8085/api/stats"
    exit 0
fi

# 2. Phase 1: Compile Resume
echo -e "\n>>> [Phase 1/4] Compiling Master Resume via RenderCV (sb2nov)..."
RESUME_FILE="master_resume.example.yaml"
if [ -f "resume/master_resume.yaml" ]; then
    RESUME_FILE="master_resume.yaml"
fi
docker compose run --rm rendercv render "$RESUME_FILE"

# 3. Phase 2: ATS Scoring & Gap Analysis
echo -e "\n>>> [Phase 2/4] Running ATS Audit & AI-Phrase Refiner..."
docker compose run --rm resume-matcher

# 4. Phase 3: Market Discovery & Funding Radar
echo -e "\n>>> [Phase 3/4] Ingesting High-Comp Opportunities & Checking Funding Radar..."
docker compose run --rm career-ops

# 5. Phase 4: Cold Outreach, LinkedIn Notes & Form Answers
echo -e "\n>>> [Phase 4/4] Generating Cold Outreach, LinkedIn Sequences & Form Auto-Answers..."
docker compose run --rm outreach-engine python pipeline.py

# 6. Phase 5: Start / Refresh Background Telemetry Daemon
echo -e "\n>>> [Phase 5] Ensuring Telemetry Tracking Server is Running (Port 8085)..."
docker compose up -d outreach-engine

# 7. Summary
echo ""
echo "=================================================================="
echo "                      AUTONOMOUS RUN COMPLETE!                    "
echo "=================================================================="
echo ""
echo "Generated Reports & Artifacts:"
echo "  • ATS Audit Report:        resume/reports/ats_audit_report.md"
echo "  • Interview Defense Guide: resume/reports/interview_defense_prep.md"
echo "  • High-Comp Opportunities: tracker/reports/top_opportunities.md"
echo "  • Cold Email Sequences:    tracker/reports/outreach_pipeline.md"
echo "  • Application Form Answers:tracker/reports/application_answers.md"
echo "  • Live Funnel Telemetry:   http://localhost:8085/api/stats"
echo ""
echo "All systems operational. No human intervention needed."
echo ""
