"""The worker: turn queued jobs into finished tabs.

`process_job` is the unit of work for one job; `run` is the loop that claims
ids off the queue and calls it. `python -m gtab.worker` runs the loop.
"""

from gtab.worker.runner import process_job, run

__all__ = ["process_job", "run"]
