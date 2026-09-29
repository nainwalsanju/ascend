#!/bin/sh
set -e

# If master_resume.yaml does not exist, but master_resume.example.yaml exists, initialize it
if [ ! -f "master_resume.yaml" ] && [ -f "master_resume.example.yaml" ]; then
    echo "[RenderCV Autopilot] master_resume.yaml not found. Initializing from master_resume.example.yaml..."
    cp master_resume.example.yaml master_resume.yaml
fi

# If no arguments provided, default to rendering master_resume.yaml
if [ "$#" -eq 0 ]; then
    exec rendercv render master_resume.yaml
fi

exec rendercv "$@"
