"""Entrypoint shim: ``uvicorn main:app``.

The app lives in ``gtab.api.main``; the worker in ``gtab.worker``. This module
just re-exports the ASGI app so existing run commands keep working.
"""

from gtab.api.main import app

__all__ = ["app"]
