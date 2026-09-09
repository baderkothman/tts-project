# Single-process deployment: FastAPI serves both the API and the built
# frontend from one origin (backend/app/main.py already mounts
# frontend/dist/ when present — this is that mode, not a new one).
#
# Model weights (~2.4GB Lahgtna + ~1.2GB Fine-Tashkeel) are NOT baked into
# this image — they download on first boot into $HF_HOME via the same
# `omnivoice`/`transformers` from_pretrained() calls used locally. On
# Railway, mount a persistent Volume at $HF_HOME (see README's "Deploy
# (Railway)" section) so a redeploy doesn't pay that download again.

# ---------- Stage 1: build the frontend ----------
FROM node:22-slim AS frontend-build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---------- Stage 2: Python runtime ----------
FROM python:3.12-slim AS runtime

# espeak-ng: Kokoro's phonemizer + the transliteration fallback
# (services/english_tts.py, services/transliterator.py).
# libsndfile1: soundfile's runtime dependency (services/audio.py).
# ffmpeg: the Talking Avatar feature's video encoding
# (services/avatar_engines/stub_engine.py shells out to it directly — see
# docs/AVATAR_SETUP.md). Face detection for portrait validation needs no
# separate system package — it's bundled inside the pinned
# opencv-python-headless<5 wheel (see pyproject.toml's comment on that pin).
RUN apt-get update && apt-get install -y --no-install-recommends \
      espeak-ng \
      libsndfile1 \
      ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# `torch` from plain PyPI on Linux defaults to the CUDA build, which drags
# in nvidia_cudnn/cuda_toolkit/etc. as pip dependencies — several GB nothing
# on a standard (GPU-less) Railway service will ever use (confirmed directly:
# an earlier build of this image spent 25+ minutes downloading a 454MB CUDA
# torch wheel, then started on a 651MB cuDNN wheel, with more NVIDIA
# packages still queued). Installing the CPU wheel from PyTorch's own index
# *first* means the later `pip install .` finds torch already satisfied
# instead of replacing it with the CUDA build.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY pyproject.toml ./
COPY backend/__init__.py ./backend/__init__.py
COPY backend/app/ ./backend/app/
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu .

COPY --from=frontend-build /app/dist ./frontend/dist

# Overridable at deploy time (Railway env vars) — this is just the
# container-local default so `docker run` alone works for a smoke test.
ENV HF_HOME=/data/hf_cache
ENV PYTHONUNBUFFERED=1

EXPOSE 8000
# Railway injects $PORT; uvicorn must bind 0.0.0.0 (not the 127.0.0.1
# `--reload` dev default) to be reachable from outside the container.
CMD ["sh", "-c", "python -m uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
