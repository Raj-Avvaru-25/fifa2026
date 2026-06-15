"""JSON file cache with per-resource timestamps.

We deliberately use plain JSON files (not SQLite) because the GitHub Actions
refresh commits the cache back to the repo — text diffs are clean and reviewable,
a binary DB blob is not. Every write stamps an ISO-8601 UTC timestamp into
``meta.json`` so the app can show "last refreshed" and flag stale data.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fifa import config


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dirs() -> None:
    for d in (config.CACHE_DIR, config.SQUADS_DIR, config.AI_DIR):
        d.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------- #
# Low-level read / write
# --------------------------------------------------------------------------- #

def _read(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _write(path: Path, data: Any) -> None:
    _ensure_dirs()
    # sort_keys keeps git diffs stable across refreshes.
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )


# --------------------------------------------------------------------------- #
# Meta (timestamps + quota)
# --------------------------------------------------------------------------- #

def read_meta() -> dict:
    """Return the meta document, with sane defaults if it doesn't exist yet."""
    meta = _read(config.CACHE_DIR / "meta.json")
    if not isinstance(meta, dict):
        meta = {}
    meta.setdefault("last_refreshed", None)
    meta.setdefault("source", None)          # "api-football" or "mock"
    meta.setdefault("resources", {})         # name -> iso timestamp
    meta.setdefault("squads_refreshed", {})  # team_id -> iso timestamp
    meta.setdefault("quota", {})             # api-football quota snapshot
    return meta


def write_meta(meta: dict) -> None:
    _write(config.CACHE_DIR / "meta.json", meta)


def touch_resource(meta: dict, name: str) -> None:
    """Stamp ``name`` (and the global last_refreshed) with the current time."""
    now = _utcnow_iso()
    meta["resources"][name] = now
    meta["last_refreshed"] = now


# --------------------------------------------------------------------------- #
# Named resources (teams / standings / fixtures)
# --------------------------------------------------------------------------- #

def read_resource(name: str) -> Any | None:
    return _read(config.CACHE_DIR / f"{name}.json")


def write_resource(name: str, data: Any) -> None:
    _write(config.CACHE_DIR / f"{name}.json", data)


# --------------------------------------------------------------------------- #
# Squads (one file per team)
# --------------------------------------------------------------------------- #

def read_squad(team_id: int) -> Any | None:
    return _read(config.SQUADS_DIR / f"{team_id}.json")


def write_squad(team_id: int, data: Any) -> None:
    _write(config.SQUADS_DIR / f"{team_id}.json", data)


def all_squads() -> dict[int, Any]:
    """Return every cached squad keyed by team id."""
    squads: dict[int, Any] = {}
    if not config.SQUADS_DIR.exists():
        return squads
    for path in config.SQUADS_DIR.glob("*.json"):
        try:
            squads[int(path.stem)] = _read(path)
        except ValueError:
            continue
    return squads


# --------------------------------------------------------------------------- #
# AI artifacts (summaries / predictions)
# --------------------------------------------------------------------------- #

def read_ai(name: str) -> Any | None:
    return _read(config.AI_DIR / f"{name}.json")


def write_ai(name: str, data: Any) -> None:
    _write(config.AI_DIR / f"{name}.json", data)
