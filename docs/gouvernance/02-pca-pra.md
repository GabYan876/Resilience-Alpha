# PCA / PRA — Resilience-Alpha

Statut : squelette. Responsable : Antoine. Valeurs RTO/RPO : mesurées par Kevin lors des essais.

## 1. Périmètre et hypothèses
- Hébergement : PC Hôte unique (Docker Compose). Pas de site de secours réel : à écrire comme limite.
- Services couverts : front, API métier, auth, BDD, WAF, moteur de remédiation, observabilité.

## 2. Scénarios couverts

| ID | Scénario | Type | Réponse | Automatique ? |
|---|---|---|---|---|
| S1 | Flood sur l'API | Disponibilité | Blocage IP + restart + vérif transaction | Oui (Zero-Touch) |
| S2 | SQLi / exfiltration | Compromission | Rotation des secrets, investigation, blocage | À DÉFINIR (partie manuelle ?) |
| S3 | Crash d'un conteneur | Disponibilité | Restart + vérif | Oui |
| S4 | Perte de la BDD / corruption | Données | Restauration sauvegarde | À DÉFINIR |
| S5 | Perte du PC Hôte | Site | Hors périmètre démontrable | Non |

Distinguer **restauration de disponibilité** (S1, S3) et **correction de compromission** (S2) : les actions sont différentes.

## 3. Objectifs de continuité et de reprise

| Service | Criticité | RTO cible | RTO mesuré | RPO cible | RPO mesuré | Source de la mesure |
|---|---|---|---|---|---|---|
| Paiement (API + auth + BDD) | À DÉFINIR | À DÉFINIR | À MESURER | À DÉFINIR | À MESURER | Événements JSON de remédiation (Loki) |
| Dashboard | À DÉFINIR | | | | | |
| Observabilité | À DÉFINIR | | | | | |

Définition de la reprise : **API saine ET transaction de test réussie** (pas seulement un conteneur relancé).

## 4. Responsabilités

| Rôle | Qui | Responsabilité en cas d'incident |
|---|---|---|
| Pilotage / décision | Kevin | À DÉFINIR |
| Infra / WAF | Hugo | |
| Backend / BDD | Antoine | |
| Front / dashboard | Gabriel | |
| Investigation / red team | François | |

## 5. Choix de restauration
Stratégie de sauvegarde (fréquence, lieu, chiffrement), restauration de la BDD, rejouabilité (script de reset d'état). À DÉFINIR avec Hugo et Antoine.

## 6. Procédures
Les procédures opérationnelles vont dans `docs/procedures/`. Une procédure par scénario.

## 7. Essais et preuves
Chaque essai : date, scénario, résultat, RTO observé, intervention humaine (oui/non), lien vers log ou capture.

| Date | Scénario | Résultat | RTO observé | Intervention humaine | Preuve |
|---|---|---|---|---|---|
| | | | | | |

Objectif : ≥ 5 passages sans intervention.

## 8. Risques qui subsistent après la reprise
À DÉFINIR. À rédiger honnêtement : ex. attaquant qui revient, secret compromis non détecté, SPOF du PC Hôte, faux positif du modèle ML.
