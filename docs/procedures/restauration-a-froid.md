# Restauration à froid, PROJECT RESILIENCE-ALPHA

## Objectif

Vérifier qu'un arrêt complet des conteneurs suivi d'un démarrage Compose unique rétablit
la pile et qu'une transaction fictive aboutit. La reprise n'est validée que si Compose
attend les services sains **et** si `scripts/check_transaction.sh` réussit.

Cette mesure est un essai de redémarrage à froid, pas un RTO d'incident : elle ne part
pas d'un début d'attaque ou d'une détection horodatée.

## Garde-fous

- Exécuter l'essai dans un projet Compose jetable dont les conteneurs, réseaux, volumes et
  ports publiés sont distincts de toute pile active. Contrôler ces noms et l'absence de
  ressources partagées avant l'arrêt.
- Utiliser des données et identifiants fictifs. Les archives PostgreSQL et le volume
  `jwt-secret-live` doivent être ceux du projet d'essai.
- Arrêter avec `docker compose stop` : cette commande conserve les conteneurs et volumes.
  Ne pas employer `down -v` ni un script de reset qui efface l'état.
- Si les fichiers Compose sont séparés, vérifier le modèle complet effectivement utilisé
  pour l'essai ; ne pas fusionner les fichiers bruts si leurs réseaux ou noms de projet
  ne sont pas compatibles.

## Exécution

Définir `COMPOSE_FILE` comme le fichier Compose effectif du projet isolé et `ENV_FILE`
comme son fichier d'environnement synthétique, puis exécuter :

```bash
export COMPOSE_FILE=/chemin/vers/compose-isole.yml
export ENV_FILE=/chemin/vers/.env-test
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" stop
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up --detach --wait
./scripts/check_transaction.sh
```

Avant et après `stop`, relever les noms/identifiants des volumes `postgres-data` et
`postgres-backups` ainsi que les archives présentes dans `/backups`. Confirmer qu'aucun
conteneur du projet ne tourne entre `stop` et `up`. Le seul démarrage est la commande
`up --detach --wait`; la dernière étape vérifie l'API puis une transaction de 100 centimes.
Consigner séparément la durée d'arrêt, celle de `up --wait` jusqu'à l'état sain et celle
de la sonde. Ne pas présenter le délai de démarrage ou le chronomètre de l'essai comme un
RTO complet.

## Preuve du 22/10/2026

Essai local jetable `coldrestore-b625c11f`, sur `main` (`00cf2af`), avec 18 conteneurs,
8 réseaux et 8 volumes tous nommés pour ce projet ; aucun réseau externe, aucun nom de
conteneur préexistant et seul le port `127.0.0.1:18080` publié. La découverte Alloy était
filtrée au projet d'essai. Les stacks actives `resilience-alpha` et `website` n'ont pas été
arrêtées ni modifiées. L'environnement, le fichier SOPS factice et le modèle ML entraîné
sur `ml/data/normal.csv` étaient temporaires et synthétiques.

- Sonde avant arrêt : `OK santé + transaction réglée (100 centimes)`.
- `docker compose stop` : 17 services arrêtés en **2,66 s** ; 18 conteneurs conservés,
  aucun conteneur du projet encore en cours d'exécution.
- `docker compose up --detach --wait` : les 17 services actifs sont revenus à leur état
  attendu en **26,72 s** (sains lorsqu'un healthcheck existe) ; le job de migration s'est
  terminé avec le code 0.
- Sonde après redémarrage : `scripts/check_transaction.sh` réussie en **0,52 s**.
- Du début de `stop` au succès de la sonde : **53,76 s** sur l'horloge murale, incluant
  l'intervalle entre les commandes. Ce chiffre décrit cet essai, pas un RTO d'incident.
- Horodatages UTC : `stop` 11:57:21.188–11:57:23.845 ; `up --wait`
  11:57:36.207–11:58:02.923 ; sonde 11:58:14.436–11:58:14.952.
- Les volumes `postgres-data` et `postgres-backups` ont conservé leurs noms et métadonnées
  de création. Les deux archives présentes avant l'arrêt sont toujours là après :
  `backup-20261022T115436.790111Z.dump` et `backup-20261022T115646.007172Z.dump` ;
  une nouvelle archive a été créée après le redémarrage :
  `backup-20261022T115744.436459Z.dump`.

Intervention humaine : oui, pour piloter l'essai ; la transaction de reprise a été vérifiée
automatiquement par le script. Les volumes de cette pile d'essai sont conservés après le
test ; les conteneurs et réseaux temporaires sont supprimés sans supprimer les volumes.
