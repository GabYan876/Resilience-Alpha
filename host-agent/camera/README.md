# Agent hôte caméra (consigne additionnelle 1)

Service Python **natif Windows, hors Docker** : Docker Desktop ne voit pas la caméra USB. Il ouvre la
caméra, compare le visage au gabarit de l'identifiant (1:1, OpenCV YuNet + SFace) et répond à `auth`.
Conception : [`docs/consigne-additionnelle-1.md`](../../docs/consigne-additionnelle-1.md).

## Mise en route (PC Hôte)

```powershell
cd host-agent\camera
python -m venv .venv ; .\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python scripts\download_models.py         # 2 modèles ONNX, empreintes vérifiées
.\.venv\Scripts\python -m app.cli genkey data\template.key  # une seule fois ; sauvegarder via SOPS
# Facultatif : sans ces deux variables, run.ps1 relit HOST_AGENT_TOKEN dans le .env racine (écrit par
# scripts/render_env.sh) et prend data\template.key s'il existe.
$env:AGENT_TOKEN = '<32+ caractères, identique à HOST_AGENT_TOKEN du .env>'
$env:TEMPLATE_KEY_FILE = 'data\template.key'
.\.venv\Scripts\python -m app.cli enroll admin@resilience.local   # membre consentant, face à la caméra
.\run.ps1                                                  # écoute sur le port 8765
```

Dans le `.env` racine : `HOST_AGENT_URL=http://host.docker.internal:8765` et `HOST_AGENT_TOKEN=...`,
puis redémarrer `auth`. Sans ces variables la connexion du back-office reste fermée.

## Contrat HTTP (jeton `Authorization: Bearer`)

| Route | Effet |
|---|---|
| `POST /camera/start` | allume la caméra (503 si introuvable) |
| `POST /camera/stop` | l'éteint (voyant éteint) |
| `POST /verify` `{"identifier"}` | `{"match": true/false}` ; exactement un visage requis ; 503 si la caméra n'est pas démarrée |

L'enrôlement et la révocation sont en **ligne de commande locale uniquement** (pas de route HTTP) :
`python -m app.cli enroll|revoke|check <identifiant>`.

## Seuil de similarité

Valeur de départ **0,363** (recommandation d'OpenCV pour SFace). Mesure du 22/10, caméra USB : membre
enrôlé 0,752 à 0,806 (10 mesures), autre membre consentant 0,023 à 0,094 (10 mesures). Valeur conservée.
Échantillon minimal (1 imposteur) : à ne pas présenter comme un taux d'erreur.
`python -m app.cli check <identifiant>` affiche la similarité d'une image : relever des valeurs
visage conforme / autre membre, puis fixer `FACE_THRESHOLD` et consigner les taux dans la doc.

## Sécurité et limites

- Seul le **gabarit** (128 valeurs) est stocké, chiffré (Fernet) ; jamais d'image. `models/*.onnx`,
  `data/` et `*.tpl` sont ignorés par Git. Seuls des membres consentants sont enrôlés.
- **Pas de détection de vivacité** : une photo ou un écran peuvent tromper la reconnaissance
  (limite connue à assumer, scénario d'attaque de François).
- Écouter sur une interface joignable par Docker, mais **restreindre le port 8765 par le pare-feu
  Windows** (sous-réseau Docker/hotspot uniquement) ; ne jamais le publier ailleurs.
- Tests : `.\.venv\Scripts\python -m pytest` (doubles ; le test des modèles réels est ignoré si
  les modèles manquent).
