# Arduino Firmware — Due versioni

Sono disponibili **due versioni** del firmware Arduino per il pannello MFA.
Entrambe sono **compatibili al 100%** con Train Simulator Bridge (stesso protocollo seriale).

---

## Quale scegliere?

| | **ArduinoSerialOnly** | **ArduinoJoystick** |
|---|---|---|
| **Scopo** | Solo pannello LED (MFA) | Pannello LED + controller joystick completo |
| **Componenti** | ~16 (Arduino + MAX7219 + 13 LED) | ~70+ (MAX7219 + LED + slider + encoder + switch + diodi) |
| **Pin usati** | 3 (A3, A4, A5) per MAX7219 | Tutti (20 pin) |
| **Librerie** | Nessuna | Joystick + Encoder |
| **Difficoltà** | ⭐ Facile | ⭐⭐⭐ Avanzato |
| **Ideale per** | Chi vuole solo le spie MFA fisiche | Chi vuole anche un controller fisico per il treno |

---

## ArduinoSerialOnly — Solo LED (versione semplice)

**Cartella**: `ArduinoSerialOnly/`

La versione minimalista: riceve comandi seriali da Train Simulator Bridge e pilota 13 LED fisici tramite modulo MAX7219 (3 pin SPI).

### Cosa fa
- Riceve comandi via USB Serial (115200 baud)
- Controlla 13 LED MFA (PZB/SIFA/LZB/Porte/Befehl)
- Test LED all'avvio (sequenza)
- Nessuna libreria esterna necessaria

### Hardware necessario
| Qtà | Componente | Note |
|-----|-----------|------|
| 1 | Arduino Leonardo (ATmega32U4) | **Deve** essere Leonardo (USB nativo) |
| 1 | Modulo MAX7219 (WCMCU DISY1) | Driver LED SPI |
| 13 | LED 5mm | 1 bianco/giallo, 5 giallo, 4 blu, 3 rosso |
| — | Cavetti, breadboard o PCB | — |

### Pin utilizzati
```
A3 = MAX7219_DIN
A4 = MAX7219_CLK
A5 = MAX7219_CS   (LOAD)
```
Tutti gli altri pin (0-13, A0-A2) sono **liberi**.

### Come caricare
1. Apri `ArduinoSerialOnly/ArduinoSerialOnly.ino` in Arduino IDE
2. Seleziona **Board → Arduino Leonardo**
3. Seleziona la porta COM corretta
4. Clicca **Upload**

---

## ArduinoJoystick — LED + Controller (versione completa)

**Cartella**: `ArduinoJoystick/`

La versione completa: oltre ai 13 LED, include un joystick USB HID con 3 slider analogici, encoder rotativo, 8 switch momentanei, 2 toggle self-lock, 2 rotary switch e pulsante/pedale.

### Cosa fa
- Tutto ciò che fa ArduinoSerialOnly **+**
- Joystick USB HID con 28 pulsanti e 4 assi
- 3 potenziometri slider 100mm (assi X, Y, Z)
- 1 encoder rotativo con click (asse Rx)
- Matrice pulsanti 5×6 (switch, toggle, rotary)
- Appare come joystick in Windows

### Hardware necessario
| Qtà | Componente | Note |
|-----|-----------|------|
| 1 | Arduino Leonardo (ATmega32U4) | **Deve** essere Leonardo |
| 3 | Potenziometro slider 100mm B10K | Assi X, Y, Z |
| 3 | Condensatore ceramico 100nF (104) | Filtro rumore slider |
| 1 | Encoder rotativo EC11 con pulsante | CLK, DT, SW |
| 8 | Switch ON-OFF-ON momentaneo | SW1–SW8, tornano al centro |
| 2 | Switch ON-OFF-ON self-lock | TOGGLE1–2, mantengono posizione |
| 1 | Rotary switch 4 posizioni | ROT4 (nessun OFF) |
| 1 | Rotary switch 3 posizioni | ROT3 (OFF + 2) |
| 1 | Pulsante momentaneo | BTN1 |
| 1 | Pedale (foot switch) | In parallelo con BTN1 |
| ~25 | Diodo 1N4148 DO-35 | Anti-ghosting matrice |
| 1 | Modulo MAX7219 (WCMCU DISY1) | Driver LED SPI |
| 13 | LED 5mm | 1 bianco/giallo, 5 giallo, 4 blu, 3 rosso |
| — | Cavetti, breadboard o PCB | — |

### Librerie richieste
- **Joystick** (Matthew Heironimus) — da [GitHub](https://github.com/MHeironworths/ArduinoJoystickLibrary)
- **Encoder** (Paul Stoffregen) — da Arduino Library Manager

### Come caricare
1. Installa le librerie Joystick e Encoder
2. Apri `ArduinoJoystick/ArduinoJoystick.ino` in Arduino IDE
3. Seleziona **Board → Arduino Leonardo**
4. Seleziona la porta COM corretta
5. Clicca **Upload**

---

## 13 LED del pannello MFA

Entrambe le versioni usano lo **stesso modulo MAX7219** per pilotare i 13 LED:

| # | LED | Colore | MAX7219 | Funzione |
|---|-----|--------|---------|----------|
| 1 | SIFA | bianco/giallo | DIG0.A | Sicherheitsfahrschaltung (vigilanza) |
| 2 | LZB | giallo | DIG0.B | Linienzugbeeinflussung Ende |
| 3 | PZB 70 | blu | DIG0.C | PZB Zugart M (70 km/h) |
| 4 | PZB 85 | blu | DIG0.D | PZB Zugart O (85 km/h) |
| 5 | PZB 55 | blu | DIG0.E | PZB Zugart U (55 km/h) |
| 6 | 500Hz | rosso | DIG0.F | PZB 500 Hz |
| 7 | 1000Hz | giallo | DIG0.G | PZB 1000 Hz |
| 8 | Türen L | giallo | DIG0.DP | Porte sinistra |
| 9 | Türen R | giallo | DIG1.A | Porte destra |
| 10 | LZB Ü | blu | DIG1.B | LZB Überwachung (sorveglianza) |
| 11 | LZB G | rosso | DIG1.C | LZB Geführt (attivo) |
| 12 | LZB S | rosso | DIG1.D | LZB Schnellbremsung (frenata) |
| 13 | Befehl 40 | giallo | DIG1.E | Befehl 40 km/h |

**LED totali**: 1 bianco/giallo, 5 giallo, 4 blu, 3 rosso
**Connessione**: Arduino A3 (DIN), A4 (CLK), A5 (CS) → modulo MAX7219

---

## Protocollo seriale (comune a entrambe)

Baud rate: **115200**, terminatore: `\n`

| Comando | Effetto |
|---------|---------|
| `SIFA:1` / `SIFA:0` | Accendi/spegni LED1 |
| `LZB:1` / `LZB:0` | Accendi/spegni LED2 |
| `PZB70:1` / `PZB70:0` | Accendi/spegni LED3 |
| `PZB80:1` / `PZB80:0` | Accendi/spegni LED4 |
| `PZB50:1` / `PZB50:0` | Accendi/spegni LED5 |
| `500HZ:1` / `500HZ:0` | Accendi/spegni LED6 |
| `1000HZ:1` / `1000HZ:0` | Accendi/spegni LED7 |
| `TUEREN_L:1` / `TUEREN_L:0` | Accendi/spegni LED8 |
| `TUEREN_R:1` / `TUEREN_R:0` | Accendi/spegni LED9 |
| `LZB_UE:1` / `LZB_UE:0` | Accendi/spegni LED10 |
| `LZB_G:1` / `LZB_G:0` | Accendi/spegni LED11 |
| `LZB_S:1` / `LZB_S:0` | Accendi/spegni LED12 |
| `BEF40:1` / `BEF40:0` | Accendi/spegni LED13 |
| `LED:n:1` / `LED:n:0` | Accendi/spegni LED n (1-13) |
| `OFF` | Spegni tutti i LED |

---

## Schema LED MAX7219 (3 pin SPI)

```
  Arduino Leonardo              MAX7219 (WCMCU DISY1)
  ┌──────────────┐             ┌─────────────────────────┐
  │   Pin A3     │──── DIN ───►│ IN                  LED │
  │              │             │                         │
  │   Pin A4     │──── CLK ───►│  DIG0:                  │
  │   Pin A5     │──── CS  ───►│    A  → LED1  (SIFA)    │
  │   +5V        │──── VCC ───►│    B  → LED2  (LZB)     │
  │   GND        │──── GND ───►│    C  → LED3  (PZB70)   │
  └──────────────┘             │    D  → LED4  (PZB85)   │
                               │    E  → LED5  (PZB55)   │
                               │    F  → LED6  (500Hz)   │
                               │    G  → LED7  (1000Hz)  │
                               │    DP → LED8  (Porte L) │
                               │                         │
                               │  DIG1:                  │
                               │    A  → LED9  (Porte R) │
                               │    B  → LED10 (LZB Ü)   │
                               │    C  → LED11 (LZB G)   │
                               │    D  → LED12 (LZB S)   │
                               │    E  → LED13 (BEF40)   │
                               └─────────────────────────┘
```

Ogni LED: ANODO (+) al pin SEG_x, CATODO (-) al pin DIG_x.
Nessun resistore individuale necessario (RSET già presente sul modulo).
Tutti e 3 i pin MAX7219 sono sull'header analogico, adiacenti.
