# Scénario de chaos — jeudi 22/10

Responsable : François (attaque + Red Team). Rejoué avec Kevin (remédiation). Objectif du
jalon : **≥ 5 démonstrations consécutives sans intervention humaine**, chacune prouvée par une
transaction de test réussie, à travers le WAF, depuis le PC Attaquant vers le PC Hôte.

Ce document fige la liste des pannes injectées, leur ordre et les critères de reprise. Les
mesures (RTO, RPO, issue) sont consignées dans [`../gouvernance/02-pca-pra.md`](../gouvernance/02-pca-pra.md) §7.

## Périmètre et garde-fous

- Toute attaque part **uniquement** du PC Attaquant vers le PC Hôte du consortium. Jamais le
  réseau du campus, un autre groupe ni Internet.
- Les scripts `attack/flood_http.py` et `attack/sqli_injection.py` refusent toute cible hors de
  leur liste `ALLOWED_HOSTS` (`127.0.0.1`, `localhost`, `192.168.137.1`, `192.168.1.140`) sauf
  confirmation explicite par `--yes-i-know-the-target`. **Ne pas utiliser `--yes-i-know-the-target`**
  pendant le chaos : c'est le garde-fou qui prouve qu'on ne sort pas du périmètre.
- Cible réelle = le WAF du PC Hôte. Régler `WAF_BIND_HOST` sur l'IP réelle du PC Hôte dans son
  `.env` **avant** chaque essai (le WAF refuse de démarrer si l'IP n'existe pas sur la machine —
  constat du 21/10 : `192.168.137.1` fixé alors que seul `192.168.1.140` existait).

## Prérequis avant le premier passage

1. Pile complète déployée sur le PC Hôte en une commande, tous les conteneurs sains.
2. Ollama joignable : `OLLAMA_URL=http://192.168.137.157:11434` dans le `.env` du PC Hôte
   (Ollama tourne sur le PC Linux de François ; `host.docker.internal` ne convient pas sur le
   PC Hôte, il y pointerait sur Windows où Ollama n'est pas installé).
3. Modèle ML entraîné sur chaque poste qui exécute le détecteur : `ml/models/isolation_forest.joblib`
   présent (le `.joblib` n'est pas versionné ; `docker compose ... exec anomaly-detector python -m
   app.cli train` le régénère depuis `ml/data/normal.csv`).
4. Trafic de fond actif pour mesurer les faux positifs : `python scripts/background_traffic.py`
   (trafic légitime continu, sert de référence « normale » au détecteur).

## Pannes injectées — ordre et critères de reprise

Le RTO se mesure du **début d'attaque** (journal horodaté du script) à l'événement
`incident.resolved` dans Loki. Décomposition : délai de détection (`incident.detected`) + temps
de remédiation.

### S1 — Flood HTTP (disponibilité)

- **Injection** : `python attack/flood_http.py --base-url http://<PC_HOTE>:8080 --duration 30`.
- **Attendu** : le détecteur ML signale une anomalie (hausse `request_rate` / `latency_p95_s`),
  `DecisionPolicy` choisit blocage du compte source + redémarrage, pas une rotation de secret.
- **Critère de reprise** : `incident.resolved`, API saine **et** transaction de sonde réussie.
- **Distinction à prouver** : disponibilité, donc blocage + restart — jamais de rotation de
  secret.

### S2 — Injection SQL (compromission)

- **Injection** : `python attack/sqli_injection.py --base-url http://<PC_HOTE>:8080`.
- **Déclenchement de l'incident — manuel, pas automatique.** Aucun détecteur n'émet
  `IncidentKind.COMPROMISE` : le SQLi seul ne lance rien. On déclenche l'incident à la main par
  `POST /incidents kind=compromise` sur le moteur de remédiation, après le SQLi. C'est ce
  `POST` qui enclenche `DecisionPolicy` → `SopsSecretRotator` (rotation de secret) + redémarrage
  de `auth`/`api`, distinct du blocage de source + restart de la branche `AVAILABILITY`.
- **Critère de reprise** : `incident.resolved`, API saine et transaction de sonde réussie après
  rotation.
- **Limites assumées** : (1) la détection automatique de compromission n'est pas développée
  (hors périmètre, arbitrage `06-pilotage-arbitrages.md`), donc S2 n'est pas « sans intervention
  humaine » comme S1/S4 — le déclenchement est manuel ; (2) l'investigation manuelle de
  compromission n'est pas automatisée. Les deux sont consignées dans « Limites connues » du
  README et au §2 de `02-pca-pra.md`.

### S4 — Corruption BDD (données)

- **Injection** : corruption directe de la base (procédure `s4-corruption-bdd.md`).
- **Attendu** : incident `DATABASE_CORRUPTION` → `RestoreDatabaseAction` (dernière archive
  valide antérieure à la détection, moins 15 s de marge) + redémarrage API.
- **Critère de reprise** : `incident.resolved`, transaction de sonde réussie ; RTO et RPO
  consignés. Référence historique du 21/10 : RTO 3,24–3,79 s et RPO 13,56–59,32 s. Rejeu
  isolé du 22/10 : 1/1, RTO 6,38 s de `Tc` à `incident.resolved`, RPO 108,78 s ; détail et
  limites du périmètre dans [`s4-corruption-bdd.md`](s4-corruption-bdd.md).

## Boucle des 5 passages sans intervention

```
python scripts/demo_loop.py --runs 5
```

`demo_loop.py` enchaîne reset d'état (`scripts/reset_demo.sh`) → flood → attente de l'issue,
par défaut contre `WAF_BIND_HOST` du `.env`. Critère de sortie du jalon : 5/5 avec
`incident.resolved` et transaction de test réussie à chaque passage (référence 21/10 : 5/5,
RTO 5,4–7,9 s).

Chaque passage ajoute une ligne au tableau d'essais de `02-pca-pra.md` §7 : date, scénario,
issue, RTO observé, intervention humaine (doit rester « Non »), lien vers le log Loki.

## Après le chaos

- Re-mesurer les faux positifs ML sous trafic de fond : aucun `incident.*` parasite attendu.
- Consigner honnêtement les écarts restants dans « Limites connues » du README et au §8 de
  `validation-jalon-22-10.md`.
