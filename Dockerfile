FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 POLYSOCIAL_DATA_DIR=/data
WORKDIR /app
RUN useradd --create-home --uid 10001 polysocial
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=polysocial:polysocial . .
USER polysocial
VOLUME ["/data"]
EXPOSE 5500
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5500/api/status', timeout=3)"
CMD ["python", "server.py", "--bind", "0.0.0.0", "--port", "5500"]
