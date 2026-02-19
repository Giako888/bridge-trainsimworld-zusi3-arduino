/*
 * Wiring Diagram — Arduino Leonardo Joystick + 13 LED Charlieplexing
 * 
 * ============================================
 * ARDUINO LEONARDO PINOUT
 * ============================================
 * 
 *             ┌────USB────┐
 *    LED_C  ─►│ 1      RAW│
 *    LED_B  ─►│ 0      GND│ ◄── GND
 *             │ GND    RST│
 *       GND   │ GND    VCC│ ◄── +5V
 *   ENC_CLK ─►│ 2      A3 │ ◄── LED_A
 *   ENC_DT  ─►│ 3      A2 │ ◄── SLIDER_Z (wiper)
 *   COL4    ─►│ 4      A1 │ ◄── SLIDER_Y (wiper)
 *   ROW0    ─►│ 5      A0 │ ◄── SLIDER_X (wiper)
 *   ROW1    ─►│ 6      A5 │ ◄── COL5 (new!)
 *   ROW2    ─►│ 7      A4 │ ◄── LED_D (new!)
 *   ROW3    ─►│ 8      13 │ ◄── COL3
 *   ROW4    ─►│ 9      12 │ ◄── COL2
 *   COL0    ─►│ 10     11 │ ◄── COL1
 *             └───────────┘
 * 
 * LED Charlieplexing: A3 (LED_A), 0 (LED_B), 1 (LED_C), A4 (LED_D), 14/MISO (LED_E)
 *
 * NOTE: Pin 14 (MISO) is on the ICSP header, NOT on the standard header.
 *       Solder a wire to the MISO pin of the ICSP header (6-pin center).
 *       ICSP header (top view):
 *         ┌──────────────┐
 *         │ ►MISO(14) VCC│
 *         │  SCK(15) MOSI│
 *         │  RST     GND │
 *         └──────────────┘
 * 
 * ============================================
 * BUTTON MATRIX 5x6 (30 positions!)
 * ============================================
 * 
 * The matrix handles ALL switches, buttons, rotary selectors AND encoder click!
 * Allows simultaneous key presses.
 * 
 * Layout:
 * 
 *              COL0     COL1     COL2     COL3     COL4     COL5
 *              (10)     (11)     (12)     (13)     (4)      (A5)
 *               │        │        │        │        │        │
 * ROW0 (5) ─────┼─BTN1───┼─ROT4_1─┼─ROT4_2─┼─ROT4_3─┼─ROT4_4─┼─ENC_SW
 *               │/PEDAL  │        │        │        │        │
 * ROW1 (6) ─────┼─SW1_UP─┼─SW2_UP─┼─SW3_UP─┼─SW4_UP─┼─SW5_UP─┼─TOG1_UP
 *               │        │        │        │        │        │
 * ROW2 (7) ─────┼─SW1_DN─┼─SW2_DN─┼─SW3_DN─┼─SW4_DN─┼─SW5_DN─┼─TOG1_DN
 *               │        │        │        │        │        │
 * ROW3 (8) ─────┼─SW6_UP─┼─SW7_UP─┼─SW8_UP─┼─ROT3_1─┼─ROT3_2─┼─TOG2_UP
 *               │        │        │        │        │        │
 * ROW4 (9) ─────┼─SW6_DN─┼─SW7_DN─┼─SW8_DN─┼─(empty)┼─(empty)┼─TOG2_DN
 *               │        │        │        │        │        │
 * 
 * Total elements: 28
 * - 8 ON-OFF-ON switches (SW1-SW8): 16 positions
 * - TOGGLE1 self-lock: 2 positions
 * - TOGGLE2 self-lock: 2 positions
 * - ROT4 (4 pos): 4 positions
 * - ROT3 (2 active pos): 2 positions
 * - BTN1/PEDAL (parallel): 1 position
 * - ENC_SW: 1 position
 * 
 * ============================================
 * JOYSTICK BUTTON MAPPING
 * ============================================
 * 
 * Button │ Function
 * ───────┼──────────────────────────
 *    0   │ SW1_UP (switch 1 up)
 *    1   │ SW1_DN (switch 1 down)
 *    2   │ SW2_UP
 *    3   │ SW2_DN
 *    4   │ SW3_UP
 *    5   │ SW3_DN
 *    6   │ SW4_UP
 *    7   │ SW4_DN
 *    8   │ SW5_UP
 *    9   │ SW5_DN
 *   10   │ SW6_UP
 *   11   │ SW6_DN
 *   12   │ SW7_UP
 *   13   │ SW7_DN
 *   14   │ SW8_UP
 *   15   │ SW8_DN
 *   16   │ ENC_SW (encoder click)
 *   17   │ BTN1/PEDAL (in parallel)
 *   18   │ ROT4_1 (4-pos rotary - 1)
 *   19   │ ROT4_2 (4-pos rotary - 2)
 *   20   │ ROT4_3 (4-pos rotary - 3)
 *   21   │ ROT4_4 (4-pos rotary - 4)
 *   22   │ TOG1_UP (self-lock toggle up)
 *   23   │ TOG1_DN (self-lock toggle down)
 *   24   │ ROT3_1 (3-pos rotary - 1)
 *   25   │ ROT3_2 (3-pos rotary - 2)
 *   26   │ TOG2_UP (self-lock toggle2 up)
 *   27   │ TOG2_DN (self-lock toggle2 down)
 * 
 * ============================================
 * ON-OFF-ON SWITCH WIRING (8 switches)
 * ============================================
 * 
 * Each switch has 3 terminals:
 * 
 *        [UP]  ────► Corresponding UP row
 *          │
 *    [COMMON] ────► Corresponding column
 *          │
 *        [DOWN] ──► Corresponding DN row
 * 
 * WARNING: With the matrix, wiring is different!
 * Do NOT connect commons to GND. Use DIODES!
 * 
 * SWITCH CONNECTION TABLE:
 * 
 * Switch │ COMMON (COL) │ UP (ROW)    │ DOWN (ROW)
 * ───────┼──────────────┼─────────────┼───────────
 *   1    │ Pin 10 (COL0)│ Pin 6 (ROW1)│ Pin 7 (ROW2)
 *   2    │ Pin 11 (COL1)│ Pin 6 (ROW1)│ Pin 7 (ROW2)
 *   3    │ Pin 12 (COL2)│ Pin 6 (ROW1)│ Pin 7 (ROW2)
 *   4    │ Pin 13 (COL3)│ Pin 6 (ROW1)│ Pin 7 (ROW2)
 *   5    │ Pin 4 (COL4) │ Pin 6 (ROW1)│ Pin 7 (ROW2)
 *   6    │ Pin 10 (COL0)│ Pin 8 (ROW3)│ Pin 9 (ROW4)
 *   7    │ Pin 11 (COL1)│ Pin 8 (ROW3)│ Pin 9 (ROW4)
 *   8    │ Pin 12 (COL2)│ Pin 8 (ROW3)│ Pin 9 (ROW4)
 * 
 * ============================================
 * SELF-LOCK TOGGLE SWITCHES (ON-OFF-ON)
 * ============================================
 * 
 * Similar to ON-OFF-ON switches but SELF-LOCK!
 * They maintain position when released (don't spring back to center).
 * 
 * TOGGLE1 (self-lock ON-OFF-ON, 3 terminals):
 *   - UP terminal: Pin 6 (ROW1) with diode
 *   - COMMON: Pin A5 (COL5)
 *   - DOWN terminal: Pin 7 (ROW2) with diode
 * 
 * Diagram with diodes:
 *   Pin 6 (ROW1) ──|◄── [UP]
 *                           │
 *                      [COMMON] ──── Pin A5 (COL5)
 *                           │
 *   Pin 7 (ROW2) ──|◄── [DOWN]
 * 
 * Operation:
 *   - UP position   → Button 22 = 1, Button 23 = 0
 *   - OFF position  → Button 22 = 0, Button 23 = 0
 *   - DOWN position → Button 22 = 0, Button 23 = 1
 * 
 * TOGGLE2 (self-lock ON-OFF-ON, 3 terminals):
 *   - UP terminal: Pin 8 (ROW3) with diode
 *   - COMMON: Pin A5 (COL5)
 *   - DOWN terminal: Pin 9 (ROW4) with diode
 * 
 * Diagram with diodes:
 *   Pin 8 (ROW3) ──|◄── [UP]
 *                           │
 *                      [COMMON] ──── Pin A5 (COL5)
 *                           │
 *   Pin 9 (ROW4) ──|◄── [DOWN]
 * 
 * Operation:
 *   - UP position   → Button 26 = 1, Button 27 = 0
 *   - OFF position  → Button 26 = 0, Button 27 = 0
 *   - DOWN position → Button 26 = 0, Button 27 = 1
 * 
 * ============================================
 * ROTARY SWITCH 4 POSITIONS (ROT4: 4 ON)
 * ============================================
 * 
 * Rotary selector with 4 positions: 1, 2, 3, 4 (no OFF!)
 * Has 5 terminals: COMMON + 4 positions
 * 
 * ROT4 wiring:
 *   Pos 1: Pin 5 (ROW0) ──|◄── Pin 11 (COL1)
 *   Pos 2: Pin 5 (ROW0) ──|◄── Pin 12 (COL2)
 *   Pos 3: Pin 5 (ROW0) ──|◄── Pin 13 (COL3)
 *   Pos 4: Pin 5 (ROW0) ──|◄── Pin 4 (COL4)
 * 
 * Operation:
 *   - Pos 1 → Button 18 = 1
 *   - Pos 2 → Button 19 = 1
 *   - Pos 3 → Button 20 = 1
 *   - Pos 4 → Button 21 = 1
 * 
 * NOTE: The 4-position rotary has no OFF!
 *       One position is always active.
 * 
 * ============================================
 * ROTARY SWITCH 3 POSITIONS (ROT3: OFF + 2)
 * ============================================
 * 
 * Rotary selector with 3 positions: OFF, 1, 2
 * Has 3 terminals: COMMON + 2 positions
 * 
 * ROT3 wiring:
 *   Pos 1: Pin 8 (ROW3) ──|◄── Pin 13 (COL3)
 *   Pos 2: Pin 8 (ROW3) ──|◄── Pin 4 (COL4)
 * 
 * Operation:
 *   - OFF    → All 0
 *   - Pos 1  → Button 24 = 1
 *   - Pos 2  → Button 25 = 1
 * 
 * ============================================
 * ANTI-GHOSTING DIODES (1N4148 DO-35)
 * ============================================
 * 
 * Every switch/button has a 1N4148 diode:
 * 
 *   [ROW pin] ────|◄────[SWITCH]──────── [COL pin]
 *                 ▲
 *            CATHODE (black band)
 *            towards the ROW pin
 * 
 * Total diodes: ~23 (depends on configuration)
 * 
 * ============================================
 * BTN1 AND PEDAL (IN PARALLEL)
 * ============================================
 * 
 * BTN1 and PEDAL are connected IN PARALLEL to the same matrix slot!
 * Pressing either one activates button 17.
 * 
 * Diagram (both with diode towards ROW0):
 *   Pin 5 (ROW0) ──|◄── [BTN1]  ──┬── Pin 10 (COL0)
 *   Pin 5 (ROW0) ──|◄── [PEDAL] ──┘
 * 
 * ============================================
 * ENCODER CLICK (ENC_SW)
 * ============================================
 * 
 * The encoder click is in the matrix:
 *   Pin 5 (ROW0) ──|◄── [ENC_SW] ──── Pin A5 (COL5)
 * 
 * ============================================
 * 100mm SLIDER POTENTIOMETERS WITH CAPACITORS
 * ============================================
 * 
 * Each B10K slider (10kΩ linear 100mm) with 100nF capacitor (104):
 *   - Left pin   → GND
 *   - Center pin → Analog pin + Capacitor
 *   - Right pin  → +5V
 * 
 * Diagram:
 *          +5V
 *           │
 *     [SLIDER B10K]
 *       ══════════
 *           │
 *    Pin A ─┼───┤├──── GND
 *           │   104 (100nF)
 *        (wiper)
 * 
 * SLIDER 1 (X axis): center → A0 + 100nF capacitor to GND
 * SLIDER 2 (Y axis): center → A1 + 100nF capacitor to GND
 * SLIDER 3 (Z axis): center → A2 + 100nF capacitor to GND
 * 
 * ============================================
 * ROTARY ENCODER
 * ============================================
 * 
 * EC11 encoder with push button (5 pins):
 *   - GND → GND
 *   - +   → +5V
 *   - SW  → MATRIX (ROW0-COL5, i.e. pin 5 and pin A5)
 *   - DT  → Pin 3 (interrupt)
 *   - CLK → Pin 2 (interrupt)
 * 
 * NOTE: The encoder click is in the matrix!
 *       Connect SW between ROW0 (pin 5) and COL5 (pin A5) with diode.
 * 
 * ============================================
 * LED CHARLIEPLEXING (13 LEDs with 5 pins!)
 * ============================================
 * 
 * With Charlieplexing, 5 pins can control up to 20 LEDs.
 * We use 13 LEDs.
 * 
 * Pins used: A3 (LED_A), 0 (LED_B), 1 (LED_C), A4 (LED_D), 14/MISO (LED_E)
 * 
 * IMPORTANT: Each LED needs a RESISTOR in series!
 * 
 * All LEDs are high-Vf (3-6V) with colored plastic.
 * LED1 (SIFA) is a white LED with yellow casing.
 * 
 * Resistor calculation (I ≈ 8mA):
 *   LED (Vf ≈ 3.2V): R = (5-3.2)/0.008 = 225Ω → use 220Ω
 * 
 * Wiring diagram (each LED has its own 220Ω resistor):
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
 *         LED9 (Doors Right)         LED10 (LZB Ü)
 *     0 ──[220Ω]──►|────────────|◄──[220Ω]── A4
 *             yellow               blue
 * 
 *                                   (NB: LED9 is 0→A4, LED10 is 1→A4)
 *         LED10 (LZB Ü)
 *     1 ──[220Ω]──►|──────────── A4
 *              blue
 * 
 *         LED11 (LZB G)             LED12 (LZB S)
 *    A4 ──[220Ω]──►|────────────|◄──[220Ω]── (none)
 *              blue                red
 *    (LED11: A4→0)              (LED12: A4→1)
 * 
 *         LED13 (Befehl 40)
 *    A3 ──[220Ω]──►|──────────── 14 (MISO, ICSP)
 *             yellow
 *    (LED13: A3→14)
 * 
 * NOTE: The resistor ALWAYS goes between the pin and the LED ANODE!
 *       The anode is the LONG leg of the LED.
 *       The cathode (short leg) goes towards the other pin.
 * 
 * LED table:
 *   LED1:  A3→0  = SIFA Warning (white/yellow, 220Ω)
 *   LED2:  0→A3  = LZB Ende (yellow, 220Ω)
 *   LED3:  A3→1  = PZB 70 (blue, 220Ω)
 *   LED4:  1→A3  = PZB 85 (blue, 220Ω)
 *   LED5:  0→1   = PZB 55 (blue, 220Ω)
 *   LED6:  1→0   = 500Hz (red, 220Ω)
 *   LED7:  A3→A4 = 1000Hz (yellow, 220Ω)
 *   LED8:  A4→A3 = Doors Left (yellow, 220Ω)
 *   LED9:  0→A4  = Doors Right (yellow, 220Ω)
 *   LED10: 1→A4  = LZB Ü (blue, 220Ω)
 *   LED11: A4→0  = LZB G (red, 220Ω)
 *   LED12: A4→1  = LZB S (red, 220Ω)
 *   LED13: A3→14  = Befehl 40 (yellow, 220Ω)
 * 
 * Serial commands (115200 baud):
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
 * - 3x 100mm Slider Potentiometer B10K
 * - 1x EC11 Rotary Encoder with push button
 * - 8x Momentary ON-OFF-ON Switch (SW1-SW8, spring back to center)
 * - 2x Self-lock ON-OFF-ON Switch (TOGGLE1, TOGGLE2, maintain position)
 * - 1x 4-position Rotary Switch (ROT4: 4 ON, no OFF)
 * - 1x 3-position Rotary Switch (ROT3: OFF + 2)
 * - 1x Momentary Push Button (BTN1)
 * - 1x Foot Switch (pedal)
 * - 3x Ceramic Capacitor 100nF (104)
 * - ~25x 1N4148 DO-35 Diode (matrix)
 * - 13x 5mm LED (1 white/yellow, 5 yellow, 4 blue, 3 red)
 * - 13x 220Ω Resistor (all LEDs)
 * - Jumper wires
 * - Breadboard or PCB
 * 
 * REQUIRED LIBRARIES:
 * - Joystick (Matthew Heironimus) — from GitHub
 * - Encoder (Paul Stoffregen) — from Library Manager
 * 
 * ============================================
 * IMPORTANT NOTES
 * ============================================
 * 
 * 1. Arduino Leonardo uses ATmega32U4 = native USB
 * 
 * 2. Pins 2 and 3 have hardware interrupts for the encoder
 * 
 * 3. TX/RX (pins 0 and 1) used for LED Charlieplexing
 *    USB Serial still works (it's on USB, not on pins!)
 * 
 * 4. The Leonardo has more pins than the Pro Micro:
 *    - Pins 11, 12, 13 directly accessible
 *    - Pins A4, A5 accessible
 *    - Pins 14 (MISO), 15 (SCK), 16 (MOSI) on ICSP header
 * 
 * 5. The 5x6 matrix allows simultaneous key presses
 *    30 positions: 28 used + 2 empty slots
 * 
 * 6. 1N4148 diodes prevent ghosting (phantom readings)
 *    Cathode (band) always towards the ROW pin
 * 
 * 7. 100nF capacitors filter noise on potentiometers
 *    Connect between center pin (wiper) and GND
 * 
 * 8. In Board Manager select "Arduino Leonardo"
 *
 * 9. Leonardo supports USB HID + Serial CDC simultaneously!
 *    Joystick and Zusi3 LEDs work together.
 *
 * 10. BTN1 and PEDAL are IN PARALLEL — same joystick button!
 *
 */
