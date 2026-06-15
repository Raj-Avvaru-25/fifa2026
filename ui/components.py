"""Shared UI bits: global styles and the all-important freshness banner."""

from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from fifa import config

_CSS = """
<style>
:root { --fifa-green:#16a34a; --fifa-amber:#d97706; --fifa-red:#dc2626; }
.fifa-banner {
  display:flex; align-items:center; gap:.6rem; flex-wrap:wrap;
  padding:.7rem 1rem; border-radius:12px; margin-bottom:1rem;
  border:1px solid rgba(255,255,255,.10); font-size:.95rem;
}
.fifa-banner.fresh { background:rgba(22,163,74,.12);  border-color:rgba(22,163,74,.45); }
.fifa-banner.stale { background:rgba(217,119,6,.12);  border-color:rgba(217,119,6,.45); }
.fifa-banner.none  { background:rgba(220,38,38,.12);  border-color:rgba(220,38,38,.45); }
.fifa-dot { width:.7rem; height:.7rem; border-radius:50%; display:inline-block; }
.fifa-dot.fresh{background:var(--fifa-green);} .fifa-dot.stale{background:var(--fifa-amber);}
.fifa-dot.none{background:var(--fifa-red);}
.fifa-badge {
  display:inline-block; padding:.12rem .55rem; border-radius:999px;
  font-size:.72rem; font-weight:600; letter-spacing:.03em; text-transform:uppercase;
  border:1px solid rgba(255,255,255,.18);
}
.fifa-pick { padding:1rem 1.1rem; border-radius:14px; border:1px solid rgba(255,255,255,.10);
  background:rgba(255,255,255,.03); height:100%; }
.fifa-pick h3 { margin:.1rem 0 .3rem 0; font-size:1.25rem; }
.fifa-pick .label { font-size:.72rem; letter-spacing:.06em; text-transform:uppercase; opacity:.6; }
.fifa-score { font-variant-numeric:tabular-nums; font-weight:700; }
</style>
"""


def inject_styles() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def _parse(iso: str | None):
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None


def time_ago(iso: str | None) -> str:
    dt = _parse(iso)
    if dt is None:
        return "never"
    delta = datetime.now(timezone.utc) - dt
    secs = int(delta.total_seconds())
    if secs < 60:
        return "just now"
    mins = secs // 60
    if mins < 60:
        return f"{mins}m ago"
    hours = mins // 60
    if hours < 24:
        return f"{hours}h {mins % 60}m ago"
    days = hours // 24
    return f"{days}d {hours % 24}h ago"


def freshness(meta: dict) -> tuple[str, str]:
    """Return (state, human_label) where state ∈ {fresh, stale, none}."""
    iso = meta.get("last_refreshed")
    dt = _parse(iso)
    if dt is None:
        return "none", "No data yet — run a refresh."
    age_h = (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0
    state = "fresh" if age_h < config.REFRESH_INTERVAL_HOURS else "stale"
    return state, time_ago(iso)


def render_banner(meta: dict) -> None:
    state, label = freshness(meta)
    source = meta.get("source") or "—"
    quota = meta.get("quota") or {}
    remaining = quota.get("remaining_day")
    quota_txt = f" · API calls left today: {remaining}" if remaining not in (None, "") else ""
    note = {
        "fresh": "Data is current.",
        "stale": f"Data is older than {config.REFRESH_INTERVAL_HOURS}h — a refresh is due.",
        "none": "No cached data found.",
    }[state]
    st.markdown(
        f"""
        <div class="fifa-banner {state}">
          <span class="fifa-dot {state}"></span>
          <strong>Last refreshed: {label}</strong>
          <span style="opacity:.7">· source: {source}{quota_txt}</span>
          <span style="opacity:.7">· {note}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def badge(text: str, color: str = "#64748b") -> str:
    return f'<span class="fifa-badge" style="color:{color};border-color:{color}55">{text}</span>'
