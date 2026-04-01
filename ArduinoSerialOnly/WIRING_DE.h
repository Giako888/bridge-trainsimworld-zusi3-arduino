/*
 * Anschlussplan — Arduino Leonardo Serial Only (13 LED MAX7219)
 * 
 * VEREINFACHTE Version: nur 3 Pins für LEDs (MAX7219) + USB.
 * Kein Joystick, Encoder, Tastenmatrix oder Schieberegler.
 * 
 * ============================================
 * ARDUINO LEONARDO PINBELEGUNG (Serial Only)
 * ============================================
 * 
 * Nur 3 Pins für MAX7219 + USB-Stromversorgung!
 * Alle anderen Pins sind FREI für zukünftige Verwendung.
 * 
 *              ┌────USB────┐
 *        ---  │ 1      RAW│
 *        ---  │ 0      GND│ ◄── GND
 *             │ GND    RST│
 *       GND   │ GND    VCC│ ◄── +5V
 *        ---  │ 2      A3 │ ◄── MAX7219_DIN
 *        ---  │ 3      A2 │ --- (frei)
 *        ---  │ 4      A1 │ --- (frei)
 *        ---  │ 5      A0 │ --- (frei)
 *        ---  │ 6      A5 │ ◄── MAX7219_CS
 *        ---  │ 7      A4 │ ◄── MAX7219_CLK
 *        ---  │ 8      13 │ --- (frei)
 *        ---  │ 9      12 │ --- (frei)
 *        ---  │ 10     11 │ --- (frei)
 *             └───────────┘
 * 
 * Verwendete Pins (alle am Analog-Header, nebeneinander):
 *   A3 = MAX7219_DIN
 *   A4 = MAX7219_CLK
 *   A5 = MAX7219_CS (LOAD)
 * 
 * ============================================
 * LED MAX7219 (13 LEDs mit WCMCU DISY1 Modul)
 * ============================================
 * 
 * Das MAX7219-Modul (WCMCU DISY1 Breakout) steuert alle 13 LEDs.
 * Software-SPI-Kommunikation über 3 Pins.
 * Keine einzelnen Widerstände nötig (RSET bereits auf dem Modul).
 * Alle LEDs können gleichzeitig leuchten!
 * 
 * Arduino → MAX7219 Verbindungen (IN-Seite):
 *   Pin A3               → DIN
 *   Pin A4               → CLK
 *   Pin A5               → CS (LOAD)
 *   +5V                  → VCC
 *   GND                  → GND
 * 
 * MAX7219 Verbindungen (LED-Seite):
 *
 *   DIG0:
 *     SEG_A  → LED1  SIFA (weiß/gelb)
 *     SEG_B  → LED2  LZB Ende (gelb)
 *     SEG_C  → LED3  PZB 70 (blau)
 *     SEG_D  → LED4  PZB 85 (blau)
 *     SEG_E  → LED5  PZB 55 (blau)
 *     SEG_F  → LED6  500Hz (rot)
 *     SEG_G  → LED7  1000Hz (gelb)
 *     SEG_DP → LED8  Türen Links (gelb)
 *
 *   DIG1:
 *     SEG_A  → LED9  Türen Rechts (gelb)
 *     SEG_B  → LED10 LZB Ü (blau)
 *     SEG_C  → LED11 LZB G (rot)
 *     SEG_D  → LED12 LZB S (rot)
 *     SEG_E  → LED13 Befehl 40 (gelb)
 * 
 * LED-Verdrahtungsschema:
 *   Jede LED: ANODE (+) an SEG_x Pin, KATHODE (-) an DIG_x Pin
 *
 *         MAX7219 DIG0
 *        ┌──────────────┐
 *   A ───┤►| LED1 SIFA  │─── DIG0
 *   B ───┤►| LED2 LZB   │─── DIG0
 *   C ───┤►| LED3 PZB70 │─── DIG0
 *   D ───┤►| LED4 PZB85 │─── DIG0
 *   E ───┤►| LED5 PZB55 │─── DIG0
 *   F ───┤►| LED6 500Hz │─── DIG0
 *   G ───┤►| LED7 1000Hz│─── DIG0
 *   DP ──┤►| LED8 TürenL│─── DIG0
 *        └──────────────┘
 *
 *         MAX7219 DIG1
 *        ┌──────────────┐
 *   A ───┤►| LED9 TürenR│─── DIG1
 *   B ───┤►| LED10 LZBÜ │─── DIG1
 *   C ───┤►| LED11 LZBG │─── DIG1
 *   D ───┤►| LED12 LZBS │─── DIG1
 *   E ───┤►| LED13 BEF40│─── DIG1
 *        └──────────────┘
 * 
 * ============================================
 * LED-ÜBERSICHTSTABELLE
 * ============================================
 * 
 *  LED │ MAX7219      │ Funktion                     │ Farbe
 * ─────┼──────────────┼──────────────────────────────┼─────────────
 *   1  │ DIG0.A       │ SIFA Warnung                 │ weiß/gelb
 *   2  │ DIG0.B       │ LZB Ende                     │ gelb
 *   3  │ DIG0.C       │ PZB 70 (Zugart M)            │ blau
 *   4  │ DIG0.D       │ PZB 85 (Zugart O)            │ blau
 *   5  │ DIG0.E       │ PZB 55 (Zugart U)            │ blau
 *   6  │ DIG0.F       │ 500Hz (PZB-Frequenz)         │ rot
 *   7  │ DIG0.G       │ 1000Hz (PZB-Frequenz)        │ gelb
 *   8  │ DIG0.DP      │ Türen Links                  │ gelb
 *   9  │ DIG1.A       │ Türen Rechts                 │ gelb
 *  10  │ DIG1.B       │ LZB Ü (Überwachung)          │ blau
 *  11  │ DIG1.C       │ LZB G (Geführt/aktiv)        │ rot
 *  12  │ DIG1.D       │ LZB S (Schnellbremsung)      │ rot
 *  13  │ DIG1.E       │ Befehl 40                    │ gelb
 * 
 * ============================================
 * SERIELLE BEFEHLE (115200 Baud)
 * ============================================
 * 
 *   SIFA:1     → LED1 ein  (weiß/gelb)
 *   SIFA:0     → LED1 aus
 *   LZB:1      → LED2 ein  (gelb) - LZB Ende
 *   LZB:0      → LED2 aus
 *   PZB70:1    → LED3 ein  (blau)
 *   PZB70:0    → LED3 aus
 *   PZB80:1    → LED4 ein  (blau)
 *   PZB80:0    → LED4 aus
 *   PZB50:1    → LED5 ein  (blau)
 *   PZB50:0    → LED5 aus
 *   500HZ:1    → LED6 ein  (rot)
 *   500HZ:0    → LED6 aus
 *   1000HZ:1   → LED7 ein  (gelb)
 *   1000HZ:0   → LED7 aus
 *   TUEREN_L:1 → LED8 ein  (gelb) - Türen links
 *   TUEREN_L:0 → LED8 aus
 *   TUEREN_R:1 → LED9 ein  (gelb) - Türen rechts
 *   TUEREN_R:0 → LED9 aus
 *   LZB_UE:1   → LED10 ein (blau) - Übertragung
 *   LZB_UE:0   → LED10 aus
 *   LZB_G:1    → LED11 ein (rot) - G aktiv
 *   LZB_G:0    → LED11 aus
 *   LZB_S:1    → LED12 ein (rot) - Schnellbremsung
 *   LZB_S:0    → LED12 aus
 *   BEF40:1    → LED13 ein (gelb) - Befehl 40
 *   BEF40:0    → LED13 aus
 *   LED:n:1    → LED n ein (1-13)
 *   LED:n:0    → LED n aus
 *   OFF        → Alle LEDs aus
 * 
 * ============================================
 * BAUTEILLISTE
 * ============================================
 * 
 * - 1x Arduino Leonardo (ATmega32U4)
 * - 1x MAX7219-Modul (WCMCU DISY1 Breakout)
 * - 13x LED 5mm (1 weiß/gelb, 5 gelb, 4 blau, 3 rot)
 * - Jumper-Kabel
 * - Breadboard oder Platine
 * 
 * Gesamt: ~16 Bauteile (+ Kabel)
 * Keine zusätzlichen Arduino-Bibliotheken erforderlich!
 * 
 * ============================================
 * WICHTIGE HINWEISE
 * ============================================
 * 
 * 1. Arduino Leonardo verwendet ATmega32U4 = natives USB
 *    USB-Serial (CDC) funktioniert über USB-Pins, NICHT über Pins 0/1!
 * 
 * 2. Keine externen Bibliotheken nötig (kein Joystick, kein Encoder)
 * 
 * 3. Der MAX7219 regelt den Strom intern (RSET auf dem Modul).
 *    Einzelne Widerstände pro LED sind NICHT nötig.
 * 
 * 4. Im Arduino IDE Board Manager: "Arduino Leonardo" auswählen
 * 
 * 5. Mit MAX7219 können alle LEDs gleichzeitig leuchten
 *    (im Gegensatz zu Charlieplexing, das Multiplexing verwendet).
 * 
 * 6. Alle nicht verwendeten Pins (0-13, A0-A2) bleiben frei
 *    für mögliche zukünftige Erweiterungen.
 * 
 */
