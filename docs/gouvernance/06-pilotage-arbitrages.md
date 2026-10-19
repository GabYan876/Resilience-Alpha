# Pilotage, arbitrages et recommandations

Le sujet attend une démarche de conseil : quels arbitrages, quelles recommandations à une direction, sur quels éléments vérifiables.
Statut : squelette. Responsable : Gabriel, avec Kevin.

## 1. Gouvernance du projet (comitologie)

| Instance | Participants | Fréquence | Décide de quoi |
|---|---|---|---|
| Point d'équipe quotidien | Toute l'équipe | Quotidien | Avancement, blocages, état du fil rouge |
| Revue d'architecture | Kevin (tech lead) + Hugo | À DÉFINIR | Choix techniques, ajout de composant (impact RAM, exposition, droits) |
| Revue de PR | Kevin | Par PR | Conformité SOLID et conventions |
| Gel du code | Équipe | Jeu 22/10 17h | Fin des changements |

Documentation des décisions : tableau de la section 2.

## 2. Registre des arbitrages

| Date | Décision | Options écartées | Raison | Preuve / mesure | Décideur |
|---|---|---|---|---|---|
| 19/10 | Python/FastAPI pour tous les services | Node.js, Go | Simplifie ML + remédiation | | Équipe |
| 19/10 | Loki plutôt qu'Elastic | Elastic | RAM limitée à 16 Go | | Équipe |
| 19/10 | Architecture hexagonale (SOLID) pour les services Python | Architecture en un bloc | Substituabilité des adaptateurs (fakes en test), moteur testable sans I/O | `services/remediation/tests/` | Kevin |
| 19/10 | Accès Docker uniquement via `docker-socket-proxy` | Montage direct de `docker.sock` | Limiter les droits du moteur (ER4) | `DockerProxyClient` | Kevin |
| 19/10 | Deux passerelles Docker distinctes : `docker-proxy-ctl` (redémarrage, moteur) et `docker-proxy` (lecture seule, Alloy) | Un proxy unique partagé ; Alloy sur `docker.sock` | Alloy ingère des logs contrôlés par l'attaquant : il ne doit avoir aucun chemin d'écriture vers Docker ; l'observabilité reste autonome pendant les redémarrages du moteur | `docker-compose.yml`, `docker-compose.observability.yml` | Kevin (à valider avec Hugo) |
| 19/10 | `trace_id` en métadonnée structurée Loki, jamais en label | `trace_id` indexé | Un `trace_id` par transaction créerait un flux Loki par transaction (limites, RAM 384 Mo) | `config.alloy`, `observabilite.md` | Kevin |
| 19/10 | Outillage Claude Code partagé : plugins tiers épinglés, context7 pour la documentation publique seule, règles ajoutées à `CLAUDE.md` | Réglages individuels ; mise à jour automatique des plugins | Même comportement sur les 5 postes, sans exécution de code non relu ; rien de confidentiel envoyé à un service externe | `.claude/settings.json`, `docs/dev.md` | Équipe (validé en présentiel) |
| 19/10 | Détection en push : le détecteur appelle `POST /incidents` (token) | Polling par le moteur | Découplage, point d'entrée unique | `services/remediation/app/api/routes.py` | Kevin |
| 19/10 | Jamais d'incident « résolu » sans API saine ET transaction de test réussie | Redémarrage seul | Preuve de reprise (axe remédiation) | `HealthAndProbeVerifier` | Kevin |
| 19/10 | Échelle de gravité unique à 4 niveaux ; AMDEC en G × F × D (1–4), seuil ≥ 24 | Échelle 1–10, criticité G × F | Cohérence EBIOS/AMDEC, la non-détection est au cœur du projet | `05-amdec.md` | Kevin (à valider en équipe) |
| 19/10 | Socle de sécurité : Guide d'hygiène ANSSI | ISO 27002, checklist interne | Référence courante avec EBIOS RM | `01-ebios-rm.md` | Kevin (à valider en équipe) |
| 19/10 | DORA applicable, NIS2 en complément | NIS2 seule, les deux sans hiérarchie | Activité de paiement, DORA lex specialis | `03-nis2-dora.md` | Kevin (à valider en équipe) |
| 19/10 | RTO mesuré de début d'attaque à `incident.resolved` | Détection → résolution seulement | Mesure réaliste, inclut la détection | Journal d'attaque + Loki | Kevin (à valider en équipe) |
| 19/10 | S2 : automatique sauf investigation (manuelle, assumée) | Tout automatique, tout manuel | L'absence de fuite ne se prouve pas automatiquement | `02-pca-pra.md` | Kevin (à valider en équipe) |
| 19/10 | S3 par health check périodique ; S4 par `RestoreDatabaseAction` | Tout par le ML ; restauration manuelle | Un crash est une panne binaire ; Zero-Touch sur la BDD | `02-pca-pra.md` | Kevin (à valider en équipe) |

## 3. Services jugés critiques et coût d'un arrêt
À DÉFINIR : quelles fonctions, pourquoi, quel coût pour l'activité fictive (hypothèses explicitées).

## 4. Recommandations à la direction
À rédiger en fin de semaine, à partir des essais :
1. Ce qui est prouvé (avec preuves).
2. Ce qui reste à faire pour un déploiement réel.
3. Investissements priorisés (lien avec l'AMDEC).
4. Risques résiduels acceptés ou à traiter.

## 5. Indicateurs de pilotage
À DÉFINIR avec l'équipe. Pistes : RTO mesuré (et sa décomposition délai de détection / temps de remédiation), taux de reprise automatique sur ≥ 5 démos, faux positifs ML, nombre d'interventions humaines (cible : 0).
