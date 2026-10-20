# Validation du jalon du lundi 19/10

Jalon : **architecture + EBIOS validés, dépôt + conventions, hotspot OK.**
Chacun relit son périmètre, répond aux questions et coche. Les réponses sont reportées dans [`06-pilotage-arbitrages.md`](gouvernance/06-pilotage-arbitrages.md).

## 1. Architecture — [`architecture/architecture.md`](architecture/architecture.md)

Tous : lire le schéma, le tableau des services et le pipeline de remédiation.

### Hugo (infra, WAF, réseaux)
- [ ] Les 5 réseaux Docker (public, app, obs, control, rag) et l'exposition (seul le WAF est publié) sont réalisables dans le Compose.
- [x] Le `docker-socket-proxy` n'expose que `restart` pour le moteur de remédiation.
- **Question 1 — WAF** : ModSecurity ou Coraza ? Quel mécanisme de blocage d'IP (liste dynamique, API restreinte) ? Le moteur appellera un port `IpBlocker`.
- **Question 3 — SOC** : Loki/Grafana seuls, ou Wazuh si la RAM le permet ? (PC Hôte : 16 Go, `mem_limit` partout.)

### Antoine (API, auth, BDD)
- [x] Contrat de la sonde de transaction : `POST /transactions` avec `{from_account, to_account, amount}` (comptes de test fictifs), réponse 2xx si succès.
- [x] `GET /health` sur l'API métier.
- **Question** : faut-il un jeton d'authentification pour la sonde ? (variable `PROBE_TOKEN`, un compte de test dédié).
- **Question** : sauvegarde et restauration de la BDD (scénario S4, `RestoreDatabaseAction`) : faisable cette semaine ? Quel mécanisme ?

### Gabriel (front, vérification du dashboard Grafana)
- [x] Le dashboard affiche l'état avant / pendant / après depuis les événements JSON du moteur (`incident.detected`, `decision.made`, `action.executed`, `verification.completed`, `incident.resolved` / `incident.failed`).
- ~~Question : source des données du dashboard~~ **Réponse (20/10)** : le dashboard est **Grafana** (`resilience-alpha.json`), alimenté par Prometheus et Loki. Aucun dashboard React à écrire.

### François (RAG, red team)
- [ ] Le RAG est isolé (réseau `rag`, lecture seule, aucun accès privilégié) : codé et vérifié en conteneur, mais ER6 reste EN COURS (injection de prompt non prouvée, voir `04-matrice-tracabilite.md`).
- [x] Le script de flood journalise un **horodatage de début d'attaque** (sert au calcul du RTO).
- **Question** : Ollama sur un 3e PC si la RAM est insuffisante (< 32 Go) ? **Réponse** : oui, Ollama tourne sur un PC Linux dédié (procédure `ufw` de `docs/dev.md`).

### Kevin (tech lead)
- **Question 2 — transport détecteur → remédiation** : HTTP direct sur `POST /incidents` (token) retenu pour mardi. D'accord ?

## 2. EBIOS RM, ateliers 1 à 3 — [`gouvernance/01-ebios-rm.md`](gouvernance/01-ebios-rm.md)

Responsable : Antoine. Contributeurs : Hugo (infra), Kevin (remédiation).

- [ ] **Échelle de gravité** à 4 niveaux (1 Mineure, 2 Significative, 3 Grave, 4 Critique) et ses définitions.
- [ ] **Valeurs métier** : criticité de chacune (colonne « Critique ? »).
- [ ] **Événements redoutés** ER1 à ER6 : gravité de chacun et coût d'arrêt retenu pour ER1.
- [ ] **Sources de risque** : l'initié malveillant ou négligent est-il retenu ?
- [ ] **Scénarios stratégiques** SS1 à SS5 : gravité et mesures liées à l'écosystème.
- [ ] **Socle de sécurité** : référentiel ANSSI retenu ; états et numéros de règles à remplir (peut attendre mardi).

## 3. Conventions — [`CONTRIBUTING.md`](../CONTRIBUTING.md)

Tous : lire `CONTRIBUTING.md` (5 min).

- [x] Branche par fonctionnalité, PR relue par Kevin, pas de push direct sur `main`.
- [x] Conventional Commits en français, **sans co-auteur**.
- [x] Aucun secret dans le dépôt, `.env` ignoré.
- [ ] Formatage `ruff format` : confirmer que ça fonctionne sur chaque PC (`black` est bloqué sur un PC par une stratégie de contrôle d'application).

## 4. Hotspot

- [ ] Point d'accès mobile actif, nom `RESILIENCE-G<n>`.
- [ ] PC Hôte en `192.168.137.1`.
- [ ] PC Attaquant connecté au hotspot et joint le PC Hôte.
- [ ] Le PC Attaquant ne vise que `192.168.137.1` (jamais le campus, un autre groupe ni Internet).
