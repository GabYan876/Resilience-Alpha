# Ansible : déploiement en une commande (Windows + Docker Desktop)

Ce dossier ne remplace aucun Compose : il enchaîne contrôle du `.env`, modèle ML, socle,
observabilité et vérification. Aucun secret n'y est stocké.

## Contenu

| Fichier | Rôle |
|---|---|
| `Deploy.ps1` | Commande unique côté Windows : preflight (Ansible), modèle ML si absent, Compose socle puis observabilité, vérification (Ansible), transaction de test |
| `Dockerfile` | Image `resilience-ansible:1.0` : Ansible + client Docker/Compose, sans démon embarqué |
| `site.yml` → `playbooks/platform.yml` | Point d'entrée Ansible |
| `roles/preflight` | `.env` présent, les deux Compose valides (`config --quiet`) |
| `roles/application`, `roles/observability` | Déploiement Compose **sur hôte Linux uniquement** (`RESILIENCE_DIRECT_DEPLOY=true`, non testé) ; sous Windows, un simple message |
| `roles/verify` | Services de longue durée en `running` : `api`, `auth`, `gateway`, `waf`, `postgres`, `remediation`, `anomaly-detector`, puis `loki`, `alloy`, `prometheus`, `grafana`, `docker-proxy` |

## Pourquoi Compose est lancé depuis Windows

Avec Docker Desktop, les bind mounts sont interprétés du point de vue du moteur Docker. Un
`docker compose up` lancé dans le conteneur Ansible (dépôt monté en `/workspace`) demanderait au
démon de monter `/workspace`, chemin inexistant sur l'hôte. `Deploy.ps1` lance donc Compose
depuis PowerShell, comme le déploiement manuel du README racine.

## Prérequis

1. Docker Desktop en conteneurs Linux.
2. `.env` à la racine (non versionné), soit déjà présent, soit produit par `-RenderEnv` (clé age « ops »
   partagée hors dépôt dans `SOPS_AGE_KEY_FILE` ; `sops` et `bash` dans le PATH ; refuse d'écraser un
   `.env` existant).
3. PowerShell ouvert à la racine du dépôt.

## Commandes

```powershell
.\infra\ansible\Deploy.ps1 -CheckOnly              # construit l'image, contrôle .env et Compose, ne déploie rien
.\infra\ansible\Deploy.ps1                         # déploiement complet + vérification + transaction de test
.\infra\ansible\Deploy.ps1 -SkipBuild              # idem sans reconstruire l'image Ansible
.\infra\ansible\Deploy.ps1 -RenderEnv               # clone neuf : produit d'abord .env depuis SOPS
.\infra\ansible\Deploy.ps1 -VerifyOnly -SkipBuild  # revérifie sans redéployer
```

Si PowerShell bloque les scripts : `powershell -ExecutionPolicy Bypass -File .\infra\ansible\Deploy.ps1`
(portée limitée à ce processus).

Le script ne remet pas la base à zéro : pour rejouer la démo, `./scripts/reset_demo.sh`.

## Ce qui est prouvé

`running` ne prouve pas la reprise. En fin de script, la même sonde que `scripts/check_transaction.sh`
est jouée depuis le conteneur `remediation` : **API saine et transaction de test réussie**. Les
logs WAF dans Loki et l'alerte SOC restent à contrôler en essai de bout en bout.

## Sécurité

- Le contexte de build est `infra/ansible` seul : ni `.env` ni secret dans l'image.
- Conteneur éphémère (`--rm`), aucun port exposé.
- `/var/run/docker.sock` n'est monté que pour la vérification, **sans** `readonly` (un montage `ro`
  ne limite pas les appels API) : accès complet au démon, réservé à ce conteneur éphémère lancé à
  la main. Le moteur de remédiation, lui, passe par un docker-socket-proxy.
- Ni `down -v`, ni suppression de volume.
- BDD, Vault et interfaces de gestion restent sur des réseaux Docker internes ; seul le WAF est publié.

## Limites

- L'agent caméra du back-office (`host-agent/camera/run.ps1`, natif Windows) est lancé par `Deploy.ps1` seulement si son environnement est prêt (venv, `data/template.key`, `HOST_AGENT_TOKEN`) ; sinon avertissement et back-office fermé. L'installation et l'enrôlement restent manuels, voir `host-agent/camera/README.md`.
- Chemin Linux (`RESILIENCE_DIRECT_DEPLOY=true`) non testé.
- Image de base `docker:27-cli` non épinglée par digest.
- `-RenderEnv` demande la clé age et `sops` ; le `bash` du PATH doit être Git Bash (pas WSL).
