"""
Zusi3 Client - Client TCP per connessione a Zusi3

Gestisce:
- Connessione al server Zusi3
- Handshake (HELLO/ACK_HELLO)
- Sottoscrizione dati (NEEDED_DATA)
- Ricezione dati in tempo reale
"""

import socket
import struct
import threading
import time
from typing import List, Dict, Callable, Optional, Set
from dataclasses import dataclass, field

from zusi3_protocol import (
    Node, Attribute, Zusi3Protocol,
    MsgType, Command, FsData, PzbLm, LzbLm,
    create_attribute_uint16, create_attribute_string,
    NODE_START, NODE_END
)


@dataclass
class PzbState:
    """Stato PZB/Indusi"""
    aktiv: bool = False           # Sistema attivo
    
    # Tipo treno (0=off, 1=on, 2=lampeggiante)
    zugart_55: float = 0.0        # Luce 55 (treno lento)
    zugart_70: float = 0.0        # Luce 70 (treno medio)
    zugart_85: float = 0.0        # Luce 85 (treno veloce)
    zugart_u: bool = False        # Luce U
    zugart_m: bool = False        # Luce M
    zugart_o: bool = False        # Luce O (senza PZB)
    
    # Magneti/Luci (0=off, 1=on, 2=lampeggiante)
    lm_1000hz: float = 0.0       # LED 1000Hz (avviso)
    lm_500hz: float = 0.0        # LED 500Hz (restrittivo)
    lm_befehl: bool = False       # LED Befehl 40 (override)
    
    # Stato
    zwangsbremsung: bool = False  # Frenatura emergenza PZB
    frei: bool = False            # Via libera


@dataclass
class LzbState:
    """Stato LZB"""
    aktiv: bool = False           # LZB attivo
    ende: bool = False            # Fine tratta LZB (lzb_ende_verfahren)
    
    # Luci con supporto lampeggio (float: 0=off, 1=on, 2=blink, 3=blink_invers)
    lm_g: float = 0.0            # G - Geführt (rosso)
    lm_ende: float = 0.0         # Ende - Fine tratta LZB (giallo)
    lm_s: float = 0.0            # S - Schnellbremsung (rosso)
    
    # Luci semplici (bool)
    lm_b: bool = False            # B - Befehl
    lm_el: bool = False           # EL - Elektrisch
    lm_v40: bool = False          # V40 - 40 km/h
    lm_pruef_stoer: bool = False  # Prüf/Stör
    
    # Luci con supporto lampeggio extra
    lm_ue: float = 0.0            # Ü - Übertragung (blu)
    
    # Valori
    v_soll: float = 0.0           # Velocità target [km/h]
    v_ziel: float = 0.0           # Velocità obiettivo [km/h]
    s_ziel: float = 0.0           # Distanza obiettivo [m]


@dataclass
class SifaState:
    """Stato SIFA (vigilante)"""
    licht: bool = False           # Luce SIFA accesa
    hupe_warning: bool = False    # Allarme acustico avviso
    hupe_zwang: bool = False      # Allarme frenatura
    hauptschalter: bool = True    # Interruttore principale SIFA
    stoerschalter: bool = True    # Interruttore disturbo
    luftabsperrhahn: bool = True  # Rubinetto aria


@dataclass
class TrainState:
    """Stato corrente del treno ricevuto da Zusi3"""
    # Velocità e movimento
    speed_ms: float = 0.0          # Velocità [m/s]
    speed_kmh: float = 0.0         # Velocità [km/h]
    
    # Pressioni freni
    pressure_main: float = 0.0     # Condotta principale [bar]
    pressure_cylinder: float = 0.0 # Cilindri freno [bar]
    pressure_tank: float = 0.0     # Serbatoio [bar]
    
    # Trazione
    tractive_effort: float = 0.0   # Forza trazione [N]
    brake_effort: float = 0.0      # Forza frenata [N]
    throttle_step: int = 0         # Gradino regolatore
    
    # Elettrico
    current: float = 0.0           # Corrente [A]
    voltage: float = 0.0           # Tensione [V]
    rpm: float = 0.0               # Giri motore
    
    # Interruttori principali
    main_switch: bool = False      # Interruttore principale
    pantograph: bool = False       # Pantografo alzato
    
    # === SIFA ===
    sifa: SifaState = field(default_factory=SifaState)
    
    # === PZB/INDUSI ===
    pzb: PzbState = field(default_factory=PzbState)
    
    # === LZB ===
    lzb: LzbState = field(default_factory=LzbState)
    
    # Porte
    doors_left: bool = False       # Porte sinistre aperte
    doors_right: bool = False      # Porte destre aperte
    doors_warning: bool = False    # Allarme chiusura porte
    
    # Luci
    headlights_front: int = 0      # Fari anteriori (0-3)
    headlights_rear: int = 0       # Fari posteriori (0-3)
    cabin_light: bool = False      # Luce cabina
    
    # Tempo
    hour: int = 0
    minute: int = 0
    second: int = 0
    
    # Max speed
    max_speed: float = 0.0         # Velocità max [km/h]
    afb_target: float = 0.0        # Target AFB [km/h]
    afb_active: bool = False       # AFB attivo
    
    # Posizione
    kilometrierung: float = 0.0    # Posizione corrente [km]
    has_km: bool = False           # True se KILOMETRIERUNG è disponibile
    
    # Altri
    sand: bool = False             # Sabbiatrice
    wiper: int = 0                 # Tergicristalli
    emergency_brake: bool = False  # Freno emergenza


class Zusi3Client:
    """Client per comunicazione con Zusi3"""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 1436):
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.connected = False
        self.running = False
        
        # Stato treno
        self.state = TrainState()
        
        # Dati sottoscritti
        self.subscribed_fs_data: Set[FsData] = set()
        
        # Callback per aggiornamenti
        self.on_state_update: Optional[Callable[[TrainState], None]] = None
        self.on_connect: Optional[Callable[[], None]] = None
        self.on_disconnect: Optional[Callable[[], None]] = None
        
        # Thread ricezione
        self._receive_thread: Optional[threading.Thread] = None
        
        # Info server
        self.zusi_version = ""
        self.connection_info = ""
    
    def connect(self, client_name: str = "Zusi3Bridge", 
                fs_data: Optional[List[FsData]] = None) -> bool:
        """
        Connette a Zusi3 e sottoscrive i dati richiesti
        
        Args:
            client_name: Nome identificativo del client
            fs_data: Lista di FsData da sottoscrivere (default: tutti i principali)
        
        Returns:
            True se connesso con successo
        """
        if self.connected:
            return True
        
        try:
            # Crea socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10.0)
            self.socket.connect((self.host, self.port))
            
            # === HELLO ===
            hello_msg = self._create_hello_message(client_name)
            Zusi3Protocol.write_message(self.socket, hello_msg)
            
            # Ricevi ACK_HELLO
            ack_hello = Zusi3Protocol.read_message(self.socket)
            if not self._parse_ack_hello(ack_hello):
                raise ConnectionError("ACK_HELLO invalido")
            
            # === NEEDED_DATA ===
            if fs_data is None:
                fs_data = self._get_default_fs_data()
            
            self.subscribed_fs_data = set(fs_data)
            
            needed_msg = self._create_needed_data_message(fs_data)
            Zusi3Protocol.write_message(self.socket, needed_msg)
            
            # Ricevi ACK_NEEDED_DATA
            ack_needed = Zusi3Protocol.read_message(self.socket)
            if not self._parse_ack_needed_data(ack_needed):
                raise ConnectionError("ACK_NEEDED_DATA invalido")
            
            # Connesso!
            self.connected = True
            self.socket.settimeout(1.0)  # Timeout più breve per receive
            
            # Avvia thread ricezione
            self.running = True
            self._receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
            self._receive_thread.start()
            
            if self.on_connect:
                self.on_connect()
            
            print(f"Connesso a Zusi3 {self.zusi_version}")
            return True
            
        except Exception as e:
            print(f"Errore connessione: {e}")
            self.disconnect()
            return False
    
    def disconnect(self):
        """Disconnette da Zusi3"""
        self.running = False
        self.connected = False
        
        if self._receive_thread:
            self._receive_thread.join(timeout=2.0)
            self._receive_thread = None
        
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        
        if self.on_disconnect:
            self.on_disconnect()
    
    def _create_hello_message(self, client_name: str) -> Node:
        """Crea messaggio HELLO"""
        msg = Node(MsgType.CONNECTING)
        
        hello = Node(Command.HELLO)
        hello.attributes.append(create_attribute_uint16(1, 2))  # Protocol version
        hello.attributes.append(create_attribute_uint16(2, 2))  # Client type (Fahrpult)
        hello.attributes.append(create_attribute_string(3, client_name))
        hello.attributes.append(create_attribute_string(4, "1.0"))
        
        msg.children.append(hello)
        return msg
    
    def _parse_ack_hello(self, msg: Node) -> bool:
        """Parsa ACK_HELLO"""
        if msg.id != MsgType.CONNECTING:
            return False
        
        for child in msg.children:
            if child.id == Command.ACK_HELLO:
                for attr in child.attributes:
                    if attr.id == 1:
                        self.zusi_version = attr.as_string()
                    elif attr.id == 3:
                        self.connection_info = attr.as_string()
                return True
        return False
    
    def _create_needed_data_message(self, fs_data: List[FsData]) -> Node:
        """Crea messaggio NEEDED_DATA"""
        msg = Node(MsgType.FAHRPULT)
        
        needed = Node(Command.NEEDED_DATA)
        
        # Führerstand data (gruppo 0x0A)
        if fs_data:
            fs_node = Node(0x0A)  # Fuehrerstand
            for fd in fs_data:
                fs_node.attributes.append(create_attribute_uint16(1, fd))
            needed.children.append(fs_node)
        
        msg.children.append(needed)
        return msg
    
    def _parse_ack_needed_data(self, msg: Node) -> bool:
        """Parsa ACK_NEEDED_DATA"""
        if msg.id != MsgType.FAHRPULT:
            return False
        
        for child in msg.children:
            if child.id == Command.ACK_NEEDED_DATA:
                return True
        return False
    
    def _get_default_fs_data(self) -> List[FsData]:
        """Ritorna lista default di dati da sottoscrivere (inclusi PZB/LZB/SIFA)"""
        return [
            # Velocità e movimento
            FsData.GESCHWINDIGKEIT,
            FsData.DRUCK_HAUPTLUFTLEITUNG,
            FsData.DRUCK_BREMSZYLINDER,
            FsData.DRUCK_HAUPTLUFTBEHAELTER,
            
            # Elettrico
            FsData.OBERSTROM,
            FsData.FAHRLEITUNGSSPANNUNG,
            FsData.MOTORDREHZAHL,
            
            # Tempo
            FsData.UHRZEIT_STUNDE,
            FsData.UHRZEIT_MINUTE,
            FsData.UHRZEIT_SEKUNDE,
            
            # Interruttori
            FsData.HAUPTSCHALTER,
            FsData.STROMABNEHMER,
            FsData.AFB_EIN_AUS,
            FsData.AFB_SOLL_GESCHW,
            FsData.STRECKENMAXGESCHW,
            FsData.FAHRSTUFE,
            
            # === SIFA ===
            FsData.SIFA,
            
            # === PZB/LZB/ETCS (sotto-messaggio complesso nidificato) ===
            FsData.STATUS_ZUGBEEINFLUSSUNG,
            
            # === Porte (sotto-messaggio complesso nidificato) ===
            FsData.STATUS_TUEREN,
            
            # === Posizione ===
            FsData.KILOMETRIERUNG,
        ]
    
    def _receive_loop(self):
        """Loop ricezione dati (in thread separato)"""
        while self.running and self.socket:
            try:
                msg = Zusi3Protocol.read_message(self.socket)
                self._process_message(msg)
            except socket.timeout:
                continue
            except ConnectionError:
                print("Connessione persa")
                break
            except Exception as e:
                if self.running:
                    print(f"Errore ricezione: {e}")
                break
        
        self.connected = False
        if self.on_disconnect:
            self.on_disconnect()
    
    def _process_message(self, msg: Node):
        """Processa messaggio ricevuto"""
        if msg.id != MsgType.FAHRPULT:
            return
        
        for child in msg.children:
            if child.id == Command.DATA_FTD:
                self._process_ftd_data(child)
    
    def _process_ftd_data(self, node: Node):
        """Processa dati Führerstand"""
        state_changed = False
        
        for attr in node.attributes:
            state_changed = True
            
            try:
                fs_id = FsData(attr.id)
            except ValueError:
                continue  # ID sconosciuto
            
            # === VELOCITÀ E MOVIMENTO ===
            if fs_id == FsData.GESCHWINDIGKEIT:
                self.state.speed_ms = attr.as_float()
                self.state.speed_kmh = self.state.speed_ms * 3.6
            
            elif fs_id == FsData.DRUCK_HAUPTLUFTLEITUNG:
                self.state.pressure_main = attr.as_float()
            
            elif fs_id == FsData.DRUCK_BREMSZYLINDER:
                self.state.pressure_cylinder = attr.as_float()
            
            elif fs_id == FsData.DRUCK_HAUPTLUFTBEHAELTER:
                self.state.pressure_tank = attr.as_float()
            
            # === ELETTRICO ===
            elif fs_id == FsData.OBERSTROM:
                self.state.current = attr.as_float()
            
            elif fs_id == FsData.FAHRLEITUNGSSPANNUNG:
                self.state.voltage = attr.as_float()
            
            elif fs_id == FsData.MOTORDREHZAHL:
                self.state.rpm = attr.as_float()
            
            # === TEMPO ===
            elif fs_id == FsData.UHRZEIT_STUNDE:
                self.state.hour = int(attr.as_float())
            
            elif fs_id == FsData.UHRZEIT_MINUTE:
                self.state.minute = int(attr.as_float())
            
            elif fs_id == FsData.UHRZEIT_SEKUNDE:
                self.state.second = int(attr.as_float())
            
            # === INTERRUTTORI ===
            elif fs_id == FsData.HAUPTSCHALTER:
                self.state.main_switch = attr.as_float() > 0
            
            elif fs_id == FsData.STROMABNEHMER:
                self.state.pantograph = attr.as_float() > 0
            
            elif fs_id == FsData.AFB_EIN_AUS:
                self.state.afb_active = attr.as_float() > 0
            
            elif fs_id == FsData.AFB_SOLL_GESCHW:
                self.state.afb_target = attr.as_float() * 3.6
            
            elif fs_id == FsData.STRECKENMAXGESCHW:
                self.state.max_speed = attr.as_float() * 3.6
            
            # === POSIZIONE ===
            elif fs_id == FsData.KILOMETRIERUNG:
                self.state.kilometrierung = attr.as_float()
                self.state.has_km = True
            
            elif fs_id == FsData.FAHRSTUFE:
                self.state.throttle_step = int(attr.as_float())
        
        # Processa sotto-messaggi (strutture complesse nidificate)
        for child in node.children:
            if child.id == FsData.SIFA:
                self._process_sifa(child)
                state_changed = True
            elif child.id == FsData.STATUS_ZUGBEEINFLUSSUNG:
                self._process_zugbeeinflussung(child)
                state_changed = True
            elif child.id == FsData.STATUS_TUEREN:
                self._process_tueren(child)
                state_changed = True
        
        if state_changed and self.on_state_update:
            self.on_state_update(self.state)
    
    def _process_sifa(self, node: Node):
        """Processa dati SIFA (struttura complessa con sotto-attributi)"""
        for attr in node.attributes:
            if attr.id == 2:  # Licht (luce)
                self.state.sifa.licht = attr.as_uint8() > 0
            elif attr.id == 3:  # Hupe (0=off, 1=warning, 2=brake)
                hupe = attr.as_uint8()
                self.state.sifa.hupe_warning = (hupe == 1)
                self.state.sifa.hupe_zwang = (hupe == 2)
            elif attr.id == 4:  # Hauptschalter
                self.state.sifa.hauptschalter = attr.as_uint8() > 1
            elif attr.id == 5:  # Störschalter
                self.state.sifa.stoerschalter = attr.as_uint8() > 1
            elif attr.id == 6:  # Luftabsperrhahn
                self.state.sifa.luftabsperrhahn = attr.as_uint8() > 1
    
    def _process_zugbeeinflussung(self, node: Node):
        """Processa STATUS_ZUGBEEINFLUSSUNG (PZB/LZB/ETCS)
        
        Struttura nidificata (da pyzusi3):
        - nodo id=1: Grundblock (bauart)
        - nodo id=2: Einstellungen (impostazioni)
        - nodo id=3: Betriebsdaten (dati operativi con Leuchtmelder PZB/LZB)
        """
        for child in node.children:
            if child.id == 3:  # BETRIEBSDATEN
                self._process_indusi_betriebsdaten(child)
    
    def _lm_to_float(self, value: int) -> float:
        """Converte LMZUSTAND_MIT_INVERS in float (0=off, 1=on, 2=lampeggiante, 3=lampeggiante invertito)
        
        Valori protocollo Zusi3:
        0 = AUS (spento), 1 = AN (acceso fisso), 2 = BLINKEND (lampeggiante),
        3 = BLINKEND_INVERS (lampeggiante invertito), 4 = DUNKEL (scuro)
        """
        if value == 0 or value == 4:   # AUS o DUNKEL
            return 0.0
        elif value == 1:                # AN (acceso fisso)
            return 1.0
        elif value == 2:                # BLINKEND (lampeggiante)
            return 2.0
        else:                           # 3=BLINKEND_INVERS (lampeggiante invertito)
            return 3.0
    
    def _process_indusi_betriebsdaten(self, node: Node):
        """Processa INDUSI Betriebsdaten (dati operativi PZB/LZB)
        
        Sub-IDs (da pyzusi3 STATUS_INDUSI_BETRIEBSDATEN):
        PZB: lm_1000hz(0x2f), lm_o(0x30)→85, lm_m(0x31)→70, lm_u(0x32)→55,
             lm_500hz(0x33), lm_befehl(0x34), zustand(2), zwangsbremsung(3)
        LZB: lzb_zustand(0x0d), sollgeschw(0x21), zielgeschw(0x22), zielweg(0x23),
             lm_g(0x24), lm_pruef_stoer(0x25), lm_b(0x3b), lm_ue(0x3c),
             lm_el(0x3d), lm_v40(0x3e), lm_s(0x3f)
        """
        for attr in node.attributes:
            aid = attr.id
            
            # === PZB Leuchtmelder (LMZUSTAND_MIT_INVERS) ===
            if aid == 0x2f:      # lm_1000hz
                self.state.pzb.lm_1000hz = self._lm_to_float(attr.as_uint8())
            elif aid == 0x30:    # lm_o → PZB 85 (Obere Zugart)
                self.state.pzb.zugart_85 = self._lm_to_float(attr.as_uint8())
            elif aid == 0x31:    # lm_m → PZB 70 (Mittlere Zugart)
                self.state.pzb.zugart_70 = self._lm_to_float(attr.as_uint8())
            elif aid == 0x32:    # lm_u → PZB 55 (Untere Zugart)
                self.state.pzb.zugart_55 = self._lm_to_float(attr.as_uint8())
            elif aid == 0x33:    # lm_500hz
                self.state.pzb.lm_500hz = self._lm_to_float(attr.as_uint8())
            elif aid == 0x34:    # lm_befehl
                self.state.pzb.lm_befehl = attr.as_uint8() > 0
            
            # === PZB Stato ===
            elif aid == 2:       # zustand (INDUSI_ZUSTAND)
                zustand = attr.as_uint16()
                self.state.pzb.aktiv = (zustand == 5)  # 5 = NORMALBETRIEB
            elif aid == 3:       # zwangsbremsung (INDUSI_ZWANGSBREMSUNG)
                self.state.pzb.zwangsbremsung = attr.as_uint16() > 0
            
            # === LZB Stato ===
            elif aid == 0x0d:    # lzb_zustand (INDUSI_LZB_ZUSTAND)
                lzb_z = attr.as_uint16()
                self.state.lzb.aktiv = (lzb_z >= 1)  # 0=keine_fuehrung
            elif aid == 0x21:    # lzb_sollgeschwindigkeit [m/s]
                self.state.lzb.v_soll = attr.as_float() * 3.6
            elif aid == 0x22:    # lzb_zielgeschwindigkeit [m/s]
                self.state.lzb.v_ziel = attr.as_float() * 3.6
            elif aid == 0x23:    # lzb_zielweg [m]
                self.state.lzb.s_ziel = attr.as_float()
            
            # === LZB Leuchtmelder (float con supporto lampeggio) ===
            elif aid == 0x24:    # lm_g (LMZUSTAND_MIT_INVERS)
                self.state.lzb.lm_g = self._lm_to_float(attr.as_uint8())
            elif aid == 0x3a:    # lm_ende (LMZUSTAND_MIT_INVERS)
                self.state.lzb.lm_ende = self._lm_to_float(attr.as_uint8())
            elif aid == 0x3f:    # lm_s (LMZUSTAND_MIT_INVERS)
                self.state.lzb.lm_s = self._lm_to_float(attr.as_uint8())
            
            # === LZB Leuchtmelder (bool) ===
            elif aid == 0x25:    # lm_pruef_stoer
                self.state.lzb.lm_pruef_stoer = attr.as_uint8() > 0
            elif aid == 0x3b:    # lm_b
                self.state.lzb.lm_b = attr.as_uint8() > 0
            elif aid == 0x3c:    # lm_ue (LMZUSTAND_MIT_INVERS)
                self.state.lzb.lm_ue = self._lm_to_float(attr.as_uint8())
            elif aid == 0x3d:    # lm_el
                self.state.lzb.lm_el = attr.as_uint8() > 0
            elif aid == 0x3e:    # lm_v40
                self.state.lzb.lm_v40 = attr.as_uint8() > 0
        
        # LZB Ende è in un sotto-nodo
        for child in node.children:
            if child.id == 0x0e:  # LZB Ende container
                for attr in child.attributes:
                    if attr.id == 1:  # lzb_ende_verfahren
                        self.state.lzb.ende = attr.as_uint8() > 0
    
    def _process_tueren(self, node: Node):
        """Processa STATUS_TUEREN (stato porte)
        
        Sub-IDs (da pyzusi3 STATUS_TUEREN):
        2 = links (TUEREN_SEITE: 0=zu, 1=oeffnend, 2=offen, 3=abgeschlossen, 4=schliessend)
        3 = rechts (TUEREN_SEITE)
        """
        for attr in node.attributes:
            if attr.id == 2:      # links (sinistra)
                self.state.doors_left = attr.as_uint8() > 0
            elif attr.id == 3:    # rechts (destra)
                self.state.doors_right = attr.as_uint8() > 0



# ============== TEST ==============

if __name__ == "__main__":
    def on_update(state: TrainState):
        # Mostra stato PZB/LZB/SIFA
        pzb_lm = []
        if state.pzb.lm_1000hz: pzb_lm.append("1000")
        if state.pzb.lm_500hz: pzb_lm.append("500")
        if state.pzb.lm_befehl: pzb_lm.append("BEF")
        if state.pzb.zwangsbremsung: pzb_lm.append("ZWANG!")
        
        lzb_info = ""
        if state.lzb.aktiv:
            lzb_info = f" LZB:{state.lzb.v_soll:.0f}/{state.lzb.v_ziel:.0f}km/h"
        
        sifa_icon = "🔴" if state.sifa.hupe_zwang else ("🟡" if state.sifa.hupe_warning else ("🟢" if state.sifa.licht else "⚪"))
        
        print(f"\rV:{state.speed_kmh:5.1f}km/h | "
              f"SIFA:{sifa_icon} | "
              f"PZB:[{','.join(pzb_lm) if pzb_lm else 'OK'}]"
              f"{lzb_info}", end='', flush=True)
    
    client = Zusi3Client()
    client.on_state_update = on_update
    
    print("Tentativo connessione a Zusi3...")
    if client.connect("Test"):
        print("Premi Ctrl+C per uscire")
        try:
            while client.connected:
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
        client.disconnect()
    else:
        print("Connessione fallita. Assicurati che Zusi3 sia avviato con la simulazione attiva.")
