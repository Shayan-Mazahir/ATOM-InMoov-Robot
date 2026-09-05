/*
 * OYMotion EMGFilters example, adapted to record to EEPROM so it can run
 * on battery power with no USB attached.
 *
 * Based on OYMotion Inc. 2019 example code (BSD 2-clause).
 *
 * Stores the raw 64-sample running sum instead of the truncated mean,
 * to keep 64x the resolution.
 *
 * USE:
 *   1. Set RECORDING to 1, upload from the laptop
 *   2. Unplug USB from the laptop, plug into a USB power bank
 *   3. 20 s slow blink   - get set up
 *      10 s fast blink   - settle, hands off everything
 *      5 s LED OFF       - filter warm-up (do not be thrown by the dark gap)
 *      SOLID ON, 0.5 s   - RECORDING
 *      3 long blinks     - done
 *   4. Back to the laptop, set RECORDING to 0, upload
 *   5. Serial Monitor at 115200
 */

#if defined(ARDUINO) && ARDUINO >= 100
#include "Arduino.h"
#else
#include "WProgram.h"
#endif

#include "EMGFilters.h"
#include <EEPROM.h>

// 1 = record (run on power bank), 0 = dump to serial (run on laptop)
#define RECORDING 0

#define SensorInputPin A4

const int N = 500;        // 500 samples, 2 bytes each = 1000 bytes
const int WARMUP = 5000;  // 5 seconds of settling before recording

EMGFilters myFilter;

SAMPLE_FREQUENCY sampleRate = SAMPLE_FREQ_1000HZ;
NOTCH_FREQUENCY  humFreq    = NOTCH_FREQ_60HZ;   // 60 Hz for North America

#define BUF_LEN 64
uint16_t rectBuf[BUF_LEN];
uint8_t  rectIndex = 0;
uint32_t rectSum   = 0;

void bufAdd(uint16_t val) {
  rectSum -= rectBuf[rectIndex];
  rectSum += val;
  rectBuf[rectIndex] = val;
  rectIndex = (rectIndex + 1) % BUF_LEN;
}

void blink(int times, int ms) {
  for (int i = 0; i < times; i++) {
    digitalWrite(LED_BUILTIN, HIGH); delay(ms);
    digitalWrite(LED_BUILTIN, LOW);  delay(ms);
  }
}

void setup() {
  pinMode(LED_BUILTIN, OUTPUT);

  myFilter.init(sampleRate, humFreq, true, true, true);

  rectSum   = 0;
  rectIndex = 0;
  for (int j = 0; j < BUF_LEN; j++) rectBuf[j] = 0;

#if RECORDING

  // 20 s: unplug from laptop, move to power bank
  blink(20, 500);

  // 10 s: get positioned and settled
  blink(50, 100);

  // 5 s warm-up, LED OFF, so the IIR state and ring buffer reach steady state
  digitalWrite(LED_BUILTIN, LOW);
  unsigned long warm = micros();
  for (int i = 0; i < WARMUP; i++) {
    warm += 1000;
    int d = analogRead(SensorInputPin);
    int f = myFilter.update(d);
    bufAdd(abs(f));
    while ((long)(micros() - warm) < 0) { }
  }

  // SOLID ON = recording
  digitalWrite(LED_BUILTIN, HIGH);

  unsigned long next = micros();
  for (int i = 0; i < N; i++) {
    next += 1000;

    int data = analogRead(SensorInputPin);
    int dataAfterFilter = myFilter.update(data);

    bufAdd(abs(dataAfterFilter));

    // store the raw running sum, not the truncated mean
    uint16_t envelope = (rectSum > 65535) ? 65535 : (uint16_t)rectSum;

    EEPROM.write(i * 2,     envelope & 0xFF);
    EEPROM.write(i * 2 + 1, (envelope >> 8) & 0xFF);

    while ((long)(micros() - next) < 0) { }
  }

  digitalWrite(LED_BUILTIN, LOW);
  delay(500);
  blink(3, 800);

#else

  Serial.begin(115200);
  delay(1000);
  Serial.println("--- envelope sum dump (vendor filter, 60 Hz notch) ---");
  for (int i = 0; i < N; i++) {
    uint16_t v = EEPROM.read(i * 2) | (EEPROM.read(i * 2 + 1) << 8);
    Serial.println(v);
  }
  Serial.println("--- end ---");

#endif
}

void loop() { }