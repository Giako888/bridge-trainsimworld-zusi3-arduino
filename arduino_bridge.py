"""
Arduino Serial Controller per TSW6
====================================
Comunica con Arduino Leonardo via seriale per controllare i 12 LED
Charlieplexing collegati all'hardware esistente (progetto arduino-train).

Lo sketch Arduino NON va modificato: è ArduinoJoystick.ino che gestisce
sia il joystick USB HID che i LED via comandi seriali.

Protocollo seriale (115200 baud):
- Ogni comando termina con newline (\\n), nessun wrapper <>
- Nessuna risposta/ACK (fire-and-forget)
- Cache stato per evitare invii duplicati

LED disponibili (Charlieplexing 4 pin, 12 LED):
  LED1  SIFA       giallo    → SIFA:0/1
  LED2  LZB Ende   giallo    → LZB:0/1
  LED3  PZB 70     blu       → PZB70:0/1
  LED4  PZB 85     blu       → PZB85:0/1
  LED5  PZB 55     blu       → PZB55:0/1
  LED6  500Hz      rosso     → 500HZ:0/1
  LED7  1000Hz     giallo    → 1000HZ:0/1
  LED8  Porte SX   giallo    → TUEREN_L:0/1
  LED9  Porte DX   giallo    → TUEREN_R:0/1
  LED10 LZB Ü      blu       → LZB_UE:0/1
  LED11 LZB G      blu       → LZB_G:0/1
  LED12 LZB S      rosso     → LZB_S:0/1

Comandi generici:
  LED:n:stato   (n=1-12, stato=0/1)
  OFF           (spegni tutti)
"""

import serial
import serial.tools.list_ports
import threading
import time
import logging
from typing import Optional, List, Dict, Callable
from dataclasses import dataclass

logger = logging.getLogger("ArduinoBridge")


# ============================================================
# Definizione dei 12 LED
# ============================================================

@dataclass(frozen=True)
class LedInfo:
    """Informazioni su un LED"""
    index: int          # 1-12
    name: str           # Nome breve (chiave)
    label: str          # Etichetta visualizzata
    color: str          # giallo, blu, rosso
    command: str        # Comando seriale (es. "SIFA")


# I 12 LED del controller — l'ordine segue lo sketch
LEDS: List[LedInfo] = [
    LedInfo(1,  "SIFA",     "SIFA Warning",              "giallo", "SIFA"),
    LedInfo(2,  "LZB",      "LZB Ende",                  "giallo", "LZB"),
    LedInfo(3,  "PZB70",    "PZB 70",                    "blu",    "PZB70"),
    LedInfo(4,  "PZB85",    "PZB 85",                    "blu",    "PZB85"),
    LedInfo(5,  "PZB55",    "PZB 55",                    "blu",    "PZB55"),
    LedInfo(6,  "500HZ",    "500 Hz",                    "rosso",  "500HZ"),
    LedInfo(7,  "1000HZ",   "1000 Hz",                   "giallo", "1000HZ"),
    LedInfo(8,  "TUEREN_L", "Porte Sinistra",            "giallo", "TUEREN_L"),
    LedInfo(9,  "TUEREN_R", "Porte Destra",              "giallo", "TUEREN_R"),
    LedInfo(10, "LZB_UE",   "LZB Ü Übertragung",        "blu",    "LZB_UE"),
    LedInfo(11, "LZB_G",    "LZB G aktiv",               "blu",    "LZB_G"),
    LedInfo(12, "LZB_S",    "LZB S Schnellbremsung",     "rosso",  "LZB_S"),
]

# Lookup rapidi
LED_BY_NAME: Dict[str, LedInfo] = {led.name: led for led in LEDS}
LED_BY_INDEX: Dict[int, LedInfo] = {led.index: led for led in LEDS}


# ============================================================
# Ricerca porte seriali
# ============================================================

def find_arduino_port() -> Optional[str]:
    """Trova automaticamente la porta dell'Arduino Leonardo"""
    for port in serial.tools.list_ports.comports():
        desc = (port.description or "").lower()
        if any(x in desc for x in ["arduino", "leonardo", "pro micro", "ch340", "cp210"]):
            return port.device
        if port.vid == 0x2341:   # Arduino
            return port.device
        if port.vid == 0x1B4F:   # SparkFun
            return port.device
    return None


def list_serial_ports() -> List[Dict[str, str]]:
    """Lista tutte le porte seriali disponibili"""
    return [
        {"port": p.device, "description": p.description or "Sconosciuto", "hwid": p.hwid or ""}
        for p in serial.tools.list_ports.comports()
    ]


# ============================================================
# Controller Arduino
# ============================================================

class ArduinoController:
    """
    Controller per Arduino Leonardo con 12 LED Charlieplexing.

    Uso:
        ctrl = ArduinoController()
        ctrl.connect()                 # auto-detect porta
        ctrl.set_led("SIFA", True)     # accendi SIFA
        ctrl.set_led("PZB70", False)   # spegni PZB 70
        ctrl.set_led_by_index(6, True) # LED 6 = 500Hz on
        ctrl.all_off()                 # spegni tutto
        ctrl.disconnect()
    """

    BAUD_RATE = 115200

    def __init__(self):
        self.serial: Optional[serial.Serial] = None
        self.connected = False
        self.port_name = ""

        # Cache stato (−1 = sconosciuto, evita invii duplicati)
        self._states: Dict[str, int] = {led.name: -1 for led in LEDS}

        # Thread lettura (per messaggi dall'Arduino, es. "OK:Joystick+Zusi Ready")
        self._running = False
        self._read_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Callbacks
        self.on_connect: Optional[Callable[[], None]] = None
        self.on_disconnect: Optional[Callable[[], None]] = None
        self.on_data: Optional[Callable[[str], None]] = None

        # Software blink (Arduino non ha BLINK command, lo gestiamo qui)
        self._blink_leds: Dict[str, float] = {}   # nome → intervallo_sec
        self._blink_thread: Optional[threading.Thread] = None

    # --------------------------------------------------------
    # Connessione
    # --------------------------------------------------------

    def connect(self, port: str = None) -> bool:
        """Connette all'Arduino. Auto-detect se port è None."""
        if self.connected:
            return True

        if port is None:
            port = find_arduino_port()

        if port is None:
            logger.warning("Arduino non trovato")
            return False

        try:
            self.serial = serial.Serial(port, self.BAUD_RATE, timeout=1)
            time.sleep(2)  # Attendi reset Arduino Leonardo

            self.connected = True
            self.port_name = port

            # Reset cache
            for name in self._states:
                self._states[name] = -1

            # Thread lettura
            self._running = True
            self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._read_thread.start()

            # Thread blink
            self._blink_thread = threading.Thread(target=self._blink_loop, daemon=True)
            self._blink_thread.start()

            logger.info(f"Arduino connesso su {port}")
            if self.on_connect:
                self.on_connect()
            return True

        except serial.SerialException as e:
            logger.error(f"Errore connessione Arduino: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """Disconnette dall'Arduino"""
        self._running = False
        self._blink_leds.clear()

        if self._read_thread:
            self._read_thread.join(timeout=2)
            self._read_thread = None
        if self._blink_thread:
            self._blink_thread.join(timeout=2)
            self._blink_thread = None

        if self.serial:
            try:
                self.all_off()
            except Exception:
                pass
            try:
                self.serial.close()
            except Exception:
                pass
            self.serial = None

        self.connected = False
        self.port_name = ""
        logger.info("Arduino disconnesso")
        if self.on_disconnect:
            self.on_disconnect()

    def is_connected(self) -> bool:
        return self.connected and self.serial is not None and self.serial.is_open

    # --------------------------------------------------------
    # Invio comandi
    # --------------------------------------------------------

    def _send(self, command: str):
        """Invia un comando raw all'Arduino (aggiunge \\n)"""
        if not self.is_connected():
            return
        try:
            with self._lock:
                self.serial.write(f"{command}\n".encode("utf-8"))
        except serial.SerialException as e:
            logger.error(f"Errore invio: {e}")
            self.connected = False

    # --------------------------------------------------------
    # Comandi LED
    # --------------------------------------------------------

    def set_led(self, name: str, on: bool):
        """
        Accende/spegne un LED per nome.

        Nomi validi: SIFA, LZB, PZB70, PZB85, PZB55, 500HZ, 1000HZ,
                     TUEREN_L, TUEREN_R, LZB_UE, LZB_G, LZB_S
        """
        led = LED_BY_NAME.get(name)
        if led is None:
            logger.warning(f"LED sconosciuto: {name}")
            return

        state = 1 if on else 0
        if self._states.get(name) == state:
            return  # Nessun cambiamento

        self._states[name] = state
        self._send(f"{led.command}:{state}")

    def set_led_by_index(self, index: int, on: bool):
        """Accende/spegne un LED per indice (1-12)"""
        led = LED_BY_INDEX.get(index)
        if led:
            self.set_led(led.name, on)

    def get_led_state(self, name: str) -> Optional[bool]:
        """Ritorna lo stato noto di un LED (None se sconosciuto)"""
        state = self._states.get(name, -1)
        if state == -1:
            return None
        return state == 1

    def all_off(self):
        """Spegni tutti i LED"""
        for name in self._states:
            self._states[name] = 0
        self._blink_leds.clear()
        self._send("OFF")

    # --------------------------------------------------------
    # Comandi singoli per ogni LED (API diretta)
    # --------------------------------------------------------

    def set_sifa(self, on: bool):
        """SIFA Warning (giallo)"""
        self.set_led("SIFA", on)

    def set_lzb(self, on: bool):
        """LZB Ende (giallo)"""
        self.set_led("LZB", on)

    def set_pzb70(self, on: bool):
        """PZB 70 (blu)"""
        self.set_led("PZB70", on)

    def set_pzb85(self, on: bool):
        """PZB 85 (blu)"""
        self.set_led("PZB85", on)

    def set_pzb55(self, on: bool):
        """PZB 55 (blu)"""
        self.set_led("PZB55", on)

    def set_500hz(self, on: bool):
        """500 Hz (rosso)"""
        self.set_led("500HZ", on)

    def set_1000hz(self, on: bool):
        """1000 Hz (giallo)"""
        self.set_led("1000HZ", on)

    def set_tueren_l(self, on: bool):
        """Porte Sinistra (giallo)"""
        self.set_led("TUEREN_L", on)

    def set_tueren_r(self, on: bool):
        """Porte Destra (giallo)"""
        self.set_led("TUEREN_R", on)

    def set_lzb_ue(self, on: bool):
        """LZB Ü Übertragung (blu)"""
        self.set_led("LZB_UE", on)

    def set_lzb_g(self, on: bool):
        """LZB G aktiv (blu)"""
        self.set_led("LZB_G", on)

    def set_lzb_s(self, on: bool):
        """LZB S Schnellbremsung (rosso)"""
        self.set_led("LZB_S", on)

    # --------------------------------------------------------
    # Software Blink (gestito lato Python)
    # --------------------------------------------------------

    def set_blink(self, name: str, interval_sec: float):
        """
        Fa lampeggiare un LED lato software.
        interval_sec = 0 → ferma lampeggio.
        """
        if interval_sec <= 0:
            self._blink_leds.pop(name, None)
        else:
            self._blink_leds[name] = interval_sec

    def stop_all_blinks(self):
        """Ferma tutti i lampeggi"""
        self._blink_leds.clear()

    def _blink_loop(self):
        """Thread che gestisce i lampeggi software"""
        toggle_state: Dict[str, bool] = {}
        last_toggle: Dict[str, float] = {}

        while self._running:
            now = time.monotonic()
            for name, interval in list(self._blink_leds.items()):
                last = last_toggle.get(name, 0)
                if now - last >= interval:
                    current = toggle_state.get(name, False)
                    new_state = not current
                    toggle_state[name] = new_state
                    last_toggle[name] = now
                    # Bypass cache per blink
                    led = LED_BY_NAME.get(name)
                    if led:
                        self._states[name] = 1 if new_state else 0
                        self._send(f"{led.command}:{1 if new_state else 0}")

            # PZB70 e PZB85 alternati: quando entrambi lampeggiano, PZB85 = opposto di PZB70
            if "PZB70" in self._blink_leds and "PZB85" in self._blink_leds:
                pzb70_on = toggle_state.get("PZB70", False)
                pzb85_should = not pzb70_on
                if toggle_state.get("PZB85") != pzb85_should:
                    toggle_state["PZB85"] = pzb85_should
                    led = LED_BY_NAME.get("PZB85")
                    if led:
                        self._states["PZB85"] = 1 if pzb85_should else 0
                        self._send(f"{led.command}:{1 if pzb85_should else 0}")

            time.sleep(0.05)

    # --------------------------------------------------------
    # Thread lettura
    # --------------------------------------------------------

    def _read_loop(self):
        """Legge messaggi dall'Arduino (es. 'OK:Joystick+Zusi Ready')"""
        while self._running and self.serial:
            try:
                if self.serial.in_waiting > 0:
                    line = self.serial.readline().decode("utf-8", errors="ignore").strip()
                    if line:
                        logger.debug(f"Arduino → {line}")
                        if self.on_data:
                            self.on_data(line)
                else:
                    time.sleep(0.02)
            except serial.SerialException:
                if self._running:
                    self.connected = False
                break
            except Exception as e:
                logger.error(f"Errore lettura seriale: {e}")
                time.sleep(0.1)

    # --------------------------------------------------------
    # Stato
    # --------------------------------------------------------

    @property
    def led_states(self) -> Dict[str, bool]:
        """Ritorna lo stato corrente di tutti i LED"""
        return {name: (state == 1) for name, state in self._states.items() if state >= 0}
