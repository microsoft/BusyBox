/*
    KY-040 Rotary Encoder Basic Example
    - Detects rotation direction and steps
    - Detects button press
    - Prints events to Serial
  
    Pinout (typical):
        CLK (A) -> D2
        DT  (B) -> D3
        SW      -> D4
        VCC     -> 5V
        GND     -> GND
*/

const int pinCLK = 2; // A (CLK)
const int pinDT  = 3; // B (DT)
const int pinSW  = 4; // Switch


int lastState = 0;
int lastSW = HIGH;
long encoderValue = 0;

bool DEBUG = false;

// State machine lookup table for quadrature decoding
// Each entry: [old_AB << 2 | new_AB] => -1, 0, or +1
const int8_t enc_states[] = {0, -1, 1, 0,
                             1, 0, 0, -1,
                            -1, 0, 0, 1,
                             0, 1, -1, 0};


void setup() {
    Serial.begin(9600);
    pinMode(pinCLK, INPUT_PULLUP);
    pinMode(pinDT, INPUT_PULLUP);
    pinMode(pinSW, INPUT_PULLUP);
    int a = digitalRead(pinCLK);
    int b = digitalRead(pinDT);
    lastState = (a << 1) | b;
    lastSW = digitalRead(pinSW);
    Serial.println(F("KY-040 Rotary Encoder Test (State Machine)"));
}


void loop() {
    // Rotary encoder state machine
    int a = digitalRead(pinCLK);
    int b = digitalRead(pinDT);
    int currState = (a << 1) | b;
    int idx = (lastState << 2) | currState;
    int8_t movement = enc_states[idx & 0x0F];
    if (movement != 0) {
        encoderValue += movement;
        if (DEBUG) {
            if (movement > 0) {
                Serial.print(F("Rotated CW, value: "));
                Serial.println(encoderValue);
            } else {
                Serial.print(F("Rotated CCW, value: "));
                Serial.println(encoderValue);
            }
        }
        Serial.print(F("Knob State: "));
        Serial.println(encoderValue);
    }
    lastState = currState;

    // Button
    int currentSW = digitalRead(pinSW);
    if (currentSW != lastSW) {
        delay(5); // debounce
        if (digitalRead(pinSW) == LOW) {
            Serial.println(F("Knob Button pressed"));
        } else {
            Serial.println(F("Knob Button released"));
        }
        lastSW = currentSW;
    }
}
