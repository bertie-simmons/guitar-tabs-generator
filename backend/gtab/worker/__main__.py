"""``python -m gtab.worker`` - run the queue consumer loop.

Reads jobs from the same store and queue the API writes to (see
``GTAB_JOBS_BACKEND`` / ``GTAB_STATE_DIR`` in ``gtab.config``). Stop it with
Ctrl-C; it finishes the job in hand first.
"""

import logging

from gtab.worker.runner import run

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

if __name__ == "__main__":
    run()
