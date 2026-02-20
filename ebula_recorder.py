"""
EBuLa Route Recorder — Registra tratta da TSW6 live
=====================================================
Registra dati in tempo reale da TSW6 (GPS, velocità, limiti, pendenze,
segnali, porte) durante una corsa reale, poi converte la registrazione
in un file .ebula.json per il Buchfahrplan.

Classi:
- RecordingSample: singolo campione dati
- RouteRecording: registrazione completa (metadati + campioni)
- RouteRecorder: registra campioni dal polling TSW6 API
- RecordingConverter: converte registrazione → EBuLaTimetable (.ebula.json)

Distanza: calcolata con formula Haversine da coordinate GPS (lon/lat).
Stazioni: rilevate da velocità ≈ 0 + porte aperte + sosta > 15 secondi.
"""

import json
import math
import os
import copy
import logging
import threading
import time
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path
from datetime import datetime

from ebula_data import (
    EBuLaTimetable, EBuLaRouteInfo, EBuLaEntry, EntryType,
    save_timetable, EBULA_DIR,
)

logger = logging.getLogger("EBuLa.Recorder")

# Directory registrazioni raw
RECORDINGS_DIR = EBULA_DIR / "recordings"


# ============================================================
# Haversine — distanza GPS in metri
# ============================================================

_EARTH_RADIUS_M = 6_371_000.0  # Raggio medio Terra in metri


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Distanza in METRI tra due punti GPS (Haversine).
    
    Precisione: ~0.3% per distanze < 100km (più che sufficiente per treni).
    """
    if lat1 == lat2 and lon1 == lon2:
        return 0.0
    
    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)
    
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return _EARTH_RADIUS_M * c


# ============================================================
# RecordingSample — singolo campione
# ============================================================

@dataclass
class RecordingSample:
    """Un singolo campione dati registrato da TSW6."""
    
    # Timing
    real_time: float = 0.0              # time.monotonic() — per calcolo dt
    wall_time: str = ""                 # Ora reale ISO8601
    sim_time_iso: str = ""              # Ora simulazione ISO8601 da TimeOfDay
    
    # GPS
    latitude: float = 0.0
    longitude: float = 0.0
    
    # Velocità
    speed_ms: float = 0.0              # Velocità attuale [m/s]
    
    # Limiti velocità
    speed_limit_ms: float = 0.0        # Limite corrente [m/s]
    next_speed_limit_ms: float = 0.0   # Prossimo limite [m/s]
    dist_to_next_limit_m: float = 0.0  # Distanza al prossimo limite [m]
    track_max_speed_ms: float = 0.0    # Velocità max tratta [m/s]
    
    # Pendenza
    gradient: float = 0.0             # Pendenza [‰ circa — valore grezzo API]
    
    # Segnali
    signal_aspect: str = ""            # "Clear", "Stop", "Warning", ecc.
    dist_to_signal_m: float = 0.0      # Distanza al prossimo segnale [m]
    
    # Porte
    doors_unlocked: bool = False
    
    # Distanza cumulativa (calcolata)
    cumulative_distance_m: float = 0.0


# ============================================================
# RouteRecording — registrazione completa
# ============================================================

@dataclass
class RouteRecording:
    """Registrazione completa di una corsa TSW6."""
    
    # Versione formato
    format_version: int = 1
    
    # Metadati auto-rilevati
    service_name: str = ""             # currentServiceName (es. "RE1-26815")
    object_class: str = ""             # ObjectClass treno (es. "RVM_DRA_DB_BR146-2_C")
    player_name: str = ""              # playerProfileName
    
    # Timing registrazione
    started_at: str = ""               # ISO8601 ora reale inizio
    stopped_at: str = ""               # ISO8601 ora reale fine
    sim_start_time: str = ""           # ISO8601 ora simulazione inizio
    sim_end_time: str = ""             # ISO8601 ora simulazione fine
    duration_seconds: float = 0.0      # Durata reale in secondi
    
    # Distanza totale (Haversine)
    total_distance_m: float = 0.0
    
    # Campioni
    samples: List[RecordingSample] = field(default_factory=list)
    
    @property
    def total_distance_km(self) -> float:
        return self.total_distance_m / 1000.0
    
    @property
    def sample_count(self) -> int:
        return len(self.samples)


# ============================================================
# RouteRecorder — registra campioni da TSW6 API
# ============================================================

class RouteRecorder:
    """
    Registra dati in tempo reale da TSW6 API.
    
    Gira in un thread separato, campiona ogni ~1 secondo.
    Usa direttamente TSW6API.get_raw() per leggere i dati necessari
    (indipendente dal poller LED che usa subscriptions).
    
    Endpoints letti:
    - DriverAid.PlayerInfo → geoLocation, currentServiceName
    - DriverAid.Data → speedLimit, nextSpeedLimit, gradient, signalAspectClass
    - TimeOfDay.Data → LocalTimeISO8601
    - CurrentDrivableActor.Function.HUD_GetSpeed → velocità attuale
    - CurrentDrivableActor.ObjectClass → classe treno
    - Doors endpoint (varia per profilo: DriverAssist, DoorLockSignal, ecc.)
    """
    
    SAMPLE_INTERVAL = 1.0  # Secondi tra campioni
    
    # Soglia velocità per "fermo" [m/s]
    STOPPED_THRESHOLD_MS = 0.5  # ~1.8 km/h
    
    def __init__(self, api):
        """
        Args:
            api: TSW6API connessa
        """
        self.api = api
        self.recording: Optional[RouteRecording] = None
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # Distanza cumulativa
        self._cumulative_m: float = 0.0
        self._last_lat: float = 0.0
        self._last_lon: float = 0.0
        self._has_first_gps: bool = False
        
        # Callback per aggiornamento stato GUI
        self._on_sample: Optional[callable] = None
        self._on_error: Optional[callable] = None
        
        # Endpoint porte (configurabile dal profilo)
        self._doors_endpoint: str = ""
    
    @property
    def is_recording(self) -> bool:
        return self._running
    
    @property
    def sample_count(self) -> int:
        with self._lock:
            return len(self.recording.samples) if self.recording else 0
    
    @property
    def distance_km(self) -> float:
        with self._lock:
            return self._cumulative_m / 1000.0
    
    @property
    def elapsed_seconds(self) -> float:
        if not self.recording or not self.recording.started_at:
            return 0.0
        with self._lock:
            if self.recording.samples:
                return self.recording.samples[-1].real_time - self.recording.samples[0].real_time
        return 0.0
    
    def set_doors_endpoint(self, endpoint: str):
        """Imposta l'endpoint porte per il profilo corrente."""
        self._doors_endpoint = endpoint
    
    def set_on_sample(self, callback: callable):
        """Callback chiamato ad ogni campione (sample_count, distance_km, elapsed_s)."""
        self._on_sample = callback
    
    def set_on_error(self, callback: callable):
        """Callback chiamato su errore (message: str)."""
        self._on_error = callback
    
    def start(self) -> bool:
        """
        Avvia la registrazione.
        
        Returns:
            True se avviata, False se errore.
        """
        if self._running:
            return False
        
        # Verifica connessione API
        try:
            self.api.info()
        except Exception as e:
            logger.error(f"Recorder: TSW6 non raggiungibile: {e}")
            if self._on_error:
                self._on_error(f"TSW6 non raggiungibile: {e}")
            return False
        
        # Rileva metadati iniziali
        rec = RouteRecording()
        rec.started_at = datetime.now().isoformat()
        
        try:
            pi = self.api.get_raw("DriverAid.PlayerInfo").get("Values", {})
            rec.service_name = pi.get("currentServiceName", "")
            rec.player_name = pi.get("playerProfileName", "")
        except Exception:
            pass
        
        try:
            rec.object_class = str(self.api.get("CurrentDrivableActor.ObjectClass") or "")
        except Exception:
            pass
        
        try:
            tod = self.api.get_raw("TimeOfDay.Data").get("Values", {})
            rec.sim_start_time = tod.get("LocalTimeISO8601", "")
        except Exception:
            pass
        
        logger.info(f"Recorder: avvio — Service={rec.service_name}, "
                     f"Train={rec.object_class}")
        
        self.recording = rec
        self._cumulative_m = 0.0
        self._has_first_gps = False
        self._last_lat = 0.0
        self._last_lon = 0.0
        
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, 
                                         name="EBuLa-Recorder")
        self._thread.start()
        return True
    
    def stop(self) -> Optional[RouteRecording]:
        """
        Ferma la registrazione e ritorna il recording.
        
        Returns:
            RouteRecording completa, o None se non attiva.
        """
        if not self._running:
            return None
        
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None
        
        with self._lock:
            if self.recording:
                self.recording.stopped_at = datetime.now().isoformat()
                self.recording.total_distance_m = self._cumulative_m
                
                if self.recording.samples:
                    first = self.recording.samples[0]
                    last = self.recording.samples[-1]
                    self.recording.duration_seconds = last.real_time - first.real_time
                    self.recording.sim_end_time = last.sim_time_iso
                
                logger.info(f"Recorder: stop — {self.recording.sample_count} campioni, "
                             f"{self.recording.total_distance_km:.2f} km, "
                             f"{self.recording.duration_seconds:.0f}s")
            
            return copy.deepcopy(self.recording)
    
    def save_recording(self, recording: RouteRecording = None, 
                        filepath: str = None) -> Optional[str]:
        """
        Salva la registrazione raw come .recording.json.
        
        Args:
            recording: Registrazione da salvare (default: self.recording)
            filepath: Path file (default: auto-generato da service_name + timestamp)
        
        Returns:
            Path file salvato, o None se errore.
        """
        rec = recording or self.recording
        if not rec or not rec.samples:
            return None
        
        if not filepath:
            RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
            safe_name = (rec.service_name or "unknown").replace("/", "_").replace("\\", "_")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = str(RECORDINGS_DIR / f"{safe_name}_{timestamp}.recording.json")
        
        try:
            data = {
                "format_version": rec.format_version,
                "service_name": rec.service_name,
                "object_class": rec.object_class,
                "player_name": rec.player_name,
                "started_at": rec.started_at,
                "stopped_at": rec.stopped_at,
                "sim_start_time": rec.sim_start_time,
                "sim_end_time": rec.sim_end_time,
                "duration_seconds": rec.duration_seconds,
                "total_distance_m": rec.total_distance_m,
                "sample_count": rec.sample_count,
                "samples": [asdict(s) for s in rec.samples],
            }
            
            os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=1, ensure_ascii=False)
            
            logger.info(f"Recorder: registrazione salvata: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Recorder: errore salvataggio: {e}")
            return None
    
    # --------------------------------------------------------
    # Thread di polling
    # --------------------------------------------------------
    
    def _poll_loop(self):
        """Thread loop: campiona TSW6 API ogni SAMPLE_INTERVAL secondi."""
        while self._running:
            try:
                sample = self._capture_sample()
                if sample:
                    with self._lock:
                        self.recording.samples.append(sample)
                    
                    if self._on_sample:
                        try:
                            self._on_sample(
                                self.sample_count,
                                self.distance_km,
                                self.elapsed_seconds
                            )
                        except Exception:
                            pass
            except Exception as e:
                logger.warning(f"Recorder: errore campionamento: {e}")
                if self._on_error:
                    try:
                        self._on_error(str(e))
                    except Exception:
                        pass
            
            time.sleep(self.SAMPLE_INTERVAL)
    
    def _capture_sample(self) -> Optional[RecordingSample]:
        """
        Cattura un singolo campione da TSW6 API.
        
        Fa 3-4 chiamate API in sequenza (~50-100ms totali):
        1. DriverAid.PlayerInfo → GPS + service
        2. DriverAid.Data → speed limit, gradient, signal
        3. TimeOfDay.Data → sim time  
        4. HUD_GetSpeed → velocità attuale
        5. Doors endpoint (opzionale)
        """
        sample = RecordingSample()
        sample.real_time = time.monotonic()
        sample.wall_time = datetime.now().isoformat()
        
        # 1) PlayerInfo — GPS
        try:
            pi = self.api.get_raw("DriverAid.PlayerInfo").get("Values", {})
            geo = pi.get("geoLocation", {})
            sample.latitude = geo.get("latitude", 0.0)
            sample.longitude = geo.get("longitude", 0.0)
        except Exception as e:
            logger.debug(f"Recorder: PlayerInfo error: {e}")
            return None  # GPS è essenziale
        
        # Aggiorna distanza GPS
        if sample.latitude != 0.0 and sample.longitude != 0.0:
            if self._has_first_gps:
                delta_m = haversine_m(self._last_lat, self._last_lon,
                                      sample.latitude, sample.longitude)
                # Filtra salti GPS > 500m (errore o teleport)
                if delta_m < 500.0:
                    self._cumulative_m += delta_m
            
            self._last_lat = sample.latitude
            self._last_lon = sample.longitude
            self._has_first_gps = True
        
        sample.cumulative_distance_m = self._cumulative_m
        
        # 2) DriverAid.Data — limiti, pendenza, segnali
        try:
            da = self.api.get_raw("DriverAid.Data").get("Values", {})
            
            sl = da.get("speedLimit", {})
            if isinstance(sl, dict):
                sample.speed_limit_ms = sl.get("value", 0.0)
            elif isinstance(sl, (int, float)):
                sample.speed_limit_ms = float(sl)
            
            nsl = da.get("nextSpeedLimit", {})
            if isinstance(nsl, dict):
                sample.next_speed_limit_ms = nsl.get("value", 0.0)
            elif isinstance(nsl, (int, float)):
                sample.next_speed_limit_ms = float(nsl)
            
            sample.dist_to_next_limit_m = float(da.get("distanceToNextSpeedLimit", 0.0))
            
            tms = da.get("trackMaxSpeed", {})
            if isinstance(tms, dict):
                sample.track_max_speed_ms = tms.get("value", 0.0)
            elif isinstance(tms, (int, float)):
                sample.track_max_speed_ms = float(tms)
            
            sample.gradient = float(da.get("gradient", 0.0))
            sample.signal_aspect = str(da.get("signalAspectClass", ""))
            sample.dist_to_signal_m = float(da.get("distanceToSignal", 0.0))
        except Exception as e:
            logger.debug(f"Recorder: DriverAid.Data error: {e}")
        
        # 3) TimeOfDay — ora simulazione
        try:
            tod = self.api.get_raw("TimeOfDay.Data").get("Values", {})
            sample.sim_time_iso = tod.get("LocalTimeISO8601", "")
        except Exception as e:
            logger.debug(f"Recorder: TimeOfDay error: {e}")
        
        # 4) Velocità attuale
        try:
            speed_val = self.api.get("CurrentDrivableActor.Function.HUD_GetSpeed")
            if speed_val is not None:
                sample.speed_ms = float(speed_val)
        except Exception as e:
            logger.debug(f"Recorder: HUD_GetSpeed error: {e}")
        
        # 5) Porte (opzionale — endpoint varia per profilo)
        if self._doors_endpoint:
            try:
                doors_val = self.api.get(self._doors_endpoint)
                if doors_val is not None:
                    sample.doors_unlocked = bool(doors_val)
            except Exception:
                pass
        
        return sample


# ============================================================
# Load recording from file
# ============================================================

def load_recording(filepath: str) -> Optional[RouteRecording]:
    """Carica una registrazione da file .recording.json."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        rec = RouteRecording()
        rec.format_version = data.get("format_version", 1)
        rec.service_name = data.get("service_name", "")
        rec.object_class = data.get("object_class", "")
        rec.player_name = data.get("player_name", "")
        rec.started_at = data.get("started_at", "")
        rec.stopped_at = data.get("stopped_at", "")
        rec.sim_start_time = data.get("sim_start_time", "")
        rec.sim_end_time = data.get("sim_end_time", "")
        rec.duration_seconds = data.get("duration_seconds", 0.0)
        rec.total_distance_m = data.get("total_distance_m", 0.0)
        
        for sd in data.get("samples", []):
            s = RecordingSample(**{
                k: v for k, v in sd.items()
                if k in RecordingSample.__dataclass_fields__
            })
            rec.samples.append(s)
        
        logger.info(f"Recording caricata: {filepath} ({rec.sample_count} campioni, "
                     f"{rec.total_distance_km:.2f} km)")
        return rec
    except Exception as e:
        logger.error(f"Errore caricamento recording {filepath}: {e}")
        return None


# ============================================================
# RecordingConverter — Converte recording → EBuLaTimetable
# ============================================================

class RecordingConverter:
    """
    Converte una RouteRecording grezza in un EBuLaTimetable.
    
    Algoritmo:
    1. Rileva stazioni: velocità ≈ 0 per > MIN_STOP_DURATION_S con porte aperte
    2. Calcola km reali da GPS Haversine
    3. Rileva cambi limite velocità significativi
    4. Rileva cambi pendenza significativi
    5. Estrae orari arrivo/partenza dalle stazioni
    6. Compila EBuLaRouteInfo dai metadati
    """
    
    # Parametri di rilevamento
    MIN_STOP_DURATION_S = 15.0    # Min secondi fermo per considerare una stazione
    STOPPED_SPEED_MS = 0.5        # Soglia "fermo" [m/s] (~1.8 km/h)
    SPEED_CHANGE_THRESHOLD_KMH = 5.0  # Min differenza per registrare cambio limit [km/h]
    GRADIENT_CHANGE_THRESHOLD = 2.0    # Min differenza per registrare cambio pendenza [‰]
    MIN_KM_BETWEEN_ENTRIES = 0.1       # Min km tra due entry (anti-spam)
    
    def __init__(self, recording: RouteRecording):
        self.recording = recording
        self._stations: List[Dict] = []       # Stazioni rilevate
        self._speed_changes: List[Dict] = []  # Cambi velocità
        self._gradient_changes: List[Dict] = []  # Cambi pendenza
    
    def convert(self) -> Optional[EBuLaTimetable]:
        """
        Esegue la conversione completa.
        
        Returns:
            EBuLaTimetable pronto per il salvataggio, o None se errore.
        """
        if not self.recording or not self.recording.samples:
            logger.error("Converter: nessun campione nella registrazione")
            return None
        
        if len(self.recording.samples) < 10:
            logger.error("Converter: troppo pochi campioni (min 10)")
            return None
        
        logger.info(f"Converter: inizio conversione — {self.recording.sample_count} campioni, "
                     f"{self.recording.total_distance_km:.2f} km")
        
        # Fase 1: Rileva stazioni (fermate)
        self._detect_stations()
        
        # Fase 2: Rileva cambi limite velocità
        self._detect_speed_changes()
        
        # Fase 3: Rileva cambi pendenza
        self._detect_gradient_changes()
        
        # Fase 4: Compila il timetable
        tt = self._build_timetable()
        
        errors = tt.validate()
        if errors:
            logger.warning(f"Converter: timetable ha {len(errors)} warnings: {errors[:5]}")
        
        logger.info(f"Converter: completato — {len(tt.entries)} entries, "
                     f"{len(tt.get_stops())} fermate")
        return tt
    
    # --------------------------------------------------------
    # Fase 1: Rileva stazioni
    # --------------------------------------------------------
    
    def _detect_stations(self):
        """
        Rileva stazioni dal profilo velocità.
        
        Una stazione è un punto dove:
        - Velocità < STOPPED_SPEED_MS per > MIN_STOP_DURATION_S
        - Opzionalmente porte aperte (conferma, ma non obbligatorio)
        
        La prima e l'ultima posizione sono sempre considerate stazioni.
        """
        self._stations = []
        samples = self.recording.samples
        
        # Sempre aggiungi stazione di partenza
        first = samples[0]
        self._stations.append({
            "km": first.cumulative_distance_m / 1000.0,
            "sim_time": self._extract_time(first.sim_time_iso),
            "arrival": "",
            "departure": self._extract_time(first.sim_time_iso),
            "doors": first.doors_unlocked,
            "lat": first.latitude,
            "lon": first.longitude,
            "sample_idx": 0,
            "is_first": True,
        })
        
        # Rileva soste intermedie
        in_stop = False
        stop_start_idx = 0
        
        for i, s in enumerate(samples):
            if s.speed_ms < self.STOPPED_SPEED_MS:
                if not in_stop:
                    in_stop = True
                    stop_start_idx = i
            else:
                if in_stop:
                    # Fine sosta — controlla durata
                    stop_end_idx = i - 1
                    stop_start = samples[stop_start_idx]
                    stop_end = samples[stop_end_idx]
                    duration = stop_end.real_time - stop_start.real_time
                    
                    if duration >= self.MIN_STOP_DURATION_S:
                        # Punto medio della sosta
                        mid_idx = (stop_start_idx + stop_end_idx) // 2
                        mid = samples[mid_idx]
                        
                        # Controlla che non sia troppo vicina alla stazione precedente
                        km = mid.cumulative_distance_m / 1000.0
                        if self._stations:
                            last_km = self._stations[-1]["km"]
                            if abs(km - last_km) < 0.3:
                                in_stop = False
                                continue
                        
                        # Controlla se porte aperte durante la sosta
                        doors_open = any(
                            samples[j].doors_unlocked 
                            for j in range(stop_start_idx, min(stop_end_idx + 1, len(samples)))
                        )
                        
                        self._stations.append({
                            "km": km,
                            "sim_time": self._extract_time(mid.sim_time_iso),
                            "arrival": self._extract_time(stop_start.sim_time_iso),
                            "departure": self._extract_time(stop_end.sim_time_iso),
                            "doors": doors_open,
                            "lat": mid.latitude,
                            "lon": mid.longitude,
                            "sample_idx": mid_idx,
                            "duration_s": duration,
                            "is_first": False,
                        })
                        
                        logger.debug(f"Stazione rilevata a km {km:.1f}, "
                                     f"durata {duration:.0f}s, porte={'sì' if doors_open else 'no'}")
                    
                    in_stop = False
        
        # Controlla se siamo fermi alla fine
        if in_stop:
            stop_start = samples[stop_start_idx]
            stop_end = samples[-1]
            duration = stop_end.real_time - stop_start.real_time
            if duration >= self.MIN_STOP_DURATION_S:
                km = stop_end.cumulative_distance_m / 1000.0
                if not self._stations or abs(km - self._stations[-1]["km"]) >= 0.3:
                    self._stations.append({
                        "km": km,
                        "sim_time": self._extract_time(stop_end.sim_time_iso),
                        "arrival": self._extract_time(stop_start.sim_time_iso),
                        "departure": "",
                        "doors": stop_end.doors_unlocked,
                        "lat": stop_end.latitude,
                        "lon": stop_end.longitude,
                        "sample_idx": len(samples) - 1,
                        "is_last": True,
                    })
        
        # Se l'ultima posizione non è una stazione, aggiungila come destinazione
        last = samples[-1]
        last_km = last.cumulative_distance_m / 1000.0
        if self._stations:
            if abs(last_km - self._stations[-1]["km"]) >= 0.3:
                self._stations.append({
                    "km": last_km,
                    "sim_time": self._extract_time(last.sim_time_iso),
                    "arrival": self._extract_time(last.sim_time_iso),
                    "departure": "",
                    "doors": False,
                    "lat": last.latitude,
                    "lon": last.longitude,
                    "sample_idx": len(samples) - 1,
                    "is_last": True,
                })
        
        logger.info(f"Converter: {len(self._stations)} stazioni rilevate")
    
    # --------------------------------------------------------
    # Fase 2: Rileva cambi limite velocità
    # --------------------------------------------------------
    
    def _detect_speed_changes(self):
        """
        Rileva cambi significativi nel limite di velocità lungo la tratta.
        
        Un cambio è registrato quando speedLimit cambia di più di
        SPEED_CHANGE_THRESHOLD_KMH rispetto all'ultimo cambio registrato.
        """
        self._speed_changes = []
        samples = self.recording.samples
        
        last_limit_kmh = -1.0
        last_change_km = -999.0
        
        for s in samples:
            current_limit_kmh = s.speed_limit_ms * 3.6
            km = s.cumulative_distance_m / 1000.0
            
            if current_limit_kmh <= 0:
                continue
            
            diff = abs(current_limit_kmh - last_limit_kmh)
            km_since_last = km - last_change_km
            
            if diff >= self.SPEED_CHANGE_THRESHOLD_KMH and km_since_last >= self.MIN_KM_BETWEEN_ENTRIES:
                self._speed_changes.append({
                    "km": km,
                    "speed_limit_kmh": round(current_limit_kmh),
                    "lat": s.latitude,
                    "lon": s.longitude,
                })
                last_limit_kmh = current_limit_kmh
                last_change_km = km
        
        logger.info(f"Converter: {len(self._speed_changes)} cambi velocità rilevati")
    
    # --------------------------------------------------------
    # Fase 3: Rileva cambi pendenza
    # --------------------------------------------------------
    
    def _detect_gradient_changes(self):
        """
        Rileva cambi significativi nella pendenza.
        """
        self._gradient_changes = []
        samples = self.recording.samples
        
        last_gradient = None
        last_change_km = -999.0
        
        for s in samples:
            km = s.cumulative_distance_m / 1000.0
            gradient = s.gradient
            km_since_last = km - last_change_km
            
            if last_gradient is None:
                last_gradient = gradient
                last_change_km = km
                self._gradient_changes.append({
                    "km": km,
                    "gradient": round(gradient, 1),
                })
                continue
            
            diff = abs(gradient - last_gradient)
            if diff >= self.GRADIENT_CHANGE_THRESHOLD and km_since_last >= self.MIN_KM_BETWEEN_ENTRIES:
                self._gradient_changes.append({
                    "km": km,
                    "gradient": round(gradient, 1),
                })
                last_gradient = gradient
                last_change_km = km
        
        logger.info(f"Converter: {len(self._gradient_changes)} cambi pendenza rilevati")
    
    # --------------------------------------------------------
    # Fase 4: Compila timetable
    # --------------------------------------------------------
    
    def _build_timetable(self) -> EBuLaTimetable:
        """Assembla il timetable finale dalle stazioni, velocità e pendenze rilevate."""
        tt = EBuLaTimetable()
        
        # --- Info tratta ---
        rec = self.recording
        
        # Estrai train number da service_name (es. "RE1-26815" → "RE1")
        train_number = rec.service_name
        service_type = ""
        if rec.service_name:
            # Prova a estrarre il tipo (RE, RB, ICE, IC, S)
            for prefix in ["ICE", "IC", "RE", "RB", "S"]:
                if rec.service_name.upper().startswith(prefix):
                    service_type = prefix
                    # Il numero: tutto prima del '-'
                    train_number = rec.service_name.split("-")[0] if "-" in rec.service_name else rec.service_name
                    break
        
        # Estrai train class da object_class (es. "RVM_DRA_DB_BR146-2_C" → "BR146")
        train_class = ""
        if rec.object_class:
            # Pattern: *_BR<tipo>*
            import re
            m = re.search(r'BR(\d{3})', rec.object_class)
            if m:
                train_class = f"BR{m.group(1)}"
            else:
                # Prova altri pattern (Vectron, ICE3M, ecc.)
                for pat in ["Vectron", "ICE3M", "ICE4"]:
                    if pat in rec.object_class:
                        train_class = pat
                        break
        
        # Nomi stazioni: usa coordinate GPS come placeholder
        station_names = []
        for i, st in enumerate(self._stations):
            if st.get("is_first"):
                station_names.append(f"Stazione partenza ({st['lat']:.4f}, {st['lon']:.4f})")
            elif st.get("is_last"):
                station_names.append(f"Stazione arrivo ({st['lat']:.4f}, {st['lon']:.4f})")
            else:
                doors_note = " [porte aperte]" if st.get("doors") else ""
                dur_note = f" ({st.get('duration_s', 0):.0f}s)" if st.get("duration_s") else ""
                station_names.append(f"Fermata {i}{doors_note}{dur_note} ({st['lat']:.4f}, {st['lon']:.4f})")
        
        # Route name
        first_name = station_names[0] if station_names else "?"
        last_name = station_names[-1] if station_names else "?"
        
        total_km = rec.total_distance_m / 1000.0
        
        tt.info = EBuLaRouteInfo(
            route_name=f"{first_name} → {last_name}",
            train_number=train_number,
            train_class=train_class,
            tsw6_object_class=rec.object_class,
            total_distance_km=round(total_km, 1),
            start_km=0.0,
            end_km=round(total_km, 1),
            is_km_ascending=True,
            service_type=service_type,
            author=f"RouteRecorder ({rec.player_name})" if rec.player_name else "RouteRecorder",
            version="1.0",
            notes=f"Registrazione automatica — {rec.service_name} — {rec.started_at[:10] if rec.started_at else ''}",
        )
        
        # --- Entries ---
        entries: List[EBuLaEntry] = []
        
        # Stazioni
        for i, st in enumerate(self._stations):
            entry = EBuLaEntry(
                km=round(st["km"], 2),
                type=EntryType.STATION,
                name=station_names[i] if i < len(station_names) else f"Stazione {i}",
                arrival=st.get("arrival", ""),
                departure=st.get("departure", ""),
                is_stopping=True,
            )
            entries.append(entry)
        
        # Cambi velocità (solo se non coincidono con una stazione ±0.2km)
        station_kms = {round(st["km"], 1) for st in self._stations}
        
        for sc in self._speed_changes:
            sc_km_r = round(sc["km"], 1)
            too_close = any(abs(sc_km_r - skm) < 0.2 for skm in station_kms)
            
            if too_close:
                # Aggiungi il speed_limit alla stazione più vicina
                for entry in entries:
                    if entry.type == EntryType.STATION and abs(entry.km - sc["km"]) < 0.3:
                        entry.speed_limit = sc["speed_limit_kmh"]
                        break
            else:
                entries.append(EBuLaEntry(
                    km=round(sc["km"], 2),
                    type=EntryType.SPEED_CHANGE,
                    speed_limit=sc["speed_limit_kmh"],
                    is_stopping=False,
                ))
        
        # Cambi pendenza (solo se non coincidono con un'altra entry ±0.1km)
        existing_kms = {round(e.km, 1) for e in entries}
        
        for gc in self._gradient_changes:
            gc_km_r = round(gc["km"], 1)
            too_close = any(abs(gc_km_r - ekm) < 0.1 for ekm in existing_kms)
            
            if too_close:
                # Aggiungi il gradient alla entry più vicina
                for entry in entries:
                    if abs(entry.km - gc["km"]) < 0.2:
                        entry.gradient = gc["gradient"]
                        break
            else:
                entries.append(EBuLaEntry(
                    km=round(gc["km"], 2),
                    type=EntryType.GRADIENT,
                    gradient=gc["gradient"],
                    is_stopping=False,
                ))
                existing_kms.add(gc_km_r)
        
        tt.entries = entries
        tt.sort_entries()
        return tt
    
    # --------------------------------------------------------
    # Utility
    # --------------------------------------------------------
    
    @staticmethod
    def _extract_time(iso_str: str) -> str:
        """
        Estrae "HH:MM" da una stringa ISO8601.
        Es: "2023-02-20T09:56:38.860+00:00" → "09:56"
        """
        if not iso_str:
            return ""
        try:
            # Cerca il pattern T HH:MM:SS
            t_idx = iso_str.index("T")
            time_part = iso_str[t_idx + 1:t_idx + 6]  # "HH:MM"
            if len(time_part) == 5 and time_part[2] == ":":
                return time_part
        except (ValueError, IndexError):
            pass
        return ""


# ============================================================
# Lista registrazioni salvate
# ============================================================

def list_recordings(directory: str = None) -> List[Dict[str, Any]]:
    """
    Lista tutti i file .recording.json nella directory.
    
    Returns:
        Lista di dict con info su ogni registrazione.
    """
    if directory is None:
        directory = str(RECORDINGS_DIR)
    
    result = []
    dir_path = Path(directory)
    
    if not dir_path.exists():
        return result
    
    for f in sorted(dir_path.glob("*.recording.json"), reverse=True):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            
            result.append({
                "path": str(f),
                "filename": f.name,
                "service_name": data.get("service_name", ""),
                "object_class": data.get("object_class", ""),
                "started_at": data.get("started_at", ""),
                "duration_seconds": data.get("duration_seconds", 0),
                "total_distance_m": data.get("total_distance_m", 0),
                "sample_count": data.get("sample_count", 0),
            })
        except Exception:
            result.append({
                "path": str(f),
                "filename": f.name,
                "service_name": "(errore lettura)",
            })
    
    return result
