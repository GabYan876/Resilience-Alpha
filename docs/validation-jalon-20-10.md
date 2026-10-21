# Validation du jalon du mardi 20/10

Jalon : **socle déployable en une commande, microservices, observabilité, 1ers scripts d'attaque + dataset ML, EBIOS et NIS2/DORA rédigés. Le fil rouge bout en bout tourne.**
Chacun relit son périmètre, répond aux questions et coche. Les réponses sont reportées dans [`06-pilotage-arbitrages.md`](gouvernance/06-pilotage-arbitrages.md).
Les cases déjà cochées ont une preuve dans le dépôt ; les autres attendent la confirmation de la personne.

## 0. Reliquat du jalon du 19/10

Cases restées ouvertes dans [`validation-jalon-19-10.md`](validation-jalon-19-10.md) : à solder avant d'ouvrir le jalon du 20/10.

- [x] Hugo : Questions 1 (WAF) et 3 (SOC) du 19/10. Réponse de fait : ModSecurity + OWASP CRS (arbitrage du 20/10, « à valider avec Hugo ») ; SOC tranché le 21/10 : Loki/Grafana seuls (`06-pilotage-arbitrages.md`).
- [x] Antoine : `PROBE_TOKEN` protège la sonde et le service privé de sauvegarde/restauration S4 (fait). Essai réel et automatique fait le 20/10 (détecteur d'intégrité, 5 passages sans intervention, voir `docs/procedures/s4-corruption-bdd.md`).
- [ ] François : RAG isolé (codé, ER6 EN COURS), horodatage de début d'attaque dans le flood (fait), Ollama sur un PC Linux dédié (décidé).
- [x] Kevin : transport détecteur → remédiation (HTTP direct sur `POST /incidents`, déjà en place et consigné le 19/10).
- [x] Antoine : EBIOS ateliers 1 à 3 (échelle de gravité, valeurs métier, ER1 à ER6, sources de risque, SS1 à SS5, socle ANSSI).
- [ ] Tous : `ruff format` fonctionne sur chaque PC.
- [ ] Tous : réseau privé du binôme (hotspot ou box, arbitrage du 21/10) ; PC Attaquant joint l'hôte (prouvé le 21/10 : flood et SQLi depuis le PC Attaquant) ; reste la confirmation « ne vise que lui » et `ruff format` sur chaque PC (`validation-jalon-21-10.md` §8).

## 1. Socle déployable en une commande — Hugo

- [x] Compose : base, migrations, API, auth, passerelle, WAF, moteur de remédiation, détecteur, observabilité (`infra/compose/`).
- [x] `mem_limit` posé sur les conteneurs du Compose.
- [ ] **Ansible** : `infra/ansible/site.yml`, rôles et playbooks sont vides (`.gitkeep`). À écrire : un playbook qui enchaîne `.env`, socle, observabilité, vérification. Sans lui, « une commande » n'est pas tenu.
- [x] **Vault ou SOPS** : tranché SOPS + age le 21/10 ; `infra/secrets/app.enc.yaml` et `jwt.enc.yaml`, `RotateSecretAction` branchée sur `SopsSecretRotator` (`06-pilotage-arbitrages.md`).
- [x] Exposer front, Grafana et dashboard via le WAF (`/grafana`, port 3000 dépublié, `WAF_BIND_HOST`) : fait et vérifié depuis un second PC le 21/10.
- [x] Mesure de la RAM de la pile complète (`docker stats`) : 885 Mo au repos, 990 Mo en pic sous flood le 21/10 (`validation-jalon-21-10.md`).

## 2. Microservices — Antoine

- [x] BDD (migrations 0001 et 0002), API métier (`/health`, `/transactions`, `/me/*`), auth (JWT), tests présents.
- [x] Correctif des deadlocks de virement (#19).
- [x] `PROBE_TOKEN` protège la sonde et le service privé de sauvegarde/restauration S4 ; `RestoreDatabaseAction` restaure la dernière archive, redémarre l'API puis la reprise est vérifiée par une transaction. RPO configuré à 5 min ; essai de corruption et mesure réelle à faire (voir `services/db/README.md`).
- [x] Doc d'API à jour (`services/api/README.md`) avec les routes d'auth.

## 3. Front et dashboard — Gabriel

- [x] Front Pay-Now sur notre API (inscription, connexion, solde, virement, historique).
- [x] **Arbitrage Grafana vs dashboard React** : validé par Gabriel le 21/10 (`06-pilotage-arbitrages.md` ligne 41). Le debrief et le sujet parlent d'un dashboard React ; le registre du 20/10 retient Grafana (« à valider avec Gabriel et le sujet »). Vérifier que le sujet accepte Grafana comme dashboard de supervision, sinon il reste un service à écrire.
- [x] Parcourir `resilience-alpha.json` pendant un flood : avant / pendant / après lisibles, événements `incident.*` visibles.
- [x] NIS2/DORA : colonnes « Couverture » de `03-nis2-dora.md` remplies et périmètre non démontrable écrit (PR #27, propositions du 20/10 : relecture de Gabriel attendue).

## 4. Attaque et ML — François, Kevin

- [x] Flood authentifié `attack/flood_http.py` ; dataset ML (`ml/data/normal.csv`, `attack.csv`, `holdout.csv`) ; modèle entraîné.
- [x] Boucle de 5 démos : 5/5 reprises, RTO moyen 45 s, 0 % de faux positifs sur 120 mesures.
- [x] Rejouer le flood **depuis le PC Attaquant** vers le PC Hôte : 5 passages le 21/10 (`02-pca-pra.md` §7).
- [x] Script d'injection SQL (ER2) : `attack/sqli_injection.py`, 12/12 charges bloquées par le WAF, rejoué depuis le PC Attaquant ; ligne SQLi de la matrice `PROUVÉ`.
- [x] RAG : `services/rag-assistant/` codé (PR #30), Ollama sur un PC Linux dédié, modèle `llama3.1:8b` (≤ 8B). Reste à prouver ER6 (injection de prompt) et à brancher le dashboard si besoin.

## 5. EBIOS RM, ateliers 4 et 5 — Antoine

- [x] Ateliers 1 à 3 validés (voir § 0). Les colonnes `À DÉFINIR` de `01-ebios-rm.md` sont remplies en propositions (PR #27) : validés par Kevin (tech lead) le 20/10.
- [x] Atelier 4 (scénarios opérationnels) : SO1 flood, SO2 SQLi ; renvoyer vers les démos mesurées.
- [x] Atelier 5 (traitement du risque) : tableau Flood / SQLi / détournement du moteur / faux positif ML, preuves liées.
- [x] `02-pca-pra.md` : RTO provisoires posés (60 s paiement, base : RTO flood mesuré 33-48 s). RPO à définir avec la sauvegarde (S4).

## 6. Cohérence d'intégration — Kevin

- [x] Matrice de traçabilité, 1re version, avec les mesures du 20/10.
- [x] Mise à jour de `docs/architecture/architecture.md` avec le WAF, la détection de crash et le blocage par compte.
- [x] Valider avec Hugo les arbitrages marqués « à valider » du 20/10 (passerelles Docker, WAF par compte) : validés le 21/10 sur 5 passages réels.
- [x] README : retirer « à venir » sur le WAF une fois la section relue, lister l'écart Ansible/RAG.
- [x] Supprimer les dossiers parasites `ml/data;C` et `services/anomaly-detector;C`.

## 7. Critères de sortie du jalon

- [x] Le fil rouge tourne de bout en bout **avec le PC Attaquant** : flood → détection ML → blocage → reprise → transaction de test.
- [ ] Un tiers lance le socle avec une commande (Ansible) et la doc.
- [x] Les écarts restants ont un responsable et une échéance : Vault/SOPS, restauration BDD et SQLi sont faits, il reste Ansible et le reste du `validation-jalon-21-10.md` §8.
