// LED bicolore pilotée par `auth` : POST /led {"mode": "off|green_blink|green_solid|red_blink|red_solid"}.
// Les durées (30 s, 10 clignotements) sont gérées ici : la LED reste cohérente si le réseau coupe.
#include <Arduino.h>
#include <ESP8266WebServer.h>
#include <ESP8266WiFi.h>

#include "secrets.h"

constexpr uint8_t PIN_GREEN = D1;  // GPIO5, via résistance 220 Ω
constexpr uint8_t PIN_RED = D2;    // GPIO4, via résistance 220 Ω
constexpr uint32_t SOLID_MS = 30000;
constexpr uint32_t BLINK_HALF_PERIOD_MS = 300;
constexpr uint8_t RED_BLINK_COUNT = 10;
constexpr size_t MAX_BODY = 128;

enum class Mode { Off, GreenBlink, GreenSolid, RedBlink, RedSolid };

ESP8266WebServer server(80);
Mode mode = Mode::Off;
uint32_t modeStart = 0;

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

// Comparaison en temps constant du jeton.
bool tokenMatches(const String& header) {
  const String expected = String("Bearer ") + LED_TOKEN;
  if (header.length() != expected.length()) return false;
  uint8_t diff = 0;
  for (size_t i = 0; i < expected.length(); i++) diff |= header[i] ^ expected[i];
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
  // Filtre IP puis jeton : tout refus est journalisé sur la liaison série.
  if (server.client().remoteIP().toString() != ALLOWED_HOST_IP) {
    Serial.println("REFUS ip");
    server.send(403, "application/json", "{\"error\":\"forbidden\"}");
    return;
  }
  if (!server.hasHeader("Authorization") || !tokenMatches(server.header("Authorization"))) {
    Serial.println("REFUS jeton");
    server.send(401, "application/json", "{\"error\":\"unauthorized\"}");
    return;
  }
  const String body = server.arg("plain");
  String value;
  Mode next;
  if (body.length() > MAX_BODY || !extractMode(body, value) || !parseMode(value, next)) {
    server.send(400, "application/json", "{\"error\":\"invalid mode\"}");
    return;
  }
  setMode(next);
  Serial.println("LED " + value);
  server.send(200, "application/json", "{\"mode\":\"" + value + "\"}");
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_GREEN, OUTPUT);
  pinMode(PIN_RED, OUTPUT);
  drive(false, false);

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  const char* headers[] = {"Authorization"};
  server.collectHeaders(headers, 1);
  server.on("/led", HTTP_POST, handleLed);
  server.begin();
}

void loop() {
  server.handleClient();
  updateLed();
}
