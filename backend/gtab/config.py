import os
from pathlib import Path

# file path of dir of local upload store
UPLOAD_DIR = Path(os.environ.get("GTAB_UPLOAD_DIR", "uploads"))

# max attempts a worker can start a job before its failed
MAX_ATTEMPTS = int(os.environ.get("GTAB_MAX_ATTEMPTS", "3"))

# file path of state for filebacked job store and queue
STATE_DIR = Path(os.environ.get("GTAB_STATE_DIR", ".gtab-state"))

# === backends ============================================================================

# memory - one process only (tests)
# file   - JSON files + a local upload dir, shared between processes on one machine
# azure  - Table Storage + Queue Storage + Blob Storage (Azurite locally)
BACKENDS = ("memory", "file", "azure")

JOBS_BACKEND = os.environ.get("GTAB_JOBS_BACKEND", "file")
if JOBS_BACKEND not in BACKENDS:
    raise ValueError(
        f"GTAB_JOBS_BACKEND={JOBS_BACKEND!r} - expected one of {', '.join(BACKENDS)}"
    )

# === azure ===============================================================================

# either a connection or an account name 
AZURE_STORAGE_CONNECTION_STRING = os.environ.get("GTAB_AZURE_STORAGE_CONNECTION_STRING")
AZURE_STORAGE_ACCOUNT = os.environ.get("GTAB_AZURE_STORAGE_ACCOUNT")
AZURE_UPLOAD_CONTAINER = os.environ.get("GTAB_AZURE_UPLOAD_CONTAINER", "uploads")
AZURE_JOB_TABLE = os.environ.get("GTAB_AZURE_JOB_TABLE", "jobs")
AZURE_JOB_QUEUE = os.environ.get("GTAB_AZURE_JOB_QUEUE", "jobs")

# how long a claimed queue message stays hidden from other workers 
# note to self : just be longer than the slowest job or a second worker picks it up mid-run
AZURE_QUEUE_VISIBILITY_TIMEOUT = int(os.environ.get("GTAB_AZURE_QUEUE_VISIBILITY_TIMEOUT", "900"))

# origins allowed to call the api; seperated by comma
CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("GTAB_CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
