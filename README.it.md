# 🚂 Train Simulator Bridge

[🇬🇧 English](README.md) | 🇮🇹 **Italiano** | [🇩🇪 Deutsch](README.de.md)

**Replica fisica delle spie MFA** di un treno tedesco (PZB / SIFA / LZB) usando un Arduino Leonardo con 12 LED Charlieplexing, pilotati in tempo reale dai dati di **Train Sim World 6** o **Zusi 3**.

![Python](https://img.shields.io/badge/Python-3.13-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Panoramica

```
┌──────────────┐    HTTP / TCP    ┌──────────────────┐    Seriale   ┌─────────────────┐
│  Train Sim   │ ──────────────> │  Train Simulator │ ──────────> │  Arduino        │
│  World 6     │   porta 31270   │  Bridge (Python) │  115200 bd  │  Leonardo       │
│  oppure      │   porta 1436    │                  │             │  12 LED (MFA)   │
│  Zusi 3      │                 │  GUI Tkinter     │             │  Charlieplexing │
└──────────────┘                 └──────────────────┘             └─────────────────┘
```

L'applicazione legge i dati del simulatore ferroviario in tempo reale e controlla 12 LED fisici che replicano il pannello **MFA** (Multifunktionale Anzeige) presente nella cabina di guida dei treni tedeschi.

## Funzionalità

- **Doppio simulatore**: supporto TSW6 (HTTP API) e Zusi 3 (protocollo TCP binario)
- **4 profili treno**: DB BR 101, Siemens Vectron, Bpmmbdzf (carrozza pilota), DB BR 146.2
- **Auto-detect treno**: riconosce automaticamente la locomotiva in uso e carica il profilo corretto
- **12 LED fisici**: PZB (55/70/85, 500Hz, 1000Hz), SIFA, LZB (Ende, Ü, G, S), Porte (L/R)
- **LED realistici**: logica a priorità con ON fisso, BLINK a velocità variabile, Wechselblinken PZB 70↔85
- **GUI moderna**: interfaccia dark theme con anteprima LED in tempo reale
- **EXE standalone**: compilabile con PyInstaller, nessuna installazione Python richiesta

## 12 LED del pannello MFA

| # | LED | Funzione |
|---|-----|----------|
| 1 | **SIFA** | Sicherheitsfahrschaltung (vigilanza) |
| 2 | **LZB** | Linienzugbeeinflussung Ende |
| 3 | **PZB 70** | PZB modalità M (70 km/h) |
| 4 | **PZB 85** | PZB modalità O (85 km/h) |
| 5 | **PZB 55** | PZB modalità U (55 km/h) |
| 6 | **500 Hz** | PZB frequenza 500 Hz |
| 7 | **1000 Hz** | PZB frequenza 1000 Hz |
| 8 | **Türen L** | Porte sinistra sbloccate |
| 9 | **Türen R** | Porte destra sbloccate |
| 10 | **LZB Ü** | LZB sorveglianza |
| 11 | **LZB G** | LZB attivo |
| 12 | **LZB S** | LZB frenata forzata |

## Requisiti

### Software
- **Python 3.13+** (oppure usare l'EXE precompilato)
- **Windows 10/11**
- **Train Sim World 6** con External Interface API abilitata, oppure **Zusi 3**

### Hardware
- **Arduino Leonardo** (ATmega32U4)
- 12 LED collegati in configurazione **Charlieplexing** su 4 pin

## Installazione

### Da sorgente

```bash
git clone https://github.com/Giako888/bridge-trainsim-arduino.git
cd bridge-trainsim-arduino
pip install -r requirements.txt
python tsw6_arduino_gui.py
```

### Compilazione EXE

```bash
python -m PyInstaller TSW6_Arduino_Bridge.spec --noconfirm
# Output: dist/TrainSimBridge.exe
```

## Configurazione TSW6

1. Avvia **Train Sim World 6**
2. L'API key viene letta automaticamente da:
   ```
   %USERPROFILE%\Documents\My Games\TrainSimWorld6\Saved\Config\CommAPIKey.txt
   ```
3. In Train Simulator Bridge, seleziona **TSW6** e premi **Connetti**
4. Il treno viene riconosciuto automaticamente e il profilo LED si carica

## Configurazione Zusi 3

1. Avvia **Zusi 3** con l'interfaccia TCP attiva (porta 1436)
2. In Train Simulator Bridge, seleziona **Zusi3** e premi **Connetti**
3. Le mappature LED sono fisse e gestite dal protocollo Zusi3

## Profili treno supportati

| Treno | PZB | LZB | SIFA | Note |
|-------|-----|-----|------|------|
| **DB BR 101** | PZB_V3 | LZB | BP_Sifa_Service | Pannello MFA completo |
| **Siemens Vectron** | PZB_Service_V3 | LZB_Service | BP_Sifa_Service | Senza MFA |
| **Bpmmbdzf** | — | — | — | Carrozza pilota (stessi endpoint BR101) |
| **DB BR 146.2** | PZB_Service_V2 | LZB_Service | SIFA | 26 mappature, PZB 90 realistico |

## Struttura del progetto

```
├── tsw6_arduino_gui.py        # GUI principale (Tkinter)
├── tsw6_api.py                # Client HTTP per TSW6 API
├── config_models.py           # Modelli dati, profili, condizioni
├── arduino_bridge.py          # Comunicazione seriale Arduino
├── zusi3_client.py            # Client TCP Zusi 3
├── zusi3_protocol.py          # Parser protocollo binario Zusi 3
├── TSW6_Arduino_Bridge.spec   # Spec file PyInstaller
├── build_tsw6_bridge.bat      # Script build Windows
├── requirements.txt           # Dipendenze Python
├── tsw6_bridge.ico            # Icona applicazione
├── tsw6_endpoints.json        # Endpoint TSW6 noti
└── COPILOT_CONTEXT.md         # Contesto completo per GitHub Copilot
```

## Come funziona la logica LED

Ogni LED può avere più mappature con **priorità numerica**. La mappatura con la priorità più alta e condizione soddisfatta vince:

| Priorità | Effetto | Esempio |
|----------|---------|---------|
| 0 | ON fisso | Modalità PZB attiva |
| 1 | BLINK 1.0s | Monitoraggio frequenza |
| 3 | BLINK 1.0s | Restricted mode (Wechselblinken) |
| 4 | BLINK 0.5s | Overspeed |
| 5 | BLINK 0.3s | Emergenza |

### Wechselblinken (PZB 90)

In modalità **restriktiv**, i LED PZB 70 e PZB 85 alternano in anti-fase (*Wechselblinken*), esattamente come nel sistema PZB 90 reale:

> *"Wird eine 1000- oder 500-Hz-Beeinflussung restriktiv, so wird dies durch Wechselblinken der Zugart-Leuchtmelder 70 und 85 angezeigt."*
> — Wikipedia DE, Punktförmige Zugbeeinflussung

## Licenza

MIT License
