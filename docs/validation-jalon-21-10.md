# Validation du jalon du mercredi 21/10

Jalon : **intégration WAF / logs / SIEM / ML / remédiation / dashboard, assistant RAG, 1ers tests de restauration.**
Chacun relit son périmètre, répond aux questions et coche. Les réponses sont reportées dans [`06-pilotage-arbitrages.md`](gouvernance/06-pilotage-arbitrages.md).
Les cases cochées ont une preuve dans le dépôt ; les autres attendent la confirmation de la personne.

## 0. Reliquat du jalon du 20/10

Cases restées ouvertes dans [`validation-jalon-20-10.md`](validation-jalon-20-10.md) : à solder avant d'ouvrir le jalon du 21/10.

- [ ] **Ansible (Hugo)** : `infra/ansible/site.yml` et les rôles écrits (`.env`, socle, observabilité, vérification). Sans lui, « une commande » n'est pas tenu.
- [ ] **Vault ou SOPS (Hugo, Kevin)** : choix tranché, `JWT_SECRET`, `PROBE_TOKEN` et mots de passe BDD dans `infra/secrets/`, `RotateSecretAction` branchée (`VaultSecretRotator` ou équivalent SOPS).
- [ ] **Fil rouge avec le PC Attaquant** : flood rejoué depuis le PC Attaquant vers `192.168.137.1` (jusqu'ici en local), à travers le WAF.
- [ ] Front, Grafana et dashboard exposés via le WAF sur `192.168.137.1`.
- [ ] Mesure de la RAM de la pile complète (`docker stats`).
- [ ] Hugo : Loki/Grafana seuls ou Wazuh pour le SIEM ; arbitrages « à valider » du 20/10 (passerelles Docker, WAF par compte).
- [ ] Gabriel : Grafana accepté comme dashboard de supervision (sujet) ; `resilience-alpha.json` parcouru pendant un flood.
- [ ] Tous : `ruff format` fonctionne sur chaque PC ; hotspot `RESILIENCE-G<n>` et PC Hôte en `192.168.137.1`.
- [x] Reliquat du 19/10 : cases EBIOS (ateliers 1 à 3) cochées et réponses d'Antoine et de Kevin reportées dans `validation-jalon-19-10.md`.
- [ ] Reliquat du 19/10 restant : les 5 réseaux Docker réalisables dans le Compose (Hugo), RAG isolé avec ER6 prouvé (François), questions WAF et SOC de Hugo.

## 1. Intégration WAF / logs / SIEM — Hugo

- [ ] WAF ModSecurity + OWASP CRS devant la passerelle ; seul le WAF est publié sur le réseau.
- [ ] Les logs du WAF arrivent dans Loki (Promtail/Alloy) avec `service`, `trace_id`, `event`.
- [ ] Fonction SOC : une règle WAF déclenchée (SQLi) est visible et alertable dans Grafana.
- [ ] Durcissement : conteneurs non-root, réseaux internes (BDD, Vault, gestion), `mem_limit` partout.
- [ ] Reset d'état : script qui remet la démo à zéro entre deux passages.

## 2. Intégration ML / remédiation — Kevin

- [ ] Fil rouge complet à travers le WAF : flood → détection ML → blocage IP + restart → `incident.resolved` après transaction de test.
- [ ] Le blocage d'IP agit sur l'IP réelle de l'attaquant (derrière WAF / hotspot), pas sur celle de la passerelle.
- [ ] Distinction disponibilité / compromission dans `DecisionPolicy` : SQLi/exfiltration → rotation de secrets + investigation, pas un simple restart.
- [ ] Boucle de démos rejouée **depuis le PC Attaquant** : au moins 5 passages sans intervention, RTO mesurés.
- [ ] Faux positifs ML re-mesurés avec le trafic de fond et le WAF actifs.
- [ ] Docker-socket-proxy : revue des endpoints autorisés, aucun accès direct au `docker.sock`.

## 3. Restauration et backend — Antoine

- [ ] S4 (corruption BDD) rejoué avec la pile complète ; RTO et RPO mesurés et reportés dans `02-pca-pra.md`.
- [ ] 1ers tests de restauration à froid : arrêt complet puis redémarrage en une commande, transaction de test réussie.
- [x] Script de vérification de transaction utilisé par le vérificateur et par la démo : même chemin.
- [ ] EBIOS ateliers 4 et 5 mis à jour avec les mesures du 21/10 ; matrice de traçabilité cohérente.
- [ ] Doc d'API à jour si une route a changé.

## 4. Front et dashboard — Gabriel

- [ ] Front de paiement joignable via le WAF depuis le PC Attaquant.
- [ ] Dashboard Grafana lisible avant / pendant / après : disponibilité, latence, requêtes bloquées, événements `incident.*`.
- [ ] Clip chrono 60 s : scénario écrit et 1re prise d'essai (sans coupe).
- [ ] NIS2/DORA relu et relié aux essais réels du 21/10.
- [ ] Trame de `Pres.pptx` et du pitch.

## 5. Attaque et RAG — François

- [ ] Script d'injection SQL (ER2) exécuté depuis le PC Attaquant vers `192.168.137.1` uniquement ; WAF qui bloque, trace dans Loki.
- [ ] Scénario de chaos du jeudi préparé (liste des pannes, ordre, critères de reprise).
- [ ] Périmètre offensif respecté : jamais le campus, un autre groupe ni Internet.
- [ ] RAG : ER6 prouvé (injection de prompt sans effet), lecture seule vérifiée, Ollama sur le PC Linux dédié, modèle ≤ 8B.
- [ ] Dossier PDF : plan en 8–12 pages et répartition des sections.

## 6. Cohérence d'intégration — Kevin

- [ ] Matrice de traçabilité : lignes SQLi, rotation de secrets et détournement du moteur passées à jour (`EN COURS` → `PROUVÉ` quand la preuve existe).
- [ ] `docs/architecture/architecture.md` et `README.md` alignés avec la pile réellement déployée.
- [ ] Branches fusionnées sur `main` ; PR relues par le tech lead.
- [ ] Liste des écarts restants pour le jeudi, avec un responsable chacun.

## 7. Critères de sortie du jalon

- [ ] Le fil rouge tourne de bout en bout **depuis le PC Attaquant, à travers le WAF**, avec détection ML et reprise vérifiée par transaction.
- [ ] Au moins une attaque de compromission (SQLi) est bloquée, visible dans le SIEM/Grafana et traitée (rotation de secrets, procédure d'investigation).
- [ ] Un tiers lance le socle avec une commande (Ansible) et la doc.
- [ ] 1ers tests de restauration consignés (RTO / RPO mesurés).
- [ ] Les écarts restants ont un responsable et une échéance jeudi (chaos engineering, ≥ 5 démos, clip, gel du code à 17h).
