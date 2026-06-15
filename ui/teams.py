"""Teams page: pick a nation, see its current squad."""

from __future__ import annotations

import streamlit as st

from fifa import store, transform
from ui import components

_POSITION_ORDER = ["Goalkeeper", "Defender", "Midfielder", "Attacker"]


def render(teams, meta) -> None:
    index = transform.team_index(teams)
    if not index:
        st.warning("No teams cached yet — run a refresh.")
        return

    names = sorted(index.values(), key=lambda t: t.get("name", ""))
    label_to_id = {t["name"]: t["id"] for t in names}
    choice = st.selectbox("Team", list(label_to_id.keys()))
    team_id = label_to_id[choice]

    refreshed = meta.get("squads_refreshed", {}).get(str(team_id))
    st.caption(f"Squad last updated: {components.time_ago(refreshed)}")

    squad_doc = store.read_squad(team_id)
    squad = transform.squad_players(squad_doc)
    players = squad["players"]
    if not players:
        st.info("This squad hasn't been pulled yet. Squads refresh on a rotating schedule — "
                "trigger a refresh or check back after the next cycle.")
        return

    st.subheader(f"{choice} — {len(players)} players")

    def _pos_rank(p):
        pos = p.get("position") or ""
        return _POSITION_ORDER.index(pos) if pos in _POSITION_ORDER else len(_POSITION_ORDER)

    for position in _POSITION_ORDER:
        group = [p for p in players if (p.get("position") or "") == position]
        if not group:
            continue
        st.markdown(f"**{position}s**")
        rows = [{
            "#": p.get("number") or "",
            "Name": p.get("name", ""),
            "Age": p.get("age") or "",
        } for p in sorted(group, key=lambda x: (x.get("number") or 99))]
        st.dataframe(rows, hide_index=True, width="stretch")

    # Any players with an unrecognised/blank position.
    other = [p for p in players if (p.get("position") or "") not in _POSITION_ORDER]
    if other:
        st.markdown("**Other**")
        st.dataframe(
            [{"#": p.get("number") or "", "Name": p.get("name", ""),
              "Position": p.get("position") or "", "Age": p.get("age") or ""} for p in other],
            hide_index=True, width="stretch",
        )
