# Service `auth` — authentification client et back-office

Service FastAPI de la plateforme de paiement **fictive**. Deux parcours distincts :

- **client** (`/auth/register`, `/auth/login`) : e-mail + mot de passe, jeton JWT lu par l'API métier ;
- **back-office** (`/auth/admin/*`, consigne additionnelle 1) : identifiant → visage (agent caméra du PC Hôte) → mot de passe, puis habilitations. Conception : [`docs/consigne-additionnelle-1.md`](../../docs/consigne-additionnelle-1.md).

Architecture hexagonale : `domain/` (modèles, erreurs, ports `FaceVerifier`, `CameraControl`, `StatusLed`, `LockoutStore`, `RoleStore`, `AccessJournal`), `application/` (`BackOfficeLogin`, `BackOfficeAdmin`), `adapters/` (agent caméra HTTP, LED HTTP, JWT, stockages en mémoire), `api/` (routes, schémas), `main.py` (composition root).

## API client

Ces routes servent l'inscription et la connexion des clients. Les exemples utilisent uniquement
des données fictives. Les e-mails sont convertis en minuscules avant traitement.

| Méthode et chemin | Corps | Succès | Erreurs métier |
|---|---|---|---|
| `POST /auth/register` | `name`, `email`, `number`, `password` | `200` : JWT et profil | `409` e-mail ou numéro déjà utilisé |
| `POST /auth/login` | `email`, `password` | `200` : JWT et profil | `401` e-mail inconnu ou mot de passe incorrect |
| `GET /health` | — | `200` si la base répond | `503` si la base est indisponible |
| `GET /metrics` | — | Métriques Prometheus au format texte | — |

`POST /auth/register` attend un nom de 1 à 120 caractères, un e-mail de 1 à 320 caractères
au format `local@domaine`, un numéro de 10 à 15 chiffres avec `+` initial facultatif, et un
mot de passe de 8 à 128 caractères. `POST /auth/login` attend un e-mail au même format et un
mot de passe de 1 à 128 caractères.

Exemple d'inscription :

```json
{
  "name": "Alice Martin",
  "email": "alice@example.test",
  "number": "0612345678",
  "password": "mot-de-passe-fictif"
}
```

Les deux routes d'authentification renvoient le même format :

```json
{
  "token": "<JWT client>",
  "resp": {
    "_id": "<UUID>",
    "name": "Alice Martin",
    "email": "alice@example.test",
    "number": "0612345678",
    "iban": "<IBAN fictif>",
    "balance_cents": 100000
  }
}
```

Le profil ne contient pas le mot de passe ni son hachage. Une inscription attribue le solde
fictif défini par `WELCOME_BALANCE_CENTS` (100 000 centimes par défaut). Un champ invalide ou
manquant renvoie `422` sous la forme `{"error": "champ invalide : <champ>"}` ; ce message ne
répète pas la saisie. Une connexion refusée renvoie `401`
`{"detail": "e-mail ou mot de passe incorrect"}`. Les jetons client sont des JWT HS256 avec
`sub` (UUID utilisateur), `iat` et `exp` ; leur durée est `JWT_TTL_SECONDS` (7 200 secondes
par défaut). L'API métier partage `JWT_SECRET` pour les vérifier.

## Connexion du back-office

| Route | Rôle | Réponses |
|---|---|---|
| `POST /auth/admin/identify` `{identifier}` | Vérifie le visage via l'agent caméra | 200 `{"status":"face_recognized"}` ; 403 visage non reconnu ; 423 identifiant bloqué (`Retry-After`) ; 503 caméra ou agent indisponible (échec fermé) |
| `POST /auth/admin/login` `{identifier, password}` | Mot de passe, après un visage reconnu | 200 `{token, identifier, name, role}` ; 401 mauvais mot de passe ; 403 visage non vérifié ou compte sans rôle (`detail.reason: "no_role"`) ; 423 bloqué |

Deux échecs cumulés de reconnaissance faciale et/ou de mot de passe bloquent l'identifiant
5 minutes (`Retry-After` en secondes) ; blocage **par identifiant**, pas par IP. La reconnaissance
doit précéder chaque tentative de mot de passe, est à usage unique et expire après 2 minutes.
Une panne caméra/agent échoue fermé et ne compte pas comme échec. Un compte sans rôle est refusé
même avec un visage et un mot de passe valides, sans échec compté.

## Habilitations et administration

Le jeton de back-office a l'audience `backoffice` et dure 15 min (`ADMIN_TOKEN_TTL_SECONDS`). L'API métier le refuse, et ces routes refusent un jeton client. Le rôle n'est pas dans le jeton : il est relu à chaque requête, un retrait prend effet immédiatement.

| Route | Rôle requis | Effet |
|---|---|---|
| `GET /auth/admin/me` | `admin`, `operator` | Rôle de la session |
| `GET /auth/admin/habilitations` | `admin`, `operator` | Liste des habilitations |
| `POST /auth/admin/habilitations` `{identifier, role}` | `admin` | Attribue `admin` ou `operator` (404 si compte inconnu) |
| `POST /auth/admin/habilitations/revoke` `{identifier}` | `admin` | Retire un rôle (409 si c'est le sien) |
| `GET /auth/admin/lockouts` | `admin`, `operator` | Identifiants bloqués |
| `POST /auth/admin/lockouts/unlock` `{identifier}` | `admin` | Débloque un identifiant |
| `GET /auth/admin/journal` | `admin`, `operator` | Journal d'accès (200 dernières lignes, en mémoire) |

GET/POST uniquement : le CRS du WAF refuse PUT et DELETE par défaut. Un `operator` est en lecture seule (403 + `auth.admin.forbidden`). L'enrôlement et la révocation des visages restent en ligne de commande sur le PC Hôte : le gabarit biométrique ne transite jamais par le réseau.

## Événements (Loki)

JSON structuré (`service`, `trace_id`, `event`, `at`, `data`). Pour les événements de connexion
du back-office, l'identifiant n'apparaît dans Loki que sous forme d'empreinte. Les événements
client incluent `auth.registered`, `auth.login_succeeded` et `auth.login_failed`.

Événements back-office : `auth.face.recognized`, `auth.face.rejected`,
`auth.face.unavailable`, `auth.password.failed`, `auth.password.refused_no_face`,
`auth.locked`, `auth.locked.refused`, `auth.login.succeeded`,
`auth.access.denied_no_role`, `auth.admin.role_granted`, `auth.admin.role_revoked`,
`auth.admin.unlocked`, `auth.admin.forbidden`, `auth.led.unavailable`,
`auth.camera.stop_failed`.

## Configuration

| Variable | Rôle |
|---|---|
| `DATABASE_URL`, `JWT_SECRET` / `JWT_SECRET_FILE` | Base et secret JWT partagé avec l'API (≥ 32 caractères, jamais en clair dans le dépôt) |
| `JWT_TTL_SECONDS` | Durée du JWT client (7 200 secondes par défaut) |
| `HOST_AGENT_URL`, `HOST_AGENT_TOKEN` | Agent caméra natif. Absent : le back-office échoue fermé (503) |
| `LED_URL`, `LED_TOKEN` | ESP32 (LED bicolore, requêtes signées HMAC). Absent : pas de retour visuel, accès inchangé |
| `BACKOFFICE_ADMINS` | Premiers `admin`, séparés par des virgules. **Vide : personne n'entre** (échec fermé) |
| `ADMIN_TOKEN_TTL_SECONDS` | Durée de la session de back-office (900 par défaut) |

## Limites connues

- Habilitations, blocage et journal sont **en mémoire** : perdus au redémarrage de `auth` (les habilitations repartent de `BACKOFFICE_ADMINS`). Les tables `roles` et `login_lockouts` (lot L1) pourront les remplacer sans changer les cas d'usage.
- Pas de détection de vivacité (une photo peut tromper la caméra).
- Habilitations testées avec des doubles, pas encore jouées sur le PC Hôte avec la vraie caméra.

## Tester

```bash
cd services/auth
pip install -r requirements.txt pytest anyio
python -m pytest -q   # 63 tests
ruff check . && ruff format --check .
```
