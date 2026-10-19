# Matrice de traçabilité

Elle prouve le lien avec le démonstrateur : **risque → mesure → preuve → exigence**. À compléter au fil de la semaine par toute l'équipe ; Kevin la tient à jour.

| Risque (EBIOS) | Scénario | Mesure technique | Composant / chemin | Preuve vérifiable | Exigence NIS2/DORA | Statut |
|---|---|---|---|---|---|---|
| ER1 Paiement indisponible | Flood (SO1) | Détection ML → blocage IP + restart | `services/remediation/` | Événements JSON dans Loki, démo n°… | Gestion d'incident, tests | À FAIRE |
| ER1 | Flood | Vérif. post-reprise (API + transaction test) | `RecoveryVerifier` | Log « incident clos » | Continuité | À FAIRE |
| ER2 Exfiltration | SQLi (SO2) | WAF bloque | WAF (Hugo) | Règle déclenchée dans les logs | Cybersécurité | À FAIRE |
| ER2 | SQLi | Rotation de secrets | `RotateSecretAction` | À DÉFINIR | Cryptographie, incident | À FAIRE |
| ER4 Détournement du moteur | Abus du `docker.sock` | docker-socket-proxy, pas d'admin exposée | Compose | Revue de la config | Contrôle d'accès | À FAIRE |
| | | | | | | |

Statut : À FAIRE / EN COURS / PROUVÉ (preuve liée) / NON DÉMONTRABLE (expliqué dans `03-nis2-dora.md`).

Règle : une ligne n'est « PROUVÉ » que si la preuve existe et est référencée.
