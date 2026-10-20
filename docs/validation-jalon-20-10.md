# Validation du jalon du mardi 20/10

Jalon : **socle déployable en une commande, microservices, observabilité, 1ers scripts d'attaque + dataset ML, EBIOS et NIS2/DORA rédigés. Le fil rouge bout en bout tourne.**
Chacun relit son périmètre, répond aux questions et coche. Les réponses sont reportées dans [`06-pilotage-arbitrages.md`](gouvernance/06-pilotage-arbitrages.md).
Les cases déjà cochées ont une preuve dans le dépôt ; les autres attendent la confirmation de la personne.

## 0. Reliquat du jalon du 19/10

Cases restées ouvertes dans [`validation-jalon-19-10.md`](validation-jalon-19-10.md) : à solder avant d'ouvrir le jalon du 20/10.

- [ ] Hugo : Questions 1 (WAF) et 3 (SOC) du 19/10. Réponse de fait : ModSecurity + OWASP CRS (arbitrage du 20/10, « à valider avec Hugo ») ; reste à trancher Loki/Grafana seuls ou Wazuh.
- [ ] Antoine : `PROBE_TOKEN` protège la sonde et le service privé de sauvegarde/restauration S4 (fait). Essai réel et automatique fait le 20/10 (détecteur d'intégrité, 5 passages sans intervention, voir `docs/procedures/s4-corruption-bdd.md`).
- [ ] François : RAG isolé (codé, ER6 EN COURS), horodatage de début d'attaque dans le flood (fait), Ollama sur un PC Linux dédié (décidé).
- [x] Kevin : transport détecteur → remédiation (HTTP direct sur `POST /incidents`, déjà en place et consigné le 19/10).
- [ ] Antoine : EBIOS ateliers 1 à 3 (échelle de gravité, valeurs métier, ER1 à ER6, sources de risque, SS1 à SS5, socle ANSSI).
- [ ] Tous : `ruff format` fonctionne sur chaque PC.
- [ ] Tous : hotspot `RESILIENCE-G<n>`, PC Hôte en `192.168.137.1`, PC Attaquant joint l'hôte et ne vise que lui.

## 1. Socle déployable en une commande — Hugo

- [x] Compose : base, migrations, API, auth, passerelle, WAF, moteur de remédiation, détecteur, observabilité (`infra/compose/`).
- [x] `mem_limit` posé sur les conteneurs du Compose.
- [ ] **Ansible** : `infra/ansible/site.yml`, rôles et playbooks sont vides (`.gitkeep`). À écrire : un playbook qui enchaîne `.env`, socle, observabilité, vérification. Sans lui, « une commande » n'est pas tenu.
- [ ] **Vault ou SOPS** : `infra/secrets/` est vide. Choisir l'un, y mettre `JWT_SECRET`, `PROBE_TOKEN`, mots de passe BDD ; brancher `RotateSecretAction`.
- [ ] Exposer front, Grafana et dashboard via le WAF sur `192.168.137.1` (aujourd'hui `127.0.0.1` seulement).
- [ ] Mesure de la RAM de la pile complète (`docker stats`) pour décider où tourne Ollama.

## 2. Microservices — Antoine

- [x] BDD (migrations 0001 et 0002), API métier (`/health`, `/transactions`, `/me/*`), auth (JWT), tests présents.
- [x] Correctif des deadlocks de virement (#19).
- [ ] `PROBE_TOKEN` protège la sonde et le service privé de sauvegarde/restauration S4 ; `RestoreDatabaseAction` restaure la dernière archive, redémarre l'API puis la reprise est vérifiée par une transaction. RPO configuré à 5 min ; essai de corruption et mesure réelle à faire (voir `services/db/README.md`).
- [x] Doc d'API à jour (`services/api/README.md`) avec les routes d'auth.

## 3. Front et dashboard — Gabriel

- [x] Front Pay-Now sur notre API (inscription, connexion, solde, virement, historique).
- [ ] **Arbitrage Grafana vs dashboard React à valider.** Le debrief et le sujet parlent d'un dashboard React ; le registre du 20/10 retient Grafana (« à valider avec Gabriel et le sujet »). Vérifier que le sujet accepte Grafana comme dashboard de supervision, sinon il reste un service à écrire.
- [ ] Parcourir `resilience-alpha.json` pendant un flood : avant / pendant / après lisibles, événements `incident.*` visibles.
- [x] NIS2/DORA : colonnes « Couverture » de `03-nis2-dora.md` remplies et périmètre non démontrable écrit (PR #27, propositions du 20/10 : relecture de Gabriel attendue).

## 4. Attaque et ML — François, Kevin

- [x] Flood authentifié `attack/flood_http.py` ; dataset ML (`ml/data/normal.csv`, `attack.csv`, `holdout.csv`) ; modèle entraîné.
- [x] Boucle de 5 démos : 5/5 reprises, RTO moyen 45 s, 0 % de faux positifs sur 120 mesures.
- [ ] Rejouer le flood **depuis le PC Attaquant** vers `192.168.137.1` (jusqu'ici en local).
- [ ] Script d'injection SQL (bonus, ER2) ; il ferait passer la ligne SQLi de la matrice de `À FAIRE` à `EN COURS`.
- [x] RAG : `services/rag-assistant/` codé (PR #30), Ollama sur un PC Linux dédié, modèle `llama3.1:8b` (≤ 8B). Reste à prouver ER6 (injection de prompt) et à brancher le dashboard si besoin.

## 5. EBIOS RM, ateliers 4 et 5 — Antoine

- [ ] Ateliers 1 à 3 validés (voir § 0). Les colonnes `À DÉFINIR` de `01-ebios-rm.md` sont remplies en propositions (PR #27) : validation d'Antoine attendue.
- [x] Atelier 4 (scénarios opérationnels) : SO1 flood, SO2 SQLi ; renvoyer vers les démos mesurées.
- [x] Atelier 5 (traitement du risque) : tableau Flood / SQLi / détournement du moteur / faux positif ML, preuves liées.
- [x] `02-pca-pra.md` : RTO provisoires posés (60 s paiement, base : RTO flood mesuré 33-48 s). RPO à définir avec la sauvegarde (S4).

## 6. Cohérence d'intégration — Kevin

- [x] Matrice de traçabilité, 1re version, avec les mesures du 20/10.
- [x] Mise à jour de `docs/architecture/architecture.md` avec le WAF, la détection de crash et le blocage par compte.
- [ ] Valider avec Hugo les arbitrages marqués « à valider » du 20/10 (passerelles Docker, WAF par compte).
- [x] README : retirer « à venir » sur le WAF une fois la section relue, lister l'écart Ansible/RAG.
- [x] Supprimer les dossiers parasites `ml/data;C` et `services/anomaly-detector;C`.

## 7. Critères de sortie du jalon

- [ ] Le fil rouge tourne de bout en bout **avec le PC Attaquant** : flood → détection ML → blocage → reprise → transaction de test.
- [ ] Un tiers lance le socle avec une commande (Ansible) et la doc.
- [ ] Les écarts restants (Ansible, Vault/SOPS, restauration BDD, SQLi) ont un responsable et une échéance mercredi.
