"""Runtime configuration, read from the environment with local-dev defaults.

Split out so the API and the worker agree on where things live without importing
each other. The env vars are what a Docker / Azure deployment overrides.
"""

import os
from pathlib import Path

# Directory the API writes uploaded videos to and the worker reads them from.
# With separate containers this needs to be shared storage (a volume, or object
# storage the `Job.source_path` points into) - a plain path only works while the
# API and worker share a filesystem.
UPLOAD_DIR = Path(os.environ.get("GTAB_UPLOAD_DIR", "uploads"))

# Directory the worker writes extracted WAV audio to.
AUDIO_DIR = Path(os.environ.get("GTAB_AUDIO_DIR", "audio_cache"))

# Where the file-backed job store and queue keep their state - the local
# stand-in for Azure Table + Queue Storage. A separate worker process on the
# same machine reads this directory, which is what lets the API and worker run
# as two processes today.
STATE_DIR = Path(os.environ.get("GTAB_STATE_DIR", ".gtab-state"))

# Job store / queue backend: "file" (default, works across processes) or
# "memory" (single process; used by the tests).
JOBS_BACKEND = os.environ.get("GTAB_JOBS_BACKEND", "file")

# Comma-separated list of origins allowed to call the API from a browser.
CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("GTAB_CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]


def ensure_dirs() -> None:
    """Create the upload and audio directories if they do not exist yet."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
