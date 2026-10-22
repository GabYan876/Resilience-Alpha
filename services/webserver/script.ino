
const int led1 = 25;
const int led2 = 32;

String command;

void setup() {
  Serial.begin(115200);

  pinMode(led1, OUTPUT);
  pinMode(led2, OUTPUT);

  digitalWrite(led1, LOW);
  digitalWrite(led2, LOW);

  Serial.println("ESP32_READY");
}

void loop() {
  if (Serial.available()) {
    command = Serial.readStringUntil('\n');
    command.trim();

    if (command == "LED1_ON") {
      digitalWrite(led1, HIGH);
      Serial.println("OK LED1 ON");
    } else if (command == "LED1_OFF") {
      digitalWrite(led1, LOW);
      Serial.println("OK LED1 OFF");
    } else if (command == "LED2_ON") {
      digitalWrite(led2, HIGH);
      Serial.println("OK LED2 ON");
    } else if (command == "LED2_OFF") {
      digitalWrite(led2, LOW);
      Serial.println("OK LED2 OFF");
    } else if (command == "STATUS") {
      Serial.printf("LED1=%d LED2=%d\n", digitalRead(led1), digitalRead(led2));
    } else {
      Serial.println("ERROR UNKNOWN_COMMAND");
    }
  }
}
