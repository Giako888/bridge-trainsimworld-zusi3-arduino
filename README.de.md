# 🚂 Train Simulator Bridge

[🇬🇧 English](README.md) | [🇮🇹 Italiano](README.it.md) | 🇩🇪 **Deutsch**

**Physische Nachbildung der MFA-Anzeige** eines deutschen Zuges (PZB / SIFA / LZB) mit einem Arduino Leonardo und 12 Charlieplexing-LEDs, gesteuert in Echtzeit durch **Train Sim World 6** oder **Zusi 3**.

![Python](https://img.shields.io/badge/Python-3.13-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6)
![License](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey)
[![Release](https://img.shields.io/github/v/release/Giako888/bridge-trainsimworld-zusi3-arduino)](https://github.com/Giako888/bridge-trainsimworld-zusi3-arduino/releases/latest)
[![Download EXE](https://img.shields.io/badge/Download-TrainSimBridge.exe-brightgreen)](https://github.com/Giako888/bridge-trainsimworld-zusi3-arduino/releases/latest)

---

## Übersicht

```
┌──────────────┐    HTTP / TCP    ┌──────────────────┐    Seriell   ┌─────────────────┐
│  Train Sim   │ ──────────────> │  Train Simulator │ ──────────> │  Arduino        │
│  World 6     │   Port 31270    │  Bridge (Python) │  115200 Bd  │  Leonardo       │
│  oder        │   Port 1436     │                  │             │  12 LEDs (MFA)  │
│  Zusi 3      │                 │  Tkinter-GUI     │             │  Charlieplexing │
└──────────────┘                 └──────────────────┘             └─────────────────┘
```

Die Anwendung liest Echtzeitdaten aus einem Zugsimulator und steuert 12 physische LEDs, die die **MFA** (Multifunktionale Anzeige) im Führerstand deutscher Lokomotiven nachbilden.

## Funktionen

- **Zwei Simulatoren**: Unterstützung für TSW6 (HTTP-API) und Zusi 3 (binäres TCP-Protokoll)
- **TSW6**: 4 Zugprofile mit spezifischen Endpunkt-Zuordnungen (DB BR 101, Vectron, Bpmmbdzf, BR 146.2)
- **Zusi 3**: funktioniert mit den meisten Zügen — LED-Daten kommen über generisches TCP-Protokoll
- **SimRail** (geplant): Unterstützung wird hinzugefügt, sobald offizielle I/O-APIs für die Führerstand-Instrumentierung veröffentlicht werden
- **Automatische Erkennung** (TSW6): erkennt die aktive Lokomotive und lädt das passende LED-Profil
- **12 physische LEDs**: PZB (55/70/85, 500Hz, 1000Hz), SIFA, LZB (Ende, Ü, G, S), Türen (L/R)
- **Realistische LED-Steuerung**: Prioritätslogik mit Dauerlicht, variablem Blinken, PZB 70↔85 Wechselblinken
- **Mehrsprachige GUI**: Italienisch, Englisch, Deutsch — erkennt die Systemsprache automatisch, umschaltbar mit Flaggen-Icons
- **Moderne GUI**: Dark-Theme-Oberfläche mit Echtzeit-LED-Vorschau
- **Standalone-EXE**: mit PyInstaller erstellbar, keine Python-Installation erforderlich

## MFA-Anzeige — 12 LEDs

| # | LED | Funktion |
|---|-----|----------|
| 1 | **SIFA** | Sicherheitsfahrschaltung |
| 2 | **LZB** | Linienzugbeeinflussung Ende |
| 3 | **PZB 70** | PZB Zugart M (70 km/h) |
| 4 | **PZB 85** | PZB Zugart O (85 km/h) |
| 5 | **PZB 55** | PZB Zugart U (55 km/h) |
| 6 | **500 Hz** | PZB 500-Hz-Beeinflussung |
| 7 | **1000 Hz** | PZB 1000-Hz-Beeinflussung |
| 8 | **Türen L** | Türen links entriegelt |
| 9 | **Türen R** | Türen rechts entriegelt |
| 10 | **LZB Ü** | LZB Überwachung |
| 11 | **LZB G** | LZB aktiv (Geführt) |
| 12 | **LZB S** | LZB Zwangsbremsung |

## Voraussetzungen

### Software
- **Python 3.13+** (oder die vorkompilierte EXE verwenden)
- **Windows 10/11**
- **Train Sim World 6** mit aktivierter External Interface API, oder **Zusi 3**

### Hardware
- **Arduino Leonardo** (ATmega32U4)
- 12 LEDs in **Charlieplexing**-Konfiguration an 4 Pins
- Siehe [Arduino-Firmware](#arduino-firmware) für zwei Firmware-Optionen

## Installation

### Aus Quellcode

```bash
git clone https://github.com/Giako888/bridge-trainsim-arduino.git
cd bridge-trainsim-arduino
pip install -r requirements.txt
python tsw6_arduino_gui.py
```

### EXE erstellen

```bash
python -m PyInstaller TSW6_Arduino_Bridge.spec --noconfirm
# Ausgabe: dist/TrainSimBridge.exe
```

## TSW6 einrichten

1. **Train Sim World 6** starten
2. Der API-Schlüssel wird automatisch gelesen aus:
   ```
   %USERPROFILE%\Documents\My Games\TrainSimWorld6\Saved\Config\CommAPIKey.txt
   ```
3. In Train Simulator Bridge **TSW6** auswählen und **Verbinden** klicken
4. Der Zug wird automatisch erkannt und das LED-Profil geladen

## Zusi 3 einrichten

1. **Zusi 3** mit aktivierter TCP-Schnittstelle starten (Port 1436)
2. In Train Simulator Bridge **Zusi3** auswählen und **Verbinden** klicken
3. LED-Daten werden über ein generisches TCP-Protokoll empfangen — **funktioniert mit den meisten Zügen**, keine zugspezifischen Profile nötig

## Unterstützte Züge

### TSW6 — Spezifische Profile erforderlich

Jeder TSW6-Zug benötigt ein eigenes Profil mit individuellen API-Endpunkt-Zuordnungen. Derzeit werden nur folgende Züge unterstützt:

| Zug | PZB | LZB | SIFA | Hinweise |
|-----|-----|-----|------|----------|
| **DB BR 101** | PZB_V3 | LZB | BP_Sifa_Service | Vollständige MFA-Anzeige |
| **Siemens Vectron** | PZB_Service_V3 | LZB_Service | BP_Sifa_Service | Ohne MFA |
| **Bpmmbdzf** | — | — | — | Steuerwagen (gleiche Endpunkte wie BR101) |
| **DB BR 146.2** | PZB_Service_V2 | LZB_Service | SIFA | 26 Zuordnungen, realistisches PZB 90 |

> Weitere TSW6-Züge werden in zukünftigen Versionen hinzugefügt. — Die meisten Züge werden unterstützt

Zusi 3 liefert Führerstand-Instrumentendaten über ein generisches TCP-Protokoll (Fahrpult-Nachricht). Die LED-Anzeige funktioniert mit **den meisten Zügen**, die PZB-/SIFA-/LZB-Daten bereitstellen — ohne zugspezifische Profile.

## Arduino-Firmware

Zwei Firmware-Versionen stehen zur Verfügung, beide **100% kompatibel** mit Train Simulator Bridge (gleiches serielles Protokoll):

| | **ArduinoSerialOnly** | **ArduinoJoystick** |
|---|---|---|
| Zweck | Nur LED-Anzeige (MFA) | LED-Anzeige + vollständiger Joystick-Controller |
| Bauteile | ~15 (Arduino + 12 LEDs + 12 Widerstände) | 70+ (LEDs + Schieber + Encoder + Schalter + Dioden) |
| Verwendete Pins | 4 (A3, 0, 1, A4) | Alle 20 Pins |
| Bibliotheken | Keine | Joystick + Encoder |
| Schwierigkeit | Einfach | Fortgeschritten |

Siehe [ARDUINO_FIRMWARE.md](ARDUINO_FIRMWARE.md) für vollständige Details, Verkabelungsanleitung und Bauteil-Liste.

## Projektstruktur

```
├── tsw6_arduino_gui.py        # Haupt-GUI (Tkinter)
├── i18n.py                    # Übersetzungen (IT/EN/DE)
├── tsw6_api.py                # TSW6-HTTP-API-Client
├── config_models.py           # Datenmodelle, Profile, Bedingungen
├── arduino_bridge.py          # Serielle Arduino-Kommunikation
├── zusi3_client.py            # Zusi-3-TCP-Client
├── zusi3_protocol.py          # Zusi-3-Binärprotokoll-Parser
├── TSW6_Arduino_Bridge.spec   # PyInstaller-Spec-Datei
├── requirements.txt           # Python-Abhängigkeiten
├── ARDUINO_FIRMWARE.md        # Arduino-Firmware-Anleitung (beide Versionen)
├── ArduinoSerialOnly/         # Firmware: nur serielle LEDs (einfach)
│   ├── ArduinoSerialOnly.ino
│   └── WIRING.h
├── ArduinoJoystick/           # Firmware: LED + Joystick (vollständig)
│   ├── ArduinoJoystick.ino
│   └── WIRING.h
├── tsw6_bridge.ico            # Anwendungssymbol
└── COPILOT_CONTEXT.md         # Vollständiger Kontext für GitHub Copilot
```

## LED-Prioritätslogik

Jede LED kann mehrere Zuordnungen mit einer **numerischen Priorität** haben. Die Zuordnung mit der höchsten Priorität und erfüllter Bedingung gewinnt:

| Priorität | Wirkung | Beispiel |
|-----------|---------|----------|
| 0 | Dauerlicht | Aktive PZB-Zugart |
| 1 | Blinken 1,0s | Frequenzüberwachung |
| 3 | Blinken 1,0s | Restriktiv (Wechselblinken) |
| 4 | Blinken 0,5s | Geschwindigkeitsüberschreitung |
| 5 | Blinken 0,3s | Zwangsbremsung |

### Wechselblinken (PZB 90)

Im **restriktiven** Modus blinken die LEDs PZB 70 und PZB 85 gegenphasig (*Wechselblinken*), genau wie beim realen PZB 90:

> *"Wird eine 1000- oder 500-Hz-Beeinflussung restriktiv, so wird dies durch Wechselblinken der Zugart-Leuchtmelder 70 und 85 angezeigt."*
> — Wikipedia, Punktförmige Zugbeeinflussung

## Lizenz

Dieses Werk ist lizenziert unter einer [Creative Commons Namensnennung - Nicht kommerziell 4.0 International Lizenz](https://creativecommons.org/licenses/by-nc/4.0/deed.de).

Sie dürfen dieses Werk für nicht-kommerzielle Zwecke teilen und bearbeiten, mit angemessener Namensnennung. Siehe [LICENSE](LICENSE) für Details.
