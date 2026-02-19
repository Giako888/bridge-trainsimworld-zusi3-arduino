# Arduino Firmware — Due versioni

Sono disponibili **due versioni** del firmware Arduino per il pannello MFA.
Entrambe sono **compatibili al 100%** con Train Simulator Bridge (stesso protocollo seriale).

---

## Quale scegliere?

| | **ArduinoSerialOnly** | **ArduinoJoystick** |
|---|---|---|
| **Scopo** | Solo pannello LED (MFA) | Pannello LED + controller joystick completo |
| **Componenti** | ~16 (Arduino + 13 LED + 13 resistori) | ~70+ (LED + slider + encoder + switch + diodi) |
| **Pin usati** | 5 (A3, 0, 1, A4, 14/MISO) | Tutti (20 pin) + pin 14 (ICSP) |
| **Librerie** | Nessuna | Joystick + Encoder |
| **Difficoltà** | ⭐ Facile | ⭐⭐⭐ Avanzato |
| **Ideale per** | Chi vuole solo le spie MFA fisiche | Chi vuole anche un controller fisico per il treno |

---

## ArduinoSerialOnly — Solo LED (versione semplice)

**Cartella**: `ArduinoSerialOnly/`

La versione minimalista: riceve comandi seriali da Train Simulator Bridge e pilota 13 LED fisici tramite Charlieplexing su 5 pin.

### Cosa fa
- Riceve comandi via USB Serial (115200 baud)
- Controlla 13 LED MFA (PZB/SIFA/LZB/Porte/Befehl)
- Test LED all'avvio (sequenza)
- Nessuna libreria esterna necessaria

### Hardware necessario
| Qtà | Componente | Note |
|-----|-----------|------|
| 1 | Arduino Leonardo (ATmega32U4) | **Deve** essere Leonardo (USB nativo) |
| 13 | LED 5mm | 1 bianco/giallo, 5 giallo, 4 blu, 3 rosso |
| 13 | Resistore 220Ω | Uno per ogni LED |
| — | Cavetti, breadboard o PCB | — |

### Pin utilizzati
```
A3 = LED_A     (Charlieplexing)
 0 = LED_B     (pin RX, ma Serial è via USB!)
 1 = LED_C     (pin TX, ma Serial è via USB!)
A4 = LED_D     (Charlieplexing)
14 = LED_E     (MISO, header ICSP — saldare 1 filo)
```
Pin 14 (MISO) si trova sull'header ICSP (6 pin al centro della scheda).
Tutti gli altri pin sono **liberi**.

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
| 13 | LED 5mm | 1 bianco/giallo, 5 giallo, 4 blu, 3 rosso |
| 13 | Resistore 220Ω | Uno per ogni LED |
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

Entrambe le versioni usano lo **stesso schema LED Charlieplexing** su 5 pin:

| # | LED | Colore | Direzione | Funzione |
|---|-----|--------|-----------|----------|
| 1 | SIFA | bianco/giallo | A3 → 0 | Sicherheitsfahrschaltung (vigilanza) |
| 2 | LZB | giallo | 0 → A3 | Linienzugbeeinflussung Ende |
| 3 | PZB 70 | blu | A3 → 1 | PZB Zugart M (70 km/h) |
| 4 | PZB 85 | blu | 1 → A3 | PZB Zugart O (85 km/h) |
| 5 | PZB 55 | blu | 0 → 1 | PZB Zugart U (55 km/h) |
| 6 | 500Hz | rosso | 1 → 0 | PZB 500 Hz |
| 7 | 1000Hz | giallo | A3 → A4 | PZB 1000 Hz |
| 8 | Türen L | giallo | A4 → A3 | Porte sinistra |
| 9 | Türen R | giallo | 0 → A4 | Porte destra |
| 10 | LZB Ü | blu | 1 → A4 | LZB Überwachung (sorveglianza) |
| 11 | LZB G | rosso | A4 → 0 | LZB Geführt (attivo) |
| 12 | LZB S | rosso | A4 → 1 | LZB Schnellbremsung (frenata) |
| 13 | Befehl 40 | giallo | A3 → 14 | Befehl 40 km/h |

**LED totali**: 1 bianco/giallo, 5 giallo, 4 blu, 3 rosso
**Pin 14** (MISO) è sull'header ICSP, richiede 1 filo saldato.

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

## Schema LED Charlieplexing (5 pin)

```
                    A3 (LED_A)
                    │
        ┌───────────┼───────────┐───────────┐───────────┐
        │           │           │           │           │
   [220Ω]→LED1  [220Ω]→LED3  [220Ω]→LED7   │      [220Ω]→LED13
        │           │           │           │           │
        ▼           ▼           ▼           │           ▼
     0 (LED_B)   1 (LED_C)   A4 (LED_D)    │      14 (LED_E)
        │           │           │           │       MISO/ICSP
   LED2→[220Ω]  LED4→[220Ω]  LED8→[220Ω]   │
        │           │           │           │
        └─────►A3   └─────►A3  └─────►A3   │
                                            │
     0 (LED_B)                              │
        │                                   │
   [220Ω]→LED5    [220Ω]→LED9              │
        │              │                    │
        ▼              ▼                    │
     1 (LED_C)    A4 (LED_D)               │
        │              │                    │
   LED6→[220Ω]                              │
        │                                   │
        └─────►0                            │
                                            │
     1 (LED_C)                              │
        │                                   │
   [220Ω]→LED10                             │
        │                                   │
        ▼                                   │
     A4 (LED_D)                             │
        │                                   │
   [220Ω]→LED11────►0                       │
   [220Ω]→LED12────►1                       │
```

Ogni LED ha il resistore 220Ω sul lato ANODO (gamba lunga).
Il catodo (gamba corta) va direttamente all'altro pin.
**Pin 14 (MISO)** è sull'header ICSP — saldare 1 filo.
