# NIS2 / DORA — Resilience-Alpha

Statut : première version du 20/10 (colonnes « Couverture » remplies d'après le dépôt, à relire). Responsable : Gabriel. Relecture : Antoine.

Principe du sujet : distinguer les exigences **pertinentes** pour une activité financière fictive des obligations qui **ne peuvent pas être démontrées** par un prototype de 4 jours.
Les références d'articles ci-dessous sont à **vérifier dans les textes** avant remise.

## 1. Applicabilité
Position retenue (décision du 19/10, à vérifier dans les textes) :
- **DORA applicable** : l'entité fictive exerce une activité de paiement, donc une entité financière.
- **NIS2 en complément** : DORA est lex specialis pour le secteur financier ; NIS2 sert de repère, notamment pour la chaîne d'approvisionnement.
- Classification « essentielle » / « importante » (NIS2) : sans objet si DORA prime ; à justifier en une phrase dans le dossier.

## 2. Exigences pertinentes et lien avec le démonstrateur

Couverture : **Couverte** (preuve dans le dépôt ou mesurée), **Partielle** (une partie seulement, écart nommé), **Non couverte** (rien de démontrable aujourd'hui).

| Thème | Exigence (résumé) | Réf. à vérifier | Ce que fait le démonstrateur | Preuve | Couverture |
|---|---|---|---|---|---|
| Gestion des risques | Analyse de risques documentée | NIS2 art. 21 / DORA chap. II | EBIOS RM | `01-ebios-rm.md` | Partielle : ateliers 1 à 5 rédigés le 20/10, à valider par Antoine |
| Gestion des incidents | Détection, traitement, classification | NIS2 art. 21-23 / DORA chap. III | Détection ML + remédiation + événements JSON | Loki, dashboard Grafana, `scripts/demo_loop.py` | Couverte : 5/5 reprises, événements `incident.*` horodatés. Pas de classification de gravité ni de notification (voir § 3) |
| Continuité | PCA/PRA, sauvegardes | NIS2 art. 21 / DORA chap. II | PCA/PRA, reset d'état | `02-pca-pra.md`, `scripts/reset_demo.sh` | Partielle : reprise de S1 et S3 prouvée ; sauvegarde/restauration de la BDD (S4) absente |
| Tests de résilience | Tests réguliers | DORA chap. IV | Chaos du jeudi, ≥ 5 démos | Journal des essais (`02-pca-pra.md` § 7) | Partielle : 5 démos flood et 1 crash joués ; chaos du jeudi à venir |
| Cryptographie / secrets | Gestion des clés | NIS2 art. 21 | Vault ou SOPS, rotation | `RotateSecretAction` (codée, testée) ; `infra/secrets/` vide | Non couverte : secrets dans `.env`, pas de Vault/SOPS ni de `VaultSecretRotator` |
| Contrôle d'accès | Moindre privilège | NIS2 art. 21 | docker-socket-proxy, réseaux internes, jeton sur `POST /incidents`, `cap_drop` sur le WAF | `infra/compose/` | Couverte : seul le WAF publie un port ; moteur sans accès direct à `docker.sock` |
| Risque tiers | Dépendances et fournisseurs | DORA chap. V / NIS2 chaîne d'approvisionnement | Images et dépendances épinglées | Images à version fixe, WAF par digest, `requirements.txt` en `==`, `package-lock.json` | Partielle : pas de scan de vulnérabilités ni de SBOM |

## 3. Non démontrable par un prototype de 4 jours

| Obligation | Pourquoi non démontrable | Ce que l'on recommanderait |
|---|---|---|
| Notification réglementaire d'incident (délais) | Pas d'autorité réelle ni d'incident réel | Décrire dans la procédure : classer la gravité, alerter dans les délais réglementaires, conserver les événements `incident.*` comme base du rapport |
| Responsabilité de l'organe de direction | Pas de gouvernance d'entreprise réelle | Faire valider les risques résiduels et le PCA/PRA par la direction (ici, le jury joue ce rôle) |
| Audit des prestataires TIC / registre de contrats | Pas de contrats | Tenir un registre des images et dépendances tierces (déjà épinglées) et prévoir des clauses de sortie |
| Tests avancés par tiers (type TLPT) | Hors délai et périmètre | Faire tester par un tiers indépendant ; ici l'attaque est jouée par notre propre équipe |

## 4. Recommandations à la direction
Voir [06-pilotage-arbitrages.md](06-pilotage-arbitrages.md).
