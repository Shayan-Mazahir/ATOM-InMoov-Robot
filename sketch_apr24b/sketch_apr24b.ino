#include <ESP32Servo.h>

Servo fingerServo;
const int SERVO_PIN = 18;

void setup() {
  Serial.begin(921600);
  fingerServo.attach(SERVO_PIN);
  fingerServo.write(90); // start at middle position
}

void loop() {
  if (Serial.available()) {
    String data = Serial.readStringUntil('\n');
    int angle = data.toInt();
    
    // Clamp to valid range
    angle = constrain(angle, 0, 180);
    
    fingerServo.write(angle);
  }
}