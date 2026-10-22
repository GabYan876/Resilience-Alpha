# Firmware ESP32 : LED bicolore d'état

Retour visuel de l'authentification du back-office (consigne additionnelle 1, voir
[`docs/consigne-additionnelle-1.md`](../../docs/consigne-additionnelle-1.md)). Le service `auth` appelle
l'ESP32 par le WiFi du point d'accès ; l'accès au back-office **ne dépend pas** de la LED (échec journalisé).
Le matériel effectivement ciblé ici est une **ESP32-DevKitC / ESP32-DevKit V1 avec ESP32-WROOM-32**.

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
`<X-Counter>.<corps exact>`. Le secret ne circule jamais ; l'ESP32 refuse un compteur déjà vu (rejeu).

Réponses : `200` mode appliqué, `400` mode invalide, `401` signature absente ou fausse, `403` IP source différente
de `ALLOWED_HOST_IP`, `409` compteur déjà vu (rejeu). Le client côté `auth` est `HttpStatusLed` (`services/auth/app/adapters/esp_led.py`).

Les durées étant dans le firmware, la LED reste cohérente (et s'éteint) si le réseau coupe en cours de séquence.

## Matériel et câblage

ESP32-DevKitC / ESP32-DevKit V1 (ESP32-WROOM-32), LED bicolore rouge/vert à **cathode commune**, deux
résistances série de 220 à 330 Ω. La cathode commune va au GND ; relier le GND de la LED et celui de la carte.

| Broche | GPIO | Branchement |
|---|---|---|
| GPIO25 | 25 | anode verte, via sa résistance |
| GPIO26 | 26 | anode rouge, via sa résistance |
| GND | — | cathode commune et masse commune |

GPIO25 et GPIO26 ne sont pas des broches de strapping sur l'ESP32. Respecter la polarité de la LED et
installer une résistance de limitation sur **chaque** anode. Les GPIO sont en logique 3,3 V et ne tolèrent
pas le 5 V ; si la LED nécessite davantage de courant que ce que la fiche technique autorise pour une sortie
GPIO, piloter chaque couleur avec un transistor/MOSFET adapté au lieu d'augmenter le courant de la broche.

## Installation

1. Brancher la carte en USB avec un câble de données. Ouvrir `firmware/esp32-led/` dans **CLion**
   (plugin PlatformIO) ; en ligne de commande, compiler : `pio run -e esp32dev`.
2. Copier `include/secrets.h.example` en `include/secrets.h` (ignoré par Git) et renseigner le WiFi
   `RESILIENCE-G<n>`, le secret `LED_TOKEN` et `ALLOWED_HOST_IP` (IP du PC Hôte, `192.168.137.1` avec le hotspot Windows).
3. Flasher : `pio run -e esp32dev -t upload`. Si plusieurs ports USB-série sont présents, ajouter
   `--upload-port COMx` sous Windows ou `--upload-port /dev/cu.usbserial-...` sous macOS. Au premier flash,
   PlatformIO lance généralement le bootloader automatiquement. Si l'outil reste bloqué sur `Connecting...`,
   maintenir **BOOT**, appuyer puis relâcher **EN**, puis relâcher **BOOT** lorsque l'écriture commence.
   Utiliser le pilote USB-série correspondant à la carte (souvent CP210x ou CH340) si aucun port n'apparaît.
   Ouvrir le moniteur série à 115200 bauds : l'adresse WiFi est affichée sous la forme `IP ESP32 : ...`
   après connexion au point d'accès.
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
- HTTP sans TLS : le **secret ne circule pas**, mais le message (un mode de LED) est lisible. Limites : le compteur
  est en RAM, donc un message capturé peut être rejoué **une fois** après un redémarrage de l'ESP32 ; l'effet d'un rejeu
  se limite à une LED qui ment, jamais à un accès. Réseau privé du point d'accès, jamais le campus ni Internet.
- Un déni de service sur l'ESP32 est un scénario du chaos (lot L5) : l'accès n'en dépend pas.

## État de la vérification

Compilation validée avec `pio run -d firmware/esp32-led -e esp32dev` (PlatformIO 6.6.0, Arduino-ESP32 2.0.14,
en-tête `secrets.h` local copié depuis l'exemple). Le firmware n'a pas été flashé ni essayé sur banc : vérifier les
cinq modes, la coupure réseau pendant `green_solid` et les deux couleurs avant de déclarer le comportement matériel validé.
