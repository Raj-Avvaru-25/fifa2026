"""Pure helpers that turn raw API-Football payloads into UI/AI-friendly shapes.

Shared by the Streamlit pages and the AI prompt builder so both read the data
the same way. No I/O, no network — just reshaping.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

# Status codes API-Football uses for in-progress matches.
_LIVE = {"1H", "2H", "HT", "ET", "BT", "P", "LIVE"}
_FINISHED = {"FT", "AET", "PEN"}


def groups_from_standings(standings: Any) -> list[dict]:
    """Return [{"group": "Group A", "rows": [...]}, ...] from a standings payload."""
    if not standings:
        return []
    league = standings[0].get("league", {})
    table = league.get("standings", []) or []
    groups = []
    for block in table:
        if not block:
            continue
        name = block[0].get("group") or "Group"
        groups.append({"group": name, "rows": block})
    return groups


def team_index(teams: Any) -> dict[int, dict]:
    """Map team id -> team dict from a teams payload."""
    index: dict[int, dict] = {}
    for entry in teams or []:
        t = entry.get("team", {})
        if "id" in t:
            index[t["id"]] = t
    return index


def _kickoff(fx: dict) -> str:
    return fx.get("fixture", {}).get("date", "")


def split_fixtures(fixtures: Any) -> dict[str, list]:
    """Bucket fixtures into live / finished / upcoming, each time-sorted."""
    live, finished, upcoming = [], [], []
    for fx in fixtures or []:
        status = fx.get("fixture", {}).get("status", {}).get("short", "")
        if status in _LIVE:
            live.append(fx)
        elif status in _FINISHED:
            finished.append(fx)
        else:
            upcoming.append(fx)
    live.sort(key=_kickoff)
    finished.sort(key=_kickoff, reverse=True)   # most recent first
    upcoming.sort(key=_kickoff)                  # soonest first
    return {"live": live, "finished": finished, "upcoming": upcoming}


def squad_players(squad_doc: Any) -> dict:
    """Return {"team": {...}, "players": [...]} from a squads payload."""
    if not squad_doc:
        return {"team": {}, "players": []}
    first = squad_doc[0]
    return {"team": first.get("team", {}), "players": first.get("players", []) or []}


def fmt_kickoff(iso: str) -> str:
    """Human kickoff label, e.g. 'Tue 17 Jun · 18:00 UTC'."""
    if not iso:
        return "TBD"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return iso
    return dt.strftime("%a %d %b · %H:%M UTC")
