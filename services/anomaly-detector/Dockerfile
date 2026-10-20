# Contexte de build attendu : racine du dépôt (voir infra/compose/docker-compose.yml).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY services/anomaly-detector/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/anomaly-detector/app ./app

# Exécution sans privilèges : le détecteur ne fait que lire Prometheus et signaler au moteur.
RUN useradd --no-create-home --shell /usr/sbin/nologin --uid 10003 detector \
    && chown -R detector:detector /app
USER detector

EXPOSE 8000

CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
