# Arduino-Firmware — Zwei Versionen

Es stehen **zwei Versionen** der Arduino-Firmware für das MFA-Panel zur Verfügung.
Beide sind **100 % kompatibel** mit Train Simulator Bridge (gleiches serielles Protokoll).

---

## Welche Version wählen?

| | **ArduinoSerialOnly** | **ArduinoJoystick** |
|---|---|---|
| **Zweck** | Nur LED-Panel (MFA) | LED-Panel + vollständiger Joystick-Controller |
| **Bauteile** | ~16 (Arduino + MAX7219 + 13 LEDs) | ~70+ (LEDs + Slider + Encoder + Schalter + Dioden) |
| **Verwendete Pins** | 3 (A3, A4, A5) für MAX7219 | Alle (20 Pins) |
| **Bibliotheken** | Keine | Joystick + Encoder |
| **Schwierigkeit** | ⭐ Einfach | ⭐⭐⭐ Fortgeschritten |
| **Ideal für** | Wer nur die physischen MFA-Anzeigen möchte | Wer auch einen physischen Zug-Controller möchte |

---

## ArduinoSerialOnly — Nur LEDs (einfache Version)

**Ordner**: `ArduinoSerialOnly/`

Die minimalistische Version: empfängt serielle Befehle von Train Simulator Bridge und steuert 13 physische LEDs über MAX7219-Modul (3 SPI-Pins).

### Funktionen
- Empfängt Befehle über USB-Seriell (115200 Baud)
- Steuert 13 MFA-LEDs (PZB/SIFA/LZB/Türen/Befehl)
- LED-Test beim Start (Sequenz)
- Keine externen Bibliotheken erforderlich

### Benötigte Hardware
| Anz. | Bauteil | Hinweise |
|------|---------|----------|
| 1 | Arduino Leonardo (ATmega32U4) | **Muss** ein Leonardo sein (nativer USB) |
| 1 | MAX7219-Modul (WCMCU DISY1) | SPI-LED-Treiber |
| 13 | 5mm LEDs | 1 weiß/gelb, 5 gelb, 4 blau, 3 rot |
| — | Kabel, Breadboard oder Platine | — |

### Verwendete Pins
```
A3 = MAX7219_DIN
A4 = MAX7219_CLK
A5 = MAX7219_CS   (LOAD)
```
Alle anderen Pins (0-13, A0-A2) sind **frei**.

### Hochladen
1. Öffne `ArduinoSerialOnly/ArduinoSerialOnly.ino` in der Arduino IDE
2. Wähle **Board → Arduino Leonardo**
3. Wähle den richtigen COM-Port
4. Klicke **Upload**

---

## ArduinoJoystick — LED + Controller (Vollversion)

**Ordner**: `ArduinoJoystick/`

Die Vollversion: neben den 13 LEDs enthält sie einen USB-HID-Joystick mit 3 analogen Schiebereglern, Drehencoder, 8 Momentschaltern, 2 selbstarretierenden Kippschaltern, 2 Drehschaltern und Taster/Fußpedal.

### Funktionen
- Alles was ArduinoSerialOnly kann **+**
- USB-HID-Joystick mit 28 Tasten und 4 Achsen
- 3 × 100mm Schiebepotentiometer (X-, Y-, Z-Achse)
- 1 Drehencoder mit Taster (Rx-Achse)
- 5×6-Tastenmatrix (Schalter, Kippschalter, Drehschalter)
- Erscheint als Joystick in Windows

### Benötigte Hardware
| Anz. | Bauteil | Hinweise |
|------|---------|----------|
| 1 | Arduino Leonardo (ATmega32U4) | **Muss** ein Leonardo sein |
| 3 | 100mm Schiebepotentiometer B10K | X-, Y-, Z-Achse |
| 3 | 100nF Keramikkondensator (104) | Rauschfilter für Slider |
| 1 | Drehencoder EC11 mit Taster | CLK, DT, SW |
| 8 | Momentschalter ON-OFF-ON | SW1–SW8, federn in Mittelstellung zurück |
| 2 | Selbstarretierende Schalter ON-OFF-ON | TOGGLE1–2, halten die Position |
| 1 | 4-Positionen-Drehschalter | ROT4 (kein OFF) |
| 1 | 3-Positionen-Drehschalter | ROT3 (OFF + 2) |
| 1 | Momenttaster | BTN1 |
| 1 | Fußschalter (Pedal) | Parallel zu BTN1 |
| ~25 | Diode 1N4148 DO-35 | Anti-Ghosting für Matrix |
| 13 | 5mm LEDs | 1 weiß/gelb, 5 gelb, 4 blau, 3 rot |
| 1 | MAX7219-Modul (WCMCU DISY1) | LED-Treiber (DIN/CLK/CS) |
| — | Kabel, Breadboard oder Platine | — |

### Benötigte Bibliotheken
- **Joystick** (Matthew Heironimus) — von [GitHub](https://github.com/MHeironimus/ArduinoJoystickLibrary)
- **Encoder** (Paul Stoffregen) — über den Arduino Library Manager

### Hochladen
1. Installiere die Bibliotheken Joystick und Encoder
2. Öffne `ArduinoJoystick/ArduinoJoystick.ino` in der Arduino IDE
3. Wähle **Board → Arduino Leonardo**
4. Wähle den richtigen COM-Port
5. Klicke **Upload**

---

## 13 LEDs des MFA-Panels

Beide Versionen verwenden das **gleiche MAX7219-Modul** zum Ansteuern aller 13 LEDs:

| # | LED | Farbe | MAX7219 | Funktion |
|---|-----|-------|---------|----------|
| 1 | SIFA | weiß/gelb | DIG0.A | Sicherheitsfahrschaltung |
| 2 | LZB | gelb | DIG0.B | Linienzugbeeinflussung Ende |
| 3 | PZB 70 | blau | DIG0.C | PZB Zugart M (70 km/h) |
| 4 | PZB 85 | blau | DIG0.D | PZB Zugart O (85 km/h) |
| 5 | PZB 55 | blau | DIG0.E | PZB Zugart U (55 km/h) |
| 6 | 500Hz | rot | DIG0.F | PZB 500 Hz |
| 7 | 1000Hz | gelb | DIG0.G | PZB 1000 Hz |
| 8 | Türen L | gelb | DIG0.DP | Türen links |
| 9 | Türen R | gelb | DIG1.A | Türen rechts |
| 10 | LZB Ü | blau | DIG1.B | LZB Überwachung |
| 11 | LZB G | rot | DIG1.C | LZB Geführt |
| 12 | LZB S | rot | DIG1.D | LZB Schnellbremsung |
| 13 | Befehl 40 | gelb | DIG1.E | Befehl 40 km/h |

**LEDs gesamt**: 1 weiß/gelb, 5 gelb, 4 blau, 3 rot
**Verbindung**: Arduino A3 (DIN), A4 (CLK), A5 (CS) → MAX7219-Modul

---

## Serielles Protokoll (gemeinsam für beide Versionen)

Baudrate: **115200**, Terminator: `\n`

| Befehl | Wirkung |
|--------|---------|
| `SIFA:1` / `SIFA:0` | LED1 ein/aus |
| `LZB:1` / `LZB:0` | LED2 ein/aus |
| `PZB70:1` / `PZB70:0` | LED3 ein/aus |
| `PZB80:1` / `PZB80:0` | LED4 ein/aus |
| `PZB50:1` / `PZB50:0` | LED5 ein/aus |
| `500HZ:1` / `500HZ:0` | LED6 ein/aus |
| `1000HZ:1` / `1000HZ:0` | LED7 ein/aus |
| `TUEREN_L:1` / `TUEREN_L:0` | LED8 ein/aus |
| `TUEREN_R:1` / `TUEREN_R:0` | LED9 ein/aus |
| `LZB_UE:1` / `LZB_UE:0` | LED10 ein/aus |
| `LZB_G:1` / `LZB_G:0` | LED11 ein/aus |
| `LZB_S:1` / `LZB_S:0` | LED12 ein/aus |
| `BEF40:1` / `BEF40:0` | LED13 ein/aus |
| `LED:n:1` / `LED:n:0` | LED n ein/aus (1-13) |
| `OFF` | Alle LEDs aus |

---

## MAX7219-LED-Schaltplan (3 SPI-Pins)

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
                               │    DP → LED8  (Türen L) │
                               │                         │
                               │  DIG1:                  │
                               │    A  → LED9  (Türen R) │
                               │    B  → LED10 (LZB Ü)   │
                               │    C  → LED11 (LZB G)   │
                               │    D  → LED12 (LZB S)   │
                               │    E  → LED13 (BEF40)   │
                               └─────────────────────────┘
```

Jede LED: ANODE (+) an SEG_x Pin, KATHODE (-) an DIG_x Pin.
Keine einzelnen Widerstände nötig (RSET bereits auf dem Modul).
Alle 3 MAX7219-Pins befinden sich auf dem Analog-Header, nebeneinander.
