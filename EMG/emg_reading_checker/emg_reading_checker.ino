/**This code contains the following things:
- Custom EMG Filter based of 60Hz
- A very not-so-reliable-but-reliable way of checking if ur sensor is working or not
- and some math that i dont fully understand
- oh yeah make sure ur either:
                              - using A4 on Arduino
                              - or change line 9**/

#define SensorInputPin A4

const float FS = 1000.0;

float nb0, nb1, nb2, na1, na2;
float nx1 = 0, nx2 = 0, ny1 = 0, ny2 = 0;
float hpA, hpPrevIn = 0, hpPrevOut = 0;
float envA, env = 0;

unsigned long nextSample;

void setupNotch(float f0, float Q) {
  float w0 = 2.0 * PI * f0 / FS;
  float alpha = sin(w0) / (2.0 * Q);
  float a0 = 1 + alpha;
  nb0 =  1.0 / a0;
  nb1 = -2.0 * cos(w0) / a0;
  nb2 =  1.0 / a0;
  na1 = -2.0 * cos(w0) / a0;
  na2 = (1 - alpha) / a0;
}

float sampleOnce() {
  nextSample += 1000;
  float x = analogRead(SensorInputPin) - 512.0;
  float y = nb0 * x + nb1 * nx1 + nb2 * nx2 - na1 * ny1 - na2 * ny2;
  nx2 = nx1; nx1 = x;
  ny2 = ny1; ny1 = y;
  float hp = hpA * (hpPrevOut + y - hpPrevIn);
  hpPrevIn = y;
  hpPrevOut = hp;
  env += envA * (fabs(hp) - env);
  while ((long)(micros() - nextSample) < 0) { }
  return env;
}

// average env over a window, in milliseconds
float measure(int ms) {
  double sum = 0;
  for (int i = 0; i < ms; i++) sum += sampleOnce();
  return sum / ms;
}

void countdown(const char *label, int secs) {
  Serial.print(label);
  for (int s = secs; s > 0; s--) {
    Serial.print(" ");
    Serial.print(s);
    measure(1000);            // 1 second of samples, discarded
  }
  Serial.println();
}

void setup() {
  Serial.begin(250000);
  setupNotch(60.0, 8.0);
  float rcHP = 1.0 / (2.0 * PI * 10.0);    // was 20.0 — let more through
  hpA = rcHP / (rcHP + 1.0 / FS);
  float rcEnv = 1.0 / (2.0 * PI * 10.0);   // was 4.0 — faster envelope
  envA = (1.0 / FS) / (rcEnv + 1.0 / FS);
  nextSample = micros();

  Serial.println();
  Serial.println("Strap the sensor on. Starting in 5 seconds.");
  countdown("Settling...", 5);
}

void loop() {
  const int ROUNDS = 8;
  float rests[ROUNDS], flexes[ROUNDS];
  int wins = 0;

  for (int r = 0; r < ROUNDS; r++) {
    Serial.print("\n--- Round ");
    Serial.print(r + 1);
    Serial.print(" of ");
    Serial.println(ROUNDS);

    Serial.println(">>> RELAX");
    measure(1000);
    rests[r] = measure(3000);

    countdown("    clench in", 2);

    Serial.println(">>> CLENCH");
    measure(1000);
    flexes[r] = measure(3000);

    Serial.print("    rest ");
    Serial.print(rests[r], 2);
    Serial.print("   clench ");
    Serial.print(flexes[r], 2);
    Serial.print("   diff ");
    Serial.print(flexes[r] - rests[r], 2);
    if (flexes[r] > rests[r]) { wins++; Serial.print("  <-- up"); }
    Serial.println();
  }

  float rSum = 0, fSum = 0;
  for (int i = 0; i < ROUNDS; i++) { rSum += rests[i]; fSum += flexes[i]; }

  Serial.println("\n=========== RESULT ===========");
  Serial.print("avg rest   : "); Serial.println(rSum / ROUNDS, 2);
  Serial.print("avg clench : "); Serial.println(fSum / ROUNDS, 2);
  Serial.print("clench higher in ");
  Serial.print(wins);
  Serial.print(" of ");
  Serial.print(ROUNDS);
  Serial.println(" rounds");

  if (wins >= 7)      Serial.println("VERDICT: real signal (consistent)");
  else if (wins >= 6) Serial.println("VERDICT: probably real");
  else if (wins >= 5) Serial.println("VERDICT: suggestive, not conclusive");
  else                Serial.println("VERDICT: no consistent response");
  Serial.println("==============================");

  countdown("Restarting in", 5);
}