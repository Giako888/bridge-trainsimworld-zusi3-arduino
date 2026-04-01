/*
 * Wiring Diagram — Arduino Leonardo Serial Only (13 LED MAX7219)
 * 
 * SIMPLIFIED version: only 3 pins for LEDs (MAX7219) + USB.
 * No joystick, encoder, button matrix or sliders.
 * 
 * ============================================
 * ARDUINO LEONARDO PINOUT (Serial Only)
 * ============================================
 * 
 * Only 3 pins used for MAX7219 + USB power!
 * All other pins are FREE for future use.
 * 
 *              ┌────USB────┐
 *        ---  │ 1      RAW│
 *        ---  │ 0      GND│ ◄── GND
 *             │ GND    RST│
 *       GND   │ GND    VCC│ ◄── +5V
 *        ---  │ 2      A3 │ ◄── MAX7219_DIN
 *        ---  │ 3      A2 │ --- (free)
 *        ---  │ 4      A1 │ --- (free)
 *        ---  │ 5      A0 │ --- (free)
 *        ---  │ 6      A5 │ ◄── MAX7219_CS
 *        ---  │ 7      A4 │ ◄── MAX7219_CLK
 *        ---  │ 8      13 │ --- (free)
 *        ---  │ 9      12 │ --- (free)
 *        ---  │ 10     11 │ --- (free)
 *             └───────────┘
 * 
 * Pins used (all on analog header, adjacent):
 *   A3 = MAX7219_DIN
 *   A4 = MAX7219_CLK
 *   A5 = MAX7219_CS (LOAD)
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
 * ============================================
 * LED SUMMARY TABLE
 * ============================================
 * 
 *  LED │ MAX7219      │ Function                     │ Color
 * ─────┼──────────────┼──────────────────────────────┼─────────────
 *   1  │ DIG0.A       │ SIFA Warning                 │ white/yellow
 *   2  │ DIG0.B       │ LZB Ende                     │ yellow
 *   3  │ DIG0.C       │ PZB 70 (Zugart M)            │ blue
 *   4  │ DIG0.D       │ PZB 85 (Zugart O)            │ blue
 *   5  │ DIG0.E       │ PZB 55 (Zugart U)            │ blue
 *   6  │ DIG0.F       │ 500Hz (PZB frequency)        │ red
 *   7  │ DIG0.G       │ 1000Hz (PZB frequency)       │ yellow
 *   8  │ DIG0.DP      │ Doors Left (Türen L)         │ yellow
 *   9  │ DIG1.A       │ Doors Right (Türen R)        │ yellow
 *  10  │ DIG1.B       │ LZB Ü (Überwachung)          │ blue
 *  11  │ DIG1.C       │ LZB G (Geführt/active)       │ red
 *  12  │ DIG1.D       │ LZB S (Schnellbremsung)      │ red
 *  13  │ DIG1.E       │ Befehl 40                    │ yellow
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
 * - 1x MAX7219 Module (WCMCU DISY1 breakout)
 * - 13x 5mm LED (1 white/yellow, 5 yellow, 4 blue, 3 red)
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
 * 3. The MAX7219 handles current internally (RSET on module).
 *    Individual resistors for each LED are NOT needed.
 * 
 * 4. In Arduino IDE Board Manager: select "Arduino Leonardo"
 * 
 * 5. With MAX7219, all LEDs can be ON simultaneously
 *    (unlike Charlieplexing which uses multiplexing).
 * 
 * 6. All unused pins (0-13, A0-A2) remain free
 *    for potential future expansions.
 * 
 */
