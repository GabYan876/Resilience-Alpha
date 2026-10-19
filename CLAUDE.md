# CLAUDE.md — PROJECT RESILIENCE-ALPHA

Contexte et règles pour Claude Code sur ce dépôt. Sources : sujet du workshop (`docs/2627_Workshop_Bac+5 - Sujet PROJECT RESILIENCE-ALPHA 1.pdf`) et debrief d'équipe (`docs/Resilience-Alpha – Debrief et répartition.pdf`).

## Mission

Plateforme de paiement **fictive**, conteneurisée, qui subit une attaque lancée depuis un second PC, la détecte (ML), se répare **sans intervention humaine** (Zero-Touch Recovery) et prouve la reprise par une **nouvelle transaction réussie**. Le service doit être visible **avant / pendant / après** l'incident.

Un conteneur qui redémarre ne prouve rien : la remédiation n'est « réussie » que si l'API répond ET qu'une transaction de test passe.

## Les 5 piliers (tous obligatoires)

1. **Dev** : microservices (BDD, API métier, auth, front), moteur de remédiation, dashboard React + Tailwind.
2. **Infra** : Docker Compose, Ansible, Prometheus, Grafana, Loki (pas d'Elastic).
3. **IA/Data** : détection d'anomalies par ML (pas de règles codées en dur) branchée sur la remédiation ; assistant RAG Ollama + LangChain (modèle ≤ 8B paramètres).
4. **Cyber** : attaque réelle depuis le PC Attaquant, WAF (ModSecurity/Coraza), SIEM ou fonction SOC (Loki/Grafana, ou Wazuh si RAM), durcissement, Vault ou SOPS.
5. **Gouvernance** : EBIOS RM, PCA/PRA, NIS2/DORA reliés à l'architecture et aux essais réels.

## Stack retenue

- Services : **Python / FastAPI** partout (suggestion du debrief : simplifie ML + remédiation). Node.js ou Go uniquement si justifié.
- Front + dashboard : React + Tailwind CSS.
- Orchestration : Docker Compose ; automatisation : playbooks Ansible.
- Observabilité : Prometheus, Grafana, Loki (+ Promtail/Alloy).
- ML : scikit-learn (ex. IsolationForest) sur métriques/logs. RAG : Ollama + LangChain.
- Réseau : hotspot Windows `192.168.137.x`, PC Hôte = `192.168.137.1`.

## Architecture : principes SOLID (obligatoire)

Chaque service Python suit une architecture en couches de type hexagonal ; les dépendances pointent **vers le domaine**, jamais l'inverse.

```
services/<service>/
  app/
    domain/          # entités, règles métier, ports (interfaces abstraites) — aucune dépendance framework
    application/     # cas d'usage (services applicatifs), orchestrent domain via ports
    adapters/        # implémentations des ports : DB, HTTP, Docker, Prometheus, Loki, WAF...
    api/             # routes FastAPI, schémas Pydantic, injection de dépendances
    config.py        # lecture de la config/secrets (env, Vault) — seul endroit
    main.py          # composition root : câble les adaptateurs aux ports
  tests/
```

- **S — Responsabilité unique** : un module = une raison de changer. Détection, décision, action et vérification sont des composants séparés.
- **O — Ouvert/fermé** : on ajoute un nouveau type d'attaque / d'action / de détecteur en ajoutant une classe, sans modifier l'existante (registre de stratégies).
- **L — Substitution de Liskov** : toute implémentation d'un port est interchangeable (ex. `FakeDockerClient` en test, `DockerProxyClient` en prod) sans casser le contrat.
- **I — Ségrégation des interfaces** : ports petits et ciblés (`ContainerRestarter`, `IpBlocker`, `HealthChecker`, `TransactionProbe`) plutôt qu'une grosse interface « Admin ».
- **D — Inversion des dépendances** : le domaine/application dépendent d'abstractions (`typing.Protocol` / `ABC`) ; les adaptateurs sont injectés dans `main.py` (FastAPI `Depends`). Pas d'import direct de `docker`, `requests`, SQLAlchemy dans `domain/` ou `application/`.

### Moteur de remédiation — pipeline

`Detector (ML)` → `DecisionPolicy` → `RemediationAction[]` → `RecoveryVerifier`

- `Detector` : port ; implémentation ML (modèle chargé), alimenté par Prometheus/Loki.
- `DecisionPolicy` : choisit les actions selon le type d'incident (disponibilité ≠ compromission).
- `RemediationAction` : stratégies (`BlockIpAction`, `RestartServiceAction`, `ScaleServiceAction`, `RotateSecretAction`…).
- `RecoveryVerifier` : vérifie **API saine + transaction de test réussie** avant de déclarer l'incident clos.
- Chaque étape émet un événement structuré (JSON) consommé par le dashboard et Loki.

## Règles de sécurité (non négociables)

- **Moteur de remédiation = droits élevés** : jamais d'accès direct au `docker.sock`. Passer par un **docker-socket-proxy** (endpoints restreints) ou une API restreinte avec token ; aucune interface d'admin exposée aux autres composants.
- **Assistant RAG** : distinct de l'automate, **aucun accès privilégié**, lecture seule sur les documents indexés.
- **Secrets** : Vault ou SOPS uniquement. Aucun secret en clair dans le dépôt, les images, les logs ni le zip final. `.env` ignoré par Git ; fournir `.env.example`.
- **Ne jamais** envoyer de clé, secret, donnée perso réelle ou document confidentiel à une IA.
- **Exposition réseau minimale** : BDD, Vault, interfaces de gestion restent sur des réseaux Docker internes ; seul le WAF/front est publié.
- **Données 100 % fictives** : aucune donnée bancaire réelle.
- **Périmètre offensif** : attaques uniquement depuis le PC Attaquant vers le PC Hôte du consortium. Jamais le réseau du campus, d'un autre groupe, ni Internet.
- Distinguer **restauration de disponibilité** (flood → blocage IP + restart) et **correction de compromission** (SQLi/exfiltration → rotation de secrets, investigation) : actions différentes.

## Contraintes d'exploitation

- Déploiement reproductible en **une commande** (Compose + Ansible) ; doc suffisante pour qu'un tiers l'installe.
- RAM du PC Hôte limitée (16 Go) : définir `mem_limit` sur les conteneurs, éviter les services superflus ; Ollama sur un 3e PC si < 32 Go.
- La démo doit être **rejouable en boucle** (≥ 5 passages sans intervention) : prévoir un script de reset d'état.
- Tout code (y compris généré par IA) doit être **compris et explicable** par son auteur devant le jury.

## Conventions de travail

- Langue : documentation et commits en **français** ; identifiants de code en **anglais**.
- Python : typage complet, `ruff` + `black`, `pytest`. Un adaptateur = un fichier de tests ; le domaine est testé sans I/O.
- Commits : Conventional Commits (`feat:`, `fix:`, `docs:`, `infra:`, `test:`). Branche par fonctionnalité, PR relue par le tech lead.
- **Aucun co-auteur dans les commits** : ne jamais ajouter de ligne `Co-Authored-By` (ni autre trailer d'attribution) dans les messages de commit.
- Pas de logique métier dans les routes FastAPI ni dans les playbooks.
- Logs structurés JSON, avec `service`, `trace_id`, `event` — exploitables dans Loki/SIEM.
- Ne pas ajouter de dépendance ou de service lourd sans vérifier l'impact RAM.

## Répartition de l'équipe

| Qui | Rôle | Périmètre |
|---|---|---|
| Hugo | Infra + Cyber | Compose, Ansible, Prom/Grafana/Loki, WAF, SIEM, Vault/SOPS, durcissement, réseau |
| Kevin | Tech lead + remédiation | Architecture, moteur de remédiation, ML d'anomalies, intégration |
| Antoine | Dev backend | BDD, API métier, auth, script de vérif. transaction, tests, doc API ; EBIOS RM + PCA/PRA |
| Gabriel | Dev front | Front paiement, dashboard, Clip Chrono ; NIS2/DORA, pitch, Pres.pptx |
| François | IA RAG + Red Team | Assistant RAG, scripts d'attaque, chaos jeudi ; assemblage du Dossier PDF |

## Jalons

- **Lun 19/10** : architecture + EBIOS validés, dépôt + conventions, hotspot OK.
- **Mar** : socle déployable en une commande, microservices, observabilité, 1ers scripts d'attaque + dataset ML. **Le fil rouge bout en bout tourne dès mardi, même moche.**
- **Mer** : intégration WAF/logs/SIEM/ML/remédiation/dashboard, RAG, 1ers tests de restauration.
- **Jeu** : chaos engineering, ≥ 5 démos sans intervention, clip 60 s sans coupe, **gel du code 17h**, remise avant **23h59**.
- **Ven** : jury (5 min démo + 5 min questions). On ne code plus.

## Rendus attendus

Dossier `Workshop2026-M2-G<n>/` : `-Dossier.pdf` (8–12 p.), `-Pres.pptx`, `-VidChrono.mp4` (≤ 60 s, sans coupe), `-Code.zip` (sources, infra, scripts attaque/ML, tests, doc API, README, **sans secret**).

## Outillage Claude Code (équipe)

Configuration versionnée : `.claude/settings.json` (plugins, hooks) et `.mcp.json` (serveurs MCP), donc
même comportement sur les 5 postes. Liste des outils, installation et dépannage : [`docs/dev.md`](docs/dev.md).

Règles applicables à tout agent travaillant sur ce dépôt :

- **context7 (MCP) est un service externe** : les requêtes de documentation quittent le poste. Documentation
  publique de bibliothèques uniquement — jamais de secret, de donnée du projet ni de document de
  gouvernance. Application directe de « ne jamais envoyer de clé, secret, donnée perso réelle ou document
  confidentiel à une IA ».
- **Ne pas brancher le dépôt sur une passerelle LLM tierce** (`caveman-setup` et les compétences Caveman
  Cloud) : cela ferait sortir du code du projet hors du périmètre. Décision à prendre explicitement, hors
  de ce dépôt.
- **Réflexe avant d'ajouter du code** : est-ce nécessaire, est-ce que ça existe déjà dans le dépôt, est-ce
  que la bibliothèque standard le fait ? Même question pour chaque dépendance et chaque conteneur, à cause
  de la contrainte de 16 Go de RAM.
- Réglages personnels dans `.claude/settings.local.json` (ignoré par Git), jamais dans
  `.claude/settings.json` qui est partagé.

## Comment travailler avec Claude ici

- Respecter SOLID et la structure ci-dessus ; proposer l'abstraction avant l'implémentation concrète.
- Toujours se demander : « est-ce que ça améliore la preuve de reprise automatique ? » — c'est ce qui rapporte les points (axe remédiation = 5 pts, 0 si intervention humaine).
- Ne jamais écrire de secret réel dans un fichier ; utiliser des placeholders.
- Avant d'ajouter un composant : impact RAM, exposition réseau, droits requis.
