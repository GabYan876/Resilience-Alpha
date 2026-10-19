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
| | | | | | |

## 3. Services jugés critiques et coût d'un arrêt
À DÉFINIR : quelles fonctions, pourquoi, quel coût pour l'activité fictive (hypothèses explicitées).

## 4. Recommandations à la direction
À rédiger en fin de semaine, à partir des essais :
1. Ce qui est prouvé (avec preuves).
2. Ce qui reste à faire pour un déploiement réel.
3. Investissements priorisés (lien avec l'AMDEC).
4. Risques résiduels acceptés ou à traiter.

## 5. Indicateurs de pilotage
À DÉFINIR avec l'équipe. Pistes : RTO mesuré, taux de reprise automatique sur ≥ 5 démos, faux positifs ML, nombre d'interventions humaines (cible : 0).
