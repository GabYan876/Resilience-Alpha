# Environnement d'exécution Ansible de RESILIENCE-ALPHA.
# Image CLIENT : pas de démon Docker embarqué.
# Pour un build strictement reproductible, épingler l'image par digest.
FROM docker:27-cli

LABEL org.opencontainers.image.title="RESILIENCE-ALPHA Ansible Runner" \
      org.opencontainers.image.description="Playbooks Ansible et CLI Docker Compose pour le preflight et la vérification" \
      org.opencontainers.image.version="1.0.0"

RUN apk add --no-cache \
        ansible \
        bash \
        ca-certificates \
        curl \
        jq \
    && ansible-playbook --version \
    && docker compose version

COPY ansible.cfg inventory.ini site.yml /opt/resilience-ansible/
COPY playbooks/ /opt/resilience-ansible/playbooks/
COPY roles/ /opt/resilience-ansible/roles/

ENV ANSIBLE_CONFIG=/opt/resilience-ansible/ansible.cfg \
    ANSIBLE_LOCAL_TEMP=/tmp/ansible-local
WORKDIR /workspace

ENTRYPOINT ["ansible-playbook"]
CMD ["--version"]
