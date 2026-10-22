# EBIOS Risk Manager, Resilience-Alpha

Statut : ateliers 1 à 5 rédigés le 20/10 sous forme de propositions, relues et reprises par Kevin le 22/10 (équipe indisponible). Responsable initial : Antoine. Données techniques : Hugo, Kevin.

## Atelier 1, Cadrage et socle de sécurité

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
| Traitement d'un paiement | Une transaction est acceptée et enregistrée | API métier, auth, BDD, WAF | Oui |
| Intégrité des données de transaction | Montants/comptes non altérés | BDD | Oui |
| Confidentialité des données clients (fictives) | Pas de fuite | BDD, secrets (Vault/SOPS) | Oui (données fictives, exigence traitée comme réelle) |
| Capacité de détection et de reprise | Détecter et se réparer sans humain | Moteur de remédiation, Prometheus, Loki, modèle ML | Oui (c'est l'objet du sujet) |

### Événements redoutés

| ID | Événement redouté | Valeur impactée | Impact (échelle) | Gravité |
|---|---|---|---|---|
| ER1 | Paiement indisponible (flood / saturation) | Traitement d'un paiement | Arrêt toléré = RTO cible (60 s) ; au-delà, des paiements sont perdus | 3 Grave |
| ER2 | Exfiltration de données (SQLi) | Confidentialité | Fuite de comptes et de soldes (fictifs) | 4 Critique |
| ER3 | Altération de transactions | Intégrité | Soldes faux, virements rejoués | 4 Critique |
| ER4 | Détournement du moteur de remédiation (droits élevés) ou du `docker-socket-proxy` | Détection et reprise | Droits élevés sur les conteneurs, perte de contrôle | 4 Critique |
| ER5 | Faux positif ou contournement du modèle ML (coupure inutile, ou attaque non vue) | Détection et reprise, Traitement d'un paiement | Coupure inutile ou attaque non vue ; reprise automatique attendue | 2 Significative |
| ER6 | Abus de l'assistant RAG (injection de prompt, fuite de documents indexés) | Confidentialité | Fuite de la documentation indexée (non confidentielle) | 2 Significative |
| ER7 | Accès frauduleux au back-office (usurpation de visage, mot de passe volé, force brute), ajouté le 22/10, consigne additionnelle 1 | Confidentialité, Intégrité, Détection et reprise | Habilitations modifiées, gabarits biométriques lus, perte de contrôle du back-office | 4 Critique |
| ER8 | Indisponibilité de l'authentification renforcée (caméra, agent hôte ou ESP32 en panne), ajouté le 22/10 | Accès des opérateurs | Back-office inaccessible (échec fermé), aucun paiement client touché | 2 Significative |

### Socle de sécurité (écarts)
Référentiel retenu (décision du 19/10) : **Guide d'hygiène informatique de l'ANSSI**, limité aux règles pertinentes pour le démonstrateur. Pour chaque règle : état (appliquée / partielle / absente) + preuve dans le dépôt. Les numéros de règles sont à reporter depuis le guide.

| Thème | Règle retenue (n° à reporter) | État | Preuve dans le dépôt |
|---|---|---|---|
| Cloisonnement réseau | Réseaux Docker internes, seul le WAF publié | Appliquée | `infra/compose/` |
| Comptes et moindre privilège | `docker-socket-proxy`, pas d'interface d'admin exposée | Appliquée | `infra/compose/`, `services/remediation/app/adapters/docker_proxy.py` |
| Secrets | SOPS + age, aucun secret en clair | Appliquée (21/10) : `.env` ignoré par Git, secrets chiffrés dans `infra/secrets/*.enc.yaml`, rotation testée en réel | `infra/secrets/`, `.sops.yaml`, `.gitignore`, `06-pilotage-arbitrages.md` |
| Journalisation et détection | Logs JSON centralisés (Loki), détection ML | Appliquée | `infra/observability/`, `services/remediation/app/adapters/json_publisher.py` |
| Sauvegarde | Sauvegarde et restauration de la BDD | Partielle : archives planifiées sur le même hôte ; chiffrement et essai réel restant | `services/db/recovery/`, `services/db/README.md` |
| Dépendances et images | Versions épinglées | Partielle : versions fixes, pas de scan de vulnérabilités | `services/*/requirements.txt` |

## Atelier 2, Sources de risque

| Source de risque | Objectif visé | Motivation | Ressources | Retenue ? |
|---|---|---|---|---|
| Attaquant externe (PC Attaquant, simulé) | Indisponibilité / vol de données | Perturber ou voler un service de paiement | Outils d'attaque (`attack/`) | Oui |
| Initié négligent | Exposer un secret ou mal configurer | Aucune intention | Accès au dépôt et au Compose | Oui (secret commité, `.env` copié) ; l'initié malveillant est hors périmètre du démonstrateur |

## Atelier 3, Scénarios stratégiques

Écosystème et parties prenantes : image Docker tierces, dépendances Python/npm, modèle Ollama, hébergeur du PC Hôte, etc.

| ID | Source | Objectif | Chemin d'attaque (partie prenante) | Gravité | Mesures écosystème |
|---|---|---|---|---|---|
| SS1 | Attaquant externe | Saturer le paiement | Flood HTTP via le WAF | 3 Grave | WAF CRS, détecteur ML, blocage du compte/subject ; l'IP source n'est pas identifiable sous Docker Desktop |
| SS2 | Attaquant externe | Exfiltrer la BDD | SQLi via API métier | 4 Critique | WAF CRS, requêtes paramétrées, compte BDD `app_rw` limité |
| SS3 | Attaquant externe | Compromettre la chaîne logicielle | Image/dépendance piégée | 4 Critique | Versions épinglées, WAF par digest ; scan de vulnérabilités à ajouter |
| SS4 | Attaquant externe | Prendre le contrôle de l'hôte | Détournement du moteur de remédiation ou du `docker-socket-proxy` | 4 Critique | Proxy limité au redémarrage/arrêt d'un conteneur existant, réseau `control` interne, jeton sur `POST /incidents` |
| SS5 | Attaquant externe | Rendre la détection aveugle ou déclencher des coupures | Données forgées pour tromper le modèle ML (faux négatifs / faux positifs) | 2 Significative | Seuil appris, confirmation sur 3 mesures, vérification avant clôture |
| SS6 | Attaquant externe ou physique | Entrer dans le back-office | Photo/écran devant la caméra, mot de passe volé ou deviné, force brute sur l'identifiant, ou voie physique (débrancher la caméra / l'ESP32) | 4 Critique | Vérification 1:1 + mot de passe, blocage 5 min par identifiant, échec fermé ; **détection de vivacité non prévue** (risque accepté, à assumer) |

## Atelier 4, Scénarios opérationnels

Pour chaque scénario stratégique : séquence (reconnaissance → intrusion → exploitation → effet), vraisemblance, lien avec le script d'attaque réel.

| ID | Scénario | Script d'attaque | Vraisemblance | Détection prévue (ML, WAF, log) |
|---|---|---|---|---|
| SO1 | Flood : compte créé, connexion, rafale sur `/me/account` jusqu'à épuiser le pool de connexions BDD | `attack/flood_http.py` | Forte (outil simple, aucun prérequis) | Détecteur ML sur métriques Prometheus ; journal d'accès du WAF dans Loki pour désigner le compte |
| SO2 | SQLi / exfiltration : reconnaissance des routes, injection dans un paramètre, extraction | `attack/sqli_injection.py` (écrit le 21/10) | Moyenne (CRS bloque les motifs courants au niveau 1) | Règles CRS dans le journal d'audit du WAF, vues dans Loki et Grafana, 12/12 charges bloquées le 21/10 (règle 942100), voir `02-pca-pra.md` §7 |
| SO3 | Force brute / usurpation sur le back-office : essais répétés d'identifiants, présentation d'une photo | À écrire (François, consigne additionnelle 1) | Moyenne (photo : aucune défense de vivacité) | Événements `auth.face.rejected` et `auth.lockout.started` dans Loki ; **non implémenté à ce jour** |

## Atelier 5, Traitement du risque

| Risque | Niveau initial | Mesure | Où dans le dépôt | Preuve (test/démo) | Risque résiduel |
|---|---|---|---|---|---|
| Flood | 3 Grave | Blocage du compte (`block_subject`) + restart + vérif transaction | `services/remediation/` | `scripts/demo_loop.py` : 5/5 reprises, RTO 33-48 s ; essai du 21/10 depuis le PC Attaquant à travers le WAF : 5/5, vérification 403 du compte bloqué (`02-pca-pra.md` §7). Le 22/10, `block_ip` a échoué faute d'IP source identifiable sous Docker Desktop ; `block_subject` + restart ont réussi (4,84 s de `incident.detected` à `incident.resolved`, détection du flood non chronométrée), même référence §7 | Faible à moyen : l'IP n'est pas distinguée sous Docker Desktop ; un attaquant peut créer d'autres comptes |
| SQLi | 4 Critique | WAF + rotation de secrets + investigation (manuelle, assumée) | `infra/waf/`, `RotateSecretAction`/`SopsSecretRotator` | `attack/sqli_injection.py` le 21/10 : 12/12 charges bloquées (403, règle CRS 942100) ; le 22/10 depuis le PC Attaquant : 6/6 bloquées (403). Rotation essayée séparément et manuellement (`POST /incidents kind=compromise`), `02-pca-pra.md` §7 | Moyen : blocage WAF prouvé pour les charges testées ; rotation essayée mais pas déclenchée par un signal SQLi ; investigation toujours manuelle |
| Altération de transactions (ER3 / S4) | 4 Critique | Détection d'intégrité → restauration de l'archive antérieure → restart API → vérification par transaction | `services/remediation/`, `services/db/recovery/` | Essais automatiques : 20/10, 5 passages isolés (RTO ≈ 5 s) ; 21/10, 2 passages pile complète (RTO 3,24–3,79 s, RPO 13,56–59,32 s) ; 22/10, 1 passage S4 isolé (RTO 6,376839 s de `Tc` à `incident.resolved`, dont 4,826715 s jusqu'à la détection et 1,550124 s de remédiation ; RPO 108,776809 s). API saine et transaction de sonde réussie. Journaux JSON stdout horodatés, incident `719c01d79127434898a87be13d2bdb5f`, archive `backup-20261022T113339.759793Z.dump` ; [preuve détaillée `s4-corruption-bdd.md`](../procedures/s4-corruption-bdd.md), procédure `docs/procedures/s4-corruption-bdd.md` | Moyen : le rejeu du 22/10 est un passage unique sur pile jetable, sans WAF, Alloy ni Grafana ; événements capturés en stdout et non dans Loki ; résultat non statistique. RPO théorique ≈315 s, supérieur à la cible de 5 min ; sauvegardes locales non chiffrées |
| Détournement du moteur | 4 Critique | `docker-socket-proxy` (endpoints restreints), token sur `POST /incidents` | `infra/compose/`, `services/remediation/app/api/routes.py` | Revue de configuration des endpoints autorisés le 21/10 (`docs/validation-jalon-21-10.md` §2) ; architecture (`docs/architecture/architecture.md` §2/§6). Cette revue ne constitue pas un essai d'exploitation du moteur ou du proxy | Moyen : la configuration est documentée, mais la résistance à une exploitation n'a pas été démontrée ; un jeton volé permet de déclencher des redémarrages |
| Faux positif / contournement ML | 2 Significative | Seuil calibré, vérification de reprise avant clôture | `services/remediation/`, `ml/` | `evaluate` : 0 faux positif sur 120 mesures | Moyen : le score d'IsolationForest sature, seuil à recalibrer sur trafic réel |
| Accès frauduleux au back-office (ER7) | 4 Critique | Caméra USB + reconnaissance 1:1, mot de passe, blocage 5 min par identifiant, gabarits chiffrés (SOPS) | `services/auth` (dont habilitations `admin` / `operator`, PR #93), `host-agent/camera` (livrés) ; `firmware/esp32-led/` (flashé, essayé sur banc le 22/10) ; conception dans `docs/consigne-additionnelle-1.md` | Parcours identifiant → visage → mot de passe, blocage 423 et échec fermé (503/403) essayés en réel le 22/10 via le WAF ; voir `04-matrice-tracabilite.md` ; habilitations et refus sans rôle prouvés par tests avec des doubles seulement ; aucune attaque (force brute, photo) rejouée | Moyen après essai du parcours ; usurpation par photo non couverte (pas de vivacité), blocage et habilitations non persistants (en mémoire) |

Les lignes alimentent [04-matrice-tracabilite.md](04-matrice-tracabilite.md).
