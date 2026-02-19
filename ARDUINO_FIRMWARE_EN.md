# Arduino Firmware — Two Versions

Two **versions** of the Arduino firmware are available for the MFA panel.
Both are **100% compatible** with Train Simulator Bridge (same serial protocol).

---

## Which one to choose?

| | **ArduinoSerialOnly** | **ArduinoJoystick** |
|---|---|---|
| **Purpose** | LED panel only (MFA) | LED panel + full joystick controller |
| **Components** | ~16 (Arduino + 13 LEDs + 13 resistors) | ~70+ (LEDs + sliders + encoder + switches + diodes) |
| **Pins used** | 5 (A3, 0, 1, A4, 14/MISO) | All (20 pins) + pin 14 (ICSP) |
| **Libraries** | None | Joystick + Encoder |
| **Difficulty** | ⭐ Easy | ⭐⭐⭐ Advanced |
| **Ideal for** | Those who only want the physical MFA indicators | Those who also want a physical train controller |

---

## ArduinoSerialOnly — LED Only (simple version)

**Folder**: `ArduinoSerialOnly/`

The minimalist version: receives serial commands from Train Simulator Bridge and drives 13 physical LEDs via Charlieplexing on 5 pins.

### What it does
- Receives commands via USB Serial (115200 baud)
- Controls 13 MFA LEDs (PZB/SIFA/LZB/Doors/Befehl)
- LED test on startup (sequence)
- No external libraries required

### Required hardware
| Qty | Component | Notes |
|-----|-----------|-------|
| 1 | Arduino Leonardo (ATmega32U4) | **Must** be a Leonardo (native USB) |
| 13 | 5mm LEDs | 1 white/yellow, 5 yellow, 4 blue, 3 red |
| 13 | 220Ω resistor | One per LED |
| — | Wires, breadboard or PCB | — |

### Pins used
```
A3 = LED_A     (Charlieplexing)
 0 = LED_B     (RX pin, but Serial is via USB!)
 1 = LED_C     (TX pin, but Serial is via USB!)
A4 = LED_D     (Charlieplexing)
14 = LED_E     (MISO, ICSP header — solder 1 wire)
```
Pin 14 (MISO) is located on the ICSP header (6-pin header in the center of the board).
All other pins are **free**.

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
| 13 | 220Ω resistor | One per LED |
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

Both versions use the **same Charlieplexing LED wiring** on 5 pins:

| # | LED | Color | Direction | Function |
|---|-----|-------|-----------|----------|
| 1 | SIFA | white/yellow | A3 → 0 | Sicherheitsfahrschaltung (vigilance) |
| 2 | LZB | yellow | 0 → A3 | Linienzugbeeinflussung Ende |
| 3 | PZB 70 | blue | A3 → 1 | PZB Zugart M (70 km/h) |
| 4 | PZB 85 | blue | 1 → A3 | PZB Zugart O (85 km/h) |
| 5 | PZB 55 | blue | 0 → 1 | PZB Zugart U (55 km/h) |
| 6 | 500Hz | red | 1 → 0 | PZB 500 Hz |
| 7 | 1000Hz | yellow | A3 → A4 | PZB 1000 Hz |
| 8 | Türen L | yellow | A4 → A3 | Doors left |
| 9 | Türen R | yellow | 0 → A4 | Doors right |
| 10 | LZB Ü | blue | 1 → A4 | LZB Überwachung (supervision) |
| 11 | LZB G | red | A4 → 0 | LZB Geführt (active) |
| 12 | LZB S | red | A4 → 1 | LZB Schnellbremsung (emergency braking) |
| 13 | Befehl 40 | yellow | A3 → 14 | Befehl 40 km/h |

**Total LEDs**: 1 white/yellow, 5 yellow, 4 blue, 3 red
**Pin 14** (MISO) is on the ICSP header, requires 1 soldered wire.

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

## Charlieplexing LED Wiring Diagram (5 pins)

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

Each LED has a 220Ω resistor on the ANODE side (long leg).
The cathode (short leg) goes directly to the other pin.
**Pin 14 (MISO)** is on the ICSP header — solder 1 wire.
