# Self-host image (Render / Railway / Fly / your own server).
# Streamlit Community Cloud does NOT use this — it builds from requirements.txt.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

# Most PaaS hosts inject $PORT; default to 8501 for local `docker run`.
ENV PORT=8501

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://localhost:{os.environ.get(\"PORT\",\"8501\")}/_stcore/health')" || exit 1

# Pass API_FOOTBALL_KEY / ANTHROPIC_API_KEY as runtime env vars (-e or host secrets).
CMD ["sh", "-c", "streamlit run app.py --server.port=${PORT} --server.address=0.0.0.0 --server.headless=true"]
