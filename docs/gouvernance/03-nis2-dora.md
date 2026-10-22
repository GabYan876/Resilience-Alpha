# NIS2 / DORA — Resilience-Alpha

Statut : version du 22/10, relue par Gabriel et reliée aux essais réels du 20 au 22/10 (chaos du 22/10 compris). Première version : 20/10 (Kevin). Responsable : Gabriel. Relecture : Antoine.

Principe du sujet : distinguer les exigences **pertinentes** pour une activité financière fictive des obligations qui **ne peuvent pas être démontrées** par un prototype de 4 jours. Règle appliquée ici : une ligne n'est « Couverte » que si un essai réel la prouve (journal des essais : [`02-pca-pra.md`](02-pca-pra.md) §7) ; sinon, l'écart est nommé.

Textes : NIS2 = directive (UE) 2022/2555 ; DORA = règlement (UE) 2022/2554. Les numéros d'articles ont été précisés le 22/10 ; vérifiés le 22/10 un par un (intitulé et alinéa) sur des miroirs du texte (nis-2-directive.com, digital-operational-resilience-act.com) : aucun écart. EUR-Lex n'a pas répondu (page vide) ; **relire le Journal officiel avant la remise**.

## 1. Applicabilité

Position retenue (décision du 19/10) :
- **DORA applicable** : l'entité fictive exerce une activité de paiement, c'est donc une entité financière au sens de DORA (art. 2).
- **NIS2 en complément** : quand un acte sectoriel impose des exigences au moins équivalentes, il prime (NIS2 art. 4, *lex specialis*). DORA est cet acte pour le secteur financier. NIS2 reste un repère, notamment pour la chaîne d'approvisionnement et l'authentification multifacteur.
- Classification « essentielle » / « importante » de NIS2 : sans objet, puisque DORA prime pour la gestion du risque TIC et la notification des incidents.

## 2. Exigences pertinentes et lien avec le démonstrateur

Couverture : **Couverte** (prouvée par un essai réel, preuve citée), **Partielle** (une partie seulement, écart nommé), **Non couverte** (rien de démontrable).

| Thème | Exigence (résumé) | Réf. | Ce que fait le démonstrateur | Preuve (essai réel) | Couverture |
|---|---|---|---|---|---|
| Gestion des risques | Analyse de risques documentée, cadre de gestion du risque TIC | NIS2 art. 21 §2 a) / DORA art. 6 | EBIOS RM (5 ateliers), AMDEC, matrice de traçabilité | [`01-ebios-rm.md`](01-ebios-rm.md), [`05-amdec.md`](05-amdec.md), [`04-matrice-tracabilite.md`](04-matrice-tracabilite.md) | Partielle : ateliers rédigés le 20/10, encore au statut « proposition », pas validés formellement ; pas encore mis à jour avec les essais du 22/10 (lot L6, Hugo) |
| Détection | Détecter rapidement les activités anormales | DORA art. 10 | Détecteur ML (IsolationForest) sur les métriques Prometheus, sans règle codée en dur | `app.cli evaluate` du 22/10 : 60 mesures inédites avec trafic de fond, **0 fausse alerte** ; jeu d'attaque : 75 % des mesures jugées anormales, alerte à la 5ᵉ mesure. 21/10 : 0/120 à travers le WAF | Couverte pour le flood. Pas de détecteur de compromission automatique (la SQLi est arrêtée par le WAF, pas par le ML) |
| Réponse et rétablissement | Réponse aux incidents, rétablissement rapide, sans dépendre d'une intervention humaine | DORA art. 11 / NIS2 art. 21 §2 b) | Pipeline `Detector → DecisionPolicy → RemediationAction[] → RecoveryVerifier` ; incident clos seulement si API saine **et** transaction de test réussie | `demo_loop.py --runs 5` rejoué le 22/10 sur `main` : **5/5 reprises sans intervention**, RTO 28 à 35 s (moyenne 32 s), détection comprise. 22/10, flood depuis le PC Attaquant à travers le WAF : `incident.detected` → `incident.resolved` en **4,84 s**. 21/10 : 5/5 depuis le PC Attaquant | Couverte. `block_ip` reste inopérant sous Docker Desktop (le WAF ne voit que la passerelle Docker) : seul `block_subject` agit, écart assumé (arbitrage du 20/10) |
| Disponibilité ≠ compromission | Traiter différemment une panne et une compromission | DORA art. 11 | `DecisionPolicy` : flood → blocage + redémarrage ; compromission → rotation de secret | Flood : `block_subject` + `restart_service` (22/10). SQLi : 6/6 charges bloquées par le WAF depuis le PC Attaquant (403, règle CRS 942100, 22/10) ; rotation du `JWT_SECRET` prouvée le 21/10 en déclenchement manuel | Partielle : la rotation n'est pas déclenchée automatiquement par un signal SQLi réel ; pas d'investigation de compromission |
| Gestion des incidents | Processus de gestion, classification, traçabilité | DORA art. 17-18 / NIS2 art. 21 §2 b) | Chaque étape émet un événement JSON (`incident.detected`, `decision.made`, `action.executed`, `verification.completed`, `incident.resolved`) dans Loki ; dashboard Grafana avant / pendant / après | `incident_id` horodatés dans Loki (ex. `1f545270…` du 22/10) ; alerte Grafana sur la SQLi | Partielle : traçabilité complète et horodatée, mais pas de classification de gravité au sens de DORA art. 18 ni de notification (voir § 3) |
| Continuité, sauvegarde et restauration | PCA/PRA, sauvegardes, restauration testée | DORA art. 11-12 / NIS2 art. 21 §2 c) | PCA/PRA, sauvegarde PostgreSQL, restauration automatique sur corruption (S4), reset d'état | S4 rejoué 2 fois le 21/10 : restauration automatique, transaction de sonde réussie, **RTO 3,24 à 3,79 s, RPO 13,56 à 59,32 s** ; S3 (crash de l'API) : reprise en 34 s le 20/10 | Couverte pour S1, S3 et S4. Restauration à froid complète (arrêt total puis redémarrage en une commande) pas encore rejouée après le chaos |
| Tests de résilience | Programme de tests réguliers, scénarios réalistes | DORA art. 24-25 | Démonstration rejouable en boucle, chaos du jeudi, attaques réelles depuis le PC Attaquant | 5/5 (20/10), 5/5 depuis le PC Attaquant (21/10), 5/5 sur `main` (22/10) ; flood et SQLi depuis le PC Attaquant (22/10) | Couverte à l'échelle du prototype. Pas de programme dans la durée ni de test par un tiers (voir § 3) |
| Cryptographie et secrets | Politique de chiffrement, gestion des clés | NIS2 art. 21 §2 h) / DORA art. 9 | SOPS + age, aucun secret en clair dans le dépôt, rotation du secret JWT | `infra/secrets/*.enc.yaml` ; rotation `RotateSecretAction` / `SopsSecretRotator` prouvée en réel le 21/10 ; gabarit biométrique chiffré (Fernet) sur le PC Hôte seulement | Couverte. Déclenchement de la rotation encore manuel |
| Contrôle d'accès, moindre privilège | Politiques d'accès, gestion des droits | NIS2 art. 21 §2 i) / DORA art. 9 §4 | docker-socket-proxy (aucun accès direct à `docker.sock`), réseaux internes, seul le WAF publie un port, jeton sur `POST /incidents`, `cap_drop`, assistant RAG en lecture seule | `infra/compose/` ; transactions jouées à travers le WAF depuis le PC Attaquant | Couverte |
| Authentification forte | MFA pour l'accès aux systèmes critiques | NIS2 art. 21 §2 j) / DORA art. 9 §4 d) | Back-office (consigne additionnelle 1) : identifiant → visage 1:1 (caméra du PC Hôte) → mot de passe ; 1 reprise puis blocage 5 min **par identifiant** ; échec fermé si caméra ou agent en panne ; habilitations `admin` / `operator` (sans rôle, pas d'accès) | 22/10 : visage reconnu / refusé et blocage 5 min joués à travers le WAF ; seuil mesuré (membre enrôlé 0,752-0,806, autre membre 0,023-0,094) ; RAM de l'agent ~198 Mo. Habilitations : 63 tests `pytest` du service `auth` (doubles) | Partielle : pas de détection de vivacité (une photo peut tromper la caméra, scénario de François) ; blocage et habilitations en mémoire (perdus au redémarrage de `auth`) ; firmware ESP32 de la LED compilé, non essayé sur banc ; habilitations testées avec des doubles, pas encore jouées sur le PC Hôte |
| Données biométriques | Traitement de catégorie particulière | RGPD art. 9 (et art. 35, analyse d'impact) | Seul le gabarit (128 valeurs) est stocké, chiffré, jamais l'image ; jamais dans Git, le zip, les logs ni une IA externe ; seuls des membres consentants enrôlés ; enrôlement en ligne de commande sur le PC Hôte, jamais par le réseau | `host-agent/camera/README.md` ; `.gitignore` (`data/`, `*.tpl`) ; événements Loki avec empreinte de l'identifiant, jamais en clair | Partielle : consentement écrit des membres enrôlés à archiver ; pas d'analyse d'impact formelle |
| Risque lié aux tiers | Dépendances et fournisseurs TIC | DORA art. 28 / NIS2 art. 21 §2 d) | Images et dépendances épinglées | Images à version fixe, WAF par digest, `requirements.txt` en `==`, `package-lock.json` | Partielle : pas de scan de vulnérabilités ni de SBOM, pas de registre d'informations (DORA art. 28 §3) |

## 3. Non démontrable par un prototype de 4 jours

| Obligation | Réf. | Pourquoi non démontrable | Ce que l'on recommanderait |
|---|---|---|---|
| Notification des incidents majeurs (alerte initiale, rapport intermédiaire, rapport final) | DORA art. 19 / NIS2 art. 23 | Pas d'autorité réelle ni d'incident réel | Classer la gravité (DORA art. 18) à partir des événements `incident.*`, qui donnent déjà l'horodatage, l'action et la durée ; pré-remplir le rapport depuis Loki |
| Responsabilité de l'organe de direction | DORA art. 5 / NIS2 art. 20 | Pas de gouvernance d'entreprise réelle | Faire valider les risques résiduels et le PCA/PRA par la direction (ici, le jury joue ce rôle) |
| Registre d'informations et clauses contractuelles des prestataires TIC | DORA art. 28 §3, art. 30 | Pas de contrats | Tenir un registre des images et dépendances tierces (déjà épinglées) et prévoir des clauses de sortie |
| Tests de pénétration fondés sur la menace (TLPT) | DORA art. 26 | Hors délai et périmètre | Faire tester par un tiers indépendant ; ici l'attaque est jouée par notre propre équipe |
| Formation et cyberhygiène | NIS2 art. 21 §2 g) | Pas de personnel réel | Programme de sensibilisation, en commençant par l'hameçonnage et le mot de passe du back-office |

## 4. Écarts à présenter au jury

Ces écarts sont assumés, pas cachés. Chacun est relié à un essai ou à une limite connue du README :

1. **Compromission** : la SQLi est arrêtée par le WAF (prouvé), mais la rotation de secret n'est pas déclenchée automatiquement par ce signal (prouvée seulement en déclenchement manuel).
2. **`block_ip` inopérant sous Docker Desktop** : le blocage se fait par sujet (`block_subject`), pas par IP (arbitrage du 20/10).
3. **Authentification forte** : pas de détection de vivacité, blocage et habilitations non persistants, firmware ESP32 de la LED compilé mais non essayé sur banc.
4. **Notification réglementaire et classification de gravité** : non développées ; les événements `incident.*` en sont la base.

## 5. Recommandations à la direction

Voir [06-pilotage-arbitrages.md](06-pilotage-arbitrages.md). Priorités issues des écarts ci-dessus : (1) brancher la rotation de secret sur un détecteur de compromission ; (2) ajouter une détection de vivacité et persister blocages et habilitations (tables `login_lockouts` et `roles`) ; (3) passer d'un hôte Docker Desktop à un hôte Linux pour retrouver l'IP source et le blocage par IP ; (4) SBOM et scan de vulnérabilités dans la chaîne de livraison.
