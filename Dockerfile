FROM python:3.12-slim

LABEL maintainer="popek1990"
WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py handler.py config.py szablony.py ./

RUN mkdir -p /usr/src/app/logs
# Usunieto USER appuser, aby uniknac problemow z uprawnieniami do pliku .env (PermissionError)
# Oba kontenery (webhook i dashboard) beda teraz dzialac jako root, co pozwala na wspoldzielenie i edycje .env.

EXPOSE 1990

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:1990/health')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "1990", "--timeout-graceful-shutdown", "10"]
