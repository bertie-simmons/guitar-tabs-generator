import os
from pathlib import Path

# file path of dir of local upload store
UPLOAD_DIR = Path(os.environ.get("GTAB_UPLOAD_DIR", "uploads"))

# max attempts a worker can start a job before its failed
MAX_ATTEMPTS = int(os.environ.get("GTAB_MAX_ATTEMPTS", "3"))

# file path of state for filebacked job store and queue
# will be Azure Table + Queue Storage in future
STATE_DIR = Path(os.environ.get("GTAB_STATE_DIR", ".gtab-state"))


# file what actually is used
# memory is only for running in one process
# TODO: add azure for azure storage stuff; typos fail silently
JOBS_BACKEND = os.environ.get("GTAB_JOBS_BACKEND", "file")

# origins allowed to call the api; seperated by comma
CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("GTAB_CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
