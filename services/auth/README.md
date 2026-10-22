# Service `auth`, authentification client et back-office

Service FastAPI de la plateforme de paiement **fictive**. Deux parcours distincts :

- **client** (`/auth/register`, `/auth/login`) : e-mail + mot de passe, jeton JWT lu par l'API métier ;
- **back-office** (`/auth/admin/*`, consigne additionnelle 1) : identifiant → visage (agent caméra du PC Hôte) → mot de passe, puis habilitations. Conception : [`docs/consigne-additionnelle-1.md`](../../docs/consigne-additionnelle-1.md).

Architecture hexagonale : `domain/` (modèles, erreurs, ports `FaceVerifier`, `CameraControl`, `StatusLed`, `LockoutStore`, `RoleStore`, `AccessJournal`), `application/` (`BackOfficeLogin`, `BackOfficeAdmin`), `adapters/` (agent caméra HTTP, LED HTTP, JWT, stockages en mémoire), `api/` (routes, schémas), `main.py` (composition root).

## Connexion du back-office

| Route | Rôle | Réponses |
|---|---|---|
| `POST /auth/admin/identify` | Vérifie le visage via l'agent caméra | 200 `{status}` ; 403 visage non reconnu ; 423 identifiant bloqué (`Retry-After`) ; 503 caméra ou agent indisponible (échec fermé) |
| `POST /auth/admin/login` | Mot de passe, après un visage reconnu | 200 `{token, identifier, name, role}` ; 401 mauvais mot de passe ; 403 visage non vérifié **ou** compte sans rôle (`reason: "no_role"`) ; 423 bloqué |

Un mot de passe faux permet une reprise, puis l'identifiant est bloqué 5 min (blocage **par identifiant**, pas par IP). Un compte sans rôle est refusé même avec un visage et un mot de passe valides, sans échec compté.

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

JSON structuré (`service`, `trace_id`, `event`). L'identifiant n'apparaît que sous forme d'empreinte.

`auth.face.recognized`, `auth.face.rejected`, `auth.face.unavailable`, `auth.password.failed`, `auth.password.refused_no_face`, `auth.locked`, `auth.locked.refused`, `auth.login.succeeded`, `auth.access.denied_no_role`, `auth.admin.role_granted`, `auth.admin.role_revoked`, `auth.admin.unlocked`, `auth.admin.forbidden`, `auth.led.unavailable`.

## Configuration

| Variable | Rôle |
|---|---|
| `DATABASE_URL`, `JWT_SECRET` / `JWT_SECRET_FILE` | Base et secret JWT (≥ 32 caractères, jamais en clair dans le dépôt) |
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
