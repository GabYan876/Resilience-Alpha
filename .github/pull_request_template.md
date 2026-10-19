## Résumé

<!-- Ce que fait la PR, en quelques lignes. -->

## Points d'attention pour la relecture

<!-- Ce que le relecteur doit regarder en priorité, limites connues. -->

## Tests

<!-- Ce qui est testé (commande + résultat) et ce qui ne l'est pas. -->

## Checklist

- [ ] Commits en Conventional Commits, en français, sans co-auteur
- [ ] Aucun secret ni donnée réelle (`.env` non commité)
- [ ] Respect de l'architecture en couches (pas d'import d'infrastructure dans `domain/` ou `application/`)
- [ ] Impact RAM (`mem_limit`), exposition réseau et droits évalués si un composant est ajouté
- [ ] Documentation mise à jour (README, `docs/`, matrice de traçabilité si concerné)
- [ ] Code compris et explicable par son auteur
