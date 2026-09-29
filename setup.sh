#!/usr/bin/env bash
# ==============================================================================
# End-to-End SWE Career System - 60-Second Interactive Setup Wizard (Bash)
# Usage:
#   ./setup.sh
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "=================================================================="
echo "     SWE CAREER SYSTEM - 60-SECOND PLUG & PLAY SETUP WIZARD       "
echo "=================================================================="
echo "Turnkey containerized career autopilot for High-Paying SWE roles."
echo ""

# 1. Initialize .env from .env.example if missing
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "[1/4] Creating local .env from .env.example..."
        cp .env.example .env
    fi
else
    echo "[1/4] Found existing local .env configuration."
fi

# 2. Initialize resume/master_resume.yaml from example if missing
if [ ! -f "resume/master_resume.yaml" ]; then
    if [ -f "resume/master_resume.example.yaml" ]; then
        echo "[2/4] Initializing resume/master_resume.yaml from template..."
        cp resume/master_resume.example.yaml resume/master_resume.yaml
    fi
else
    echo "[2/4] Found existing local resume/master_resume.yaml."
fi

# 3. Interactive Personalization Prompts
echo ""
echo "--- Quick Profile Customization (Press Enter to keep defaults) ---"

DEFAULT_NAME="Candidate Name"
read -r -p "Enter your Full Name [$DEFAULT_NAME]: " INPUT_NAME
INPUT_NAME="${INPUT_NAME:-$DEFAULT_NAME}"

DEFAULT_TITLE="Senior Full-Stack & Distributed Systems Engineer"
read -r -p "Enter your Target Role Title [$DEFAULT_TITLE]: " INPUT_TITLE
INPUT_TITLE="${INPUT_TITLE:-$DEFAULT_TITLE}"

read -r -p "Enter Google Gemini API Key (Optional - press Enter for 100% offline mode): " INPUT_KEY

# Update .env if customized
if [ -n "$INPUT_KEY" ]; then
    sed -i.bak "s/GEMINI_API_KEY=.*/GEMINI_API_KEY=$INPUT_KEY/" .env 2>/dev/null || true
    rm -f .env.bak
fi

# Update master_resume.yaml with personalized name if provided
if [ "$INPUT_NAME" != "$DEFAULT_NAME" ] && [ -f "resume/master_resume.yaml" ]; then
    sed -i.bak "s/name: Candidate Name/name: $INPUT_NAME/" resume/master_resume.yaml 2>/dev/null || true
    rm -f resume/master_resume.yaml.bak
    echo "[Personalization] Updated resume/master_resume.yaml with name: $INPUT_NAME"
fi

echo -e "\n[3/4] Setup configuration saved successfully!"

# 4. Docker Readiness & Launch Option
echo ""
if ! command -v docker >/dev/null 2>&1; then
    echo "[Notice] 'docker' command not found. Please install Docker to run containers."
    echo "Setup complete. When Docker is ready, run: ./run_pipeline.sh"
    exit 0
fi

if ! docker info >/dev/null 2>&1; then
    echo "[Notice] Docker daemon is not currently running."
    echo "Setup complete! Once you start Docker, launch the autopilot with:"
    echo "  ./run_pipeline.sh"
    echo ""
    exit 0
fi

echo "[4/4] Docker is running and healthy!"
read -r -p "Would you like to run the autonomous career pipeline now? (Y/n): " RUN_NOW
RUN_NOW="${RUN_NOW:-Y}"

if [[ "$RUN_NOW" =~ ^[Yy]$ ]]; then
    echo -e "\nStarting autonomous pipeline...\n"
    ./run_pipeline.sh
else
    echo -e "\nSetup complete! You can run the pipeline anytime with:"
    echo "  ./run_pipeline.sh"
    echo ""
fi
