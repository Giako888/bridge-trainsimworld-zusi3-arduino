"""
Configurazione e modelli dati
===============================
Definisce le mappature tra endpoint TSW6 e i 12 LED Charlieplexing
dell'Arduino Leonardo (sketch ArduinoJoystick.ino).

Ogni mappatura collega un dato TSW6 a un LED specifico con
una condizione di attivazione e un'azione (on/off o blink).
"""

import json
import os
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger("Config")

APP_NAME = "TSW6 Arduino Bridge"
APP_VERSION = "2.0.0"
CONFIG_DIR = Path(os.path.expanduser("~")) / ".tsw6_arduino_bridge"
CONFIG_FILE = CONFIG_DIR / "config.json"
PROFILES_DIR = CONFIG_DIR / "profiles"


# ============================================================
# Azioni LED
# ============================================================

class LedAction:
    """Tipo di azione sul LED quando la condizione Ã¨ vera"""
    ON = "on"             # Accendi
    OFF = "off"           # Spegni
    BLINK = "blink"       # Lampeggia (software, lato Python)


# ============================================================
# Condizioni
# ============================================================

class Condition:
    """Condizioni per attivare un'azione"""
    GREATER_THAN = ">"
    LESS_THAN = "<"
    EQUAL = "=="
    NOT_EQUAL = "!="
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    BETWEEN = "between"
    TRUE = "true"
    FALSE = "false"


ALL_CONDITIONS = [">", "<", "==", "!=", ">=", "<=", "between", "true", "false"]


# ============================================================
# Mappatura singola: TSW6 endpoint â†’ LED
# ============================================================

@dataclass
class LedMapping:
    """
    Una singola mappatura: dato TSW6 â†’ LED Arduino.

    Esempio: VelocitÃ  > 100 km/h â†’ accendi LED6 (500Hz, rosso)
    """
    name: str = "Nuova Mappatura"
    enabled: bool = True

    # Sorgente dati TSW6
    tsw6_endpoint: str = ""
    value_multiplier: float = 1.0   # es. 3.6 per m/s â†’ km/h
    value_offset: float = 0.0

    # Condizione
    condition: str = Condition.GREATER_THAN
    threshold: float = 0.0
    threshold_min: float = 0.0      # Per BETWEEN
    threshold_max: float = 1.0      # Per BETWEEN

    # LED target (nome dal dizionario LEDS in arduino_bridge)
    led_name: str = "SIFA"

    # Azione
    action: str = LedAction.ON          # on / off / blink
    blink_interval_sec: float = 1.0     # Intervallo blink in secondi

    def evaluate(self, value: Any) -> bool:
        """Valuta se la condizione Ã¨ soddisfatta"""
        try:
            val = float(value) * self.value_multiplier + self.value_offset
        except (TypeError, ValueError):
            if self.condition == Condition.TRUE:
                return bool(value)
            elif self.condition == Condition.FALSE:
                return not bool(value)
            return False

        if self.condition == Condition.GREATER_THAN:
            return val > self.threshold
        elif self.condition == Condition.LESS_THAN:
            return val < self.threshold
        elif self.condition == Condition.EQUAL:
            return abs(val - self.threshold) < 0.001
        elif self.condition == Condition.NOT_EQUAL:
            return abs(val - self.threshold) >= 0.001
        elif self.condition == Condition.GREATER_EQUAL:
            return val >= self.threshold
        elif self.condition == Condition.LESS_EQUAL:
            return val <= self.threshold
        elif self.condition == Condition.BETWEEN:
            return self.threshold_min <= val <= self.threshold_max
        elif self.condition == Condition.TRUE:
            return bool(val)
        elif self.condition == Condition.FALSE:
            return not bool(val)
        return False


# ============================================================
# Profilo
# ============================================================

@dataclass
class Profile:
    """Profilo di configurazione completo"""
    name: str = "Profilo Predefinito"
    description: str = ""
    train_class: str = ""

    # Lista di mappature (serializzate come dicts)
    mappings: List[dict] = field(default_factory=list)

    # Connessione TSW6
    tsw6_host: str = "127.0.0.1"
    tsw6_port: int = 31270
    tsw6_api_key: str = ""          # vuoto = auto-detect

    # Connessione Arduino
    arduino_port: str = ""          # vuoto = auto-detect

    # Polling
    poll_interval_ms: int = 100
    subscription_id: int = 1

    def get_mappings(self) -> List[LedMapping]:
        """Deserializza le mappature"""
        result = []
        for d in self.mappings:
            m = LedMapping(**{k: v for k, v in d.items() if k in LedMapping.__dataclass_fields__})
            result.append(m)
        return result

    def set_mappings(self, mappings: List[LedMapping]):
        """Serializza le mappature"""
        self.mappings = [asdict(m) for m in mappings]

    def get_tsw6_endpoints(self) -> List[str]:
        """Endpoint TSW6 unici usati nelle mappature attive"""
        eps = set()
        for m in self.get_mappings():
            if m.enabled and m.tsw6_endpoint:
                eps.add(m.tsw6_endpoint)
        return list(eps)


# ============================================================
# Template mappature predefinite
# ============================================================

def create_default_profile() -> Profile:
    """
    Profilo predefinito per BR101 (e treni tedeschi simili con PZB/LZB/SIFA).

    Usa gli endpoint verificati dal vivo con TSW6 External Interface API.
    Testato su BR101 il 14/02/2026.

    LOGICA IsActive + IsFlashing:
    Ogni spia MFA puÃ² essere accesa (IsActive) oppure lampeggiante (IsFlashing).
    Per ciascun LED che ha entrambe le varianti, creiamo DUE mappature:
    - IsActive  â†’ action=ON  (luce fissa)
    - IsFlashing â†’ action=BLINK (lampeggio)
    La GUI usa logica OR: basta che UNA sia True per accendere il LED.
    Se IsFlashing Ã¨ True, il LED lampeggia; se solo IsActive Ã¨ True, resta fisso.

    Varianti speciali:
    - 1000Hz ha anche IsFlashing_BP (Bremsprobe) oltre a IsFlashing_PZB
    - G e S hanno varianti sia _LZB che _PZB
    - 70 ha anche IsFlashing_Inverted e IsFlashing_Grunddaten
    """
    MFA = "CurrentFormation/0/MFA_Indicators.Property."

    mappings = [
        # =============================================
        # SIFA â€” Sicherheitsfahrschaltung (vigilanza)
        # =============================================
        LedMapping(
            name="SIFA Warning (Visual)",
            enabled=True,
            tsw6_endpoint="CurrentFormation/0/BP_Sifa_Service.Property.WarningStateVisual",
            condition=Condition.TRUE,
            led_name="SIFA",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
        ),

        # =============================================
        # PZB 1000Hz â€” Wachsam
        # =============================================
        LedMapping(
            name="1000Hz attivo (PZB)",
            enabled=True,
            tsw6_endpoint=MFA + "1000Hz_IsActive_PZB",
            condition=Condition.TRUE,
            led_name="1000HZ",
            action=LedAction.ON,
        ),
        LedMapping(
            name="1000Hz lampeggio (PZB)",
            enabled=True,
            tsw6_endpoint=MFA + "1000Hz_IsFlashing_PZB",
            condition=Condition.TRUE,
            led_name="1000HZ",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
        ),
        LedMapping(
            name="1000Hz lampeggio (BP/Bremsprobe)",
            enabled=True,
            tsw6_endpoint=MFA + "1000Hz_IsFlashing_BP",
            condition=Condition.TRUE,
            led_name="1000HZ",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
        ),        LedMapping(
            name="1000Hz lampeggio (Cutout)",
            enabled=True,
            tsw6_endpoint=MFA + "1000Hz_IsFlashing_Cutout",
            condition=Condition.TRUE,
            led_name="1000HZ",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
        ),
        LedMapping(
            name="1000Hz lampeggio (FaultIsolation)",
            enabled=True,
            tsw6_endpoint=MFA + "1000Hz_IsFlashing_FaultIsolation",
            condition=Condition.TRUE,
            led_name="1000HZ",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
        ),
        # =============================================
        # PZB 500Hz â€” Restriktiv (solo IsActive, nessun IsFlashing)
        # =============================================
        LedMapping(
            name="500Hz attivo",
            enabled=True,
            tsw6_endpoint=MFA + "500Hz_IsActive",
            condition=Condition.TRUE,
            led_name="500HZ",
            action=LedAction.ON,
        ),

        # =============================================
        # PZB 70 km/h
        # ATTENZIONE: B_IsActive = Befehl (comando), NON 70 km/h!
        # =============================================
        LedMapping(
            name="PZB 70 attivo",
            enabled=True,
            tsw6_endpoint=MFA + "70_IsActive_PZB",
            condition=Condition.TRUE,
            led_name="PZB70",
            action=LedAction.ON,
        ),
        LedMapping(
            name="PZB 70 attivo (TrainData)",
            enabled=True,
            tsw6_endpoint=MFA + "70_IsActive_TrainData",
            condition=Condition.TRUE,
            led_name="PZB70",
            action=LedAction.ON,
        ),
        LedMapping(
            name="PZB 70 lampeggio",
            enabled=True,
            tsw6_endpoint=MFA + "70_IsFlashing_PZB",
            condition=Condition.TRUE,
            led_name="PZB70",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
        ),
        LedMapping(
            name="PZB 70 lampeggio (Inverted)",
            enabled=True,
            tsw6_endpoint=MFA + "70_IsFlashing_Inverted",
            condition=Condition.TRUE,
            led_name="PZB70",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
        ),
        LedMapping(
            name="PZB 70 lampeggio (Grunddaten)",
            enabled=True,
            tsw6_endpoint=MFA + "70_IsFlashing_Grunddaten",
            condition=Condition.TRUE,
            led_name="PZB70",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
        ),

        # =============================================
        # PZB 85 â†’ LED PZB85
        # Usa 85_IsActive_PZB (endpoint specifico numerico),
        # coerente con 70_IsActive_PZB per PZB70.
        # =============================================
        LedMapping(
            name="PZB 85 attivo",
            enabled=True,
            tsw6_endpoint=MFA + "85_IsActive_PZB",
            condition=Condition.TRUE,
            led_name="PZB85",
            action=LedAction.ON,
        ),
        LedMapping(
            name="PZB 85 attivo (TrainData)",
            enabled=True,
            tsw6_endpoint=MFA + "85_IsActive_TrainData",
            condition=Condition.TRUE,
            led_name="PZB85",
            action=LedAction.ON,
        ),
        LedMapping(
            name="PZB 85 lampeggio",
            enabled=True,
            tsw6_endpoint=MFA + "85_IsFlashing_PZB",
            condition=Condition.TRUE,
            led_name="PZB85",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
        ),
        LedMapping(
            name="PZB 85 lampeggio (LZB)",
            enabled=True,
            tsw6_endpoint=MFA + "85_IsFlashing_LZB",
            condition=Condition.TRUE,
            led_name="PZB85",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
        ),
        LedMapping(
            name="PZB 85 lampeggio (Grunddaten)",
            enabled=True,
            tsw6_endpoint=MFA + "85_IsFlashing_Grunddaten",
            condition=Condition.TRUE,
            led_name="PZB85",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
        ),

        # =============================================
        # PZB 55 â†’ LED PZB55
        # Usa 55_IsActive_PZB (endpoint specifico numerico),
        # coerente con 70/85.
        # =============================================
        LedMapping(
            name="PZB 55 attivo",
            enabled=True,
            tsw6_endpoint=MFA + "55_IsActive_PZB",
            condition=Condition.TRUE,
            led_name="PZB55",
            action=LedAction.ON,
        ),
        LedMapping(
            name="PZB 55 attivo (TrainData)",
            enabled=True,
            tsw6_endpoint=MFA + "55_IsActive_TrainData",
            condition=Condition.TRUE,
            led_name="PZB55",
            action=LedAction.ON,
        ),
        LedMapping(
            name="PZB 55 lampeggio",
            enabled=True,
            tsw6_endpoint=MFA + "55_IsFlashing_PZB",
            condition=Condition.TRUE,
            led_name="PZB55",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
        ),
        LedMapping(
            name="PZB 55 lampeggio (Grunddaten)",
            enabled=True,
            tsw6_endpoint=MFA + "55_IsFlashing_Grunddaten",
            condition=Condition.TRUE,
            led_name="PZB55",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
        ),

        # =============================================
        # LZB Ende â†’ LED LZB
        # =============================================
        LedMapping(
            name="LZB Ende attivo",
            enabled=True,
            tsw6_endpoint=MFA + "Ende_IsActive",
            condition=Condition.TRUE,
            led_name="LZB",
            action=LedAction.ON,
        ),
        LedMapping(
            name="LZB Ende lampeggio",
            enabled=True,
            tsw6_endpoint=MFA + "Ende_IsFlashing",
            condition=Condition.TRUE,
            led_name="LZB",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
        ),

        # =============================================
        # LZB Ü (Überwachung) â†’ LED LZB_UE
        # =============================================
        LedMapping(
            name="LZB Ü attivo",
            enabled=True,
            tsw6_endpoint=MFA + "Ü_IsActive",
            condition=Condition.TRUE,
            led_name="LZB_UE",
            action=LedAction.ON,
        ),
        LedMapping(
            name="LZB Ü attivo (Test)",
            enabled=True,
            tsw6_endpoint=MFA + "Ü_IsActive_Test",
            condition=Condition.TRUE,
            led_name="LZB_UE",
            action=LedAction.ON,
        ),
        LedMapping(
            name="LZB Ü lampeggio",
            enabled=True,
            tsw6_endpoint=MFA + "Ü_IsFlashing",
            condition=Condition.TRUE,
            led_name="LZB_UE",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
        ),
        LedMapping(
            name="LZB Ü lampeggio (Test)",
            enabled=True,
            tsw6_endpoint=MFA + "Ü_IsFlashing_Test",
            condition=Condition.TRUE,
            led_name="LZB_UE",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
        ),
        LedMapping(
            name="LZB Ü lampeggio (LZB Fault)",
            enabled=True,
            tsw6_endpoint=MFA + "Ü_IsFlashing_LZB_Fault",
            condition=Condition.TRUE,
            led_name="LZB_UE",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
        ),

        # =============================================
        # LZB G (Grunddaten) â†’ LED LZB_G
        # =============================================
        LedMapping(
            name="LZB G attivo (LZB)",
            enabled=True,
            tsw6_endpoint=MFA + "G_IsActive_LZB",
            condition=Condition.TRUE,
            led_name="LZB_G",
            action=LedAction.ON,
        ),
        LedMapping(
            name="LZB G attivo (PZB)",
            enabled=True,
            tsw6_endpoint=MFA + "G_IsActive_PZB",
            condition=Condition.TRUE,
            led_name="LZB_G",
            action=LedAction.ON,
        ),
        LedMapping(
            name="LZB G lampeggio",
            enabled=True,
            tsw6_endpoint=MFA + "G_IsFlashing_LZB",
            condition=Condition.TRUE,
            led_name="LZB_G",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
        ),
        LedMapping(
            name="LZB G lampeggio (PZB)",
            enabled=True,
            tsw6_endpoint=MFA + "G_IsFlashing_PZB",
            condition=Condition.TRUE,
            led_name="LZB_G",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
        ),

        # =============================================
        # LZB S â†’ LED LZB_S
        # =============================================
        LedMapping(
            name="LZB S attivo (LZB)",
            enabled=True,
            tsw6_endpoint=MFA + "S_IsActive_LZB",
            condition=Condition.TRUE,
            led_name="LZB_S",
            action=LedAction.ON,
        ),
        LedMapping(
            name="LZB S attivo (PZB)",
            enabled=True,
            tsw6_endpoint=MFA + "S_IsActive_PZB",
            condition=Condition.TRUE,
            led_name="LZB_S",
            action=LedAction.ON,
        ),
        LedMapping(
            name="LZB S attivo (Test)",
            enabled=True,
            tsw6_endpoint=MFA + "S_IsActive_Test",
            condition=Condition.TRUE,
            led_name="LZB_S",
            action=LedAction.ON,
        ),
        LedMapping(
            name="LZB S lampeggio",
            enabled=True,
            tsw6_endpoint=MFA + "S_IsFlashing_LZB",
            condition=Condition.TRUE,
            led_name="LZB_S",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
        ),

        # =============================================
        # Porte â€” DoorLockSignal: True=bloccate, False=rilasciate
        # Quando DoorLockSignal Ã¨ FALSE â†’ porte rilasciate â†’ LED ON
        # Su BR101 Ã¨ un singolo segnale per entrambi i lati
        # =============================================
        LedMapping(
            name="Porte Sinistra (rilascio)",
            enabled=True,
            tsw6_endpoint="CurrentFormation/0.Property.DoorLockSignal",
            condition=Condition.FALSE,
            led_name="TUEREN_L",
            action=LedAction.ON,
        ),
        LedMapping(
            name="Porte Destra (rilascio)",
            enabled=True,
            tsw6_endpoint="CurrentFormation/0.Property.DoorLockSignal",
            condition=Condition.FALSE,
            led_name="TUEREN_R",
            action=LedAction.ON,
        ),
    ]

    profile = Profile(
        name="Profilo BR101 (PZB/LZB/SIFA)",
        description="Mappature per BR101 e treni tedeschi simili â€” usa indicatori MFA reali",
    )
    profile.set_mappings(mappings)
    return profile


# ============================================================
# Endpoint TSW6 comuni (per la GUI)
# ============================================================

COMMON_TSW6_ENDPOINTS = [
    {
        "category": "VelocitÃ  e Movimento",
        "endpoints": [
            ("CurrentDrivableActor.Function.HUD_GetSpeed", "VelocitÃ  (m/s)", "Ã—3.6 = km/h"),
            ("CurrentDrivableActor.Function.HUD_GetIsSlipping", "Slittamento ruote", "True/False"),
        ]
    },
    {
        "category": "Freni",
        "endpoints": [
            ("CurrentDrivableActor.Function.HUD_GetBrakeGauge_1", "Indicatore Freno 1", "0.0â€“1.0"),
            ("CurrentDrivableActor.Function.HUD_GetBrakeGauge_2", "Indicatore Freno 2", "0.0â€“1.0"),
        ]
    },
    {
        "category": "SIFA (Vigilanza)",
        "endpoints": [
            ("CurrentFormation/0.Property.bSifaPedalWarning", "SIFA Warning", "True/False"),
            ("CurrentFormation/0.Property.bSifaPedalPressed", "SIFA Pedale premuto", "True/False"),
            ("CurrentFormation/0.Function.IsSifaActive", "SIFA Attivo", "True/False"),
            ("CurrentFormation/0.Function.GetSifaEmergencyState", "SIFA Emergenza", "True/False"),
            ("CurrentFormation/0.Function.IsSifaCutIn", "SIFA Inserito", "True/False"),
        ]
    },
    {
        "category": "PZB / Indusi",
        "endpoints": [
            ("CurrentFormation/0.Property.PZB_Mode", "Modo PZB", "O/M/U"),
            ("CurrentFormation/0.Function.GetPZBMode", "Modo PZB (funzione)", "O/M/U"),
            ("CurrentFormation/0.Function.GetPZBEmergencyState", "PZB Emergenza", "True/False"),
            ("CurrentFormation/0.Function.GetIsPZBIsolated", "PZB Isolato", "True/False"),
        ]
    },
    {
        "category": "LZB",
        "endpoints": [
            ("CurrentFormation/0.Function.GetIsLZBIsolated", "LZB Isolato", "True/False"),
            ("CurrentFormation/0.Function.GetLZBEmergencyState", "LZB Emergenza", "True/False"),
        ]
    },
    {
        "category": "MFA Indicatori (spie pannello)",
        "endpoints": [
            ("CurrentFormation/0/MFA_Indicators.Property.Ü_IsActive", "Ü (Überwachung)", "True/False"),
            ("CurrentFormation/0/MFA_Indicators.Property.1000Hz_IsActive_PZB", "1000Hz PZB", "True/False"),
            ("CurrentFormation/0/MFA_Indicators.Property.500Hz_IsActive", "500Hz", "True/False"),
            ("CurrentFormation/0/MFA_Indicators.Property.B_IsActive", "B (Befehl)", "True/False"),
            ("CurrentFormation/0/MFA_Indicators.Property.H_IsActive", "H (Halt)", "True/False"),
            ("CurrentFormation/0/MFA_Indicators.Property.EL_IsActive", "EL", "True/False"),
            ("CurrentFormation/0/MFA_Indicators.Property.Ende_IsActive", "Ende", "True/False"),
            ("CurrentFormation/0/MFA_Indicators.Property.E40_IsActive", "E40", "True/False"),
            ("CurrentFormation/0/MFA_Indicators.Property.V40_IsActive", "V40", "True/False"),
            ("CurrentFormation/0/MFA_Indicators.Property.G_IsActive_LZB", "G (Grunddaten LZB)", "True/False"),
            ("CurrentFormation/0/MFA_Indicators.Property.G_IsActive_PZB", "G (Grunddaten PZB)", "True/False"),
            ("CurrentFormation/0/MFA_Indicators.Property.S_IsActive_LZB", "S (LZB)", "True/False"),
            ("CurrentFormation/0/MFA_Indicators.Property.S_IsActive_PZB", "S (PZB)", "True/False"),
            ("CurrentFormation/0/MFA_Indicators.Property.Stoer_IsActive_LZB", "StÃ¶rung LZB", "True/False"),
        ]
    },
    {
        "category": "Porte",
        "endpoints": [
            ("CurrentFormation/0.Property.DoorLockSignal", "Porte bloccate", "True/False"),
            ("CurrentFormation/0/PassengerDoorSelector_F.InputValue", "Selettore porte F", "0.0â€“1.0"),
            ("CurrentFormation/0/PassengerDoorSelector_B.InputValue", "Selettore porte B", "0.0â€“1.0"),
        ]
    },
    {
        "category": "Emergenza",
        "endpoints": [
            ("CurrentFormation/0.Function.GetSafetySystemEmergencyState", "Emergenza sicurezza", "True/False"),
            ("CurrentFormation/0.Function.GetEmergencyBrakeRequest", "Richiesta freno emergenza", "True/False"),
        ]
    },
    {
        "category": "VirtualRailDriver",
        "endpoints": [
            ("VirtualRailDriver.Throttle", "Regolatore", "0.0â€“1.0"),
            ("VirtualRailDriver.TrainBrake", "Freno Treno", "0.0â€“1.0"),
            ("VirtualRailDriver.LocoBrake", "Freno Locomotiva", "0.0â€“1.0"),
            ("VirtualRailDriver.Reverser", "Inversore", "-1.0 a 1.0"),
        ]
    },
    {
        "category": "Meteo",
        "endpoints": [
            ("WeatherManager.Temperature", "Temperatura", "Â°C"),
            ("WeatherManager.Cloudiness", "NuvolositÃ ", "0.0â€“1.0"),
            ("WeatherManager.Precipitation", "Precipitazioni", "0.0â€“1.0"),
            ("WeatherManager.FogDensity", "DensitÃ  Nebbia", "0.0â€“1.0"),
        ]
    },
]


# ============================================================
# Gestione salvataggio/caricamento
# ============================================================

class ConfigManager:
    """Gestisce salvataggio e caricamento di profili"""

    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        PROFILES_DIR.mkdir(parents=True, exist_ok=True)

    def save_profile(self, profile: Profile, filename: str = None) -> str:
        if filename is None:
            filename = profile.name.replace(" ", "_").lower() + ".json"
        filepath = PROFILES_DIR / filename
        data = asdict(profile)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Profilo salvato: {filepath}")
        return str(filepath)

    def load_profile(self, filepath: str) -> Profile:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        profile = Profile(**{k: v for k, v in data.items() if k in Profile.__dataclass_fields__})
        logger.info(f"Profilo caricato: {filepath}")
        return profile

    def list_profiles(self) -> List[Dict[str, str]]:
        profiles = []
        for f in PROFILES_DIR.glob("*.json"):
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                profiles.append({
                    "name": data.get("name", f.stem),
                    "description": data.get("description", ""),
                    "filepath": str(f),
                })
            except Exception as e:
                logger.warning(f"Errore lettura profilo {f}: {e}")
        return profiles

    def delete_profile(self, filepath: str):
        try:
            os.remove(filepath)
        except OSError as e:
            logger.error(f"Errore eliminazione: {e}")

    def save_app_config(self, config: dict):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def load_app_config(self) -> dict:
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
