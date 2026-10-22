# Validation du jalon du mercredi 21/10

Jalon : **intégration WAF / logs / SIEM / ML / remédiation / dashboard, assistant RAG, 1ers tests de restauration.**
Chacun relit son périmètre, répond aux questions et coche. Les réponses sont reportées dans [`06-pilotage-arbitrages.md`](gouvernance/06-pilotage-arbitrages.md).
Les cases cochées ont une preuve dans le dépôt ; les autres attendent la confirmation de la personne.

## 0. Reliquat du jalon du 20/10

Cases restées ouvertes dans [`validation-jalon-20-10.md`](validation-jalon-20-10.md) : à solder avant d'ouvrir le jalon du 21/10.

- [x] **Ansible (Hugo)** : `infra/ansible/Deploy.ps1`, `site.yml` et rôles (preflight, vérification) ; `-CheckOnly` et `-VerifyOnly` essayés en réel le 21/10 (11 services en marche + transaction de test). Déploiement complet depuis un clone neuf essayé (§7).
- [x] **Vault ou SOPS (Hugo, Kevin)** : tranché **SOPS + age** le 21/10 (`06-pilotage-arbitrages.md`). `JWT_SECRET`, `PROBE_TOKEN` et mots de passe BDD dans `infra/secrets/app.enc.yaml`/`jwt.enc.yaml`, `RotateSecretAction` branchée sur `SopsSecretRotator`. Essai réel : `POST /incidents kind=compromise` → JWT tourné, `auth`/`api` redémarrés, transaction de test encore réglée.
- [x] **Fil rouge avec le PC Attaquant** : flood rejoué depuis le PC Attaquant, à travers le WAF, 5 passages le 21/10, voir `docs/gouvernance/02-pca-pra.md` §7.
- [x] Front, Grafana et dashboard exposés via le WAF : `/grafana` routé par la passerelle, port 3000 dépublié, vérifié depuis un second PC sur la box (`192.168.1.140:8080`, login, dashboard, `POST /api/ds/query` sans 403). `WAF_BIND_HOST` et `GRAFANA_ROOT_URL` réglés sur cette IP dans `.env`. Arbitrage du 21/10 (`06-pilotage-arbitrages.md`) : le réseau n'importe pas (hotspot ou box), seul compte le réseau privé du binôme, box et hotspot sont équivalents pour la démo.
- [x] Mesure de la RAM de la pile complète (`docker stats`, 21/10, 17 conteneurs) : **885 Mo réels au repos, 990 Mo en pic pendant `attack/flood_http.py` (30 s, 60 req/s)**, pour 3 128 Mo de limites cumulées (hors Ollama), loin des 16 Go. Aucun conteneur n'a approché sa limite sous flood (le plus chargé : détecteur 132/256 Mo). Les trois `docker-socket-proxy` restent stables à 25–30/32 Mo. Fil rouge confirmé dans le même passage : `block_subject` (le flood est authentifié, identifié par compte, `block_ip` échoue faute d'IP source, cohérent avec l'arbitrage WAF-par-compte du 20/10) + `restart_service` → `api_healthy: true` + `probe_transaction_ok: true` → incident résolu en ~5 s, sans intervention humaine.
- [x] Hugo : Loki/Grafana seuls ou Wazuh pour le SIEM. *(Loki/Grafana seuls, confirmé par Hugo le 21/10 ; `06-pilotage-arbitrages.md`)*
- [x] Arbitrage « à valider » du 20/10 : passerelle Docker non distinguée, WAF par **compte** plutôt que par IP, validé le 21/10 sur 5 passages réels (`06-pilotage-arbitrages.md` ligne 40).
- [x] Gabriel : Grafana accepté comme dashboard de supervision (sujet) ; `resilience-alpha.json` parcouru pendant un flood (`06-pilotage-arbitrages.md` ligne 41).
- [ ] Tous : `ruff format` fonctionne sur chaque PC *(vérifié sur le PC de Kevin le 21/10 : `ruff format --check` et `ruff check` passent sur tout le dépôt après correction de 10 fichiers ; reste à confirmer sur les autres postes)* ; réseau privé du binôme (hotspot `RESILIENCE-G<n>` ou box) opérationnel entre PC Attaquant et PC Hôte.
- [x] Reliquat du 19/10 : cases EBIOS (ateliers 1 à 3) cochées et réponses d'Antoine et de Kevin reportées dans `validation-jalon-19-10.md`.
- [x] Reliquat du 19/10 restant, vérifié le 21/10 contre le dépôt (voir `validation-jalon-19-10.md` §Hugo) :
  - 5 réseaux Docker : **réalisés**, chaque service n'a que les réseaux dont il a besoin (`rag-assistant` seul sur `rag`, `docker-proxy-ctl` seul sur `control-internal`, etc.), seul le WAF publie un port.
  - RAG isolé : **réalisé côté Compose**, `rag-assistant` : réseau `rag` seul membre, `read_only: true`, `cap_drop: ALL`, `no-new-privileges`, corpus monté `:ro`, et `LLM_MODEL` par défaut = `llama3.1:8b` (le modèle qui a résisté le 20/10, pas le 3B qui avait cédé).
  - ER6 prouvé : **partiel, assumé comme tel**, la config de démo utilise déjà le modèle qui résiste, mais un seul scénario et 3 questions ont été joués (`04-matrice-tracabilite.md` ligne ER6) : pas une garantie, reste `EN COURS`. Gap reporté en §8 (François).
  - Question WAF de Hugo (ModSecurity/Coraza) : **répondue** le 20/10, revalidée le 21/10 (`06-pilotage-arbitrages.md` ligne 40).
  - Question SOC de Hugo (Loki/Grafana seuls ou Wazuh) : **tranchée** le 21/10 en faveur de Loki/Grafana seuls (`06-pilotage-arbitrages.md`, ligne du 21/10 « Fonction SOC »), confirmé par Hugo.

## 1. Intégration WAF / logs / SIEM, Hugo

- [x] WAF ModSecurity + OWASP CRS devant la passerelle ; seul le WAF est publié sur le réseau. *(`waf` = seul `ports:` du Compose ; 12/12 SQLi bloquées en 403, règle CRS 942100)*
- [x] Les logs du WAF arrivent dans Loki (Promtail/Alloy) avec `service`, `trace_id`, `event`. *(21/10 : journal d’accès `waf.request`, audit ModSecurity `waf.blocked` / `waf.audit` étiqueté par Alloy ; `trace_id` = `$request_id` pour l’accès, `transaction.unique_id` pour l’audit ; les requêtes du dashboard SIEM et du détecteur filtrent `event="waf.request"`)*
- [x] Fonction SOC : une règle WAF déclenchée (SQLi) est visible et alertable dans Grafana. *(règle `WAF - Détection SQLi`, PR #55 ; essai du 21/10 : `inactive` puis `firing` après une SQLi)*
- [x] Durcissement : conteneurs non-root, réseaux internes (BDD, Vault, gestion), `mem_limit` partout. *(21/10 : `gateway` Caddy passé en `nobody` (65534) ; seules exceptions root, les 3 `docker-socket-proxy`, qui lisent le socket Docker root et restent bornés par `cap_drop: ALL`, `no-new-privileges`, sections d'API limitées et réseau interne ; Vault non déployé, secrets SOPS)*
- [x] Reset d'état : script qui remet la démo à zéro entre deux passages. *(`scripts/reset_demo.sh`, rejoué 5 fois le 21/10)*

## 2. Intégration ML / remédiation, Kevin

- [x] Fil rouge complet à travers le WAF : flood → détection ML → blocage **compte** (`block_subject`) + restart → `incident.resolved` après transaction de test. `block_ip` échoue toujours sans attaquant identifiable par IP (voir case suivante), c'est le comportement attendu, pas un défaut de ce fil rouge.
- [x] ~~Le blocage d'IP agit sur l'IP réelle de l'attaquant~~, **non applicable sous Docker Desktop, par conception, déjà arbitré le 20/10** (`06-pilotage-arbitrages.md` ligne 40, `architecture.md:152`). Reconfirmé le 21/10 : les 5 passages montrent `block_ip` échouant (« aucune IP source identifiée ») car `attacker_ip` n'est jamais renseigné (`detection.py` ne fait que résoudre `attacker_subject` via Loki), et le `remote` vu par le WAF pour tout le trafic LAN, y compris le flood réel du PC Attaquant, est `172.25.0.1` (passerelle Docker). Implémenter un locator d'IP bloquerait cette passerelle, donc tout le trafic externe, pas l'attaquant : `block_subject` reste la seule action de blocage de source valide sous Docker Desktop. **Arbitrage validé le 21/10** (`06-pilotage-arbitrages.md` ligne 40) sur la base de ces 5 passages réels.
- [x] Distinction disponibilité / compromission dans `DecisionPolicy` : branche `IncidentKind.COMPROMISE` → `RotateSecretAction` + redémarrage de `auth`/`api`, distincte du blocage de source + restart de `AVAILABILITY`. Déclenché manuellement via `POST /incidents kind=compromise` (pas encore par un détecteur de compromission automatique, hors périmètre de ce jalon, voir `06-pilotage-arbitrages.md`) ; investigation manuelle toujours `À FAIRE` (`04-matrice-tracabilite.md`).
- [x] Boucle de démos rejouée **depuis le PC Attaquant** : 5 passages sans intervention le 21/10, RTO (détection→résolution) mesurés à 5,4 / 7,1 / 6,6 / 7,0 / 7,9 s, reset d'état (`scripts/reset_demo.sh`) entre chaque passage. Détail dans `docs/gouvernance/02-pca-pra.md` §7.
- [x] Faux positifs ML re-mesurés avec le trafic de fond et le WAF actifs : 0/120 mesures (2907 requêtes, 0 erreur, `holdout_waf.csv`), aucun `incident.*` parasite, attaque toujours détectée. Détail dans `docs/gouvernance/02-pca-pra.md` §7.
- [x] Docker-socket-proxy : revue des endpoints autorisés, aucun accès direct au `docker.sock`. Nouvelle passerelle `docker-proxy-autoheal` ajoutée le 21/10 (auto-guérison d'Alloy) avec le même principe de moindre privilège que `docker-proxy`/`docker-proxy-ctl` : scope limité à `EVENTS`/`CONTAINERS`/`ALLOW_RESTARTS`, tout le reste explicitement à `0`, réseau `internal: true` dédié. Détail dans `docs/architecture/observabilite.md` §7bis.

## 3. Restauration et backend, Antoine

- [x] S4 (corruption BDD) rejoué avec la pile complète ; RTO et RPO mesurés et reportés dans `02-pca-pra.md` (2 passages le 21/10 : RTO 3,24-3,79 s, RPO 13,56-59,32 s).
- [x] 1ers tests de restauration à froid : arrêt complet puis redémarrage en une commande, transaction de test réussie (pile isolée, volumes conservés ; `scripts/check_transaction.sh` réussi le 21/10).
- [x] Script de vérification de transaction utilisé par le vérificateur et par la démo : même chemin.
- [x] EBIOS ateliers 4 et 5 mis à jour avec les mesures du 21/10 ; matrice de traçabilité cohérente (`01-ebios-rm.md` ateliers 4/5, `04-matrice-tracabilite.md` lignes ER1/ER2/ER4 passées à PROUVÉ avec preuve référencée).
- [ ] Doc d'API à jour si une route a changé.

## 4. Front et dashboard, Gabriel

- [x] Front de paiement joignable via le WAF depuis le PC Attaquant. *(confirmé par Kevin le 21/10)*
- [x] Dashboard Grafana lisible avant / pendant / après : disponibilité, latence, requêtes bloquées, événements `incident.*`. *(passage réel le 21/10 : flood de 30 s via le WAF, `incident.resolved` en ~10 s ; vu par Kevin sur `siem-waf` : comptes bloqués = 1, incidents clos = 1 ; données de `resilience-alpha` relevées dans Prometheus/Loki : débit 0 → 42–48 req/s, événements du moteur)*
- [ ] Clip chrono 60 s : scénario écrit et 1re prise d'essai (sans coupe).
- [ ] NIS2/DORA relu et relié aux essais réels du 21/10.
- [ ] Trame de `Pres.pptx` et du pitch.

## 5. Attaque et RAG, François

- [x] Script d'injection SQL (ER2) : `attack/sqli_injection.py` (gabarit substitué par Kevin le 21/10, François reprend pour le chaos de jeudi). 12/12 charges bloquées (403) à travers le WAF, règle CRS 942100, tracé dans Loki, voir `docs/gouvernance/02-pca-pra.md` §7. Rejoué depuis le PC Attaquant vers le PC Hôte, sur le réseau privé du binôme (confirmé par l'équipe le 21/10), comme le flood ER1.
- [ ] Scénario de chaos du jeudi préparé (liste des pannes, ordre, critères de reprise).
- [x] Périmètre offensif respecté : jamais le campus, un autre groupe ni Internet. *(garde-fou `ALLOWED_HOSTS` dans `attack/flood_http.py` et `attack/sqli_injection.py` : cibles `10.0.0.5`, `8.8.8.8` et `192.168.1.50` refusées sans `--yes-i-know-the-target`, essayé le 21/10 ; seuls la boucle locale et les PC Hôte du binôme passent. Les essais réels du 21/10 n'ont visé que le PC Hôte.)*
- [ ] RAG : ER6 prouvé (injection de prompt sans effet), lecture seule vérifiée, Ollama sur le PC Linux dédié, modèle ≤ 8B.
- [ ] Dossier PDF : plan en 8–12 pages et répartition des sections.

## 6. Cohérence d'intégration, Kevin

- [x] Matrice de traçabilité : lignes SQLi, détournement du moteur et rotation de secrets passées à `PROUVÉ` (preuve référencée, `SopsSecretRotator` testée et essayée en réel le 21/10) ; investigation manuelle reste `À FAIRE`.
- [x] `docs/architecture/architecture.md` et `README.md` alignés avec la pile réellement déployée (fait le 21/10 : services renommés, `gateway` documenté comme embarquant le front, `vault` marqué non déployé).
- [x] Branches fusionnées sur `main` ; PR relues par le tech lead (`gh pr list --state open` vide le 21/10, toutes les branches `kevin/*` et `docs/*` supprimées après fusion).
- [x] Liste des écarts restants pour le jeudi, avec un responsable chacun, voir §8.

## 7. Critères de sortie du jalon

- [x] Le fil rouge tourne de bout en bout **depuis le PC Attaquant, à travers le WAF**, avec détection ML et reprise vérifiée par transaction (5/5 le 21/10, voir §2).
- [x] Au moins une attaque de compromission (SQLi) est **bloquée et visible dans le SIEM/Grafana** (12/12, règle CRS 942100, `02-pca-pra.md` §7), et maintenant aussi **traitée** côté remédiation : `RotateSecretAction`/`SopsSecretRotator` tourne le JWT et redémarre `auth`/`api`, transaction de test vérifiée après coup. La procédure d'investigation manuelle reste à développer (écart §8).
- [x] Le socle se lance en une commande depuis un clone neuf (Ansible) : `Deploy.ps1 -RenderEnv` essayé le 21/10 sur un clone vierge du dépôt (sans `.env` ni modèle ML) → `.env` rendu depuis SOPS, modèle entraîné, 17 conteneurs, services vérifiés, transaction de test réussie, front joignable via le WAF (HTTP 200). Essai fait par Kevin ; une relecture du README par un autre membre reste souhaitable.
- [x] 1ers tests de restauration consignés (RTO / RPO mesurés) : restauration à froid (§3) et S4 corruption BDD (§3, `02-pca-pra.md` §7).
- [x] Les écarts restants ont un responsable et une échéance jeudi, voir §8.

## 8. Écarts restants pour le jeudi

Vérifiés le 21/10 contre l'état réel du dépôt (code, Compose, docs), pas seulement contre les cases
cochées. Tout ce qui est listé ici est confirmé encore ouvert.

| Écart | Responsable | Échéance | Pourquoi ça bloque |
|---|---|---|---|
| Scénario de chaos du jeudi préparé (liste des pannes, ordre, critères de reprise) | François | Jeudi, avant les essais | Sans ce plan écrit, les ≥ 5 démos sans intervention ne sont pas pilotables |
| RAG ER6 : résiste sur `llama3.1:8b`, cède sur `llama3.2:3b` (1 seul scénario, 3 questions) ; modèle de démo et isolement du PC Linux à confirmer | François | Jeudi avant le chaos | Le modèle utilisé en démo doit être celui qui résiste, sinon ER6 n'est plus couvert |
| Clip chrono 60 s (scénario écrit, 1re prise sans coupe) | Gabriel | Jeudi, avant gel du code 17h | Rendu obligatoire |
| NIS2/DORA relu et relié aux essais réels du 21/10 | Gabriel | Jeudi matin | Rendu obligatoire (pilier Gouvernance) |
| Trame `Pres.pptx` et pitch | Gabriel | Jeudi | Jury vendredi |
| Dossier PDF (plan 8–12 p., répartition des sections) | François | Jeudi, avant gel du code | Rendu obligatoire |
| `ruff format` fonctionnel sur chaque poste ; réseau privé du binôme (hotspot ou box) confirmé opérationnel entre PC Attaquant et PC Hôte | Tous | Jeudi matin | Condition du chaos en réseau réel |

Non listés ici parce que déjà prouvés avec preuve référencée (voir §2, §3, §6) : fil rouge flood
depuis le PC Attaquant, SQLi bloqué/visible depuis le PC Attaquant, S4 (2 passages), restauration à froid, revue
docker-socket-proxy, alignement architecture/README, matrice de traçabilité et ateliers EBIOS 4/5.
