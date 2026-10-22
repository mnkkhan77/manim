# On-disk history of past renders, shown in app.py's sidebar. Each saved
# session copies its final video into sessions/<id>/ because
# interview_simulation.py's manim output path is always the same filename —
# without copying, the next render would silently overwrite it.
import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SESSIONS_DIR = BASE_DIR / "sessions"
INDEX_PATH = SESSIONS_DIR / "index.json"


def _load_index():
    if not INDEX_PATH.exists():
        return []
    with open(INDEX_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_index(entries):
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)


def list_sessions():
    """Newest first."""
    return sorted(_load_index(), key=lambda e: e["created_at"], reverse=True)


def save_session(config, video_path, label, render_settings=None, kind="interview"):
    session_id = uuid.uuid4().hex[:12]
    session_dir = SESSIONS_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    video_path = Path(video_path)
    dest_video = session_dir / video_path.name
    shutil.copy2(video_path, dest_video)

    entries = _load_index()
    entries.append(
        {
            "id": session_id,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "label": label,
            "config": config,
            "render_settings": render_settings or {},
            "video_filename": dest_video.name,
            "kind": kind,
        }
    )
    _save_index(entries)
    return session_id, dest_video


def get_video_path(entry):
    return SESSIONS_DIR / entry["id"] / entry["video_filename"]


def delete_session(session_id):
    entries = _load_index()
    entries = [e for e in entries if e["id"] != session_id]
    _save_index(entries)
    session_dir = SESSIONS_DIR / session_id
    if session_dir.exists():
        shutil.rmtree(session_dir)
