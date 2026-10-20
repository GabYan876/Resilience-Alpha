# NIS2 / DORA — Resilience-Alpha

Statut : squelette. Responsable : Gabriel. Relecture : Antoine.

Principe du sujet : distinguer les exigences **pertinentes** pour une activité financière fictive des obligations qui **ne peuvent pas être démontrées** par un prototype de 4 jours.
Les références d'articles ci-dessous sont à **vérifier dans les textes** avant remise.

## 1. Applicabilité
Position retenue (décision du 19/10, à vérifier dans les textes) :
- **DORA applicable** : l'entité fictive exerce une activité de paiement, donc une entité financière.
- **NIS2 en complément** : DORA est lex specialis pour le secteur financier ; NIS2 sert de repère, notamment pour la chaîne d'approvisionnement.
- Classification « essentielle » / « importante » (NIS2) : sans objet si DORA prime ; à justifier en une phrase dans le dossier.

## 2. Exigences pertinentes et lien avec le démonstrateur

| Thème | Exigence (résumé) | Réf. à vérifier | Ce que fait le démonstrateur | Preuve | Couverture |
|---|---|---|---|---|---|
| Gestion des risques | Analyse de risques documentée | NIS2 art. 21 / DORA chap. II | EBIOS RM | `01-ebios-rm.md` | À DÉFINIR |
| Gestion des incidents | Détection, traitement, classification | NIS2 art. 21-23 / DORA chap. III | Détection ML + remédiation + événements JSON | Loki, dashboard Grafana | À DÉFINIR |
| Continuité | PCA/PRA, sauvegardes | NIS2 art. 21 / DORA chap. II | PCA/PRA, reset d'état | `02-pca-pra.md` | À DÉFINIR |
| Tests de résilience | Tests réguliers | DORA chap. IV | Chaos du jeudi, ≥ 5 démos | Journal des essais | À DÉFINIR |
| Cryptographie / secrets | Gestion des clés | NIS2 art. 21 | Vault ou SOPS, rotation | | À DÉFINIR |
| Contrôle d'accès | Moindre privilège | NIS2 art. 21 | docker-socket-proxy, réseaux internes | Compose | À DÉFINIR |
| Risque tiers | Dépendances et fournisseurs | DORA chap. V / NIS2 chaîne d'approvisionnement | Images et dépendances épinglées | À DÉFINIR | À DÉFINIR |

## 3. Non démontrable par un prototype de 4 jours

| Obligation | Pourquoi non démontrable | Ce que l'on recommanderait |
|---|---|---|
| Notification réglementaire d'incident (délais) | Pas d'autorité réelle ni d'incident réel | À DÉFINIR |
| Responsabilité de l'organe de direction | Pas de gouvernance d'entreprise réelle | |
| Audit des prestataires TIC / registre de contrats | Pas de contrats | |
| Tests avancés par tiers (type TLPT) | Hors délai et périmètre | |

## 4. Recommandations à la direction
Voir [06-pilotage-arbitrages.md](06-pilotage-arbitrages.md).
