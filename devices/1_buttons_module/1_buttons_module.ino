/*
  nano_input_change_debounce_binary.ino
  Reads D2..D5, debounces each input, and prints all 4 states (1 for HIGH, 0 for LOW)
  whenever any debounced state changes.

  Config:
    USE_INTERNAL_PULLUPS  - set true to enable INPUT_PULLUP (switch to GND).
    DEBOUNCE_MS           - debounce period (ms).
    POLL_INTERVAL_MS      - how often the loop polls inputs (ms).

  Note:
    - If USE_INTERNAL_PULLUPS = true, switches to GND will read LOW when closed
      (so "pressed" will be 0). The sketch prints raw pin values as 1 (HIGH) / 0 (LOW).
*/

const bool USE_INTERNAL_PULLUPS = true; // true -> INPUT_PULLUP (active = LOW when switch to GND)
const unsigned long DEBOUNCE_MS = 50;   // debounce time in ms
const unsigned long POLL_INTERVAL_MS = 5; // sampling interval in ms


const uint8_t inputPins[] = {2, 3, 4, 5};
const uint8_t outputPins[] = {6, 7, 8, 9};
const uint8_t NUM_PINS = sizeof(inputPins) / sizeof(inputPins[0]);

// Heartbeat (on-board LED) pattern: 1 distinct flash separated by an OFF beat
// We enforce at least one OFF after the flash so it is visible (cycle length 2 beats here)
const uint8_t HB_FLASHES = 1; // number of flashes per cycle
const unsigned long HB_BEAT_MS = 500; // 2 Hz beat period
const uint8_t HB_CYCLE_BEATS = (HB_FLASHES == 1) ? 2 : (uint8_t)(HB_FLASHES * 2 - 1); // ensure an OFF follows single flash
const unsigned long HB_CYCLE_PAUSE_MS = 1500; // extra OFF pause after full pattern
uint8_t hbBeatIndex = 0; // 0..HB_CYCLE_BEATS-1
unsigned long hbNextBeatDueMs = 0; // scheduling timestamp

uint8_t lastReading[NUM_PINS];
uint8_t stableState[NUM_PINS];
unsigned long lastEdgeTime[NUM_PINS];

// For LED hold logic
unsigned long ledHoldUntil[NUM_PINS] = {0, 0, 0, 0};

// --- Alive beacon via shared header (DRY) ---
#define MODULE_NAME "buttons_module"
#include <alive_beacon.h>

// Alive beacon data line: current button states
void beaconData() {
  Serial.print(F("Button States: "));
  for (uint8_t i = 0; i < NUM_PINS; ++i) {
    Serial.print('D'); Serial.print(inputPins[i]); Serial.print('=');
    Serial.print(stableState[i] == HIGH ? '1' : '0');
    if (i < NUM_PINS - 1) Serial.print(' ');
  }
  Serial.println();
}

void setup() {
  Serial.begin(9600);
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);

  for (uint8_t i = 0; i < NUM_PINS; ++i) {
    pinMode(inputPins[i], USE_INTERNAL_PULLUPS ? INPUT_PULLUP : INPUT);
    pinMode(outputPins[i], OUTPUT);
    lastReading[i] = digitalRead(inputPins[i]);
    stableState[i] = lastReading[i];
    lastEdgeTime[i] = millis();
    digitalWrite(outputPins[i], LOW); // Start with LEDs off
    ledHoldUntil[i] = 0;
  }

  Serial.println(F("Starting input monitor (D2..D5) - output 1=HIGH, 0=LOW"));
  Serial.print(F("USE_INTERNAL_PULLUPS="));
  Serial.println(USE_INTERNAL_PULLUPS ? F("true (active=LOW)") : F("false (active=HIGH)"));
  Serial.print(F("DEBOUNCE_MS="));
  Serial.println(DEBOUNCE_MS);
  printStates();

  // Initialize alive beacon AFTER initial informational prints so identity beacons are clean
  setAliveDataPrinter(beaconData);
  initAliveBeacon();
}

void loop() {
  bool anyChanged = false;
  unsigned long now = millis();

  // Periodic identity message (non-blocking)
  runAliveBeacon();


  for (uint8_t i = 0; i < NUM_PINS; ++i) {
    uint8_t r = digitalRead(inputPins[i]);
    if (r != lastReading[i]) {
      lastEdgeTime[i] = now;
      lastReading[i] = r;
    } else {
      if ((now - lastEdgeTime[i]) >= DEBOUNCE_MS && r != stableState[i]) {
        stableState[i] = r;
        anyChanged = true;
      }
    }

    // LED logic: illuminate while pressed, and for 1s after release, reset timer if pressed again
    bool pressed = (USE_INTERNAL_PULLUPS ? (stableState[i] == LOW) : (stableState[i] == HIGH));
    if (pressed) {
      digitalWrite(outputPins[i], HIGH);
      ledHoldUntil[i] = now + 1000; // 1 second hold after release
    } else {
      if (now < ledHoldUntil[i]) {
        digitalWrite(outputPins[i], HIGH);
      } else {
        digitalWrite(outputPins[i], LOW);
      }
    }
  }

  if (anyChanged) {
    printStates();
  }

  delay(POLL_INTERVAL_MS);

  // Heartbeat update with extended pause after cycle
  if (now >= hbNextBeatDueMs) {
    bool on = (hbBeatIndex % 2 == 0) && ((hbBeatIndex / 2) < HB_FLASHES);
    digitalWrite(LED_BUILTIN, on ? HIGH : LOW);
    hbBeatIndex++;
    if (hbBeatIndex >= HB_CYCLE_BEATS) {
      // End of pattern: force OFF and insert long pause
      digitalWrite(LED_BUILTIN, LOW);
      hbBeatIndex = 0;
      hbNextBeatDueMs = now + HB_CYCLE_PAUSE_MS;
    } else {
      hbNextBeatDueMs = now + HB_BEAT_MS;
    }
  }
}

void printStates() {
  // Example: States: D2=1 D3=0 D4=1 D5=1
  Serial.print(F("Button States: "));
  for (uint8_t i = 0; i < NUM_PINS; ++i) {
    Serial.print('D');
    Serial.print(inputPins[i]);
    Serial.print('=');
    Serial.print(stableState[i] == HIGH ? '1' : '0');
    if (i < NUM_PINS - 1) Serial.print(' ');
  }
  Serial.println();
}
