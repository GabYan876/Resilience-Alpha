# Reste à faire avant la remise (jeudi 22/10, 23h59)

Passe de revue du 22/10 à 17h50, sur `main` (dernier commit `53d94af`). Dérogation au gel de 17h accordée à l'équipe.
Cases à cocher au fur et à mesure ; ajouter le nom de la personne et l'heure quand c'est fait.

## État vérifié à 17h50

- `pytest` vert : api 58, auth 64, remediation 85, anomaly-detector 45, agent caméra 21 (`rag-assistant` et `db/recovery` non lancés, pas de venv sur ce poste).
- `ruff check` et `ruff format --check` propres (263 fichiers) ; `tsc` du front propre.
- PR ouvertes : 0.
- Rendus présents : `dist/Workshop2026-M2-G2/Workshop2026-M2-G2-Dossier.pdf` (10 pages, généré à 17h21). Pas de `Pres.pptx`, `VidChrono.mp4` ni `Code.zip` constatés (non versionnés, peut-être faits ailleurs).
- Pile Docker non rejouée pendant la revue (Docker Desktop arrêté sur le poste).

## 1. Priorité haute

- [x] **Fusionner le correctif LED** (PR #103, `2dabca0`, Kevin, 22/10) : la branche `origin/francois/webserver` porte `a1e91ac` (signature par paramètres d'URL, `espressif32@8.0.0`) et `4050edb` (essai de bout en bout sur banc), absents de `main`. Sur `main`, `services/auth/app/adapters/esp_led.py` envoie `X-Counter` / `X-Signature` en en-têtes, que le WebServer de l'ESP32 ne restitue pas : la LED est refusée en 401. Faire une PR, `pytest` de `auth` vert, reflasher si besoin, fusionner.
- [x] **Livrables** dans `Workshop2026-M2-G2/` :
  - [x] `-Pres.pptx` (Kevin, 22/10, Canva, 12 diapos ; chiffres alignés sur le rejeu : RTO moyen 31 s, max 34 s)
  - [x] `-VidChrono.mp4` ≤ 60 s, sans coupe, avant / pendant / après dans Grafana (Kevin, 22/10)
  - [x] `-Dossier.pdf` régénéré (Kevin, 22/10 20h40, 12 pages, Gantt corrigé, Edge sans fenêtre depuis `docs/dossier.md`) à partir de `docs/dossier.md` après les corrections de doc, 8 à 12 pages (François)
  - [x] `-Code.zip` sans secret (fait et vérifié par Kevin le 22/10 : aucun `.env` ni clé age dans l'archive) : exclure `.env`, `infra/secrets/*-age-key.txt`, `.venv`, `node_modules`, `dist/`, `ml/models/*.joblib` ; garder les `*.enc.yaml`
- [x] **Rejeu à froid sur le PC Hôte** (Kevin, 22/10, voir sous-cases), à refaire après la fusion LED :
  - [x] démarrer Docker Desktop
  - [x] (Kevin, 22/10 : `-RenderEnv` produit `WAF_BIND_HOST=127.0.0.1`, hotspot en `192.168.137.1` à fixer pour le PC Attaquant) vérifier l'IP du PC Hôte et `WAF_BIND_HOST` dans `.env` (le WAF refuse de démarrer si l'IP est absente)
  - [x] (Kevin, 22/10 vers 19h45 : clone neuf de `dc1dfeb`, volumes supprimés, `Deploy.ps1 -RenderEnv` sans erreur, 12 services en marche, transaction réglée ; puis `demo_loop.py --runs 5` : 5/5 reprises, RTO moyen 33 s, max 36 s, depuis le PC Hôte) `Deploy.ps1` sur clone neuf, pile saine, transaction de test réussie
  - [x] `scripts/reset_demo.sh` puis `python scripts/demo_loop.py --runs 5` : 5/5 reprises (Kevin, 22/10 18h55, RTO moyen 31 s, max 34 s ; pile déjà démarrée, flood depuis le PC Hôte, donc à refaire sur clone neuf et depuis le PC Attaquant)
  - [x] (Kevin, 22/10 de 19h57 à 20h08 heure locale) 5 passages depuis le PC Attaquant : flood lancé depuis le PC Attaquant vers le WAF du PC Hôte (`192.168.137.1:8080`, hotspot), clone neuf, 5/5 reprises automatiques, transaction de test réussie à chaque passage, un seul incident par passage, aucun échec ; détection 25 à 32 s, RTO de l'attaque à `incident.resolved` : 35, 32, 34, 31 et 30 s (moyenne 32 s, max 35 s ; horloges des deux PC non comparées, incertitude d'environ 1 s). Le compteur « erreurs » du flood ne compte que les 5xx et les erreurs réseau, il ne prouve pas le blocage en cours d'attaque

## 2. Consigne additionnelle 1

- [x] **Parcours complet joué sur le PC Hôte** (Kevin, 22/10 vers 18h40, LED sur banc ; reste à garder une capture ou vidéo) : identifiant → caméra → LED → mot de passe → blocage 5 min, avec preuve (capture, vidéo, événements `auth.*` dans Loki). Jamais essayé de bout en bout avec la LED.
- [ ] Habilitations `admin` / `operator` et console `/admin/console` (PR #93) jouées sur le PC Hôte (testées jusqu'ici avec des doubles seulement).
- [ ] Coupure réseau de l'ESP32 en cours de séquence (`green_solid`) essayée.
- [ ] **Persistance** (lot L1 de Hugo, non fait) : tables `roles`, `face_templates`, `login_lockouts` (migration Alembic), `PostgresLockoutStore`, test de redémarrage de `auth`. Sinon, le consigner comme limite assumée.
- [x] (Kevin, 22/10 : commande documentée dans le README racine et `infra/ansible/README.md`, `Deploy.ps1` ne le lance pas) Agent caméra lancé par `Deploy.ps1` (aujourd'hui lancé à la main via `host-agent/camera/run.ps1`). Sinon, documenter la commande.
- [ ] Consentement écrit des membres enrôlés ; aucun gabarit hors du PC Hôte.
- [ ] Attaques de François (L5) : force brute sur l'identifiant, photo devant la caméra, coupure caméra / ESP32, avec journal des résultats réels, y compris les échecs de la défense.
- [ ] Pare-feu du PC Ollama (n'accepter que `192.168.137.1`) vérifié.

## 3. Documentation incohérente à corriger

- [x] `docs/gouvernance/03-nis2-dora.md` §4 point 3 : dit « firmware compilé mais non essayé sur banc », alors que la matrice (ER8) et le dossier disent flashé et essayé le 22/10.
- [x] `docs/validation-jalon-22-10.md` (§7 et §8 remplis, responsables proposés à valider) : cocher ce qui est fait (L2 caméra, remédiation, etc.) et remplir le §8 « Écarts restants » avec un responsable par ligne.
- [x] `docs/repartition-reelle.md` §7 (L3 firmware, L5, L6) : L3 firmware (« non flashé »), L5 et L6 (« à faire ») à mettre à jour.
- [x] `docs/gouvernance/04-matrice-tracabilite.md` : ligne ER2 encore « À FAIRE » (investigation manuelle de la SQLi) ; garder « À FAIRE » avec responsable ou passer en « NON DÉMONTRABLE » expliqué.
- [x] `services/db/README.md` « Reste à implémenter » : points périmés (auth n'est plus un squelette, RPO / S4 mesurés).
- [x] `README.md` « Limites connues » : retirer « À compléter au fil du sprint » et ajouter les limites ci-dessous.
- [x] Statuts « à valider par Antoine / l'équipe » à solder dans EBIOS, AMDEC et PCA/PRA.
- [x] (Kevin, 22/10 : #93 confirmée, PR de Gabriel fusionnée) `docs/dossier.md` cite le bon numéro de PR pour les habilitations.
- [x] (Kevin, 22/10) `README.md`, `architecture.md` et matrice alignés avec la pile réellement déployée.

## 4. Hygiène du dépôt

- [x] (Kevin, 22/10 : `origin/main` seule branche distante, 0 PR ouverte) Supprimer les branches de travail distantes une fois la fusion LED faite (`origin/pr/*`, `francois/*`, `kevin/*`, `gabriel/*`, `antoine/*`, `infra/*`, `fix/*`, `eosiswastaken-*`, `docs/*`) ; `gh pr list --state open` doit rester vide.
- [x] `mem_limit` présent sur les 18 services des deux fichiers compose (Kevin, 22/10 : 11 + 7, aucun `deploy:`).
- [x] Seul le WAF publie un port (Kevin, 22/10 : `${WAF_BIND_HOST}:8080:8080`, aucun autre `ports:`).
- [ ] `ruff check` et `ruff format --check` confirmés sur les postes de Hugo, Antoine, Gabriel et François après `git pull`.
- [ ] `infra/ansible/README.md` relu par un autre membre que Kevin.
- [ ] Dashboard Grafana vérifié sur les trois temps (Gabriel).
- [ ] Chacun sait expliquer son périmètre devant le jury, code généré par IA compris.

## 5. Limites à assumer devant le jury (ne rien développer vendredi)

- Compromission (S2) non détectée automatiquement : rotation de secret prouvée seulement en déclenchement manuel (`POST /incidents kind=compromise`).
- `block_ip` inopérant sous Docker Desktop (blocage par compte via `block_subject`).
- Sauvegardes S4 locales, non chiffrées, non répliquées.
- Pas de détection de vivacité (photo devant la caméra).
- Blocage et habilitations en mémoire si la persistance n'est pas faite.
- Blocage WAF non réinitialisé hors `reset_demo.sh`.
- Pas de test de l'équilibre comptable (ER3) dans `check_transaction.sh` ; tests de la base sur des doubles, pas un vrai PostgreSQL.
- Score IsolationForest saturé, seuil à recalibrer sur trafic réel.
- Injection de prompt RAG (ER6) : défense par le prompt non étanche.

## 6. Critères de sortie avant 23h59

- [x] ≥ 5 démos consécutives sans intervention, transaction de test réussie à chaque passage
- [x] Une attaque de disponibilité et une de compromission traitées, RTO mesuré
- [x] Clip 60 s sans coupe livré
- [x] `main` stable, PR ouvertes = 0, branches supprimées
- [x] Dossier PDF, Pres.pptx, VidChrono.mp4 et Code.zip (sans secret) remis
- [ ] Consigne 1 : tranche démontrée avec preuve, ou écart consigné avec responsable
