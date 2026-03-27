/*
  sliders_module.ino
  Samples A0 and A1 continuously, applies EWMA smoothing with TAU_MS (50 ms),
  and prints integer values 0..1023 when they change by DELTA_THRESHOLD.
  Prints at most once per DEBOUNCE_MS (50 ms) => up to 20 Hz.
*/

const unsigned long DEBOUNCE_MS = 50;     // 50 ms debounce / max output interval (=> 20 Hz)
const float TAU_MS = 50.0f;               // EWMA time constant (ms) - smoothing window
const int DELTA_THRESHOLD = 2;            // minimum integer change (0..1023) to report
const unsigned long SERIAL_BAUD = 9600;   // 115200;
// Heartbeat: 3 distinct flashes (ON OFF ON OFF ON) plus tail OFF beats
const uint8_t HB_FLASHES = 3;
const unsigned long HB_BEAT_MS = 500; // 2 Hz
const uint8_t HB_MIN_BEATS = (uint8_t)(HB_FLASHES * 2 - 1); // 3 flashes -> 5 beats minimal pattern
const uint8_t HB_TAIL_OFF = 2; // extra OFF tail beats for clarity
const uint8_t HB_CYCLE_BEATS = HB_MIN_BEATS + HB_TAIL_OFF; // 5 + 2 = 7 beats total
const unsigned long HB_CYCLE_PAUSE_MS = 1500; // extended pause after pattern
uint8_t hbBeatIndex = 0; // 0..HB_CYCLE_BEATS-1
unsigned long hbNextBeatDueMs = 0;

unsigned long lastSampleMicros = 0;
unsigned long lastOutputMs = 0;

float emaA0 = -1.0f; // initialized on first sample
float emaA1 = -1.0f;

// Alive beacon
#define MODULE_NAME "sliders_module"
#include <alive_beacon.h>

int lastOutA0 = -1; // moved from static inside loop for beacon visibility
int lastOutA1 = -1;

void beaconData() {
  if (lastOutA0 >= 0 && lastOutA1 >= 0) {
    Serial.print(F("Slider States: A0="));
    Serial.print(lastOutA0);
    Serial.print(F(" A1="));
    Serial.println(lastOutA1);
  } else {
    Serial.println(F("Slider States: pending"));
  }
}

void setup() {
  Serial.begin(SERIAL_BAUD);
  // DON'T block waiting for Serial on a Nano; that can hang on some boards.
  pinMode(A0, INPUT);
  pinMode(A1, INPUT);
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);

  // small info line (won't block)
  Serial.println(F("A0/A1 EWMA monitor (TAU_MS=50ms, max 20Hz)"));
  lastSampleMicros = micros();
  setAliveDataPrinter(beaconData);
  initAliveBeacon();
}

void loop() {
  runAliveBeacon();
  // read both channels as fast as possible
  unsigned long nowMicros = micros();
  unsigned long dtMicros = nowMicros - lastSampleMicros;
  if (dtMicros == 0) dtMicros = 1; // avoid div0
  float dtMs = dtMicros * 0.001f;
  lastSampleMicros = nowMicros;

  int raw0 = analogRead(A0);
  int raw1 = analogRead(A1);

  // compute EWMA alpha = dt / (tau + dt)
  float alpha = dtMs / (TAU_MS + dtMs);

  if (emaA0 < 0.0f) emaA0 = raw0; // init on first sample
  else emaA0 = alpha * raw0 + (1.0f - alpha) * emaA0;

  if (emaA1 < 0.0f) emaA1 = raw1;
  else emaA1 = alpha * raw1 + (1.0f - alpha) * emaA1;

  // Rate limit outputs to at most once per DEBOUNCE_MS (50 ms => 20 Hz)
  unsigned long nowMs = millis();
  if ((nowMs - lastOutputMs) >= DEBOUNCE_MS) {
  // lastOutA0/lastOutA1 now globals for beacon usage

    int outA0 = (int)(emaA0 + 0.5f); // round
    int outA1 = (int)(emaA1 + 0.5f);

    bool changed = false;
    if (lastOutA0 < 0 || abs(outA0 - lastOutA0) >= DELTA_THRESHOLD) changed = true;
    if (lastOutA1 < 0 || abs(outA1 - lastOutA1) >= DELTA_THRESHOLD) changed = true;

    if (changed) {
      Serial.print("Slider States: A0=");
      Serial.print(outA0);
      Serial.print(" A1=");
      Serial.println(outA1);
      lastOutA0 = outA0;
      lastOutA1 = outA1;
      lastOutputMs = nowMs;
    } else {
      // still update rate limiter even if not printing to ensure max rate
      lastOutputMs = nowMs;
    }
  }

  // small tight loop; no delay required — analogRead itself is ~100µs.

  // Heartbeat
  if (nowMs >= hbNextBeatDueMs) {
    bool on = (hbBeatIndex % 2 == 0) && (hbBeatIndex/2 < HB_FLASHES);
    digitalWrite(LED_BUILTIN, on ? HIGH : LOW);
    hbBeatIndex++;
    if (hbBeatIndex >= HB_CYCLE_BEATS) {
      digitalWrite(LED_BUILTIN, LOW);
      hbBeatIndex = 0;
      hbNextBeatDueMs = nowMs + HB_CYCLE_PAUSE_MS;
    } else {
      hbNextBeatDueMs = nowMs + HB_BEAT_MS;
    }
  }
}
