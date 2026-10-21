# Contexte de build attendu : racine du dépôt (voir infra/compose/docker-compose.yml).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY services/remediation/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# sops : seul binaire nécessaire à RotateSecretAction pour graver la rotation dans
# infra/secrets/jwt.enc.yaml (voir adapters/secret_rotation.py). Version et somme figées.
ARG SOPS_VERSION=3.13.3
ARG SOPS_SHA256=e5bec3346a873ae91d871550f3e698c1aad962aff462a080e40f25fde17fef6b
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -fsSLo /usr/local/bin/sops \
       "https://github.com/getsops/sops/releases/download/v${SOPS_VERSION}/sops-v${SOPS_VERSION}.linux.amd64" \
    && echo "${SOPS_SHA256}  /usr/local/bin/sops" | sha256sum -c - \
    && chmod +x /usr/local/bin/sops \
    && apt-get purge -y curl && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY services/remediation/app ./app

# Exécution sans privilèges : le moteur agit par la passerelle Docker restreinte, pas en root.
RUN useradd --no-create-home --shell /usr/sbin/nologin --uid 10002 remediation \
    && mkdir /blocklist \
    && chown -R remediation:remediation /app /blocklist
USER remediation

EXPOSE 8000

CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
