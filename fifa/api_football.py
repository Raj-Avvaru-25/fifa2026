"""A thin API-Football (api-sports.io) client.

Only the handful of endpoints the dashboard needs are wrapped. Every call goes
through :func:`_get`, which surfaces the API's own ``errors`` array and tracks
how many requests remain on the daily quota via response headers.
"""

from __future__ import annotations

from typing import Any

import requests

from fifa import config


class APIFootballError(RuntimeError):
    """Raised when API-Football returns an error or an unexpected payload."""


class APIFootballClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or config.get_api_football_key()
        if not self.api_key:
            raise APIFootballError(
                "No API-Football key. Set API_FOOTBALL_KEY in the environment."
            )
        self.base = config.API_FOOTBALL_BASE.rstrip("/")
        # The most recent quota snapshot, populated from response headers.
        self.last_quota: dict[str, Any] = {}

    # ----------------------------------------------------------------- #
    def _get(self, path: str, params: dict | None = None) -> list[Any]:
        url = f"{self.base}/{path.lstrip('/')}"
        try:
            resp = requests.get(
                url,
                headers={"x-apisports-key": self.api_key},
                params=params or {},
                timeout=config.API_FOOTBALL_TIMEOUT,
            )
        except requests.RequestException as exc:  # network failure
            raise APIFootballError(f"Request to {path} failed: {exc}") from exc

        # Quota headers (present on the direct API-Sports host).
        self.last_quota = {
            "limit_day": resp.headers.get("x-ratelimit-requests-limit"),
            "remaining_day": resp.headers.get("x-ratelimit-requests-remaining"),
        }

        if resp.status_code != 200:
            raise APIFootballError(f"{path} -> HTTP {resp.status_code}: {resp.text[:200]}")

        payload = resp.json()
        errors = payload.get("errors")
        # API-Football returns errors as a dict (or an empty list when fine).
        if errors:
            raise APIFootballError(f"{path} -> {errors}")
        return payload.get("response", [])

    # ----------------------------------------------------------------- #
    # Endpoints
    # ----------------------------------------------------------------- #
    def status(self) -> dict:
        """Account/quota status — cheap, good for a connectivity check."""
        resp = self._get("status")
        return resp if isinstance(resp, dict) else (resp[0] if resp else {})

    def teams(self) -> list[Any]:
        return self._get("teams", {"league": config.LEAGUE_ID, "season": config.SEASON})

    def standings(self) -> list[Any]:
        return self._get("standings", {"league": config.LEAGUE_ID, "season": config.SEASON})

    def fixtures(self) -> list[Any]:
        return self._get("fixtures", {"league": config.LEAGUE_ID, "season": config.SEASON})

    def squad(self, team_id: int) -> list[Any]:
        return self._get("players/squads", {"team": team_id})
