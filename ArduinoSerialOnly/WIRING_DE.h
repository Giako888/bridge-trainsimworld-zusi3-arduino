/*
 * Anschlussplan — Arduino Leonardo Serial Only (13 LED Charlieplexing)
 * 
 * VEREINFACHTE Version: nur 5 Pins für LEDs + USB.
 * Kein Joystick, Encoder, Tastenmatrix oder Schieberegler.
 * 
 * ============================================
 * ARDUINO LEONARDO PINBELEGUNG (Serial Only)
 * ============================================
 * 
 * Nur 5 Pins für LEDs + USB-Stromversorgung!
 * Alle anderen Pins sind FREI für zukünftige Verwendung.
 * 
 *              ┌────USB────┐
 *   LED_C (TX)│ 1      RAW│
 *   LED_B (RX)│ 0      GND│ ◄── GND
 *             │ GND    RST│
 *       GND   │ GND    VCC│ ◄── +5V
 *        ---  │ 2      A3 │ ◄── LED_A
 *        ---  │ 3      A2 │ --- (frei)
 *        ---  │ 4      A1 │ --- (frei)
 *        ---  │ 5      A0 │ --- (frei)
 *        ---  │ 6      A5 │ --- (frei)
 *        ---  │ 7      A4 │ ◄── LED_D
 *        ---  │ 8      13 │ --- (frei)
 *        ---  │ 9      12 │ --- (frei)
 *        ---  │ 10     11 │ --- (frei)
 *             └───────────┘
 * 
 * Pin 14 (MISO) befindet sich auf dem ICSP-Header (6-Pin-Header in der Mitte):
 *   ┌──────────────┐
 *   │ ►MISO(14) VCC│   ← LED_E hier
 *   │  SCK(15) MOSI│
 *   │  RST     GND │
 *   └──────────────┘
 * 
 * Verwendete Pins:
 *   A3 = LED_A (Charlieplexing Pin A)
 *    0 = LED_B (Charlieplexing Pin B) — RX, aber Serial läuft über USB!
 *    1 = LED_C (Charlieplexing Pin C) — TX, aber Serial läuft über USB!
 *   A4 = LED_D (Charlieplexing Pin D)
 *   14 = LED_E (Charlieplexing Pin E) — MISO, ICSP-Header
 * 
 * HINWEIS: Die Pins 0 (RX) und 1 (TX) am Leonardo sind für die
 * Hardware-UART (Serial1), NICHT für USB-Serial! Die serielle
 * Kommunikation mit dem PC erfolgt über natives USB (CDC), daher
 * sind diese Pins frei für LEDs.
 * 
 * ============================================
 * LED CHARLIEPLEXING (13 LEDs mit 5 Pins)
 * ============================================
 * 
 * Mit Charlieplexing können 5 Pins bis zu 20 LEDs steuern.
 * Wir verwenden 13 LEDs. Jedes Pin-Paar kann 2 LEDs treiben (eine pro Richtung).
 * 
 * Verwendete Pins: A3 (LED_A), 0 (LED_B), 1 (LED_C), A4 (LED_D), 14/MISO (LED_E)
 * 
 * WICHTIG: Jede LED benötigt einen 220Ω WIDERSTAND in Reihe!
 * Der Widerstand kommt zwischen Pin und LED-ANODE (langes Bein).
 * Die KATHODE (kurzes Bein) wird direkt mit dem anderen Pin verbunden.
 * 
 * Anschlussplan:
 * 
 *         LED1 (SIFA)               LED2 (LZB Ende)
 *    A3 ──[220Ω]──►|────────────|◄──[220Ω]── 0
 *         weiß(gelb)              gelb
 * 
 *         LED3 (PZB 70)             LED4 (PZB 85)
 *    A3 ──[220Ω]──►|────────────|◄──[220Ω]── 1
 *              blau                blau
 * 
 *         LED5 (PZB 55)             LED6 (500Hz)
 *     0 ──[220Ω]──►|────────────|◄──[220Ω]── 1
 *              blau                rot
 * 
 *         LED7 (1000Hz)             LED8 (Türen Links)
 *    A3 ──[220Ω]──►|────────────|◄──[220Ω]── A4
 *             gelb                gelb
 * 
 *         LED9 (Türen Rechts)
 *     0 ──[220Ω]──►|──────────── A4
 *             gelb
 * 
 *         LED10 (LZB Ü)
 *     1 ──[220Ω]──►|──────────── A4
 *              blau
 * 
 *         LED11 (LZB G)
 *    A4 ──[220Ω]──►|──────────── 0
 *             rot
 * 
 *         LED12 (LZB S)
 *    A4 ──[220Ω]──►|──────────── 1
 *             rot
 * 
 *         LED13 (Befehl 40)
 *    A3 ──[220Ω]──►|──────────── 14 (MISO, ICSP)
 *             gelb
 * 
 * ============================================
 * LED-ÜBERSICHTSTABELLE
 * ============================================
 * 
 *  LED │ Richtung  │ Funktion                     │ Farbe
 * ─────┼───────────┼──────────────────────────────┼─────────────
 *   1  │ A3 → 0    │ SIFA Warnung                 │ weiß/gelb
 *   2  │  0 → A3   │ LZB Ende                     │ gelb
 *   3  │ A3 → 1    │ PZB 70 (Zugart M)            │ blau
 *   4  │  1 → A3   │ PZB 85 (Zugart O)            │ blau
 *   5  │  0 → 1    │ PZB 55 (Zugart U)            │ blau
 *   6  │  1 → 0    │ 500Hz (PZB-Frequenz)         │ rot
 *   7  │ A3 → A4   │ 1000Hz (PZB-Frequenz)        │ gelb
 *   8  │ A4 → A3   │ Türen Links                  │ gelb
 *   9  │  0 → A4   │ Türen Rechts                 │ gelb
 *  10  │  1 → A4   │ LZB Ü (Überwachung)          │ blau
 *  11  │ A4 → 0    │ LZB G (Geführt/aktiv)        │ rot
 *  12  │ A4 → 1    │ LZB S (Schnellbremsung)      │ rot
 *  13  │ A3 → 14   │ Befehl 40                    │ gelb
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
 * - 13x LED 5mm (1 weiß/gelb, 5 gelb, 4 blau, 3 rot)
 * - 13x Widerstand 220Ω
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
 * 3. Widerstandsberechnung: R = (5V - 3,2V) / 8mA ≈ 225Ω → verwende 220Ω
 * 
 * 4. Im Arduino IDE Board Manager: "Arduino Leonardo" auswählen
 * 
 * 5. LED-Multiplexing läuft mit ~62Hz (2ms pro LED), schnell genug
 *    um dem menschlichen Auge als Dauerlicht zu erscheinen.
 * 
 * 6. Alle nicht verwendeten Pins (2-13, A0-A2, A5) bleiben frei
 *    für mögliche zukünftige Erweiterungen.
 *    Pins 15 (SCK) und 16 (MOSI) am ICSP-Header sind ebenfalls frei.
 * 
 */
