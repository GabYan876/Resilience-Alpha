# Contexte de build attendu : racine du dépôt (voir infra/compose/docker-compose.yml).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY services/auth/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/auth/app ./app

# Exécution sans privilèges : une RCE via l'auth ne doit pas donner root.
RUN useradd --no-create-home --shell /usr/sbin/nologin --uid 10002 authuser \
    && chown -R authuser:authuser /app
USER authuser

EXPOSE 8000

CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
