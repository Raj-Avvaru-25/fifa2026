"""Matches page: live, recent results, and upcoming fixtures with AI predictions."""

from __future__ import annotations

import streamlit as st

from fifa import transform
from ui import components


def _pred_index(predictions) -> dict:
    out = {}
    for m in (predictions or {}).get("matches", []):
        out[m.get("fixture_id")] = m
    return out


def _result_line(fx) -> None:
    t = fx["teams"]; g = fx["goals"]
    home, away = t["home"]["name"], t["away"]["name"]
    hg, ag = g.get("home"), g.get("away")
    # Bold the winner.
    if hg is not None and ag is not None:
        home_s = f"**{home}**" if hg > ag else home
        away_s = f"**{away}**" if ag > hg else away
    else:
        home_s, away_s = home, away
    st.markdown(
        f"{home_s} <span class='fifa-score'>{hg} – {ag}</span> {away_s}"
        f"<span style='opacity:.55'> · {fx['league'].get('round','')}</span>",
        unsafe_allow_html=True,
    )


def render(fixtures, predictions) -> None:
    buckets = transform.split_fixtures(fixtures)
    preds = _pred_index(predictions)

    if buckets["live"]:
        st.subheader("🔴 Live")
        for fx in buckets["live"]:
            _result_line(fx)
        st.divider()

    st.subheader("Upcoming")
    if not buckets["upcoming"]:
        st.caption("No upcoming fixtures scheduled.")
    for fx in buckets["upcoming"]:
        t = fx["teams"]
        fid = fx["fixture"]["id"]
        with st.container(border=True):
            st.markdown(
                f"**{t['home']['name']}** vs **{t['away']['name']}**  \n"
                f"<span style='opacity:.6'>{transform.fmt_kickoff(fx['fixture']['date'])}"
                f" · {fx['league'].get('round','')}</span>",
                unsafe_allow_html=True,
            )
            p = preds.get(fid)
            if p:
                conf = p.get("confidence")
                conf_txt = f" · {round(conf * 100)}% confident" if isinstance(conf, (int, float)) else ""
                st.markdown(
                    components.badge("AI prediction", "#7c3aed")
                    + f" &nbsp; **{p.get('predicted_winner','?')}** "
                    f"<span class='fifa-score'>({p.get('predicted_score','?')})</span>{conf_txt}",
                    unsafe_allow_html=True,
                )
                if p.get("rationale"):
                    st.caption(p["rationale"])

    st.divider()
    st.subheader("Recent results")
    if not buckets["finished"]:
        st.caption("No completed matches yet.")
    for fx in buckets["finished"][:20]:
        _result_line(fx)
