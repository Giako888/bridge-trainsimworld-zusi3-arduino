# TSW6 Arduino Bridge — Contesto per GitHub Copilot

> Apri questo file e incollalo come primo messaggio in una nuova sessione Copilot
> per riprendere il lavoro esattamente da dove è stato lasciato.

---

## Progetto

**TSW6 Arduino Bridge** — Applicazione Python/Tkinter che legge dati in tempo reale
da Train Sim World 6 (TSW6) tramite le sue HTTP API e li invia ad un Arduino Leonardo
per controllare 12 LED fisici (Charlieplexing) che replicano le spie del pannello MFA
di un treno tedesco (PZB/SIFA/LZB).

### File principali

| File | Scopo |
|------|-------|
| `tsw6_api.py` | Client HTTP per TSW6 API (porta 31270) + classe TSW6Poller (polling GET) |
| `tsw6_arduino_gui.py` | GUI Tkinter principale, 3 tab: Connessione, Mappature, Scopri Endpoint |
| `arduino_bridge.py` | ArduinoController — comunicazione seriale con Arduino Leonardo (12 LED) |
| `config_models.py` | Modelli dati: LedMapping, Profile, ConfigManager, mappature predefinite |
| `extracted_endpoints_final.txt` | Lista curata di endpoint TSW6 utili |
| `tsw6_endpoints.json` | Dump completo di ~81.000 endpoint TSW6 (486K righe) |

### Stack tecnologico
- Python 3.14.3, Windows 11
- `requests` + `urllib3` (HTTP con retry)
- `tkinter` (GUI)
- `pyserial` (Arduino)
- `PyInstaller` (compilazione EXE)
- Arduino Leonardo (ATmega32U4), Charlieplexing 4 pin → 12 LED, Serial 115200 baud

---

## TSW6 External Interface API — Punti critici

### Formato risposta (IMPORTANTE!)

TSW6 API (porta 31270) ritorna risposte in questo formato:

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
Il valore effettivo è dentro `Values` come `{"Value": true}` oppure `{"NomeProprietà": valore}`.
Per estrarlo: `list(result["Values"].values())[0]`

### Formato subscription

```json
GET /subscription?Subscription=1

{
  "Entries": [
    {
      "Values": {"Value": true},
      "NodeValid": true
    },
    ...
  ]
}
```

### URL encoding dei path

I path con caratteri speciali DEVONO essere URL-encoded segmento per segmento:
- `Ü` → `%C3%9C` (es. `Ü_IsActive` → `%C3%9C_IsActive`)
- `(` → `%28`, `)` → `%29` (es. `Throttle(Lever)` → `Throttle%28Lever%29`)
- Separatori `/` e `.` NON vanno codificati

La funzione `encode_path()` in `tsw6_api.py` gestisce questo.

### CommAPIKey

File: `Documents\My Games\TrainSimWorld6\Saved\Config\CommAPIKey.txt`
Header HTTP: `DTGCommKey: <chiave>`
Senza chiave → 403 Forbidden.

---

## 12 LED e mappature predefinite (aggiornate 14/02/2026 — IsActive + IsFlashing)

Ogni LED MFA ha fino a 2 mappature: `IsActive` (ON fisso) + `IsFlashing` (BLINK).
Logica OR con priorità **BLINK > ON > OFF**: se una mappatura IsFlashing è True, il LED
lampeggia anche se IsActive è False.

| LED | Nome | Endpoint IsActive | Endpoint IsFlashing | Note |
|-----|------|-------------------|---------------------|------|
| 1 | SIFA | `BP_Sifa_Service.Property.WarningStateVisual` | — | BLINK 0.5s (segnale visivo) |
| 2 | LZB | `MFA..Ende_IsActive` | `MFA..Ende_IsFlashing` | Ende = LZB termine |
| 3 | PZB70 | `MFA..70_IsActive_PZB` | `MFA..70_IsFlashing_PZB` | Pattern numerico |
| 4 | PZB85 | `MFA..85_IsActive_PZB` | `MFA..85_IsFlashing_PZB` | Pattern numerico (NON B_IsActive/H_IsActive) |
| 5 | PZB55 | `MFA..55_IsActive_PZB` | `MFA..55_IsFlashing_PZB` | Pattern numerico (NON EL_IsActive) |
| 6 | 500HZ | `MFA..500Hz_IsActive` | — | Nessuna variante IsFlashing |
| 7 | 1000HZ | `MFA..1000Hz_IsActive_PZB` | `MFA..1000Hz_IsFlashing_PZB` + `..._BP` | 3 mappature totali (OR) |
| 8 | TUEREN_L | `PassengerDoorSelector_F.Function.GetCurrentOutputValue` | — | ⚠️ NON usare InputValue (0.5 sempre) |
| 9 | TUEREN_R | `PassengerDoorSelector_R.Function.GetCurrentOutputValue` | — | |
| 10 | LZB_UE | `MFA..Ü_IsActive` | `MFA..Ü_IsFlashing` | Ü = Überwachung |
| 11 | LZB_G | `MFA..G_IsActive_LZB` + `..._PZB` | `MFA..G_IsFlashing_LZB` + `..._PZB` | 4 mappature (LZB+PZB, OR) |
| 12 | LZB_S | `MFA..S_IsActive_LZB` + `..._PZB` | `MFA..S_IsFlashing_LZB` | 3 mappature (OR) |

`MFA..` = `CurrentFormation/0/MFA_Indicators.Property.`
Totale: **24 mappature** per 12 LED (era 13 mappature prima dell'aggiornamento IsFlashing).

---

## Stato attuale e problemi

### ✅ Cosa funziona
- Connessione a TSW6 (auto-detect CommAPIKey o inserimento manuale)
- Polling GET di tutti gli endpoint — tutti rispondono correttamente
- Il parsing `"Values"` è corretto
- L'URL encoding funziona (Ü, parentesi ecc.)
- Compilazione EXE con PyInstaller
- **LED GUI si aggiornano correttamente** (fix thread-safety)
- **Logica OR con priorità BLINK > ON > OFF** per LED con endpoint multipli
- **IsActive + IsFlashing dual mapping** per tutti i LED MFA (24 mappature totali)
- **Blink dinamico**: `_gui_led_blink` dict traccia in tempo reale quali LED devono lampeggiare
- **Endpoint corretti verificati dal vivo con TSW6 su BR101 (14/02/2026)**

### ✅ Bug risolto: LED GUI non si aggiornavano (14/02/2026)

**Causa principale trovata**: la funzione callback `_on_tsw6_data` veniva chiamata
direttamente dal thread del poller (tsw6_api.py riga 831), **NON dal main thread Tkinter**.

**Fix applicati**:

1. **Thread-safety callback**: Il callback del poller ora è wrappato con `root.after(0, ...)`:
   ```python
   def on_tsw6_data_threadsafe(data):
       self.root.after(0, lambda d=data: self._on_tsw6_data(d))
   self.poller.add_callback(on_tsw6_data_threadsafe)
   ```
   Così `_on_tsw6_data()` gira nel main thread Tkinter, come gli altri callback.

2. **Blink visivo GUI**: Aggiunto supporto blink per i LED con `action=BLINK` (SIFA, LZB).
   Il `_update_led_indicators()` ora alterna la fase blink ogni 200ms usando
   `_blink_phase` e una `_led_action_cache` che mappa i nomi LED con azione blink.

3. **Diagnostica migliorata**: Al primo ciclo di dati, il debug panel ora mostra:
   - `📦 Data keys`: le chiavi effettive ricevute dal poller
   - `📋 Mapping endpoints`: gli endpoint configurati nelle mappature
   - `⚠️ No match per ...`: endpoint che non matchano (diagnosi istantanea)
   - `💡 LED update #N`: conferma che il loop di update gira e quali LED sono ON

4. **Reset contatori**: Quando il bridge si ferma, i contatori diagnostici e gli
   stati LED vengono resettati per il prossimo avvio pulito.

### ✅ Bug risolto: endpoint sbagliati nelle mappature predefinite (14/02/2026)

**Problema**: testando dal vivo con TSW6 + BR101, 4 mappature su 12 avevano endpoint errati:

| LED | Endpoint SBAGLIATO | Valore API | Stato reale | Endpoint CORRETTO |
|-----|-------------------|-----------|-------------|-------------------|
| SIFA | `bSifaPedalWarning` | False | **ON** | `BP_Sifa_Service.Property.WarningStateVisual` |
| 1000Hz | solo `1000Hz_IsActive_PZB` | False | **ON** | + `1000Hz_IsFlashing_BP` (OR) |
| PZB70 | `B_IsActive` (Befehl!) | True | **OFF** | `70_IsActive_PZB` |
| TUEREN_L | `PassengerDoorSelector_F.InputValue` | 0.5 (sempre!) | **OFF** | `...Function.GetCurrentOutputValue` |

**Fix applicati**:
1. SIFA → `BP_Sifa_Service.Property.WarningStateVisual` (stato visivo del warning SIFA)
2. 1000Hz → due mappature (IsActive_PZB + IsFlashing_BP) con logica OR per stesso LED
3. PZB70 → `70_IsActive_PZB` (B_IsActive è Befehl/comando, non 70 km/h!)
4. TUEREN_L → `GetCurrentOutputValue` (OutputValue=0 quando neutro, InputValue=0.5 sempre)
5. Aggiunta logica OR in `_on_tsw6_data`: se più mappature puntano allo stesso LED,
   basta che UNA valuti True per accenderlo (usa `led_accumulator` dict)

### ✅ IsFlashing dual mapping per tutti i LED MFA (14/02/2026)

**Problema**: i LED MFA hanno sia `IsActive` (accesione fissa) che `IsFlashing` (lampeggio).
Servono entrambe le varianti per replicare il comportamento reale del pannello.

**Architettura implementata**:

1. **config_models.py**: `create_default_profile()` ora genera **24 mappature** (era 13):
   - Ogni LED MFA ha una mappatura `IsActive` con `action=ON` e una `IsFlashing` con `action=BLINK`
   - LZB_G ha 4 mappature (LZB+PZB × Active+Flashing), 1000Hz ne ha 3, ecc.

2. **_on_tsw6_data()**: Logica accumulator con priorità **BLINK > ON > OFF**:
   - `led_accumulator: Dict[str, str]` tiene "blink"/"on"/"off" per ogni LED
   - BLINK ha sempre la priorità (non viene mai declassato a ON)
   - Alla fine, setta `_gui_led_states[led]` e `_gui_led_blink[led]` 

3. **_gui_led_blink: Dict[str, bool]**: Nuovo dict in `__init__`, traccia dinamicamente
   quali LED stanno lampeggiando. Rimpiazza il vecchio `_led_action_cache` statico.

4. **_send_led_to_arduino(led_name, led_on, is_blink)**: Nuovo parametro `is_blink`.
   Se `is_blink and led_on` → `set_blink(interval)`, altrimenti → `set_led(on/off)`.

5. **_update_led_indicators()**: Usa `_gui_led_blink.get(name, False)` per decidere
   se alternare il colore del cerchietto. Non più cache statica.

### ✅ GUI testata e porte verificate (15/02/2026)

- **GUI completa testata** con il bridge avviato — cerchietti LED funzionanti
- **Porte verificate** — TUEREN_L/R funzionano correttamente nel gioco

### ❌ Ancora da verificare

- **Arduino fisico**: testare la comunicazione seriale con l'Arduino collegato

---

## Progetto di riferimento: Trenino

https://github.com/albertorestifo/trenino — Progetto Elixir/Phoenix simile al nostro.
Ha rivelato il formato corretto delle risposte TSW6 API (`"Values"` non `"Value"`).

Punti chiave da Trenino:
- Usa `Req` con retry `:transient`, pool_timeout 5000ms, receive_timeout 10000ms
- `encode_path()` per URL-encoding dei segmenti
- Subscription con `POST /subscription/{path}?Subscription=id` (body vuoto)
- Lettura con `GET /subscription?Subscription=id`
- Risposta entries: `{"Entries": [{"Values": {...}, "NodeValid": true}]}`
- Poll interval 200ms per le subscription
- Condizioni: eq_true, eq_false, gt, lt, between

---

## Comandi utili

```powershell
# Compilare EXE
cd c:\Users\Postazione-Giako\progetto2\tsw6_joystick_bridge
python -m PyInstaller --onefile --noconsole --name TSW6_Arduino_Bridge tsw6_arduino_gui.py

# Test diretto API TSW6 (PowerShell)
$headers = @{"DTGCommKey" = "<API_KEY>"}
Invoke-RestMethod -Uri "http://127.0.0.1:31270/info" -Headers $headers
Invoke-RestMethod -Uri "http://127.0.0.1:31270/get/CurrentFormation/0/MFA_Indicators.Property.B_IsActive" -Headers $headers

# Avviare GUI da sorgente
python tsw6_arduino_gui.py
```

---

## Prossimi passi

1. ~~**Avviare la GUI** e verificare i LED nella UI con il gioco attivo~~ ✅
2. **Testare con Arduino collegato** — Verificare comunicazione seriale e accensione LED fisici
3. ~~**Verificare porte** — Rilasciare le porte nel gioco e controllare TUEREN_L/R~~ ✅
4. **Opzionale**: passare a subscription mode invece di GET individuali (più efficiente)
5. **Opzionale**: aggiungere supporto per altri treni (diversi percorsi MFA_Indicators)
