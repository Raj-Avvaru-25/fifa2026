"""The refresh job: pull World Cup 2026 stats into the JSON cache.

Run directly (``python -m fifa.fetch``) or on a schedule (GitHub Actions). It is
deliberately *quota-aware*: standings and fixtures refresh every run (a few API
calls), while squads — 48 teams, far too many to refetch every 6h on the free
100/day tier — refresh on a rotating, TTL-based basis.

If no API-Football key is present it falls back to bundled mock data, so the app
always has something coherent to render.

    python -m fifa.fetch                 # refresh stats from API-Football
    python -m fifa.fetch --with-ai       # also (re)generate Claude summaries/predictions
    python -m fifa.fetch --mock          # force mock data (no network)
    python -m fifa.fetch --force-squads  # ignore the squad TTL and refresh the full rotation
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

from fifa import ai, config, mock, store
from fifa.api_football import APIFootballClient, APIFootballError


def _parse_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _due_squads(team_ids, meta, *, force: bool) -> list:
    """Team ids whose cached squad is missing or older than the TTL, oldest first."""
    now = datetime.now(timezone.utc)
    refreshed = meta.get("squads_refreshed", {})
    scored = []
    for tid in team_ids:
        ts = _parse_iso(refreshed.get(str(tid)))
        if force or ts is None:
            age_hours = float("inf")
        else:
            age_hours = (now - ts).total_seconds() / 3600.0
        if force or age_hours >= config.SQUAD_TTL_HOURS:
            scored.append((age_hours, tid))
    scored.sort(reverse=True)  # most stale first
    return [tid for _, tid in scored]


def _team_ids_from(teams_payload) -> list:
    ids = []
    for entry in teams_payload or []:
        t = entry.get("team", {})
        if "id" in t:
            ids.append(t["id"])
    return ids


# --------------------------------------------------------------------------- #

def run(*, with_ai: bool = False, use_mock: bool = False, force_squads: bool = False) -> dict:
    meta = store.read_meta()
    now_iso = datetime.now(timezone.utc).isoformat()

    api_key = config.get_api_football_key()
    use_mock = use_mock or not api_key
    client = None
    if not use_mock:
        try:
            client = APIFootballClient(api_key)
        except APIFootballError as exc:
            print(f"⚠️  {exc}\n    Falling back to mock data.", file=sys.stderr)
            use_mock = True

    source = "mock" if use_mock else "api-football"
    print(f"→ Refreshing {config.TOURNAMENT_NAME} from: {source}")

    # --- Stats (cheap: ~3 calls when live) ---------------------------------
    if use_mock:
        teams, standings, fixtures = mock.teams(), mock.standings(), mock.fixtures()
    else:
        teams = client.teams()
        standings = client.standings()
        fixtures = client.fixtures()

    store.write_resource("teams", teams)
    store.touch_resource(meta, "teams")
    store.write_resource("standings", standings)
    store.touch_resource(meta, "standings")
    store.write_resource("fixtures", fixtures)
    store.touch_resource(meta, "fixtures")
    print(f"  ✓ teams ({len(teams)}), standings, fixtures ({len(fixtures)})")

    # --- Squads (rotating, quota-aware) ------------------------------------
    team_ids = _team_ids_from(teams) or (mock.all_team_ids() if use_mock else [])
    if use_mock:
        due = team_ids  # mock has no quota cost; refresh everything
    else:
        due = _due_squads(team_ids, meta, force=force_squads)[: config.SQUADS_PER_RUN]

    refreshed = 0
    for tid in due:
        try:
            data = mock.squad(tid) if use_mock else client.squad(tid)
        except APIFootballError as exc:
            print(f"  ⚠️  squad {tid} failed: {exc}", file=sys.stderr)
            continue
        store.write_squad(tid, data)
        meta["squads_refreshed"][str(tid)] = now_iso
        refreshed += 1
    remaining = max(0, len(team_ids) - len([t for t in team_ids
                                            if str(t) in meta["squads_refreshed"]]))
    print(f"  ✓ squads refreshed this run: {refreshed} (still missing: {remaining})")

    # --- Bookkeeping --------------------------------------------------------
    meta["source"] = source
    if client is not None:
        meta["quota"] = client.last_quota
    store.write_meta(meta)

    # --- AI (optional) ------------------------------------------------------
    if with_ai:
        anth = config.get_anthropic_key()
        if anth and not use_mock:
            try:
                ai.generate(standings, fixtures, api_key=anth)
                print("  ✓ AI summaries + predictions (Claude)")
            except Exception as exc:  # noqa: BLE001 — never let AI break a refresh
                print(f"  ⚠️  Claude generation failed ({exc}); using mock AI.", file=sys.stderr)
                ai.mock_ai(standings, fixtures)
        else:
            ai.mock_ai(standings, fixtures)
            why = "no ANTHROPIC_API_KEY" if not anth else "mock data"
            print(f"  ✓ AI summaries + predictions (mock — {why})")

    print(f"✓ Done. last_refreshed = {meta['last_refreshed']}")
    return meta


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Refresh the FIFA 2026 cache.")
    parser.add_argument("--with-ai", action="store_true", help="Regenerate Claude summaries/predictions.")
    parser.add_argument("--mock", action="store_true", help="Use bundled mock data (no network).")
    parser.add_argument("--force-squads", action="store_true", help="Ignore the squad TTL.")
    args = parser.parse_args(argv)
    run(with_ai=args.with_ai, use_mock=args.mock, force_squads=args.force_squads)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
