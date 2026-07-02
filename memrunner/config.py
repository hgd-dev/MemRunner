from __future__ import annotations

import json
import os
import re
from urllib.parse import parse_qs, urlparse
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

APP_DIR = Path(".memrunner")
SETTINGS_PATH = APP_DIR / "settings.json"
RUN_STATE_PATH = APP_DIR / "current_run.json"
LOG_PATH = APP_DIR / "memrunner.log"


@dataclass(frozen=True)
class MemRunnerConfig:
    course_id: str = ""
    email: str = ""
    password: str = ""
    source_label: str = "source"
    target_label: str = "target"
    db_path: Path = Path("memrunner_vocab.sqlite3")
    headless: bool = False
    mute_audio: bool = True
    action_delay_s: float = 0.04
    idle_timeout_s: float = 3.0

    @property
    def learn_url(self) -> str:
        return f"https://community-courses.memrise.com/aprender/learn?course_id={self.course_id}"

    @property
    def review_url(self) -> str:
        return f"https://community-courses.memrise.com/aprender/review?course_id={self.course_id}"

    @property
    def speed_url(self) -> str:
        return f"https://community-courses.memrise.com/aprender/speed?course_id={self.course_id}"

    def missing_required(self) -> list[str]:
        missing: list[str] = []
        if not self.course_id:
            missing.append("course_id")
        if not self.email:
            missing.append("email")
        if not self.password:
            missing.append("password")
        return missing

    def require_ready(self) -> None:
        missing = self.missing_required()
        if missing:
            joined = ", ".join(missing)
            raise RuntimeError(
                "MemRunner is missing required settings: "
                f"{joined}. Open `memrunner ui` and fill the Settings card, "
                "or provide them through .env."
            )



def extract_course_id(value: Any) -> str:
    """Accept a raw Memrise course ID or a copied course/home URL and return the ID.

    Supported examples:
    - 1234567
    - https://community-courses.memrise.com/community/course/1234567/course-name/
    - https://community-courses.memrise.com/aprender/learn?course_id=1234567
    - https://community-courses.memrise.com/aprender/review?course_id=1234567
    - https://community-courses.memrise.com/aprender/speed?course_id=1234567
    """
    raw = str(value or "").strip()
    if not raw:
        return ""

    parsed = urlparse(raw)
    query_course_id = parse_qs(parsed.query).get("course_id")
    if query_course_id and query_course_id[0].strip():
        return query_course_id[0].strip()

    path = parsed.path if parsed.scheme or parsed.netloc else raw
    match = re.search(r"/(?:community/)?course/(\d+)(?:/|$)", path)
    if match:
        return match.group(1)

    match = re.fullmatch(r"\s*(\d+)\s*", raw)
    if match:
        return match.group(1)

    # Last-resort extraction for copied text that contains a course URL fragment.
    match = re.search(r"course_id=(\d+)", raw) or re.search(r"/(?:community/)?course/(\d+)(?:/|$)", raw)
    if match:
        return match.group(1)

    return raw

def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).casefold() in {"1", "true", "yes", "on"}


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_path(value: Any, default: str) -> Path:
    raw = str(value or default).strip() or default
    return Path(raw)


def load_config(env_path: str | Path | None = None, *, require_ready: bool = True) -> MemRunnerConfig:
    if env_path:
        load_dotenv(env_path)
    else:
        load_dotenv()

    saved = _read_json(SETTINGS_PATH)

    # Dashboard settings are the normal-user path. Environment variables remain
    # useful for power users, CI, or temporary overrides.
    course_id = os.getenv("MEMRISE_COURSE_ID", saved.get("course_id", ""))
    email = os.getenv("MEMRISE_EMAIL", saved.get("email", ""))
    password = os.getenv("MEMRISE_PASSWORD", saved.get("password", ""))
    source_label = os.getenv("MEMRUNNER_SOURCE_LABEL", saved.get("source_label", "source"))
    target_label = os.getenv("MEMRUNNER_TARGET_LABEL", saved.get("target_label", "target"))
    db_path = _as_path(os.getenv("MEMRUNNER_DB_PATH", saved.get("db_path", "memrunner_vocab.sqlite3")), "memrunner_vocab.sqlite3")
    headless = _as_bool(os.getenv("MEMRUNNER_HEADLESS", saved.get("headless", False)), False)
    mute_audio = _as_bool(os.getenv("MEMRUNNER_MUTE_AUDIO", saved.get("mute_audio", True)), True)
    action_delay_s = _as_float(os.getenv("MEMRUNNER_ACTION_DELAY_S", saved.get("action_delay_s", 0.04)), 0.04)
    idle_timeout_s = _as_float(os.getenv("MEMRUNNER_IDLE_TIMEOUT_S", saved.get("idle_timeout_s", 3.0)), 3.0)

    config = MemRunnerConfig(
        course_id=extract_course_id(course_id),
        email=str(email).strip(),
        password=str(password),
        source_label=str(source_label).strip() or "source",
        target_label=str(target_label).strip() or "target",
        db_path=db_path,
        headless=headless,
        mute_audio=mute_audio,
        action_delay_s=action_delay_s,
        idle_timeout_s=idle_timeout_s,
    )
    if require_ready:
        config.require_ready()
    return config


def save_dashboard_settings(data: dict[str, Any]) -> MemRunnerConfig:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    current = _read_json(SETTINGS_PATH)

    password = data.get("password", "")
    if password == "__KEEP__":
        password = current.get("password", "")

    settings = {
        "course_id": extract_course_id(data.get("course_id", current.get("course_id", ""))),
        "email": str(data.get("email", current.get("email", ""))).strip(),
        "password": str(password),
        "source_label": str(data.get("source_label", current.get("source_label", "source"))).strip() or "source",
        "target_label": str(data.get("target_label", current.get("target_label", "target"))).strip() or "target",
        "db_path": str(data.get("db_path", current.get("db_path", "memrunner_vocab.sqlite3"))).strip() or "memrunner_vocab.sqlite3",
        "headless": _as_bool(data.get("headless", False), False),
        "mute_audio": _as_bool(data.get("mute_audio", True), True),
        "action_delay_s": _as_float(data.get("action_delay_s", current.get("action_delay_s", 0.04)), 0.04),
        "idle_timeout_s": _as_float(data.get("idle_timeout_s", current.get("idle_timeout_s", 3.0)), 3.0),
    }
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    return load_config(require_ready=False)


def public_config_dict(config: MemRunnerConfig) -> dict[str, Any]:
    data = asdict(config)
    data["db_path"] = str(config.db_path)
    data["password"] = "" if not config.password else "********"
    return data
