# Firmware ESP8266 : LED bicolore d'état

Retour visuel de l'authentification du back-office (consigne additionnelle 1, voir
[`docs/consigne-additionnelle-1.md`](../../docs/consigne-additionnelle-1.md)). Le service `auth` appelle
l'ESP8266 par le WiFi du point d'accès ; l'accès au back-office **ne dépend pas** de la LED (échec journalisé).

## Contrat

`POST http://<ip-esp>/led`, en-tête `Authorization: Bearer <LED_TOKEN>`, corps JSON :

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

Réponses : `200` mode appliqué, `400` mode ou corps invalide, `401` jeton absent ou faux, `403` IP source différente
de `ALLOWED_HOST_IP`. Le client côté `auth` est `HttpStatusLed` (`services/auth/app/adapters/esp_led.py`).

Les durées étant dans le firmware, la LED reste cohérente (et s'éteint) si le réseau coupe en cours de séquence.

## Matériel et câblage

ESP8266 (carte D1 mini), LED bicolore rouge/vert à **cathode commune**, 2 résistances de 220 Ω.

| Broche | GPIO | Branchement |
|---|---|---|
| D1 | 5 | anode verte, via 220 Ω |
| D2 | 4 | anode rouge, via 220 Ω |
| GND | — | cathode commune |

## Installation

1. Ouvrir `firmware/esp8266-led/` dans **CLion** (plugin PlatformIO) ; en ligne de commande : `pio run`.
2. Copier `include/secrets.h.example` en `include/secrets.h` (ignoré par Git) et renseigner le WiFi
   `RESILIENCE-G<n>`, le jeton et `ALLOWED_HOST_IP` (IP du PC Hôte, `192.168.137.1` avec le hotspot Windows).
3. Flasher : `pio run -t upload`. Moniteur série à 115200 bauds : l'IP obtenue n'est pas affichée, la relever
   dans la liste des clients du point d'accès.
4. Dans le `.env` du PC Hôte : `LED_URL=http://<ip-esp>` et `LED_TOKEN=<même jeton que secrets.h>`
   (jeton généré : `python -c "import secrets; print(secrets.token_urlsafe(32))"`).
5. Essai depuis le PC Hôte :

```bash
curl -X POST http://<ip-esp>/led -H "Authorization: Bearer $LED_TOKEN" -d '{"mode":"green_solid"}'
```

## Sécurité

- Jeton comparé en temps constant ; refus aussi de toute IP autre que le PC Hôte (les deux contrôles sont
  nécessaires : le filtrage IP seul se contourne par usurpation).
- Aucun secret dans le dépôt : `secrets.h` est ignoré, seul l'exemple est versionné.
- HTTP en clair sur le réseau privé du point d'accès : le jeton y circule en clair. Limite assumée, réseau
  jamais le campus ni Internet.
- Un déni de service sur l'ESP8266 est un scénario du chaos (lot L5) : l'accès n'en dépend pas.

## État de la vérification

**Non compilé et non essayé sur banc** à la rédaction (pas de PlatformIO sur le poste de revue). À faire par le
responsable du lot : `pio run`, essai des 5 modes, coupure réseau pendant `green_solid`, photo ou vidéo du banc.
