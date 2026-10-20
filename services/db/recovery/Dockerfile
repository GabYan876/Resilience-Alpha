FROM postgres:16-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN apk add --no-cache python3 py3-pip \
    && python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

WORKDIR /app
COPY services/db/recovery/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY services/db/recovery/app ./app

RUN mkdir -p /backups \
    && chown -R postgres:postgres /app /backups
USER postgres

EXPOSE 8001
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8001"]
