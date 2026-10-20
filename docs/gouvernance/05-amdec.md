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

Cotation du 20/10 : **proposition** (Kevin) à valider par Antoine et l'équipe. La colonne D cite la
preuve disponible ; sans preuve, D vaut 3 ou 4. Les lignes `db-recovery` et « Corruption » sont ajoutées
avec le scénario S4. RPN = G × F × D ; en gras, les RPN ≥ 24 (seuil d'action indicatif).

| Composant | Défaillance | Cause | Effet | G | F | D | RPN | Prévention | Repli / reprise | Preuve de D |
|---|---|---|---|---|---|---|---|---|---|---|
| API métier | Saturation | Flood | Paiement indisponible | 3 | 4 | 1 | 12 | Détection ML, rate limit | Blocage IP + restart | ML : 5/5 reprises mesurées |
| BDD | Fuite de données | SQLi | Atteinte à la confidentialité | 4 | 2 | 3 | **24** | WAF, requêtes paramétrées | Rotation secrets | WAF seul, aucune démo SQLi |
| BDD | Corruption ou suppression de données | Compromission applicative, erreur d'exploitation | Soldes et historique faux ou perdus | 4 | 2 | 3 | **24** | Rôle applicatif sans `DELETE`, grand livre en ajout seul | `db-recovery` : restauration de l'archive antérieure à la détection | Compteurs vus (essai du 20/10), montant modifié non vu |
| db-recovery | Archives indisponibles ou altérées | Volume perdu, archive prise après la corruption | Restauration impossible ou vers un état altéré | 4 | 2 | 2 | 16 | 12 archives, marge `DB_RESTORE_SAFETY_MARGIN_S`, `pg_restore --list` avant restauration | Incident en échec, pas de faux succès | `/health` exige une archive |
| db-recovery | Archives lisibles par un tiers | Volume sur le même hôte, non chiffré | Fuite des données fictives | 3 | 2 | 4 | **24** | Mode 0600, réseau interne, jeton | Chiffrement des archives (non fait) | Aucune alerte de lecture |
| Moteur de remédiation | Faux positif | Modèle ML mal calibré | Coupure inutile | 3 | 2 | 2 | 12 | Seuil appris, 3 confirmations | Retour arrière | 0 % sur 120 mesures |
| Prometheus / Loki | Indisponible | Manque de RAM | Détection aveugle | 3 | 2 | 3 | 18 | `mem_limit` | Restart | Aucune alerte sur la supervision elle-même |
| Vault / SOPS | Secret exposé | Mauvaise config | Compromission | 4 | 2 | 4 | **32** | Variables d'environnement hors dépôt (`.env` ignoré) | Rotation | `infra/secrets/` vide : rien ne détecte une fuite |
| WAF | Faux positif | Règle trop stricte / IP partagée sur le hotspot | Utilisateur légitime bloqué | 2 | 3 | 2 | 12 | Règles testées, liste blanche | Déblocage d'IP (reset) | Visible dans les logs du WAF |
| Modèle ML | Dérive ou contournement | Données d'entraînement non représentatives, trafic forgé | Attaque non vue ou coupure inutile | 3 | 2 | 3 | 18 | Réentraînement, seuil calibré | Retour arrière | Mesure de qualité hors ligne seulement |
| docker-socket-proxy | Détourné ou trop permissif | Mauvaise liste d'endpoints | Prise de contrôle de l'hôte | 4 | 1 | 3 | 12 | Endpoints restreints, réseau interne | Rotation des secrets, reconstruction | Pas de surveillance des appels |
| Assistant RAG | Injection de prompt | Document indexé piégé | Fuite d'information indexée | 2 | 3 | 4 | **24** | Lecture seule, aucun accès privilégié | Désactivation du service | ER6 non prouvée |
| PC Hôte | Indisponible | Panne matérielle / réseau hotspot | Plateforme entière arrêtée | 4 | 1 | 1 | 4 | Non démontrable (SPOF) | Hors périmètre | Panne immédiatement visible |

## Priorités qui en découlent

Classement par RPN décroissant (à recaler une fois la cotation validée) :

1. Vault / SOPS : secret exposé (RPN 32)
2. BDD : fuite de données (RPN 24)
3. BDD : corruption ou suppression de données (RPN 24)
4. db-recovery : archives lisibles par un tiers (RPN 24)
5. Assistant RAG : injection de prompt (RPN 24)
6. Prometheus / Loki : indisponible (RPN 18)

Lecture : les cinq premiers pointent des choix d'infrastructure encore ouverts (secrets, chiffrement
des archives) ou une preuve manquante (SQLi, injection de prompt). La disponibilité de l'API, seul
scénario rejoué 5 fois, sort au plus bas.
