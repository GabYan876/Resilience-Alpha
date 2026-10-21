# Validation du jalon du lundi 19/10

Jalon : **architecture + EBIOS validés, dépôt + conventions, hotspot OK.**
Chacun relit son périmètre, répond aux questions et coche. Les réponses sont reportées dans [`06-pilotage-arbitrages.md`](gouvernance/06-pilotage-arbitrages.md).

## 1. Architecture — [`architecture/architecture.md`](architecture/architecture.md)

Tous : lire le schéma, le tableau des services et le pipeline de remédiation.

### Hugo (infra, WAF, réseaux)
- [x] Les 5 réseaux Docker (`resilience-net`, `db-internal`, `logs-query`, `control-internal`, `rag`) et l'exposition (seul le WAF publie un port, `127.0.0.1:8080` par défaut) sont réalisés dans `infra/compose/docker-compose.yml` : chaque service n'a que les réseaux dont il a besoin (`postgres`/`db-recovery` → `db-internal` seul ou + `control-internal` ; `docker-proxy-ctl` → `control-internal` seul ; `rag-assistant` → `rag` seul). Vérifié le 21/10 (Kevin) directement dans le fichier Compose.
- [x] Le `docker-socket-proxy` n'expose que `restart` pour le moteur de remédiation.
- ~~**Question 1 — WAF** : ModSecurity ou Coraza ?~~ **Réponse (20/10, `06-pilotage-arbitrages.md`)** : ModSecurity + OWASP CRS (nginx), blocage par **compte** (`sub` du JWT) en plus de l'IP — la passerelle Docker Desktop masque l'IP réelle. Revalidé le 21/10 sur 5 passages réels depuis le PC Attaquant.
- **Question 3 — SOC** : Loki/Grafana seuls, ou Wazuh si la RAM le permet ? **Tranchée le 21/10** : Loki/Grafana seuls, confirmé par Hugo (`06-pilotage-arbitrages.md`, ligne « Fonction SOC »).

### Antoine (API, auth, BDD)
- [x] Contrat de la sonde de transaction : `POST /transactions` avec `{from_account, to_account, amount}` (comptes de test fictifs), réponse 2xx si succès.
- [x] `GET /health` sur l'API métier.
- ~~Question : faut-il un jeton d'authentification pour la sonde ?~~ **Réponse (20/10)** : oui, `PROBE_TOKEN` protège la sonde et le service privé de sauvegarde/restauration S4.
- ~~Question : sauvegarde et restauration de la BDD (S4, `RestoreDatabaseAction`)~~ **Réponse (20/10)** : faisable et fait. Le service `db-recovery` restaure la dernière archive, un détecteur d'intégrité déclenche la reprise ; essai réel de 5 passages sans intervention (voir `procedures/s4-corruption-bdd.md`).

### Gabriel (front, vérification du dashboard Grafana)
- [x] Le dashboard affiche l'état avant / pendant / après depuis les événements JSON du moteur (`incident.detected`, `decision.made`, `action.executed`, `verification.completed`, `incident.resolved` / `incident.failed`).
- ~~Question : source des données du dashboard~~ **Réponse (20/10)** : le dashboard est **Grafana** (`resilience-alpha.json`), alimenté par Prometheus et Loki. Aucun dashboard React à écrire.

### François (RAG, red team)
- [ ] Le RAG est isolé (réseau `rag`, lecture seule, aucun accès privilégié) : codé et vérifié en conteneur, mais ER6 reste EN COURS (injection de prompt non prouvée, voir `04-matrice-tracabilite.md`).
- [x] Le script de flood journalise un **horodatage de début d'attaque** (sert au calcul du RTO).
- **Question** : Ollama sur un 3e PC si la RAM est insuffisante (< 32 Go) ? **Réponse** : oui, Ollama tourne sur un PC Linux dédié (procédure `ufw` de `docs/dev.md`).

### Kevin (tech lead)
- ~~Question 2 : transport détecteur → remédiation~~ **Réponse (20/10)** : HTTP direct sur `POST /incidents` (token), déjà en place et consigné le 19/10.

## 2. EBIOS RM, ateliers 1 à 3 — [`gouvernance/01-ebios-rm.md`](gouvernance/01-ebios-rm.md)

Responsable : Antoine. Contributeurs : Hugo (infra), Kevin (remédiation).

Ateliers 1 à 3 validés par le tech lead le 20/10 (voir `validation-jalon-20-10.md`, § 0 et § 5).

- [x] **Échelle de gravité** à 4 niveaux (1 Mineure, 2 Significative, 3 Grave, 4 Critique) et ses définitions.
- [x] **Valeurs métier** : criticité de chacune (colonne « Critique ? »).
- [x] **Événements redoutés** ER1 à ER6 : gravité de chacun et coût d'arrêt retenu pour ER1.
- [x] **Sources de risque** : l'initié malveillant ou négligent est-il retenu ?
- [x] **Scénarios stratégiques** SS1 à SS5 : gravité et mesures liées à l'écosystème.
- [x] **Socle de sécurité** : référentiel ANSSI retenu ; états et numéros de règles à remplir (peut attendre mardi).

## 3. Conventions — [`CONTRIBUTING.md`](../CONTRIBUTING.md)

Tous : lire `CONTRIBUTING.md` (5 min).

- [x] Branche par fonctionnalité, PR relue par Kevin, pas de push direct sur `main`.
- [x] Conventional Commits en français, **sans co-auteur**.
- [x] Aucun secret dans le dépôt, `.env` ignoré.
- [ ] Formatage `ruff format` : confirmer que ça fonctionne sur chaque PC (`black` est bloqué sur un PC par une stratégie de contrôle d'application).

## 4. Hotspot

- [ ] ~~Point d'accès mobile actif, nom `RESILIENCE-G<n>`.~~ Hotspot ou box indifféremment : arbitrage du 21/10 (`06-pilotage-arbitrages.md`), seul compte le réseau privé du binôme.
- [ ] ~~PC Hôte en `192.168.137.1`.~~ Adresse de l'hôte réglée par `WAF_BIND_HOST` dans `.env` (hotspot `192.168.137.1` ou IP de la box), même arbitrage.
- [x] PC Attaquant connecté au réseau privé du binôme et joint le PC Hôte. *(flood rejoué 5/5 depuis le PC Attaquant à travers le WAF le 21/10, SQLi rejouée depuis le PC Attaquant ; `validation-jalon-21-10.md` §0 et §2)*
- [ ] Le PC Attaquant ne vise que `192.168.137.1` (jamais le campus, un autre groupe ni Internet).
