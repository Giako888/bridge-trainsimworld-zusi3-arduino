# Arduino Firmware — Two Versions

Two **versions** of the Arduino firmware are available for the MFA panel.
Both are **100% compatible** with Train Simulator Bridge (same serial protocol).

---

## Which one to choose?

| | **ArduinoSerialOnly** | **ArduinoJoystick** |
|---|---|---|
| **Purpose** | LED panel only (MFA) | LED panel + full joystick controller |
| **Components** | ~16 (Arduino + MAX7219 + 13 LEDs) | ~70+ (MAX7219 + LEDs + sliders + encoder + switches + diodes) |
| **Pins used** | 3 (A3, A4, A5) for MAX7219 | All (20 pins) |
| **Libraries** | None | Joystick + Encoder |
| **Difficulty** | ⭐ Easy | ⭐⭐⭐ Advanced |
| **Ideal for** | Those who only want the physical MFA indicators | Those who also want a physical train controller |

---

## ArduinoSerialOnly — LED Only (simple version)

**Folder**: `ArduinoSerialOnly/`

The minimalist version: receives serial commands from Train Simulator Bridge and drives 13 physical LEDs via MAX7219 module (3 SPI pins).

### What it does
- Receives commands via USB Serial (115200 baud)
- Controls 13 MFA LEDs (PZB/SIFA/LZB/Doors/Befehl)
- LED test on startup (sequence)
- No external libraries required

### Required hardware
| Qty | Component | Notes |
|-----|-----------|-------|
| 1 | Arduino Leonardo (ATmega32U4) | **Must** be a Leonardo (native USB) |
| 1 | MAX7219 Module (WCMCU DISY1) | SPI LED driver |
| 13 | 5mm LEDs | 1 white/yellow, 5 yellow, 4 blue, 3 red |
| — | Wires, breadboard or PCB | — |

### Pins used
```
A3 = MAX7219_DIN
A4 = MAX7219_CLK
A5 = MAX7219_CS   (LOAD)
```
All other pins (0-13, A0-A2) are **free**.

### How to upload
1. Open `ArduinoSerialOnly/ArduinoSerialOnly.ino` in Arduino IDE
2. Select **Board → Arduino Leonardo**
3. Select the correct COM port
4. Click **Upload**

---

## ArduinoJoystick — LED + Controller (full version)

**Folder**: `ArduinoJoystick/`

The full version: in addition to the 13 LEDs, includes a USB HID joystick with 3 analog sliders, rotary encoder, 8 momentary switches, 2 self-lock toggles, 2 rotary switches, and a button/pedal.

### What it does
- Everything ArduinoSerialOnly does **+**
- USB HID joystick with 28 buttons and 4 axes
- 3 × 100mm slider potentiometers (X, Y, Z axes)
- 1 rotary encoder with click (Rx axis)
- 5×6 button matrix (switches, toggles, rotary)
- Appears as a joystick in Windows

### Required hardware
| Qty | Component | Notes |
|-----|-----------|-------|
| 1 | Arduino Leonardo (ATmega32U4) | **Must** be a Leonardo |
| 3 | 100mm slider potentiometer B10K | X, Y, Z axes |
| 3 | 100nF ceramic capacitor (104) | Slider noise filter |
| 1 | EC11 rotary encoder with pushbutton | CLK, DT, SW |
| 8 | Momentary ON-OFF-ON switch | SW1–SW8, spring return to center |
| 2 | Self-lock ON-OFF-ON switch | TOGGLE1–2, maintain position |
| 1 | 4-position rotary switch | ROT4 (no OFF) |
| 1 | 3-position rotary switch | ROT3 (OFF + 2) |
| 1 | Momentary pushbutton | BTN1 |
| 1 | Foot switch (pedal) | In parallel with BTN1 |
| ~25 | 1N4148 DO-35 diode | Matrix anti-ghosting |
| 13 | 5mm LEDs | 1 white/yellow, 5 yellow, 4 blue, 3 red |
| 1 | MAX7219 module (WCMCU DISY1) | LED driver (DIN/CLK/CS) |
| — | Wires, breadboard or PCB | — |

### Required libraries
- **Joystick** (Matthew Heironimus) — from [GitHub](https://github.com/MHeironimus/ArduinoJoystickLibrary)
- **Encoder** (Paul Stoffregen) — from Arduino Library Manager

### How to upload
1. Install the Joystick and Encoder libraries
2. Open `ArduinoJoystick/ArduinoJoystick.ino` in Arduino IDE
3. Select **Board → Arduino Leonardo**
4. Select the correct COM port
5. Click **Upload**

---

## 13 LEDs of the MFA panel

Both versions use the **same MAX7219 module** to drive all 13 LEDs:

| # | LED | Color | MAX7219 | Function |
|---|-----|-------|---------|----------|
| 1 | SIFA | white/yellow | DIG0.A | Sicherheitsfahrschaltung (vigilance) |
| 2 | LZB | yellow | DIG0.B | Linienzugbeeinflussung Ende |
| 3 | PZB 70 | blue | DIG0.C | PZB Zugart M (70 km/h) |
| 4 | PZB 85 | blue | DIG0.D | PZB Zugart O (85 km/h) |
| 5 | PZB 55 | blue | DIG0.E | PZB Zugart U (55 km/h) |
| 6 | 500Hz | red | DIG0.F | PZB 500 Hz |
| 7 | 1000Hz | yellow | DIG0.G | PZB 1000 Hz |
| 8 | Türen L | yellow | DIG0.DP | Doors left |
| 9 | Türen R | yellow | DIG1.A | Doors right |
| 10 | LZB Ü | blue | DIG1.B | LZB Überwachung (supervision) |
| 11 | LZB G | red | DIG1.C | LZB Geführt (active) |
| 12 | LZB S | red | DIG1.D | LZB Schnellbremsung (emergency braking) |
| 13 | Befehl 40 | yellow | DIG1.E | Befehl 40 km/h |

**Total LEDs**: 1 white/yellow, 5 yellow, 4 blue, 3 red
**Connection**: Arduino A3 (DIN), A4 (CLK), A5 (CS) → MAX7219 module

---

## Serial protocol (common to both versions)

Baud rate: **115200**, terminator: `\n`

| Command | Effect |
|---------|--------|
| `SIFA:1` / `SIFA:0` | Turn on/off LED1 |
| `LZB:1` / `LZB:0` | Turn on/off LED2 |
| `PZB70:1` / `PZB70:0` | Turn on/off LED3 |
| `PZB80:1` / `PZB80:0` | Turn on/off LED4 |
| `PZB50:1` / `PZB50:0` | Turn on/off LED5 |
| `500HZ:1` / `500HZ:0` | Turn on/off LED6 |
| `1000HZ:1` / `1000HZ:0` | Turn on/off LED7 |
| `TUEREN_L:1` / `TUEREN_L:0` | Turn on/off LED8 |
| `TUEREN_R:1` / `TUEREN_R:0` | Turn on/off LED9 |
| `LZB_UE:1` / `LZB_UE:0` | Turn on/off LED10 |
| `LZB_G:1` / `LZB_G:0` | Turn on/off LED11 |
| `LZB_S:1` / `LZB_S:0` | Turn on/off LED12 |
| `BEF40:1` / `BEF40:0` | Turn on/off LED13 |
| `LED:n:1` / `LED:n:0` | Turn on/off LED n (1-13) |
| `OFF` | Turn off all LEDs |

---

## MAX7219 LED Wiring Diagram (3 SPI pins)

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
                               │    DP → LED8  (Doors L) │
                               │                         │
                               │  DIG1:                  │
                               │    A  → LED9  (Doors R) │
                               │    B  → LED10 (LZB Ü)   │
                               │    C  → LED11 (LZB G)   │
                               │    D  → LED12 (LZB S)   │
                               │    E  → LED13 (BEF40)   │
                               └─────────────────────────┘
```

Each LED: ANODE (+) to SEG_x pin, CATHODE (-) to DIG_x pin.
No individual resistors needed (RSET already on the module).
All 3 MAX7219 pins are on the analog header, adjacent.
