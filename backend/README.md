# Backend

FastAPI service that turns an uploaded guitar video into tablature.

```
video => ffmpeg => mono 22.05 kHz wav => basic-pitch => notes => (string, fret) positions
        extract_audio            detect_notes                notes_to_tab
```

## Modules

| file           | responsibility                                              |
| -------------- | ---------------------------------------------------------- |
| `main.py`      | HTTP API, in-memory job store, background processing        |
| `audio.py`     | `extract_audio` (ffmpeg), `load_audio`, `detect_notes`      |
| `tabs.py`      | map notes to the most playable fretboard positions          |
| `models.py`    | pydantic models: `Note`, `TabPosition`, `Tab`, `Job`        |
| `constants.py` | tuning, sample rate, thresholds                             |

## API

| method | path                | purpose                                            |
| ------ | ------------------- | ------------------------------------------------- |
| GET    | `/health`           | liveness check                                     |
| POST   | `/upload`           | multipart file upload, returns `{ "job_id": ... }` |
| GET    | `/status/{job_id}`  | `{ status, error }` where status is pending/processing/done/failed |
| GET    | `/result/{job_id}`  | the `Tab` (409 until the job is `done`)            |

Processing runs in a background task; the client polls `/status` then fetches `/result`.
Job state is an in-memory dict — fine for a single-process demo, not for production.

## Running

Requires [ffmpeg](https://ffmpeg.org/) on `PATH`.

```bash
python -m venv .venv && source .venv/Scripts/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open http://localhost:8000/docs to try it.

## Tests

```bash
pytest -m "not slow"   # fast unit + route tests
pytest                 # also runs the basic-pitch model test
```
