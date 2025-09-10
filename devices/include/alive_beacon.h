#pragma once
/*
  alive_beacon.h (shared include)
  Non-blocking periodic identity beacon for Arduino modules.

  Usage (in each module .ino BEFORE including this file):
    #define MODULE_NAME "buttons_module"            // REQUIRED exact identity string
    // #define ALIVE_INTERVAL_MS 5000UL             // (Optional) override default interval
    #include "../include/alive_beacon.h"           // path relative to sketch file

  In setup():
    initAliveBeacon();

  In loop():
    runAliveBeacon();

  Notes:
    - Keeps baud at whatever the sketch sets (e.g. Serial.begin(9600)).
    - First beacon randomizes initial phase to reduce collisions.
    - Uses millis() (no delay) so it won't block.
    - Ensure the analog pin used for randomSeed() is floating / unused (A0 here).
*/
#ifndef MODULE_NAME
#warning "MODULE_NAME not defined before including alive_beacon.h; defaulting to unknown_module"
#define MODULE_NAME "unknown_module"
#endif

#ifndef ALIVE_INTERVAL_MS
#define ALIVE_INTERVAL_MS 5000UL
#endif

static unsigned long _alive_next_due_ms = 0; // internal scheduling variable

inline void initAliveBeacon() {
  randomSeed(analogRead(A0));
  unsigned long interval = ALIVE_INTERVAL_MS;
  if (interval < 600UL) interval = 600UL; // guard minimal interval
  unsigned long spread = interval > 1000UL ? (interval - 1000UL) : 1UL; // space after +/- 500
  if ((long)spread <= 0) spread = 1;
  unsigned long phase = 500UL + (unsigned long)random(spread);
  _alive_next_due_ms = millis() + phase;
}

inline void runAliveBeacon() {
  unsigned long now = millis();
  if ((long)(now - _alive_next_due_ms) >= 0) {
    Serial.println(F(MODULE_NAME)); // EXACT output line
    _alive_next_due_ms += ALIVE_INTERVAL_MS;
    if ((long)(now - _alive_next_due_ms) >= 0) { // catch-up or millis wrap
      _alive_next_due_ms = now + ALIVE_INTERVAL_MS;
    }
  }
}
