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

APP_NAME = "Train Simulator Bridge"
APP_VERSION = "3.6.0.0"


# ============================================================
# Selezione Simulatore
# ============================================================

class SimulatorType:
    """Tipo di simulatore collegato"""
    TSW6 = "TSW6"
    ZUSI3 = "Zusi3"
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
    priority: int = 0                   # Priorità mappatura (più alto vince)
    requires_endpoint: str = ""          # Se impostato, la mappatura si attiva solo se anche questo endpoint è True
    requires_endpoint_false: str = ""     # Se impostato, la mappatura si attiva solo se questo endpoint è False
    value_key: str = ""                   # Se impostato, estrai questo campo dal dict di risposta (match parziale)

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
        # SIFA — Sicherheitsfahrschaltung (vigilanza)
        # Warning visivo → fisso ON
        # Penalità (frenata emergenza) → fisso ON (stessa azione, priority più alta)
        # Il LED SIFA si accende fisso in entrambi i casi.
        # =============================================
        LedMapping(
            name="SIFA Warning (Visual)",
            enabled=True,
            tsw6_endpoint="CurrentFormation/0/BP_Sifa_Service.Property.WarningStateVisual",
            condition=Condition.TRUE,
            led_name="SIFA",
            action=LedAction.ON,
            priority=0,
        ),
        LedMapping(
            name="SIFA Penalità (Frenata)",
            enabled=True,
            tsw6_endpoint="CurrentFormation/0/BP_Sifa_Service.Property.inPenaltyBrakeApplication",
            condition=Condition.TRUE,
            led_name="SIFA",
            action=LedAction.ON,
            priority=10,
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
            requires_endpoint=MFA + "IsBelowGrunddatenSpeed",
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
            requires_endpoint=MFA + "IsBelowGrunddatenSpeed",
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
            requires_endpoint=MFA + "IsBelowGrunddatenSpeed",
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
        name="Profilo BR101 (Expert) (PZB/LZB/SIFA)",
        description="Mappature per BR101 (Expert) e treni tedeschi simili — usa indicatori MFA reali",
        train_class="BR101",
    )
    profile.set_mappings(mappings)
    return profile


def create_br101_profile() -> Profile:
    """Alias: create_default_profile ≡ profilo BR101"""
    return create_default_profile()


# ============================================================
# Profilo Vectron DB
# ============================================================

def create_vectron_profile() -> Profile:
    """
    Profilo per DB Vectron (RVM_FTF_DB_Vectron_C).

    Il Vectron NON ha il pannello MFA_Indicators.
    Usa endpoint diversi dalla BR101:
      - PZB_Service_V3 (invece di PZB_V3)
      - LZB_Service (invece di LZB)
      - BP_Sifa_Service (identico alla BR101)

    Gli stati PZB 1000Hz/500Hz/2000Hz vengono dalla Function
    Get_InfluenceState tramite value_key per estrarre i singoli flag.
    Gli stati LZB usano le Property numeriche (ULightState, EndeState, ecc.)
    """
    PZB_FN = "CurrentFormation/0/PZB_Service_V3.Function."
    PZB_PR = "CurrentFormation/0/PZB_Service_V3.Property."
    LZB_PR = "CurrentFormation/0/LZB_Service.Property."

    mappings = [
        # =============================================
        # SIFA (identica alla BR101)
        # =============================================
        LedMapping(
            name="SIFA Warning (Visual)",
            enabled=True,
            tsw6_endpoint="CurrentFormation/0/BP_Sifa_Service.Property.WarningStateVisual",
            condition=Condition.TRUE,
            led_name="SIFA",
            action=LedAction.ON,
        ),
        LedMapping(
            name="SIFA Penalità (Frenata)",
            enabled=True,
            tsw6_endpoint="CurrentFormation/0/BP_Sifa_Service.Property.inPenaltyBrakeApplication",
            condition=Condition.TRUE,
            led_name="SIFA",
            action=LedAction.ON,
            priority=10,
        ),

        # =============================================
        # PZB 1000Hz — da Get_InfluenceState
        # =============================================
        LedMapping(
            name="1000Hz attivo (PZB)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "Get_InfluenceState",
            condition=Condition.TRUE,
            led_name="1000HZ",
            action=LedAction.ON,
            value_key="1000Hz_Active",
        ),

        # =============================================
        # PZB 500Hz — da Get_InfluenceState
        # =============================================
        LedMapping(
            name="500Hz attivo (PZB)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "Get_InfluenceState",
            condition=Condition.TRUE,
            led_name="500HZ",
            action=LedAction.ON,
            value_key="500Hz_Active",
        ),

        # =============================================
        # PZB 85 — attivato da 1000Hz
        # =============================================
        LedMapping(
            name="PZB 85 attivo (1000Hz)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "Get_InfluenceState",
            condition=Condition.TRUE,
            led_name="PZB85",
            action=LedAction.ON,
            value_key="1000Hz_Active",
        ),
        LedMapping(
            name="PZB 85 restrizione",
            enabled=True,
            tsw6_endpoint=PZB_FN + "Get_InfluenceState",
            condition=Condition.TRUE,
            led_name="PZB85",
            action=LedAction.ON,
            value_key="isRestricted",
        ),
        LedMapping(
            name="PZB 85 lampeggio (emergenza)",
            enabled=True,
            tsw6_endpoint=PZB_PR + "_InEmergency",
            condition=Condition.TRUE,
            led_name="PZB85",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
            priority=5,
        ),

        # =============================================
        # PZB 70 — attivato da 500Hz
        # =============================================
        LedMapping(
            name="PZB 70 attivo (500Hz)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "Get_InfluenceState",
            condition=Condition.TRUE,
            led_name="PZB70",
            action=LedAction.ON,
            value_key="500Hz_Active",
        ),

        # =============================================
        # PZB 55 — attivato da 2000Hz
        # =============================================
        LedMapping(
            name="PZB 55 attivo (2000Hz)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "Get_InfluenceState",
            condition=Condition.TRUE,
            led_name="PZB55",
            action=LedAction.ON,
            value_key="2000Hz_Active",
        ),

        # =============================================
        # LZB Ende — EndeState > 0
        # EndeState 1 = lampeggio (attesa conferma), 2 = fisso (confermato)
        # =============================================
        LedMapping(
            name="LZB Ende attivo",
            enabled=True,
            tsw6_endpoint=LZB_PR + "EndeState",
            condition=Condition.GREATER_THAN,
            threshold=0,
            led_name="LZB",
            action=LedAction.ON,
        ),
        LedMapping(
            name="LZB Ende lampeggio (attesa conferma)",
            enabled=True,
            tsw6_endpoint=LZB_PR + "EndeState",
            condition=Condition.EQUAL,
            threshold=1,
            led_name="LZB",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
            priority=1,
        ),

        # =============================================
        # LZB Ü — ULightState > 0
        # =============================================
        LedMapping(
            name="LZB Ü attivo",
            enabled=True,
            tsw6_endpoint=LZB_PR + "ULightState",
            condition=Condition.GREATER_THAN,
            threshold=0,
            led_name="LZB_UE",
            action=LedAction.ON,
        ),
        LedMapping(
            name="LZB Ü lampeggio (fault)",
            enabled=True,
            tsw6_endpoint=LZB_PR + "FaultCode",
            condition=Condition.GREATER_THAN,
            threshold=0,
            led_name="LZB_UE",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
            priority=3,
        ),

        # =============================================
        # Porte
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

    # Quando LZB Ü è attivo (ULightState > 0), i LED PZB devono spegnersi
    _pzb_leds = {"PZB85", "PZB70", "PZB55", "1000HZ", "500HZ"}
    for m in mappings:
        if m.led_name in _pzb_leds:
            m.requires_endpoint_false = LZB_PR + "ULightState"

    profile = Profile(
        name="Profilo Vectron DB (PZB/LZB/SIFA)",
        description="DB Vectron — PZB_Service_V3, LZB_Service, senza pannello MFA",
        train_class="Vectron",
    )
    profile.set_mappings(mappings)
    return profile


# ============================================================
# Profilo Bpmmbdzf (Cab Car)
# ============================================================

def create_bpmmbdzf_profile() -> Profile:
    """
    Profilo per Bpmmbdzf (carrozza pilota).
    Usa gli stessi endpoint MFA della BR101 perché condivide
    i sistemi di sicurezza con la locomotiva.
    """
    profile = create_default_profile()
    profile.name = "Profilo Bpmmbdzf (Expert) (Cab Car)"
    profile.description = "Carrozza pilota Bpmmbdzf — stessi indicatori MFA della BR101 (Expert)"
    profile.train_class = "Bpmmbdzf"
    return profile


# ============================================================
# Profilo DB BR 146.2
# ============================================================

def create_br146_profile() -> Profile:
    """
    Profilo per DB BR 146.2 (RVM_DRA_DB_BR146-2_C).

    La BR146.2 NON ha il pannello MFA_Indicators.
    Usa endpoint diversi dalla BR101 e dal Vectron:
      - PZB_Service_V2 (invece di PZB_V3 sulla BR101 o PZB_Service_V3 sul Vectron)
      - LZB_Service (come il Vectron)
      - SIFA (componente diretto, non BP_Sifa_Service)
      - Porte: DriverAssist.Function.GetAreDoorsUnlocked

    Differenze PZB rispetto alla BR101:
      - In restricted mode, il limite scende a ~45 km/h (non 85)
        → PZB85 lampeggia (BLINK) durante restricted mode
      - Non alterna PZB85/70 come la BR101
      - Finestra Wachsam (4s per confermare): 1000HZ lampeggia

    Gli stati PZB 1000Hz/500Hz/2000Hz vengono dalla Function
    Get_InfluenceState tramite value_key per estrarre i singoli flag.
    """
    PZB_FN = "CurrentFormation/0/PZB_Service_V2.Function."
    PZB_PR = "CurrentFormation/0/PZB_Service_V2.Property."
    LZB_PR = "CurrentFormation/0/LZB_Service.Property."

    mappings = [
        # =============================================
        # SIFA — componente diretto "SIFA"
        # =============================================
        LedMapping(
            name="SIFA Warning",
            enabled=True,
            tsw6_endpoint="CurrentFormation/0/SIFA.Function.isWarningState",
            condition=Condition.TRUE,
            led_name="SIFA",
            action=LedAction.ON,
        ),
        LedMapping(
            name="SIFA Emergenza (Frenata)",
            enabled=True,
            tsw6_endpoint="CurrentFormation/0/SIFA.Function.InEmergency",
            condition=Condition.TRUE,
            led_name="SIFA",
            action=LedAction.BLINK,
            blink_interval_sec=0.5,
            priority=10,
        ),

        # =============================================
        # PZB 1000Hz — da Get_InfluenceState
        # Fisso ON durante monitoraggio, BLINK durante
        # finestra Wachsam (acknowledge richiesto)
        # =============================================
        LedMapping(
            name="1000Hz attivo (PZB)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "Get_InfluenceState",
            condition=Condition.TRUE,
            led_name="1000HZ",
            action=LedAction.ON,
            value_key="1000Hz_Active",
        ),
        LedMapping(
            name="1000Hz Wachsam (conferma richiesta)",
            enabled=True,
            tsw6_endpoint=PZB_PR + "_RequiresAcknowledge",
            condition=Condition.TRUE,
            led_name="1000HZ",
            action=LedAction.BLINK,
            blink_interval_sec=0.5,
            priority=3,
        ),

        # =============================================
        # PZB 500Hz — da Get_InfluenceState
        # =============================================
        LedMapping(
            name="500Hz attivo (PZB)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "Get_InfluenceState",
            condition=Condition.TRUE,
            led_name="500HZ",
            action=LedAction.ON,
            value_key="500Hz_Active",
        ),

        # =============================================
        # PZB 85 / 70 / 55 — Logica LED:
        #   ActiveMode indica quale modalità PZB è attiva:
        #     3 = O (85 km/h), 2 = M (70 km/h), 1 = U (55 km/h)
        #   pri 0: ON fisso    = modalità attiva (da ActiveMode)
        #   pri 1: BLINK 1.0s  = frequenza attiva (monitoraggio)
        #   pri 3: BLINK 1.0s  = restricted (85 alterna con 70)
        #   pri 4: BLINK 0.5s  = overspeed
        #   pri 5: BLINK 0.3s  = emergenza
        # =============================================

        # --- PZB 85 (ActiveMode == 3) ---
        LedMapping(
            name="PZB 85 fisso (modalità O attiva)",
            enabled=True,
            tsw6_endpoint=PZB_PR + "ActiveMode",
            condition=Condition.EQUAL,
            threshold=3,
            led_name="PZB85",
            action=LedAction.ON,
        ),
        LedMapping(
            name="PZB 85 lampeggio (1000Hz attivo)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "Get_InfluenceState",
            condition=Condition.TRUE,
            led_name="PZB85",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
            priority=1,
            value_key="1000Hz_Active",
        ),
        LedMapping(
            name="PZB 85 lampeggio (restriktiv, Wechselblinken con 70)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "Get_InfluenceState",
            condition=Condition.TRUE,
            led_name="PZB85",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
            priority=3,
            value_key="isRestricted",
        ),
        LedMapping(
            name="PZB 85 lampeggio (overspeed)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "PZB_GetOverspeed",
            condition=Condition.TRUE,
            led_name="PZB85",
            action=LedAction.BLINK,
            blink_interval_sec=0.5,
            priority=4,
        ),
        LedMapping(
            name="PZB 85 lampeggio (emergenza)",
            enabled=True,
            tsw6_endpoint=PZB_PR + "_InEmergency",
            condition=Condition.TRUE,
            led_name="PZB85",
            action=LedAction.BLINK,
            blink_interval_sec=0.3,
            priority=5,
        ),

        # --- PZB 70 (ActiveMode == 2) ---
        LedMapping(
            name="PZB 70 fisso (modalit\u00e0 M attiva)",
            enabled=True,
            tsw6_endpoint=PZB_PR + "ActiveMode",
            condition=Condition.EQUAL,
            threshold=2,
            led_name="PZB70",
            action=LedAction.ON,
        ),
        LedMapping(
            name="PZB 70 lampeggio (500Hz attivo)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "Get_InfluenceState",
            condition=Condition.TRUE,
            led_name="PZB70",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
            priority=1,
            value_key="500Hz_Active",
        ),
        LedMapping(
            name="PZB 70 lampeggio (restriktiv, Wechselblinken con 85)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "Get_InfluenceState",
            condition=Condition.TRUE,
            led_name="PZB70",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
            priority=3,
            value_key="isRestricted",
        ),
        LedMapping(
            name="PZB 70 lampeggio (overspeed)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "PZB_GetOverspeed",
            condition=Condition.TRUE,
            led_name="PZB70",
            action=LedAction.BLINK,
            blink_interval_sec=0.5,
            priority=4,
        ),
        LedMapping(
            name="PZB 70 lampeggio (emergenza)",
            enabled=True,
            tsw6_endpoint=PZB_PR + "_InEmergency",
            condition=Condition.TRUE,
            led_name="PZB70",
            action=LedAction.BLINK,
            blink_interval_sec=0.3,
            priority=5,
        ),

        # --- PZB 55 (ActiveMode == 1) ---
        LedMapping(
            name="PZB 55 fisso (modalit\u00e0 U attiva)",
            enabled=True,
            tsw6_endpoint=PZB_PR + "ActiveMode",
            condition=Condition.EQUAL,
            threshold=1,
            led_name="PZB55",
            action=LedAction.ON,
        ),
        LedMapping(
            name="PZB 55 lampeggio (2000Hz attivo)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "Get_InfluenceState",
            condition=Condition.TRUE,
            led_name="PZB55",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
            priority=1,
            value_key="2000Hz_Active",
        ),
        LedMapping(
            name="PZB 55 lampeggio (overspeed)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "PZB_GetOverspeed",
            condition=Condition.TRUE,
            led_name="PZB55",
            action=LedAction.BLINK,
            blink_interval_sec=0.5,
            priority=4,
        ),
        LedMapping(
            name="PZB 55 lampeggio (emergenza)",
            enabled=True,
            tsw6_endpoint=PZB_PR + "_InEmergency",
            condition=Condition.TRUE,
            led_name="PZB55",
            action=LedAction.BLINK,
            blink_interval_sec=0.3,
            priority=5,
        ),

        # =============================================
        # LZB Ende — EndeState > 0
        # EndeState 1 = lampeggio (attesa conferma), 2 = fisso (confermato)
        # =============================================
        LedMapping(
            name="LZB Ende attivo",
            enabled=True,
            tsw6_endpoint=LZB_PR + "EndeState",
            condition=Condition.GREATER_THAN,
            threshold=0,
            led_name="LZB",
            action=LedAction.ON,
        ),
        LedMapping(
            name="LZB Ende lampeggio (attesa conferma)",
            enabled=True,
            tsw6_endpoint=LZB_PR + "EndeState",
            condition=Condition.EQUAL,
            threshold=1,
            led_name="LZB",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
            priority=1,
        ),

        # =============================================
        # LZB Ü — ULightState > 0
        # =============================================
        LedMapping(
            name="LZB Ü attivo",
            enabled=True,
            tsw6_endpoint=LZB_PR + "ULightState",
            condition=Condition.GREATER_THAN,
            threshold=0,
            led_name="LZB_UE",
            action=LedAction.ON,
        ),
        LedMapping(
            name="LZB Ü lampeggio (fault)",
            enabled=True,
            tsw6_endpoint=LZB_PR + "FaultCode",
            condition=Condition.GREATER_THAN,
            threshold=0,
            led_name="LZB_UE",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
            priority=3,
        ),

        # =============================================
        # LZB G — OverspeedState > 0 (LZB interviene: frenata/rallentamento)
        # bIsActivated indica solo che il sistema è acceso, NON che sta frenando
        # =============================================
        LedMapping(
            name="LZB G attivo (LZB interviene)",
            enabled=True,
            tsw6_endpoint=LZB_PR + "OverspeedState",
            condition=Condition.GREATER_THAN,
            threshold=0,
            led_name="LZB_G",
            action=LedAction.ON,
        ),

        # =============================================
        # LZB S — Enforcement (frenata forzata LZB)
        # =============================================
        LedMapping(
            name="LZB S (frenata forzata)",
            enabled=True,
            tsw6_endpoint=LZB_PR + "Enforcement",
            condition=Condition.TRUE,
            led_name="LZB_S",
            action=LedAction.ON,
        ),

        # =============================================
        # Porte — DriverAssist.GetAreDoorsUnlocked
        # =============================================
        LedMapping(
            name="Porte Sinistra (sbloccate)",
            enabled=True,
            tsw6_endpoint="CurrentFormation/0/DriverAssist.Function.GetAreDoorsUnlocked",
            condition=Condition.TRUE,
            led_name="TUEREN_L",
            action=LedAction.ON,
        ),
        LedMapping(
            name="Porte Destra (sbloccate)",
            enabled=True,
            tsw6_endpoint="CurrentFormation/0/DriverAssist.Function.GetAreDoorsUnlocked",
            condition=Condition.TRUE,
            led_name="TUEREN_R",
            action=LedAction.ON,
        ),
    ]

    # Quando LZB Ü è attivo (ULightState > 0), i LED PZB devono spegnersi
    _pzb_leds = {"PZB85", "PZB70", "PZB55", "1000HZ", "500HZ"}
    for m in mappings:
        if m.led_name in _pzb_leds:
            m.requires_endpoint_false = LZB_PR + "ULightState"

    profile = Profile(
        name="Profilo DB BR 146.2 (PZB/LZB/SIFA)",
        description="DB BR 146.2 — PZB_Service_V2, LZB_Service, SIFA diretto, senza MFA",
        train_class="BR146",
    )
    profile.set_mappings(mappings)
    return profile


# ============================================================
# Profilo DB BR 114
# ============================================================

def create_br114_profile() -> Profile:
    """
    Profilo per DB BR 114 (RVM_FTF_DB_BR114_C).

    La BR 114 è una locomotiva elettrica per servizi regionali.
    NON ha LZB — solo PZB e SIFA.

    Endpoint specifici:
      - PZB: componente "PZB" (non PZB_V3 né PZB_Service_V2)
        Ha Get_InfluenceState, ActiveMode, _RequiresAcknowledge, _InEmergency, PZB_GetOverspeed
      - SIFA: BP_Sifa_Service (come BR101)
        WarningStateVisual, inPenaltyBrakeApplication
      - Porte: DriverAssist_F/B.Function.GetAreDoorsUnlocked (entrambe le cabine)
      - LZB: assente

    Gli stati PZB 1000Hz/500Hz/2000Hz vengono dalla Function
    Get_InfluenceState tramite value_key per estrarre i singoli flag.
    """
    PZB_FN = "CurrentFormation/0/PZB.Function."
    PZB_PR = "CurrentFormation/0/PZB.Property."

    mappings = [
        # =============================================
        # SIFA — BP_Sifa_Service (come BR101)
        # =============================================
        LedMapping(
            name="SIFA Warning (Visual)",
            enabled=True,
            tsw6_endpoint="CurrentFormation/0/BP_Sifa_Service.Property.WarningStateVisual",
            condition=Condition.TRUE,
            led_name="SIFA",
            action=LedAction.ON,
            priority=0,
        ),
        LedMapping(
            name="SIFA Penalità (Frenata)",
            enabled=True,
            tsw6_endpoint="CurrentFormation/0/BP_Sifa_Service.Property.inPenaltyBrakeApplication",
            condition=Condition.TRUE,
            led_name="SIFA",
            action=LedAction.BLINK,
            blink_interval_sec=0.5,
            priority=10,
        ),

        # =============================================
        # PZB 1000Hz — da Get_InfluenceState
        # Fisso ON durante monitoraggio, BLINK durante
        # finestra Wachsam (acknowledge richiesto)
        # =============================================
        LedMapping(
            name="1000Hz attivo (PZB)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "Get_InfluenceState",
            condition=Condition.TRUE,
            led_name="1000HZ",
            action=LedAction.ON,
            value_key="1000Hz_Active",
        ),
        LedMapping(
            name="1000Hz Wachsam (conferma richiesta)",
            enabled=True,
            tsw6_endpoint=PZB_PR + "_RequiresAcknowledge",
            condition=Condition.TRUE,
            led_name="1000HZ",
            action=LedAction.BLINK,
            blink_interval_sec=0.5,
            priority=3,
        ),

        # =============================================
        # PZB 500Hz — da Get_InfluenceState
        # =============================================
        LedMapping(
            name="500Hz attivo (PZB)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "Get_InfluenceState",
            condition=Condition.TRUE,
            led_name="500HZ",
            action=LedAction.ON,
            value_key="500Hz_Active",
        ),

        # =============================================
        # PZB 85 / 70 / 55 — Logica LED:
        #   ActiveMode indica quale modalità PZB è attiva:
        #     3 = O (85 km/h), 2 = M (70 km/h), 1 = U (55 km/h)
        #   pri 0: ON fisso    = modalità attiva (da ActiveMode)
        #   pri 1: BLINK 1.0s  = frequenza attiva (monitoraggio)
        #   pri 3: BLINK 1.0s  = restricted (85 alterna con 70)
        #   pri 4: BLINK 0.5s  = overspeed
        #   pri 5: BLINK 0.3s  = emergenza
        # =============================================

        # --- PZB 85 (ActiveMode == 3) ---
        LedMapping(
            name="PZB 85 fisso (modalità O attiva)",
            enabled=True,
            tsw6_endpoint=PZB_PR + "ActiveMode",
            condition=Condition.EQUAL,
            threshold=3,
            led_name="PZB85",
            action=LedAction.ON,
        ),
        LedMapping(
            name="PZB 85 lampeggio (1000Hz attivo)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "Get_InfluenceState",
            condition=Condition.TRUE,
            led_name="PZB85",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
            priority=1,
            value_key="1000Hz_Active",
        ),
        LedMapping(
            name="PZB 85 lampeggio (restriktiv, Wechselblinken con 70)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "Get_InfluenceState",
            condition=Condition.TRUE,
            led_name="PZB85",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
            priority=3,
            value_key="isRestricted",
        ),
        LedMapping(
            name="PZB 85 lampeggio (overspeed)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "PZB_GetOverspeed",
            condition=Condition.TRUE,
            led_name="PZB85",
            action=LedAction.BLINK,
            blink_interval_sec=0.5,
            priority=4,
        ),
        LedMapping(
            name="PZB 85 lampeggio (emergenza)",
            enabled=True,
            tsw6_endpoint=PZB_PR + "_InEmergency",
            condition=Condition.TRUE,
            led_name="PZB85",
            action=LedAction.BLINK,
            blink_interval_sec=0.3,
            priority=5,
        ),

        # --- PZB 70 (ActiveMode == 2) ---
        LedMapping(
            name="PZB 70 fisso (modalità M attiva)",
            enabled=True,
            tsw6_endpoint=PZB_PR + "ActiveMode",
            condition=Condition.EQUAL,
            threshold=2,
            led_name="PZB70",
            action=LedAction.ON,
        ),
        LedMapping(
            name="PZB 70 lampeggio (500Hz attivo)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "Get_InfluenceState",
            condition=Condition.TRUE,
            led_name="PZB70",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
            priority=1,
            value_key="500Hz_Active",
        ),
        LedMapping(
            name="PZB 70 lampeggio (restriktiv, Wechselblinken con 85)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "Get_InfluenceState",
            condition=Condition.TRUE,
            led_name="PZB70",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
            priority=3,
            value_key="isRestricted",
        ),
        LedMapping(
            name="PZB 70 lampeggio (overspeed)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "PZB_GetOverspeed",
            condition=Condition.TRUE,
            led_name="PZB70",
            action=LedAction.BLINK,
            blink_interval_sec=0.5,
            priority=4,
        ),
        LedMapping(
            name="PZB 70 lampeggio (emergenza)",
            enabled=True,
            tsw6_endpoint=PZB_PR + "_InEmergency",
            condition=Condition.TRUE,
            led_name="PZB70",
            action=LedAction.BLINK,
            blink_interval_sec=0.3,
            priority=5,
        ),

        # --- PZB 55 (ActiveMode == 1) ---
        LedMapping(
            name="PZB 55 fisso (modalità U attiva)",
            enabled=True,
            tsw6_endpoint=PZB_PR + "ActiveMode",
            condition=Condition.EQUAL,
            threshold=1,
            led_name="PZB55",
            action=LedAction.ON,
        ),
        LedMapping(
            name="PZB 55 lampeggio (2000Hz attivo)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "Get_InfluenceState",
            condition=Condition.TRUE,
            led_name="PZB55",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
            priority=1,
            value_key="2000Hz_Active",
        ),
        LedMapping(
            name="PZB 55 lampeggio (overspeed)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "PZB_GetOverspeed",
            condition=Condition.TRUE,
            led_name="PZB55",
            action=LedAction.BLINK,
            blink_interval_sec=0.5,
            priority=4,
        ),
        LedMapping(
            name="PZB 55 lampeggio (emergenza)",
            enabled=True,
            tsw6_endpoint=PZB_PR + "_InEmergency",
            condition=Condition.TRUE,
            led_name="PZB55",
            action=LedAction.BLINK,
            blink_interval_sec=0.3,
            priority=5,
        ),

        # =============================================
        # Porte — DriverAssist_F / DriverAssist_B
        # True = porte sbloccate. Servono entrambi perché
        # la BR114 ha due cabine (F=fronte, B=retro).
        # Il segnale attivo dipende da quale cabina è occupata.
        # =============================================
        LedMapping(
            name="Porte Sinistra (cab F)",
            enabled=True,
            tsw6_endpoint="CurrentFormation/0/DriverAssist_F.Function.GetAreDoorsUnlocked",
            condition=Condition.TRUE,
            led_name="TUEREN_L",
            action=LedAction.ON,
        ),
        LedMapping(
            name="Porte Sinistra (cab B)",
            enabled=True,
            tsw6_endpoint="CurrentFormation/0/DriverAssist_B.Function.GetAreDoorsUnlocked",
            condition=Condition.TRUE,
            led_name="TUEREN_L",
            action=LedAction.ON,
        ),
        LedMapping(
            name="Porte Destra (cab F)",
            enabled=True,
            tsw6_endpoint="CurrentFormation/0/DriverAssist_F.Function.GetAreDoorsUnlocked",
            condition=Condition.TRUE,
            led_name="TUEREN_R",
            action=LedAction.ON,
        ),
        LedMapping(
            name="Porte Destra (cab B)",
            enabled=True,
            tsw6_endpoint="CurrentFormation/0/DriverAssist_B.Function.GetAreDoorsUnlocked",
            condition=Condition.TRUE,
            led_name="TUEREN_R",
            action=LedAction.ON,
        ),
    ]

    profile = Profile(
        name="Profilo DB BR 114 (PZB/SIFA, no LZB)",
        description="DB BR 114 — PZB diretto, BP_Sifa_Service, senza LZB, senza MFA",
        train_class="BR114",
    )
    profile.set_mappings(mappings)
    return profile


# ============================================================
# Profilo DB BR 411 ICE-T
# ============================================================

def create_br411_profile() -> Profile:
    """
    Profilo per DB BR 411 ICE-T (RVM_FTF_DB_BR411_TW_*_C).

    L'ICE-T è un treno ad assetto variabile per servizi InterCity.
    Composizione tipica: 7 carri (TW_5, SR_6, FM_7, MW_8, FM_2, SR_1, TW_0).
    I sottosistemi di sicurezza sono sul carro guidato (idx 0).

    Endpoint specifici:
      - PZB: PZB_Service_V3 (come Vectron) con Get_InfluenceState, ActiveMode
      - LZB: LZB (come BR101, NON LZB_Service)
      - SIFA: BP_Sifa_Service (come BR101)
      - Porte: DriverAssist.Function.GetAreDoorsUnlocked (come BR146, senza suffisso)

    Gli stati PZB 1000Hz/500Hz/2000Hz vengono dalla Function
    Get_InfluenceState tramite value_key per estrarre i singoli flag.
    """
    PZB_FN = "CurrentFormation/0/PZB_Service_V3.Function."
    PZB_PR = "CurrentFormation/0/PZB_Service_V3.Property."
    LZB_PR = "CurrentFormation/0/LZB.Property."

    mappings = [
        # =============================================
        # SIFA — BP_Sifa_Service (come BR101)
        # =============================================
        LedMapping(
            name="SIFA Warning (Visual)",
            enabled=True,
            tsw6_endpoint="CurrentFormation/0/BP_Sifa_Service.Property.WarningStateVisual",
            condition=Condition.TRUE,
            led_name="SIFA",
            action=LedAction.ON,
            priority=0,
        ),
        LedMapping(
            name="SIFA Penalità (Frenata)",
            enabled=True,
            tsw6_endpoint="CurrentFormation/0/BP_Sifa_Service.Property.inPenaltyBrakeApplication",
            condition=Condition.TRUE,
            led_name="SIFA",
            action=LedAction.BLINK,
            blink_interval_sec=0.5,
            priority=10,
        ),

        # =============================================
        # PZB 1000Hz — da Get_InfluenceState
        # Fisso ON durante monitoraggio, BLINK durante
        # finestra Wachsam (acknowledge richiesto)
        # =============================================
        LedMapping(
            name="1000Hz attivo (PZB)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "Get_InfluenceState",
            condition=Condition.TRUE,
            led_name="1000HZ",
            action=LedAction.ON,
            value_key="1000Hz_Active",
        ),
        LedMapping(
            name="1000Hz Wachsam (conferma richiesta)",
            enabled=True,
            tsw6_endpoint=PZB_PR + "_RequiresAcknowledge",
            condition=Condition.TRUE,
            led_name="1000HZ",
            action=LedAction.BLINK,
            blink_interval_sec=0.5,
            priority=3,
        ),

        # =============================================
        # PZB 500Hz — da Get_InfluenceState
        # =============================================
        LedMapping(
            name="500Hz attivo (PZB)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "Get_InfluenceState",
            condition=Condition.TRUE,
            led_name="500HZ",
            action=LedAction.ON,
            value_key="500Hz_Active",
        ),

        # =============================================
        # PZB 85 / 70 / 55 — Logica LED completa:
        #   ActiveMode: 3=O(85), 2=M(70), 1=U(55)
        #   pri 0: ON fisso    = modalità attiva
        #   pri 1: BLINK 1.0s  = frequenza attiva (monitoraggio)
        #   pri 3: BLINK 1.0s  = restricted (Wechselblinken 70↔85)
        #   pri 4: BLINK 0.5s  = overspeed
        #   pri 5: BLINK 0.3s  = emergenza
        # =============================================

        # --- PZB 85 (ActiveMode == 3) ---
        LedMapping(
            name="PZB 85 fisso (modalità O attiva)",
            enabled=True,
            tsw6_endpoint=PZB_PR + "ActiveMode",
            condition=Condition.EQUAL,
            threshold=3,
            led_name="PZB85",
            action=LedAction.ON,
        ),
        LedMapping(
            name="PZB 85 lampeggio (1000Hz attivo)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "Get_InfluenceState",
            condition=Condition.TRUE,
            led_name="PZB85",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
            priority=1,
            value_key="1000Hz_Active",
        ),
        LedMapping(
            name="PZB 85 lampeggio (restriktiv, Wechselblinken con 70)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "Get_InfluenceState",
            condition=Condition.TRUE,
            led_name="PZB85",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
            priority=3,
            value_key="isRestricted",
        ),
        LedMapping(
            name="PZB 85 lampeggio (overspeed)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "PZB_GetOverspeed",
            condition=Condition.TRUE,
            led_name="PZB85",
            action=LedAction.BLINK,
            blink_interval_sec=0.5,
            priority=4,
        ),
        LedMapping(
            name="PZB 85 lampeggio (emergenza)",
            enabled=True,
            tsw6_endpoint=PZB_PR + "_InEmergency",
            condition=Condition.TRUE,
            led_name="PZB85",
            action=LedAction.BLINK,
            blink_interval_sec=0.3,
            priority=5,
        ),

        # --- PZB 70 (ActiveMode == 2) ---
        LedMapping(
            name="PZB 70 fisso (modalità M attiva)",
            enabled=True,
            tsw6_endpoint=PZB_PR + "ActiveMode",
            condition=Condition.EQUAL,
            threshold=2,
            led_name="PZB70",
            action=LedAction.ON,
        ),
        LedMapping(
            name="PZB 70 lampeggio (500Hz attivo)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "Get_InfluenceState",
            condition=Condition.TRUE,
            led_name="PZB70",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
            priority=1,
            value_key="500Hz_Active",
        ),
        LedMapping(
            name="PZB 70 lampeggio (restriktiv, Wechselblinken con 85)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "Get_InfluenceState",
            condition=Condition.TRUE,
            led_name="PZB70",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
            priority=3,
            value_key="isRestricted",
        ),
        LedMapping(
            name="PZB 70 lampeggio (overspeed)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "PZB_GetOverspeed",
            condition=Condition.TRUE,
            led_name="PZB70",
            action=LedAction.BLINK,
            blink_interval_sec=0.5,
            priority=4,
        ),
        LedMapping(
            name="PZB 70 lampeggio (emergenza)",
            enabled=True,
            tsw6_endpoint=PZB_PR + "_InEmergency",
            condition=Condition.TRUE,
            led_name="PZB70",
            action=LedAction.BLINK,
            blink_interval_sec=0.3,
            priority=5,
        ),

        # --- PZB 55 (ActiveMode == 1) ---
        LedMapping(
            name="PZB 55 fisso (modalità U attiva)",
            enabled=True,
            tsw6_endpoint=PZB_PR + "ActiveMode",
            condition=Condition.EQUAL,
            threshold=1,
            led_name="PZB55",
            action=LedAction.ON,
        ),
        LedMapping(
            name="PZB 55 lampeggio (2000Hz attivo)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "Get_InfluenceState",
            condition=Condition.TRUE,
            led_name="PZB55",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
            priority=1,
            value_key="2000Hz_Active",
        ),
        LedMapping(
            name="PZB 55 lampeggio (overspeed)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "PZB_GetOverspeed",
            condition=Condition.TRUE,
            led_name="PZB55",
            action=LedAction.BLINK,
            blink_interval_sec=0.5,
            priority=4,
        ),
        LedMapping(
            name="PZB 55 lampeggio (emergenza)",
            enabled=True,
            tsw6_endpoint=PZB_PR + "_InEmergency",
            condition=Condition.TRUE,
            led_name="PZB55",
            action=LedAction.BLINK,
            blink_interval_sec=0.3,
            priority=5,
        ),

        # =============================================
        # LZB Ende — EndeState > 0
        # EndeState 1 = lampeggio (attesa conferma), 2 = fisso (confermato)
        # =============================================
        LedMapping(
            name="LZB Ende attivo",
            enabled=True,
            tsw6_endpoint=LZB_PR + "EndeState",
            condition=Condition.GREATER_THAN,
            threshold=0,
            led_name="LZB",
            action=LedAction.ON,
        ),
        LedMapping(
            name="LZB Ende lampeggio (attesa conferma)",
            enabled=True,
            tsw6_endpoint=LZB_PR + "EndeState",
            condition=Condition.EQUAL,
            threshold=1,
            led_name="LZB",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
            priority=1,
        ),

        # =============================================
        # LZB Ü — ULightState > 0
        # =============================================
        LedMapping(
            name="LZB Ü attivo",
            enabled=True,
            tsw6_endpoint=LZB_PR + "ULightState",
            condition=Condition.GREATER_THAN,
            threshold=0,
            led_name="LZB_UE",
            action=LedAction.ON,
        ),
        LedMapping(
            name="LZB Ü lampeggio (fault)",
            enabled=True,
            tsw6_endpoint=LZB_PR + "faultCode",
            condition=Condition.GREATER_THAN,
            threshold=0,
            led_name="LZB_UE",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
            priority=3,
        ),

        # =============================================
        # LZB G — OverspeedState > 0 (LZB interviene: frenata/rallentamento)
        # bIsActivated indica solo che il sistema è acceso, NON che sta frenando
        # =============================================
        LedMapping(
            name="LZB G attivo (LZB interviene)",
            enabled=True,
            tsw6_endpoint=LZB_PR + "OverspeedState",
            condition=Condition.GREATER_THAN,
            threshold=0,
            led_name="LZB_G",
            action=LedAction.ON,
        ),

        # =============================================
        # LZB S — Enforcement (frenata forzata LZB)
        # =============================================
        LedMapping(
            name="LZB S (frenata forzata)",
            enabled=True,
            tsw6_endpoint=LZB_PR + "Enforcement",
            condition=Condition.TRUE,
            led_name="LZB_S",
            action=LedAction.ON,
        ),

        # =============================================
        # Porte — DriverAssist.GetAreDoorsUnlocked
        # =============================================
        LedMapping(
            name="Porte Sinistra (sbloccate)",
            enabled=True,
            tsw6_endpoint="CurrentFormation/0/DriverAssist.Function.GetAreDoorsUnlocked",
            condition=Condition.TRUE,
            led_name="TUEREN_L",
            action=LedAction.ON,
        ),
        LedMapping(
            name="Porte Destra (sbloccate)",
            enabled=True,
            tsw6_endpoint="CurrentFormation/0/DriverAssist.Function.GetAreDoorsUnlocked",
            condition=Condition.TRUE,
            led_name="TUEREN_R",
            action=LedAction.ON,
        ),
    ]

    # Quando LZB Ü è attivo (ULightState > 0), i LED PZB devono spegnersi
    _pzb_leds = {"PZB85", "PZB70", "PZB55", "1000HZ", "500HZ"}
    for m in mappings:
        if m.led_name in _pzb_leds:
            m.requires_endpoint_false = LZB_PR + "ULightState"

    profile = Profile(
        name="Profilo DB BR 411 ICE-T (PZB/LZB/SIFA)",
        description="DB BR 411 ICE-T — PZB_Service_V3, LZB, BP_Sifa_Service, senza MFA",
        train_class="BR411",
    )
    profile.set_mappings(mappings)
    return profile


# ============================================================
# Profilo DB BR 406 ICE 3
# ============================================================

def create_br406_profile() -> Profile:
    """
    Profilo per DB BR 406 ICE 3 (RVM_KAH_DB_ICE3M_EndCar).

    L'ICE 3M è un treno ad alta velocità con modulo RVM/KAH.
    
    Endpoint specifici:
      - PZB: componente "PZB" (come BR114)
        Ha Get_InfluenceState (chiavi con suffisso GUID, match parziale),
        ActiveMode, _RequiresAcknowledge, _InEmergency, PZB_GetOverspeed
      - LZB: componente "LZB" (come BR101/BR411)
        EndeState, ULightState, OverspeedState, Enforcement, faultCode
      - SIFA: funzione car-level HUD_GetAlerter
        AleterState: 0=normale, 1=warning/emergenza → LED fisso (no blink)
      - Porte: PassengerDoor_FL/FR/BL/BR (GetCurrentOutputValue)
        0=chiusa, 1=aperta. FL/BL=sinistra, FR/BR=destra

    Formazione 8 carri: EndCar-5, TransformerCar-6, ConverterCar-7,
    MiddleCar-8, MiddleCar-3, ConverterCar-2, EndCar-0.
    """
    PZB_FN = "CurrentFormation/0/PZB.Function."
    PZB_PR = "CurrentFormation/0/PZB.Property."
    LZB_PR = "CurrentFormation/0/LZB.Property."
    # Endpoint SIFA car-level (formato: nodo.Function.nome)
    SIFA_ALERTER = "CurrentFormation/0.Function.HUD_GetAlerter"
    # Porte singole
    DOOR_FL = "CurrentFormation/0/PassengerDoor_FL.Function.GetCurrentOutputValue"
    DOOR_FR = "CurrentFormation/0/PassengerDoor_FR.Function.GetCurrentOutputValue"
    DOOR_BL = "CurrentFormation/0/PassengerDoor_BL.Function.GetCurrentOutputValue"
    DOOR_BR = "CurrentFormation/0/PassengerDoor_BR.Function.GetCurrentOutputValue"

    mappings = [
        # =============================================
        # SIFA — car-level function
        # HUD_GetAlerter: api.get() ritorna AleterState (int)
        #   0 = normale, 1 = warning/emergenza
        # Il LED SIFA resta fisso sia in warning che in emergenza
        # =============================================
        LedMapping(
            name="SIFA warning (alerter attivo)",
            enabled=True,
            tsw6_endpoint=SIFA_ALERTER,
            condition=Condition.GREATER_THAN,
            threshold=0,
            led_name="SIFA",
            action=LedAction.ON,
        ),

        # =============================================
        # PZB 1000Hz — da Get_InfluenceState
        # =============================================
        LedMapping(
            name="1000Hz attivo (PZB)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "Get_InfluenceState",
            condition=Condition.TRUE,
            led_name="1000HZ",
            action=LedAction.ON,
            value_key="1000Hz_Active",
        ),
        LedMapping(
            name="1000Hz Wachsam (conferma richiesta)",
            enabled=True,
            tsw6_endpoint=PZB_PR + "_RequiresAcknowledge",
            condition=Condition.TRUE,
            led_name="1000HZ",
            action=LedAction.BLINK,
            blink_interval_sec=0.5,
            priority=3,
        ),

        # =============================================
        # PZB 500Hz — da Get_InfluenceState
        # =============================================
        LedMapping(
            name="500Hz attivo (PZB)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "Get_InfluenceState",
            condition=Condition.TRUE,
            led_name="500HZ",
            action=LedAction.ON,
            value_key="500Hz_Active",
        ),

        # =============================================
        # PZB 85 / 70 / 55
        # =============================================

        # --- PZB 85 (ActiveMode == 3) ---
        LedMapping(
            name="PZB 85 fisso (modalità O attiva)",
            enabled=True,
            tsw6_endpoint=PZB_PR + "ActiveMode",
            condition=Condition.EQUAL,
            threshold=3,
            led_name="PZB85",
            action=LedAction.ON,
        ),
        LedMapping(
            name="PZB 85 lampeggio (1000Hz attivo)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "Get_InfluenceState",
            condition=Condition.TRUE,
            led_name="PZB85",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
            priority=1,
            value_key="1000Hz_Active",
        ),
        LedMapping(
            name="PZB 85 lampeggio (restriktiv, Wechselblinken con 70)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "Get_InfluenceState",
            condition=Condition.TRUE,
            led_name="PZB85",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
            priority=3,
            value_key="isRestricted",
        ),
        LedMapping(
            name="PZB 85 lampeggio (overspeed)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "PZB_GetOverspeed",
            condition=Condition.TRUE,
            led_name="PZB85",
            action=LedAction.BLINK,
            blink_interval_sec=0.5,
            priority=4,
        ),
        LedMapping(
            name="PZB 85 lampeggio (emergenza)",
            enabled=True,
            tsw6_endpoint=PZB_PR + "_InEmergency",
            condition=Condition.TRUE,
            led_name="PZB85",
            action=LedAction.BLINK,
            blink_interval_sec=0.3,
            priority=5,
        ),

        # --- PZB 70 (ActiveMode == 2) ---
        LedMapping(
            name="PZB 70 fisso (modalità M attiva)",
            enabled=True,
            tsw6_endpoint=PZB_PR + "ActiveMode",
            condition=Condition.EQUAL,
            threshold=2,
            led_name="PZB70",
            action=LedAction.ON,
        ),
        LedMapping(
            name="PZB 70 lampeggio (500Hz attivo)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "Get_InfluenceState",
            condition=Condition.TRUE,
            led_name="PZB70",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
            priority=1,
            value_key="500Hz_Active",
        ),
        LedMapping(
            name="PZB 70 lampeggio (restriktiv, Wechselblinken con 85)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "Get_InfluenceState",
            condition=Condition.TRUE,
            led_name="PZB70",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
            priority=3,
            value_key="isRestricted",
        ),
        LedMapping(
            name="PZB 70 lampeggio (overspeed)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "PZB_GetOverspeed",
            condition=Condition.TRUE,
            led_name="PZB70",
            action=LedAction.BLINK,
            blink_interval_sec=0.5,
            priority=4,
        ),
        LedMapping(
            name="PZB 70 lampeggio (emergenza)",
            enabled=True,
            tsw6_endpoint=PZB_PR + "_InEmergency",
            condition=Condition.TRUE,
            led_name="PZB70",
            action=LedAction.BLINK,
            blink_interval_sec=0.3,
            priority=5,
        ),

        # --- PZB 55 (ActiveMode == 1) ---
        LedMapping(
            name="PZB 55 fisso (modalità U attiva)",
            enabled=True,
            tsw6_endpoint=PZB_PR + "ActiveMode",
            condition=Condition.EQUAL,
            threshold=1,
            led_name="PZB55",
            action=LedAction.ON,
        ),
        LedMapping(
            name="PZB 55 lampeggio (2000Hz attivo)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "Get_InfluenceState",
            condition=Condition.TRUE,
            led_name="PZB55",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
            priority=1,
            value_key="2000Hz_Active",
        ),
        LedMapping(
            name="PZB 55 lampeggio (overspeed)",
            enabled=True,
            tsw6_endpoint=PZB_FN + "PZB_GetOverspeed",
            condition=Condition.TRUE,
            led_name="PZB55",
            action=LedAction.BLINK,
            blink_interval_sec=0.5,
            priority=4,
        ),
        LedMapping(
            name="PZB 55 lampeggio (emergenza)",
            enabled=True,
            tsw6_endpoint=PZB_PR + "_InEmergency",
            condition=Condition.TRUE,
            led_name="PZB55",
            action=LedAction.BLINK,
            blink_interval_sec=0.3,
            priority=5,
        ),

        # =============================================
        # LZB Ende — EndeState > 0
        # EndeState 1 = lampeggio (attesa conferma), 2 = fisso (confermato)
        # =============================================
        LedMapping(
            name="LZB Ende attivo",
            enabled=True,
            tsw6_endpoint=LZB_PR + "EndeState",
            condition=Condition.GREATER_THAN,
            threshold=0,
            led_name="LZB",
            action=LedAction.ON,
        ),
        LedMapping(
            name="LZB Ende lampeggio (attesa conferma)",
            enabled=True,
            tsw6_endpoint=LZB_PR + "EndeState",
            condition=Condition.EQUAL,
            threshold=1,
            led_name="LZB",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
            priority=1,
        ),

        # =============================================
        # LZB Ü — ULightState > 0
        # =============================================
        LedMapping(
            name="LZB Ü attivo",
            enabled=True,
            tsw6_endpoint=LZB_PR + "ULightState",
            condition=Condition.GREATER_THAN,
            threshold=0,
            led_name="LZB_UE",
            action=LedAction.ON,
        ),
        LedMapping(
            name="LZB Ü lampeggio (fault)",
            enabled=True,
            tsw6_endpoint=LZB_PR + "faultCode",
            condition=Condition.GREATER_THAN,
            threshold=0,
            led_name="LZB_UE",
            action=LedAction.BLINK,
            blink_interval_sec=1.0,
            priority=3,
        ),

        # =============================================
        # LZB G — OverspeedState > 0 (LZB interviene)
        # =============================================
        LedMapping(
            name="LZB G attivo (LZB interviene)",
            enabled=True,
            tsw6_endpoint=LZB_PR + "OverspeedState",
            condition=Condition.GREATER_THAN,
            threshold=0,
            led_name="LZB_G",
            action=LedAction.ON,
        ),

        # =============================================
        # LZB S — Enforcement (frenata forzata LZB)
        # =============================================
        LedMapping(
            name="LZB S (frenata forzata)",
            enabled=True,
            tsw6_endpoint=LZB_PR + "Enforcement",
            condition=Condition.TRUE,
            led_name="LZB_S",
            action=LedAction.ON,
        ),

        # =============================================
        # Porte — PassengerDoor singole (GetCurrentOutputValue)
        # FL/BL = sinistra, FR/BR = destra
        # 0 = chiusa, > 0 = aperta
        # =============================================
        LedMapping(
            name="Porte sinistra aperte (FL)",
            enabled=True,
            tsw6_endpoint=DOOR_FL,
            condition=Condition.GREATER_THAN,
            threshold=0,
            led_name="TUEREN_L",
            action=LedAction.ON,
        ),
        LedMapping(
            name="Porte sinistra aperte (BL)",
            enabled=True,
            tsw6_endpoint=DOOR_BL,
            condition=Condition.GREATER_THAN,
            threshold=0,
            led_name="TUEREN_L",
            action=LedAction.ON,
        ),
        LedMapping(
            name="Porte destra aperte (FR)",
            enabled=True,
            tsw6_endpoint=DOOR_FR,
            condition=Condition.GREATER_THAN,
            threshold=0,
            led_name="TUEREN_R",
            action=LedAction.ON,
        ),
        LedMapping(
            name="Porte destra aperte (BR)",
            enabled=True,
            tsw6_endpoint=DOOR_BR,
            condition=Condition.GREATER_THAN,
            threshold=0,
            led_name="TUEREN_R",
            action=LedAction.ON,
        ),
    ]

    # Quando LZB Ü è attivo (ULightState > 0), i LED PZB devono spegnersi
    _pzb_leds = {"PZB85", "PZB70", "PZB55", "1000HZ", "500HZ"}
    for m in mappings:
        if m.led_name in _pzb_leds:
            m.requires_endpoint_false = LZB_PR + "ULightState"

    profile = Profile(
        name="Profilo DB BR 406 ICE 3 (PZB/LZB/SIFA)",
        description="DB BR 406 ICE 3 — PZB/LZB/SIFA/Porte, senza MFA",
        train_class="BR406",
    )
    profile.set_mappings(mappings)
    return profile


# ============================================================
# Registro profili treno
# ============================================================

TRAIN_PROFILES = {
    "BR101": {
        "name": "DB BR 101 (Expert)",
        "description": "BR 101 (Expert) — PZB/LZB/SIFA con pannello MFA",
        "patterns": ["BR101", "BR_101"],
        "creator": create_default_profile,
    },
    "Vectron": {
        "name": "DB Vectron",
        "description": "Vectron — PZB/LZB/SIFA senza pannello MFA",
        "patterns": ["Vectron"],
        "creator": create_vectron_profile,
    },
    "Bpmmbdzf": {
        "name": "Bpmmbdzf (Expert) (Cab Car)",
        "description": "Carrozza pilota — stessi indicatori MFA della BR101 (Expert)",
        "patterns": ["Bpmmbdzf"],
        "creator": create_bpmmbdzf_profile,
    },
    "BR146": {
        "name": "DB BR 146.2",
        "description": "BR 146.2 — PZB_V2/LZB_Service/SIFA diretto, senza MFA",
        "patterns": ["BR146", "BR_146"],
        "creator": create_br146_profile,
    },
    "BR114": {
        "name": "DB BR 114",
        "description": "BR 114 — PZB/SIFA, senza LZB, senza MFA",
        "patterns": ["BR114", "BR_114"],
        "creator": create_br114_profile,
    },
    "BR411": {
        "name": "DB BR 411 ICE-T",
        "description": "BR 411 ICE-T — PZB_V3/LZB/SIFA, senza MFA",
        "patterns": ["BR411", "BR_411"],
        "creator": create_br411_profile,
    },
    "BR406": {
        "name": "DB BR 406 ICE 3",
        "description": "BR 406 ICE 3 — PZB/LZB/SIFA/Porte, senza MFA",
        "patterns": ["BR406", "BR_406", "ICE3M"],
        "creator": create_br406_profile,
    },
}


def detect_profile_id(object_class: str) -> Optional[str]:
    """
    Dato l'ObjectClass del treno (es. 'RVM_FTF_DB_Vectron_C'),
    ritorna l'ID del profilo corrispondente o None.
    """
    if not object_class:
        return None
    oc_lower = object_class.lower()
    for profile_id, info in TRAIN_PROFILES.items():
        for pattern in info["patterns"]:
            if pattern.lower() in oc_lower:
                return profile_id
    return None


def get_profile_by_id(profile_id: str) -> Optional[Profile]:
    """Crea e ritorna il profilo dato il suo ID."""
    info = TRAIN_PROFILES.get(profile_id)
    if info:
        return info["creator"]()
    return None


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
