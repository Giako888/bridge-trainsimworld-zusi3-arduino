/*
 * Wiring Diagram — Arduino Leonardo Joystick + 13 LED MAX7219
 * 
 * ============================================
 * ARDUINO LEONARDO PINOUT
 * ============================================
 * 
 *             ┌────USB────┐
 *   COL5    ─►│ 1      RAW│
 *        ---  │ 0      GND│ ◄── GND
 *             │ GND    RST│
 *       GND   │ GND    VCC│ ◄── +5V
 *   ENC_CLK ─►│ 2      A3 │ ◄── MAX7219_DIN
 *   ENC_DT  ─►│ 3      A2 │ ◄── SLIDER_Z (wiper)
 *   COL4    ─►│ 4      A1 │ ◄── SLIDER_Y (wiper)
 *   ROW0    ─►│ 5      A0 │ ◄── SLIDER_X (wiper)
 *   ROW1    ─►│ 6      A5 │ ◄── MAX7219_CS
 *   ROW2    ─►│ 7      A4 │ ◄── MAX7219_CLK
 *   ROW3    ─►│ 8      13 │ ◄── COL3
 *   ROW4    ─►│ 9      12 │ ◄── COL2
 *   COL0    ─►│ 10     11 │ ◄── COL1
 *             └───────────┘
 * 
 * MAX7219: DIN=A3, CLK=A4, CS=A5 (header analogico)
 *
 * All 3 MAX7219 pins are on the analog header (A3, A4, A5),
 *       adjacent to the potentiometer pins (A0, A1, A2).
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
 *              (10)     (11)     (12)     (13)     (4)      (1) 
 *               │        │        │        │        │        │
 * ROW0 (5) ─────┼─BTN1───┼─(free)─┼─ROT3_2─┼─ROT3_1─┼─ENC_SW─┼─ROT4_1
 *               │/PEDAL  │        │        │        │        │
 * ROW1 (6) ─────┼─SW2_UP─┼─SW1_UP─┼─SW6_UP─┼─SW8_UP─┼─SW5_UP─┼─ROT4_2
 *               │        │        │        │        │        │
 * ROW2 (7) ─────┼─SW2_DN─┼─SW1_DN─┼─SW6_DN─┼─SW8_DN─┼─SW5_DN─┼─ROT4_3
 *               │        │        │        │        │        │
 * ROW3 (8) ─────┼─SW3_UP─┼─SW4_UP─┼─SW7_UP─┼─SW9_UP─┼─TOG1_UP┼─ROT4_4
 *               │        │        │        │        │        │
 * ROW4 (9) ─────┼─SW3_DN─┼─SW4_DN─┼─SW7_DN─┼─SW9_DN─┼─TOG1_DN┼─(free)
 *               │        │        │        │        │        │
 * 
 * Total elements: 28
 * - 9 ON-OFF-ON switches (SW1-SW9): 18 positions
 * - TOGGLE1 self-lock: 2 positions
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
 *   16   │ SW9_UP
 *   17   │ SW9_DN
 *   18   │ ENC_SW (encoder click)
 *   19   │ BTN1/PEDAL (in parallel)
 *   20   │ ROT4_1 (4-pos rotary - 1)
 *   21   │ ROT4_2 (4-pos rotary - 2)
 *   22   │ ROT4_3 (4-pos rotary - 3)
 *   23   │ ROT4_4 (4-pos rotary - 4)
 *   24   │ TOG1_UP (self-lock toggle up)
 *   25   │ TOG1_DN (self-lock toggle down)
 *   26   │ ROT3_1 (3-pos rotary - 1)
 *   27   │ ROT3_2 (3-pos rotary - 2)
 * 
 * ============================================
 * ON-OFF-ON SWITCH WIRING (9 switches)
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
 *   1    │ Pin 11 (COL1)│ Pin 6 (ROW1)│ Pin 7 (ROW2)
 *   2    │ Pin 10 (COL0)│ Pin 6 (ROW1)│ Pin 7 (ROW2)
 *   3    │ Pin 10 (COL0)│ Pin 8 (ROW3)│ Pin 9 (ROW4)
 *   4    │ Pin 11 (COL1)│ Pin 8 (ROW3)│ Pin 9 (ROW4)
 *   5    │ Pin 4 (COL4) │ Pin 6 (ROW1)│ Pin 7 (ROW2)
 *   6    │ Pin 12 (COL2)│ Pin 6 (ROW1)│ Pin 7 (ROW2)
 *   7    │ Pin 12 (COL2)│ Pin 8 (ROW3)│ Pin 9 (ROW4)
 *   8    │ Pin 13 (COL3)│ Pin 6 (ROW1)│ Pin 7 (ROW2)
 *   9    │ Pin 13 (COL3)│ Pin 8 (ROW3)│ Pin 9 (ROW4)
 * 
 * ============================================
 * SELF-LOCK TOGGLE SWITCHES (ON-OFF-ON)
 * ============================================
 * 
 * Similar to ON-OFF-ON switches but SELF-LOCK!
 * They maintain position when released (don't spring back to center).
 * 
 * TOGGLE1 (self-lock ON-OFF-ON, 3 terminals):
 *   - UP terminal: Pin 8 (ROW3) with diode
 *   - COMMON: Pin 4 (COL4)
 *   - DOWN terminal: Pin 9 (ROW4) with diode
 * 
 * Diagram with diodes:
 *   Pin 8 (ROW3) ──|◄── [UP]
 *                           │
 *                      [COMMON] ──── Pin 4 (COL4)
 *                           │
 *   Pin 9 (ROW4) ──|◄── [DOWN]
 * 
 * Operation:
 *   - UP position   → Button 24 = 1, Button 25 = 0
 *   - OFF position  → Button 24 = 0, Button 25 = 0
 *   - DOWN position → Button 24 = 0, Button 25 = 1
 * 
 * ============================================
 * ROTARY SWITCH 4 POSITIONS (ROT4: 4 ON)
 * ============================================
 * 
 * Rotary selector with 4 positions: 1, 2, 3, 4 (no OFF!)
 * Has 5 terminals: COMMON + 4 positions
 * 
 * ROT4 wiring:
 *   Pos 1: Pin 5 (ROW0) ──|◄── Pin 1 (COL5)
 *   Pos 2: Pin 6 (ROW1) ──|◄── Pin 1 (COL5)
 *   Pos 3: Pin 7 (ROW2) ──|◄── Pin 1 (COL5)
 *   Pos 4: Pin 8 (ROW3) ──|◄── Pin 1 (COL5)
 * 
 * Operation:
 *   - Pos 1 → Button 20 = 1
 *   - Pos 2 → Button 21 = 1
 *   - Pos 3 → Button 22 = 1
 *   - Pos 4 → Button 23 = 1
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
 *   Pos 1: Pin 5 (ROW0) ──|◄── Pin 13 (COL3)
 *   Pos 2: Pin 5 (ROW0) ──|◄── Pin 12 (COL2)
 * 
 * Operation:
 *   - OFF    → All 0
 *   - Pos 1  → Button 26 = 1
 *   - Pos 2  → Button 27 = 1
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
 * Pressing either one activates button 19.
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
 *   Pin 5 (ROW0) ──|◄── [ENC_SW] ──── Pin 4 (COL4)
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
 * EC11 encoder with push button (4 pins used):
 *   - GND → GND Arduino
 *   - CLK → Pin 2 (interrupt)
 *   - DT  → Pin 3 (interrupt)
 *   - SW  → MATRIX (ROW0-COL4, i.e. pin 5 and pin 4)
 * 
 * +5V is NOT needed! The encoder is purely mechanical (switches).
 * Pins 2 and 3 use internal pull-ups enabled by the Encoder library.
 * 
 * NOTE: The encoder click (SW) is in the matrix!
 *       Connect SW between ROW0 (pin 5) and COL4 (pin 4) with diode.
 * 
 * ============================================
 * LED MAX7219 (13 LEDs with WCMCU DISY1 module)
 * ============================================
 * 
 * The MAX7219 module (WCMCU DISY1 breakout) drives all 13 LEDs.
 * Software SPI communication on 3 pins.
 * No individual resistors needed (RSET already on module).
 * All LEDs can be ON simultaneously!
 * 
 * Arduino → MAX7219 connections (IN side):
 *   Pin A3               → DIN
 *   Pin A4               → CLK
 *   Pin A5               → CS (LOAD)
 *   +5V                  → VCC
 *   GND                  → GND
 * 
 * MAX7219 connections (LED side):
 *
 *   DIG0:
 *     SEG_A  → LED1  SIFA (white/yellow)
 *     SEG_B  → LED2  LZB Ende (yellow)
 *     SEG_C  → LED3  PZB 70 (blue)
 *     SEG_D  → LED4  PZB 85 (blue)
 *     SEG_E  → LED5  PZB 55 (blue)
 *     SEG_F  → LED6  500Hz (red)
 *     SEG_G  → LED7  1000Hz (yellow)
 *     SEG_DP → LED8  Doors Left (yellow)
 *
 *   DIG1:
 *     SEG_A  → LED9  Doors Right (yellow)
 *     SEG_B  → LED10 LZB Ü (blue)
 *     SEG_C  → LED11 LZB G (red)
 *     SEG_D  → LED12 LZB S (red)
 *     SEG_E  → LED13 Befehl 40 (yellow)
 * 
 * LED wiring diagram:
 *   Each LED: ANODE (+) to SEG_x pin, CATHODE (-) to DIG_x pin
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
 *   DP ──┤►| LED8 DoorsL│─── DIG0
 *        └──────────────┘
 *
 *         MAX7219 DIG1
 *        ┌──────────────┐
 *   A ───┤►| LED9 DoorsR│─── DIG1
 *   B ───┤►| LED10 LZBÜ │─── DIG1
 *   C ───┤►| LED11 LZBG │─── DIG1
 *   D ───┤►| LED12 LZBS │─── DIG1
 *   E ───┤►| LED13 BEF40│─── DIG1
 *        └──────────────┘
 * 
 * LED table:
 *   LED1:  DIG0.A  = SIFA Warning (white/yellow)
 *   LED2:  DIG0.B  = LZB Ende (yellow)
 *   LED3:  DIG0.C  = PZB 70 (blue)
 *   LED4:  DIG0.D  = PZB 85 (blue)
 *   LED5:  DIG0.E  = PZB 55 (blue)
 *   LED6:  DIG0.F  = 500Hz (red)
 *   LED7:  DIG0.G  = 1000Hz (yellow)
 *   LED8:  DIG0.DP = Doors Left (yellow)
 *   LED9:  DIG1.A  = Doors Right (yellow)
 *   LED10: DIG1.B  = LZB Ü (blue)
 *   LED11: DIG1.C  = LZB G (red)
 *   LED12: DIG1.D  = LZB S (red)
 *   LED13: DIG1.E  = Befehl 40 (yellow)
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
 * - 1x MAX7219 Module (WCMCU DISY1 breakout)
 * - 3x 100mm Slider Potentiometer B10K
 * - 1x EC11 Rotary Encoder with push button
 * - 9x Momentary ON-OFF-ON Switch (SW1-SW9, spring back to center)
 * - 1x Self-lock ON-OFF-ON Switch (TOGGLE1, maintains position)
 * - 1x 4-position Rotary Switch (ROT4: 4 ON, no OFF)
 * - 1x 3-position Rotary Switch (ROT3: OFF + 2)
 * - 1x Momentary Push Button (BTN1)
 * - 1x Foot Switch (pedal)
 * - 3x Ceramic Capacitor 100nF (104)
 * - ~25x 1N4148 DO-35 Diode (matrix)
 * - 13x 5mm LED (1 white/yellow, 5 yellow, 4 blue, 3 red)
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
 * 3. MAX7219 uses only 3 adjacent pins on the analog header: DIN(A3), CLK(A4), CS(A5).
 *    Pins 0, 1 (TX/RX) and 14 (MISO/ICSP) are all FREE.
 * 
 * 4. Leonardo has more pins than Pro Micro:
 *    - Pins 11, 12, 13 directly accessible
 *    - Pins A0-A5 on analog header (sliders + MAX7219)
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
