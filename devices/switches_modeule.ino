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

const uint8_t pins[] = {2, 3};
const uint8_t NUM_PINS = sizeof(pins) / sizeof(pins[0]);

// Heartbeat: 4 distinct flashes (each separated by one OFF beat) then long pause.
// Sequence (steps, each evaluated on schedule):
//  ON (flash1) 500ms
//  OFF 500ms
//  ON (flash2) 500ms
//  OFF 500ms
//  ON (flash3) 500ms
//  OFF 500ms
//  ON (flash4) 500ms
//  OFF long pause (HB_CYCLE_PAUSE_MS)
const uint8_t HB_FLASHES = 4;
const unsigned long HB_BEAT_MS = 500;      // duration of ON and inter-flash OFF beats
const unsigned long HB_CYCLE_PAUSE_MS = 1500; // long OFF after last flash
// Total steps per cycle = flashes*2 (each flash ON plus an OFF, with last OFF being long pause)
const uint8_t HB_TOTAL_STEPS = HB_FLASHES * 2; // 8 steps
uint8_t hbStep = 0; // 0..HB_TOTAL_STEPS-1
unsigned long hbNextChangeMs = 0; // when to advance heartbeat

uint8_t lastReading[NUM_PINS];
uint8_t stableState[NUM_PINS];
unsigned long lastEdgeTime[NUM_PINS];

void setup() {
  Serial.begin(9600);
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);
  for (uint8_t i = 0; i < NUM_PINS; ++i) {
    pinMode(pins[i], USE_INTERNAL_PULLUPS ? INPUT_PULLUP : INPUT);
    lastReading[i] = digitalRead(pins[i]);
    stableState[i] = lastReading[i];
    lastEdgeTime[i] = millis();
  }

  Serial.println(F("Starting input monitor (D2, D3) - output 1=HIGH, 0=LOW"));
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

  // Heartbeat
  unsigned long now2 = millis();
  if (now2 >= hbNextChangeMs) {
    bool isOnStep = (hbStep % 2 == 0); // even steps are ON
    bool lastStep = (hbStep == HB_TOTAL_STEPS - 1); // final OFF (long pause)
    if (isOnStep) {
      digitalWrite(LED_BUILTIN, HIGH); // flash ON
      hbNextChangeMs = now2 + HB_BEAT_MS; // ON duration
    } else {
      digitalWrite(LED_BUILTIN, LOW); // OFF beat
      hbNextChangeMs = now2 + (lastStep ? HB_CYCLE_PAUSE_MS : HB_BEAT_MS);
    }
    hbStep++;
    if (hbStep >= HB_TOTAL_STEPS) hbStep = 0; // restart cycle
  }
}

void printStates() {
  // Example: Switch States: D2=1 D3=0
  Serial.print(F("Switch States: "));
  for (uint8_t i = 0; i < NUM_PINS; ++i) {
    Serial.print('D');
    Serial.print(pins[i]);
    Serial.print('=');
    Serial.print(stableState[i] == HIGH ? '1' : '0');
    if (i < NUM_PINS - 1) Serial.print(' ');
  }
  Serial.println();
}
