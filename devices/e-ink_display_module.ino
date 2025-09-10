/*
    Waveshare 2.13" (250x122) B/W E-Paper Demo (Arduino Nano)
    Shows the text: "BusyBox v1.0"

    Hardware (8-pin header):
        1 VCC  -> 3.3V (preferred) or 5V (module has level shifting)
        2 GND  -> GND
        3 DIN  -> D11 (MOSI)
        4 CLK  -> D13 (SCK)
        5 CS   -> D10 (chip select)
        6 DC   -> D9  (data/command)
        7 RST  -> D8  (reset)
        8 BUSY -> D7  (busy)

    Library required (Arduino Library Manager):
        Install: "GxEPD2" by Jean-Marc Zingg

    NOTE about memory:
        The 250x122 display needs ~3813 bytes for a full buffer (> 2KB SRAM of Nano).
        GxEPD2 automatically uses paged drawing with the template below to fit SRAM.

    Serial Command Interface (dynamic text update):
        Baud: 9600 (Serial Monitor must match)
        Each command is a single line terminated by Newline ("\n"). Carriage return ("\r") is ignored.

        Set top line:
            1:New Top Text\n
        Set second line:
            2:Second Line Text\n
        Special commands:
            CLEAR    -> clears both lines and refreshes display
            REFRESH  -> redraws current text (useful after unintended partial update)

        Limits / behavior:
            - Max 40 characters per line (extra characters truncated).
            - Leading spaces after the colon are trimmed.
            - Display auto-scales each line so both fit (shrinks if too wide / tall).
            - On success you get: "Updated L1 -> 'text'" or "Updated L2 -> 'text'".
            - If an input line exceeds 63 chars total, it's dropped with: "Input overflow; line dropped.".
            - Unknown commands print: "Unknown cmd: '...'."

        Examples:
            1:BusyBox Demo\n
            2:Ready!\n
            CLEAR\n
            REFRESH\n
*/

#include <GxEPD2_BW.h>

// Select the correct driver class for your specific 2.13" variant.
// For the 250x122 (V3/V4) black/white module (SSD1680) use GxEPD2_213_B74 (or _B73 depending on revision).
// If compile fails, open GxEPD2_display_selection.h example to find the matching class name and replace below.

// Pins: (CS, DC, RST, BUSY)
// Using: CS=D10, DC=D9, RST=D8, BUSY=D7
// Reduce SRAM by using a small page buffer height (e.g. 32 instead of full height 122)
GxEPD2_BW<GxEPD2_213_B74, 32> display(GxEPD2_213_B74(/*CS=*/10, /*DC=*/9, /*RST=*/8, /*BUSY=*/7));

// ---- Dynamic Text State ----
// (Keep modest lengths; Nano SRAM is limited. 40 chars * 2 lines * ~1 byte)
static char line1[41] = "BusyBox"; // initial text
static char line2[41] = "v1.0";    // initial text

// Incoming serial line buffer
static char inBuf[64];
static uint8_t inPos = 0;

// Renders the two lines with adaptive scaling so they fit width & height.
void updateDisplay() {
    display.setRotation(1); // landscape
    display.setTextColor(GxEPD_BLACK);

    const uint16_t w = display.width();
    const uint16_t h = display.height();
    const uint8_t baseCharW = 6; // 5 glyph + 1 space
    const uint8_t baseCharH = 8;

    // Desired starting sizes (can be reduced if needed)
    uint8_t size1 = 5;
    uint8_t size2 = 4;
    uint8_t gap = 12; // vertical gap between baselines
    uint8_t topMargin = 0;

    // Ensure lines fit horizontally by shrinking size while width exceeds display
    auto shrinkToFit = [&](const char* txt, uint8_t &sz){
        while (sz > 1) {
            uint16_t pw = (uint16_t)strlen(txt) * baseCharW * sz;
            if (pw <= w) break;
            sz--;
        }
    };
    shrinkToFit(line1, size1);
    shrinkToFit(line2, size2);

    // Compute geometry; adjust if total height overflows
    auto computeGeometry = [&](uint8_t s1, uint8_t s2, uint8_t &x1, uint8_t &x2, int16_t &y1, int16_t &y2, int16_t &line1H, int16_t &line2H){
        uint16_t line1PixelW = (uint16_t)strlen(line1) * baseCharW * s1;
        uint16_t line2PixelW = (uint16_t)strlen(line2) * baseCharW * s2;
        line1H = baseCharH * s1;
        line2H = baseCharH * s2;
        x1 = (uint8_t)((int)w - (int)line1PixelW) / 2;
        x2 = (uint8_t)((int)w - (int)line2PixelW) / 2;
        y1 = topMargin + line1H;
        y2 = y1 + gap + line2H;
    };

    uint8_t x1, x2; int16_t y1, y2, line1H, line2H;
    computeGeometry(size1, size2, x1, x2, y1, y2, line1H, line2H);

    // If vertical overflow, reduce sizes (prefer shrinking second line first)
    while ((y2 > (int16_t)h) && (size1 > 1 || size2 > 1)) {
        if (size2 > 1) size2--; else if (size1 > 1) size1--; else break;
        computeGeometry(size1, size2, x1, x2, y1, y2, line1H, line2H);
        if (gap > 4 && y2 > (int16_t)h) { gap -= 1; computeGeometry(size1, size2, x1, x2, y1, y2, line1H, line2H); }
    }

    display.setFullWindow();
    display.firstPage();
    do {
        display.fillScreen(GxEPD_WHITE);
        if (line1[0]) {
            display.setTextSize(size1);
            display.setCursor(x1, y1);
            display.print(line1);
        }
        if (line2[0]) {
            display.setTextSize(size2);
            display.setCursor(x2, y2);
            display.print(line2);
        }
    } while (display.nextPage());
}

// Trim leading spaces (simple)
char* ltrim(char* s) {
    while (*s == ' ' || *s == '\t') ++s; return s;
}

void processCommand(char *cmd) {
    if (!cmd[0]) return;
    // Expected format: N:Text  where N is '1' or '2'
    if ((cmd[0] == '1' || cmd[0] == '2') && cmd[1] == ':') {
        char lineIdx = cmd[0];
        char *text = ltrim(cmd + 2);
        // Truncate to fit buffer
        if (lineIdx == '1') {
            strncpy(line1, text, sizeof(line1) - 1);
            line1[sizeof(line1) - 1] = '\0';
            Serial.print(F("Updated L1 -> '")); Serial.print(line1); Serial.println('\'');
        } else {
            strncpy(line2, text, sizeof(line2) - 1);
            line2[sizeof(line2) - 1] = '\0';
            Serial.print(F("Updated L2 -> '")); Serial.print(line2); Serial.println('\'');
        }
        updateDisplay();
        return;
    }
    // Optional commands (extendable)
    if (strcmp(cmd, "REFRESH") == 0) { updateDisplay(); Serial.println(F("Manual refresh done.")); return; }
    if (strcmp(cmd, "CLEAR") == 0) { line1[0] = 0; line2[0] = 0; updateDisplay(); Serial.println(F("Cleared.")); return; }
    Serial.print(F("Unknown cmd: '")); Serial.print(cmd); Serial.println('\'');
}

void pollSerial() {
    while (Serial.available()) {
        char c = (char)Serial.read();
        if (c == '\r') continue; // ignore CR
        if (c == '\n') {
            inBuf[inPos] = '\0';
            processCommand(inBuf);
            inPos = 0; // reset buffer
        } else {
            if (inPos < sizeof(inBuf) - 1) {
                inBuf[inPos++] = c;
            } else {
                // Overflow -> reset buffer (simple strategy)
                inPos = 0;
                Serial.println(F("Input overflow; line dropped."));
            }
        }
    }
}

void setup() {
    Serial.begin(9600);
    while(!Serial && millis() < 3000) { /* wait for serial (optional) */ }
    Serial.println(F("E-Paper init..."));
    display.init(9600); // keep same baud for internal debug (if enabled)
    updateDisplay();
    Serial.println(F("Ready. Send '1:Your Text' or '2:Your Text' then newline."));
}

void loop() {
    // Non-blocking serial polling; only refresh after full command received.
    pollSerial();
}

