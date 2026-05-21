#include <Servo.h>

Servo servo;

void setup() {
  // Pin 2 - Thumb
  servo.attach(2);
  servo.write(90);
  delay(4000);
  servo.detach();

  // Pin 3 - Index
  servo.attach(3);
  servo.write(90);
  delay(4000);
  servo.detach();

  // Pin 4 - Majeure
  servo.attach(4);
  servo.write(90);
  delay(4000);
  servo.detach();

  // Pin 5 - Ring finger
  servo.attach(5);
  servo.write(90);
  delay(4000);
  servo.detach();

  // Pin 6 - Pinky
  servo.attach(6);
  servo.write(90);
  delay(4000);
  servo.detach();

  // Pin 7 - Wrist
  servo.attach(7);
  servo.write(90);
  delay(4000);
  servo.detach();

  // Pin 8 - Biceps
  servo.attach(8);
  servo.write(90);
  delay(4000);
  servo.detach();

  // Pin 9 - Rotate
  servo.attach(9);
  servo.write(90);
  delay(4000);
  servo.detach();

  // Pin 10 - Shoulder
  servo.attach(10);
  servo.write(90);
  delay(4000);
  servo.detach();

  // Pin 11 - Omoplat
  servo.attach(11);
  servo.write(90);
  delay(4000);
  servo.detach();

  // Pin 12 - Neck
  servo.attach(12);
  servo.write(90);
  delay(4000);
  servo.detach();

  // Pin 13 - Rot Head
  servo.attach(13);
  servo.write(90);
  delay(4000);
  servo.detach();
}

void loop() {}