# 🚂 Train Simulator Bridge

[🇬🇧 English](README.md) | 🇮🇹 **Italiano** | [🇩🇪 Deutsch](README.de.md)

**Replica fisica delle spie MFA** di un treno tedesco (PZB / SIFA / LZB) usando un Arduino Leonardo con 13 LED tramite driver MAX7219 (3 pin), pilotati in tempo reale dai dati di **Train Sim World 6** o **Zusi 3**.

![Python](https://img.shields.io/badge/Python-3.13-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6)
![License](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey)
[![Release](https://img.shields.io/github/v/release/Giako888/bridge-trainsimworld-zusi3-arduino)](https://github.com/Giako888/bridge-trainsimworld-zusi3-arduino/releases/latest)
[![Download EXE](https://img.shields.io/badge/Download-TrainSimBridge.exe-brightgreen)](https://github.com/Giako888/bridge-trainsimworld-zusi3-arduino/releases/latest)

---

## Screenshot

| GUI Principale | Popup MFA | Pannello Web | Tab Profilo |
|:--------------:|:---------:|:------------:|:-----------:|
| ![GUI Principale](screenshots/gui_main_en.png) | ![Popup MFA](screenshots/mfa_popup.png) | ![Pannello Web](screenshots/web_panel.png) | ![Tab Profilo](screenshots/tab_profili.png) |

## Panoramica

```
┌──────────────┐    HTTP / TCP    ┌──────────────────┐    Seriale   ┌─────────────────┐
│  Train Sim   │ ──────────────> │  Train Simulator │ ──────────> │  Arduino        │
│  World 6     │   porta 31270   │  Bridge (Python) │  115200 bd  │  Leonardo       │
│  oppure      │   porta 1436    │                  │             │  13 LED (MFA)   │
│  Zusi 3      │                 │  GUI Tkinter     │             │  MAX7219 LED    │
└──────────────┘                 └──────────────────┘             └─────────────────┘
```

L'applicazione legge i dati del simulatore ferroviario in tempo reale e controlla 13 LED fisici che replicano il pannello **MFA** (Multifunktionale Anzeige) presente nella cabina di guida dei treni tedeschi.

## Funzionalità

- **Doppio simulatore**: supporto TSW6 (HTTP API) e Zusi 3 (protocollo TCP binario)
- **TSW6**: 7 profili treno con mappature endpoint specifiche (DB BR 101 Expert, Vectron, Bpmmbdzf Expert, BR 146.2, BR 114, BR 411 ICE-T, BR 406 ICE 3)
- **Zusi 3**: funziona con la maggior parte dei treni — i dati LED arrivano via protocollo TCP generico
- **SimRail** (previsto): il supporto verrà aggiunto quando verranno rilasciate le API ufficiali di I/O per la strumentazione di cabina
- **Auto-detect** (TSW6): riconosce automaticamente la locomotiva in uso e carica il profilo corretto
- **13 LED fisici**: PZB (55/70/85, 500Hz, 1000Hz), SIFA, LZB (Ende, Ü, G, S), Porte (L/R), Befehl 40
- **LED realistici**: logica a priorità con ON fisso, BLINK a velocità variabile, Wechselblinken PZB 70↔85
- **Pannello MFA Web**: pannello LED consultabile da browser su tablet / telefono nella rete locale
- **QR Code**: QR code per collegare rapidamente il tablet al pannello web
- **GUI multilingua**: italiano, inglese, tedesco — rileva la lingua di sistema, selezionabile con icone bandiera
- **GUI moderna**: interfaccia dark theme con anteprima LED in tempo reale
- **EXE standalone**: compilabile con PyInstaller, nessuna installazione Python richiesta

## 13 LED del pannello MFA

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
| 13 | **Befehl 40** | Befehl 40 km/h |

## Requisiti

### Software
- **Python 3.13+** (oppure usare l'EXE precompilato)
- **Windows 10/11**
- **Train Sim World 6** con External Interface API abilitata (vedi [Configurazione TSW6](#configurazione-tsw6)), oppure **Zusi 3**

### Hardware
- **Arduino Leonardo** (ATmega32U4)
- 13 LED pilotati da modulo **MAX7219** (3 pin)
- Vedi [Firmware Arduino](#firmware-arduino) per le due versioni disponibili

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

### 1. Abilitare la HTTP API

L'External Interface API di TSW6 è **disabilitata di default**. Devi aggiungere il parametro di avvio `-HTTPAPI`:

<details>
<summary><b>Steam</b></summary>

1. Apri **Steam** → **Libreria**
2. Clic destro su **Train Sim World 6** → **Proprietà**
3. Nella scheda **Generali**, cerca **Opzioni di avvio**
4. Scrivi:
   ```
   -HTTPAPI
   ```
5. Chiudi la finestra — l'impostazione viene salvata automaticamente

</details>

<details>
<summary><b>Epic Games</b></summary>

1. Apri **Epic Games Launcher** → **Libreria**
2. Clicca i **tre puntini (⋯)** su Train Sim World 6 → **Gestisci**
3. Spunta **Argomenti aggiuntivi della riga di comando**
4. Scrivi:
   ```
   -HTTPAPI
   ```
5. Chiudi la finestra

</details>

### 2. Avviare TSW6 e generare la API key

1. Avvia **Train Sim World 6** (con `-HTTPAPI` attivo)
2. Il gioco genererà automaticamente il file chiave API in:
   ```
   %USERPROFILE%\Documents\My Games\TrainSimWorld6\Saved\Config\CommAPIKey.txt
   ```
   > **Nota:** questo file viene creato solo dopo il primo avvio con `-HTTPAPI`.

### 3. Connettere Train Simulator Bridge

1. Apri **Train Simulator Bridge**, seleziona **TSW6** e premi **Connetti**
2. La chiave API viene letta automaticamente — nessuna configurazione manuale
3. Il treno viene riconosciuto automaticamente e il profilo LED si carica

## Configurazione Zusi 3

1. Avvia **Zusi 3** con l'interfaccia TCP attiva (porta 1436)
2. In Train Simulator Bridge, seleziona **Zusi3** e premi **Connetti**
3. I dati LED arrivano via protocollo TCP generico — **funziona con la maggior parte dei treni**, senza bisogno di profili specifici

## Treni supportati

### TSW6 — Servono profili specifici

Ogni treno TSW6 necessita di un profilo dedicato con mappature endpoint API personalizzate. Solo i seguenti treni sono attualmente supportati:

| Treno | PZB | LZB | SIFA | Note |
|-------|-----|-----|------|------|
| **DB BR 101 (Expert)** | PZB_V3 | LZB | BP_Sifa_Service | Pannello MFA completo |
| **Siemens Vectron** | PZB_Service_V3 | LZB_Service | BP_Sifa_Service | Senza MFA |
| **Bpmmbdzf (Expert)** | — | — | — | Carrozza pilota (stessi endpoint BR101 Expert) |
| **DB BR 146.2** | PZB_Service_V2 | LZB_Service | SIFA | 26 mappature, PZB 90 realistico |
| **DB BR 114** | PZB | — | BP_Sifa_Service | Senza LZB, entrambe le cabine (F/B) |
| **DB BR 411 ICE-T** | PZB_Service_V3 | LZB | BP_Sifa_Service | Treno ad assetto variabile, senza MFA |
| **DB BR 406 ICE 3** | PZB | LZB | IsSifaInEmergency | ICE 3M, match parziale chiavi |

> Altri treni TSW6 verranno aggiunti nelle future versioni. — La maggior parte dei treni è supportata

Zusi 3 fornisce i dati della strumentazione di cabina tramite protocollo TCP generico (messaggio Fahrpult). Il pannello LED funziona con **la maggior parte dei treni** che espongono dati PZB/SIFA/LZB — senza bisogno di profili per singolo treno.

## Firmware Arduino

Sono disponibili due versioni del firmware, entrambe **compatibili al 100%** con Train Simulator Bridge (stesso protocollo seriale):

| | **ArduinoSerialOnly** | **ArduinoJoystick** |
|---|---|---|
| Scopo | Solo pannello LED (MFA) | Pannello LED + controller joystick completo |
| Componenti | ~16 (Arduino + 13 LED + 13 resistori) | 70+ (LED + slider + encoder + switch + diodi) |
| Pin usati | 5 (A3, 0, 1, A4, 14/MISO) | Tutti (20 pin) + pin 14 (ICSP) |
| Librerie | Nessuna | Joystick + Encoder |
| Difficoltà | Facile | Avanzato |

Vedi [ARDUINO_FIRMWARE.md](ARDUINO_FIRMWARE.md) per dettagli completi, schema di cablaggio e lista componenti.
Disponibile anche in: [English](ARDUINO_FIRMWARE_EN.md) | [Deutsch](ARDUINO_FIRMWARE_DE.md)

> **💡 Consiglio per la versione Joystick:** per configurare il joystick Arduino in TSW6, dai un'occhiata a [TSW Controller App](https://github.com/LiamMartens/tsw-controller-app) — un ottimo tool per mappare gli assi e i pulsanti del controller.

## Struttura del progetto

```
├── tsw6_arduino_gui.py        # GUI principale (Tkinter)
├── led_panel.py               # Pannello LED MFA (popup Tkinter + web server)
├── i18n.py                    # Traduzioni (IT/EN/DE)
├── tsw6_api.py                # Client HTTP per TSW6 API
├── config_models.py           # Modelli dati, profili, condizioni
├── arduino_bridge.py          # Comunicazione seriale Arduino
├── zusi3_client.py            # Client TCP Zusi 3
├── zusi3_protocol.py          # Parser protocollo binario Zusi 3
├── TSW6_Arduino_Bridge.spec   # Spec file PyInstaller
├── requirements.txt           # Dipendenze Python
├── ARDUINO_FIRMWARE.md        # Guida firmware Arduino (IT)
├── ARDUINO_FIRMWARE_EN.md     # Guida firmware Arduino (EN)
├── ARDUINO_FIRMWARE_DE.md     # Guida firmware Arduino (DE)
├── ArduinoSerialOnly/         # Firmware: solo LED seriale (semplice)
│   ├── ArduinoSerialOnly.ino
│   └── WIRING.h
├── ArduinoJoystick/           # Firmware: LED + joystick (completo)
│   ├── ArduinoJoystick.ino
│   └── WIRING.h
├── tsw6_bridge.ico            # Icona applicazione
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

Quest'opera è distribuita con licenza [Creative Commons Attribuzione - Non commerciale 4.0 Internazionale](https://creativecommons.org/licenses/by-nc/4.0/deed.it).

Puoi condividere e modificare quest'opera per scopi non commerciali, con attribuzione appropriata. Vedi [LICENSE](LICENSE) per i dettagli.
