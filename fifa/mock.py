"""Mock World Cup 2026 data shaped exactly like API-Football responses.

This lets the whole app — UI, store, AI prompt-building — run with no API keys
at all. The shapes here are the contract every UI module reads against, so the
real fetcher and the mock fetcher are interchangeable.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

# (id, name, country, group) — a compact 8-team, 2-group stand-in for the real 48.
_TEAMS = [
    (2384, "USA", "USA", "A"),
    (1118, "Netherlands", "Netherlands", "A"),
    (13, "Senegal", "Senegal", "A"),
    (22, "Iran", "Iran", "A"),
    (26, "Argentina", "Argentina", "B"),
    (16, "Mexico", "Mexico", "B"),
    (12, "Japan", "Japan", "B"),
    (3, "Croatia", "Croatia", "B"),
]

_FLAG = "https://media.api-sports.io/flags/{0}.svg"

# Per-team standings line: played, win, draw, lose, gf, ga, form.
_TABLE = {
    "Netherlands": (2, 2, 0, 0, 5, 1, "WW"),
    "USA": (2, 1, 0, 1, 3, 3, "LW"),
    "Senegal": (2, 1, 0, 1, 2, 2, "WL"),
    "Iran": (2, 0, 0, 2, 1, 5, "LL"),
    "Argentina": (2, 2, 0, 0, 4, 0, "WW"),
    "Croatia": (2, 1, 1, 0, 3, 1, "WD"),
    "Japan": (2, 0, 1, 1, 2, 3, "DL"),
    "Mexico": (2, 0, 0, 2, 1, 6, "LL"),
}

# A handful of representative players per team (real squads return ~26).
_SQUAD_SAMPLES = {
    "USA": [("Matt Turner", "Goalkeeper", 1), ("Sergiño Dest", "Defender", 2),
            ("Tyler Adams", "Midfielder", 4), ("Weston McKennie", "Midfielder", 8),
            ("Christian Pulisic", "Attacker", 10), ("Folarin Balogun", "Attacker", 9)],
    "Netherlands": [("Bart Verbruggen", "Goalkeeper", 1), ("Virgil van Dijk", "Defender", 4),
                    ("Nathan Aké", "Defender", 5), ("Frenkie de Jong", "Midfielder", 21),
                    ("Cody Gakpo", "Attacker", 11), ("Memphis Depay", "Attacker", 10)],
    "Senegal": [("Édouard Mendy", "Goalkeeper", 16), ("Kalidou Koulibaly", "Defender", 3),
                ("Idrissa Gueye", "Midfielder", 5), ("Pape Sarr", "Midfielder", 17),
                ("Sadio Mané", "Attacker", 10), ("Nicolas Jackson", "Attacker", 9)],
    "Iran": [("Alireza Beiranvand", "Goalkeeper", 1), ("Sadegh Moharrami", "Defender", 2),
             ("Saeid Ezatolahi", "Midfielder", 6), ("Alireza Jahanbakhsh", "Midfielder", 7),
             ("Mehdi Taremi", "Attacker", 9), ("Sardar Azmoun", "Attacker", 20)],
    "Argentina": [("Emiliano Martínez", "Goalkeeper", 23), ("Cuti Romero", "Defender", 13),
                  ("Nicolás Otamendi", "Defender", 19), ("Enzo Fernández", "Midfielder", 24),
                  ("Lionel Messi", "Attacker", 10), ("Julián Álvarez", "Attacker", 9)],
    "Mexico": [("Guillermo Ochoa", "Goalkeeper", 13), ("César Montes", "Defender", 3),
               ("Edson Álvarez", "Midfielder", 4), ("Luis Chávez", "Midfielder", 14),
               ("Hirving Lozano", "Attacker", 22), ("Santiago Giménez", "Attacker", 9)],
    "Japan": [("Zion Suzuki", "Goalkeeper", 1), ("Ko Itakura", "Defender", 22),
              ("Wataru Endo", "Midfielder", 6), ("Hidemasa Morita", "Midfielder", 13),
              ("Kaoru Mitoma", "Attacker", 11), ("Takefusa Kubo", "Attacker", 20)],
    "Croatia": [("Dominik Livaković", "Goalkeeper", 1), ("Joško Gvardiol", "Defender", 20),
                ("Luka Modrić", "Midfielder", 10), ("Mateo Kovačić", "Midfielder", 8),
                ("Andrej Kramarić", "Attacker", 9), ("Ante Budimir", "Attacker", 17)],
}


def _by_name(name: str) -> tuple:
    for t in _TEAMS:
        if t[1] == name:
            return t
    raise KeyError(name)


def teams() -> list:
    out = []
    for tid, name, country, _ in _TEAMS:
        out.append({
            "team": {"id": tid, "name": name, "country": country, "logo": _FLAG.format(country[:2].lower())},
            "venue": {"name": f"{name} National Stadium", "city": country},
        })
    return out


def standings() -> list:
    groups: dict[str, list] = {"A": [], "B": []}
    for tid, name, _country, group in _TEAMS:
        played, win, draw, lose, gf, ga, form = _TABLE[name]
        groups[group].append({
            "rank": 0,  # filled after sorting
            "team": {"id": tid, "name": name, "logo": _FLAG.format(_country[:2].lower())},
            "points": win * 3 + draw,
            "goalsDiff": gf - ga,
            "group": f"Group {group}",
            "form": form,
            "all": {"played": played, "win": win, "draw": draw, "lose": lose,
                    "goals": {"for": gf, "against": ga}},
        })
    table = []
    for group in ("A", "B"):
        rows = sorted(groups[group], key=lambda r: (r["points"], r["goalsDiff"]), reverse=True)
        for i, row in enumerate(rows, start=1):
            row["rank"] = i
        table.append(rows)
    return [{"league": {"id": 1, "name": "World Cup", "season": 2026, "standings": table}}]


def fixtures() -> list:
    now = datetime.now(timezone.utc)
    played = [
        ("Netherlands", "Iran", 3, 0, "A"), ("USA", "Senegal", 2, 1, "A"),
        ("Argentina", "Mexico", 2, 0, "B"), ("Croatia", "Japan", 1, 1, "B"),
        ("Netherlands", "USA", 2, 1, "A"), ("Senegal", "Iran", 1, 1, "A"),
        ("Argentina", "Japan", 2, 0, "B"), ("Mexico", "Croatia", 0, 2, "B"),
    ]
    upcoming = [
        ("Netherlands", "Senegal", "A"), ("USA", "Iran", "A"),
        ("Argentina", "Croatia", "B"), ("Mexico", "Japan", "B"),
    ]
    out = []
    fid = 1001
    for i, (home, away, hg, ag, group) in enumerate(played):
        kickoff = now - timedelta(days=6 - i // 2, hours=2)
        out.append(_fixture(fid, home, away, group, kickoff, "FT", hg, ag))
        fid += 1
    for i, (home, away, group) in enumerate(upcoming):
        kickoff = now + timedelta(days=2 + i // 2, hours=3)
        out.append(_fixture(fid, home, away, group, kickoff, "NS", None, None))
        fid += 1
    return out


def _fixture(fid, home, away, group, kickoff, status, hg, ag):
    h, a = _by_name(home), _by_name(away)
    home_win = away_win = None
    if hg is not None:
        home_win = hg > ag
        away_win = ag > hg
    long_status = {"FT": "Match Finished", "NS": "Not Started", "LIVE": "In Play"}.get(status, status)
    return {
        "fixture": {
            "id": fid,
            "date": kickoff.isoformat(),
            "status": {"short": status, "long": long_status},
            "venue": {"name": f"{home} National Stadium", "city": h[2]},
        },
        "league": {"round": "Group Stage - " + ("1" if status == "FT" else "3"), "name": "World Cup"},
        "teams": {
            "home": {"id": h[0], "name": home, "logo": _FLAG.format(h[2][:2].lower()), "winner": home_win},
            "away": {"id": a[0], "name": away, "logo": _FLAG.format(a[2][:2].lower()), "winner": away_win},
        },
        "goals": {"home": hg, "away": ag},
    }


def squad(team_id: int) -> list:
    name = next((n for tid, n, _, _ in _TEAMS if tid == team_id), None)
    if name is None:
        return []
    players = []
    for pid, (pname, position, number) in enumerate(_SQUAD_SAMPLES[name], start=1):
        players.append({
            "id": team_id * 100 + pid,
            "name": pname,
            "age": 26,
            "number": number,
            "position": position,
            "photo": "",
        })
    return [{"team": {"id": team_id, "name": name}, "players": players}]


def all_team_ids() -> list:
    return [t[0] for t in _TEAMS]
