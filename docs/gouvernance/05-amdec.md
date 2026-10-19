# AMDEC — priorisation des défaillances

Complète EBIOS : classe les défaillances par ordre de priorité (RPN) pour décider où investir en premier.
Les échelles et seuils ne sont pas inventés : l'équipe doit les fixer.

## Échelles (à décider en équipe)

| Critère | Échelle | Définition |
|---|---|---|
| Gravité (G) | À DÉFINIR (ex. 1–10) | |
| Fréquence (F) | À DÉFINIR | |
| Non-détection (D) | À DÉFINIR | Capacité du modèle ML / WAF / logs à voir la défaillance |
| RPN | À DÉFINIR | Formule à retenir : G × F × D ? (le cours cite aussi la « criticité » : à trancher) |
| Seuil d'action | À DÉFINIR | |

## Arborescence du système
Front → WAF → API métier → auth / BDD ; moteur de remédiation ; observabilité (Prometheus, Loki, Grafana) ; Vault/SOPS ; assistant RAG.

## Tableau

| Composant | Défaillance | Cause | Effet | G | F | D | RPN | Prévention | Repli / reprise |
|---|---|---|---|---|---|---|---|---|---|
| API métier | Saturation | Flood | Paiement indisponible | | | | | Détection ML, rate limit | Blocage IP + restart |
| BDD | Fuite de données | SQLi | Atteinte à la confidentialité | | | | | WAF, requêtes paramétrées | Rotation secrets |
| Moteur de remédiation | Faux positif | Modèle ML mal calibré | Coupure inutile | | | | | Seuil à calibrer | Retour arrière |
| Prometheus / Loki | Indisponible | Manque de RAM | Détection aveugle | | | | | `mem_limit` | Restart |
| Vault / SOPS | Secret exposé | Mauvaise config | Compromission | | | | | | Rotation |
