"""Central configuration for the FIFA 2026 dashboard.

Every tunable knob lives here: where data comes from, how often it refreshes,
how much API quota a refresh is allowed to spend, and which Claude model writes
the summaries and predictions.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load variables from a local .env file (if present) into the environment.
load_dotenv()

# --- Paths -------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = PROJECT_ROOT / "data" / "cache"
SQUADS_DIR = CACHE_DIR / "squads"
AI_DIR = CACHE_DIR / "ai"


# --- Tournament --------------------------------------------------------------
# In API-Football the FIFA World Cup is league id 1. The 2026 edition is
# season 2026. These are the only two coordinates the whole pipeline needs.
LEAGUE_ID = int(os.environ.get("FIFA_LEAGUE_ID", "1"))
SEASON = int(os.environ.get("FIFA_SEASON", "2026"))
TOURNAMENT_NAME = "FIFA World Cup 2026"


# --- API-Football (api-sports.io) --------------------------------------------
# Get a free key at https://dashboard.api-football.com/ (100 requests/day on the
# free tier). The direct API-Sports host uses the `x-apisports-key` header.
API_FOOTBALL_BASE = os.environ.get("API_FOOTBALL_BASE", "https://v3.football.api-sports.io")
API_FOOTBALL_TIMEOUT = 20  # seconds per request


# --- Refresh policy ----------------------------------------------------------
# The whole point of the system: pull fresh stats every 6 hours. The app reads
# the cache and flags it amber once it is older than this.
REFRESH_INTERVAL_HOURS = 6

# Squads barely change during a tournament and there are 48 teams, so refreshing
# every squad on every 6h run would blow the 100/day quota. Instead we refresh a
# rotating slice each run and treat a squad as fresh for SQUAD_TTL_HOURS.
SQUAD_TTL_HOURS = 24
SQUADS_PER_RUN = int(os.environ.get("FIFA_SQUADS_PER_RUN", "12"))


# --- Claude (AI summaries + predictions) -------------------------------------
# claude-opus-4-8 is Anthropic's most capable model; it writes the group
# summaries and the structured match/tournament predictions.
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-4-8")
CLAUDE_EFFORT = os.environ.get("CLAUDE_EFFORT", "high")  # low | medium | high | xhigh | max
CLAUDE_MAX_TOKENS = 8000


def get_api_football_key() -> str | None:
    """Return the API-Football key from the environment, or None if unset."""
    key = os.environ.get("API_FOOTBALL_KEY")
    return key.strip() if key else None


def get_anthropic_key() -> str | None:
    """Return the Anthropic API key from the environment, or None if unset."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    return key.strip() if key else None
