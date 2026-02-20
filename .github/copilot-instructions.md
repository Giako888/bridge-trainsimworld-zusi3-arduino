# Copilot Instructions — Train Simulator Bridge

## Panoramica progetto

**Train Simulator Bridge** v3.6.0.0 — App Python/Tkinter che legge dati in tempo reale da
**Train Sim World 6** (HTTP API porta 31270) o **Zusi 3** (TCP binary porta 1436) e li invia
a un Arduino Leonardo per controllare 13 LED fisici (Charlieplexing 5 pin) che replicano
il pannello MFA di un treno tedesco (PZB/SIFA/LZB).

## Stack

- Python 3.13, Windows 11
- `requests` + `urllib3` (HTTP), `tkinter` (GUI), `pyserial` (Arduino)
- `PyInstaller` → `dist/TrainSimBridge.exe`
- Arduino Leonardo (ATmega32U4), Charlieplexing 5 pin → 13 LED, Serial 115200 baud

## File principali

| File | Ruolo |
|------|-------|
| `tsw6_arduino_gui.py` | GUI Tkinter principale (~1497 righe), 2 tab: Connessione/Profilo |
| `i18n.py` | Traduzioni multilingua (IT/EN/DE), auto-detect lingua sistema |
| `tsw6_api.py` | Client HTTP TSW6 API + TSW6Poller (polling GET) |
| `config_models.py` | Modelli dati: LedMapping, Profile, SimulatorType, 6 profili treno |
| `arduino_bridge.py` | ArduinoController — comunicazione seriale, 13 LED |
| `zusi3_client.py` | Client TCP Zusi 3 (HELLO/ACK, data streaming, TrainState) |
| `zusi3_protocol.py` | Parser protocollo binario Zusi 3 (Node/Attribute) |
| `ARDUINO_FIRMWARE.md` | Guida completa firmware Arduino (entrambe le versioni) |

## Due firmware Arduino

Due versioni del firmware, entrambe 100% compatibili con Train Simulator Bridge:

| | **ArduinoSerialOnly** | **ArduinoJoystick** |
|---|---|---|
| Scopo | Solo LED seriale | LED + joystick USB HID completo |
| Componenti | ~16 | 70+ |
| Pin | 5 (A3, 0, 1, A4, 14/MISO) | Tutti (20 pin) + pin 14 (ICSP) |
| Librerie | Nessuna | Joystick + Encoder |
| Cartella | `ArduinoSerialOnly/` | `ArduinoJoystick/` |

Stesso protocollo seriale: `SIFA:0/1`, `LED:n:0/1`, `OFF`, ecc.

## Versionamento

Schema: `A.B.C.D`
- **A** (major): riservato
- **B** (minor): cambiamenti enormi (nuove feature importanti)
- **C** (profile): quando si aggiungono profili treno
- **D** (fix): solo bugfix

## ⚠️ REGOLE CRITICHE

### MAI killare il gioco TSW6!
Per chiudere il nostro EXE prima di ricompilare:
```powershell
Get-Process -Name "TrainSimBridge" -ErrorAction SilentlyContinue | Stop-Process -Force
```
**MAI** usare `*TrainSim*` come pattern — matcha anche il processo del gioco!

### Compilazione EXE
```powershell
cd c:\Users\Giako\Desktop\progetto2\tsw6_joystick_bridge
Get-Process -Name "TrainSimBridge" -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 1
python -m PyInstaller TSW6_Arduino_Bridge.spec --noconfirm
```

### Distribuzione EXE — SOLO via GitHub Releases!
**MAI** fare `git add` dell'EXE! La cartella `dist/` è in `.gitignore`.
Per pubblicare l'EXE, usare **GitHub Releases**:
```powershell
gh release create vX.Y.Z.W dist/TrainSimBridge.exe --title "vX.Y.Z.W" --notes "changelog..."
```

### ⛔ MAI committare file grandi o protetti da copyright!
**Questo ha causato la SOSPENSIONE dell'account GitHub a febbraio 2026!**

File **VIETATI** nel repo (sono tutti in `.gitignore`):
- **Binari**: `.exe`, `.pkg`, `.pyz`, `.zip` — usare GitHub Releases
- **JSON grandi**: `tsw6_endpoints.json`, dump API, file > 1MB
- **PDF/documenti proprietari**: `TSW External Interface API.pdf` — copyright DTG!
- **Asset di gioco**: `.pak`, `.uasset`, `.umap`, `.uexp`, `.ubulk`
- **Build artifacts**: `build/`, `dist/`, `__pycache__/`

Prima di ogni `git add` o `git commit -a`, verificare con:
```powershell
git status --short
# Controllare che NON ci siano file binari/grandi nella lista!
```

Se per errore viene committato un file grande:
```powershell
git reset HEAD~1  # annulla l'ultimo commit (se non ancora pushato)
# oppure, se già pushato:
pip install git-filter-repo
git filter-repo --force --invert-paths --path <file-da-rimuovere>
git push --force origin main
```

## TSW6 API — Formato risposta

```json
GET http://127.0.0.1:31270/get/<endpoint>
Headers: DTGCommKey: <api_key>

{
  "Result": "Success",
  "Values": { "Value": true }   // ← "Values" (plurale, dict!), NON "Value"
}
```
Per estrarre: `list(result["Values"].values())[0]`

### CommAPIKey
Auto-detect da `%USERPROFILE%\Documents\My Games\TrainSimWorld6\Saved\Config\CommAPIKey.txt`

### URL encoding
I path con caratteri speciali vanno URL-encoded segmento per segmento.
La funzione `encode_path()` in `tsw6_api.py` lo gestisce.

## Architettura Dual-Simulator

- **TSW6**: HTTP API porta 31270, CommAPIKey, polling 50ms
- **Zusi3**: TCP binary porta 1436, HELLO/ACK handshake, streaming real-time
- Radio buttons nella tab Connessione, si bloccano durante la connessione

## 13 LED Arduino

| # | Nome | Sistema |
|---|------|---------|
| 1 | SIFA | Vigilanza |
| 2 | LZB | LZB Ende |
| 3 | PZB70 | PZB 70 km/h |
| 4 | PZB85 | PZB 85 km/h |
| 5 | PZB55 | PZB 55 km/h |
| 6 | 500HZ | PZB 500Hz |
| 7 | 1000HZ | PZB 1000Hz |
| 8 | TUEREN_L | Porte sinistra |
| 9 | TUEREN_R | Porte destra |
| 10 | LZB_UE | LZB Ü (sorveglianza) |
| 11 | LZB_G | LZB G (attivo) |
| 12 | LZB_S | LZB S (frenata) |
| 13 | BEF40 | Befehl 40 km/h |

> **Nota:** Il LED BEF40 (Befehl 40) non è ancora mappato in nessun profilo.
> Sulla BR101 Expert gli endpoint MFA esistono (`B_IsActive`, `B_IsFlashing`,
> `E40_IsActive`, `V40_IsActive`) e rispondono correttamente dall'API.

## Sistema a priorità LED

Le mappature per lo stesso LED usano un **accumulator a priorità numerica**:
- La mappatura con **priority più alta** e condizione True vince
- `BLINK` → lampeggia, `ON` → acceso fisso, nessuna True → spento
- `value_key` estrae campi da risposte dict (es. `Get_InfluenceState`)
- `Condition.EQUAL` con `threshold` per matchare valori numerici (es. `ActiveMode == 3`)

## 7 Profili treno

### BR101 — `create_default_profile()` (24 mappature)
- Match: `BR101`, `BR_101`
- Versione Expert del gioco
- PZB: `PZB_V3`, LZB: `LZB`, SIFA: `BP_Sifa_Service`, MFA: `MFA_Indicators`
- Porte: `PassengerDoorSelector_F/R.Function.GetCurrentOutputValue`

### Vectron — `create_vectron_profile()`
- Match: `Vectron`
- PZB: `PZB_Service_V3` con `Get_InfluenceState` + `value_key`
- LZB: `LZB_Service`, SIFA: `BP_Sifa_Service`, Porte: `DoorLockSignal`

### Bpmmbdzf — `create_bpmmbdzf_profile()`
- Match: `Bpmmbdzf` — carrozza pilota (stessi endpoint MFA della BR101 Expert)

### BR146 — `create_br146_profile()` (26 mappature)
- Match: `BR146`, `BR_146`
- PZB: `PZB_Service_V2` con `Get_InfluenceState` + `value_key`
- LZB: `LZB_Service`
- SIFA: `SIFA` (componente diretto — `isWarningState`, `InEmergency`)
- Porte: `DriverAssist.Function.GetAreDoorsUnlocked`

#### Endpoint PZB BR146:
```
PZB_FN = "CurrentFormation/0/PZB_Service_V2.Function."
PZB_PR = "CurrentFormation/0/PZB_Service_V2.Property."
```
- `Get_InfluenceState` → dict: `1000Hz_Active`, `500Hz_Active`, `2000Hz_Active`,
  `isRestricted`, `isOverspeed`, `isEmergency`, `1000Hz_Time`, `1000Hz_ReleaseRange`
- `ActiveMode` → int: 3=O(85), 2=M(70), 1=U(55)
- `_RequiresAcknowledge` → bool (finestra Wachsam)
- `_InEmergency` → bool
- `PZB_GetOverspeed` → bool

#### Logica PZB LED (comportamento reale PZB 90):

| Priorità | Stato | Azione | Intervallo |
|----------|-------|--------|------------|
| 0 | Modalità attiva (ActiveMode) | ON fisso | — |
| 1 | Frequenza attiva (monitoraggio) | BLINK | 1.0s |
| 3 | Restriktiv (Wechselblinken 70↔85) | BLINK | 1.0s |
| 4 | Overspeed | BLINK | 0.5s |
| 5 | Emergenza | BLINK | 0.3s |

PZB55 **NON** partecipa al Wechselblinken (solo 70 e 85 alternano in restricted).

#### Wechselblinken (Wikipedia DE):
> *"Wird eine 1000- oder 500-Hz-Beeinflussung restriktiv, so wird dies durch
> Wechselblinken der Zugart-Leuchtmelder 70 und 85 angezeigt."*

La GUI auto-alterna in `_update_led_indicators()`:
```python
both_pzb_blink = pzb70_blink and pzb85_blink
if both_pzb_blink and name == "PZB85":
    phase = 1 - phase  # anti-fase = alternanza
```

### BR114 — `create_br114_profile()`
- Match: `BR114`, `BR_114`
- PZB: `PZB` (componente diretto) con `Get_InfluenceState` + `value_key`
- LZB: **assente** (la BR 114 non ha LZB)
- SIFA: `BP_Sifa_Service` (come BR101)
- Porte: `DriverAssist_F/B.Function.GetAreDoorsUnlocked` (entrambe le cabine)

#### Endpoint PZB BR114:
```
PZB_FN = "CurrentFormation/0/PZB.Function."
PZB_PR = "CurrentFormation/0/PZB.Property."
```
- `Get_InfluenceState` → dict: `1000Hz_Active`, `500Hz_Active`, `2000Hz_Active`,
  `isRestricted`, `isOverspeed`, `isEmergency`, `1000Hz_Time`
- `ActiveMode` → int: 3=O(85), 2=M(70), 1=U(55)
- `_RequiresAcknowledge` → bool (finestra Wachsam)
- `_InEmergency` → bool
- `PZB_GetOverspeed` → bool

Stessa logica PZB LED della BR146 (priorità 0→5), stessa struttura Wechselblinken.

### BR411 — `create_br411_profile()`
- Match: `BR411`, `BR_411`
- PZB: `PZB_Service_V3` (come Vectron) con `Get_InfluenceState` + `value_key`
- LZB: `LZB` (come BR101, NON LZB_Service)
- SIFA: `BP_Sifa_Service` (come BR101)
- Porte: `DriverAssist.Function.GetAreDoorsUnlocked` (come BR146, senza suffisso cabina)

#### Endpoint PZB BR411:
```
PZB_FN = "CurrentFormation/0/PZB_Service_V3.Function."
PZB_PR = "CurrentFormation/0/PZB_Service_V3.Property."
```
- `Get_InfluenceState` → dict: `1000Hz_Active`, `500Hz_Active`, `2000Hz_Active`,
  `isRestricted`, `isOverspeed`, `isEmergency`, `1000Hz_Time`, `1000Hz_ReleaseRange`
- `ActiveMode` → int: 3=O(85), 2=M(70), 1=U(55)
- `_RequiresAcknowledge` → bool (finestra Wachsam)
- `_InEmergency` → bool
- `PZB_GetOverspeed` → bool

#### Endpoint LZB BR411:
```
LZB_PR = "CurrentFormation/0/LZB.Property."
```
- `EndeState` → int (>0 = LZB Ende attivo)
- `ULightState` → int (>0 = LZB Ü attivo)
- `OverspeedState` → int (>0 = LZB G, LZB interviene con frenata/rallentamento)
- `Enforcement` → bool (LZB S frenata)
- `faultCode` → int (>0 = fault, lampeggio Ü)

Stessa logica PZB LED della BR146 (priorità 0→5), stessa struttura Wechselblinken.
Formazione 7 carri: TW_5, SR_6, FM_7, MW_8, FM_2, SR_1, TW_0.

### BR406 — `create_br406_profile()`
- Match: `BR406`, `BR_406`, `ICE3M`
- ObjectClass: `RVM_KAH_DB_ICE3M_EndCar-5_C`
- PZB: `PZB` (come BR114) con `Get_InfluenceState` + `value_key` (chiavi con suffisso GUID, match parziale)
- LZB: `LZB` (come BR101/BR411)
- SIFA: funzione car-level `IsSifaInEmergency` + `HUD_GetAlerter`
  - `HUD_GetAlerter`: `AleterState` 0=normale, 1=warning/emergenza (api.get() ritorna il primo valore = AleterState)
  - `IsSifaInEmergency`: `bReturnValue` False=OK/warning, True=emergenza
- Porte: `PassengerDoor_FL/FR/BL/BR.Function.GetCurrentOutputValue` (0=chiusa, >0=aperta)

#### Endpoint PZB BR406:
```
PZB_FN = "CurrentFormation/0/PZB.Function."
PZB_PR = "CurrentFormation/0/PZB.Property."
```
- `Get_InfluenceState` → dict: `1000Hz_Active`, `500Hz_Active`, `2000Hz_Active`,
  `isRestricted`, `isOverspeed`, `isEmergency`, `1000Hz_Time`
  (chiavi con suffisso GUID, es. `1000Hz_Active_93_200CCCBC...`, match parziale)
- `ActiveMode` → int: 3=O(85), 2=M(70), 1=U(55)
- `_RequiresAcknowledge` → bool (finestra Wachsam)
- `_InEmergency` → bool
- `PZB_GetOverspeed` → bool

#### Endpoint LZB BR406:
```
LZB_PR = "CurrentFormation/0/LZB.Property."
```
- `EndeState` → int (>0 = LZB Ende attivo)
- `ULightState` → int (>0 = LZB Ü attivo)
- `OverspeedState` → int (>0 = LZB G, LZB interviene con frenata/rallentamento)
- `Enforcement` → bool (LZB S frenata)
- `faultCode` → int (>0 = fault, lampeggio Ü)

Stessa logica PZB LED della BR146 (priorità 0→5), stessa struttura Wechselblinken.
Soppressione PZB durante LZB Ü (requires_endpoint_false su ULightState).
Formazione 8 carri: EndCar-5, TransformerCar-6, ConverterCar-7, MiddleCar-8,
MiddleCar-3, ConverterCar-2, EndCar-0.

### ⚠️ ERRORI DA NON RIPETERE
1. `bIsPZB_Active` indica se il **sistema** PZB è attivo, NON quale modalità.
   Usato come mappatura LED accende **tutti e 3 i LED** → SBAGLIATO.
   Usare sempre `ActiveMode` (1/2/3) per determinare il singolo LED.

2. `bIsActivated` (LZB) indica che il **sistema** LZB è acceso, NON che sta frenando.
   Usato per LZB G → LED sempre acceso → SBAGLIATO.
   Usare `OverspeedState > 0` per rilevare l'intervento LZB (frenata/rallentamento).

## Tabella comparativa endpoint per treno

| Sistema | BR101 | Vectron | BR146.2 | BR114 | BR411 | BR406 |
|---------|-------|---------|---------|-------|-------|-------|
| PZB | `PZB_V3` | `PZB_Service_V3` | `PZB_Service_V2` | `PZB` | `PZB_Service_V3` | `PZB` |
| LZB | `LZB` | `LZB_Service` | `LZB_Service` | — | `LZB` | `LZB` |
| SIFA | `BP_Sifa_Service` | `BP_Sifa_Service` | `SIFA` | `BP_Sifa_Service` | `BP_Sifa_Service` | `IsSifaInEmergency` |
| MFA | `MFA_Indicators` | — | — | — | — | — |
| Porte | `PassengerDoorSelector` | `DoorLockSignal` | `DriverAssist.GetAreDoorsUnlocked` | `DriverAssist_F/B.GetAreDoorsUnlocked` | `DriverAssist.GetAreDoorsUnlocked` | `PassengerDoor_FL/FR/BL/BR` |

## Zusi 3

- TCP binary: Node/Attribute, header 4 bytes (ID uint16 + length uint16)
- Handshake: HELLO → ACK_HELLO → NEEDED_DATA → streaming
- Messaggio tipo 10 (Fahrpult) → TrainState dataclass → LED diretti
- Blink timer separato `_start_zusi3_blink_timer()`

## Bug noti risolti (per evitare regressioni)

1. **LED GUI fuori thread**: callback poller fuori main thread Tkinter → fix `root.after(0, ...)`
2. **Endpoint sbagliati BR101**: SIFA usava `bSifaPedalWarning` → `BP_Sifa_Service.Property.WarningStateVisual`
3. **detect_train()**: usava `get_raw` → `get` (estrae valore dal dict)
4. **PZB LED BR146 tutti accesi**: `bIsPZB_Active` → sostituito con `ActiveMode`
5. **Wechselblinken è corretto**: BLINK alternato 70↔85 in restricted è il comportamento reale PZB 90

## Diagnostica live

Per leggere lo stato PZB dal gioco in esecuzione:
```python
import requests
headers = {"DTGCommKey": open(r"path\to\CommAPIKey.txt").read().strip()}
base = "http://127.0.0.1:31270/get/"
influence = requests.get(base + "CurrentFormation/0/PZB_Service_V2.Function.Get_InfluenceState", headers=headers).json()
active_mode = requests.get(base + "CurrentFormation/0/PZB_Service_V2.Property.ActiveMode", headers=headers).json()
```
