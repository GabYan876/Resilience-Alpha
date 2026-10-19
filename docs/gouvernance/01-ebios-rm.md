# EBIOS Risk Manager — Resilience-Alpha

Statut : squelette. Responsable : Antoine. Données techniques : Hugo, Kevin.

## Atelier 1 — Cadrage et socle de sécurité

### Périmètre
- Plateforme de paiement **fictive** conteneurisée : front, API métier, auth, BDD, WAF, observabilité, moteur de remédiation, assistant RAG.
- Référence architecture : [`docs/architecture/architecture.md`](../architecture/architecture.md) (schéma, réseaux Docker, ports du moteur de remédiation). Les biens supports ci-dessous reprennent ses noms de services.

### Échelle de gravité (commune à EBIOS et à l'AMDEC)

Décision du 19/10 : une seule échelle à 4 niveaux (proposition de définitions, à valider en équipe).

| Niveau | Libellé | Repère |
|---|---|---|
| 1 | Mineure | Gêne sans impact sur le paiement |
| 2 | Significative | Dégradation temporaire, reprise automatique attendue |
| 3 | Grave | Paiement indisponible ou atteinte limitée aux données |
| 4 | Critique | Fuite/altération de données ou perte de contrôle du moteur de remédiation |

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
| ER4 | Détournement du moteur de remédiation (droits élevés) ou du `docker-socket-proxy` | Détection et reprise | À DÉFINIR | À DÉFINIR |
| ER5 | Faux positif ou contournement du modèle ML (coupure inutile, ou attaque non vue) | Détection et reprise, Traitement d'un paiement | À DÉFINIR | À DÉFINIR |
| ER6 | Abus de l'assistant RAG (injection de prompt, fuite de documents indexés) | Confidentialité | À DÉFINIR | À DÉFINIR |

### Socle de sécurité (écarts)
Référentiel retenu (décision du 19/10) : **Guide d'hygiène informatique de l'ANSSI**, limité aux règles pertinentes pour le démonstrateur. Pour chaque règle : état (appliquée / partielle / absente) + preuve dans le dépôt. Les numéros de règles sont à reporter depuis le guide.

| Thème | Règle retenue (n° à reporter) | État | Preuve dans le dépôt |
|---|---|---|---|
| Cloisonnement réseau | Réseaux Docker internes, seul le WAF publié | À ÉVALUER | `infra/compose/` |
| Comptes et moindre privilège | `docker-socket-proxy`, pas d'interface d'admin exposée | À ÉVALUER | `infra/compose/`, `services/remediation/app/adapters/docker_proxy.py` |
| Secrets | Vault ou SOPS, aucun secret en clair | À ÉVALUER | `infra/secrets/`, `.gitignore` |
| Journalisation et détection | Logs JSON centralisés (Loki), détection ML | À ÉVALUER | `infra/observability/`, `services/remediation/app/adapters/json_publisher.py` |
| Sauvegarde | Sauvegarde et restauration de la BDD | À ÉVALUER | À DÉFINIR |
| Dépendances et images | Versions épinglées | À ÉVALUER | `services/*/requirements.txt` |

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
| SS4 | Attaquant externe | Prendre le contrôle de l'hôte | Détournement du moteur de remédiation ou du `docker-socket-proxy` | À DÉFINIR | |
| SS5 | Attaquant externe | Rendre la détection aveugle ou déclencher des coupures | Données forgées pour tromper le modèle ML (faux négatifs / faux positifs) | À DÉFINIR | |

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
| SQLi | À DÉFINIR | WAF + rotation de secrets + investigation (manuelle, assumée) | `infra/waf/`, `RotateSecretAction` | | |
| Détournement du moteur | À DÉFINIR | `docker-socket-proxy` (endpoints restreints), token sur `POST /incidents` | `infra/compose/`, `services/remediation/app/api/routes.py` | Revue de la config | |
| Faux positif / contournement ML | À DÉFINIR | Seuil calibré, vérification de reprise avant clôture | `services/remediation/`, `ml/` | Résultats d'essais | |

Les lignes alimentent [04-matrice-tracabilite.md](04-matrice-tracabilite.md).
