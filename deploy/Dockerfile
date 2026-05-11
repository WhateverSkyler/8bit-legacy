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

# Bebas Neue — required by generate_thumbnail.py for YT thumbnail titles.
# Installed under /usr/local/share/fonts so it's picked up by _find_bebas_font().
COPY assets/fonts/BebasNeue-Regular.ttf /usr/local/share/fonts/bebas-neue/BebasNeue-Regular.ttf

# Brand end-card (1080x1920) — overlaid on the last 4s of every rendered short
# by render_clip.py. Path mirrors repo layout so the existing END_CARD constant
# (ROOT / "assets/brand/end-card-9x16.png") resolves at runtime.
COPY assets/brand/end-card-9x16.png /app/assets/brand/end-card-9x16.png

# YuNet face-detection ONNX model (227KB) — used by scripts/podcast/_face_detect.py
# for centering shorts on the active speaker. Replaces the Haar cascades that had
# a 33% Gate-3 rejection rate due to false-positive detections (lamps, picture
# frames, etc.) and missed profile/angled poses.
COPY deploy/_models/face_detection_yunet_2023mar.onnx /app/data/podcast/_models/face_detection_yunet_2023mar.onnx

# Intermediate artifacts (transcripts, rendered clips pre-archive, etc.) live inside the container
# at /app/data. The NAS drop/archive volumes are mounted separately at /media.
RUN mkdir -p /app/data/podcast /app/data/social-media /app/data/logs

# Create the runtime user with the same UID/GID as the NAS's truenas_admin (950:950).
# Running as this user keeps files created under /media/* compatible with the SMB share's
# ACL inheritance — root-owned subdirs break it. See docs/TRUENAS-ACCESS.md.
# Also pre-create .cache and .local so HuggingFace Hub (used by faster-whisper) can
# write its model refs at runtime — otherwise transcribe.py fails silently with perm errors.
RUN groupadd --gid 950 pipeline \
    && useradd --uid 950 --gid 950 --home /app --shell /usr/sbin/nologin pipeline \
    && mkdir -p /app/.cache /app/.local /app/.cache/nltk_data /app/.cache/torch /app/.cache/huggingface \
    && chown -R 950:950 /app/data /app/.cache /app/.local

# whisperX needs writable cache locations; default fall-throughs are root-owned
# system paths that uid 950 can't write. Without these env vars, alignment fails
# silently with: "Permission denied: '/app/nltk_data'" or '/root/.cache/...'.
ENV SCRIPTS_ROOT=/app/scripts \
    MEDIA_ROOT=/media \
    PYTHONPATH=/app/scripts \
    NLTK_DATA=/app/.cache/nltk_data \
    TORCH_HOME=/app/.cache/torch \
    HF_HOME=/app/.cache/huggingface \
    XDG_CACHE_HOME=/app/.cache

USER 950:950

# drop_watcher runs the polling loop and invokes buffer_scheduler every ~60 min.
# SIGTERM is propagated so docker compose down cleanly stops the loop.
STOPSIGNAL SIGTERM

ENTRYPOINT ["python3", "/app/scripts/watcher/drop_watcher.py"]
