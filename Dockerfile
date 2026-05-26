FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY stt_service ./stt_service
COPY voicebus ./voicebus
COPY agent_tts_v3 ./agent_tts_v3

RUN pip install --no-cache-dir ".[ml]"

RUN groupadd --gid 10001 sttservice && \
    useradd --create-home --uid 10001 --gid 10001 sttservice && \
    mkdir -p /data /models && \
    chown -R sttservice:sttservice /app /data /models

USER sttservice

EXPOSE 8000

VOLUME ["/data", "/models"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read()"

CMD ["stt", "serve"]
