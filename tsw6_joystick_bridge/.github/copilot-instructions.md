# RailDriver Bridge - Istruzioni per AI

## Panoramica del Progetto

RailDriver Bridge è un sistema di emulazione joystick-to-RailDriver **solo per Windows** per Train Sim World 6. È composto da due componenti strettamente accoppiati che condividono un formato di configurazione comune.

### Architettura

```
┌─────────────────────────┐      ┌────────────────────────────┐
│  raildriver_bridge_gui.py │ ──> │  raildriver_bridge.ini     │
│  (GUI Python/Tkinter)     │      │  (formato config condiviso)│
└─────────────────────────┘      └────────────────────────────┘
                                           │
                                           ▼
┌─────────────────────────────────────────────────────────────┐
│  RailDriver.dll (DLL C - proxy delle API RailDriver reali)  │
│  Esporta: RailDriverInit, GetRailSimValue, ecc.             │
│  Legge joystick via winmm.dll, applica mappatura da .ini    │
└─────────────────────────────────────────────────────────────┘
```

## Componenti Principali

### GUI Python (`raildriver_bridge_gui.py`)
- **Framework**: Tkinter con `ttk` (tema Windows Vista)
- **I/O Joystick**: pygame o pygame-ce (gestisce il fallback automaticamente)
- **Classi principali**: `JoystickManager` (polling joystick), `RailDriverBridgeApp` (GUI principale)
- **Strutture dati**: dataclass `JoystickProfile`, `AxisMapping`, `ButtonMapping`

### DLL C (`dll_source/PieHid64_Bridge.c`)
- **Emula PieHid64.dll**: La libreria PIE HID usata dal RailDriver fisico
- **Autocontenuta**: Tutte le definizioni Windows API inline (non richiede SDK headers)
- **API Joystick**: Caricata a runtime da `winmm.dll` usando `GetProcAddress`
- **Filtro anti-spike**: Media mobile con rilevamento spike (struct `AxisFilter`)
- **Deve esportare**: Funzioni in `PieHid64.def` con ordinal specifici (EnumeratePIE, ReadData, ecc.)

### Protocollo RailDriver HID
Il RailDriver comunica via report HID di 8 byte:
```
Byte 0: Report ID (0x00)
Byte 1: Reverser (0-255, 127=centro)
Byte 2: Throttle (0-255)
Byte 3: Auto Brake (0-255)
Byte 4: Independent Brake
Byte 5: Bail Off / Wiper
Byte 6: Lights
Byte 7: Buttons bitmask
```

## Formato Configurazione (`.ini`)

```ini
[General]
JoystickIndex=0

[Axes]
reverser=0,0,0.05     # indice_asse,invertito(0/1),deadzone
throttle=1,0,0.05

[Buttons]
0=5,0                  # pulsante_raildriver=pulsante_joystick,toggle(0/1)
```

**Importante**: Gli indici degli assi corrispondono a:
- 0=reverser, 1=throttle, 2=auto_brake, 3=indep_brake, 4=bail_off, 5=wiper, 6=lights

## Workflow di Build

### Build completa (crea EXE + DLL + pacchetto distribuzione):
```bat
build_all.bat
```

### Solo GUI (PyInstaller):
```bash
python build_exe.py
```

### Solo DLL (da `dll_source/`):
```bash
# MinGW (consigliato)
gcc -shared -o PieHid64.dll PieHid64_Bridge.c PieHid64.def -lwinmm -Wl,--kill-at

# Oppure con script
build_piehid.bat
```

**IMPORTANTE**: La DLL deve chiamarsi `PieHid64.dll` (non RailDriver.dll) e deve esportare le funzioni con gli ordinal corretti definiti in `PieHid64.def`.

## Convenzioni del Codice

### Python
- **Commenti/stringhe in italiano**: Label UI e docstring sono in italiano
- **Callback con prefisso**: `_on_*` per event handler, `_create_*` per costruttori UI
- **Flusso mappatura**: Utente clicca "Mappa" → rilevamento asse/pulsante → validazione anti-spike

### C
- **Logging**: Usare funzione `Log()` - scrive su `raildriver_bridge.log`
- **Anti-spike**: Tutte le letture assi passano per `FilterAxisValue()` prima dell'uso
- **Percorsi config**: Controlla sia directory DLL che directory di lavoro per `.ini`

## Pattern Critici

### Rilevamento Assi Anti-Spike (GUI)
Durante la mappatura assi, la GUI richiede movimento sostenuto sopra soglia per evitare falsi positivi:
```python
# In _on_joystick_update(): richiede movement > MAPPING_THRESHOLD (0.7)
# E l'asse deve avere 2x più movimento degli altri assi
if best_movement > other_movement * 2:
    self.axis_vars[self.mapping_axis]['joystick_axis'].set(best_axis)
```

### Convenzione Export DLL
Tutte le funzioni esportate devono usare calling convention `__cdecl`:
```c
__declspec(dllexport) float __cdecl GetRailSimValue(int index, int valueType);
```

### Thread Safety
- La GUI esegue il polling joystick nel main thread via callback `root.after()`
- La DLL è single-threaded (chiamata dal main thread del gioco)

## Testing

1. **Test GUI**: Eseguire `python raildriver_bridge_gui.py` con joystick connesso
2. **Test DLL**: Copiare DLL + `.ini` nella directory TSW6, controllare `raildriver_bridge.log`
3. **Tab Monitor**: Visualizzazione real-time assi/pulsanti per debug mappature

## Dipendenze

- **Python**: pygame>=2.5.0 OPPURE pygame-ce, pyinstaller>=6.0.0
- **Compilazione C**: TCC, MinGW, o MSVC (qualsiasi funziona)
- **Runtime**: Solo Windows (usa winmm.dll per API joystick)
