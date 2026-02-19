/*
 * Wiring Diagram — Arduino Leonardo Serial Only (13 LED Charlieplexing)
 * 
 * SIMPLIFIED version: only 5 pins for LEDs + USB.
 * No joystick, encoder, button matrix or sliders.
 * 
 * ============================================
 * ARDUINO LEONARDO PINOUT (Serial Only)
 * ============================================
 * 
 * Only 5 pins used for LEDs + USB power!
 * All other pins are FREE for future use.
 * 
 *              ┌────USB────┐
 *   LED_C (TX)│ 1      RAW│
 *   LED_B (RX)│ 0      GND│ ◄── GND
 *             │ GND    RST│
 *       GND   │ GND    VCC│ ◄── +5V
 *        ---  │ 2      A3 │ ◄── LED_A
 *        ---  │ 3      A2 │ --- (free)
 *        ---  │ 4      A1 │ --- (free)
 *        ---  │ 5      A0 │ --- (free)
 *        ---  │ 6      A5 │ --- (free)
 *        ---  │ 7      A4 │ ◄── LED_D
 *        ---  │ 8      13 │ --- (free)
 *        ---  │ 9      12 │ --- (free)
 *        ---  │ 10     11 │ --- (free)
 *             └───────────┘
 * 
 * Pin 14 (MISO) is on the ICSP header (6-pin header in the center of the board):
 *   ┌──────────────┐
 *   │ ►MISO(14) VCC│   ← LED_E here
 *   │  SCK(15) MOSI│
 *   │  RST     GND │
 *   └──────────────┘
 * 
 * Pins used:
 *   A3 = LED_A (Charlieplexing pin A)
 *    0 = LED_B (Charlieplexing pin B) — RX, but Serial is on USB!
 *    1 = LED_C (Charlieplexing pin C) — TX, but Serial is on USB!
 *   A4 = LED_D (Charlieplexing pin D)
 *   14 = LED_E (Charlieplexing pin E) — MISO, ICSP header
 * 
 * NOTE: Pins 0 (RX) and 1 (TX) on the Leonardo are for the hardware
 * UART (Serial1), NOT for USB Serial! Serial communication with the
 * PC uses native USB (CDC), so these pins are free for LEDs.
 * 
 * ============================================
 * LED CHARLIEPLEXING (13 LEDs with 5 pins)
 * ============================================
 * 
 * With Charlieplexing, 5 pins can control up to 20 LEDs.
 * We use 13 LEDs. Each pin pair can drive 2 LEDs (one per direction).
 * 
 * Pins used: A3 (LED_A), 0 (LED_B), 1 (LED_C), A4 (LED_D), 14/MISO (LED_E)
 * 
 * IMPORTANT: Each LED needs a 220Ω RESISTOR in series!
 * The resistor goes between the pin and the LED ANODE (long leg).
 * The CATHODE (short leg) goes directly to the other pin.
 * 
 * Wiring diagram:
 * 
 *         LED1 (SIFA)               LED2 (LZB Ende)
 *    A3 ──[220Ω]──►|────────────|◄──[220Ω]── 0
 *         white(yellow)           yellow
 * 
 *         LED3 (PZB 70)             LED4 (PZB 85)
 *    A3 ──[220Ω]──►|────────────|◄──[220Ω]── 1
 *              blue                blue
 * 
 *         LED5 (PZB 55)             LED6 (500Hz)
 *     0 ──[220Ω]──►|────────────|◄──[220Ω]── 1
 *              blue                red
 * 
 *         LED7 (1000Hz)             LED8 (Doors Left)
 *    A3 ──[220Ω]──►|────────────|◄──[220Ω]── A4
 *             yellow              yellow
 * 
 *         LED9 (Doors Right)
 *     0 ──[220Ω]──►|──────────── A4
 *             yellow
 * 
 *         LED10 (LZB Ü)
 *     1 ──[220Ω]──►|──────────── A4
 *              blue
 * 
 *         LED11 (LZB G)
 *    A4 ──[220Ω]──►|──────────── 0
 *             red
 * 
 *         LED12 (LZB S)
 *    A4 ──[220Ω]──►|──────────── 1
 *             red
 * 
 *         LED13 (Befehl 40)
 *    A3 ──[220Ω]──►|──────────── 14 (MISO, ICSP)
 *             yellow
 * 
 * ============================================
 * LED SUMMARY TABLE
 * ============================================
 * 
 *  LED │ Direction │ Function                     │ Color
 * ─────┼───────────┼──────────────────────────────┼─────────────
 *   1  │ A3 → 0    │ SIFA Warning                 │ white/yellow
 *   2  │  0 → A3   │ LZB Ende                     │ yellow
 *   3  │ A3 → 1    │ PZB 70 (Zugart M)            │ blue
 *   4  │  1 → A3   │ PZB 85 (Zugart O)            │ blue
 *   5  │  0 → 1    │ PZB 55 (Zugart U)            │ blue
 *   6  │  1 → 0    │ 500Hz (PZB frequency)        │ red
 *   7  │ A3 → A4   │ 1000Hz (PZB frequency)       │ yellow
 *   8  │ A4 → A3   │ Doors Left (Türen L)         │ yellow
 *   9  │  0 → A4   │ Doors Right (Türen R)        │ yellow
 *  10  │  1 → A4   │ LZB Ü (Überwachung)          │ blue
 *  11  │ A4 → 0    │ LZB G (Geführt/active)       │ red
 *  12  │ A4 → 1    │ LZB S (Schnellbremsung)      │ red
 *  13  │ A3 → 14   │ Befehl 40                    │ yellow
 * 
 * ============================================
 * SERIAL COMMANDS (115200 baud)
 * ============================================
 * 
 *   SIFA:1     → Turn on LED1  (white/yellow)
 *   SIFA:0     → Turn off LED1
 *   LZB:1      → Turn on LED2  (yellow) - LZB Ende
 *   LZB:0      → Turn off LED2
 *   PZB70:1    → Turn on LED3  (blue)
 *   PZB70:0    → Turn off LED3
 *   PZB80:1    → Turn on LED4  (blue)
 *   PZB80:0    → Turn off LED4
 *   PZB50:1    → Turn on LED5  (blue)
 *   PZB50:0    → Turn off LED5
 *   500HZ:1    → Turn on LED6  (red)
 *   500HZ:0    → Turn off LED6
 *   1000HZ:1   → Turn on LED7  (yellow)
 *   1000HZ:0   → Turn off LED7
 *   TUEREN_L:1 → Turn on LED8  (yellow) - doors left
 *   TUEREN_L:0 → Turn off LED8
 *   TUEREN_R:1 → Turn on LED9  (yellow) - doors right
 *   TUEREN_R:0 → Turn off LED9
 *   LZB_UE:1   → Turn on LED10 (blue) - Übertragung
 *   LZB_UE:0   → Turn off LED10
 *   LZB_G:1    → Turn on LED11 (red) - G active
 *   LZB_G:0    → Turn off LED11
 *   LZB_S:1    → Turn on LED12 (red) - Schnellbremsung
 *   LZB_S:0    → Turn off LED12
 *   BEF40:1    → Turn on LED13 (yellow) - Befehl 40
 *   BEF40:0    → Turn off LED13
 *   LED:n:1    → Turn on LED n (1-13)
 *   LED:n:0    → Turn off LED n
 *   OFF        → Turn off all LEDs
 * 
 * ============================================
 * COMPONENTS LIST
 * ============================================
 * 
 * - 1x Arduino Leonardo (ATmega32U4)
 * - 13x 5mm LED (1 white/yellow, 5 yellow, 4 blue, 3 red)
 * - 13x 220Ω Resistor
 * - Jumper wires
 * - Breadboard or PCB
 * 
 * Total: ~16 components (+ wires)
 * No extra Arduino libraries required!
 * 
 * ============================================
 * IMPORTANT NOTES
 * ============================================
 * 
 * 1. Arduino Leonardo uses ATmega32U4 = native USB
 *    USB Serial (CDC) works on USB pins, NOT on pins 0/1!
 * 
 * 2. No external libraries needed (no Joystick, no Encoder)
 * 
 * 3. Resistor calculation: R = (5V - 3.2V) / 8mA ≈ 225Ω → use 220Ω
 * 
 * 4. In Arduino IDE Board Manager: select "Arduino Leonardo"
 * 
 * 5. LED multiplexing runs at ~62Hz (2ms per LED), fast enough
 *    to appear as continuous light to the human eye.
 * 
 * 6. All unused pins (2-13, A0-A2, A5) remain free
 *    for potential future expansions.
 *    Pins 15 (SCK) and 16 (MOSI) on the ICSP header are also free.
 * 
 */
