# Répartition réelle du travail (d'après l'historique Git)

Établie le 21/10/2026, puis mise à jour le 22/10 au soir à partir de `git log main` (179 commits hors fusions, 106 PR fusionnées) et des diffs par commit et par PR. Les sections 1 à 5 portent sur tout l'historique de `main` ; le §7 détaille la consigne additionnelle 1.
Elle montre ce qui a été **réellement livré**, pas ce que prévoyait le debrief.

## 1. Identités Git

| Personne | Identités Git / GitHub | Commits (hors merges) | PR fusionnées |
|---|---|---|---|
| Kevin | `MrSuricate` / `Kevin Ferraretto` (`MrSuricate2` sur GitHub) | 138 | 84 sur 106 |
| François | `francois` / `François Talaban` (`Francoistlb` sur GitHub) | 24 | 8 (#7, #8, #9, #30, #74, #82, #84, #96) |
| Antoine | `eosiswastaken` / `eosis` | 11 | 9 (#31, #36, #41, #42, #87, #90, #91, #92, #100) |
| Gabriel | `Gabriel` / `GabYan876` | 4 | 3 (#4, #21, #93) |
| Hugo | `Hugo Pécal` (`Hogupeck` sur GitHub) | 2 | 2 (#55, #62) |

- Les commits « Kevin Ferraretto » sont des fusions de PR (squash) faites par le tech lead ; les 8 commits de ce type comptés ci-dessus portent le contenu de ses propres PR. Les merges classiques ne comptent pas comme travail de contenu.

## 2. Tableau de répartition réelle

| Périmètre | Qui a livré | Preuves (PR / commits) | Volume approximatif |
|---|---|---|---|
| Architecture, conventions, CONTRIBUTING, hook pre-push | Kevin | #2, #5, #6 | ~1 500 lignes |
| Moteur de remédiation (pipeline, actions, politique, vérificateur, proxy Docker, `/metrics`, `/incidents`, watcher de crash, blocage par compte, rotation de secrets) | Kevin | #2, #11, #12, #14, #15, #23, #50 | ~2 300 lignes + 103 fichiers |
| Détecteur ML (IsolationForest), jeu de données, trafic de fond, mesure des faux positifs | Kevin | #17, #18, #33, #43 | ~2 000 lignes |
| Service d'authentification (JWT), passerelle Caddy | Kevin | `f493305`, `c15fbe8`, `ceb6fda` | ~930 lignes |
| WAF ModSecurity + CRS, dashboard SIEM, durcissement Caddy, logs d'audit WAF dans Loki, Grafana via le WAF | Kevin | #22, #51, #57 | ~1 200 lignes |
| Corrections de l'API métier (deadlock des virements, `/me`, `/metrics` auth, montant) | Kevin | #19, `28c5af5`, #53 | ~800 lignes |
| Boucle de démo rejouable, campagne de 5 passages de flood, auto-guérison d'Alloy | Kevin | #23, #37, #61 | ~500 lignes |
| Script d'attaque SQLi (ER2), flood (horodatage de début) | Kevin (SQLi, #45), François (flood, `0e44b59`) | #45 | ~350 lignes |
| Gouvernance : EBIOS RM ateliers 1 à 5, PCA/PRA, NIS2/DORA, AMDEC, matrice de traçabilité, registre des arbitrages | Kevin (rédaction), Antoine (retouches mineures) | #1, #3, #27, #28 | ~660 lignes, 55 fichiers |
| Documentation : README, architecture, jalons 19/10, 20/10, 21/10, procédures | Kevin (très majoritaire), François (architecture de l'observabilité, `docs/dev.md`) | #10, #13, #24 à #29, #32, #44 à #49, #52, #56, #58 à #60 | ~1 200 lignes |
| Socle PostgreSQL, migrations Alembic, API métier de transactions (domaine, cas d'usage, adaptateurs, tests) | François | #8 (`17e02e0`, `66d3735`, `29868be`, `8d978ac`) | ~2 900 lignes |
| Pile d'observabilité (Prometheus, Loki, Alloy, Grafana), dashboard provisionné, Compose du socle, scripts de démo | François | #9 (`6a1ffe1`, `f404434`, `0aae393`, `dd72429`) | ~1 700 lignes |
| Outillage Claude Code partagé (plugins, MCP context7, hook rtk) | François | #7 | ~240 lignes |
| Assistant RAG isolé (LangChain + Ollama) et doc de segmentation | François | #30 (`a13beef`, `045eb0c`) | ~1 270 lignes |
| Sauvegarde et restauration PostgreSQL (S4), sonde de transaction unifiée | Antoine | #31, #36 (`eff6f01`, `6fdacca`) | ~930 lignes |
| Mesures RTO/RPO de S4 sur pile complète, restauration à froid | Antoine | #41, #42 | docs |
| Détection automatique de la corruption de la base (S4 Zero-Touch) | Kevin | `3dbe268`, `9efce59`, `ba2c41b` | ~600 lignes |
| Front de paiement Pay-Now (interface d'origine adaptée au back) | Gabriel | #4, #21 | ~9 200 lignes ajoutées |
| Front : déplacement vers `frontend/`, session conservée, retrait des scripts tiers | Kevin | #16, `c1a7a4c`, `ac44f35` | ~400 lignes |
| Dashboard Grafana provisionné (création) puis validation | Création : François (#9). Validation : consignée par Kevin comme faite par Gabriel, sans trace Git de Gabriel | #9, #53, #54, #60 | docs |
| Alerting Grafana (règle d'alerte SQLi) | Hugo | #55 (`bcf2d08`) | 64 lignes |
| Documentation de la règle d'alerte, arbitrage SOC (Loki/Grafana seuls) | Kevin, arbitrage confirmé par Hugo | #56, `a038d6c` | docs |
| Secrets : `.sops.yaml`, `infra/secrets`, rotation | Kevin | #50 | ~130 lignes |
| Essais d'installation de la pile : lundi 19/10 sur WSL (échec, erreur réseau), mardi 20/10 sur Windows (échec), mercredi 21/10 réussi | Hugo | Déclaré par l'équipe, **aucune trace Git** (travail d'environnement) | n/a |
| Runner Ansible, commande de déploiement unique (`Deploy.ps1`), rôles preflight/application/observability/verify | Hugo | #62 (`f285f48`) | ~440 lignes, 14 fichiers |
| Option `-RenderEnv` de `Deploy.ps1` (rendu du `.env` depuis SOPS) | Kevin | #63 (`55b5cdb`) | ~35 lignes |
| Consigne 1 : machine à états d'authentification, agent caméra (YuNet + SFace), page `/admin`, panneaux Grafana `auth.*` | Kevin | #72, #75, #76, #77 | ~3 500 lignes |
| Consigne 1 : LED signée HMAC-SHA256 côté `auth` et firmware ESP8266 initial, puis correctif de signature par l'URL | Kevin | #94, #103 | ~600 lignes |
| Consigne 1 : habilitations `admin` / `operator`, console `/admin/console`, jeton de back-office distinct | Gabriel | #93 (`58e120f`) | ~1 200 lignes |
| Consigne 1 : firmware ESP32-DevKit (PlatformIO, requêtes signées), contrôle web des LED | Antoine | #87 (`d317668`, `aa0abf5`) | ~600 lignes |
| Consigne 1 : portage du firmware sur ESP32 (env `esp32dev`), ré-annonce d'IP toutes les 30 s, WiFi maintenu éveillé | François | #96, #98 (`fc586d8`, `2da5798`, `9f3c0b1`) | ~400 lignes |
| Banc d'injection de prompt ER6 multi-scénarios et scénario de chaos | François | #74 (`df54ac1`) | ~550 lignes |
| Rejeu S4 du chaos du 22/10, restauration à froid complète, EBIOS et PCA mis à jour après le chaos, documentation des API | Antoine | #90, #91, #92, #100 | docs |
| NIS2/DORA relu et relié aux essais réels du 20 au 22/10 | Gabriel | `1c2c9d6` | docs |
| Alertes Grafana flood (incident ML, 5xx API), filet de sécurité du blocage WAF (`GET /blocklist`) | Kevin | #99, #101 | ~300 lignes |
| Dossier technique : version initiale (François), complétée et corrigée (Kevin) | François, Kevin | #82, #84, #88, #102 | docs |
| Formatage `ruff` du dépôt, validation du jalon du 22/10 | Kevin | #65, #66 | 10 fichiers + 77 lignes de doc |

## 3. Part de chacun (lignes ajoutées, hors merges)

| Personne | Lignes ajoutées | Part du code applicatif et infra | Remarque |
|---|---|---|---|
| Kevin | ~18 500 | ~60 % | `-5 114` lignes côté front sont un déplacement de dossier, pas une suppression de contenu |
| Gabriel | ~10 400 | front et habilitations | Un commit importe l'application Pay-Now (~9 200 lignes), trois autres portent les habilitations et NIS2/DORA |
| François | ~6 800 | BDD, API, observabilité, RAG, banc ER6, firmware ESP32 | 24 commits |
| Antoine | ~1 700 | sauvegarde BDD, sonde, firmware ESP32, docs de reprise | 11 commits |
| Hugo | ~500 | alerting Grafana, Ansible | 2 commits |

Chiffres calculés le 22/10 sur `git log main --no-merges --numstat`, identités Git regroupées par personne.

Le compte de lignes surestime le front de Gabriel : l'application Pay-Now d'origine est importée telle quelle, puis adaptée. Il mesure la quantité de texte, pas l'effort ni la difficulté.

## 3 bis. Diagramme de Gantt (travail réellement commité)

Les dates sont celles des commits et des merges de PR, à la journée près (le 22/10 a été ajouté après la consigne additionnelle 1). Les deux barres rouges de Hugo (essais d'installation ratés) sont déclarées par l'équipe et absentes de Git. Chaque barre va du premier au dernier commit du lot, sans refléter le temps passé dessus. Le diagramme s'affiche sur GitHub et dans les éditeurs compatibles Mermaid.

```mermaid
gantt
    title Travail réel par personne (19/10 au 22/10/2026)
    dateFormat YYYY-MM-DD
    axisFormat %d/%m
    tickInterval 1day
    todayMarker off

    section Kevin
    Architecture, conventions, gouvernance (squelettes)  :k1, 2026-10-19, 1d
    Moteur de remédiation, proxy Docker, /metrics        :k2, 2026-10-19, 1d
    Auth JWT, passerelle Caddy, espace client            :k3, 2026-10-19, 1d
    Détecteur ML, trafic de fond, deadlock virements     :k4, 2026-10-20, 1d
    WAF ModSecurity, blocage par compte, dashboard SIEM  :k5, 2026-10-20, 1d
    Watcher de crash, boucle de démo, détection S4       :k6, 2026-10-20, 1d
    EBIOS 1 à 5, NIS2/DORA, PCA/PRA, AMDEC               :k7, 2026-10-20, 2d
    SOPS, rotation de secrets, durcissement Caddy        :k8, 2026-10-21, 1d
    Autoheal Alloy, campagne flood, script SQLi          :k9, 2026-10-21, 1d
    Jalons, README, clôture des écarts                   :k10, 2026-10-19, 3d
    -RenderEnv, ruff, validation du jalon du 22/10       :k11, 2026-10-21, 1d
    Consigne 1, auth, agent caméra, /admin, LED, rejeu :k12, 2026-10-22, 1d
    Alertes flood, blocklist, correctif LED, docs        :k13, 2026-10-22, 1d

    section François
    Outillage Claude Code                                :f1, 2026-10-19, 1d
    BDD PostgreSQL et API métier                         :f2, 2026-10-19, 1d
    Pile d'observabilité et Compose du socle             :f3, 2026-10-19, 1d
    Assistant RAG, horodatage du flood                   :f4, 2026-10-20, 1d
    Banc ER6, firmware ESP32, dossier                    :f5, 2026-10-22, 1d

    section Gabriel
    Intégration de l'app Pay-Now                         :g1, 2026-10-19, 1d
    Reprise de l'interface d'origine adaptée au back     :g2, 2026-10-20, 1d
    Habilitations, console, NIS2/DORA                    :g3, 2026-10-22, 1d

    section Antoine
    Sauvegarde et restauration PostgreSQL (S4)           :a1, 2026-10-20, 1d
    Sonde de transaction unifiée, mesures S4             :a2, 2026-10-21, 1d
    Firmware ESP32, rejeu S4, EBIOS/PCA, API docs        :a3, 2026-10-22, 1d

    section Hugo
    Installation sur WSL (échec, erreur réseau)          :crit, h0, 2026-10-19, 1d
    Essai sur Windows (échec)                            :crit, h0b, 2026-10-20, 1d
    Alerting Grafana (règle SQLi)                        :h1, 2026-10-21, 1d
    Runner Ansible et Deploy.ps1                         :h2, 2026-10-21, 1d

    section Échéances
    Gel du code à 17h (dérogation accordée)              :milestone, m1, 2026-10-22, 0d
    Remise avant 23h59                                   :milestone, m2, 2026-10-22, 0d
```

Lecture : Kevin occupe les quatre jours sans interruption ; François travaille surtout le 19/10 puis revient le 22/10 ; Gabriel et Antoine n'apparaissent qu'à partir du 20/10 ou du 21/10 et contribuent surtout le 22/10 (consigne 1) ; Hugo reste à deux commits. La dernière ligne droite (rejeu, dossier, présentation, rendus) repose presque entièrement sur Kevin, l'équipe n'étant plus disponible le 22/10 au soir.

## 4. Écarts avec la répartition prévue (`CLAUDE.md`)

| Rôle prévu | Prévu | Constaté dans Git |
|---|---|---|
| Hugo : Infra + Cyber (Compose, Ansible, Prom/Grafana/Loki, WAF, SIEM, Vault/SOPS, durcissement, réseau) | Tout le périmètre infra et cyber | Toujours 2 commits au 22/10 : alerting Grafana et runner Ansible avec `Deploy.ps1`. Aucun des lots L1 (persistance) et L3 (réseau) de la consigne 1 n'est livré. Les 19 et 20/10 ont été consacrés à des essais d'installation qui ont échoué (WSL puis Windows), d'où l'absence de commits avant le 21/10 ; l'installation a réussi le 21/10 et Hugo a pu avancer. Le WAF, le SIEM, le durcissement, SOPS et le Compose ont été faits par Kevin ; l'observabilité par François. |
| Kevin : tech lead + remédiation | Architecture, remédiation, ML, intégration | Conforme, mais Kevin a aussi porté l'infra, la cyber, l'auth, la gouvernance et la doc. |
| Antoine : backend, BDD, API, auth, vérification de transaction, EBIOS, PCA/PRA | Backend + gouvernance | Commits sous `eosiswastaken` : sonde de transaction, sauvegarde et restauration BDD, mesures S4, rejeu S4 et restauration à froid, EBIOS et PCA mis à jour après le chaos (#92), firmware ESP32 (#87), documentation des API (#100). BDD et API livrées par François ; auth et rédaction initiale d'EBIOS et PCA/PRA par Kevin. |
| Gabriel : front, Clip Chrono, Grafana, NIS2/DORA, pitch, Pres.pptx | Front + gouvernance + rendus | Front livré, puis habilitations et console du back-office (#93) et relecture de NIS2/DORA le 22/10 (rédigé d'abord par Kevin). Le pitch et la présentation ne sont pas dans Git ; le `Pres.pptx` final a été corrigé et complété par Kevin dans Canva le 22/10. |
| François : RAG + Red Team | RAG, scripts d'attaque, chaos, Dossier PDF | RAG livré. Il a aussi fait BDD, API, observabilité, le banc ER6 (#74) et le portage du firmware sur ESP32. Le script SQLi a été écrit par Kevin ; les scripts d'attaque de la consigne 1 (L5) ne sont pas écrits. |

## 5. Points d'attention avant le gel du code (jeudi 17h)

- **Charge concentrée sur une personne** : environ 60 % du code applicatif et infra, presque toute la gouvernance de base et tous les rendus finaux viennent de Kevin. Le jury demande que chacun explique le code qu'il présente.
- **Preuves de contribution** : les rendus (Dossier PDF, Pres.pptx, clip, zip) ne sont pas versionnés, donc cette analyse ne les couvre pas ; seul le Dossier existe en Markdown (`docs/dossier.md`).

## 7. Répartition de la consigne additionnelle 1 (prévisionnelle, 22/10)

La répartition ci-dessous est **prévisionnelle** ; seul le lot de Kevin (L1 machine à états, L2 agent hôte) est livré, et l'état réel avec ses preuves figure dans le tableau « Avancement et preuves » plus bas. Les autres lignes restent des prévisions, pas des preuves. Conception : [`consigne-additionnelle-1.md`](consigne-additionnelle-1.md). Elle est à valider par l'équipe ; l'historique ci-dessus (§5) montre que Kevin porte déjà la majorité du code, donc le code neuf est réparti sur les autres, Kevin ne gardant que la machine à états, l'agent caméra, l'intégration et les revues. Variante du 22/10 : Antoine prend l'IoT (L3) à sa demande, Hugo reprend la persistance (L1) et les documents EBIOS/AMDEC/PCA.

Échéances : **J0** = avant le gel (si maintenu, jeudi 17h), **J1** = après arbitrage du calendrier (à confirmer auprès de l'enseignant, voir `validation-jalon-22-10.md` §0bis). Tout se fait sur branche, une PR par lot, relue par Kevin.

| Qui | Lot | Tâches | Livrable vérifiable | Échéance |
|---|---|---|---|---|
| Hugo | L1 (persistance) + L3 (réseau) | 1. Tables `roles`, `face_templates`, `login_lockouts` (migration Alembic) et adaptateur `PostgresLockoutStore`, testés. 2. WiFi du point d'accès pour l'ESP32 et pare-feu : l'ESP n'accepte que l'IP du PC Hôte. 3. Lancement de l'agent caméra par `Deploy.ps1`, avec Kevin | Migration rejouable à froid ; blocage conservé après redémarrage de `auth` ; ESP32 joignable depuis le PC Hôte seulement | J0 (tables), J1 (réseau, déploiement) |
| Kevin | L1 (machine à états) + L2 | 1. Machine à états d'authentification dans `application/` (identifiant → visage → mot de passe, 2 échecs → blocage 5 min par identifiant), ports `FaceVerifier`, `CameraControl`, `StatusLed`, `LockoutStore` + fakes, tests `pytest`. 2. Agent hôte natif `host-agent/camera` : ouverture/fermeture de la caméra, détection et comparaison (YuNet + SFace), API locale à jeton. 3. Mesure du seuil de similarité sur les membres consentants et de la RAM de l'agent | Scénarios de la table de la LED verts avec des fakes ; un visage enrôlé reconnu, un autre rejeté, caméra éteinte après décision ; chiffres du seuil | J0 (états + reconnu/rejeté), J1 (mesures) |
| Antoine | L3 (firmware) | 1. Firmware `firmware/esp32-led/` (CLion + PlatformIO) pour la carte disponible ESP32-DevKitC/V1 : client WiFi, `POST /led` signé, durées dans le firmware. 2. Câblage de la LED bicolore et résistances, test sur banc. 3. README du service `auth` (réclamé au §0 du jalon). Aide de Hugo pour le WiFi | LED qui suit chaque état de la table, y compris après coupure réseau ; photo ou vidéo du banc | J0 (WiFi + 2 couleurs), J1 (tous les modes) |
| Gabriel | L4 | 1. Page `/admin` dans le front (React + Tailwind) : comptes, rôles, enrôlement et révocation d'un visage, déblocage d'un identifiant, journal d'accès. 2. Parcours de connexion du back-office (saisie identifiant, retour visuel de la caméra, saisie du mot de passe). 3. Panneau Grafana des événements `auth.*` | Parcours complet utilisable avec les fakes, puis avec l'agent | J1 |
| François | L5 | 1. Scripts d'attaque `attack/` : force brute sur l'identifiant, présentation d'une photo, coupure de la caméra/de l'ESP32 (garde-fous `ALLOWED_HOSTS`, depuis le PC Attaquant seulement). 2. Scénario de chaos correspondant et critères de reprise. 3. Rapport honnête : l'usurpation par photo réussit-elle ? | Journal d'attaque avec résultats réels, y compris les échecs de la défense | J1 |
| Gabriel + Hugo | L6 | Gabriel : NIS2/DORA, Dossier PDF, Pres.pptx, pitch. Hugo : EBIOS (ER7/ER8, SS6, SO3), AMDEC, matrice, PCA (mode dégradé si caméra ou ESP en panne), mis à jour **avec les résultats réels** | Plus aucune ligne « À FAIRE » sans responsable ; aucune ligne « PROUVÉ » sans essai | J1 |
| Kevin | Transverse | Arbitrage du gel, revue de chaque PR (SOLID, pas de logique dans les routes), `pytest` et `scripts/demo_loop.py --runs 5` verts avant chaque merge, mise à jour de ce tableau avec les preuves | `main` stable | en continu |

### Avancement et preuves (22/10)

Mis à jour par Kevin après le merge de la PR #72 (`fd95d3b`, commits `e4f71fb` et `ccd0d42`). Complété le 22/10 après la PR #75 (`2430ebc`) et un premier essai sur la caméra intégrée du PC de Kevin. Seul ce qui a été exécuté est marqué « prouvé » ; tout le reste est dit non prouvé.

| Lot | Responsable | État | Preuve (commande ou constat) | Non prouvé / reste à faire |
|---|---|---|---|---|
| L1 machine à états | Kevin | **Livré** (PR #72) | `pytest` de `services/auth` : 39 tests verts (hors `test_metrics.py`, dépendance absente du venv local), `ruff` et `black` propres. Les scénarios de la table de la LED, le blocage 2 échecs / 5 min, la libération après 5 min, la remise à zéro après succès, l'usage unique de la reconnaissance et l'échec fermé sont couverts avec des fakes | Le test avec une vraie caméra |
| Routes et câblage `auth` | Kevin | **Livré** (PR #72) | Image `auth` reconstruite, conteneur sain. Sans agent configuré : `POST /auth/admin/identify` → 503, `POST /auth/admin/login` sans visage → 403 ; le parcours client reste à 401 sur un mauvais mot de passe. `docker compose config` valide avec le `.env` | Avec l'agent et un visage enrôlé (essai du 22/10, via le WAF) : parcours nominal `identify` 200 puis `login` 200 ; mauvais mot de passe 401, puis 403 tant que le visage n'est pas revérifié ; deux échecs, puis `identify` → 423 avec `Retry-After: 300`. Événements `auth.*` présents dans Loki | Le blocage reste en mémoire (voir L1 persistance) ; cas « agent arrêté » rejoué le 22/10 via le WAF : `identify` → 503, `login` → 403 (échec fermé) |
| L2 agent hôte | Kevin | **Livré, essayé sur la caméra intégrée** (PR #72) | Agent : 21 tests verts, dont un test de fumée sur les vrais modèles ONNX. Démarrage réel sur le port 8765 : 401 sans jeton, 503 sans caméra (échec fermé). Essai du 22/10 sur la **caméra USB** (UGREEN) : gabarit enrôlé sur la caméra intégrée, réutilisé tel quel. Similarité du membre enrôlé : 10 mesures, min 0,752, moyenne 0,786, max 0,806. Un autre membre consentant (1 personne, 10 mesures) : min 0,023, moyenne 0,060, max 0,094. Seuil 0,363 entre les deux groupes, conservé. Agent réel : 401 sans jeton, 503 caméra éteinte, `verify` → `match: true` puis `false` pour un identifiant sans gabarit, 503 après `camera/stop`. RAM de l'agent caméra allumée : environ 198 Mo (working set) | Mesure faite sur **1 seul imposteur** et 10 images, une caméra, une lumière : pas un taux d'erreur ; voyant de la caméra non constaté ; aucune détection de vivacité |
| Non-régression du fil rouge | Kevin | **Prouvé** | `scripts/demo_loop.py --runs 5` : avant le merge, 5/5 reprises automatiques, RTO moyen 39 s, max 44 s ; après le merge sur `main`, 5/5, RTO moyen 39 s, max 41 s ; transaction de test réussie à chaque passage. Rejoué le 22/10 après le merge des PR #77/#78 : 5/5, RTO moyen 32 s, max 36 s, transaction réussie à chaque passage. Rejoué une nouvelle fois le 22/10 (10:35) après le merge des PR #79/#80/#81 : 5/5, RTO moyen 32 s, max 35 s, transaction réussie à chaque passage, critère de sortie du jalon du 22/10 (§7 de `validation-jalon-22-10.md`) atteint. Rejoué le 22/10 (18h55) après la PR #103 et le banc LED, avec `reset_demo.sh` sur la pile déjà démarrée (pas de clone neuf) et le flood lancé depuis le PC Hôte : 5/5, détection 22 à 27 s, RTO moyen 31 s, max 34 s, transaction réussie à chaque passage | |
| RAG sur Ollama distant | Kevin (vérification) | **Prouvé** | `OLLAMA_URL=http://192.168.137.157:11434` : `llama3.1:8b` (8,0 B) et `nomic-embed-text` présents ; depuis le conteneur `rag-assistant`, `/ask` → 200 avec 5 sources (13,8 s), sans jeton → 401 | Pare-feu du PC Ollama (n'accepter que `192.168.137.1`) non vérifié |
| L1 persistance | Hugo | À faire | Aucune. Le blocage est **en mémoire** (perdu au redémarrage de `auth`) en attendant `PostgresLockoutStore` | Tables, migration, adaptateur, test de redémarrage |
| L3 réseau et déploiement | Hugo | À faire | Aucune. `Deploy.ps1` ne lance pas encore l'agent (`host-agent/camera/run.ps1` existe et relit désormais le jeton dans le `.env`) ; `render_env.sh` génère `HOST_AGENT_URL` et `HOST_AGENT_TOKEN` | WiFi de l'ESP32, pare-feu, lancement de l'agent |
| L3 firmware | Antoine | **Flashé et essayé sur banc** (PR #87, correctif PR #103) | `firmware/esp32-led/` (PlatformIO, ESP32-DevKitC/V1) : `POST /led` signé HMAC-SHA256 (compteur anti-rejeu) et filtre sur l'IP du PC Hôte, 5 modes, durées dans le firmware ; README avec contrat, câblage GPIO25/26 et flash USB | Le 22/10 : compilation (`pio run -d firmware/esp32-led -e esp32dev`), flash sur COM3, IP 192.168.137.226. Les 5 modes renvoient 200 depuis le PC Hôte et depuis le conteneur `auth` ; signature invalide 401, rejeu 409, IP hors liste 403. La signature passe par des paramètres d'URL car le `WebServer` ESP32 ne rend pas les en-têtes personnalisés (PR #103). Voie rouge reprise après un contact fragile, puis confirmée | Coupure réseau de l'ESP32 en cours de séquence, photo ou vidéo de la LED |
| L4 page `/admin` | Kevin (connexion, PR #75) puis Gabriel (habilitations, console) | **Livré en partie** (PR #75, `2430ebc` ; PR #93 de Gabriel, `58e120f`) | Connexion : page `/admin` (identifiant, visage, mot de passe ; messages 403, 503, 401 ; compte à rebours 423) jouée contre le vrai back ; section « Authentification du back-office » du dashboard (6 événements comptés dans Loki). Habilitations (Gabriel) : rôles `admin` / `operator`, refus sans rôle (`auth.access.denied_no_role`), jeton de back-office à audience `backoffice` (refusé par l'API métier), console `/admin/console` (habilitations, déblocage, journal d'accès) ; 63 tests `pytest` verts dans `auth`, `tsc` de l'application et `vite build` propres | Habilitations jouées seulement avec des doubles, pas sur le PC Hôte ; aucun test automatisé du front ; panneau « caméra ou agent indisponible » non déclenché ; blocage et habilitations en mémoire ; enrôlement volontairement en ligne de commande |
| L5 attaques | François | À faire | Aucune script L5 constaté ; essais manuels du 22/10 sur le banc (mauvais mot de passe, 2e échec et blocage, visage inconnu, agent arrêté) | Force brute scriptée, photo, coupure ESP32, chaos |
| L6 gouvernance | Hugo + Gabriel (réalisé par Gabriel, Antoine et Kevin) | **Livré** | NIS2/DORA relu par Gabriel (`1c2c9d6`) ; EBIOS et PCA mis à jour par Antoine après le chaos (#92) ; matrice, AMDEC et statuts « à valider » soldés par Kevin le 22/10 (relecture seule, équipe indisponible) ; aucun lot assuré par Hugo | Investigation manuelle de la SQLi non démontrable |

Écarts connus à signaler au jury : habilitations non persistantes (en mémoire, repartent de `BACKOFFICE_ADMINS` au redémarrage), pas de détection de vivacité, blocage non persistant.

Ordre : L1 et L3 démarrent en parallèle (aucune dépendance matérielle croisée), L2 dès que la caméra est sur le PC Hôte, L4 après le contrat d'API de L1, L5 et L6 en dernier.

Chacun doit pouvoir expliquer son lot devant le jury, code généré par IA compris (règle du dépôt).

## 6. Méthode et limites

- Sources : `git log --all --numstat`, `git shortlog`, `gh pr list` (auteur de chaque PR).
- Un commit ou une PR est attribué·e à son auteur Git. Le travail fait à plusieurs sur un même poste, ou commité par une autre personne, n'apparaît pas.
- Les volumes de lignes sont approximatifs et incluent les tests, la documentation et les fichiers générés.
- Les lignes ne mesurent ni la difficulté ni l'effort de conception.
