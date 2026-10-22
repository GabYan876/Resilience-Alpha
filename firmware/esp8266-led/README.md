# Firmware ESP8266 / ESP32 : LED bicolore d'état

Retour visuel de l'authentification du back-office (consigne additionnelle 1, voir
[`docs/consigne-additionnelle-1.md`](../../docs/consigne-additionnelle-1.md)). Le service `auth` appelle
la carte par le WiFi du point d'accès ; l'accès au back-office **ne dépend pas** de la LED (échec journalisé).

Deux cartes sont gérées par le même code, via les gardes `ARDUINO_ARCH_ESP32` de `src/main.cpp` :
env `d1_mini` (ESP8266, HMAC BearSSL) et env `esp32dev` (ESP32, HMAC mbedTLS). Seules les
bibliothèques réseau, le calcul du HMAC et les broches diffèrent ; le contrat HTTP est identique.

## Contrat

`POST http://<ip-esp>/led`, requête **signée**, corps JSON :

```json
{"mode": "off | green_blink | green_solid | red_blink | red_solid"}
```

| Mode | LED | Durée (gérée **dans le firmware**) |
|---|---|---|
| `off` | éteinte | — |
| `green_blink` | vert clignotant | jusqu'au mode suivant |
| `green_solid` | vert fixe | 30 s, puis éteinte |
| `red_blink` | rouge clignotant | 10 clignotements, puis éteinte |
| `red_solid` | rouge fixe | 30 s, puis éteinte |

Signature : en-têtes `X-Counter` (entier strictement croissant ; le client `auth` envoie l'horloge en millisecondes)
et `X-Signature` = HMAC-SHA256 en hexadécimal minuscule, avec `LED_TOKEN` comme clé, du texte
`<X-Counter>.<corps exact>`. Le secret ne circule jamais ; l'ESP8266 refuse un compteur déjà vu (rejeu).

Réponses : `200` mode appliqué, `400` mode invalide, `401` signature absente ou fausse, `403` IP source différente
de `ALLOWED_HOST_IP`, `409` compteur déjà vu (rejeu). Le client côté `auth` est `HttpStatusLed` (`services/auth/app/adapters/esp_led.py`).

Les durées étant dans le firmware, la LED reste cohérente (et s'éteint) si le réseau coupe en cours de séquence.

## Matériel et câblage

LED rouge et LED verte (ou bicolore rouge/vert à **cathode commune**), 2 résistances de 220 Ω.

ESP8266, carte D1 mini :

| Broche | GPIO | Branchement |
|---|---|---|
| D1 | 5 | anode verte, via 220 Ω |
| D2 | 4 | anode rouge, via 220 Ω |
| GND | — | cathode commune |

ESP32, carte DevKit (puce ESP32-D0WD-V3) :

| Broche | GPIO | Branchement |
|---|---|---|
| G25 | 25 | anode verte, via 220 Ω |
| G26 | 26 | anode rouge, via 220 Ω |
| GND | — | cathode commune |

Les GPIO 6 à 11 sont câblés à la flash interne de l'ESP32 et les GPIO 0, 2, 12, 15 servent au boot :
aucun ne doit porter la LED. 25 et 26 sont libres sur toutes les cartes ESP32 classiques.

## Installation

1. Ouvrir `firmware/esp8266-led/` dans **CLion** (plugin PlatformIO) ; en ligne de commande :
   `pio run -e esp32dev` (ou `-e d1_mini`). Sans `-e`, les deux cartes sont construites.
2. Copier `include/secrets.h.example` en `include/secrets.h` (ignoré par Git) et renseigner le WiFi
   `RESILIENCE-G<n>`, le secret `LED_TOKEN` et `ALLOWED_HOST_IP` (IP du PC Hôte, `192.168.137.1` avec le hotspot Windows).
3. Flasher : `pio run -e esp32dev -t upload`. Moniteur série à 115200 bauds (`pio device monitor`) :
   la carte annonce son adresse une fois connectée, ligne `IP <adresse>`, à reporter dans `LED_URL`.
4. Dans le `.env` du PC Hôte : `LED_URL=http://<ip-esp>` et `LED_TOKEN=<même secret que secrets.h>`
   (secret généré : `python -c "import secrets; print(secrets.token_urlsafe(32))"`).
5. Essai depuis le PC Hôte :

```bash
python - <<'PY'
import hashlib, hmac, os, time, urllib.request
body = b'{"mode":"green_solid"}'
counter = str(time.time_ns() // 1_000_000)
signature = hmac.new(os.environ["LED_TOKEN"].encode(), counter.encode() + b"." + body, hashlib.sha256).hexdigest()
request = urllib.request.Request("http://<ip-esp>/led", body, {"X-Counter": counter, "X-Signature": signature})
print(urllib.request.urlopen(request).read())
PY
```

## Sécurité

- Requêtes signées en HMAC-SHA256, signature comparée en temps constant ; refus aussi de toute IP autre que le PC
  Hôte (les deux contrôles sont nécessaires : le filtrage IP seul se contourne par usurpation).
- Aucun secret dans le dépôt : `secrets.h` est ignoré, seul l'exemple est versionné.
- HTTP sans TLS (BearSSL + certificats coûteux en RAM sur l'ESP8266) : le **secret ne circule pas**, mais le
  message (un mode de LED) est lisible. Limites : le compteur est en RAM, donc un message capturé peut être
  rejoué **une fois** après un redémarrage de l'ESP8266 (pas d'horloge fiable sans Internet) ; l'effet d'un rejeu
  se limite à une LED qui ment, jamais à un accès. Réseau privé du point d'accès, jamais le campus ni Internet.
- Un déni de service sur l'ESP8266 est un scénario du chaos (lot L5) : l'accès n'en dépend pas.

## État de la vérification

- **ESP32** : essayé sur banc le 22/10 (carte ESP32-D0WD-V3 rev 3.1, flash 76,9 %, RAM 14,5 %).
  Les 5 modes répondent `200` et le comportement des LED a été vérifié à l'œil ; signature fausse
  refusée en `401`, compteur rejoué et compteur ancien refusés en `409`. Reste à essayer : le
  parcours d'authentification complet de bout en bout et la coupure réseau pendant `green_solid`.
- **ESP8266** : non compilé et non essayé sur banc, faute de carte D1 mini sur le poste.
- **Couleur** : le banc utilise une LED **jaune** à la place de la verte. Le protocole garde les noms
  `green_*` ; l'écart avec la consigne (LED bicolore vert/rouge) doit être tenu pour une limite
  assumée tant qu'une LED verte n'est pas montée.
