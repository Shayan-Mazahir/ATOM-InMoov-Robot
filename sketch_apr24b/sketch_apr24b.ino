#include <ESP32Servo.h>
// #include "wifi_config.h"

// ------- Pin Configuration ---------------------------------------------------
// Servo slot order matches protocol.json servo_map:
// slot 0=index_6, 1=middle_10, 2=ring_14, 3=pinky_18, 4=thumb_3
Servo servos[5];
const int SERVO_PINS[5] = {18, 19, 21, 22, 23};

// ------- Setup ---------------------------------------------------------------
void setup()
{
  Serial.begin(921600); // Must match baud rate in protocol.json

  // Attach each servo to its pin and centre it at 90°
  for (int i = 0; i < 5; i++)
  {
    servos[i].attach(SERVO_PINS[i]);
    servos[i].write(90);
  }
}

// ------- Main Loop -----------------------------------------------------------
void loop()
{
  // Wait for incoming data from Python over serial
  if (Serial.available())
  {

    // Read one full message, e.g. "120,90,45,60,130\n"
    String data = Serial.readStringUntil('\n');

    // ------- Parse Comma-Separated Values --------------------------------
    // Walk through the string character by character, slicing out each
    // value between commas and writing it to the corresponding servo slot
    int slot = 0;  // Current servo index (0–4)
    int start = 0; // Start index of the current token

    for (int i = 0; i <= data.length(); i++)
    {
      if (i == data.length() || data[i] == ',')
      {

        // Extract the substring for this slot and parse it as an int
        String val = data.substring(start, i);

        // Clamp to valid servo range before writing — guards against
        // corrupt or out-of-range values from the serial line
        int angle = constrain(val.toInt(), 0, 180);
        servos[slot].write(angle);

        slot++;
        start = i + 1; // Next token starts after the comma

        if (slot >= 5)
          break; // Ignore any extra values beyond slot 4
      }
    }
  }
}