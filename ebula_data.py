"""
EBuLa Data Models — Elektronischer Buchfahrplan
=================================================
Modelli dati per il sistema EBuLa (Electronic Timetable/Buchfahrplan).

Struttura:
- EBuLaTimetable: Un orario completo per una tratta (es. München → Hamburg)
- EBuLaEntry: Una singola riga dell'orario (fermata o punto chilometrico)
- EBuLaSpeedChange: Cambio limite velocità lungo la tratta
- EBuLaGradient: Pendenza lungo la tratta
- TrainPosition: Posizione corrente del treno sulla tratta

Il formato è ispirato all'EBuLa di Zusi 3 ma adattato per TSW6
dove i dati di tratta NON sono esposti dall'API e vanno forniti
dall'utente tramite file JSON (timetable profiles).

Formato file: JSON con estensione .ebula.json
Directory: ~/.tsw6_arduino_bridge/ebula/
"""

import json
import os
import logging
import time
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path

logger = logging.getLogger("EBuLa")

# Directory timetable
EBULA_DIR = Path(os.path.expanduser("~")) / ".tsw6_arduino_bridge" / "ebula"


# ============================================================
# EBuLa Entry Types
# ============================================================

class EntryType:
    """Tipo di riga nell'orario EBuLa"""
    STATION = "station"           # Fermata (con orario arrivo/partenza)
    HALT = "halt"                 # Fermata facoltativa
    PASS = "pass"                 # Transito (senza fermata)
    SPEED_CHANGE = "speed"        # Cambio limite velocità
    GRADIENT = "gradient"         # Cambio pendenza
    SIGNAL = "signal"             # Segnale
    TUNNEL_START = "tunnel_start" # Inizio tunnel
    TUNNEL_END = "tunnel_end"     # Fine tunnel
    BRIDGE = "bridge"             # Ponte
    CROSSING = "crossing"         # Passaggio a livello
    MARKER = "marker"             # Punto chilometrico generico
    ELECTRIFICATION = "electrif"  # Cambio elettrificazione


# ============================================================
# Dati di una singola riga EBuLa
# ============================================================

@dataclass
class EBuLaEntry:
    """
    Singola riga dell'orario EBuLa.
    
    Ogni entry ha una posizione chilometrica e opzionalmente
    un orario previsto, un limite velocità, una pendenza, ecc.
    
    Campi principali:
    - km: posizione chilometrica sulla tratta
    - type: tipo di voce (station/pass/speed/gradient/...)
    - name: nome stazione o descrizione
    - arrival: orario arrivo previsto ("HH:MM" o "HH:MM:SS")
    - departure: orario partenza previsto ("HH:MM" o "HH:MM:SS")
    - track: binario previsto (es. "3", "2a")
    - speed_limit: limite velocità da questo punto [km/h]
    - gradient: pendenza da questo punto [‰] (positivo=salita)
    - notes: note aggiuntive
    """
    km: float = 0.0
    type: str = EntryType.STATION
    name: str = ""
    
    # Orario (solo per station/halt/pass)
    arrival: str = ""        # "HH:MM" o "HH:MM:SS"
    departure: str = ""      # "HH:MM" o "HH:MM:SS"
    track: str = ""          # Binario
    platform: str = ""       # Banchina
    
    # Velocità
    speed_limit: Optional[float] = None   # km/h, None = nessun cambio
    
    # Pendenza
    gradient: Optional[float] = None      # ‰, None = nessun cambio
    
    # Elettrificazione
    electrification: str = ""  # "AC 15kV", "DC 3kV", "none", ecc.
    
    # Segnale
    signal_type: str = ""      # "Hp", "Ks", "Sv", ecc.
    
    # Note
    notes: str = ""
    
    # Flag
    is_stopping: bool = True   # True se il treno si ferma qui

    def arrival_seconds(self) -> Optional[int]:
        """Converte arrival in secondi dal mezzanotte"""
        return _parse_time_to_seconds(self.arrival)
    
    def departure_seconds(self) -> Optional[int]:
        """Converte departure in secondi dal mezzanotte"""
        return _parse_time_to_seconds(self.departure)


# ============================================================
# Metadati tratta
# ============================================================

@dataclass
class EBuLaRouteInfo:
    """
    Metadata della tratta/servizio.
    """
    route_name: str = ""           # Es. "München Hbf → Hamburg-Altona"
    route_number: str = ""         # Es. "ICE 785"
    train_number: str = ""         # Es. "ICE 785"
    train_class: str = ""          # Es. "BR101", "Vectron", ecc.
    
    # Matching con TSW6 (per auto-selezione)
    tsw6_object_class: str = ""    # Pattern match su ObjectClass
    tsw6_route_match: str = ""     # Pattern match su route name se disponibile
    
    # Matching con Zusi 3 (auto)
    zusi3_zugnummer: str = ""      # Match su zugnummer Zusi
    zusi3_zugdatei: str = ""       # Match su zugdatei Zusi
    
    # Info tratta
    total_distance_km: float = 0.0
    start_km: float = 0.0         # Primo km della tratta
    end_km: float = 0.0           # Ultimo km della tratta
    is_km_ascending: bool = True   # True se km crescono nella direzione di marcia
    
    # Informazioni aggiuntive
    operator: str = ""             # Es. "DB Fernverkehr"
    service_type: str = ""         # "ICE", "IC", "RE", "RB", "S", ecc.
    days: str = ""                 # "Mo-Fr", "täglich", ecc.
    valid_from: str = ""           # Data validità inizio
    valid_to: str = ""             # Data validità fine
    
    # Note
    notes: str = ""
    author: str = ""               # Autore del timetable
    version: str = "1.0"


# ============================================================
# Timetable completo
# ============================================================

@dataclass
class EBuLaTimetable:
    """
    Orario completo EBuLa per una tratta.
    
    Contiene tutte le entry ordinate per km, con metadati
    della tratta e del servizio.
    """
    info: EBuLaRouteInfo = field(default_factory=EBuLaRouteInfo)
    entries: List[EBuLaEntry] = field(default_factory=list)
    
    # Computed
    _station_count: int = 0
    _speed_changes: int = 0
    
    def sort_entries(self):
        """Ordina entries per km"""
        if self.info.is_km_ascending:
            self.entries.sort(key=lambda e: e.km)
        else:
            self.entries.sort(key=lambda e: e.km, reverse=True)
    
    def get_stations(self) -> List[EBuLaEntry]:
        """Ritorna solo le stazioni (con fermata)"""
        return [e for e in self.entries 
                if e.type in (EntryType.STATION, EntryType.HALT)]
    
    def get_stops(self) -> List[EBuLaEntry]:
        """Ritorna solo le fermate programmmate"""
        return [e for e in self.entries 
                if e.type in (EntryType.STATION, EntryType.HALT) and e.is_stopping]
    
    def get_speed_profile(self) -> List[Tuple[float, float]]:
        """Ritorna il profilo velocità: [(km, speed_limit), ...]"""
        profile = []
        for e in self.entries:
            if e.speed_limit is not None:
                profile.append((e.km, e.speed_limit))
        return profile
    
    def get_gradient_profile(self) -> List[Tuple[float, float]]:
        """Ritorna il profilo pendenza: [(km, gradient_permille), ...]"""
        profile = []
        for e in self.entries:
            if e.gradient is not None:
                profile.append((e.km, e.gradient))
        return profile
    
    def get_speed_at_km(self, km: float) -> Optional[float]:
        """Ritorna il limite velocità al km indicato"""
        profile = self.get_speed_profile()
        if not profile:
            return None
        
        current_speed = profile[0][1]
        for p_km, p_speed in profile:
            if self.info.is_km_ascending:
                if p_km <= km:
                    current_speed = p_speed
                else:
                    break
            else:
                if p_km >= km:
                    current_speed = p_speed
                else:
                    break
        return current_speed
    
    def get_next_station(self, km: float) -> Optional[EBuLaEntry]:
        """Ritorna la prossima stazione dopo il km indicato"""
        stations = self.get_stops()
        for s in stations:
            if self.info.is_km_ascending:
                if s.km > km:
                    return s
            else:
                if s.km < km:
                    return s
        return None
    
    def get_prev_station(self, km: float) -> Optional[EBuLaEntry]:
        """Ritorna la stazione precedente al km indicato"""
        stations = self.get_stops()
        prev = None
        for s in stations:
            if self.info.is_km_ascending:
                if s.km < km:
                    prev = s
                else:
                    break
            else:
                if s.km > km:
                    prev = s
                else:
                    break
        return prev
    
    def get_entries_in_range(self, km_start: float, km_end: float) -> List[EBuLaEntry]:
        """Ritorna tutte le entry tra km_start e km_end"""
        return [e for e in self.entries if km_start <= e.km <= km_end]
    
    def validate(self) -> List[str]:
        """Valida il timetable e ritorna lista di errori"""
        errors = []
        
        if not self.info.route_name:
            errors.append("route_name vuoto")
        if not self.entries:
            errors.append("Nessuna entry")
        
        stations = self.get_stations()
        if len(stations) < 2:
            errors.append("Servono almeno 2 stazioni")
        
        # Verifica ordine km
        for i in range(1, len(self.entries)):
            if self.info.is_km_ascending:
                if self.entries[i].km < self.entries[i-1].km:
                    errors.append(f"Entry {i}: km non crescente ({self.entries[i-1].km} → {self.entries[i].km})")
            else:
                if self.entries[i].km > self.entries[i-1].km:
                    errors.append(f"Entry {i}: km non decrescente ({self.entries[i-1].km} → {self.entries[i].km})")
        
        # Verifica orari crescenti
        last_time = None
        for e in self.entries:
            t = e.departure_seconds() or e.arrival_seconds()
            if t is not None:
                if last_time is not None and t < last_time:
                    errors.append(f"Orario non crescente a {e.name} (km {e.km})")
                last_time = t
        
        return errors


# ============================================================
# Posizione treno corrente
# ============================================================

@dataclass 
class TrainPosition:
    """
    Posizione corrente del treno sulla tratta EBuLa.
    
    Aggiornata dal poller TSW6 o dal client Zusi3.
    """
    km: float = 0.0                    # Posizione corrente [km]
    speed_kmh: float = 0.0             # Velocità corrente [km/h]
    sim_time: str = ""                 # Ora simulazione "HH:MM:SS"
    sim_time_seconds: int = 0          # Ora in secondi dal mezzanotte
    
    # Calcolati rispetto al timetable
    current_speed_limit: Optional[float] = None  # Limite velocità attuale
    next_station_name: str = ""
    next_station_km: float = 0.0
    next_station_arrival: str = ""
    distance_to_next_station: float = 0.0  # km
    
    prev_station_name: str = ""
    prev_station_km: float = 0.0
    
    # Ritardo
    delay_seconds: int = 0
    is_delayed: bool = False
    
    # Tracking
    is_tracking: bool = False    # True se stiamo tracciando la posizione
    tracking_method: str = ""    # "speed_integration", "km_marker", "zusi3_km"
    
    # Statistics
    total_distance_covered: float = 0.0  # km percorsi
    last_update_time: float = 0.0        # time.monotonic()


# ============================================================
# Position tracker — stima posizione da velocità (TSW6)
# ============================================================

class PositionTracker:
    """
    Stima la posizione del treno integrando la velocità nel tempo.
    
    Per TSW6: l'API non espone direttamente il km, quindi calcoliamo
    la distanza percorsa integrando speed * dt e aggiorniamo il km
    di partenza dalla fermata corrente.
    
    Per Zusi 3: se disponibile KILOMETRIERUNG, usa quello direttamente.
    """
    
    def __init__(self, timetable: Optional[EBuLaTimetable] = None):
        self.timetable = timetable
        self.position = TrainPosition()
        
        # Integrazione velocità
        self._last_speed_ms: float = 0.0
        self._last_update: float = 0.0
        self._distance_from_start_m: float = 0.0
        self._start_km: float = 0.0
        self._is_ascending: bool = True
        
        # Calibrazione
        self._calibrated: bool = False
        self._station_calibrations: int = 0
        
    def set_timetable(self, timetable: EBuLaTimetable):
        """Imposta o cambia il timetable"""
        self.timetable = timetable
        self._is_ascending = timetable.info.is_km_ascending
        
        # Se ci sono stazioni, parti dalla prima
        stops = timetable.get_stops()
        if stops:
            self._start_km = stops[0].km
            self.position.km = self._start_km
        
        self._update_position_context()
    
    def set_start_km(self, km: float):
        """Imposta manualmente il km di partenza"""
        self._start_km = km
        self._distance_from_start_m = 0.0
        self.position.km = km
        self._calibrated = True
        self._update_position_context()
    
    def update_from_speed(self, speed_ms: float, sim_time_seconds: int = 0):
        """
        Aggiorna la posizione dalla velocità (TSW6 mode).
        
        Integra velocità × Δt per stimare la distanza percorsa.
        """
        now = time.monotonic()
        
        if self._last_update > 0:
            dt = now - self._last_update
            if dt > 0 and dt < 2.0:  # Max 2 secondi di gap
                # Trapezoidal integration
                avg_speed = (self._last_speed_ms + speed_ms) / 2.0
                delta_m = avg_speed * dt
                self._distance_from_start_m += delta_m
                
                # Aggiorna km
                delta_km = self._distance_from_start_m / 1000.0
                if self._is_ascending:
                    self.position.km = self._start_km + delta_km
                else:
                    self.position.km = self._start_km - delta_km
        
        self._last_speed_ms = speed_ms
        self._last_update = now
        self.position.speed_kmh = speed_ms * 3.6
        self.position.last_update_time = now
        self.position.tracking_method = "speed_integration"
        self.position.is_tracking = True
        
        if sim_time_seconds > 0:
            self.position.sim_time_seconds = sim_time_seconds
            h = sim_time_seconds // 3600
            m = (sim_time_seconds % 3600) // 60
            s = sim_time_seconds % 60
            self.position.sim_time = f"{h:02d}:{m:02d}:{s:02d}"
        
        self._update_position_context()
    
    def update_from_km(self, km: float, speed_ms: float = 0.0, 
                       sim_time_seconds: int = 0):
        """
        Aggiorna la posizione dal km reale (Zusi 3 mode).
        
        Usa il dato KILOMETRIERUNG dal protocollo Zusi.
        """
        self.position.km = km
        self.position.speed_kmh = speed_ms * 3.6
        self.position.last_update_time = time.monotonic()
        self.position.tracking_method = "km_marker"
        self.position.is_tracking = True
        
        if sim_time_seconds > 0:
            self.position.sim_time_seconds = sim_time_seconds
            h = sim_time_seconds // 3600
            m = (sim_time_seconds % 3600) // 60
            s = sim_time_seconds % 60
            self.position.sim_time = f"{h:02d}:{m:02d}:{s:02d}"
        
        self._update_position_context()
    
    def calibrate_at_station(self, station_name: str):
        """
        Calibra la posizione a una stazione nota.
        
        Utile quando il treno si ferma a una stazione: resetta
        il km alla posizione nota nel timetable.
        """
        if not self.timetable:
            return
        
        for entry in self.timetable.entries:
            if entry.type in (EntryType.STATION, EntryType.HALT):
                if station_name.lower() in entry.name.lower():
                    self._start_km = entry.km
                    self._distance_from_start_m = 0.0
                    self.position.km = entry.km
                    self._calibrated = True
                    self._station_calibrations += 1
                    logger.info(f"Posizione calibrata a {entry.name} (km {entry.km})")
                    self._update_position_context()
                    return
    
    def calibrate_at_stop(self):
        """
        Auto-calibra quando il treno è fermo a una fermata.
        
        Confronta orario simulazione con orario previsto
        per determinare a quale stazione ci troviamo.
        """
        if not self.timetable or self.position.speed_kmh > 2.0:
            return  # Calibra solo se fermo
        
        sim_t = self.position.sim_time_seconds
        if sim_t == 0:
            return
        
        best_match = None
        best_diff = 999999
        
        for entry in self.timetable.get_stops():
            arr = entry.arrival_seconds()
            dep = entry.departure_seconds()
            
            if arr is not None:
                diff = abs(sim_t - arr)
                if diff < best_diff and diff < 120:  # Max 2 min di scarto
                    best_diff = diff
                    best_match = entry
            
            if dep is not None:
                diff = abs(sim_t - dep)
                if diff < best_diff and diff < 120:
                    best_diff = diff
                    best_match = entry
        
        if best_match:
            self._start_km = best_match.km
            self._distance_from_start_m = 0.0
            self.position.km = best_match.km
            self._calibrated = True
            self._station_calibrations += 1
            logger.info(f"Auto-calibrato a {best_match.name} (km {best_match.km}, diff {best_diff}s)")
            self._update_position_context()
    
    def _update_position_context(self):
        """Aggiorna dati derivati dalla posizione"""
        if not self.timetable:
            return
        
        # Limite velocità corrente
        self.position.current_speed_limit = self.timetable.get_speed_at_km(self.position.km)
        
        # Stazione successiva
        next_st = self.timetable.get_next_station(self.position.km)
        if next_st:
            self.position.next_station_name = next_st.name
            self.position.next_station_km = next_st.km
            self.position.next_station_arrival = next_st.arrival
            self.position.distance_to_next_station = abs(next_st.km - self.position.km)
            
            # Calcolo ritardo
            if next_st.arrival and self.position.sim_time_seconds > 0:
                arr_s = next_st.arrival_seconds()
                if arr_s is not None:
                    self.position.delay_seconds = self.position.sim_time_seconds - arr_s
                    self.position.is_delayed = self.position.delay_seconds > 30
        
        # Stazione precedente
        prev_st = self.timetable.get_prev_station(self.position.km)
        if prev_st:
            self.position.prev_station_name = prev_st.name
            self.position.prev_station_km = prev_st.km


# ============================================================
# I/O: Salvataggio e caricamento timetable
# ============================================================

def save_timetable(timetable: EBuLaTimetable, filepath: str) -> bool:
    """Salva un timetable come file .ebula.json"""
    try:
        data = {
            "ebula_version": "1.0",
            "info": asdict(timetable.info),
            "entries": [asdict(e) for e in timetable.entries]
        }
        
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Timetable salvato: {filepath}")
        return True
    except Exception as e:
        logger.error(f"Errore salvataggio timetable: {e}")
        return False


def load_timetable(filepath: str) -> Optional[EBuLaTimetable]:
    """Carica un timetable da file .ebula.json"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        tt = EBuLaTimetable()
        
        # Info
        info_data = data.get("info", {})
        tt.info = EBuLaRouteInfo(**{
            k: v for k, v in info_data.items()
            if k in EBuLaRouteInfo.__dataclass_fields__
        })
        
        # Entries
        entries_data = data.get("entries", [])
        for entry_data in entries_data:
            entry = EBuLaEntry(**{
                k: v for k, v in entry_data.items()
                if k in EBuLaEntry.__dataclass_fields__
            })
            tt.entries.append(entry)
        
        # Valida
        errors = tt.validate()
        if errors:
            logger.warning(f"Timetable {filepath} ha {len(errors)} warning: {errors[:3]}")
        
        logger.info(f"Timetable caricato: {filepath} ({len(tt.entries)} entries)")
        return tt
        
    except Exception as e:
        logger.error(f"Errore caricamento timetable {filepath}: {e}")
        return None


def list_timetables(directory: str = None) -> List[Dict[str, str]]:
    """
    Lista tutti i file .ebula.json nella directory.
    
    Ritorna: [{"path": "...", "name": "...", "route": "..."}, ...]
    """
    if directory is None:
        directory = str(EBULA_DIR)
    
    result = []
    dir_path = Path(directory)
    
    if not dir_path.exists():
        return result
    
    for f in sorted(dir_path.glob("*.ebula.json")):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            info = data.get("info", {})
            result.append({
                "path": str(f),
                "filename": f.name,
                "route_name": info.get("route_name", ""),
                "train_number": info.get("train_number", ""),
                "train_class": info.get("train_class", ""),
                "author": info.get("author", ""),
            })
        except Exception:
            result.append({
                "path": str(f),
                "filename": f.name,
                "route_name": "(errore lettura)",
                "train_number": "",
                "train_class": "",
                "author": "",
            })
    
    return result


# ============================================================
# Utility
# ============================================================

def _parse_time_to_seconds(time_str: str) -> Optional[int]:
    """Converte "HH:MM" o "HH:MM:SS" in secondi dal mezzanotte"""
    if not time_str:
        return None
    
    parts = time_str.strip().split(":")
    try:
        if len(parts) == 2:
            return int(parts[0]) * 3600 + int(parts[1]) * 60
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except (ValueError, IndexError):
        pass
    return None


def format_delay(seconds: int) -> str:
    """Formatta il ritardo in minuti (+2, -1, ecc.)"""
    if abs(seconds) < 30:
        return "±0"
    minutes = seconds // 60
    if minutes > 0:
        return f"+{minutes}"
    return str(minutes)


def create_example_timetable() -> EBuLaTimetable:
    """
    Crea un timetable di esempio per test.
    
    Rotta: Köln Hbf → Frankfurt(Main) Hbf (linea del Reno, KBS 471)
    Treno: ICE 123 con BR101
    """
    tt = EBuLaTimetable()
    
    tt.info = EBuLaRouteInfo(
        route_name="Köln Hbf → Frankfurt(Main) Hbf",
        route_number="KBS 471",
        train_number="ICE 123",
        train_class="BR101",
        tsw6_object_class="BR101",
        total_distance_km=177.0,
        start_km=0.0,
        end_km=177.0,
        is_km_ascending=True,
        operator="DB Fernverkehr",
        service_type="ICE",
        author="EBuLa Example",
        version="1.0",
        notes="Esempio per test — dati NON reali",
    )
    
    tt.entries = [
        # Köln Hbf
        EBuLaEntry(km=0.0, type=EntryType.STATION, name="Köln Hbf",
                   arrival="", departure="10:00", track="5",
                   speed_limit=60, is_stopping=True),
        EBuLaEntry(km=0.5, type=EntryType.SPEED_CHANGE, name="",
                   speed_limit=100),
        EBuLaEntry(km=2.0, type=EntryType.SPEED_CHANGE, name="",
                   speed_limit=160),
        
        # Siegburg/Bonn (NBS)
        EBuLaEntry(km=28.0, type=EntryType.SPEED_CHANGE, name="",
                   speed_limit=250),
        EBuLaEntry(km=29.0, type=EntryType.STATION, name="Siegburg/Bonn",
                   arrival="10:12", departure="10:12", 
                   speed_limit=250, is_stopping=False),
        
        # Tunnel Ittenbach
        EBuLaEntry(km=35.0, type=EntryType.TUNNEL_START, name="Tunnel Ittenbach"),
        EBuLaEntry(km=39.0, type=EntryType.TUNNEL_END, name=""),
        
        # Montabaur
        EBuLaEntry(km=71.0, type=EntryType.STATION, name="Montabaur",
                   arrival="10:24", departure="10:24",
                   speed_limit=300, is_stopping=False),
        
        # Limburg Süd
        EBuLaEntry(km=99.0, type=EntryType.STATION, name="Limburg Süd",
                   arrival="10:32", departure="10:32",
                   speed_limit=300, is_stopping=False),
        
        # Wiesbaden junction
        EBuLaEntry(km=140.0, type=EntryType.SPEED_CHANGE, name="",
                   speed_limit=200),
        
        # Frankfurt Flughafen Fernbhf
        EBuLaEntry(km=155.0, type=EntryType.STATION, name="Frankfurt Flughafen Fernbhf",
                   arrival="10:48", departure="10:50", track="fern 7",
                   speed_limit=160, is_stopping=True),
        
        # Avvicinamento Frankfurt
        EBuLaEntry(km=168.0, type=EntryType.SPEED_CHANGE, name="",
                   speed_limit=100),
        EBuLaEntry(km=174.0, type=EntryType.SPEED_CHANGE, name="",
                   speed_limit=60),
        
        # Frankfurt(Main) Hbf
        EBuLaEntry(km=177.0, type=EntryType.STATION, name="Frankfurt(Main) Hbf",
                   arrival="11:02", departure="", track="12",
                   speed_limit=30, is_stopping=True),
    ]
    
    return tt


# ============================================================
# Zusi 3 Buchfahrplan XML Parser
# ============================================================

def parse_zusi3_buchfahrplan_xml(xml_bytes: bytes) -> Optional[EBuLaTimetable]:
    """
    Parsa il Buchfahrplan XML di Zusi 3 e lo converte in EBuLaTimetable.
    
    Il formato XML contiene nodi come:
    <Buchfahrplan>
      <Fahrplaneintrag km="..." name="..." ankunft="..." abfahrt="..." 
                       track="..." vmax="..." neigung="..." />
      ...
    </Buchfahrplan>
    
    Nota: il formato esatto dipende dalla versione di Zusi 3.
    Questa è un'implementazione iniziale che verrà raffinata
    una volta testata con dati reali.
    """
    try:
        import xml.etree.ElementTree as ET
        
        root = ET.fromstring(xml_bytes)
        tt = EBuLaTimetable()
        
        # Cerca info base
        zugnummer = root.findtext("Zugnummer", "")
        strecke = root.findtext("Strecke", "")
        
        tt.info.train_number = zugnummer
        tt.info.route_name = strecke
        
        # Parsing entries
        for elem in root.iter():
            tag = elem.tag.lower()
            
            if "fahrplaneintrag" in tag or "eintrag" in tag:
                entry = EBuLaEntry()
                
                # Km
                km_str = elem.get("km", elem.get("Km", "0"))
                try:
                    entry.km = float(km_str.replace(",", "."))
                except ValueError:
                    entry.km = 0.0
                
                # Nome
                entry.name = elem.get("name", elem.get("Name", ""))
                
                # Tipo
                if entry.name:
                    entry.type = EntryType.STATION
                else:
                    entry.type = EntryType.SPEED_CHANGE
                
                # Orari
                entry.arrival = elem.get("ankunft", elem.get("Ankunft", ""))
                entry.departure = elem.get("abfahrt", elem.get("Abfahrt", ""))
                
                # Binario
                entry.track = elem.get("track", elem.get("Gleis", ""))
                
                # Velocità
                vmax = elem.get("vmax", elem.get("Vmax", ""))
                if vmax:
                    try:
                        entry.speed_limit = float(vmax.replace(",", "."))
                    except ValueError:
                        pass
                
                # Pendenza
                grad = elem.get("neigung", elem.get("Neigung", ""))
                if grad:
                    try:
                        entry.gradient = float(grad.replace(",", "."))
                    except ValueError:
                        pass
                
                # Fermata
                entry.is_stopping = bool(entry.arrival or entry.departure)
                
                tt.entries.append(entry)
        
        tt.sort_entries()
        
        # Calcolo distanza totale
        if tt.entries:
            tt.info.start_km = tt.entries[0].km
            tt.info.end_km = tt.entries[-1].km
            tt.info.total_distance_km = abs(tt.info.end_km - tt.info.start_km)
        
        logger.info(f"Zusi3 Buchfahrplan parsato: {len(tt.entries)} entries, {zugnummer}")
        return tt
        
    except Exception as e:
        logger.error(f"Errore parsing Zusi3 Buchfahrplan XML: {e}")
        return None


# ============================================================
# EBuLa State Manager (thread-safe, SSE-ready)
# ============================================================

class EBuLaStateManager:
    """
    Gestore stato EBuLa thread-safe con supporto SSE.
    
    Stesso pattern di LEDStateManager in led_panel.py:
    usa threading.Condition per wait/notify efficiente.
    """
    
    def __init__(self):
        import threading
        self._lock = threading.Lock()
        self._condition = threading.Condition(self._lock)
        self._version = 0
        
        # Stato corrente
        self.timetable: Optional[EBuLaTimetable] = None
        self.position: TrainPosition = TrainPosition()
        self.tracker: Optional[PositionTracker] = None
        
        # Visible window (per display scorrevole)
        self._window_entries: List[EBuLaEntry] = []
        self._window_km_start: float = 0.0
        self._window_km_end: float = 0.0
    
    def load_timetable(self, timetable: EBuLaTimetable):
        """Carica un nuovo timetable"""
        with self._lock:
            self.timetable = timetable
            self.tracker = PositionTracker(timetable)
            self.position = self.tracker.position
            self._version += 1
            self._condition.notify_all()
    
    def update_position(self, speed_ms: float = 0.0, km: float = None,
                        sim_time_seconds: int = 0):
        """
        Aggiorna posizione treno (chiamato dal poller).
        
        Se km è fornito (Zusi 3) usa quello, altrimenti integra velocità (TSW6).
        """
        with self._lock:
            if not self.tracker:
                return
            
            if km is not None:
                self.tracker.update_from_km(km, speed_ms, sim_time_seconds)
            else:
                self.tracker.update_from_speed(speed_ms, sim_time_seconds)
            
            self.position = self.tracker.position
            self._version += 1
            self._condition.notify_all()
    
    def get_state(self) -> Dict[str, Any]:
        """Ritorna lo stato corrente come dizionario (per SSE/REST)"""
        with self._lock:
            state = {
                "version": self._version,
                "has_timetable": self.timetable is not None,
                "position": asdict(self.position) if self.position else {},
            }
            
            if self.timetable:
                state["route_name"] = self.timetable.info.route_name
                state["train_number"] = self.timetable.info.train_number
                
                # Prossime entries (finestra scorrevole)
                km = self.position.km
                window_km = 20.0  # Mostra ±20 km
                entries_window = self.timetable.get_entries_in_range(
                    km - window_km, km + window_km
                )
                state["entries"] = [asdict(e) for e in entries_window[:30]]
                
                # Speed profile nella finestra
                state["speed_profile"] = [
                    {"km": e.km, "limit": e.speed_limit}
                    for e in entries_window if e.speed_limit is not None
                ]
            
            return state
    
    def wait_for_change(self, last_version: int, timeout: float = 30.0) -> int:
        """Attende un cambio di stato (per SSE). Ritorna la nuova versione."""
        with self._condition:
            while self._version == last_version:
                if not self._condition.wait(timeout=timeout):
                    break  # Timeout
            return self._version


# Singleton
_ebula_state_manager: Optional[EBuLaStateManager] = None

def get_ebula_state_manager() -> EBuLaStateManager:
    """Ritorna il singleton EBuLaStateManager"""
    global _ebula_state_manager
    if _ebula_state_manager is None:
        _ebula_state_manager = EBuLaStateManager()
    return _ebula_state_manager
