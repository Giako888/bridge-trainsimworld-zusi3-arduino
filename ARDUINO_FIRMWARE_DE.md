# Arduino-Firmware — Zwei Versionen

Es stehen **zwei Versionen** der Arduino-Firmware für das MFA-Panel zur Verfügung.
Beide sind **100 % kompatibel** mit Train Simulator Bridge (gleiches serielles Protokoll).

---

## Welche Version wählen?

| | **ArduinoSerialOnly** | **ArduinoJoystick** |
|---|---|---|
| **Zweck** | Nur LED-Panel (MFA) | LED-Panel + vollständiger Joystick-Controller |
| **Bauteile** | ~16 (Arduino + 13 LEDs + 13 Widerstände) | ~70+ (LEDs + Slider + Encoder + Schalter + Dioden) |
| **Verwendete Pins** | 5 (A3, 0, 1, A4, 14/MISO) | Alle (20 Pins) + Pin 14 (ICSP) |
| **Bibliotheken** | Keine | Joystick + Encoder |
| **Schwierigkeit** | ⭐ Einfach | ⭐⭐⭐ Fortgeschritten |
| **Ideal für** | Wer nur die physischen MFA-Anzeigen möchte | Wer auch einen physischen Zug-Controller möchte |

---

## ArduinoSerialOnly — Nur LEDs (einfache Version)

**Ordner**: `ArduinoSerialOnly/`

Die minimalistische Version: empfängt serielle Befehle von Train Simulator Bridge und steuert 13 physische LEDs über Charlieplexing an 5 Pins.

### Funktionen
- Empfängt Befehle über USB-Seriell (115200 Baud)
- Steuert 13 MFA-LEDs (PZB/SIFA/LZB/Türen/Befehl)
- LED-Test beim Start (Sequenz)
- Keine externen Bibliotheken erforderlich

### Benötigte Hardware
| Anz. | Bauteil | Hinweise |
|------|---------|----------|
| 1 | Arduino Leonardo (ATmega32U4) | **Muss** ein Leonardo sein (nativer USB) |
| 13 | 5mm LEDs | 1 weiß/gelb, 5 gelb, 4 blau, 3 rot |
| 13 | 220Ω Widerstand | Einer pro LED |
| — | Kabel, Breadboard oder Platine | — |

### Verwendete Pins
```
A3 = LED_A     (Charlieplexing)
 0 = LED_B     (RX-Pin, aber Serial läuft über USB!)
 1 = LED_C     (TX-Pin, aber Serial läuft über USB!)
A4 = LED_D     (Charlieplexing)
14 = LED_E     (MISO, ICSP-Header — 1 Draht anlöten)
```
Pin 14 (MISO) befindet sich auf dem ICSP-Header (6-Pin-Header in der Mitte der Platine).
Alle anderen Pins sind **frei**.

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
| 13 | 220Ω Widerstand | Einer pro LED |
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

Beide Versionen verwenden die **gleiche Charlieplexing-LED-Verdrahtung** an 5 Pins:

| # | LED | Farbe | Richtung | Funktion |
|---|-----|-------|----------|----------|
| 1 | SIFA | weiß/gelb | A3 → 0 | Sicherheitsfahrschaltung |
| 2 | LZB | gelb | 0 → A3 | Linienzugbeeinflussung Ende |
| 3 | PZB 70 | blau | A3 → 1 | PZB Zugart M (70 km/h) |
| 4 | PZB 85 | blau | 1 → A3 | PZB Zugart O (85 km/h) |
| 5 | PZB 55 | blau | 0 → 1 | PZB Zugart U (55 km/h) |
| 6 | 500Hz | rot | 1 → 0 | PZB 500 Hz |
| 7 | 1000Hz | gelb | A3 → A4 | PZB 1000 Hz |
| 8 | Türen L | gelb | A4 → A3 | Türen links |
| 9 | Türen R | gelb | 0 → A4 | Türen rechts |
| 10 | LZB Ü | blau | 1 → A4 | LZB Überwachung |
| 11 | LZB G | rot | A4 → 0 | LZB Geführt |
| 12 | LZB S | rot | A4 → 1 | LZB Schnellbremsung |
| 13 | Befehl 40 | gelb | A3 → 14 | Befehl 40 km/h |

**LEDs gesamt**: 1 weiß/gelb, 5 gelb, 4 blau, 3 rot
**Pin 14** (MISO) befindet sich auf dem ICSP-Header, erfordert 1 angelöteten Draht.

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

## Charlieplexing-LED-Schaltplan (5 Pins)

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

Jede LED hat den 220Ω-Widerstand auf der ANODEN-Seite (langes Bein).
Die Kathode (kurzes Bein) geht direkt zum anderen Pin.
**Pin 14 (MISO)** befindet sich auf dem ICSP-Header — 1 Draht anlöten.
