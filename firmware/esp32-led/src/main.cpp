// LED bicolore pilotée par `auth` : POST /led {"mode": "off|green_blink|green_solid|red_blink|red_solid"}.
// Requête signée : X-Counter (croissant) et X-Signature = HMAC-SHA256(secret, "<compteur>." + corps) en hexa.
// Les durées (30 s, 10 clignotements) sont gérées ici : la LED reste cohérente si le réseau coupe.
// Deux cartes : D1 mini (ESP8266) et DevKit ESP32. Seules les bibliothèques réseau, le calcul du
// HMAC et les broches diffèrent ; la machine à états et le contrat HTTP sont communs.
#include <Arduino.h>

#if defined(ARDUINO_ARCH_ESP32)
#include <WebServer.h>
#include <WiFi.h>
#include <mbedtls/md.h>
using LedServer = WebServer;
constexpr uint8_t PIN_GREEN = 25;  // GPIO25, via résistance 220 Ω
constexpr uint8_t PIN_RED = 26;    // GPIO26, via résistance 220 Ω
#else
#include <ESP8266WebServer.h>
#include <ESP8266WiFi.h>
#include <bearssl/bearssl_hmac.h>
using LedServer = ESP8266WebServer;
constexpr uint8_t PIN_GREEN = D1;  // GPIO5, via résistance 220 Ω
constexpr uint8_t PIN_RED = D2;    // GPIO4, via résistance 220 Ω
#endif

#include "secrets.h"

constexpr uint32_t SOLID_MS = 30000;
constexpr uint32_t BLINK_HALF_PERIOD_MS = 300;
constexpr uint8_t RED_BLINK_COUNT = 10;
constexpr size_t MAX_BODY = 128;
constexpr size_t SIG_HEX_LEN = 64;

enum class Mode { Off, GreenBlink, GreenSolid, RedBlink, RedSolid };

LedServer server(80);
Mode mode = Mode::Off;
uint32_t modeStart = 0;
uint64_t lastCounter = 0;  // en RAM : un rejeu reste possible une fois après un redémarrage
uint32_t lastAnnounce = 0;
constexpr uint32_t ANNOUNCE_PERIOD_MS = 30000;

void setMode(Mode next) {
  mode = next;
  modeStart = millis();
}

void drive(bool green, bool red) {
  digitalWrite(PIN_GREEN, green ? HIGH : LOW);
  digitalWrite(PIN_RED, red ? HIGH : LOW);
}

// Appelée à chaque tour de loop() : ne dépend pas du réseau.
void updateLed() {
  const uint32_t elapsed = millis() - modeStart;
  const bool blinkOn = (elapsed / BLINK_HALF_PERIOD_MS) % 2 == 0;
  switch (mode) {
    case Mode::GreenBlink:
      drive(blinkOn, false);
      break;
    case Mode::GreenSolid:
      if (elapsed >= SOLID_MS) { setMode(Mode::Off); drive(false, false); } else drive(true, false);
      break;
    case Mode::RedSolid:
      if (elapsed >= SOLID_MS) { setMode(Mode::Off); drive(false, false); } else drive(false, true);
      break;
    case Mode::RedBlink:
      if (elapsed >= 2UL * RED_BLINK_COUNT * BLINK_HALF_PERIOD_MS) { setMode(Mode::Off); drive(false, false); }
      else drive(false, blinkOn);
      break;
    case Mode::Off:
      drive(false, false);
      break;
  }
}

bool parseMode(const String& value, Mode& out) {
  if (value == "off") out = Mode::Off;
  else if (value == "green_blink") out = Mode::GreenBlink;
  else if (value == "green_solid") out = Mode::GreenSolid;
  else if (value == "red_blink") out = Mode::RedBlink;
  else if (value == "red_solid") out = Mode::RedSolid;
  else return false;
  return true;
}

// HMAC-SHA256(secret, "<compteur>." + corps) en hexadécimal minuscule.
String sign(const String& counter, const String& body) {
  const String message = counter + "." + body;
  const char* secret = LED_TOKEN;
  uint8_t digest[32];
#if defined(ARDUINO_ARCH_ESP32)
  mbedtls_md_context_t context;
  mbedtls_md_init(&context);
  mbedtls_md_setup(&context, mbedtls_md_info_from_type(MBEDTLS_MD_SHA256), 1);
  mbedtls_md_hmac_starts(&context, reinterpret_cast<const unsigned char*>(secret), strlen(secret));
  mbedtls_md_hmac_update(&context, reinterpret_cast<const unsigned char*>(message.c_str()),
                         message.length());
  mbedtls_md_hmac_finish(&context, digest);
  mbedtls_md_free(&context);
#else
  br_hmac_key_context keyContext;
  br_hmac_context context;
  br_hmac_key_init(&keyContext, &br_sha256_vtable, secret, strlen(secret));
  br_hmac_init(&context, &keyContext, 0);
  br_hmac_update(&context, message.c_str(), message.length());
  br_hmac_out(&context, digest);
#endif
  String hex;
  for (uint8_t byte : digest) {
    if (byte < 16) hex += '0';
    hex += String(byte, HEX);
  }
  return hex;
}

// Comparaison en temps constant de deux signatures hexadécimales.
bool sameSignature(const String& a, const String& b) {
  if (a.length() != SIG_HEX_LEN || b.length() != SIG_HEX_LEN) return false;
  uint8_t diff = 0;
  for (size_t i = 0; i < SIG_HEX_LEN; i++) diff |= a[i] ^ b[i];
  return diff == 0;
}

// Extrait la valeur de "mode" du corps JSON sans dépendance supplémentaire.
bool extractMode(const String& body, String& value) {
  int key = body.indexOf("\"mode\"");
  if (key < 0) return false;
  int open = body.indexOf('"', body.indexOf(':', key) + 1);
  if (open < 0) return false;
  int close = body.indexOf('"', open + 1);
  if (close < 0) return false;
  value = body.substring(open + 1, close);
  return true;
}

void handleLed() {
  // Filtre IP puis signature : tout refus est journalisé sur la liaison série.
  if (server.client().remoteIP().toString() != ALLOWED_HOST_IP) {
    Serial.println("REFUS ip");
    server.send(403, "application/json", "{\"error\":\"forbidden\"}");
    return;
  }
  const String body = server.arg("plain");
  const String counter = server.header("X-Counter");
  const uint64_t counterValue = strtoull(counter.c_str(), nullptr, 10);
  const String signature = server.header("X-Signature");
  // Signature d'abord, puis compteur : un message rejoué ou falsifié ne change jamais l'état.
  if (body.length() > MAX_BODY || counter.length() == 0 || counter.length() > 20 ||
      !sameSignature(sign(counter, body), signature)) {
    Serial.println("REFUS signature");
    server.send(401, "application/json", "{\"error\":\"unauthorized\"}");
    return;
  }
  if (counterValue <= lastCounter) {
    Serial.println("REFUS rejeu");
    server.send(409, "application/json", "{\"error\":\"replay\"}");
    return;
  }
  lastCounter = counterValue;
  String value;
  Mode next;
  if (!extractMode(body, value) || !parseMode(value, next)) {
    server.send(400, "application/json", "{\"error\":\"invalid mode\"}");
    return;
  }
  setMode(next);
  Serial.println("LED " + value);
  server.send(200, "application/json", "{\"mode\":\"" + value + "\"}");
}

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println("BOOT");
  pinMode(PIN_GREEN, OUTPUT);
  pinMode(PIN_RED, OUTPUT);
  drive(false, false);

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  // La carte sert un serveur HTTP : l'économie d'énergie WiFi lui ferait manquer des requêtes
  // ARP, et l'hôte ne saurait plus la joindre du tout (ARP FAILED) malgré une association valide.
#if defined(ARDUINO_ARCH_ESP32)
  WiFi.setSleep(false);
#else
  WiFi.setSleepMode(WIFI_NONE_SLEEP);
#endif
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  const char* headers[] = {"X-Counter", "X-Signature"};
  server.collectHeaders(headers, 2);
  server.on("/led", HTTP_POST, handleLed);
  server.begin();
}

void loop() {
  // L'IP est réannoncée toutes les 30 s : elle sert à renseigner LED_URL du PC Hôte, et un
  // moniteur série branché après le démarrage doit pouvoir la lire sans redémarrer la carte.
  if (static_cast<int32_t>(millis() - lastAnnounce) >= 0) {
    lastAnnounce = millis() + ANNOUNCE_PERIOD_MS;
    if (WiFi.status() == WL_CONNECTED) Serial.println("IP " + WiFi.localIP().toString());
    else Serial.printf("WIFI non connecte (status=%d)\n", WiFi.status());
  }
  server.handleClient();
  updateLed();
}
