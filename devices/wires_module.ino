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

const uint8_t pins[] = {2, 3, 4, 5};
const uint8_t NUM_PINS = sizeof(pins) / sizeof(pins[0]);

uint8_t lastReading[NUM_PINS];
uint8_t stableState[NUM_PINS];
unsigned long lastEdgeTime[NUM_PINS];

void setup() {
  Serial.begin(9600);
  for (uint8_t i = 0; i < NUM_PINS; ++i) {
    pinMode(pins[i], USE_INTERNAL_PULLUPS ? INPUT_PULLUP : INPUT);
    lastReading[i] = digitalRead(pins[i]);
    stableState[i] = lastReading[i];
    lastEdgeTime[i] = millis();
  }

  Serial.println(F("Starting input monitor (D2..D5) - output 1=HIGH, 0=LOW"));
  Serial.print(F("USE_INTERNAL_PULLUPS="));
  Serial.println(USE_INTERNAL_PULLUPS ? F("true (active=LOW)") : F("false (active=HIGH)"));
  Serial.print(F("DEBOUNCE_MS="));
  Serial.println(DEBOUNCE_MS);
  printStates();
}

void loop() {
  bool anyChanged = false;
  unsigned long now = millis();

  for (uint8_t i = 0; i < NUM_PINS; ++i) {
    uint8_t r = digitalRead(pins[i]);
    if (r != lastReading[i]) {
      lastEdgeTime[i] = now;
      lastReading[i] = r;
    } else {
      if ((now - lastEdgeTime[i]) >= DEBOUNCE_MS && r != stableState[i]) {
        stableState[i] = r;
        anyChanged = true;
      }
    }
  }

  if (anyChanged) {
    printStates();
  }

  delay(POLL_INTERVAL_MS);
}

void printStates() {
  // Example: States: D2=1 D3=0 D4=1 D5=1
  Serial.print(F("Wire States: "));
  for (uint8_t i = 0; i < NUM_PINS; ++i) {
    Serial.print('D');
    Serial.print(pins[i]);
    Serial.print('=');
    Serial.print(stableState[i] == HIGH ? '1' : '0');
    if (i < NUM_PINS - 1) Serial.print(' ');
  }
  Serial.println();
}
