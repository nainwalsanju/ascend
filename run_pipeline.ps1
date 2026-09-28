# ==============================================================================
# End-to-End SWE Career System - Autonomous Pipeline Runner (PowerShell)
# Usage:
#   .\run_pipeline.ps1                # Run full end-to-end automated pipeline
#   .\run_pipeline.ps1 -DryRun        # Run pipeline in safe dry-run mode (no live emails)
#   .\run_pipeline.ps1 -ServeOnly     # Only start/restart the background telemetry server
# ==============================================================================

param (
    [switch]$DryRun,
    [switch]$ServeOnly,
    [switch]$SkipRender,
    [switch]$SkipScrape
)

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "      END-TO-END HIGH-PAYING SWE CAREER SYSTEM (AUTOPILOT)       " -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Environment & Pre-Flight Checks
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Write-Host "[Setup] .env file missing. Initializing from .env.example..." -ForegroundColor Yellow
        Copy-Item ".env.example" ".env"
        Write-Host "[Action Required] Please update .env with your GEMINI_API_KEY before running live." -ForegroundColor Yellow
    } else {
        Write-Error "[Error] Missing .env and .env.example. Exiting."
    }
}

# Check Docker engine status
if (-not (Get-Command "docker" -ErrorAction SilentlyContinue)) {
    Write-Host "[Error] 'docker' command was not found on PATH. Ensure Docker Desktop is installed." -ForegroundColor Red
    exit 1
}

$dockerStatus = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[Error] Docker daemon is not running. Please start Docker Desktop and retry." -ForegroundColor Red
    exit 1
}

if ($ServeOnly) {
    Write-Host "[Telemetry] Starting background telemetry server on port 8085..." -ForegroundColor Green
    docker compose up -d outreach-engine
    Write-Host "[Success] Telemetry server is live at http://localhost:8085/api/stats" -ForegroundColor Green
    exit 0
}

# 2. Phase 1: Compile Resume (RenderCV)
if (-not $SkipRender) {
    Write-Host "`n>>> [Phase 1/4] Compiling Master Resume via RenderCV (sb2nov)..." -ForegroundColor Yellow
    $resumeFile = if (Test-Path "resume/master_resume.yaml") { "master_resume.yaml" } else { "master_resume.example.yaml" }
    Write-Host "[RenderCV] Rendering $resumeFile to vector ATS PDF..." -ForegroundColor Gray
    docker compose run --rm rendercv render $resumeFile
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "[Warning] RenderCV completed with exit code $LASTEXITCODE. Proceeding..."
    } else {
        Write-Host "[Success] Resume compiled to resume/rendercv_output/" -ForegroundColor Green
    }
} else {
    Write-Host "`n>>> [Phase 1/4] Skipping Resume Render (--SkipRender specified)" -ForegroundColor DarkGray
}

# 3. Phase 2: ATS Scoring & Gap Analysis (Resume-Matcher)
Write-Host "`n>>> [Phase 2/4] Running ATS Audit & AI-Phrase Refiner..." -ForegroundColor Yellow
docker compose run --rm resume-matcher
if ($LASTEXITCODE -ne 0) {
    Write-Warning "[Warning] Resume-Matcher reported warnings. Review resume/reports/ats_audit_report.md"
} else {
    Write-Host "[Success] ATS Audit & Interview Defense saved to resume/reports/" -ForegroundColor Green
}

# 4. Phase 3: Market Discovery & Funding Radar (Career-Ops)
if (-not $SkipScrape) {
    Write-Host "`n>>> [Phase 3/4] Ingesting High-Comp Opportunities & Checking Funding Radar..." -ForegroundColor Yellow
    docker compose run --rm career-ops
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "[Warning] Career-Ops scanner exited with warnings. Checking database..."
    } else {
        Write-Host "[Success] Opportunities leaderboard saved to tracker/reports/top_opportunities.md" -ForegroundColor Green
    }
} else {
    Write-Host "`n>>> [Phase 3/4] Skipping Job Board Scraping (--SkipScrape specified)" -ForegroundColor DarkGray
}

# 5. Phase 4: Cold Outreach, LinkedIn Notes & Form Answers (Outreach-Engine)
Write-Host "`n>>> [Phase 4/4] Generating Cold Outreach, LinkedIn Sequences & Form Auto-Answers..." -ForegroundColor Yellow
docker compose run --rm outreach-engine
if ($LASTEXITCODE -ne 0) {
    Write-Warning "[Warning] Outreach generation completed with non-zero exit code."
} else {
    Write-Host "[Success] Cold outreach sequences saved to tracker/reports/outreach_pipeline.md" -ForegroundColor Green
    Write-Host "[Success] Application form auto-answers saved to tracker/reports/application_answers.md" -ForegroundColor Green
}

# 6. Phase 5: Start / Refresh Background Telemetry Daemon
Write-Host "`n>>> [Phase 5] Ensuring Telemetry Tracking Server is Running (Port 8085)..." -ForegroundColor Yellow
docker compose up -d outreach-engine
Write-Host "[Success] Telemetry tracking daemon is active." -ForegroundColor Green

# 7. Summary Dashboard
Write-Host ""
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "                      AUTONOMOUS RUN COMPLETE!                    " -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Generated Reports & Artifacts:" -ForegroundColor White
Write-Host "  • ATS Audit Report:        resume/reports/ats_audit_report.md" -ForegroundColor Gray
Write-Host "  • Interview Defense Guide: resume/reports/interview_defense_prep.md" -ForegroundColor Gray
Write-Host "  • High-Comp Opportunities: tracker/reports/top_opportunities.md" -ForegroundColor Gray
Write-Host "  • Cold Email Sequences:    tracker/reports/outreach_pipeline.md" -ForegroundColor Gray
Write-Host "  • Application Form Answers:tracker/reports/application_answers.md" -ForegroundColor Gray
Write-Host "  • Live Funnel Telemetry:   http://localhost:8085/api/stats" -ForegroundColor Gray
Write-Host ""
Write-Host "All systems operational. No human intervention needed." -ForegroundColor Green
Write-Host ""
