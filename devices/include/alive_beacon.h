#pragma once
/*
  alive_beacon.h
  Periodic identity beacon that can also emit a second line of current device data.

  Sketch usage:
    #define MODULE_NAME "buttons_module"
    #include <alive_beacon.h>
    void myDataLine() { Serial.println(F("Button States: D2=1 D3=0 ...")); }
    setAliveDataPrinter(myDataLine); // (in setup, before initAliveBeacon)
    initAliveBeacon();
    // In loop: runAliveBeacon();

  The beacon prints:
    <MODULE_NAME>\n
    <data-line>\n   (if a printer callback was registered)

  Notes:
    - Non-blocking (millis scheduling).
    - Randomized initial phase to reduce collision.
    - If no data printer set, only identity line is printed.
*/
#ifndef MODULE_NAME
#warning "MODULE_NAME not defined before including alive_beacon.h; defaulting to unknown_module"
#define MODULE_NAME "unknown_module"
#endif

#ifndef ALIVE_INTERVAL_MS
// Default steady-state beacon interval (user requested 1s)
#define ALIVE_INTERVAL_MS 1000UL
#endif

typedef void (*AliveDataPrinter)();

static unsigned long _alive_next_due_ms = 0;      // scheduling
static AliveDataPrinter _alive_printer = nullptr; // optional data callback

inline void setAliveDataPrinter(AliveDataPrinter cb) { _alive_printer = cb; }

inline void initAliveBeacon() {
  randomSeed(analogRead(A0));
  unsigned long now = millis();
#ifdef ALIVE_IMMEDIATE_FIRST
  _alive_next_due_ms = now; // immediate first publish
#else
  // Randomize first beacon anywhere within the first interval (0 .. ALIVE_INTERVAL_MS-1)
  // to decorrelate multiple modules starting together.
  unsigned long interval = ALIVE_INTERVAL_MS ? ALIVE_INTERVAL_MS : 1000UL;
  unsigned long phase = (unsigned long)random(interval); // 0..interval-1
  _alive_next_due_ms = now + phase;
#endif
}

inline void runAliveBeacon() {
  unsigned long now = millis();
  if ((long)(now - _alive_next_due_ms) >= 0) {
    Serial.println(F(MODULE_NAME));       // identity line
    if (_alive_printer) { _alive_printer(); } // data line (must end with newline)
    _alive_next_due_ms += ALIVE_INTERVAL_MS;
    if ((long)(now - _alive_next_due_ms) >= 0) {
      _alive_next_due_ms = now + ALIVE_INTERVAL_MS;
    }
  }
}
