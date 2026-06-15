"""Predictions page: Claude's tournament outlook + per-match calls."""

from __future__ import annotations

import streamlit as st

from ui import components


def _pick_card(label: str, pick: dict, color: str) -> str:
    name = (pick or {}).get("name", "—")
    rationale = (pick or {}).get("rationale", "")
    return (
        f'<div class="fifa-pick">'
        f'<div class="label">{label}</div>'
        f'<h3>{name}</h3>'
        f'<div style="opacity:.75;font-size:.9rem">{rationale}</div>'
        f'</div>'
    )


def render(predictions) -> None:
    if not predictions:
        st.info("No predictions yet — run a refresh with AI enabled.")
        return

    model = predictions.get("model", "?")
    st.markdown(
        components.badge(f"AI · {model}", "#7c3aed")
        + f" &nbsp;<span style='opacity:.6'>generated {components.time_ago(predictions.get('generated_at'))}</span>",
        unsafe_allow_html=True,
    )
    st.subheader("Tournament outlook")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(_pick_card("🏆 Champion", predictions.get("champion"), "#eab308"),
                    unsafe_allow_html=True)
    with c2:
        st.markdown(_pick_card("🐎 Dark horse", predictions.get("dark_horse"), "#0ea5e9"),
                    unsafe_allow_html=True)
    with c3:
        st.markdown(_pick_card("⚽ Golden boot", predictions.get("golden_boot"), "#f97316"),
                    unsafe_allow_html=True)

    finalists = predictions.get("finalists") or []
    if finalists:
        st.markdown(
            "##### Predicted finalists  \n"
            + " &nbsp;**vs**&nbsp; ".join(f"**{f}**" for f in finalists)
        )

    st.divider()
    st.subheader("Match predictions")
    matches = predictions.get("matches") or []
    if not matches:
        st.caption("No upcoming-match predictions available.")
        return
    rows = []
    for m in matches:
        conf = m.get("confidence")
        rows.append({
            "Match": f"{m.get('home','?')} vs {m.get('away','?')}",
            "Pick": m.get("predicted_winner", "?"),
            "Score": m.get("predicted_score", "?"),
            "Confidence": f"{round(conf * 100)}%" if isinstance(conf, (int, float)) else "—",
            "Why": m.get("rationale", ""),
        })
    st.dataframe(rows, hide_index=True, width="stretch")
