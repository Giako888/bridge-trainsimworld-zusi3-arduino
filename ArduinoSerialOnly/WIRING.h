/*
 * Schema Connessioni — Arduino Leonardo Serial Only (12 LED Charlieplexing)
 * 
 * Versione SEMPLIFICATA: solo 4 pin per i LED + USB.
 * Niente joystick, encoder, matrice pulsanti o slider.
 * 
 * ============================================
 * PINOUT ARDUINO LEONARDO (Serial Only)
 * ============================================
 * 
 * Solo 4 pin usati per i LED + alimentazione USB!
 * Tutti gli altri pin sono LIBERI per usi futuri.
 * 
 *              ┌────USB────┐
 *   LED_C (TX)│ 1      RAW│
 *   LED_B (RX)│ 0      GND│ ◄── GND
 *             │ GND    RST│
 *       GND   │ GND    VCC│ ◄── +5V
 *        ---  │ 2      A3 │ ◄── LED_A
 *        ---  │ 3      A2 │ --- (libero)
 *        ---  │ 4      A1 │ --- (libero)
 *        ---  │ 5      A0 │ --- (libero)
 *        ---  │ 6      A5 │ --- (libero)
 *        ---  │ 7      A4 │ ◄── LED_D
 *        ---  │ 8      13 │ --- (libero)
 *        ---  │ 9      12 │ --- (libero)
 *        ---  │ 10     11 │ --- (libero)
 *             └───────────┘
 * 
 * Pin utilizzati:
 *   A3 = LED_A (Charlieplexing pin A)
 *    0 = LED_B (Charlieplexing pin B) — RX, ma Serial è su USB!
 *    1 = LED_C (Charlieplexing pin C) — TX, ma Serial è su USB!
 *   A4 = LED_D (Charlieplexing pin D)
 * 
 * NOTA: I pin 0 (RX) e 1 (TX) sul Leonardo sono per la UART
 * hardware (Serial1), NON per la Serial USB! La comunicazione
 * seriale con il PC avviene via USB nativo (CDC), quindi
 * questi pin sono liberi per i LED.
 * 
 * ============================================
 * LED CHARLIEPLEXING (12 LED con 4 pin)
 * ============================================
 * 
 * Con la tecnica Charlieplexing, 4 pin controllano 12 LED.
 * Ogni coppia di pin può gestire 2 LED (uno per direzione).
 * 
 * Pin usati: A3 (LED_A), 0 (LED_B), 1 (LED_C), A4 (LED_D)
 * 
 * IMPORTANTE: Ogni LED necessita di un RESISTORE 220Ω in serie!
 * Il resistore va tra il pin e l'ANODO del LED (gamba lunga).
 * Il CATODO (gamba corta) va verso l'altro pin.
 * 
 * Schema cablaggio:
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
 *         LED9 (Porte DX)
 *     0 ──[220Ω]──►|──────────── A4
 *             giallo
 * 
 *         LED10 (LZB Ü)
 *     1 ──[220Ω]──►|──────────── A4
 *              blu
 * 
 *         LED11 (LZB G)
 *    A4 ──[220Ω]──►|──────────── 0
 *             rosso
 * 
 *         LED12 (LZB S)
 *    A4 ──[220Ω]──►|──────────── 1
 *             rosso
 * 
 * ============================================
 * TABELLA RIASSUNTIVA LED
 * ============================================
 * 
 *  LED │ Direzione │ Funzione                     │ Colore
 * ─────┼───────────┼──────────────────────────────┼─────────────
 *   1  │ A3 → 0    │ SIFA Warning                 │ bianco/giallo
 *   2  │  0 → A3   │ LZB Ende                     │ giallo
 *   3  │ A3 → 1    │ PZB 70 (Zugart M)            │ blu
 *   4  │  1 → A3   │ PZB 85 (Zugart O)            │ blu
 *   5  │  0 → 1    │ PZB 55 (Zugart U)            │ blu
 *   6  │  1 → 0    │ 500Hz (PZB frequenza)        │ rosso
 *   7  │ A3 → A4   │ 1000Hz (PZB frequenza)       │ giallo
 *   8  │ A4 → A3   │ Porte Sinistra (Türen L)     │ giallo
 *   9  │  0 → A4   │ Porte Destra (Türen R)       │ giallo
 *  10  │  1 → A4   │ LZB Ü (Überwachung)          │ blu
 *  11  │ A4 → 0    │ LZB G (Geführt/attivo)       │ rosso
 *  12  │ A4 → 1    │ LZB S (Schnellbremsung)      │ rosso
 * 
 * ============================================
 * COMANDI SERIALI (115200 baud)
 * ============================================
 * 
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
 *   LED:n:1    → Accendi LED n (1-12)
 *   LED:n:0    → Spegni LED n
 *   OFF        → Spegni tutti i LED
 * 
 * ============================================
 * LISTA COMPONENTI
 * ============================================
 * 
 * - 1x Arduino Leonardo (ATmega32U4)
 * - 12x LED 5mm (1 bianco/giallo, 4 giallo, 4 blu, 3 rosso)
 * - 12x Resistore 220Ω
 * - Cavetti jumper
 * - Breadboard o PCB
 * 
 * Totale: ~15 componenti (+ cavetti)
 * Nessuna libreria Arduino extra richiesta!
 * 
 * ============================================
 * NOTE IMPORTANTI
 * ============================================
 * 
 * 1. Arduino Leonardo usa ATmega32U4 = USB nativo
 *    La Serial USB (CDC) funziona sui pin USB, NON sui pin 0/1!
 * 
 * 2. Nessuna libreria esterna necessaria (no Joystick, no Encoder)
 * 
 * 3. Calcolo resistori: R = (5V - 3.2V) / 8mA ≈ 225Ω → uso 220Ω
 * 
 * 4. Nel Board Manager di Arduino IDE: seleziona "Arduino Leonardo"
 * 
 * 5. Il LED multiplexing gira a ~62Hz (2ms per LED), abbastanza
 *    veloce da apparire come accensione continua all'occhio umano.
 * 
 * 6. Tutti i pin non usati (2-13, A0-A2, A5) restano liberi
 *    per eventuali espansioni future.
 * 
 */
