# Validation du jalon du jeudi 22/10

Jalon : **chaos engineering, ≥ 5 démos sans intervention, clip chrono 60 s sans coupe, gel du code à 17h, remise avant 23h59.**
Chacun relit son périmètre, répond aux questions et coche. Les réponses sont reportées dans [`06-pilotage-arbitrages.md`](gouvernance/06-pilotage-arbitrages.md).
Les cases cochées ont une preuve dans le dépôt ; les autres attendent la confirmation de la personne.
Rappel : le vendredi est le jury (5 min de démo + 5 min de questions), **on ne code plus**.

## 0. Reliquat du jalon du 21/10

Cases restées ouvertes dans [`validation-jalon-21-10.md`](validation-jalon-21-10.md) §8 : à solder **avant** d'ouvrir le chaos.

- [ ] **`ruff format --check .` et `ruff check .` passent sur chaque poste** (Hugo, Antoine, Gabriel, François) après `git pull` ; confirmé sur le poste de Kevin le 21/10.
- [ ] **Réseau privé du binôme opérationnel entre PC Attaquant et PC Hôte**, avec `WAF_BIND_HOST` réglé sur l'IP réelle du PC Hôte. Constat du 21/10 soir : `.env` du PC de Kevin fixait `192.168.137.1` (hotspot) alors que seul `192.168.1.140` (box) existait ; le WAF refuse de démarrer si l'IP n'est pas présente. Vérifier l'IP avant chaque essai.
- [x] Doc d'API à jour (Antoine) : `services/api/README.md` couvre l'API métier et l'espace client ; `services/auth/README.md` documente les routes d'inscription et de connexion ainsi que le back-office.
- [ ] Relecture du README `infra/ansible/README.md` par un autre membre que Kevin (clone neuf essayé le 21/10 par Kevin seul).
- [ ] Trame `Pres.pptx`, NIS2/DORA relu et relié aux essais du 21/10 (Gabriel), plan du Dossier PDF (François) : échéances « jeudi matin » du §8 de la veille.

## 0bis. Consigne additionnelle 1 (reçue le 22/10)

Authentification du back-office renforcée : caméra USB sur le PC Hôte + reconnaissance de visage + habilitations + ESP8266 (LED bicolore). Analyse complète : [`consigne-additionnelle-1.md`](consigne-additionnelle-1.md). **Avant toute ligne de code**, à trancher ensemble :

- [ ] **Arbitrage calendrier (Kevin + équipe)** : gel de 17h maintenu ou décalé ? Demander à l'enseignant. Sans réponse, viser la tranche minimale démontrable (§8 de l'analyse).
- [ ] Interprétations validées (§2 de l'analyse) : « recommencer 1 fois puis bloqué 5 min, etc. », compteur d'échecs, blocage par identifiant, vérification 1:1.
- [x] Caméra USB sur le PC Hôte (Kevin) : UGREEN, détectée et utilisée le 22/10 (voir `repartition-reelle.md` §7, L2).
- [ ] ESP8266 + LED bicolore + résistances (Hugo), WiFi du point d'accès joignable par l'ESP8266.
- [x] Choix agent hôte natif (option A) confirmé, RAM de l'agent mesurée sur le PC Hôte (environ 198 Mo caméra allumée, 22/10).
- [ ] Consentement écrit des membres enrôlés ; aucun gabarit hors du PC Hôte (§5 de l'analyse).
- [ ] Lots L1 à L6 attribués (§7 de l'analyse) ; code sur branche, merge seulement si `pytest` et `demo_loop.py --runs 5` restent verts.

## 1. Infra et durcissement, Hugo

- [ ] Déploiement en une commande rejoué à froid sur le PC Hôte final (`Deploy.ps1 -RenderEnv` sur clone neuf, ou `Deploy.ps1` si `.env` existe), pile complète saine, transaction de test réussie.
- [ ] Ansible, Compose et `.env.example` figés : plus aucun changement d'infra après le gel du code.
- [ ] `mem_limit` sur tous les conteneurs et RAM de la pile mesurée pendant le chaos (référence du 21/10 : 885 Mo au repos, 990 Mo en pic sous flood).
- [ ] Seul le WAF publie un port ; aucune interface de gestion (Grafana, Prometheus, Loki, proxys Docker) exposée au-delà du WAF.
- [ ] Aucun secret dans l'arbre qui part au zip : `.env`, `infra/secrets/*-age-key.txt`, `.venv`, `ml/models/*.joblib` exclus du `-Code.zip` (les fichiers `*.enc.yaml` chiffrés sont les seuls autorisés).

## 2. Chaos et remédiation, Kevin

- [x] **≥ 5 démos consécutives sans intervention humaine** : `python scripts/demo_loop.py --runs 5` rejoué le 22/10 sur `main` (10:35), 5/5 reprises, `incident.resolved` et transaction de test réussie à chaque passage, RTO 28-35 s (moyenne 32 s). *Rejoué depuis le PC Hôte, ciblant le WAF (`192.168.137.1:8080`) ; un flood isolé lancé directement depuis le PC Attaquant a aussi été prouvé le même jour (1 passage, RTO 4,84 s, voir `docs/gouvernance/02-pca-pra.md` §7), à refaire en 5 passages depuis le PC Attaquant si le temps le permet avant le gel.
- [ ] Scénarios du chaos de François rejoués contre la pile : pour chacun, détection, action choisie par `DecisionPolicy`, vérification (API saine **et** transaction de test) et RTO consignés dans `docs/gouvernance/02-pca-pra.md` §7.
- [x] Disponibilité ≠ compromission : rejouées le 22/10. Flood → `block_subject` + `restart_service` (RTO 4,84 s, voir `02-pca-pra.md` §7). SQLi → bloqué en périmètre WAF (403, règle CRS), *pas* de rotation de secret automatique câblée sur ce signal (la rotation existe et est prouvée en déclenchement manuel, voir §7) : écart à assumer devant le jury, pas une démonstration de remédiation de compromission de bout en bout.
- [x] Faux positifs ML re-mesurés après le chaos (22/10, trafic de fond actif pendant la collecte) : `app.cli evaluate` sur 60 mesures inédites (`ml/data/holdout_22_10.csv`) → **0 jugée anormale, 0 fausse alerte** après 3 confirmations ; jeu d'attaque existant (16 mesures) → 75 % jugées anormales, alerte à la mesure 5.
- [x] Écarts honnêtes consignés dans « Limites connues » du README (22/10) : investigation manuelle de compromission non développée, `block_ip` inopérant sous Docker Desktop (arbitrage du 20/10), détecteur de compromission non automatique, consigne additionnelle 1 partielle, blocklist WAF non réinitialisée entre essais hors `reset_demo.sh`.
- [ ] **Gel du code à 17h** : plus aucun commit fonctionnel sur `main` après l'heure ; seuls les ajustements de rendu (docs, zip) restent permis.

## 3. Restauration et backend, Antoine

- [x] S4 (corruption BDD) rejoué automatiquement le 22/10 dans une pile S4 locale jetable isolée : 1/1 reprise, RTO 6,38 s de `Tc` à `incident.resolved` (détection 4,83 s, remédiation 1,55 s), RPO 108,78 s ; API saine et transaction de sonde réussie. Détails, horodatages et limites du périmètre dans [`s4-corruption-bdd.md`](procedures/s4-corruption-bdd.md) et [`02-pca-pra.md`](gouvernance/02-pca-pra.md) §7.
- [x] Restauration à froid rejouée en fin de chaos : pile complète isolée arrêtée puis relancée en une commande, transaction réussie ; volumes PostgreSQL/sauvegardes conservés. Preuve et chronométrages (non assimilés à un RTO) dans [`02-pca-pra.md`](gouvernance/02-pca-pra.md) §7 et [`restauration-a-froid.md`](procedures/restauration-a-froid.md).
- [x] EBIOS RM et PCA/PRA mis à jour avec les mesures réelles du chaos ; matrice de traçabilité sans ligne `PROUVÉ` sans preuve référencée (ER4 rétrogradé à `EN COURS`, S1 corrigé en `block_subject`).
- [x] Doc d'API à jour (voir §0) ; tests `pytest` verts avant le gel : API (58), auth (64) et remediation (80). Commandes et résultats détaillés dans la PR.

## 4. Front, dashboard, rendus, Gabriel

- [ ] **Clip chrono 60 s sans coupe** : scénario écrit, prise finale tournée, fichier `Workshop2026-M2-G<n>-VidChrono.mp4` ≤ 60 s. Le clip montre le service **avant / pendant / après** l'incident dans Grafana (disponibilité, latence, requêtes bloquées, événements `incident.*`).
- [ ] Dashboard Grafana vérifié pendant le chaos : lisible sur les trois temps.
- [ ] NIS2/DORA relu et relié aux essais réels (chaos du 22/10 inclus).
- [ ] `Pres.pptx` et pitch prêts pour le jury (5 min de démo + 5 min de questions).

## 5. Attaque et RAG, François

- [x] **Scénario de chaos écrit** (liste des pannes, ordre, critères de reprise) et rejoué ; toute attaque ne vise que le PC Hôte (garde-fous `ALLOWED_HOSTS`, jamais le campus, un autre groupe ni Internet). Scénario : [`docs/procedures/chaos-engineering.md`](procedures/chaos-engineering.md) (S1 flood auto, S2 SQLi + déclenchement manuel `compromise`, S4 corruption BDD). Rejeu 22/10 depuis le PC Attaquant à travers le WAF consigné dans [`02-pca-pra.md`](gouvernance/02-pca-pra.md) §7 : S1 flood RTO 4,84 s, S2 SQLi 6/6 bloquées (403) ; S4 non rejoué le 22/10 (derniers passages le 21/10, voir §7). Les attaques S1 et S2 viennent du PC Attaquant ; `demo_loop.py` est lancé depuis le PC Hôte. `demo_loop.py --runs 5` rejoué après merge : 5/5, RTO moyen 32 s, max 36 s (consigné dans [`repartition-reelle.md`](repartition-reelle.md)).
- [x] RAG : ER6 prouvé sur plusieurs scénarios d'injection de prompt (banc [`attack/rag_prompt_injection/`](../attack/rag_prompt_injection/) : 6 scénarios, 10 questions, 2 passages, `temperature=0`). Modèle de démo `llama3.1:8b` (≤ 8B) : 9/10 repoussées, cède sur l'injection conditionnelle ciblée (06) ; `llama3.2:3b` 5/10. Ollama sur le PC Linux dédié (`192.168.137.157:11434`), conteneur en lecture seule avec les restrictions du Compose. Détail et risque résiduel dans [`04-matrice-tracabilite.md`](gouvernance/04-matrice-tracabilite.md) (ER6) et « Limites connues » du README.
- [ ] Dossier PDF (8–12 p.) assemblé : architecture, 5 piliers, essais réels avec chiffres, limites. Source Markdown : [`dossier.md`](dossier.md) ; reste l'export PDF et le contrôle du nombre de pages.
- [ ] `Workshop2026-M2-G<n>-Code.zip` : sources, infra, scripts d'attaque/ML, tests, doc d'API, README, **sans secret** (voir §1).

## 6. Cohérence d'intégration, Kevin

- [ ] `README.md`, `architecture.md` et matrice de traçabilité alignés avec la pile réellement déployée au gel.
- [ ] `gh pr list --state open` vide au gel ; toutes les branches de travail supprimées.
- [ ] Section « Limites connues » du README complétée (ML, périmètre NIS2/DORA démontrable, écarts avec un contexte industriel).
- [ ] Une revue finale de « chaque ligne du code est explicable par son auteur devant le jury » : chacun sait expliquer son périmètre, y compris le code généré par IA.

## 7. Critères de sortie du jalon

- [ ] ≥ 5 démos consécutives sans intervention humaine, preuve de reprise par transaction à chaque passage (§2).
- [ ] Au moins une attaque de disponibilité **et** une de compromission traitées automatiquement, avec RTO mesuré (§2).
- [ ] Clip 60 s sans coupe livré (§4).
- [ ] Code gelé à 17h, `main` stable, PR ouvertes = 0 (§2, §6).
- [ ] Remise complète avant **23h59** : `-Dossier.pdf`, `-Pres.pptx`, `-VidChrono.mp4`, `-Code.zip` sans secret.
- [ ] Consigne additionnelle 1 *(partiel au 22/10 : identifiant → caméra → mot de passe → blocage 5 min prouvés via le WAF ; LED et ESP8266 non faits, blocage non persistant)* : soit tranche minimale démontrée (identifiant → caméra → LED → mot de passe → blocage 5 min) avec preuve, soit écart consigné au §8 avec responsable. Aucun point « prouvé » sans essai réel sur le PC Hôte.

## 8. Écarts restants pour le vendredi

À remplir en fin de journée du 22/10, après le chaos : tout ce qui reste ouvert doit figurer ici avec un responsable. Le vendredi est réservé au jury, donc **rien de neuf ne sera développé** ; ces écarts sont à présenter comme limites assumées, pas à corriger.

| Écart | Responsable | Pourquoi c'est assumé |
|---|---|---|
| Consigne additionnelle 1 : parties non livrées (reconnaissance de visage, habilitations, ESP8266) | À fixer après l'arbitrage du §0bis | Reçue le jour du chaos ; spécifiée dans `consigne-additionnelle-1.md` |
| *(autres écarts à compléter après le chaos)* | | |
