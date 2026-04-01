/*
 * Schema Connessioni — Arduino Leonardo Serial Only (13 LED MAX7219)
 * 
 * Versione SEMPLIFICATA: solo 3 pin per i LED (MAX7219) + USB.
 * Niente joystick, encoder, matrice pulsanti o slider.
 * 
 * ============================================
 * PINOUT ARDUINO LEONARDO (Serial Only)
 * ============================================
 * 
 * Solo 3 pin usati per MAX7219 + alimentazione USB!
 * Tutti gli altri pin sono LIBERI per usi futuri.
 * 
 *              ┌────USB────┐
 *        ---  │ 1      RAW│
 *        ---  │ 0      GND│ ◄── GND
 *             │ GND    RST│
 *       GND   │ GND    VCC│ ◄── +5V
 *        ---  │ 2      A3 │ ◄── MAX7219_DIN
 *        ---  │ 3      A2 │ --- (libero)
 *        ---  │ 4      A1 │ --- (libero)
 *        ---  │ 5      A0 │ --- (libero)
 *        ---  │ 6      A5 │ ◄── MAX7219_CS
 *        ---  │ 7      A4 │ ◄── MAX7219_CLK
 *        ---  │ 8      13 │ --- (libero)
 *        ---  │ 9      12 │ --- (libero)
 *        ---  │ 10     11 │ --- (libero)
 *             └───────────┘
 * 
 * Pin utilizzati (tutti sullo header analogico, adiacenti):
 *   A3 = MAX7219_DIN
 *   A4 = MAX7219_CLK
 *   A5 = MAX7219_CS (LOAD)
 * 
 * ============================================
 * LED MAX7219 (13 LED con modulo WCMCU DISY1)
 * ============================================
 * 
 * Il modulo MAX7219 (WCMCU DISY1 breakout) pilota tutti i 13 LED.
 * Comunicazione SPI software su 3 pin.
 * Nessun resistore individuale necessario (RSET già sul modulo).
 * Tutti i LED possono essere accesi contemporaneamente!
 * 
 * Connessioni Arduino → MAX7219 (lato IN):
 *   Pin A3               → DIN
 *   Pin A4               → CLK
 *   Pin A5               → CS (LOAD)
 *   +5V                  → VCC
 *   GND                  → GND
 * 
 * Connessioni MAX7219 (lato LED):
 *
 *   DIG0:
 *     SEG_A  → LED1  SIFA (bianco/giallo)
 *     SEG_B  → LED2  LZB Ende (giallo)
 *     SEG_C  → LED3  PZB 70 (blu)
 *     SEG_D  → LED4  PZB 85 (blu)
 *     SEG_E  → LED5  PZB 55 (blu)
 *     SEG_F  → LED6  500Hz (rosso)
 *     SEG_G  → LED7  1000Hz (giallo)
 *     SEG_DP → LED8  Porte SX (giallo)
 *
 *   DIG1:
 *     SEG_A  → LED9  Porte DX (giallo)
 *     SEG_B  → LED10 LZB Ü (blu)
 *     SEG_C  → LED11 LZB G (rosso)
 *     SEG_D  → LED12 LZB S (rosso)
 *     SEG_E  → LED13 Befehl 40 (giallo)
 * 
 * Schema cablaggio LED:
 *   Ogni LED: ANODO (+) al pin SEG_x, CATODO (-) al pin DIG_x
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
 *   DP ──┤►| LED8 PorteL│─── DIG0
 *        └──────────────┘
 *
 *         MAX7219 DIG1
 *        ┌──────────────┐
 *   A ───┤►| LED9 PorteR│─── DIG1
 *   B ───┤►| LED10 LZBÜ │─── DIG1
 *   C ───┤►| LED11 LZBG │─── DIG1
 *   D ───┤►| LED12 LZBS │─── DIG1
 *   E ───┤►| LED13 BEF40│─── DIG1
 *        └──────────────┘
 * 
 * ============================================
 * TABELLA RIASSUNTIVA LED
 * ============================================
 * 
 *  LED │ MAX7219      │ Funzione                     │ Colore
 * ─────┼──────────────┼──────────────────────────────┼─────────────
 *   1  │ DIG0.A       │ SIFA Warning                 │ bianco/giallo
 *   2  │ DIG0.B       │ LZB Ende                     │ giallo
 *   3  │ DIG0.C       │ PZB 70 (Zugart M)            │ blu
 *   4  │ DIG0.D       │ PZB 85 (Zugart O)            │ blu
 *   5  │ DIG0.E       │ PZB 55 (Zugart U)            │ blu
 *   6  │ DIG0.F       │ 500Hz (PZB frequenza)        │ rosso
 *   7  │ DIG0.G       │ 1000Hz (PZB frequenza)       │ giallo
 *   8  │ DIG0.DP      │ Porte Sinistra (Türen L)     │ giallo
 *   9  │ DIG1.A       │ Porte Destra (Türen R)       │ giallo
 *  10  │ DIG1.B       │ LZB Ü (Überwachung)          │ blu
 *  11  │ DIG1.C       │ LZB G (Geführt/attivo)       │ rosso
 *  12  │ DIG1.D       │ LZB S (Schnellbremsung)      │ rosso
 *  13  │ DIG1.E       │ Befehl 40                    │ giallo
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
 * - 1x Modulo MAX7219 (WCMCU DISY1 breakout)
 * - 13x LED 5mm (1 bianco/giallo, 5 giallo, 4 blu, 3 rosso)
 * - Cavetti jumper
 * - Breadboard o PCB
 * 
 * Totale: ~16 componenti (+ cavetti)
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
 * 3. Il MAX7219 gestisce la corrente internamente (RSET sul modulo).
 *    NON servono resistori individuali per ogni LED.
 * 
 * 4. Nel Board Manager di Arduino IDE: seleziona "Arduino Leonardo"
 * 
 * 5. Con il MAX7219, tutti i LED possono essere accesi contemporaneamente
 *    (a differenza del Charlieplexing che usa multiplexing).
 * 
 * 6. Tutti i pin non usati (0-13, A0-A2) restano liberi
 *    per eventuali espansioni future.
 * 
 */
