"""Overview page: AI tournament narrative + group standings + live strip."""

from __future__ import annotations

import streamlit as st

from fifa import transform
from ui import components


def _standings_rows(rows: list) -> list[dict]:
    out = []
    for r in rows:
        allg = r.get("all", {})
        goals = allg.get("goals", {})
        out.append({
            "#": r.get("rank", ""),
            "Team": r.get("team", {}).get("name", ""),
            "P": allg.get("played", 0),
            "W": allg.get("win", 0),
            "D": allg.get("draw", 0),
            "L": allg.get("lose", 0),
            "GF": goals.get("for", 0),
            "GA": goals.get("against", 0),
            "GD": r.get("goalsDiff", 0),
            "Pts": r.get("points", 0),
            "Form": r.get("form") or "-",
        })
    return out


def render(standings, fixtures, summaries) -> None:
    st.subheader("Tournament overview")
    if summaries and summaries.get("tournament_overview"):
        model = summaries.get("model", "?")
        st.markdown(components.badge(f"AI · {model}", "#7c3aed"), unsafe_allow_html=True)
        st.write(summaries["tournament_overview"])
    else:
        st.info("No AI summary yet — run a refresh with AI enabled.")

    # Live strip
    buckets = transform.split_fixtures(fixtures)
    if buckets["live"]:
        st.markdown("##### 🔴 Live now")
        for fx in buckets["live"]:
            t = fx["teams"]; g = fx["goals"]
            st.markdown(
                f"**{t['home']['name']}** "
                f"<span class='fifa-score'>{g.get('home','-')} – {g.get('away','-')}</span> "
                f"**{t['away']['name']}** · {fx['fixture']['status']['long']}",
                unsafe_allow_html=True,
            )

    st.divider()
    st.subheader("Group standings")
    groups = transform.groups_from_standings(standings)
    if not groups:
        st.warning("No standings available yet.")
        return

    summary_by_group = {g["group"]: g["summary"] for g in (summaries or {}).get("groups", [])}
    # Two groups per row.
    for i in range(0, len(groups), 2):
        cols = st.columns(2)
        for col, grp in zip(cols, groups[i:i + 2]):
            with col:
                st.markdown(f"**{grp['group']}**")
                st.dataframe(_standings_rows(grp["rows"]), hide_index=True, width="stretch")
                note = summary_by_group.get(grp["group"])
                if note:
                    st.caption("🧠 " + note)
