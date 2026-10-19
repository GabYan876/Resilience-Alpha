# Matrice de traçabilité

Elle prouve le lien avec le démonstrateur : **risque → mesure → preuve → exigence**. À compléter au fil de la semaine par toute l'équipe ; Kevin la tient à jour.

| Risque (EBIOS) | Scénario | Mesure technique | Composant / chemin | Preuve vérifiable | Exigence NIS2/DORA | Statut |
|---|---|---|---|---|---|---|
| ER1 Paiement indisponible | Flood (SO1) | Détection ML → blocage IP + restart | `services/remediation/`, `ml/` | Événements JSON dans Loki, démo n°… | Gestion d'incident (DORA chap. III), tests | EN COURS (restart + tests unitaires ; `WafIpBlocker` et `MlDetector` à faire) |
| ER1 | Flood | Vérif. post-reprise (API + transaction test) | `HealthAndProbeVerifier` (`services/remediation/app/application/verifier.py`) | Événement `incident.resolved` (Loki) ; tests `test_policy_verifier.py` | Continuité | EN COURS (pas encore de démo) |
| ER1 | Crash conteneur (S3) | Health check périodique → restart + vérif | Watcher à créer | À DÉFINIR | Continuité | À FAIRE |
| ER2 Exfiltration | SQLi (SO2) | WAF bloque | WAF (Hugo) | Règle déclenchée dans les logs | Cybersécurité (art. à citer) | À FAIRE |
| ER2 | SQLi | Rotation de secrets | `RotateSecretAction` | À DÉFINIR | Cryptographie, incident | EN COURS (action codée et testée, `VaultSecretRotator` à faire) |
| ER2 | SQLi | Investigation manuelle (assumée) | `docs/procedures/` | Procédure + journal d'investigation | Gestion d'incident | À FAIRE |
| ER3 Altération de transactions | Corruption BDD (S4) | Restauration de sauvegarde | `RestoreDatabaseAction` à créer, script de reset | À DÉFINIR (RPO mesuré) | Continuité, sauvegardes | À FAIRE |
| ER4 Détournement du moteur | Abus du `docker.sock` | docker-socket-proxy, pas d'admin exposée, token sur `POST /incidents` | Compose, `services/remediation/app/adapters/docker_proxy.py` | Revue de la config | Contrôle d'accès | EN COURS (client via proxy codé ; Compose à faire) |
| ER5 Faux positif / contournement ML | Coupure inutile | Seuil calibré, retour arrière, vérif avant clôture | `services/remediation/`, `ml/` | Taux de faux positifs sur les essais | Gestion d'incident, tests | À FAIRE |
| ER6 Abus du RAG | Injection de prompt | RAG isolé, lecture seule, sans droits | `services/rag-assistant/`, réseau `rag` | Revue de la config | Contrôle d'accès | À FAIRE |

Statut : À FAIRE / EN COURS / PROUVÉ (preuve liée) / NON DÉMONTRABLE (expliqué dans `03-nis2-dora.md`).

Règle : une ligne n'est « PROUVÉ » que si la preuve existe et est référencée.
