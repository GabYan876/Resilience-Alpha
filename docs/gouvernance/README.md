# Gouvernance, PROJECT RESILIENCE-ALPHA

Pilier 5 du sujet (§3.5) : **10 pts / 70**, « Risques, PCA/PRA et NIS2/DORA reliés au démonstrateur ».
Un rapport de conformité générique, sans lien avec l'architecture et les essais, ne rapporte rien.

## Documents

| Fichier | Contenu | Responsable | Contributeurs |
|---|---|---|---|
| [01-ebios-rm.md](01-ebios-rm.md) | Analyse de risques EBIOS RM (5 ateliers) | Antoine | Hugo (infra), Kevin (remédiation) |
| [02-pca-pra.md](02-pca-pra.md) | PCA/PRA : scénarios, RTO/RPO, responsabilités, risques résiduels | Antoine | Hugo, Kevin |
| [03-nis2-dora.md](03-nis2-dora.md) | NIS2/DORA : exigences pertinentes vs non démontrables | Gabriel | Antoine |
| [04-matrice-tracabilite.md](04-matrice-tracabilite.md) | Risque → mesure → preuve → exigence | Kevin | toute l'équipe |
| [05-amdec.md](05-amdec.md) | Priorisation des défaillances (gravité, fréquence, non-détection, RPN) | Antoine | Kevin |
| [06-pilotage-arbitrages.md](06-pilotage-arbitrages.md) | Comitologie, arbitrages, recommandations à la direction | Gabriel | Kevin |

Le Dossier PDF (8–12 p.) est assemblé par François à partir de ces sources.

## Règles

- Tout énoncé doit pointer vers un **élément vérifiable** : fichier du dépôt, log Loki, événement de remédiation, résultat de test, capture de démo.
- Les valeurs marquées `À DÉFINIR` ne sont pas inventées : à décider en équipe ou à mesurer lors des essais.
- Données 100 % fictives. Aucun secret dans ces documents.
- Ce qu'un prototype de 4 jours ne peut pas démontrer est écrit **explicitement** (honnêteté valorisée par le sujet).

## Jalons gouvernance

| Date | Livrable |
|---|---|
| Lun 19/10 | EBIOS : ateliers 1 à 3 validés avec l'architecture |
| Mar 20/10 | EBIOS atelier 4-5 (brouillon), 1re version de la matrice de traçabilité |
| Mer 21/10 | PCA/PRA + NIS2/DORA rédigés, RTO provisoires |
| Jeu 22/10 | RTO/RPO **mesurés** lors du chaos et des ≥ 5 démos, matrice complétée ; gel 17h |
| Jeu 22/10 | Remise avant 23h59 |
