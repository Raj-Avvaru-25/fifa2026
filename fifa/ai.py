"""Claude-written summaries and predictions.

Two structured artifacts are generated from the cached stats and written back to
the cache so the app never has to call Claude on page load:

  * ``ai/summaries.json``    — a tournament overview + a paragraph per group
  * ``ai/predictions.json``  — champion / finalists / dark horse / golden boot
                               plus a predicted winner & scoreline per upcoming match

Both use ``client.messages.parse()`` with Pydantic schemas so the output is
always valid, parseable JSON — no brittle text scraping.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List

import anthropic
from pydantic import BaseModel, Field

from fifa import config, store, transform


# --------------------------------------------------------------------------- #
# Structured output schemas
# --------------------------------------------------------------------------- #

class GroupSummary(BaseModel):
    group: str = Field(description="Group label, e.g. 'Group A'")
    summary: str = Field(description="2-3 sentence summary of the group's state")


class Summaries(BaseModel):
    tournament_overview: str = Field(description="3-4 sentence overview of the tournament so far")
    groups: List[GroupSummary]


class Pick(BaseModel):
    name: str = Field(description="Team or player name")
    rationale: str = Field(description="One sentence justification")


class MatchPrediction(BaseModel):
    fixture_id: int
    home: str
    away: str
    predicted_winner: str = Field(description="Home team, away team, or 'Draw'")
    predicted_score: str = Field(description="Scoreline like '2-1'")
    confidence: float = Field(description="Confidence from 0.0 to 1.0")
    rationale: str = Field(description="One sentence reason")


class Predictions(BaseModel):
    champion: Pick
    finalists: List[str] = Field(description="The two teams predicted to reach the final")
    dark_horse: Pick
    golden_boot: Pick = Field(description="Predicted top scorer (player)")
    matches: List[MatchPrediction]


# --------------------------------------------------------------------------- #
# Prompt context
# --------------------------------------------------------------------------- #

def _standings_text(standings) -> str:
    lines = []
    for grp in transform.groups_from_standings(standings):
        lines.append(grp["group"])
        for row in grp["rows"]:
            allg = row.get("all", {})
            goals = allg.get("goals", {})
            lines.append(
                "  {rank}. {name} — {pts} pts, "
                "{w}W {d}D {l}L, GF {gf} GA {ga}, form {form}".format(
                    rank=row.get("rank", "?"),
                    name=row.get("team", {}).get("name", "?"),
                    pts=row.get("points", 0),
                    w=allg.get("win", 0), d=allg.get("draw", 0), l=allg.get("lose", 0),
                    gf=goals.get("for", 0), ga=goals.get("against", 0),
                    form=row.get("form") or "-",
                )
            )
    return "\n".join(lines) if lines else "(no standings yet)"


def _results_text(fixtures, limit=12) -> str:
    finished = transform.split_fixtures(fixtures)["finished"][:limit]
    lines = []
    for fx in finished:
        teams = fx["teams"]; goals = fx["goals"]
        lines.append("  {h} {hg}-{ag} {a}".format(
            h=teams["home"]["name"], a=teams["away"]["name"],
            hg=goals.get("home"), ag=goals.get("away"),
        ))
    return "\n".join(lines) if lines else "(no results yet)"


def _upcoming_list(fixtures, limit=12) -> list:
    return transform.split_fixtures(fixtures)["upcoming"][:limit]


def _upcoming_text(upcoming) -> str:
    lines = []
    for fx in upcoming:
        teams = fx["teams"]
        lines.append("  [id {fid}] {h} vs {a} ({ko})".format(
            fid=fx["fixture"]["id"],
            h=teams["home"]["name"], a=teams["away"]["name"],
            ko=transform.fmt_kickoff(fx["fixture"]["date"]),
        ))
    return "\n".join(lines) if lines else "(no upcoming matches)"


def _build_context(standings, fixtures) -> str:
    return (
        f"{config.TOURNAMENT_NAME} — current state.\n\n"
        f"STANDINGS:\n{_standings_text(standings)}\n\n"
        f"RECENT RESULTS:\n{_results_text(fixtures)}\n\n"
        f"UPCOMING MATCHES:\n{_upcoming_text(_upcoming_list(fixtures))}\n"
    )


# --------------------------------------------------------------------------- #
# Generation
# --------------------------------------------------------------------------- #

_SYSTEM = (
    "You are a sharp, concise football analyst covering the FIFA World Cup 2026. "
    "Base every claim only on the standings, results, and fixtures provided. "
    "Be specific and confident but never invent stats that aren't in the data."
)


def generate(standings, fixtures, *, api_key: str | None = None, model: str | None = None) -> dict:
    """Generate summaries + predictions and write them to the cache.

    Returns ``{"summaries": ..., "predictions": ...}``.
    """
    key = api_key or config.get_anthropic_key()
    if not key:
        raise RuntimeError("No Anthropic API key. Set ANTHROPIC_API_KEY to generate AI content.")

    model = model or config.CLAUDE_MODEL
    client = anthropic.Anthropic(api_key=key)
    context = _build_context(standings, fixtures)
    now = datetime.now(timezone.utc).isoformat()

    # 1) Summaries -----------------------------------------------------------
    summ_resp = client.messages.parse(
        model=model,
        max_tokens=config.CLAUDE_MAX_TOKENS,
        system=_SYSTEM,
        messages=[{
            "role": "user",
            "content": context + "\nWrite a tournament overview and a short summary for each group.",
        }],
        output_format=Summaries,
    )
    summaries = summ_resp.parsed_output.model_dump()
    summaries.update({"generated_at": now, "model": model})
    store.write_ai("summaries", summaries)

    # 2) Predictions ---------------------------------------------------------
    upcoming = _upcoming_list(fixtures)
    pred_resp = client.messages.parse(
        model=model,
        max_tokens=config.CLAUDE_MAX_TOKENS,
        system=_SYSTEM,
        messages=[{
            "role": "user",
            "content": (
                context
                + "\nPredict the tournament outcome (champion, the two finalists, a dark horse, "
                "and the golden boot winner). Then, for EACH upcoming match listed above, predict "
                "the winner, a plausible scoreline, and your confidence (0-1). Use the exact "
                "fixture id shown in brackets for each match."
            ),
        }],
        output_format=Predictions,
    )
    predictions = pred_resp.parsed_output.model_dump()
    predictions.update({"generated_at": now, "model": model})
    store.write_ai("predictions", predictions)

    return {"summaries": summaries, "predictions": predictions}


def mock_ai(standings, fixtures) -> dict:
    """Deterministic stand-in for :func:`generate` when no Anthropic key is set."""
    now = datetime.now(timezone.utc).isoformat()
    groups = transform.groups_from_standings(standings)
    summaries = {
        "generated_at": now,
        "model": "mock",
        "tournament_overview": (
            "Through two rounds of group play the favourites are asserting themselves: "
            "Argentina and the Netherlands have maximum points, while several hosts and "
            "fancied sides already face must-win finales. The knockout picture is taking shape."
        ),
        "groups": [
            {"group": g["group"],
             "summary": "{leader} lead {grp} and are well placed to advance, while the "
                        "lower half still have it all to play for in the final round.".format(
                            leader=(g["rows"][0]["team"]["name"] if g["rows"] else "?"),
                            grp=g["group"])}
            for g in groups
        ],
    }
    store.write_ai("summaries", summaries)

    upcoming = _upcoming_list(fixtures)
    matches = []
    for fx in upcoming:
        teams = fx["teams"]
        matches.append({
            "fixture_id": fx["fixture"]["id"],
            "home": teams["home"]["name"],
            "away": teams["away"]["name"],
            "predicted_winner": teams["home"]["name"],
            "predicted_score": "2-1",
            "confidence": 0.55,
            "rationale": "Home side carries better form into the decisive group fixture.",
        })
    predictions = {
        "generated_at": now,
        "model": "mock",
        "champion": {"name": "Argentina", "rationale": "Reigning champions with the best balance and form."},
        "finalists": ["Argentina", "Netherlands"],
        "dark_horse": {"name": "Croatia", "rationale": "Battle-tested core that always overperforms in knockouts."},
        "golden_boot": {"name": "Julián Álvarez", "rationale": "Leads a high-scoring side and takes the penalties."},
        "matches": matches,
    }
    store.write_ai("predictions", predictions)
    return {"summaries": summaries, "predictions": predictions}
