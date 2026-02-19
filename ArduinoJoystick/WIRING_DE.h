/*
 * Anschlussplan — Arduino Leonardo Joystick + 13 LED Charlieplexing
 * 
 * ============================================
 * ARDUINO LEONARDO PINBELEGUNG
 * ============================================
 * 
 *             ┌────USB────┐
 *    LED_C  ─►│ 1      RAW│
 *    LED_B  ─►│ 0      GND│ ◄── GND
 *             │ GND    RST│
 *       GND   │ GND    VCC│ ◄── +5V
 *   ENC_CLK ─►│ 2      A3 │ ◄── LED_A
 *   ENC_DT  ─►│ 3      A2 │ ◄── SLIDER_Z (Schleifer)
 *   COL4    ─►│ 4      A1 │ ◄── SLIDER_Y (Schleifer)
 *   ROW0    ─►│ 5      A0 │ ◄── SLIDER_X (Schleifer)
 *   ROW1    ─►│ 6      A5 │ ◄── COL5 (neu!)
 *   ROW2    ─►│ 7      A4 │ ◄── LED_D (neu!)
 *   ROW3    ─►│ 8      13 │ ◄── COL3
 *   ROW4    ─►│ 9      12 │ ◄── COL2
 *   COL0    ─►│ 10     11 │ ◄── COL1
 *             └───────────┘
 * 
 * LED Charlieplexing: A3 (LED_A), 0 (LED_B), 1 (LED_C), A4 (LED_D), 14/MISO (LED_E)
 *
 * HINWEIS: Pin 14 (MISO) befindet sich auf dem ICSP-Header, NICHT auf dem Standard-Header.
 *          Einen Draht an den MISO-Pin des ICSP-Headers löten (6-Pin-Header in der Mitte).
 *          ICSP-Header (Draufsicht):
 *            ┌──────────────┐
 *            │ ►MISO(14) VCC│
 *            │  SCK(15) MOSI│
 *            │  RST     GND │
 *            └──────────────┘
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
 * ROW4 (9) ─────┼─SW6_DN─┼─SW7_DN─┼─SW8_DN─┼─(leer)─┼─(leer)─┼─TOG2_DN
 *               │        │        │        │        │        │
 * 
 * Elemente gesamt: 28
 * - 8 ON-OFF-ON-Schalter (SW1-SW8): 16 Positionen
 * - TOGGLE1 selbsthaltend: 2 Positionen
 * - TOGGLE2 selbsthaltend: 2 Positionen
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
 *   16  │ ENC_SW (Encoder-Klick)
 *   17  │ BTN1/PEDAL (parallel)
 *   18  │ ROT4_1 (4-Pos.-Drehschalter - 1)
 *   19  │ ROT4_2 (4-Pos.-Drehschalter - 2)
 *   20  │ ROT4_3 (4-Pos.-Drehschalter - 3)
 *   21  │ ROT4_4 (4-Pos.-Drehschalter - 4)
 *   22  │ TOG1_UP (selbsthaltend hoch)
 *   23  │ TOG1_DN (selbsthaltend runter)
 *   24  │ ROT3_1 (3-Pos.-Drehschalter - 1)
 *   25  │ ROT3_2 (3-Pos.-Drehschalter - 2)
 *   26  │ TOG2_UP (selbsthaltend2 hoch)
 *   27  │ TOG2_DN (selbsthaltend2 runter)
 * 
 * ============================================
 * VERKABELUNG ON-OFF-ON-SCHALTER (8 Schalter)
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
 *    1     │ Pin 10 (COL0)  │ Pin 6 (ROW1)│ Pin 7 (ROW2)
 *    2     │ Pin 11 (COL1)  │ Pin 6 (ROW1)│ Pin 7 (ROW2)
 *    3     │ Pin 12 (COL2)  │ Pin 6 (ROW1)│ Pin 7 (ROW2)
 *    4     │ Pin 13 (COL3)  │ Pin 6 (ROW1)│ Pin 7 (ROW2)
 *    5     │ Pin 4 (COL4)   │ Pin 6 (ROW1)│ Pin 7 (ROW2)
 *    6     │ Pin 10 (COL0)  │ Pin 8 (ROW3)│ Pin 9 (ROW4)
 *    7     │ Pin 11 (COL1)  │ Pin 8 (ROW3)│ Pin 9 (ROW4)
 *    8     │ Pin 12 (COL2)  │ Pin 8 (ROW3)│ Pin 9 (ROW4)
 * 
 * ============================================
 * SELBSTHALTENDE KIPPSCHALTER (ON-OFF-ON)
 * ============================================
 * 
 * Ähnlich wie ON-OFF-ON-Schalter, aber SELBSTHALTEND!
 * Sie behalten die Position bei (federn nicht zurück zur Mitte).
 * 
 * TOGGLE1 (selbsthaltend ON-OFF-ON, 3 Anschlüsse):
 *   - HOCH-Anschluss: Pin 6 (ROW1) mit Diode
 *   - GEMEINSAM: Pin A5 (COL5)
 *   - RUNTER-Anschluss: Pin 7 (ROW2) mit Diode
 * 
 * Schema mit Dioden:
 *   Pin 6 (ROW1) ──|◄── [HOCH]
 *                           │
 *                      [GEMEINSAM] ──── Pin A5 (COL5)
 *                           │
 *   Pin 7 (ROW2) ──|◄── [RUNTER]
 * 
 * Funktion:
 *   - Position HOCH   → Taste 22 = 1, Taste 23 = 0
 *   - Position AUS    → Taste 22 = 0, Taste 23 = 0
 *   - Position RUNTER → Taste 22 = 0, Taste 23 = 1
 * 
 * TOGGLE2 (selbsthaltend ON-OFF-ON, 3 Anschlüsse):
 *   - HOCH-Anschluss: Pin 8 (ROW3) mit Diode
 *   - GEMEINSAM: Pin A5 (COL5)
 *   - RUNTER-Anschluss: Pin 9 (ROW4) mit Diode
 * 
 * Schema mit Dioden:
 *   Pin 8 (ROW3) ──|◄── [HOCH]
 *                           │
 *                      [GEMEINSAM] ──── Pin A5 (COL5)
 *                           │
 *   Pin 9 (ROW4) ──|◄── [RUNTER]
 * 
 * Funktion:
 *   - Position HOCH   → Taste 26 = 1, Taste 27 = 0
 *   - Position AUS    → Taste 26 = 0, Taste 27 = 0
 *   - Position RUNTER → Taste 26 = 0, Taste 27 = 1
 * 
 * ============================================
 * DREHSCHALTER 4 POSITIONEN (ROT4: 4 EIN)
 * ============================================
 * 
 * Drehwahlschalter mit 4 Positionen: 1, 2, 3, 4 (kein AUS!)
 * Hat 5 Anschlüsse: GEMEINSAM + 4 Positionen
 * 
 * ROT4-Verkabelung:
 *   Pos. 1: Pin 5 (ROW0) ──|◄── Pin 11 (COL1)
 *   Pos. 2: Pin 5 (ROW0) ──|◄── Pin 12 (COL2)
 *   Pos. 3: Pin 5 (ROW0) ──|◄── Pin 13 (COL3)
 *   Pos. 4: Pin 5 (ROW0) ──|◄── Pin 4 (COL4)
 * 
 * Funktion:
 *   - Pos. 1 → Taste 18 = 1
 *   - Pos. 2 → Taste 19 = 1
 *   - Pos. 3 → Taste 20 = 1
 *   - Pos. 4 → Taste 21 = 1
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
 *   Pos. 1: Pin 8 (ROW3) ──|◄── Pin 13 (COL3)
 *   Pos. 2: Pin 8 (ROW3) ──|◄── Pin 4 (COL4)
 * 
 * Funktion:
 *   - AUS    → Alle 0
 *   - Pos. 1 → Taste 24 = 1
 *   - Pos. 2 → Taste 25 = 1
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
 * Das Drücken eines der beiden aktiviert Taste 17.
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
 *   Pin 5 (ROW0) ──|◄── [ENC_SW] ──── Pin A5 (COL5)
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
 * EC11-Encoder mit Taster (5 Pins):
 *   - GND → GND
 *   - +   → +5V
 *   - SW  → MATRIX (ROW0-COL5, also Pin 5 und Pin A5)
 *   - DT  → Pin 3 (Interrupt)
 *   - CLK → Pin 2 (Interrupt)
 * 
 * HINWEIS: Der Encoder-Klick ist in der Matrix!
 *          SW zwischen ROW0 (Pin 5) und COL5 (Pin A5) mit Diode verbinden.
 * 
 * ============================================
 * LED CHARLIEPLEXING (13 LEDs mit 5 Pins!)
 * ============================================
 * 
 * Mit Charlieplexing können 5 Pins bis zu 20 LEDs steuern.
 * Wir verwenden 13 LEDs.
 * 
 * Verwendete Pins: A3 (LED_A), 0 (LED_B), 1 (LED_C), A4 (LED_D), 14/MISO (LED_E)
 * 
 * WICHTIG: Jede LED benötigt einen WIDERSTAND in Reihe!
 * 
 * Alle LEDs haben hohe Vf (3-6V) mit farbigem Kunststoff.
 * LED1 (SIFA) ist eine weiße LED mit gelbem Gehäuse.
 * 
 * Widerstandsberechnung (I ≈ 8mA):
 *   LED (Vf ≈ 3,2V): R = (5-3,2)/0,008 = 225Ω → verwende 220Ω
 * 
 * Anschlussplan (jede LED hat ihren eigenen 220Ω-Widerstand):
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
 *         LED9 (Türen Rechts)        LED10 (LZB Ü)
 *     0 ──[220Ω]──►|────────────|◄──[220Ω]── A4
 *             gelb                blau
 * 
 *                                   (NB: LED9 ist 0→A4, LED10 ist 1→A4)
 *         LED10 (LZB Ü)
 *     1 ──[220Ω]──►|──────────── A4
 *              blau
 * 
 *         LED11 (LZB G)             LED12 (LZB S)
 *    A4 ──[220Ω]──►|────────────|◄──[220Ω]── (keiner)
 *              blau                rot
 *    (LED11: A4→0)              (LED12: A4→1)
 * 
 *         LED13 (Befehl 40)
 *    A3 ──[220Ω]──►|──────────── 14 (MISO, ICSP)
 *             gelb
 *    (LED13: A3→14)
 * 
 * HINWEIS: Der Widerstand kommt IMMER zwischen Pin und LED-ANODE!
 *          Die Anode ist das LANGE Bein der LED.
 *          Die Kathode (kurzes Bein) geht zum anderen Pin.
 * 
 * LED-Tabelle:
 *   LED1:  A3→0  = SIFA Warnung (weiß/gelb, 220Ω)
 *   LED2:  0→A3  = LZB Ende (gelb, 220Ω)
 *   LED3:  A3→1  = PZB 70 (blau, 220Ω)
 *   LED4:  1→A3  = PZB 85 (blau, 220Ω)
 *   LED5:  0→1   = PZB 55 (blau, 220Ω)
 *   LED6:  1→0   = 500Hz (rot, 220Ω)
 *   LED7:  A3→A4 = 1000Hz (gelb, 220Ω)
 *   LED8:  A4→A3 = Türen Links (gelb, 220Ω)
 *   LED9:  0→A4  = Türen Rechts (gelb, 220Ω)
 *   LED10: 1→A4  = LZB Ü (blau, 220Ω)
 *   LED11: A4→0  = LZB G (rot, 220Ω)
 *   LED12: A4→1  = LZB S (rot, 220Ω)
 *   LED13: A3→14  = Befehl 40 (gelb, 220Ω)
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
 * - 3x Schiebepotentiometer 100mm B10K
 * - 1x Drehencoder EC11 mit Taster
 * - 8x Momentan-Schalter ON-OFF-ON (SW1-SW8, federn zur Mitte zurück)
 * - 2x Selbsthaltender Schalter ON-OFF-ON (TOGGLE1, TOGGLE2, behalten Position)
 * - 1x Drehschalter 4 Positionen (ROT4: 4 EIN, kein AUS)
 * - 1x Drehschalter 3 Positionen (ROT3: AUS + 2)
 * - 1x Momentan-Taster (BTN1)
 * - 1x Fußschalter (Pedal)
 * - 3x Keramikkondensator 100nF (104)
 * - ~25x Diode 1N4148 DO-35 (Matrix)
 * - 13x LED 5mm (1 weiß/gelb, 5 gelb, 4 blau, 3 rot)
 * - 13x Widerstand 220Ω (alle LEDs)
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
 * 3. TX/RX (Pins 0 und 1) werden für LED-Charlieplexing verwendet
 *    USB-Serial funktioniert trotzdem (läuft über USB, nicht über Pins!)
 * 
 * 4. Der Leonardo hat mehr Pins als der Pro Micro:
 *    - Pins 11, 12, 13 direkt zugänglich
 *    - Pins A4, A5 zugänglich
 *    - Pins 14 (MISO), 15 (SCK), 16 (MOSI) auf dem ICSP-Header
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
