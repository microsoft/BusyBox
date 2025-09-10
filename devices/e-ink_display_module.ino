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
*/

#include <GxEPD2_BW.h>

// Select the correct driver class for your specific 2.13" variant.
// For the 250x122 (V3/V4) black/white module (SSD1680) use GxEPD2_213_B74 (or _B73 depending on revision).
// If compile fails, open GxEPD2_display_selection.h example to find the matching class name and replace below.

// Pins: (CS, DC, RST, BUSY)
// Using: CS=D10, DC=D9, RST=D8, BUSY=D7
// Reduce SRAM by using a small page buffer height (e.g. 32 instead of full height 122)
GxEPD2_BW<GxEPD2_213_B74, 32> display(GxEPD2_213_B74(/*CS=*/10, /*DC=*/9, /*RST=*/8, /*BUSY=*/7));

void showMessage() {
    display.setRotation(1); // 1 = landscape (optional)
    display.setTextColor(GxEPD_BLACK);
    const char *msg1 = "BusyBox";
    const char *msg2 = "v1.0";
    // Use built‑in font with scaling (setTextSize) for larger text without extra font tables.
    uint16_t w = display.width();
    uint16_t h = display.height();
    const uint8_t baseCharW = 6; // 5 glyph + 1 spacing
    const uint8_t baseCharH = 8;
    uint8_t size1 = 5; // larger first line
    uint8_t size2 = 4; // larger second line
    uint8_t gap   = 12; // pixels between lines
    uint8_t topMargin = 0; // move block further upward

    uint16_t line1PixelW = strlen(msg1) * baseCharW * size1;
    uint16_t line2PixelW = strlen(msg2) * baseCharW * size2;
    int16_t x1 = (int16_t)((int)w - (int)line1PixelW) / 2;
    int16_t x2 = (int16_t)((int)w - (int)line2PixelW) / 2;
    int16_t line1PixelH = baseCharH * size1;
    int16_t line2PixelH = baseCharH * size2;
    int16_t y1 = topMargin + line1PixelH;          // baseline for first line
    int16_t y2 = y1 + gap + line2PixelH;           // baseline for second line
    // Simple overflow guard: if y2 exceeds display, reduce sizes
    if (y2 > (int16_t)h) {
        // Fallback sizes if overflow
        size1 = 4; size2 = 3; gap = 10; topMargin = 8;
        line1PixelW = strlen(msg1) * baseCharW * size1;
        line2PixelW = strlen(msg2) * baseCharW * size2;
        x1 = (int16_t)((int)w - (int)line1PixelW) / 2;
        x2 = (int16_t)((int)w - (int)line2PixelW) / 2;
        line1PixelH = baseCharH * size1;
        line2PixelH = baseCharH * size2;
        y1 = topMargin + line1PixelH;
        y2 = y1 + gap + line2PixelH;
    }
    display.setFullWindow();
    display.firstPage();
    do {
        display.fillScreen(GxEPD_WHITE);
        display.setTextSize(size1);
        display.setCursor(x1, y1);
        display.print(msg1);
        display.setTextSize(size2);
        display.setCursor(x2, y2);
        display.print(msg2);
    } while (display.nextPage());
}

void setup() {
    Serial.begin(9600);
    while(!Serial && millis() < 3000) { /* wait for serial (optional) */ }
    Serial.println(F("E-Paper init..."));
        display.init(115200); // fast SPI; paged buffer reduces SRAM use
    showMessage();
    Serial.println(F("Done. Display will retain image with power removed."));
}

void loop() {
    // Nothing. Image persists until next refresh.
}

