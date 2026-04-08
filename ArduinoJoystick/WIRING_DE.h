/*
 * Anschlussplan — Arduino Leonardo Joystick + 13 LED MAX7219
 * 
 * ============================================
 * ARDUINO LEONARDO PINBELEGUNG
 * ============================================
 * 
 *             ┌────USB────┐
 *   COL5    ─►│ 1      RAW│
 *        ---  │ 0      GND│ ◄── GND
 *             │ GND    RST│
 *       GND   │ GND    VCC│ ◄── +5V
 *   ENC_CLK ─►│ 2      A3 │ ◄── MAX7219_DIN
 *   ENC_DT  ─►│ 3      A2 │ ◄── SLIDER_Z (Schleifer)
 *   COL4    ─►│ 4      A1 │ ◄── SLIDER_Y (Schleifer)
 *   ROW0    ─►│ 5      A0 │ ◄── SLIDER_X (Schleifer)
 *   ROW1    ─►│ 6      A5 │ ◄── MAX7219_CS
 *   ROW2    ─►│ 7      A4 │ ◄── MAX7219_CLK
 *   ROW3    ─►│ 8      13 │ ◄── COL3
 *   ROW4    ─►│ 9      12 │ ◄── COL2
 *   COL0    ─►│ 10     11 │ ◄── COL1
 *             └───────────┘
 * 
 * MAX7219: DIN=A3, CLK=A4, CS=A5 (header analogico)
 *
 * Alle 3 MAX7219-Pins befinden sich am Analog-Header (A3, A4, A5),
 *       neben den Potentiometer-Pins (A0, A1, A2).
 * 
 * ============================================
 * TASTENMATRIX 5x6 (30 Positionen!)
 * ============================================
 * 
 * Die Matrix verwaltet ALLE Schalter, Taster, Drehschalter UND Encoder-Klick!
 * Ermöglicht gleichzeitiges Drücken.
 * 
 * Layout:
 * 
 *              COL0     COL1     COL2     COL3     COL4     COL5
 *              (10)     (11)     (12)     (13)     (4)      (1) 
 *               │        │        │        │        │        │
 * ROW0 (5) ─────┼─BTN1───┼─(leer)─┼─ROT3_2─┼─ROT3_1─┼─ENC_SW─┼─ROT4_1
 *               │/PEDAL  │        │        │        │        │
 * ROW1 (6) ─────┼─SW2_UP─┼─SW1_UP─┼─SW6_UP─┼─SW8_UP─┼─SW5_UP─┼─ROT4_2
 *               │        │        │        │        │        │
 * ROW2 (7) ─────┼─SW2_DN─┼─SW1_DN─┼─SW6_DN─┼─SW8_DN─┼─SW5_DN─┼─ROT4_3
 *               │        │        │        │        │        │
 * ROW3 (8) ─────┼─SW3_UP─┼─SW4_UP─┼─SW7_UP─┼─SW9_UP─┼─TOG1_UP┼─ROT4_4
 *               │        │        │        │        │        │
 * ROW4 (9) ─────┼─SW3_DN─┼─SW4_DN─┼─SW7_DN─┼─SW9_DN─┼─TOG1_DN┼─(leer)
 *               │        │        │        │        │        │
 * 
 * Elemente gesamt: 28
 * - 9 ON-OFF-ON-Schalter (SW1-SW9): 18 Positionen
 * - TOGGLE1 selbsthaltend: 2 Positionen
 * - ROT4 (4 Pos.): 4 Positionen
 * - ROT3 (2 aktive Pos.): 2 Positionen
 * - BTN1/PEDAL (parallel): 1 Position
 * - ENC_SW: 1 Position
 * 
 * ============================================
 * JOYSTICK-TASTENZUORDNUNG
 * ============================================
 * 
 * Taste │ Funktion
 * ──────┼──────────────────────────
 *    0  │ SW1_UP (Schalter 1 hoch)
 *    1  │ SW1_DN (Schalter 1 runter)
 *    2  │ SW2_UP
 *    3  │ SW2_DN
 *    4  │ SW3_UP
 *    5  │ SW3_DN
 *    6  │ SW4_UP
 *    7  │ SW4_DN
 *    8  │ SW5_UP
 *    9  │ SW5_DN
 *   10  │ SW6_UP
 *   11  │ SW6_DN
 *   12  │ SW7_UP
 *   13  │ SW7_DN
 *   14  │ SW8_UP
 *   15  │ SW8_DN
 *   16  │ SW9_UP
 *   17  │ SW9_DN
 *   18  │ ENC_SW (Encoder-Klick)
 *   19  │ BTN1/PEDAL (parallel)
 *   20  │ ROT4_1 (4-Pos.-Drehschalter - 1)
 *   21  │ ROT4_2 (4-Pos.-Drehschalter - 2)
 *   22  │ ROT4_3 (4-Pos.-Drehschalter - 3)
 *   23  │ ROT4_4 (4-Pos.-Drehschalter - 4)
 *   24  │ TOG1_UP (selbsthaltend hoch)
 *   25  │ TOG1_DN (selbsthaltend runter)
 *   26  │ ROT3_1 (3-Pos.-Drehschalter - 1)
 *   27  │ ROT3_2 (3-Pos.-Drehschalter - 2)
 * 
 * ============================================
 * VERKABELUNG ON-OFF-ON-SCHALTER (9 Schalter)
 * ============================================
 * 
 * Jeder Schalter hat 3 Anschlüsse:
 * 
 *        [HOCH] ────► Entsprechende UP-Zeile
 *          │
 *    [GEMEINSAM] ──► Entsprechende Spalte
 *          │
 *        [RUNTER] ──► Entsprechende DN-Zeile
 * 
 * ACHTUNG: Bei der Matrix ist die Verkabelung anders!
 * Die Gemeinsamen NICHT mit GND verbinden. DIODEN verwenden!
 * 
 * ANSCHLUSSTABELLE SCHALTER:
 * 
 * Schalter │ GEMEINSAM (COL)│ HOCH (ROW)  │ RUNTER (ROW)
 * ─────────┼────────────────┼─────────────┼─────────────
 *    1     │ Pin 11 (COL1)  │ Pin 6 (ROW1)│ Pin 7 (ROW2)
 *    2     │ Pin 10 (COL0)  │ Pin 6 (ROW1)│ Pin 7 (ROW2)
 *    3     │ Pin 10 (COL0)  │ Pin 8 (ROW3)│ Pin 9 (ROW4)
 *    4     │ Pin 11 (COL1)  │ Pin 8 (ROW3)│ Pin 9 (ROW4)
 *    5     │ Pin 4 (COL4)   │ Pin 6 (ROW1)│ Pin 7 (ROW2)
 *    6     │ Pin 12 (COL2)  │ Pin 6 (ROW1)│ Pin 7 (ROW2)
 *    7     │ Pin 12 (COL2)  │ Pin 8 (ROW3)│ Pin 9 (ROW4)
 *    8     │ Pin 13 (COL3)  │ Pin 6 (ROW1)│ Pin 7 (ROW2)
 *    9     │ Pin 13 (COL3)  │ Pin 8 (ROW3)│ Pin 9 (ROW4)
 * 
 * ============================================
 * SELBSTHALTENDE KIPPSCHALTER (ON-OFF-ON)
 * ============================================
 * 
 * Ähnlich wie ON-OFF-ON-Schalter, aber SELBSTHALTEND!
 * Sie behalten die Position bei (federn nicht zurück zur Mitte).
 * 
 * TOGGLE1 (selbsthaltend ON-OFF-ON, 3 Anschlüsse):
 *   - HOCH-Anschluss: Pin 8 (ROW3) mit Diode
 *   - GEMEINSAM: Pin 4 (COL4)
 *   - RUNTER-Anschluss: Pin 9 (ROW4) mit Diode
 * 
 * Schema mit Dioden:
 *   Pin 8 (ROW3) ──|◄── [HOCH]
 *                           │
 *                      [GEMEINSAM] ──── Pin 4 (COL4)
 *                           │
 *   Pin 9 (ROW4) ──|◄── [RUNTER]
 * 
 * Funktion:
 *   - Position HOCH   → Taste 24 = 1, Taste 25 = 0
 *   - Position AUS    → Taste 24 = 0, Taste 25 = 0
 *   - Position RUNTER → Taste 24 = 0, Taste 25 = 1
 * 
 * ============================================
 * DREHSCHALTER 4 POSITIONEN (ROT4: 4 EIN)
 * ============================================
 * 
 * Drehwahlschalter mit 4 Positionen: 1, 2, 3, 4 (kein AUS!)
 * Hat 5 Anschlüsse: GEMEINSAM + 4 Positionen
 * 
 * ROT4-Verkabelung:
 *   Pos. 1: Pin 5 (ROW0) ──|◄── Pin 1 (COL5)
 *   Pos. 2: Pin 6 (ROW1) ──|◄── Pin 1 (COL5)
 *   Pos. 3: Pin 7 (ROW2) ──|◄── Pin 1 (COL5)
 *   Pos. 4: Pin 8 (ROW3) ──|◄── Pin 1 (COL5)
 * 
 * Funktion:
 *   - Pos. 1 → Taste 20 = 1
 *   - Pos. 2 → Taste 21 = 1
 *   - Pos. 3 → Taste 22 = 1
 *   - Pos. 4 → Taste 23 = 1
 * 
 * HINWEIS: Der 4-Positions-Drehschalter hat kein AUS!
 *          Eine Position ist immer aktiv.
 * 
 * ============================================
 * DREHSCHALTER 3 POSITIONEN (ROT3: AUS + 2)
 * ============================================
 * 
 * Drehwahlschalter mit 3 Positionen: AUS, 1, 2
 * Hat 3 Anschlüsse: GEMEINSAM + 2 Positionen
 * 
 * ROT3-Verkabelung:
 *   Pos. 1: Pin 5 (ROW0) ──|◄── Pin 13 (COL3)
 *   Pos. 2: Pin 5 (ROW0) ──|◄── Pin 12 (COL2)
 * 
 * Funktion:
 *   - AUS    → Alle 0
 *   - Pos. 1 → Taste 26 = 1
 *   - Pos. 2 → Taste 27 = 1
 * 
 * ============================================
 * ANTI-GHOSTING-DIODEN (1N4148 DO-35)
 * ============================================
 * 
 * Jeder Schalter/Taster hat eine 1N4148-Diode:
 * 
 *   [ROW-Pin] ────|◄────[SCHALTER]──────── [COL-Pin]
 *                 ▲
 *            KATHODE (schwarzer Ring)
 *            zum ROW-Pin hin
 * 
 * Dioden gesamt: ~23 (je nach Konfiguration)
 * 
 * ============================================
 * BTN1 UND PEDAL (PARALLEL)
 * ============================================
 * 
 * BTN1 und PEDAL sind PARALLEL zum gleichen Matrixplatz geschaltet!
 * Das Drücken eines der beiden aktiviert Taste 19.
 * 
 * Schema (beide mit Diode zu ROW0):
 *   Pin 5 (ROW0) ──|◄── [BTN1]  ──┬── Pin 10 (COL0)
 *   Pin 5 (ROW0) ──|◄── [PEDAL] ──┘
 * 
 * ============================================
 * ENCODER-KLICK (ENC_SW)
 * ============================================
 * 
 * Der Encoder-Klick ist in der Matrix:
 *   Pin 5 (ROW0) ──|◄── [ENC_SW] ──── Pin 4 (COL4)
 * 
 * ============================================
 * SCHIEBEPOTENTIOMETER 100mm MIT KONDENSATOREN
 * ============================================
 * 
 * Jeder B10K-Schieberegler (10kΩ linear 100mm) mit 100nF-Kondensator (104):
 *   - Linker Pin    → GND
 *   - Mittlerer Pin → Analoger Pin + Kondensator
 *   - Rechter Pin   → +5V
 * 
 * Schema:
 *          +5V
 *           │
 *     [SCHIEBER B10K]
 *       ══════════
 *           │
 *    Pin A ─┼───┤├──── GND
 *           │   104 (100nF)
 *        (Schleifer)
 * 
 * SCHIEBER 1 (X-Achse): Mitte → A0 + 100nF-Kondensator nach GND
 * SCHIEBER 2 (Y-Achse): Mitte → A1 + 100nF-Kondensator nach GND
 * SCHIEBER 3 (Z-Achse): Mitte → A2 + 100nF-Kondensator nach GND
 * 
 * ============================================
 * DREHENCODER
 * ============================================
 * 
 * EC11-Encoder mit Taster (4 Pins verwendet):
 *   - GND → GND Arduino
 *   - CLK → Pin 2 (Interrupt)
 *   - DT  → Pin 3 (Interrupt)
 *   - SW  → MATRIX (ROW0-COL4, also Pin 5 und Pin 4)
 * 
 * +5V wird NICHT benötigt! Der Encoder ist rein mechanisch (Schalter).
 * Pins 2 und 3 nutzen interne Pull-ups, aktiviert durch die Encoder-Bibliothek.
 * 
 * HINWEIS: Der Encoder-Klick (SW) ist in der Matrix!
 *          SW zwischen ROW0 (Pin 5) und COL4 (Pin 4) mit Diode verbinden.
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
 * LED-Tabelle:
 *   LED1:  DIG0.A  = SIFA Warnung (weiß/gelb)
 *   LED2:  DIG0.B  = LZB Ende (gelb)
 *   LED3:  DIG0.C  = PZB 70 (blau)
 *   LED4:  DIG0.D  = PZB 85 (blau)
 *   LED5:  DIG0.E  = PZB 55 (blau)
 *   LED6:  DIG0.F  = 500Hz (rot)
 *   LED7:  DIG0.G  = 1000Hz (gelb)
 *   LED8:  DIG0.DP = Türen Links (gelb)
 *   LED9:  DIG1.A  = Türen Rechts (gelb)
 *   LED10: DIG1.B  = LZB Ü (blau)
 *   LED11: DIG1.C  = LZB G (rot)
 *   LED12: DIG1.D  = LZB S (rot)
 *   LED13: DIG1.E  = Befehl 40 (gelb)
 * 
 * Serielle Befehle (115200 Baud):
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
 * - 3x Schiebepotentiometer 100mm B10K
 * - 1x Drehencoder EC11 mit Taster
 * - 9x Momentan-Schalter ON-OFF-ON (SW1-SW9, federn zur Mitte zurück)
 * - 1x Selbsthaltender Schalter ON-OFF-ON (TOGGLE1, behält Position)
 * - 1x Drehschalter 4 Positionen (ROT4: 4 EIN, kein AUS)
 * - 1x Drehschalter 3 Positionen (ROT3: AUS + 2)
 * - 1x Momentan-Taster (BTN1)
 * - 1x Fußschalter (Pedal)
 * - 3x Keramikkondensator 100nF (104)
 * - ~25x Diode 1N4148 DO-35 (Matrix)
 * - 13x LED 5mm (1 weiß/gelb, 5 gelb, 4 blau, 3 rot)
 * - Jumper-Kabel
 * - Breadboard oder Platine
 * 
 * BENÖTIGTE BIBLIOTHEKEN:
 * - Joystick (Matthew Heironimus) — von GitHub
 * - Encoder (Paul Stoffregen) — vom Library Manager
 * 
 * ============================================
 * WICHTIGE HINWEISE
 * ============================================
 * 
 * 1. Arduino Leonardo verwendet ATmega32U4 = natives USB
 * 
 * 2. Pins 2 und 3 haben Hardware-Interrupts für den Encoder
 * 
 * 3. MAX7219 verwendet nur 3 nebeneinanderliegende Pins am Analog-Header: DIN(A3), CLK(A4), CS(A5).
 *    Pins 0, 1 (TX/RX) und 14 (MISO/ICSP) sind alle FREI.
 * 
 * 4. Leonardo hat mehr Pins als Pro Micro:
 *    - Pins 11, 12, 13 direkt zugänglich
 *    - Pins A0-A5 am Analog-Header (Slider + MAX7219)
 * 
 * 5. Die 5x6-Matrix ermöglicht gleichzeitiges Drücken
 *    30 Positionen: 28 belegt + 2 leere Plätze
 * 
 * 6. 1N4148-Dioden verhindern Ghosting (Phantomlesungen)
 *    Kathode (Ring) immer zum ROW-Pin hin
 * 
 * 7. 100nF-Kondensatoren filtern Rauschen an den Potentiometern
 *    Zwischen Mittelpin (Schleifer) und GND anschließen
 * 
 * 8. Im Board Manager "Arduino Leonardo" auswählen
 *
 * 9. Leonardo unterstützt USB HID + Serial CDC gleichzeitig!
 *    Joystick und Zusi3-LEDs funktionieren zusammen.
 *
 * 10. BTN1 und PEDAL sind PARALLEL geschaltet — gleiche Joystick-Taste!
 *
 */
