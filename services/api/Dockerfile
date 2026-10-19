# Contexte de build attendu : racine du dépôt (voir infra/compose/docker-compose.yml).
# Python 3.12 et non 3.14 : les roues asyncpg/greenlet y sont stables.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY services/api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services/api/pyproject.toml ./pyproject.toml
COPY services/api/app ./app
# Migrations et scripts embarqués : reset_demo.sh les exécute dans ce conteneur,
# le seul qui a le droit de parler à PostgreSQL.
COPY services/db ./db
COPY scripts ./scripts

# Exécution sans privilèges : une RCE via l'API ne doit pas donner root.
RUN useradd --no-create-home --shell /usr/sbin/nologin --uid 10001 apiuser \
    && chown -R apiuser:apiuser /app
USER apiuser

EXPOSE 8000

CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
