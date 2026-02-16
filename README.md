# 🚂 Train Simulator Bridge

🇬🇧 **English** | [🇮🇹 Italiano](README.it.md) | [🇩🇪 Deutsch](README.de.md)

**Physical replica of the MFA indicator panel** from German trains (PZB / SIFA / LZB) using an Arduino Leonardo with 12 Charlieplexing LEDs, driven in real-time by **Train Sim World 6** or **Zusi 3**.

![Python](https://img.shields.io/badge/Python-3.13-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6)
![License](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey)

---

## Overview

```
┌──────────────┐    HTTP / TCP    ┌──────────────────┐    Serial    ┌─────────────────┐
│  Train Sim   │ ──────────────> │  Train Simulator │ ──────────> │  Arduino        │
│  World 6     │   port 31270    │  Bridge (Python) │  115200 bd  │  Leonardo       │
│  or          │   port 1436     │                  │             │  12 LEDs (MFA)  │
│  Zusi 3      │                 │  Tkinter GUI     │             │  Charlieplexing │
└──────────────┘                 └──────────────────┘             └─────────────────┘
```

The application reads real-time data from a train simulator and controls 12 physical LEDs that replicate the **MFA** (Multifunktionale Anzeige) panel found in German locomotive cabs.

## Features

- **Dual simulator support**: TSW6 (HTTP API) and Zusi 3 (TCP binary protocol)
- **TSW6**: 4 train profiles with custom endpoint mappings (DB BR 101, Vectron, Bpmmbdzf, BR 146.2)
- **Zusi 3**: works with most trains — LED data comes via generic TCP protocol
- **Auto-detect** (TSW6): automatically identifies the active locomotive and loads the correct LED profile
- **12 physical LEDs**: PZB (55/70/85, 500Hz, 1000Hz), SIFA, LZB (Ende, Ü, G, S), Doors (L/R)
- **Realistic LED behavior**: priority-based logic with steady ON, variable-speed BLINK, PZB 70↔85 Wechselblinken
- **Modern GUI**: dark theme interface with real-time LED preview
- **Standalone EXE**: build with PyInstaller, no Python installation required

## MFA Panel — 12 LEDs

| # | LED | Function |
|---|-----|----------|
| 1 | **SIFA** | Sicherheitsfahrschaltung (dead man's switch) |
| 2 | **LZB** | Linienzugbeeinflussung Ende |
| 3 | **PZB 70** | PZB mode M (70 km/h) |
| 4 | **PZB 85** | PZB mode O (85 km/h) |
| 5 | **PZB 55** | PZB mode U (55 km/h) |
| 6 | **500 Hz** | PZB 500 Hz frequency |
| 7 | **1000 Hz** | PZB 1000 Hz frequency |
| 8 | **Türen L** | Left doors unlocked |
| 9 | **Türen R** | Right doors unlocked |
| 10 | **LZB Ü** | LZB supervision |
| 11 | **LZB G** | LZB active |
| 12 | **LZB S** | LZB forced braking |

## Requirements

### Software
- **Python 3.13+** (or use the prebuilt EXE)
- **Windows 10/11**
- **Train Sim World 6** with External Interface API enabled, or **Zusi 3**

### Hardware
- **Arduino Leonardo** (ATmega32U4)
- 12 LEDs in **Charlieplexing** configuration on 4 pins
- See [Arduino Firmware](#arduino-firmware) for two firmware options

## Installation

### From source

```bash
git clone https://github.com/Giako888/bridge-trainsim-arduino.git
cd bridge-trainsim-arduino
pip install -r requirements.txt
python tsw6_arduino_gui.py
```

### Build EXE

```bash
python -m PyInstaller TSW6_Arduino_Bridge.spec --noconfirm
# Output: dist/TrainSimBridge.exe
```

## TSW6 Setup

1. Launch **Train Sim World 6**
2. The API key is read automatically from:
   ```
   %USERPROFILE%\Documents\My Games\TrainSimWorld6\Saved\Config\CommAPIKey.txt
   ```
3. In Train Simulator Bridge, select **TSW6** and click **Connect**
4. The train is detected automatically and the LED profile loads

## Zusi 3 Setup

1. Launch **Zusi 3** with the TCP interface active (port 1436)
2. In Train Simulator Bridge, select **Zusi3** and click **Connect**
3. LED data is received via generic TCP protocol — **works with most trains**, no per-train profiles needed

## Supported Trains

### TSW6 — Specific profiles required

Each TSW6 train needs a dedicated profile with custom API endpoint mappings. Only the following trains are currently supported:

| Train | PZB | LZB | SIFA | Notes |
|-------|-----|-----|------|-------|
| **DB BR 101** | PZB_V3 | LZB | BP_Sifa_Service | Full MFA panel |
| **Siemens Vectron** | PZB_Service_V3 | LZB_Service | BP_Sifa_Service | No MFA |
| **Bpmmbdzf** | — | — | — | Cab car (same endpoints as BR101) |
| **DB BR 146.2** | PZB_Service_V2 | LZB_Service | SIFA | 26 mappings, realistic PZB 90 |

> More TSW6 trains will be added in future versions. — Most trains supported

Zusi 3 provides cab instrumentation data via a generic TCP protocol (Fahrpult message). The LED panel works with **most trains** that expose PZB/SIFA/LZB data — no per-train profiles needed.

## Arduino Firmware

Two firmware versions are available, both **100% compatible** with Train Simulator Bridge (same serial protocol):

| | **ArduinoSerialOnly** | **ArduinoJoystick** |
|---|---|---|
| Purpose | LED panel only (MFA) | LED panel + full joystick controller |
| Components | ~15 (Arduino + 12 LEDs + 12 resistors) | 70+ (LEDs + sliders + encoder + switches + diodes) |
| Pins used | 4 (A3, 0, 1, A4) | All 20 pins |
| Libraries | None | Joystick + Encoder |
| Difficulty | Easy | Advanced |

See [ARDUINO_FIRMWARE.md](ARDUINO_FIRMWARE.md) for full details, wiring guide, and component list.

## Project Structure

```
├── tsw6_arduino_gui.py        # Main GUI (Tkinter)
├── tsw6_api.py                # TSW6 HTTP API client
├── config_models.py           # Data models, profiles, conditions
├── arduino_bridge.py          # Arduino serial communication
├── zusi3_client.py            # Zusi 3 TCP client
├── zusi3_protocol.py          # Zusi 3 binary protocol parser
├── TSW6_Arduino_Bridge.spec   # PyInstaller spec file
├── requirements.txt           # Python dependencies
├── ARDUINO_FIRMWARE.md        # Arduino firmware guide (both versions)
├── ArduinoSerialOnly/         # Firmware: serial LED only (simple)
│   ├── ArduinoSerialOnly.ino
│   └── WIRING.h
├── ArduinoJoystick/           # Firmware: LED + joystick (full)
│   ├── ArduinoJoystick.ino
│   └── WIRING.h
├── tsw6_bridge.ico            # Application icon
└── COPILOT_CONTEXT.md         # Full context for GitHub Copilot
```

## LED Priority Logic

Each LED can have multiple mappings with a **numeric priority**. The highest-priority mapping with a satisfied condition wins:

| Priority | Effect | Example |
|----------|--------|---------|
| 0 | Steady ON | Active PZB mode |
| 1 | BLINK 1.0s | Frequency monitoring |
| 3 | BLINK 1.0s | Restricted mode (Wechselblinken) |
| 4 | BLINK 0.5s | Overspeed |
| 5 | BLINK 0.3s | Emergency |

### Wechselblinken (PZB 90)

In **restriktiv** mode, PZB 70 and PZB 85 LEDs alternate in anti-phase (*Wechselblinken*), exactly like the real PZB 90 system:

> *"Wird eine 1000- oder 500-Hz-Beeinflussung restriktiv, so wird dies durch Wechselblinken der Zugart-Leuchtmelder 70 und 85 angezeigt."*
> — Wikipedia DE, Punktförmige Zugbeeinflussung

## License

This work is licensed under a [Creative Commons Attribution-NonCommercial 4.0 International License](https://creativecommons.org/licenses/by-nc/4.0/).

You are free to share and adapt this work for non-commercial purposes, with appropriate credit. See [LICENSE](LICENSE) for details.
