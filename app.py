"""FIFA World Cup 2026 — live dashboard.

Run with:  streamlit run app.py

The app only ever *reads* the JSON cache (so it's fast and never burns API quota
on page load). A scheduled job — GitHub Actions every 6 hours, or the "Refresh
now" button — is what pulls fresh stats and regenerates the Claude summaries and
predictions. Every page shows how fresh the data is.
"""

from __future__ import annotations

import os

import streamlit as st

from fifa import config, fetch, store
from ui import components, matches, overview, predictions, teams

st.set_page_config(
    page_title="FIFA World Cup 2026",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="expanded",
)
components.inject_styles()

# On Streamlit Community Cloud, secrets entered in the app dashboard are exposed
# via st.secrets. Bridge them into the environment so fifa.config (which reads
# os.environ, and is also used by the keyless GitHub Actions refresh) picks them up.
try:
    for _k in ("API_FOOTBALL_KEY", "ANTHROPIC_API_KEY", "CLAUDE_MODEL"):
        if _k in st.secrets and not os.environ.get(_k):
            os.environ[_k] = str(st.secrets[_k])
except Exception:  # no secrets.toml configured (e.g. local run) — that's fine
    pass


# --------------------------------------------------------------------------- #
# Data access (plain cache reads — cheap enough to do per render)
# --------------------------------------------------------------------------- #

def _load() -> dict:
    return {
        "meta": store.read_meta(),
        "teams": store.read_resource("teams") or [],
        "standings": store.read_resource("standings") or [],
        "fixtures": store.read_resource("fixtures") or [],
        "summaries": store.read_ai("summaries"),
        "predictions": store.read_ai("predictions"),
    }


def _sidebar() -> None:
    with st.sidebar:
        st.markdown(f"## 🏆 {config.TOURNAMENT_NAME}")
        st.caption("Latest stats, squads & AI predictions — refreshed every 6 hours.")

        if st.button("🔄 Refresh now", width="stretch", type="primary"):
            with st.spinner("Pulling latest stats and regenerating AI…"):
                fetch.run(with_ai=True)
            st.success("Refreshed.")
            st.rerun()

        st.divider()
        has_api = bool(config.get_api_football_key())
        has_anthropic = bool(config.get_anthropic_key())
        st.markdown("**Data sources**")
        st.caption(("✅ API-Football connected" if has_api
                    else "⚠️ No API-Football key — using mock data"))
        st.caption(("✅ Claude connected · " + config.CLAUDE_MODEL if has_anthropic
                    else "⚠️ No Anthropic key — using mock AI"))
        st.caption(f"Refresh cadence: every {config.REFRESH_INTERVAL_HOURS}h · "
                   f"squad TTL: {config.SQUAD_TTL_HOURS}h")


# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #

def page_overview() -> None:
    data = _load()
    st.title("Overview")
    components.render_banner(data["meta"])
    overview.render(data["standings"], data["fixtures"], data["summaries"])


def page_matches() -> None:
    data = _load()
    st.title("Matches")
    components.render_banner(data["meta"])
    matches.render(data["fixtures"], data["predictions"])


def page_squads() -> None:
    data = _load()
    st.title("Squads")
    components.render_banner(data["meta"])
    teams.render(data["teams"], data["meta"])


def page_predictions() -> None:
    data = _load()
    st.title("AI Predictions")
    components.render_banner(data["meta"])
    predictions.render(data["predictions"])


def main() -> None:
    _sidebar()
    nav = st.navigation([
        st.Page(page_overview, title="Overview", icon="📊", default=True),
        st.Page(page_matches, title="Matches", icon="⚽"),
        st.Page(page_squads, title="Squads", icon="👥"),
        st.Page(page_predictions, title="AI Predictions", icon="🔮"),
    ])
    nav.run()


if __name__ == "__main__":
    main()
