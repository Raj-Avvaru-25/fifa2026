"""FIFA World Cup 2026 live dashboard.

A small, quota-aware pipeline that pulls World Cup 2026 stats from API-Football
every 6 hours into a JSON cache, layers Claude-written summaries and predictions
on top, and serves it all through a Streamlit app that always shows how fresh the
data is.
"""

__version__ = "0.1.0"
