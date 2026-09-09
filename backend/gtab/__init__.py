"""Guitar Tablature Generator backend.

The package is split into three layers:

* ``gtab.pipeline`` - pure video -> audio -> notes -> tab transforms
* ``gtab.worker``   - runs the pipeline for a queued job and records the result
* ``gtab.api``      - the FastAPI HTTP service clients talk to

``gtab.models`` holds the pydantic objects shared across all three, and
``gtab.jobs`` is the job store that the API writes to and the worker reads from.
Today everything runs in one process against an in-memory store; the split keeps
the API and worker independently deployable (Docker / Azure) once that store is
swapped for something out-of-process.
"""
