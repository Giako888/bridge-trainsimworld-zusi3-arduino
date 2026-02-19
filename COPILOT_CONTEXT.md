# Train Simulator Bridge — Contesto per GitHub Copilot

> Apri questo file e incollalo come primo messaggio in una nuova sessione Copilot
> per riprendere il lavoro esattamente da dove è stato lasciato.
>
> **Ultimo aggiornamento**: 19 febbraio 2026

---

## Progetto

**Train Simulator Bridge** v3.5.0.0 — Applicazione Python/Tkinter che legge dati in tempo reale
da **Train Sim World 6** (HTTP API) oppure **Zusi 3** (TCP binary protocol) e li invia ad un
Arduino Leonardo per controllare 13 LED fisici (Charlieplexing 5 pin) che replicano le spie del
pannello MFA di un treno tedesco (PZB/SIFA/LZB).

### File principali

| File | Scopo |
|------|-------|
| `tsw6_api.py` | Client HTTP per TSW6 API (porta 31270) + classe TSW6Poller (polling GET) |
| `tsw6_arduino_gui.py` | GUI Tkinter principale, 2 tab: Connessione, Profilo (~1977 righe) |
| `led_panel.py` | Pannello LED MFA (popup Tkinter ridimensionabile + web server HTTP) |
| `i18n.py` | Traduzioni multilingua (IT/EN/DE), auto-detect lingua sistema |
| `arduino_bridge.py` | ArduinoController — comunicazione seriale con Arduino Leonardo (13 LED) |
| `config_models.py` | Modelli dati: LedMapping, Profile, SimulatorType, 7 profili treno (~2070 righe) |
| `zusi3_protocol.py` | Protocollo binario TCP Zusi 3 (Node/Attribute parser) |
| `zusi3_client.py` | Client TCP Zusi 3 (HELLO/ACK, data streaming, TrainState) |
| `ARDUINO_FIRMWARE.md` | Guida completa firmware Arduino (entrambe le versioni) |

### Due firmware Arduino

Sono disponibili **due versioni** del firmware Arduino, entrambe 100% compatibili:

| | **ArduinoSerialOnly** | **ArduinoJoystick** |
|---|---|---|
| Scopo | Solo pannello LED (MFA) | LED + controller joystick completo |
| Componenti | ~16 (Arduino + 13 LED + 13 resistori) | 70+ (slider, encoder, switch, diodi, LED) |
| Pin usati | 5 (A3, 0, 1, A4, 14/MISO) | Tutti (20 pin) + pin 14 (ICSP) |
| Librerie | Nessuna | Joystick + Encoder |
| Cartella | `ArduinoSerialOnly/` | `ArduinoJoystick/` |
| Setup msg | `OK:SerialOnly Ready` | `OK:Joystick+Zusi Ready` |

Stesso protocollo seriale in entrambe: `SIFA:0/1`, `LED:n:0/1`, `OFF`, ecc.

### Stack tecnologico
- Python 3.13, Windows 11
- `requests` + `urllib3` (HTTP con retry)
- `tkinter` (GUI)
- `pyserial` (Arduino)
- `qrcode` (QR code per pannello web)
- `PyInstaller` (compilazione EXE → `dist/TrainSimBridge.exe`)
- Arduino Leonardo (ATmega32U4), Charlieplexing 5 pin → 13 LED, Serial 115200 baud

---

## ⚠️ REGOLE IMPORTANTI

### NON killare il gioco TSW6!
Quando si deve chiudere il nostro EXE prima di ricompilare, usare SEMPRE:
```powershell
Get-Process -Name "TrainSimBridge" -ErrorAction SilentlyContinue | Stop-Process -Force
```
**MAI** usare pattern generici come `*TrainSim*` — questo matcha anche il processo del gioco TSW6!

### Compilazione EXE
```powershell
cd c:\Users\Giako\Desktop\progetto2\tsw6_joystick_bridge
Get-Process -Name "TrainSimBridge" -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 1
python -m PyInstaller TSW6_Arduino_Bridge.spec --noconfirm
```
L'EXE viene generato in `dist/TrainSimBridge.exe`.

---

## Architettura Dual-Simulator

### Selettore Simulatore (Radio buttons in tab Connessione)
- **TSW6**: HTTP API porta 31270, CommAPIKey header, polling 50ms
- **Zusi3**: TCP binary protocol porta 1436, HELLO/ACK handshake, real-time streaming

### Blocco simulatore
Quando ci si connette a un simulatore, i radio buttons si disabilitano con messaggio
"🔒 TSW6/Zusi3 connesso — disconnetti per cambiare". Si sbloccano alla disconnessione.

### Tab Profilo
- **Abilitato** quando TSW6 è selezionato (profili con endpoint configurabili)
- **Disabilitato** quando Zusi3 è selezionato (testo "🚂 Profilo (N/A)", stile greyed out)
- Zusi3 ha mappature LED fisse via TrainState → direct LED control

### Tab Scopri Endpoint
**RIMOSSO** — era usato per scansionare endpoint TSW6, ora non serve più.

---

## TSW6 External Interface API — Punti critici

### Formato risposta (IMPORTANTE!)

```json
GET /get/CurrentFormation/0/MFA_Indicators.Property.B_IsActive
Headers: DTGCommKey: <api_key>

Risposta:
{
  "Result": "Success",
  "Values": {
    "Value": true
  }
}
```

**ATTENZIONE**: La chiave è `"Values"` (plurale, è un dizionario), NON `"Value"` (singolare).
Per estrarre il valore: `list(result["Values"].values())[0]`

### CommAPIKey
File: `Documents\My Games\TrainSimWorld6\Saved\Config\CommAPIKey.txt`
Header HTTP: `DTGCommKey: <chiave>`
Senza chiave → 403 Forbidden. L'app ha auto-detect della chiave.

### URL encoding dei path
I path con caratteri speciali DEVONO essere URL-encoded segmento per segmento:
- `Ü` → `%C3%9C`, `(` → `%28`, `)` → `%29`
- Separatori `/` e `.` NON vanno codificati
La funzione `encode_path()` in `tsw6_api.py` gestisce questo.

---

## 13 LED Arduino

| # | Nome | Descrizione |
|---|------|-------------|
| 1 | SIFA | Sicherheitsfahrschaltung (Vigilanza) |
| 2 | LZB | Linienzugbeeinflussung Ende |
| 3 | PZB70 | PZB 70 km/h |
| 4 | PZB85 | PZB 85 km/h |
| 5 | PZB55 | PZB 55 km/h |
| 6 | 500HZ | PZB 500Hz |
| 7 | 1000HZ | PZB 1000Hz |
| 8 | TUEREN_L | Porte sinistra |
| 9 | TUEREN_R | Porte destra |
| 10 | LZB_UE | LZB Überwachung |
| 11 | LZB_G | LZB G (attivo) |
| 12 | LZB_S | LZB S (frenata) |
| 13 | BEF40 | Befehl 40 km/h |

---

## Profili Treno (7 profili)

### BR101 — `create_default_profile()` (24 mappature)
- **ObjectClass match**: `BR101`, `BR_101`
- **PZB**: `PZB_V3` (Property/Function)
- **LZB**: `LZB` (Property)
- **SIFA**: `BP_Sifa_Service` (Property)
- **MFA**: `MFA_Indicators` (pannello completo con IsActive + IsFlashing)
- **Porte**: `PassengerDoorSelector_F/R.Function.GetCurrentOutputValue`

### Vectron — `create_vectron_profile()`
- **ObjectClass match**: `Vectron`
- **PZB**: `PZB_Service_V3` — usa `Get_InfluenceState` con `value_key`
- **LZB**: `LZB_Service` (Property)
- **SIFA**: `BP_Sifa_Service` (identica a BR101)
- **MFA**: NON presente — usa endpoint diretti PZB/LZB
- **Porte**: `DoorLockSignal`

### Bpmmbdzf — `create_bpmmbdzf_profile()`
- **ObjectClass match**: `Bpmmbdzf`
- Carrozza pilota — stessi endpoint MFA della BR101

### BR146 — `create_br146_profile()` (26 mappature) ← AGGIORNATO 15/02/2026
- **ObjectClass match**: `BR146`, `BR_146`
- **PZB**: `PZB_Service_V2` — usa `Get_InfluenceState` con `value_key`
- **LZB**: `LZB_Service` (Property)
- **SIFA**: `SIFA` (componente diretto, non BP_Sifa_Service)
  - Warning: `SIFA.Function.isWarningState`
  - Emergency: `SIFA.Function.InEmergency`
- **MFA**: NON presente
- **Porte**: `DriverAssist.Function.GetAreDoorsUnlocked`

### Tabella comparativa endpoint

| Sistema | BR101 | Vectron | BR146.2 | BR114 | BR411 | BR406 |
|---------|-------|---------|---------|-------|-------|-------|
| PZB | `PZB_V3` | `PZB_Service_V3` | `PZB_Service_V2` | `PZB` | `PZB_Service_V3` | `PZB` |
| LZB | `LZB` | `LZB_Service` | `LZB_Service` | — | `LZB` | `LZB` |
| SIFA | `BP_Sifa_Service` | `BP_Sifa_Service` | `SIFA` | `BP_Sifa_Service` | `BP_Sifa_Service` | `IsSifaInEmergency` |
| MFA | `MFA_Indicators` | — | — | — | — | — |
| Porte | `PassengerDoorSelector` | `DoorLockSignal` | `DriverAssist.GetAreDoorsUnlocked` | `DriverAssist_F/B.GetAreDoorsUnlocked` | `DriverAssist.GetAreDoorsUnlocked` | `PassengerDoor_FL/FR/BL/BR` |

---

## Logica LED — Sistema a priorità numerica

Le mappature per lo stesso LED usano un **accumulator con priorità numerica**:
- La mappatura con **priority più alta** e condizione True vince
- Se la mappatura vincente è `BLINK` → LED lampeggia
- Se la mappatura vincente è `ON` → LED acceso fisso
- Se nessuna mappatura è True → LED spento

Il `value_key` nelle mappature serve per estrarre campi da risposte dict
(es. `Get_InfluenceState` ritorna un dict con `1000Hz_Active`, `500Hz_Active`, ecc.)

La condizione `Condition.EQUAL` con `threshold` serve per matchare valori numerici
(es. `ActiveMode == 3` per selezionare la modalità PZB attiva).

---

## BR146 PZB — Comportamento reale PZB 90 (da Wikipedia DE)

### Riferimento: Wikipedia DE "Punktförmige Zugbeeinflussung"
> *"Wird eine 1000- oder 500-Hz-Beeinflussung restriktiv, so wird dies durch
> **Wechselblinken der Zugart-Leuchtmelder 70 und 85** angezeigt."*

### Zugart (Modalità treno) — Endpoint: `PZB_Service_V2.Property.ActiveMode`
| ActiveMode | Nome | Velocità max |
|------------|------|-------------|
| 3 | **O** (Obere) | 85 km/h |
| 2 | **M** (Mittlere) | 70 km/h |
| 1 | **U** (Untere) | 55 km/h |

### Logica LED PZB (26 mappature totali nel profilo BR146)

#### Livelli di priorità:
| Priorità | Stato | Azione | Intervallo |
|----------|-------|--------|------------|
| 0 (base) | Modalità attiva (da ActiveMode) | **ON fisso** | — |
| 1 | Frequenza attiva (monitoraggio) | **BLINK** | 1.0s |
| 3 | **Restriktiv** (Wechselblinken 70↔85) | **BLINK** | 1.0s |
| 4 | Overspeed | **BLINK** | 0.5s |
| 5 | Emergenza (_InEmergency) | **BLINK** | 0.3s |

#### Dettaglio per LED:

**PZB85** (5 mappature):
1. `ActiveMode == 3` → ON (pri 0) — modalità O attiva
2. `1000Hz_Active` → BLINK 1.0s (pri 1) — magnete 1000Hz superato
3. `isRestricted` → BLINK 1.0s (pri 3) — Wechselblinken con PZB70
4. `PZB_GetOverspeed` → BLINK 0.5s (pri 4)
5. `_InEmergency` → BLINK 0.3s (pri 5)

**PZB70** (5 mappature):
1. `ActiveMode == 2` → ON (pri 0) — modalità M attiva
2. `500Hz_Active` → BLINK 1.0s (pri 1) — magnete 500Hz superato
3. `isRestricted` → BLINK 1.0s (pri 3) — Wechselblinken con PZB85
4. `PZB_GetOverspeed` → BLINK 0.5s (pri 4)
5. `_InEmergency` → BLINK 0.3s (pri 5)

**PZB55** (4 mappature — NO restricted!):
1. `ActiveMode == 1` → ON (pri 0) — modalità U attiva
2. `2000Hz_Active` → BLINK 1.0s (pri 1) — magnete 2000Hz
3. `PZB_GetOverspeed` → BLINK 0.5s (pri 4)
4. `_InEmergency` → BLINK 0.3s (pri 5)

#### Wechselblinken (alternanza 70↔85 in restricted):
La GUI ha logica automatica in `_update_led_indicators()`:
```python
both_pzb_blink = pzb70_blink and pzb85_blink
if both_pzb_blink and name == "PZB85":
    phase = 1 - phase  # fase opposta = alternanza
```
Quando sia PZB70 che PZB85 sono BLINK contemporaneamente (entrambi hanno
`isRestricted=True`), la GUI li alterna automaticamente = Wechselblinken reale.

#### PZB55 NON partecipa al Wechselblinken
Solo PZB70 e PZB85 alternano in restricted mode, come da specifica PZB 90 reale.

### Endpoint PZB BR146 usati:
```
PZB_FN = "CurrentFormation/0/PZB_Service_V2.Function."
PZB_PR = "CurrentFormation/0/PZB_Service_V2.Property."
```
- `PZB_FN + "Get_InfluenceState"` → dict con: `1000Hz_Active`, `500Hz_Active`,
  `2000Hz_Active`, `isRestricted`, `isOverspeed`, `isEmergency`,
  `1000Hz_Time`, `1000Hz_ReleaseRange`, `500Hz_Time`, `500Hz_ReleaseRange`
- `PZB_PR + "ActiveMode"` → int (1/2/3)
- `PZB_PR + "bIsPZB_Active"` → bool (True = sistema PZB acceso — ⚠️ NON usare per LED individuali, accende tutti e 3!)
- `PZB_PR + "_RequiresAcknowledge"` → bool (finestra Wachsam 4s)
- `PZB_PR + "_InEmergency"` → bool
- `PZB_FN + "PZB_GetOverspeed"` → bool

### ⚠️ ERRORI DA NON RIPETERE

**1. `bIsPZB_Active`** — indica se il **sistema** PZB è attivo, NON quale modalità è selezionata.
Se usato come mappatura per PZB85/70/55, accende **tutti e 3 i LED insieme** = SBAGLIATO.
Usare sempre `ActiveMode` (1/2/3) per determinare quale singolo LED accendere.

**2. `bIsActivated` (LZB)** — indica che il **sistema** LZB è acceso, NON che sta frenando.
Se usato per LZB G → LED sempre acceso = SBAGLIATO.
Usare `OverspeedState > 0` per rilevare l'intervento LZB (frenata/rallentamento).

### LZB Ende — EndeState valori
- `EndeState == 1` → lampeggio (attesa conferma macchinista) → mappatura BLINK priority 1
- `EndeState == 2` → fisso (confermato) → mappatura ON priority 0 (`> 0`)
- `EndeState == 0` → spento

### PZB suppression quando LZB Ü attivo
Quando LZB Ü è attivo (`ULightState > 0`), i LED PZB devono spegnersi.
Implementato con `requires_endpoint_false = LZB_PR + "ULightState"` su tutte le
mappature PZB (PZB85, PZB70, PZB55, 1000HZ, 500HZ) nei profili Vectron, BR146, BR411.

---

## Diagnostica live dal simulatore

### Script di analisi rapida
Per leggere lo stato corrente degli endpoint PZB dal gioco in esecuzione:
```python
import requests
headers = {"DTGCommKey": open(r"path\to\CommAPIKey.txt").read().strip()}
base = "http://127.0.0.1:31270/get/"

# Stato PZB
influence = requests.get(base + "CurrentFormation/0/PZB_Service_V2.Function.Get_InfluenceState", headers=headers).json()
active_mode = requests.get(base + "CurrentFormation/0/PZB_Service_V2.Property.ActiveMode", headers=headers).json()
pzb_active = requests.get(base + "CurrentFormation/0/PZB_Service_V2.Property.bIsPZB_Active", headers=headers).json()
```

### Ultimo stato diagnosticato (sessione 15/02/2026):
- `ActiveMode = 3` (Zugart O, 85 km/h)
- `bIsPZB_Active = True`
- `1000Hz_Active = False`, `500Hz_Active = False`, `2000Hz_Active = False`
- `isRestricted = True` → Wechselblinken 70↔85 attivo (comportamento corretto!)
- `1000Hz_Time = 24`, `1000Hz_ReleaseRange = True`
- Questa situazione = dopo passaggio magnete 1000Hz, velocità scesa sotto Vum,
  monitoraggio restriktiv attivo con limite 45 km/h

---

## Zusi 3 Bridge

### Protocollo
- TCP binary: Node/Attribute con header 4 bytes (ID uint16 + lunghezza uint16)
- Handshake: HELLO → ACK_HELLO
- Richiesta dati: NEEDED_DATA → streaming continuo
- Messaggio tipo 10 (Fahrpult): dati treno in tempo reale

### TrainState → LED
Mappatura diretta da `TrainState` dataclass a 13 LED:
- `sifa_warning` → SIFA
- `pzb_1000hz` → 1000HZ, PZB85
- `pzb_500hz` → 500HZ, PZB70
- `pzb_55` → PZB55
- `lzb_ende` → LZB
- `lzb_ue` → LZB_UE
- `lzb_g` → LZB_G
- `lzb_s` → LZB_S
- `doors_left` → TUEREN_L
- `doors_right` → TUEREN_R
- `lm_befehl` → BEF40

### Blink Timer Zusi3
Timer separato `_start_zusi3_blink_timer()` per gestire LED lampeggianti
(es. SIFA warning → BLINK, PZB emergenza → BLINK).

---

## Bug risolti storici

- **LED GUI non si aggiornavano**: callback poller chiamato fuori dal main thread Tkinter
  → fix con `root.after(0, ...)` wrapper
- **Endpoint sbagliati BR101**: SIFA usava `bSifaPedalWarning` (sbagliato) invece di
  `BP_Sifa_Service.Property.WarningStateVisual`, PZB70 usava `B_IsActive` (Befehl!)
  invece di `70_IsActive_PZB`, TUEREN_L usava `InputValue` (0.5 sempre) invece di
  `GetCurrentOutputValue`
- **detect_train()**: usava `get_raw` (ritorna dict grezzo) invece di `get` (estrae valore)
- **PZB LED BR146 tutti accesi insieme**: usato `bIsPZB_Active` (accende tutti e 3) →
  fix con `ActiveMode` (1/2/3) per accendere solo il LED della modalità attiva
- **PZB85 blinkava al posto di essere fisso**: priority BLINK da `isRestricted` (pri 3)
  sovrascriveva ON da `ActiveMode` (pri 0) — comportamento corretto! Il Wechselblinken
  è il comportamento reale del PZB 90 in restricted mode (confermato Wikipedia DE)
- **LZB G sempre acceso**: usato `bIsActivated` (sistema ON) → fix con `OverspeedState > 0`
  (intervento LZB attivo). Fix applicato a Vectron, BR146, BR411
- **PZB LED attivi durante LZB Ü**: i LED PZB devono spegnersi quando LZB Ü è attivo →
  fix con `requires_endpoint_false = ULightState` su tutte le mappature PZB
- **LZB Ende fisso invece di lampeggiare**: `EndeState == 1` = attesa conferma (BLINK),
  `EndeState == 2` = confermato (ON fisso). Aggiunta mappatura BLINK per EndeState == 1

---

## Stato attuale (19 febbraio 2026)

### Cosa funziona:
- ✅ 7 profili treno: BR101 Expert, Vectron, Bpmmbdzf Expert, BR146, BR114, BR411 ICE-T, BR406 ICE 3
- ✅ PZB LED con ActiveMode (solo il LED della modalità attiva si accende)
- ✅ Wechselblinken 70↔85 in restricted mode (confermato comportamento reale PZB 90)
- ✅ PZB55 escluso dal Wechselblinken (corretto)
- ✅ Frequenze (1000Hz/500Hz/2000Hz) → BLINK sui LED corrispondenti
- ✅ Overspeed e emergenza → BLINK rapido
- ✅ SIFA warning/emergenza funzionante
- ✅ LZB Ende: lampeggia (EndeState == 1) o fisso (EndeState > 0)
- ✅ LZB Ü: attivo (ULightState > 0), lampeggio fault (FaultCode > 0)
- ✅ LZB G: intervento attivo (OverspeedState > 0)
- ✅ LZB S: frenata (Enforcement = True)
- ✅ PZB suppression quando LZB Ü attivo
- ✅ Befehl 40 (LED13 su pin 14/MISO) — 5 pin Charlieplexing
- ✅ Pannello MFA popup Tkinter ridimensionabile (proporzioni mantenute)
- ✅ Web server MFA con porta configurabile (default 8080)
- ✅ QR code per connessione rapida da tablet
- ✅ Gestione automatica regola Windows Firewall (netsh)
- ✅ EXE compilato correttamente (`dist/TrainSimBridge.exe`)

### Prossimi passi:
1. **Testare con Arduino collegato** — Verificare comunicazione seriale e LED fisici
2. **Opzionale**: passare a subscription mode TSW6 (più efficiente del polling GET)
3. **Aggiungere altri treni**: scansionare endpoint di nuovi treni e creare profili
