FROM python:3.12-slim

LABEL maintainer="fabston"
WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py handler.py config.py ./

RUN useradd -m appuser && mkdir -p /usr/src/app/logs && chown appuser:appuser /usr/src/app/logs
USER appuser

EXPOSE 1990

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:1990/health')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "1990", "--timeout-graceful-shutdown", "10"]
