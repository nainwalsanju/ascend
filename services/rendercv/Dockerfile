FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install fontconfig and common free typography packages for ATS LaTeX/Typst rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    fontconfig \
    libfontconfig1 \
    fonts-lmodern \
    fonts-liberation \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install rendercv[full] for complete CLI, typst and templating engine, plus click
RUN pip install --no-cache-dir "rendercv[full]" click

WORKDIR /work

ENTRYPOINT ["rendercv"]
CMD ["--help"]
