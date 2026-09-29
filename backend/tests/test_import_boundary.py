"""The API must not import the pipeline.

`gtab.api` only enqueues work; `gtab.worker` runs it. Keeping the pipeline (and
its ffmpeg / TensorFlow / librosa weight) out of the API's import graph is what
lets the two ship as separate, very differently sized container images. Run in a
subprocess because the test session itself imports the pipeline elsewhere.
"""

import subprocess
import sys
import textwrap
from pathlib import Path

BACKEND = Path(__file__).parent.parent

_CHECK = textwrap.dedent(
    """
    import sys
    import gtab.api.main  # noqa: F401

    forbidden = {"tensorflow", "librosa", "basic_pitch", "soundfile", "numpy"}
    leaked = sorted(
        m for m in sys.modules
        if m == "gtab.pipeline"
        or m.startswith("gtab.pipeline.")
        or m.split(".")[0] in forbidden
    )
    if leaked:
        print(",".join(leaked))
        sys.exit(1)
    """
)


def test_api_import_does_not_pull_in_the_pipeline():
    result = subprocess.run(
        [sys.executable, "-c", _CHECK],
        capture_output=True,
        text=True,
        cwd=BACKEND,
    )
    assert result.returncode == 0, (
        f"gtab.api.main pulled in: {result.stdout.strip()}\n{result.stderr}"
    )
