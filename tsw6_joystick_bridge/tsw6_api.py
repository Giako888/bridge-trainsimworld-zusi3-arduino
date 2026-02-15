"""
TSW6 External Interface API Client
====================================
Client Python per comunicare con Train Sim World 6 tramite le HTTP API
su TCP porta 31270.

Supporta:
- Lettura automatica della CommAPIKey
- GET /info, /list, /get
- PATCH /set (scrittura valori)
- Subscriptions (POST/GET/DELETE)
- VirtualRailDriver
- Weather Manager
- Time of Day
- Driver Aid
"""

import json
import os
import re
import time
import threading
import logging
from typing import Optional, Dict, List, Any, Callable
from pathlib import Path
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

logger = logging.getLogger("TSW6_API")


# ============================================================
# Utilità URL path encoding
# ============================================================

def encode_path(path: str) -> str:
    """
    URL-encode ogni segmento di un path TSW6, preservando '/' e '.' come separatori.
    
    Codifica caratteri speciali come Ü, parentesi, spazi ecc.
    Esempio: "CurrentFormation/0/MFA_Indicators.Property.Ü_IsActive"
           → "CurrentFormation/0/MFA_Indicators.Property.%C3%9C_IsActive"
    """
    # Splitta per '/' e '.' preservando i separatori
    parts = re.split(r'([/.])', path)
    encoded_parts = []
    for part in parts:
        if part in ('/', '.'):
            encoded_parts.append(part)
        else:
            encoded_parts.append(quote(part, safe=''))
    return ''.join(encoded_parts)


# ============================================================
# Percorsi noti per la CommAPIKey
# ============================================================

def _find_comm_api_key() -> Optional[str]:
    """
    Cerca automaticamente la CommAPIKey nei percorsi noti.
    
    Release: Documents\\My Games\\TrainSimWorld6\\Saved\\Config\\CommAPIKey.txt
    Dev: <installdir>\\WindowsNoEditor\\TS2Prototype\\Saved\\Config\\CommAPIKey.txt
    """
    # Percorso Release
    docs = Path(os.path.expanduser("~")) / "Documents" / "My Games" / "TrainSimWorld6" / "Saved" / "Config" / "CommAPIKey.txt"
    if docs.exists():
        key = docs.read_text(encoding="utf-8").strip()
        if key:
            logger.info(f"CommAPIKey trovata in: {docs}")
            return key

    # Percorso alternativo (OneDrive, ecc.)
    for env_var in ["USERPROFILE", "HOME"]:
        base = os.environ.get(env_var, "")
        if base:
            alt = Path(base) / "Documents" / "My Games" / "TrainSimWorld6" / "Saved" / "Config" / "CommAPIKey.txt"
            if alt.exists():
                key = alt.read_text(encoding="utf-8").strip()
                if key:
                    logger.info(f"CommAPIKey trovata in: {alt}")
                    return key
    
    # Prova anche OneDrive
    onedrive = os.environ.get("OneDrive", "")
    if onedrive:
        alt = Path(onedrive) / "Documents" / "My Games" / "TrainSimWorld6" / "Saved" / "Config" / "CommAPIKey.txt"
        if alt.exists():
            key = alt.read_text(encoding="utf-8").strip()
            if key:
                logger.info(f"CommAPIKey trovata in: {alt}")
                return key

    logger.warning("CommAPIKey non trovata automaticamente")
    return None


class TSW6APIError(Exception):
    """Errore generico dell'API TSW6"""
    pass


class TSW6ConnectionError(TSW6APIError):
    """Impossibile connettersi a TSW6"""
    pass


class TSW6AuthError(TSW6APIError):
    """Chiave API non valida (403)"""
    pass


class TSW6API:
    """
    Client per la TSW6 External Interface API.
    
    Uso:
        api = TSW6API()
        api.connect()  # Trova la chiave e verifica la connessione
        
        # Ottenere dati
        speed = api.get("CurrentDrivableActor.Function.HUD_GetSpeed")
        
        # Impostare valori
        api.set("CurrentDrivableActor/Throttle(Lever)", "InputValue", 0.5)
        
        # Subscriptions
        api.subscribe(1, "CurrentDrivableActor.Function.HUD_GetSpeed")
        api.subscribe(1, "CurrentDrivableActor.Function.HUD_GetBrakeGauge_1")
        data = api.read_subscription(1)
    """
    
    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_PORT = 31270
    
    def __init__(self, host: str = None, port: int = None, api_key: str = None):
        self.host = host or self.DEFAULT_HOST
        self.port = port or self.DEFAULT_PORT
        self.api_key = api_key
        self.base_url = f"http://{self.host}:{self.port}"
        self.connected = False
        self.session = None
        self._lock = threading.Lock()
        
        # Callbacks per eventi
        self._on_connected: Optional[Callable] = None
        self._on_disconnected: Optional[Callable] = None
        self._on_error: Optional[Callable[[str], None]] = None
    
    # --------------------------------------------------------
    # Connessione
    # --------------------------------------------------------
    
    def connect(self, api_key: str = None) -> bool:
        """
        Inizializza la connessione a TSW6.
        
        1. Cerca la CommAPIKey se non fornita
        2. Crea la sessione HTTP
        3. Verifica la connessione con /info
        """
        if not REQUESTS_AVAILABLE:
            raise TSW6APIError("La libreria 'requests' non è installata. Eseguire: pip install requests")
        
        # Trova la chiave
        if api_key:
            self.api_key = api_key
        elif not self.api_key:
            self.api_key = _find_comm_api_key()
        
        if not self.api_key:
            raise TSW6AuthError(
                "CommAPIKey non trovata. Assicurati che TSW6 sia stato avviato "
                "almeno una volta con il parametro -HTTPAPI, oppure fornisci la chiave manualmente."
            )
        
        # Crea sessione con retry automatico
        self.session = requests.Session()
        self.session.headers.update({
            "DTGCommKey": self.api_key,
        })
        # Retry adapter: gestisce connessioni chiuse da TSW6 e errori transienti
        retry_strategy = Retry(
            total=1,
            backoff_factor=0.05,
            allowed_methods=["GET", "POST", "PATCH", "DELETE"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_maxsize=12, pool_connections=12)
        self.session.mount("http://", adapter)
        
        # Verifica connessione
        try:
            result = self.info()
            if result is not None:
                self.connected = True
                logger.info(f"Connesso a TSW6 su {self.base_url}")
                if self._on_connected:
                    self._on_connected()
                return True
        except requests.ConnectionError:
            self.connected = False
            raise TSW6ConnectionError(
                f"Impossibile connettersi a TSW6 su {self.base_url}. "
                "Assicurati che il gioco sia in esecuzione con -HTTPAPI."
            )
        except Exception as e:
            self.connected = False
            raise TSW6ConnectionError(f"Errore di connessione: {e}")
        
        return False
    
    def disconnect(self):
        """Chiude la sessione"""
        if self.session:
            self.session.close()
            self.session = None
        self.connected = False
        if self._on_disconnected:
            self._on_disconnected()
    
    def is_connected(self) -> bool:
        """Verifica se la connessione è attiva"""
        return self.connected and self.session is not None
    
    # --------------------------------------------------------
    # Richieste base
    # --------------------------------------------------------
    
    def _request(self, method: str, path: str, params: dict = None, timeout: float = 5.0) -> dict:
        """Esegue una richiesta HTTP all'API"""
        if not self.session:
            raise TSW6ConnectionError("Non connesso. Chiamare connect() prima.")
        
        url = f"{self.base_url}{path}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                timeout=timeout
            )
            
            # Se riceviamo risposta, la connessione funziona
            if not self.connected:
                self.connected = True
                logger.info("Connessione TSW6 ripristinata")
            
            if response.status_code == 403:
                raise TSW6AuthError("Chiave API non valida (403 Forbidden)")
            
            if response.status_code == 200:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    return {"raw": response.text}
            else:
                # Prova a decodificare l'errore JSON
                try:
                    error_data = response.json()
                    raise TSW6APIError(f"Errore API ({response.status_code}): {error_data}")
                except json.JSONDecodeError:
                    raise TSW6APIError(f"Errore API ({response.status_code}): {response.text}")
        
        except requests.Timeout:
            # Timeout: NON invalida la connessione
            raise TSW6ConnectionError("Timeout nella richiesta a TSW6")
        except requests.ConnectionError:
            # NON settiamo connected=False qui - lo fa solo disconnect() esplicito.
            # Il poller gestisce i retry. Errori transienti non devono rompere lo stato.
            raise TSW6ConnectionError("Errore di connessione con TSW6")
    
    # --------------------------------------------------------
    # Comandi principali
    # --------------------------------------------------------
    
    def info(self) -> dict:
        """GET /info - Informazioni sui comandi disponibili"""
        return self._request("GET", "/info")
    
    def list_nodes(self, path: str = "") -> dict:
        """
        GET /list[/path] - Lista nodi e endpoint disponibili
        
        Esempi:
            api.list_nodes()  # Top level
            api.list_nodes("CurrentDrivableActor")
            api.list_nodes("CurrentDrivableActor/Simulation")
        """
        route = "/list"
        if path:
            route += f"/{encode_path(path)}"
        return self._request("GET", route)
    
    def get(self, path: str) -> Any:
        """
        GET /get/path - Legge un valore da un endpoint
        
        Il path usa '/' per i nodi e '.' per gli endpoint.
        TSW6 ritorna: {"Result": "Success", "Values": {"NomeProprietà": valore}}
        
        Esempi:
            api.get("CurrentDrivableActor.Function.HUD_GetSpeed")
            api.get("CurrentDrivableActor/Throttle(Lever).Function.GetCurrentNotchIndex")
            api.get("WeatherManager.Cloudiness")
            api.get("TimeOfDay.Data")
        """
        result = self._request("GET", f"/get/{encode_path(path)}")
        # TSW6 ritorna {"Result": "Success", "Values": {"Key": value}}
        if isinstance(result, dict) and "Values" in result:
            values = result["Values"]
            if isinstance(values, dict) and values:
                return list(values.values())[0]
            return values
        # Fallback per formato vecchio
        if isinstance(result, dict) and "Value" in result:
            return result["Value"]
        return result
    
    def get_raw(self, path: str) -> dict:
        """GET /get/path - Legge il JSON completo di risposta"""
        return self._request("GET", f"/get/{encode_path(path)}")
    
    def set(self, path: str, value: Any) -> dict:
        """
        PATCH /set/path?Value=value - Imposta un valore
        
        Esempi:
            api.set("CurrentDrivableActor/Throttle(Lever).InputValue", 0.5)
            api.set("WeatherManager.Cloudiness", 0.8)
            api.set("VirtualRailDriver.Throttle", 0.5)
            api.set("VirtualRailDriver.Enabled", "true")
        """
        return self._request("PATCH", f"/set/{encode_path(path)}", params={"Value": str(value)})
    
    # --------------------------------------------------------
    # Subscriptions
    # --------------------------------------------------------
    
    def subscribe(self, subscription_id: int, endpoint_path: str) -> dict:
        """
        POST /subscription/path?Subscription=id - Aggiunge un endpoint a una subscription
        
        Esempio:
            api.subscribe(1, "CurrentDrivableActor.Function.HUD_GetSpeed")
            api.subscribe(1, "CurrentDrivableActor.Function.HUD_GetBrakeGauge_1")
        """
        return self._request(
            "POST",
            f"/subscription/{encode_path(endpoint_path)}",
            params={"Subscription": subscription_id}
        )
    
    def read_subscription(self, subscription_id: int) -> dict:
        """
        GET /subscription?Subscription=id - Legge tutti i valori di una subscription
        """
        return self._request("GET", "/subscription", params={"Subscription": subscription_id})
    
    def remove_subscription(self, subscription_id: int) -> dict:
        """
        DELETE /subscription?Subscription=id - Rimuove una subscription
        """
        return self._request("DELETE", "/subscription", params={"Subscription": subscription_id})
    
    def list_subscriptions(self) -> dict:
        """GET /listsubscriptions - Lista tutte le subscription attive"""
        return self._request("GET", "/listsubscriptions")
    
    def clear_subscription_safe(self, subscription_id: int):
        """Rimuove una subscription ignorando errori (utile all'avvio)"""
        try:
            self.remove_subscription(subscription_id)
        except TSW6APIError:
            pass  # Normale se non esisteva
    
    # --------------------------------------------------------
    # VirtualRailDriver
    # --------------------------------------------------------
    
    def enable_virtual_raildriver(self, enable: bool = True) -> dict:
        """Abilita/disabilita il VirtualRailDriver"""
        return self.set("VirtualRailDriver.Enabled", "true" if enable else "false")
    
    def set_virtual_raildriver(self, control: str, value: float) -> dict:
        """
        Imposta un controllo del VirtualRailDriver.
        
        Controlli comuni: Throttle, TrainBrake, LocoBrake, Reverser, etc.
        """
        return self.set(f"VirtualRailDriver.{control}", value)
    
    # --------------------------------------------------------
    # Weather
    # --------------------------------------------------------
    
    def get_weather(self) -> Dict[str, float]:
        """Legge tutti i parametri meteo"""
        params = [
            "Temperature", "Cloudiness", "Precipitation",
            "Wetness", "GroundSnow", "PiledSnow", "FogDensity"
        ]
        result = {}
        for p in params:
            try:
                result[p] = self.get(f"WeatherManager.{p}")
            except TSW6APIError:
                result[p] = None
        return result
    
    def set_weather(self, param: str, value: float) -> dict:
        """
        Imposta un parametro meteo.
        Parametri: Temperature, Cloudiness, Precipitation, Wetness,
                   GroundSnow, PiledSnow, FogDensity
        """
        return self.set(f"WeatherManager.{param}", value)
    
    # --------------------------------------------------------
    # Time of Day
    # --------------------------------------------------------
    
    def get_time_of_day(self) -> dict:
        """Legge le informazioni sull'ora del giorno"""
        return self.get_raw("TimeOfDay.Data")
    
    # --------------------------------------------------------
    # Driver Aid
    # --------------------------------------------------------
    
    def get_driver_aid_data(self) -> dict:
        """Legge i dati del Driver Aid"""
        return self.get_raw("DriverAid.Data")
    
    def get_player_info(self) -> dict:
        """Legge le info del giocatore (include Lat/Lon)"""
        return self.get_raw("DriverAid.PlayerInfo")
    
    def get_track_data(self) -> dict:
        """Legge i dati del tracciato davanti al giocatore"""
        return self.get_raw("DriverAid.TrackData")
    
    # --------------------------------------------------------
    # Info treno
    # --------------------------------------------------------
    
    def get_player_train_class(self) -> Any:
        """Ritorna la classe del treno guidato dal giocatore"""
        return self.get("CurrentFormation/Vehicles/0.RailVehicleClass")

    # --------------------------------------------------------
    # Scoperta endpoint
    # --------------------------------------------------------

    def discover_endpoints(self, path: str = "", max_depth: int = 5,
                           progress_callback: Callable[[str], None] = None) -> List[Dict[str, Any]]:
        """
        Esplora ricorsivamente l'albero API e ritorna tutti gli endpoint trovati.

        Ogni elemento ha: path, name, writable, type (se disponibile).

        Uso:
            endpoints = api.discover_endpoints("CurrentDrivableActor")
            for ep in endpoints:
                print(f"{ep['path']}  (writable={ep['writable']})")
        """
        results = []
        self._discover_recursive(path, results, max_depth, 0, progress_callback)
        return results

    def _discover_recursive(self, path: str, results: list, max_depth: int,
                            depth: int, progress_cb):
        """Helper ricorsivo per discover_endpoints"""
        if depth > max_depth:
            return

        try:
            route = f"/list/{encode_path(path)}" if path else "/list"
            data = self._request("GET", route, timeout=10.0)
        except TSW6APIError:
            return

        if progress_cb:
            progress_cb(path or "(root)")

        # Estrai endpoint
        endpoints = data.get("Endpoints", [])
        if isinstance(endpoints, list):
            for ep in endpoints:
                if isinstance(ep, dict):
                    ep_name = ep.get("Name", "")
                    full_path = f"{path}.{ep_name}" if path else ep_name
                    results.append({
                        "path": full_path,
                        "name": ep_name,
                        "writable": ep.get("Writable", False),
                        "type": ep.get("Type", ""),
                        "node": path,
                    })
                elif isinstance(ep, str):
                    full_path = f"{path}.{ep}" if path else ep
                    results.append({
                        "path": full_path,
                        "name": ep,
                        "writable": False,
                        "type": "",
                        "node": path,
                    })

        # Ricorsione sui nodi figli
        nodes = data.get("Nodes", [])
        if isinstance(nodes, list):
            for node in nodes:
                if isinstance(node, dict):
                    node_name = node.get("Name", "")
                    collapsed = node.get("Collapsed", False)
                    child_path = f"{path}/{node_name}" if path else node_name
                    if collapsed or True:  # esplora sempre
                        self._discover_recursive(child_path, results, max_depth,
                                                 depth + 1, progress_cb)
                elif isinstance(node, str):
                    child_path = f"{path}/{node}" if path else node
                    self._discover_recursive(child_path, results, max_depth,
                                             depth + 1, progress_cb)

    def search_endpoints(self, path: str = "CurrentDrivableActor",
                         keywords: List[str] = None,
                         max_depth: int = 5,
                         progress_callback: Callable[[str], None] = None) -> List[Dict[str, Any]]:
        """
        Scopre tutti gli endpoint e filtra per parole chiave.

        Utile per trovare PZB, SIFA, LZB, ecc:
            results = api.search_endpoints(keywords=["PZB", "SIFA", "LZB", "Safety", "Brake"])
        """
        all_eps = self.discover_endpoints(path, max_depth, progress_callback)

        if not keywords:
            return all_eps

        filtered = []
        kw_lower = [k.lower() for k in keywords]
        for ep in all_eps:
            searchable = f"{ep['path']} {ep['name']} {ep['node']}".lower()
            if any(kw in searchable for kw in kw_lower):
                filtered.append(ep)
        return filtered
    
    def get_speed_ms(self) -> float:
        """Velocità in m/s"""
        return float(self.get("CurrentDrivableActor.Function.HUD_GetSpeed"))
    
    def get_speed_kmh(self) -> float:
        """Velocità in km/h"""
        return self.get_speed_ms() * 3.6
    
    def get_speed_mph(self) -> float:
        """Velocità in mph"""
        return self.get_speed_ms() * 2.23694
    
    # --------------------------------------------------------
    # Helpers per leve e controlli
    # --------------------------------------------------------
    
    def get_lever_info(self, lever_name: str) -> dict:
        """
        Ottiene informazioni su una leva (min, max, notch count, valore attuale).
        
        lever_name: es. "Throttle(Lever)", "TrainBrake(Lever)", "Reverser(Lever)"
        """
        base = f"CurrentDrivableActor/{lever_name}"
        info = {}
        
        endpoints = [
            ("min", "Function.GetMinimumInputValue"),
            ("max", "Function.GetMaximumInputValue"),
            ("notch_count", "Function.GetNotchCount"),
            ("input_value", "InputValue"),
            ("output_value", "OutputValue"),
            ("current_notch", "Function.GetCurrentNotchIndex"),
        ]
        
        for key, endpoint in endpoints:
            try:
                info[key] = self.get(f"{base}.{endpoint}")
            except TSW6APIError:
                info[key] = None
        
        return info
    
    def set_lever(self, lever_name: str, value: float) -> dict:
        """
        Imposta il valore di una leva.
        
        lever_name: es. "Throttle(Lever)", "TrainBrake(Lever)"
        value: valore tra min e max della leva
        """
        return self.set(f"CurrentDrivableActor/{lever_name}.InputValue", value)
    
    # --------------------------------------------------------
    # Subscription helper per polling multiplo
    # --------------------------------------------------------
    
    def setup_train_subscription(self, subscription_id: int = 1,
                                  endpoints: List[str] = None,
                                  max_retries: int = 3) -> List[str]:
        """
        Configura una subscription per monitorare lo stato del treno.
        
        Se endpoints non è specificato, usa un set predefinito.
        Ritorna la lista degli endpoint sottoscritti con successo.
        Lancia TSW6ConnectionError solo se la connessione è completamente persa.
        """
        if not self.is_connected():
            raise TSW6ConnectionError("Non connesso a TSW6")
        
        # Verifica che TSW6 risponda
        for attempt in range(max_retries):
            try:
                self.info()
                break
            except TSW6ConnectionError:
                if attempt == max_retries - 1:
                    raise TSW6ConnectionError(
                        "TSW6 non raggiungibile. Assicurati che il gioco sia "
                        "in esecuzione con -HTTPAPI e che stai guidando un treno."
                    )
                time.sleep(0.5)
            except TSW6APIError:
                break  # Connessione ok, altro errore
        
        # Pulisci prima
        self.clear_subscription_safe(subscription_id)
        
        if endpoints is None:
            endpoints = [
                "CurrentDrivableActor.Function.HUD_GetSpeed",
                "CurrentDrivableActor.Function.HUD_GetBrakeGauge_1",
                "CurrentDrivableActor.Function.HUD_GetBrakeGauge_2",
                "CurrentDrivableActor.Function.HUD_GetAmmeter",
                "CurrentDrivableActor.Function.HUD_GetIsSlipping",
            ]
        
        subscribed = []
        failed = []
        for ep in endpoints:
            for attempt in range(max_retries):
                try:
                    self.subscribe(subscription_id, ep)
                    subscribed.append(ep)
                    break
                except TSW6ConnectionError:
                    if attempt == max_retries - 1:
                        # Verifica se il server è ancora raggiungibile
                        try:
                            self.info()
                            # Server ok, endpoint non sottoscrivibile
                            failed.append(ep)
                            logger.warning(f"Endpoint non sottoscrivibile: {ep}")
                        except TSW6ConnectionError:
                            raise TSW6ConnectionError(
                                f"Connessione persa con TSW6 durante setup "
                                f"(sottoscritti {len(subscribed)}/{len(endpoints)})"
                            )
                    else:
                        time.sleep(0.3)
                except TSW6APIError as e:
                    failed.append(ep)
                    logger.warning(f"Errore subscription per '{ep}': {e}")
                    break
        
        if failed:
            logger.info(f"Subscription: {len(subscribed)} OK, {len(failed)} falliti: {failed}")
        if not subscribed:
            raise TSW6APIError(
                f"Nessun endpoint sottoscritto con successo su {len(endpoints)} tentativi.\n"
                f"Verifica che stai guidando un treno e che gli endpoint esistano."
            )
        
        return subscribed
    
    def poll_subscription(self, subscription_id: int = 1) -> Dict[str, Any]:
        """
        Legge una subscription e restituisce un dizionario path→valore.
        
        TSW6 ritorna: {"Entries": [{"Values": {"Key": val}, "NodeValid": true}, ...]}
        """
        raw = self.read_subscription(subscription_id)
        result = {}
        
        if isinstance(raw, dict):
            # Formato subscription: {"Entries": [{"Values": {...}, "NodeValid": true}, ...]}
            entries = raw.get("Entries", [])
            if isinstance(entries, list):
                for entry in entries:
                    if isinstance(entry, dict) and entry.get("NodeValid", False):
                        values = entry.get("Values", {})
                        if isinstance(values, dict):
                            for key, val in values.items():
                                result[key] = val
            
            # Fallback: formato non-Entries
            if not result:
                for key, val in raw.items():
                    if key in ("Result", "Entries"):
                        continue
                    if isinstance(val, dict) and "Values" in val:
                        values = val["Values"]
                        if isinstance(values, dict):
                            for vk, vv in values.items():
                                result[vk] = vv
                    elif isinstance(val, dict) and "Value" in val:
                        result[key] = val["Value"]
                    else:
                        result[key] = val
        
        return result


# ============================================================
# Polling Thread - per aggiornamenti periodici
# ============================================================

class TSW6Poller:
    """
    Thread di polling che legge periodicamente dati da TSW6
    e invoca callback con i valori aggiornati.
    
    Usa esclusivamente GET individuali per massima robustezza.
    Include delay tra richieste per evitare sovraccarico di TSW6.
    """
    
    def __init__(self, api: TSW6API, interval: float = 0.2):
        self.api = api
        self.interval = max(interval, 0.05)  # Minimo 50ms tra cicli
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self._error_callback: Optional[Callable[[str], None]] = None
        self._data_callback: Optional[Callable[[str], None]] = None  # Debug
        self._last_data: Dict[str, Any] = {}
        self._endpoints: List[str] = []
        self._endpoint_errors: Dict[str, int] = {}  # Conta errori per endpoint
        self._successful_polls = 0
    
    def add_callback(self, callback: Callable[[Dict[str, Any]], None]):
        self._callbacks.append(callback)
    
    def set_error_callback(self, callback: Callable[[str], None]):
        self._error_callback = callback
    
    def set_data_callback(self, callback: Callable[[str], None]):
        """Callback per debug: riceve stringa con dati ricevuti"""
        self._data_callback = callback
    
    def start(self, endpoints: List[str] = None):
        """Avvia il polling con GET individuali"""
        if self._running:
            return
        
        self._endpoints = endpoints or []
        if not self._endpoints:
            if self._error_callback:
                self._error_callback("Nessun endpoint da monitorare")
            return
        
        # Verifica che TSW6 risponda
        try:
            self.api.info()
        except Exception as e:
            if self._error_callback:
                self._error_callback(f"TSW6 non raggiungibile: {e}")
            return
        
        # Test rapido: prova il primo endpoint per verificare che funziona
        test_ep = self._endpoints[0]
        try:
            test_val = self.api.get(test_ep)
            logger.info(f"Test endpoint OK: {test_ep} = {test_val}")
            if self._error_callback:
                self._error_callback(f"✅ Polling GET avviato ({len(self._endpoints)} endpoint)")
        except TSW6APIError as e:
            logger.warning(f"Test endpoint fallito: {test_ep} -> {e}")
            if self._error_callback:
                self._error_callback(f"⚠️ Avvio polling ({test_ep} non disponibile, provo tutti)")
        except TSW6ConnectionError as e:
            if self._error_callback:
                self._error_callback(f"❌ TSW6 non raggiungibile: {e}")
            return
        
        self._endpoint_errors.clear()
        self._successful_polls = 0
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Ferma il polling"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)
            self._thread = None
    
    def _poll_loop(self):
        """Loop principale di polling GET"""
        consecutive_total_failures = 0
        
        while self._running:
            try:
                data = self._poll_all_endpoints()
                
                if data:
                    self._last_data = data
                    self._successful_polls += 1
                    consecutive_total_failures = 0
                    
                    for cb in self._callbacks:
                        try:
                            cb(data)
                        except Exception as e:
                            logger.error(f"Errore nel callback: {e}")
                else:
                    consecutive_total_failures += 1
                    
                    if consecutive_total_failures == 1 and self._error_callback:
                        # Mostra quali endpoint falliscono
                        bad = [ep for ep, cnt in self._endpoint_errors.items() if cnt > 2]
                        if bad:
                            names = ", ".join(ep.rsplit(".", 1)[-1] for ep in bad[:5])
                            self._error_callback(f"⚠️ Endpoint non disponibili: {names}")
                        else:
                            self._error_callback("⚠️ Nessun dato ricevuto, riprovo...")
                    
                    if consecutive_total_failures > 30:
                        if self._error_callback:
                            self._error_callback("❌ Troppi errori consecutivi, polling fermato")
                        self._running = False
                        break
                    
                    # Backoff progressivo
                    time.sleep(min(0.5 * consecutive_total_failures, 5.0))
                    continue
                
            except TSW6ConnectionError as e:
                consecutive_total_failures += 1
                if consecutive_total_failures <= 2 and self._error_callback:
                    self._error_callback(f"⚠️ {e}, riprovo...")
                
                if consecutive_total_failures > 30:
                    if self._error_callback:
                        self._error_callback("❌ Connessione persa definitivamente")
                    self._running = False
                    break
                
                time.sleep(min(1.0 * consecutive_total_failures, 5.0))
                continue
                    
            except Exception as e:
                logger.error(f"Errore inaspettato nel polling: {e}")
                time.sleep(1.0)
            
            time.sleep(self.interval)
    
    def _poll_all_endpoints(self) -> Dict[str, Any]:
        """
        Polling GET concorrente per tutti gli endpoint.
        Usa ThreadPoolExecutor per parallelizzare le richieste HTTP.
        Timeout 1.5s per richiesta.
        """
        result = {}
        connection_errors = 0
        api_errors = 0
        is_first_poll = (self._successful_polls == 0)

        def _fetch_one(ep: str):
            """Fetch singolo endpoint, ritorna (ep, value, error_type)"""
            try:
                raw = self.api._request("GET", f"/get/{encode_path(ep)}", timeout=1.5)

                # Log prima risposta raw per debug
                if is_first_poll:
                    logger.info(f"Prima risposta raw da TSW6: {raw}")

                # TSW6 ritorna {"Result": "Success", "Values": {"Key": value}}
                if isinstance(raw, dict) and "Values" in raw:
                    values = raw["Values"]
                    if isinstance(values, dict) and values:
                        return (ep, list(values.values())[0], None)
                    else:
                        return (ep, values, None)
                elif isinstance(raw, dict) and "Value" in raw:
                    return (ep, raw["Value"], None)
                elif isinstance(raw, dict):
                    return (ep, raw, None)
                else:
                    return (ep, raw, None)

            except TSW6ConnectionError:
                return (ep, None, "connection")
            except TSW6APIError as e:
                return (ep, None, f"api:{e}")
            except Exception as e:
                return (ep, None, f"unknown:{e}")

        # Esegui tutte le richieste in parallelo (max 10 worker)
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                executor.submit(_fetch_one, ep): ep
                for ep in self._endpoints if self._running
            }
            for future in as_completed(futures):
                if not self._running:
                    break
                ep, value, error_type = future.result()

                if error_type is None:
                    result[ep] = value
                    self._endpoint_errors.pop(ep, None)
                elif error_type == "connection":
                    connection_errors += 1
                    self._endpoint_errors[ep] = self._endpoint_errors.get(ep, 0) + 1
                else:
                    api_errors += 1
                    err_cnt = self._endpoint_errors.get(ep, 0) + 1
                    self._endpoint_errors[ep] = err_cnt
                    if err_cnt == 1:
                        logger.warning(f"Endpoint errore: {ep} -> {error_type}")

        if connection_errors >= 3:
            raise TSW6ConnectionError("Connessione instabile")

        # Log debug per prima risposta
        if is_first_poll and result and self._data_callback:
            first_ep = next(iter(result))
            self._data_callback(f"🔍 Raw: {result[first_ep]}")

        return result
    
    @property
    def last_data(self) -> Dict[str, Any]:
        """Ultimo set di dati ricevuto"""
        return self._last_data
