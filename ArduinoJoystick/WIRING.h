/*
 * Schema Connessioni - Arduino Leonardo Joystick + 13 LED Charlieplexing
 * 
 * ============================================
 * PINOUT ARDUINO LEONARDO
 * ============================================
 * 
 *              ┌────USB────┐
 *   LED_C  ─►│ 1      RAW│
 *   LED_B  ─►│ 0      GND│ ◄── GND
 *             │ GND    RST│
 *       GND   │ GND    VCC│ ◄── +5V
 *   ENC_CLK ─►│ 2      A3 │ ◄── LED_A
 *   ENC_DT  ─►│ 3      A2 │ ◄── SLIDER_Z (wiper)
 *   COL4    ─►│ 4      A1 │ ◄── SLIDER_Y (wiper)
 *   ROW0    ─►│ 5      A0 │ ◄── SLIDER_X (wiper)
 *   ROW1    ─►│ 6      A5 │ ◄── COL5 (nuovo!)
 *   ROW2    ─►│ 7      A4 │ ◄── LED_D (nuovo!)
 *   ROW3    ─►│ 8      13 │ ◄── COL3
 *   ROW4    ─►│ 9      12 │ ◄── COL2
 *   COL0    ─►│ 10     11 │ ◄── COL1
 *             └───────────┘
 * 
 * LED Charlieplexing: A3 (LED_A), 0 (LED_B), 1 (LED_C), A4 (LED_D), 14/MISO (LED_E)
 *
 * NOTA: Pin 14 (MISO) è sull'header ICSP, NON sullo standard header.
 *       Saldare un filo al pin MISO dell'header ICSP (6 pin al centro).
 *       Header ICSP (visto dall'alto):
 *         ┌──────────────┐
 *         │ ►MISO(14) VCC│
 *         │  SCK(15) MOSI│
 *         │  RST     GND │
 *         └──────────────┘
 * 
 * ============================================
 * MATRICE PULSANTI 5x6 (30 posizioni!)
 * ============================================
 * 
 * La matrice gestisce TUTTI gli switch, pulsanti, rotary E encoder click!
 * Permette pressioni simultanee.
 * 
 * Layout:
 * 
 *              COL0     COL1     COL2     COL3     COL4     COL5
 *              (10)     (11)     (12)     (13)     (4)      (A5)
 *               │        │        │        │        │        │
 * ROW0 (5) ─────┼─BTN1───┼─ROT4_1─┼─ROT4_2─┼─ROT4_3─┼─ROT4_4─┼─ENC_SW
 *               │/PEDALE │        │        │        │        │
 * ROW1 (6) ─────┼─SW1_UP─┼─SW2_UP─┼─SW3_UP─┼─SW4_UP─┼─SW5_UP─┼─TOG1_UP
 *               │        │        │        │        │        │
 * ROW2 (7) ─────┼─SW1_DN─┼─SW2_DN─┼─SW3_DN─┼─SW4_DN─┼─SW5_DN─┼─TOG1_DN
 *               │        │        │        │        │        │
 * ROW3 (8) ─────┼─SW6_UP─┼─SW7_UP─┼─SW8_UP─┼─ROT3_1─┼─ROT3_2─┼─TOG2_UP
 *               │        │        │        │        │        │
 * ROW4 (9) ─────┼─SW6_DN─┼─SW7_DN─┼─SW8_DN─┼─(vuoto)┼─(vuoto)┼─TOG2_DN
 *               │        │        │        │        │        │
 * 
 * Totale elementi: 28
 * - 8 switch ON-OFF-ON (SW1-SW8): 16 posizioni
 * - TOGGLE1 self-lock: 2 posizioni
 * - TOGGLE2 self-lock: 2 posizioni
 * - ROT4 (4 pos): 4 posizioni
 * - ROT3 (2 pos attive): 2 posizioni
 * - BTN1/PEDALE (parallelo): 1 posizione
 * - ENC_SW: 1 posizione
 * 
 * ============================================
 * MAPPATURA PULSANTI JOYSTICK
 * ============================================
 * 
 * Pulsante │ Funzione
 * ─────────┼──────────────────────────
 *    0     │ SW1_UP (switch 1 su)
 *    1     │ SW1_DN (switch 1 giù)
 *    2     │ SW2_UP
 *    3     │ SW2_DN
 *    4     │ SW3_UP
 *    5     │ SW3_DN
 *    6     │ SW4_UP
 *    7     │ SW4_DN
 *    8     │ SW5_UP
 *    9     │ SW5_DN
 *   10     │ SW6_UP
 *   11     │ SW6_DN
 *   12     │ SW7_UP
 *   13     │ SW7_DN
 *   14     │ SW8_UP
 *   15     │ SW8_DN
 *   16     │ ENC_SW (click encoder)
 *   17     │ BTN1/PEDALE (in parallelo)
 *   18     │ ROT4_1 (rotary 4 pos - 1)
 *   19     │ ROT4_2 (rotary 4 pos - 2)
 *   20     │ ROT4_3 (rotary 4 pos - 3)
 *   21     │ ROT4_4 (rotary 4 pos - 4)
 *   22     │ TOG1_UP (toggle self-lock su)
 *   23     │ TOG1_DN (toggle self-lock giù)
 *   24     │ ROT3_1 (rotary 3 pos - 1)
 *   25     │ ROT3_2 (rotary 3 pos - 2)
 *   26     │ TOG2_UP (toggle2 self-lock su)
 *   27     │ TOG2_DN (toggle2 self-lock giù)
 * 
 * ============================================
 * CABLAGGIO SWITCH ON-OFF-ON (8 switch)
 * ============================================
 * 
 * Ogni switch ha 3 terminali:
 * 
 *        [SU] ────► Riga corrispondente UP
 *          │
 *    [COMUNE] ────► Colonna corrispondente
 *          │
 *        [GIÙ] ───► Riga corrispondente DN
 * 
 * ATTENZIONE: Con la matrice, il cablaggio è diverso!
 * NON collegare i comuni a GND. Usare DIODI!
 * 
 * TABELLA CONNESSIONI SWITCH ON-OFF-ON:
 * 
 * Switch │ COMUNE (COL) │ SU (ROW)    │ GIÙ (ROW)
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
 * SWITCH TOGGLE SELF-LOCK (ON-OFF-ON)
 * ============================================
 * 
 * Simile agli switch ON-OFF-ON ma SELF-LOCK!
 * Mantiene la posizione quando rilasciato (non torna al centro).
 * 
 * TOGGLE1 (self-lock ON-OFF-ON, 3 terminali):
 *   - Terminale SU: Pin 6 (ROW1) con diodo
 *   - COMUNE: Pin A5 (COL5)
 *   - Terminale GIÙ: Pin 7 (ROW2) con diodo
 * 
 * Schema con diodi:
 *   Pin 6 (ROW1) ──|◄── [SU]
 *                           │
 *                      [COMUNE] ──── Pin A5 (COL5)
 *                           │
 *   Pin 7 (ROW2) ──|◄── [GIÙ]
 * 
 * Funzionamento:
 *   - Posizione SU   → Pulsante 22 = 1, Pulsante 23 = 0
 *   - Posizione OFF  → Pulsante 22 = 0, Pulsante 23 = 0
 *   - Posizione GIÙ  → Pulsante 22 = 0, Pulsante 23 = 1
 * 
 * TOGGLE2 (self-lock ON-OFF-ON, 3 terminali):
 *   - Terminale SU: Pin 8 (ROW3) con diodo
 *   - COMUNE: Pin A5 (COL5)
 *   - Terminale GIÙ: Pin 9 (ROW4) con diodo
 * 
 * Schema con diodi:
 *   Pin 8 (ROW3) ──|◄── [SU]
 *                           │
 *                      [COMUNE] ──── Pin A5 (COL5)
 *                           │
 *   Pin 9 (ROW4) ──|◄── [GIÙ]
 * 
 * Funzionamento:
 *   - Posizione SU   → Pulsante 26 = 1, Pulsante 27 = 0
 *   - Posizione OFF  → Pulsante 26 = 0, Pulsante 27 = 0
 *   - Posizione GIÙ  → Pulsante 26 = 0, Pulsante 27 = 1
 * 
 * ============================================
 * ROTARY SWITCH 4 POSIZIONI (ROT4: 4 ON)
 * ============================================
 * 
 * Selettore rotativo con 4 posizioni: 1, 2, 3, 4 (nessun OFF!)
 * Ha 5 terminali: COMUNE + 4 posizioni
 * 
 * Cablaggio ROT4:
 *   Pos 1: Pin 5 (ROW0) ──|◄── Pin 11 (COL1)
 *   Pos 2: Pin 5 (ROW0) ──|◄── Pin 12 (COL2)
 *   Pos 3: Pin 5 (ROW0) ──|◄── Pin 13 (COL3)
 *   Pos 4: Pin 5 (ROW0) ──|◄── Pin 4 (COL4)
 * 
 * Funzionamento:
 *   - Pos 1 → Pulsante 18 = 1
 *   - Pos 2 → Pulsante 19 = 1
 *   - Pos 3 → Pulsante 20 = 1
 *   - Pos 4 → Pulsante 21 = 1
 * 
 * NOTA: Il rotary a 4 posizioni non ha OFF!
 *       Una posizione è sempre attiva.
 * 
 * ============================================
 * ROTARY SWITCH 3 POSIZIONI (ROT3: OFF + 2)
 * ============================================
 * 
 * Selettore rotativo con 3 posizioni: OFF, 1, 2
 * Ha 3 terminali: COMUNE + 2 posizioni
 * 
 * Cablaggio ROT3:
 *   Pos 1: Pin 8 (ROW3) ──|◄── Pin 13 (COL3)
 *   Pos 2: Pin 8 (ROW3) ──|◄── Pin 4 (COL4)
 * 
 * Funzionamento:
 *   - OFF      → Tutti 0
 *   - Pos 1    → Pulsante 24 = 1
 *   - Pos 2    → Pulsante 25 = 1
 * 
 * ============================================
 * DIODI ANTI-GHOSTING (1N4148 DO-35)
 * ============================================
 * 
 * Ogni switch/pulsante ha un diodo 1N4148:
 * 
 *   [Pin ROW] ────|◄────[SWITCH]──────── [Pin COL]
 *                 ▲
 *            CATODO (banda nera)
 *            verso il pin ROW
 * 
 * Totale diodi: ~23 (dipende dalla configurazione)
 * 
 * ============================================
 * PULSANTI BTN1 e PEDALE (IN PARALLELO)
 * ============================================
 * 
 * BTN1 e PEDALE sono collegati IN PARALLELO allo stesso slot matrice!
 * Premere uno qualsiasi dei due attiva il pulsante 17.
 * 
 * Schema (entrambi con diodo verso ROW0):
 *   Pin 5 (ROW0) ──|◄── [BTN1]  ──┬── Pin 10 (COL0)
 *   Pin 5 (ROW0) ──|◄── [PEDALE]──┘
 * 
 * ============================================
 * ENCODER CLICK (ENC_SW)
 * ============================================
 * 
 * Il click dell'encoder è nella matrice:
 *   Pin 5 (ROW0) ──|◄── [ENC_SW] ──── Pin A5 (COL5)
 * 
 * ============================================
 * POTENZIOMETRI SLIDER 100mm CON CONDENSATORI
 * ============================================
 * 
 * Ogni slider B10K (10kΩ lineare 100mm) con condensatore 100nF (104):
 *   - Pin sinistro  → GND
 *   - Pin centrale  → Pin analogico + Condensatore
 *   - Pin destro    → +5V
 * 
 * Schema:
 *          +5V
 *           │
 *     [SLIDER B10K]
 *       ══════════
 *           │
 *    Pin A ─┼───┤├──── GND
 *           │   104 (100nF)
 *        (wiper)
 * 
 * SLIDER 1 (Asse X): centrale → A0 + condensatore 100nF a GND
 * SLIDER 2 (Asse Y): centrale → A1 + condensatore 100nF a GND
 * SLIDER 3 (Asse Z): centrale → A2 + condensatore 100nF a GND
 * 
 * ============================================
 * ENCODER ROTATIVO
 * ============================================
 * 
 * Encoder EC11 con pulsante (5 pin):
 *   - GND → GND
 *   - +   → +5V
 *   - SW  → MATRICE (ROW0-COL5, cioè pin 5 e pin A5)
 *   - DT  → Pin 3 (interrupt)
 *   - CLK → Pin 2 (interrupt)
 * 
 * NOTA: Il click encoder è nella matrice!
 *       Collegare SW tra ROW0 (pin 5) e COL5 (pin A5) con diodo.
 * 
 * ============================================
 * LED CHARLIEPLEXING (13 LED con 5 pin!)
 * ============================================
 * 
 * Con la tecnica Charlieplexing, 5 pin controllano fino a 20 LED.
 * Usiamo 13 LED.
 * 
 * Pin usati: A3 (LED_A), 0 (LED_B), 1 (LED_C), A4 (LED_D), 14/MISO (LED_E)
 * 
 * IMPORTANTE: Ogni LED necessita di un RESISTORE in serie!
 * 
 * Tutti i LED sono ad alta Vf (3-6V) con plastica colorata.
 * LED1 (SIFA) è un LED bianco con involucro giallo.
 * 
 * Calcolo resistori (I ≈ 8mA):
 *   LED (Vf ≈ 3.2V): R = (5-3.2)/0.008 = 225Ω → usa 220Ω
 * 
 * Schema cablaggio (ogni LED ha il suo resistore 220Ω):
 * 
 *         LED1 (SIFA)               LED2 (LZB Ende)
 *    A3 ──[220Ω]──►|────────────|◄──[220Ω]── 0
 *         bianco(giallo)          giallo
 * 
 *         LED3 (PZB 70)             LED4 (PZB 85)
 *    A3 ──[220Ω]──►|────────────|◄──[220Ω]── 1
 *              blu                 blu
 * 
 *         LED5 (PZB 55)             LED6 (500Hz)
 *     0 ──[220Ω]──►|────────────|◄──[220Ω]── 1
 *              blu                rosso
 * 
 *         LED7 (1000Hz)             LED8 (Porte SX)
 *    A3 ──[220Ω]──►|────────────|◄──[220Ω]── A4
 *             giallo              giallo
 * 
 *         LED9 (Porte DX)           LED10 (LZB Ü)
 *     0 ──[220Ω]──►|────────────|◄──[220Ω]── A4
 *             giallo               blu
 * 
 *                                   (NB: LED9 è 0→A4, LED10 è 1→A4)
 *         LED10 (LZB Ü)
 *     1 ──[220Ω]──►|──────────── A4
 *              blu
 * 
 *         LED11 (LZB G)             LED12 (LZB S)
 *    A4 ──[220Ω]──►|────────────|◄──[220Ω]── (nessuno)
 *              blu                rosso
 *    (LED11: A4→0)              (LED12: A4→1)
 * 
 *         LED13 (Befehl 40)
 *    A3 ──[220Ω]──►|──────────── 14 (MISO, ICSP)
 *             giallo
 *    (LED13: A3→14)
 * 
 * NOTA: Il resistore va SEMPRE tra il pin e l'ANODO del LED!
 *       L'anodo è la gamba LUNGA del LED.
 *       Il catodo (gamba corta) va verso l'altro pin.
 * 
 * Tabella LED:
 *   LED1:  A3→0  = SIFA Warning (bianco/giallo, 220Ω)
 *   LED2:  0→A3  = LZB Ende (giallo, 220Ω)
 *   LED3:  A3→1  = PZB 70 (blu, 220Ω)
 *   LED4:  1→A3  = PZB 85 (blu, 220Ω)
 *   LED5:  0→1   = PZB 55 (blu, 220Ω)
 *   LED6:  1→0   = 500Hz (rosso, 220Ω)
 *   LED7:  A3→A4 = 1000Hz (giallo, 220Ω)
 *   LED8:  A4→A3 = Porte SX (giallo, 220Ω)
 *   LED9:  0→A4  = Porte DX (giallo, 220Ω)
 *   LED10: 1→A4  = LZB Ü (blu, 220Ω)
 *   LED11: A4→0  = LZB G (rosso, 220Ω)
 *   LED12: A4→1  = LZB S (rosso, 220Ω)
 *   LED13: A3→14  = Befehl 40 (giallo, 220Ω)
 * 
 * Comandi seriali (115200 baud):
 *   SIFA:1     → Accendi LED1  (bianco/giallo)
 *   SIFA:0     → Spegni LED1
 *   LZB:1      → Accendi LED2  (giallo) - LZB Ende
 *   LZB:0      → Spegni LED2
 *   PZB70:1    → Accendi LED3  (blu)
 *   PZB70:0    → Spegni LED3
 *   PZB80:1    → Accendi LED4  (blu)
 *   PZB80:0    → Spegni LED4
 *   PZB50:1    → Accendi LED5  (blu)
 *   PZB50:0    → Spegni LED5
 *   500HZ:1    → Accendi LED6  (rosso)
 *   500HZ:0    → Spegni LED6
 *   1000HZ:1   → Accendi LED7  (giallo)
 *   1000HZ:0   → Spegni LED7
 *   TUEREN_L:1 → Accendi LED8  (giallo) - porte sinistra
 *   TUEREN_L:0 → Spegni LED8
 *   TUEREN_R:1 → Accendi LED9  (giallo) - porte destra
 *   TUEREN_R:0 → Spegni LED9
 *   LZB_UE:1   → Accendi LED10 (blu) - Übertragung
 *   LZB_UE:0   → Spegni LED10
 *   LZB_G:1    → Accendi LED11 (rosso) - G aktiv
 *   LZB_G:0    → Spegni LED11
 *   LZB_S:1    → Accendi LED12 (rosso) - Schnellbremsung
 *   LZB_S:0    → Spegni LED12
 *   BEF40:1    → Accendi LED13 (giallo) - Befehl 40
 *   BEF40:0    → Spegni LED13
 *   LED:n:1    → Accendi LED n (1-13)
 *   LED:n:0    → Spegni LED n
 *   OFF        → Spegni tutti i LED
 * 
 * ============================================
 * LISTA COMPONENTI
 * ============================================
 * 
 * - 1x Arduino Leonardo (ATmega32U4)
 * - 3x Potenziometro SLIDER 100mm B10K
 * - 1x Encoder rotativo EC11 con pulsante
 * - 8x Switch ON-OFF-ON momentaneo (SW1-SW8, tornano al centro)
 * - 2x Switch ON-OFF-ON self-lock (TOGGLE1, TOGGLE2, mantengono posizione)
 * - 1x Rotary switch 4 posizioni (ROT4: 4 ON, nessun OFF)
 * - 1x Rotary switch 3 posizioni (ROT3: OFF + 2)
 * - 1x Pulsante momentaneo (BTN1)
 * - 1x Pulsante a pedale (foot switch)
 * - 3x Condensatore ceramico 100nF (104)
 * - ~25x Diodo 1N4148 DO-35 (matrice)
 * - 13x LED 5mm (1 bianco/giallo, 5 giallo, 4 blu, 3 rosso)
 * - 13x Resistori 220Ω (tutti i LED)
 * - Cavetti jumper
 * - Breadboard o PCB
 * 
 * LIBRERIE RICHIESTE:
 * - Joystick (Matthew Heironimus) - da GitHub
 * - Encoder (Paul Stoffregen) - da Library Manager
 * 
 * ============================================
 * NOTE IMPORTANTI
 * ============================================
 * 
 * 1. Arduino Leonardo usa ATmega32U4 = USB nativo
 * 
 * 2. I pin 2 e 3 hanno interrupt hardware per l'encoder
 * 
 * 3. TX/RX (pin 0 e 1) usati per LED Charlieplexing
 *    Serial USB funziona comunque (è su USB, non su pin!)
 * 
 * 4. Il Leonardo ha più pin del Pro Micro:
 *    - Pin 11, 12, 13 accessibili direttamente
 *    - Pin A4, A5 accessibili
 *    - Pin 14 (MISO), 15 (SCK), 16 (MOSI) sull'header ICSP
 * 
 * 5. La matrice 5x6 permette pressioni simultanee
 *    30 posizioni: 28 usate + 2 slot vuoti
 * 
 * 6. I diodi 1N4148 prevengono ghosting (letture fantasma)
 *    Catodo (banda) sempre verso il pin ROW
 * 
 * 7. I condensatori 100nF filtrano il rumore sui potenziometri
 *    Collegare tra pin centrale (wiper) e GND
 * 
 * 8. Nel Board Manager seleziona "Arduino Leonardo"
 *
 * 9. Leonardo supporta USB HID + Serial CDC contemporaneamente!
 *    Joystick e LED Zusi3 funzionano insieme.
 *
 * 10. BTN1 e PEDALE sono IN PARALLELO - stesso pulsante joystick!
 *
 */
