# ==============================================================================
# Ascend: 60-Second Interactive Setup Wizard (PowerShell)
# Usage:
#   .\setup.ps1
# ==============================================================================

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "           ASCEND: 60-SECOND PLUG & PLAY SETUP WIZARD            " -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "The Autonomous SWE Career Acceleration Engine ($130k-$350k+)." -ForegroundColor Gray
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# 1. Initialize .env from .env.example if missing
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Write-Host "[1/4] Creating local .env from .env.example..." -ForegroundColor Green
        Copy-Item ".env.example" ".env"
    }
} else {
    Write-Host "[1/4] Found existing local .env configuration." -ForegroundColor Green
}

# 2. Initialize resume/master_resume.yaml from example if missing
if (-not (Test-Path "resume/master_resume.yaml")) {
    if (Test-Path "resume/master_resume.example.yaml") {
        Write-Host "[2/4] Initializing resume/master_resume.yaml from template..." -ForegroundColor Green
        Copy-Item "resume/master_resume.example.yaml" "resume/master_resume.yaml"
    }
} else {
    Write-Host "[2/4] Found existing local resume/master_resume.yaml." -ForegroundColor Green
}

# 3. Interactive Personalization Prompts
Write-Host ""
Write-Host "--- Quick Profile Customization (Press Enter to keep defaults) ---" -ForegroundColor Yellow

$defaultName = "Candidate Name"
$inputName = Read-Host "Enter your Full Name [$defaultName]"
if ([string]::IsNullOrWhiteSpace($inputName)) { $inputName = $defaultName }

$defaultTitle = "Senior Full-Stack & Distributed Systems Engineer"
$inputTitle = Read-Host "Enter your Target Role Title [$defaultTitle]"
if ([string]::IsNullOrWhiteSpace($inputTitle)) { $inputTitle = $defaultTitle }

$inputKey = Read-Host "Enter Google Gemini API Key (Optional - press Enter for 100% offline mode)"

# Update .env if customized
if ($inputName -ne $defaultName -or -not [string]::IsNullOrWhiteSpace($inputKey)) {
    $envContent = Get-Content ".env" -Raw
    if (-not [string]::IsNullOrWhiteSpace($inputKey)) {
        $envContent = $envContent -replace "GEMINI_API_KEY=.*", "GEMINI_API_KEY=$inputKey"
    }
    Set-Content -Path ".env" -Value $envContent
}

# Update master_resume.yaml with personalized name if provided
if ($inputName -ne $defaultName -and (Test-Path "resume/master_resume.yaml")) {
    $resumeContent = Get-Content "resume/master_resume.yaml" -Raw
    $resumeContent = $resumeContent -replace "name: Candidate Name", "name: $inputName"
    Set-Content -Path "resume/master_resume.yaml" -Value $resumeContent
    Write-Host "[Personalization] Updated resume/master_resume.yaml with name: $inputName" -ForegroundColor Green
}

Write-Host "`n[3/4] Setup configuration saved successfully!" -ForegroundColor Green

# 4. Docker Readiness & Launch Option
Write-Host ""
$dockerCmd = Get-Command "docker" -ErrorAction SilentlyContinue
if (-not $dockerCmd) {
    Write-Host "[Notice] 'docker' command not found. Please install Docker Desktop to run containers." -ForegroundColor Red
    Write-Host "Setup complete. When Docker is ready, run: .\run_pipeline.ps1" -ForegroundColor Yellow
    exit 0
}

$dockerInfo = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[Notice] Docker Desktop is not currently running." -ForegroundColor Yellow
    Write-Host "Setup complete! Once you start Docker Desktop, launch the autopilot with:" -ForegroundColor White
    Write-Host "  .\run_pipeline.ps1" -ForegroundColor Cyan
    Write-Host ""
    exit 0
}

Write-Host "[4/4] Docker Desktop is running and healthy!" -ForegroundColor Green
$runNow = Read-Host "Would you like to run the autonomous career pipeline now? (Y/n)"
if ([string]::IsNullOrWhiteSpace($runNow) -or $runNow.Trim().ToLower() -eq "y") {
    Write-Host "`nStarting autonomous pipeline...`n" -ForegroundColor Cyan
    & ".\run_pipeline.ps1"
} else {
    Write-Host "`nSetup complete! You can run the pipeline anytime with:" -ForegroundColor White
    Write-Host "  .\run_pipeline.ps1" -ForegroundColor Cyan
    Write-Host ""
}
