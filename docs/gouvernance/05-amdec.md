# AMDEC — priorisation des défaillances

Complète EBIOS : classe les défaillances par ordre de priorité (RPN) pour décider où investir en premier.
Les échelles et seuils ne sont pas inventés : l'équipe doit les fixer.

## Échelles (à décider en équipe)

| Critère | Échelle | Définition |
|---|---|---|
| Gravité (G) | 1–4 | Échelle commune avec EBIOS : voir [01-ebios-rm.md](01-ebios-rm.md) |
| Fréquence (F) | 1–4 (proposition : 1 rare, 2 occasionnelle, 3 fréquente, 4 quasi systématique dans le contexte du démonstrateur) | |
| Non-détection (D) | 1–4 (proposition : 1 détection quasi certaine, 4 non détectable) | Capacité du modèle ML / WAF / logs à voir la défaillance |
| RPN | G × F × D (max 64) | Décision du 19/10 |
| Seuil d'action | RPN ≥ 24 (indicatif) | À recaler une fois le tableau rempli |

## Arborescence du système
Front → WAF → API métier → auth / BDD ; moteur de remédiation ; observabilité (Prometheus, Loki, Grafana) ; Vault/SOPS ; assistant RAG.

## Tableau

| Composant | Défaillance | Cause | Effet | G | F | D | RPN | Prévention | Repli / reprise |
|---|---|---|---|---|---|---|---|---|---|
| API métier | Saturation | Flood | Paiement indisponible | | | | | Détection ML, rate limit | Blocage IP + restart |
| BDD | Fuite de données | SQLi | Atteinte à la confidentialité | | | | | WAF, requêtes paramétrées | Rotation secrets |
| Moteur de remédiation | Faux positif | Modèle ML mal calibré | Coupure inutile | | | | | Seuil à calibrer | Retour arrière |
| Prometheus / Loki | Indisponible | Manque de RAM | Détection aveugle | | | | | `mem_limit` | Restart |
| Vault / SOPS | Secret exposé | Mauvaise config | Compromission | | | | | | Rotation |
| WAF | Faux positif | Règle trop stricte / IP partagée sur le hotspot | Utilisateur légitime bloqué | | | | | Règles testées, liste blanche | Déblocage d'IP (reset) |
| Modèle ML | Dérive ou contournement | Données d'entraînement non représentatives, trafic forgé | Attaque non vue ou coupure inutile | | | | | Réentraînement, seuil calibré | Retour arrière |
| docker-socket-proxy | Détourné ou trop permissif | Mauvaise liste d'endpoints | Prise de contrôle de l'hôte | | | | | Endpoints restreints, réseau interne | Rotation des secrets, reconstruction |
| Assistant RAG | Injection de prompt | Document indexé piégé | Fuite d'information indexée | | | | | Lecture seule, aucun accès privilégié | Désactivation du service |
| PC Hôte | Indisponible | Panne matérielle / réseau hotspot | Plateforme entière arrêtée | | | | | Non démontrable (SPOF) | Hors périmètre |
