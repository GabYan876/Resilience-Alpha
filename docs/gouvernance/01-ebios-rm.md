# EBIOS Risk Manager — Resilience-Alpha

Statut : squelette. Responsable : Antoine. Données techniques : Hugo, Kevin.

## Atelier 1 — Cadrage et socle de sécurité

### Périmètre
- Plateforme de paiement **fictive** conteneurisée : front, API métier, auth, BDD, WAF, observabilité, moteur de remédiation, assistant RAG.
- Référence architecture : `docs/architecture/` (À COMPLÉTER avec le schéma validé lundi).

### Valeurs métier et biens supports

| Valeur métier | Description | Biens supports (conteneurs, données) | Critique ? |
|---|---|---|---|
| Traitement d'un paiement | Une transaction est acceptée et enregistrée | API métier, auth, BDD, WAF | À DÉFINIR |
| Intégrité des données de transaction | Montants/comptes non altérés | BDD | À DÉFINIR |
| Confidentialité des données clients (fictives) | Pas de fuite | BDD, secrets (Vault/SOPS) | À DÉFINIR |
| Capacité de détection et de reprise | Détecter et se réparer sans humain | Moteur de remédiation, Prometheus, Loki, modèle ML | À DÉFINIR |

### Événements redoutés

| ID | Événement redouté | Valeur impactée | Impact (échelle) | Gravité |
|---|---|---|---|---|
| ER1 | Paiement indisponible (flood / saturation) | Traitement d'un paiement | Coût d'arrêt : À DÉFINIR | À DÉFINIR |
| ER2 | Exfiltration de données (SQLi) | Confidentialité | À DÉFINIR | À DÉFINIR |
| ER3 | Altération de transactions | Intégrité | À DÉFINIR | À DÉFINIR |
| ER4 | Détournement du moteur de remédiation (droits élevés) | Détection et reprise | À DÉFINIR | À DÉFINIR |

### Socle de sécurité (écarts)
Référentiel retenu : À DÉFINIR. Pour chaque règle, état (appliquée / partielle / absente) + preuve dans le dépôt.

## Atelier 2 — Sources de risque

| Source de risque | Objectif visé | Motivation | Ressources | Retenue ? |
|---|---|---|---|---|
| Attaquant externe (PC Attaquant, simulé) | Indisponibilité / vol de données | À DÉFINIR | Outils d'attaque (`attack/`) | Oui |
| Initié malveillant ou négligent | À DÉFINIR | | | À DÉFINIR |

## Atelier 3 — Scénarios stratégiques

Écosystème et parties prenantes : image Docker tierces, dépendances Python/npm, modèle Ollama, hébergeur du PC Hôte, etc.

| ID | Source | Objectif | Chemin d'attaque (partie prenante) | Gravité | Mesures écosystème |
|---|---|---|---|---|---|
| SS1 | Attaquant externe | Saturer le paiement | Flood HTTP via le WAF | À DÉFINIR | |
| SS2 | Attaquant externe | Exfiltrer la BDD | SQLi via API métier | À DÉFINIR | |
| SS3 | Attaquant externe | Compromettre la chaîne logicielle | Image/dépendance piégée | À DÉFINIR | |

## Atelier 4 — Scénarios opérationnels

Pour chaque scénario stratégique : séquence (reconnaissance → intrusion → exploitation → effet), vraisemblance, lien avec le script d'attaque réel.

| ID | Scénario | Script d'attaque | Vraisemblance | Détection prévue (ML, WAF, log) |
|---|---|---|---|---|
| SO1 | Flood | À DÉFINIR (François) | À DÉFINIR | Détecteur ML sur métriques Prometheus |
| SO2 | SQLi / exfiltration | À DÉFINIR (François) | À DÉFINIR | WAF + Loki |

## Atelier 5 — Traitement du risque

| Risque | Niveau initial | Mesure | Où dans le dépôt | Preuve (test/démo) | Risque résiduel |
|---|---|---|---|---|---|
| Flood | À DÉFINIR | Blocage IP + restart + vérif transaction | `services/remediation/` | Démo n°… | À DÉFINIR |
| SQLi | À DÉFINIR | WAF + rotation de secrets + investigation | | | |

Les lignes alimentent [04-matrice-tracabilite.md](04-matrice-tracabilite.md).
