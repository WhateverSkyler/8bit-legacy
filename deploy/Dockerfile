# 8-Bit Legacy pipeline runtime (drop_watcher + buffer_scheduler + podcast/photo pipelines)
# Built on your Mac via deploy-to-truenas.sh, loaded on TrueNAS, run via docker compose.

FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=America/New_York

# System deps:
#   ffmpeg        — render_clip.py (needed for the vertical-short renderer)
#   fonts-*       — ASS karaoke captions + Bebas Neue baseline fallback
#   libsndfile1   — used by some audio libs (prepare_music.py / transcribe normalization)
#   ca-certificates + tzdata — HTTPS to Anthropic/Zernio/YouTube + ET scheduling
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-dejavu-core \
    fonts-liberation \
    libsndfile1 \
    ca-certificates \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps first for layer caching
COPY deploy/requirements-pipeline.txt /tmp/requirements-pipeline.txt
RUN pip install --upgrade pip && pip install -r /tmp/requirements-pipeline.txt

# Repo code. Only the dirs the pipeline uses — NOT dashboard/ (explicitly out of scope).
COPY scripts/ /app/scripts/

# Intermediate artifacts (transcripts, rendered clips pre-archive, etc.) live inside the container
# at /app/data. The NAS drop/archive volumes are mounted separately at /media.
RUN mkdir -p /app/data/podcast /app/data/social-media /app/data/logs

ENV SCRIPTS_ROOT=/app/scripts \
    MEDIA_ROOT=/media \
    PYTHONPATH=/app/scripts

# drop_watcher runs the polling loop and invokes buffer_scheduler every ~60 min.
# SIGTERM is propagated so docker compose down cleanly stops the loop.
STOPSIGNAL SIGTERM

ENTRYPOINT ["python3", "/app/scripts/watcher/drop_watcher.py"]
