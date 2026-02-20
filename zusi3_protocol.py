"""
Zusi3 TCP Protocol Implementation
Protocollo TCP per comunicazione con Zusi3 simulatore ferroviario

Basato sulla documentazione del protocollo Zusi3:
- Porta: 1436
- Formato: Little-endian, messaggi binari con nodi e attributi
"""

import struct
import socket
from enum import IntEnum
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass


# ============== COSTANTI PROTOCOLLO ==============

NODE_START = 0x00000000
NODE_END = 0xFFFFFFFF

# Message Types
class MsgType(IntEnum):
    CONNECTING = 1
    FAHRPULT = 2

# Commands
class Command(IntEnum):
    HELLO = 1
    ACK_HELLO = 2
    NEEDED_DATA = 3
    ACK_NEEDED_DATA = 4
    DATA_FTD = 0x0A        # Führerstand Data
    DATA_OPERATION = 0x0B  # Input events
    DATA_PROG = 0x0C       # Program status
    INPUT = 0x010A
    CONTROL = 0x010B
    GRAPHIC = 0x010C


# ============== FÜHRERSTAND DATA IDs ==============
# Dati del cruscotto/cabina di guida
# Lista completa basata su documentazione Zusi3 TCP Protocol

class FsData(IntEnum):
    """ID dei dati del Führerstand (cruscotto) - Lista completa"""
    
    # === VELOCITÀ E MOVIMENTO ===
    GESCHWINDIGKEIT = 1              # Velocità [m/s]
    DRUCK_HAUPTLUFTLEITUNG = 2       # Pressione condotta principale [bar]
    DRUCK_BREMSZYLINDER = 3          # Pressione cilindri freno [bar]
    DRUCK_HAUPTLUFTBEHAELTER = 4     # Pressione serbatoio principale [bar]
    DRUCK_BREMSLEIT_R = 5            # Pressione condotta freno R [bar]
    DRUCK_C_DRUCK = 6                # C-Druck [bar]
    ANTRIEBSKRAFT = 7                # Forza trazione [N]
    BREMSKRAFT_IST = 8               # Forza frenata attuale [N]
    BREMSKRAFT_SOLL = 9              # Forza frenata richiesta [N]
    DRUCK_HILFSLUFTBEHAELTER = 10    # Pressione serbatoio ausiliario [bar]
    DRUCK_ZUSATZLUFTBEHAELTER = 11   # Pressione serbatoio addizionale [bar]
    DRUCK_ZEITBEHAELTER = 12         # Pressione serbatoio temporizzatore [bar]
    
    # === ELETTRICO ===
    OBERSTROM = 13                   # Corrente pantografo [A]
    FAHRLEITUNGSSPANNUNG = 14        # Tensione linea [V]
    MOTORDREHZAHL = 15               # Giri motore [rpm]
    
    # === TEMPO ===
    UHRZEIT_STUNDE = 16              # Ora
    UHRZEIT_MINUTE = 17              # Minuto
    UHRZEIT_SEKUNDE = 18             # Secondo
    
    # === INTERRUTTORI PRINCIPALI ===
    HAUPTSCHALTER = 19               # Interruttore principale (0/1)
    TRAKTIONSSPERRE = 20             # Blocco trazione (0/1)
    FAHRSTUFE = 21                   # Gradino regolatore
    FSSTELLUNG = 22                  # Posizione leva regolatore
    AFB_SOLL_GESCHW = 23             # Velocità target AFB [m/s]
    DREHZAHL_SOLL = 24               # Giri motore target
    STRECKENMAXGESCHW = 25           # Velocità max tratta [m/s]
    ZUG_IST_ENTGLEIST = 26           # Treno deragliato (0/1)
    FAHRSTUFE_2 = 27                 # Gradino trazione secondario
    MOTOR_DREHMOMENT = 28            # Coppia motore [Nm]
    MOTOR_DREHZAHL_SOLL = 29         # Giri motore richiesti
    
    # === PZB/INDUSI - SISTEMA SICUREZZA TEDESCO ===
    # Luci display PZB
    PZB_ZUGART_55 = 30               # Luce PZB Zugart 55 (treno lento)
    PZB_ZUGART_70 = 31               # Luce PZB Zugart 70 (treno medio)
    PZB_ZUGART_85 = 32               # Luce PZB Zugart 85 (treno veloce)
    PZB_ZUGART_U = 33                # Luce PZB U (Umschaltbetrieb)
    PZB_ZUGART_M = 34                # Luce PZB M (Mehrfachtraktion)
    PZB_ZUGART_O = 35                # Luce PZB O (Ohne PZB)
    
    # Magneti PZB
    PZB_1000HZ = 36                  # Magnete 1000Hz attivo (avviso)
    PZB_500HZ = 37                   # Magnete 500Hz attivo (restrittivo)
    PZB_2000HZ = 38                  # Magnete 2000Hz attivo (halt)
    PZB_1000HZ_LICHT = 39            # LED 1000Hz
    PZB_500HZ_LICHT = 40             # LED 500Hz
    PZB_BEFEHL = 41                  # LED Befehl 40 (override)
    
    # Stato PZB
    PZB_AKTIV = 42                   # PZB sistema attivo
    PZB_ZWANGSBREMSUNG = 43          # Frenatura emergenza PZB
    PZB_SPEED_RESTR = 44             # Velocità limitata da PZB [m/s]
    
    # === LZB - LINIENFÖRMIGE ZUGBEEINFLUSSUNG ===
    LZB_AKTIV = 45                   # LZB attivo (0/1)
    LZB_ENDE = 46                    # Fine LZB (0/1)
    LZB_VSOLL = 47                   # Velocità target LZB [m/s]
    LZB_VZIEL = 48                   # Velocità obiettivo LZB [m/s]
    LZB_SZIEL = 49                   # Distanza obiettivo LZB [m]
    LZB_G = 50                       # LZB G (Geschwindigkeitsüberwachung)
    LZB_EL = 51                      # LZB EL (elektrische Bremse)
    LZB_V40 = 52                     # LZB V40 (velocità 40 km/h)
    LZB_S = 53                       # LZB S (Schnellbremsung)
    
    # === AFB - AUTOMATISCHE FAHR-UND BREMSSTEUERUNG ===
    AFB_EIN_AUS = 54                 # AFB attivo (0/1)
    AFB_SOLLGESCHW = 55              # Velocità target AFB [m/s]
    BREMSHAHN = 56                   # Rubinetto freno
    
    # === SIFA - SICHERHEITSFAHRSCHALTUNG (VIGILANTE) ===
    SIFA = 100                       # SIFA (struttura complessa)
    # Nota: SIFA ha sottostruttura con attributi:
    # 1 = Bauart (tipo)
    # 2 = Licht (luce) 0/1
    # 3 = Hupe (0=off, 1=warning, 2=brake)
    # 4 = Hauptschalter
    # 5 = Störschalter
    # 6 = Luftabsperrhahn
    
    # === ZUGBEEINFLUSSUNG - PZB/LZB/ETCS (struttura complessa) ===
    STATUS_ZUGBEEINFLUSSUNG = 101    # PZB/LZB/ETCS (sotto-messaggi nidificati)
    # Nota: Contiene sotto-nodi:
    # 1 = Grundblock (bauart)
    # 2 = Einstellungen (impostazioni)
    # 3 = Betriebsdaten (dati operativi PZB/LZB con Leuchtmelder)
    
    # === PORTE (struttura complessa) ===
    STATUS_TUEREN = 102              # Stato porte (sotto-messaggio nidificato)
    # Nota: Attributi diretti:
    # 2 = links (sinistra, TUEREN_SEITE: 0=zu, 1=oeffnend, 2=offen)
    # 3 = rechts (destra, TUEREN_SEITE)
    
    # === LM - LUCI/LED SPECIFICI ===
    LM_GETRIEBE = 57                 # Spia cambio
    LM_SCHLEUDERN = 58               # Spia slittamento
    LM_GLEITEN = 59                  # Spia pattinamento
    LM_HOBL = 60                     # Spia H-Bremse automatica
    LUEFTER_STAERKE = 61             # Ventilatore intensità
    ZUG_KRAFT_PRO_ACHSE = 62         # Forza per asse [N]
    ZUGKRAFT_SOLL_NORMIERT = 63      # Forza trazione norm.
    ZUG_KRAFT_STELLER = 64           # Regolatore forza
    STROMABNEHMER = 85               # Pantografo (0/1)
    
    # === FRENO ===
    FEDERSPEICHER = 66               # Freno molla (0/1)
    HBL_DRUCK = 67                   # Pressione HBL [bar]
    NBL_DRUCK = 68                   # Pressione NBL [bar]
    BREMSART = 69                    # Tipo freno
    DYNAMIKBREMSE_KRAFT = 70         # Forza freno dinamico [N]
    MG_BREMSE = 71                   # Freno magnetico (0/1)
    
    # === PORTE ===
    TUERSCHLIESSWARNTON = 72         # Allarme chiusura porte
    TUEREN_LINKS = 73                # Porte sinistra aperte (0/1)
    TUEREN_RECHTS = 74               # Porte destra aperte (0/1)
    DATUM = 75                       # Data
    
    # === ZBS/ZUB ===
    ZUB_BETRIEBSART = 76             # Modalità ZUB
    ZUB_AKTIV = 77                   # ZUB attivo
    
    # === ALTRI INDICATORI ===
    FAHRPULT_DEAKTIVIERT = 78        # Cabina disattivata
    SAND = 79                        # Sabbiatrice attiva
    RUECKWAERTSGANG = 80             # Retromarcia
    
    # === ETCS ===
    ETCS_ZUSTAND = 81                # Stato ETCS
    ETCS_VSOLL = 82                  # Velocità ETCS [m/s]
    ETCS_VZIEL = 83                  # Velocità obiettivo ETCS [m/s]
    ETCS_SZIEL = 84                  # Distanza obiettivo ETCS [m]
    ETCS_RELEASE_SPEED = 85          # Release speed ETCS
    ETCS_MODUS = 86                  # Modo ETCS
    ETCS_LEVEL = 87                  # Livello ETCS (0,1,2,3)
    
    # === PZB AGGIUNTIVI ===
    PZB_STOERSCHALTER = 88           # Interruttore disturbo PZB
    PZB_FREI = 89                    # PZB libero (via libera)
    
    # === DISPLAY ===
    TACHO_ANZEIGE = 90               # Valore tachimetro
    
    # === POSIZIONE ===
    KILOMETRIERUNG = 97              # Posizione corrente [km] — essenziale per EBuLa
    
    # === SPIE VARIE ===
    LM_TUERSCHLIESSEN = 91           # Spia chiusura porte
    LM_TUEREN_FREIGABE = 92          # Spia sblocco porte
    LM_NOTBREMSE_UEBERBRUECKT = 93   # Spia bypass freno emergenza
    LM_BREMSPROBE = 94               # Spia prova freni
    LM_HOCHABBREMSUNG = 95           # Spia frenatura alta
    
    # === FARI E LUCI ===
    LICHT_VORNE = 103                # Fari anteriori (0-3)
    LICHT_HINTEN = 104               # Fari posteriori (0-3)
    LICHT_INNEN = 105                # Luce cabina (0/1)
    SCHEIBENWISCHER = 106            # Tergicristalli (0/1/2)
    
    # === ZBS ===
    ZBS_AKTIV = 110                  # ZBS attivo
    ZBS_BREMSUNG = 111               # ZBS in frenatura
    
    # === NOTBREMSE ===
    NOTBREMSUEBERBRUECKUNG = 115     # Override freno emergenza
    NOTBREMSUNG = 116                # Freno emergenza attivo


# ============== PROGRAMMDATEN (EBuLa) ==============
# Dati programma Zusi3 (gruppo 0x0C) — Buchfahrplan, orario, documenti

class ProgData(IntEnum):
    """ID dei dati programma (Programmdaten) — per EBuLa"""
    ZUGDATEI = 1              # Percorso file treno (STRING)
    ZUGNUMMER = 2             # Numero treno (STRING, es. "ICE 578")
    LADEPAUSE = 3             # Pausa caricamento (BYTE)
    BUCHFAHRPLAN_XML = 4      # ★ Buchfahrplan XML — dati EBuLa strutturati
    NEU_UEBERNOMMEN = 5       # Flag: nuovo treno caricato (BYTE)
    BUCHFAHRPLAN_TIFF = 6     # Buchfahrplan come immagine TIFF
    BUCHFAHRPLAN_PDF = 7      # Buchfahrplan come PDF
    BREMSZETTEL_PDF = 8       # Certificato freni PDF
    WAGENLISTE_PDF = 9        # Lista vagoni PDF
    LA_PDF = 10               # Langsamfahrstellen (restrizioni velocità) PDF
    STRECKENBUCH_PDF = 11     # Libro tratta PDF
    ERSATZFAHRPLAN_PDF = 12   # Orario sostitutivo PDF


# ============== PZB SOTTOSTRUTTURA ==============

class PzbLm(IntEnum):
    """ID delle luci PZB nel sotto-nodo"""
    ZUGART = 1           # Tipo treno (55/70/85)
    ZUGART_BIT = 2       # Bit tipo treno
    LM_1000HZ = 3        # Luce 1000Hz
    LM_U = 4             # Luce U
    LM_M = 5             # Luce M
    LM_O = 6             # Luce O
    LM_500HZ = 7         # Luce 500Hz
    LM_BEFEHL = 8        # Luce Befehl 40


# ============== LZB SOTTOSTRUTTURA ==============

class LzbLm(IntEnum):
    """ID delle luci LZB nel sotto-nodo"""
    LM_G = 1             # Luce G
    LM_ENDE = 2          # Luce Ende
    LM_B = 3             # Luce B
    LM_UE = 4            # Luce Ü
    LM_EL = 5            # Luce EL
    LM_V40 = 6           # Luce V40
    LM_S = 7             # Luce S
    LM_PRUEF_STOER = 8   # Luce Prüf/Stör
    VSOLL = 9            # Velocità target
    VZIEL = 10           # Velocità obiettivo
    SZIEL = 11           # Distanza obiettivo


# ============== STRUTTURE DATI ==============

@dataclass
class Attribute:
    """Attributo di un nodo Zusi"""
    id: int
    data: bytes
    
    def as_uint8(self) -> int:
        return struct.unpack('<B', self.data)[0] if len(self.data) >= 1 else 0
    
    def as_uint16(self) -> int:
        return struct.unpack('<H', self.data)[0] if len(self.data) >= 2 else 0
    
    def as_int16(self) -> int:
        return struct.unpack('<h', self.data)[0] if len(self.data) >= 2 else 0
    
    def as_float(self) -> float:
        return struct.unpack('<f', self.data)[0] if len(self.data) >= 4 else 0.0
    
    def as_string(self) -> str:
        return self.data.decode('utf-8', errors='ignore').rstrip('\x00')


@dataclass
class Node:
    """Nodo di un messaggio Zusi"""
    id: int
    attributes: List[Attribute]
    children: List['Node']
    
    def __init__(self, node_id: int = 0):
        self.id = node_id
        self.attributes = []
        self.children = []
    
    def find_attribute(self, attr_id: int) -> Optional[Attribute]:
        """Trova attributo per ID"""
        for attr in self.attributes:
            if attr.id == attr_id:
                return attr
        return None
    
    def find_child(self, node_id: int) -> Optional['Node']:
        """Trova nodo figlio per ID"""
        for child in self.children:
            if child.id == node_id:
                return child
        return None


# ============== PARSER/WRITER ==============

class Zusi3Protocol:
    """Parser e writer per il protocollo Zusi3"""
    
    @staticmethod
    def read_node(sock: socket.socket) -> Node:
        """Legge un nodo dal socket"""
        # Leggi ID nodo (2 bytes)
        node_id_data = sock.recv(2)
        if len(node_id_data) < 2:
            raise ConnectionError("Connessione persa durante lettura nodo")
        node_id = struct.unpack('<H', node_id_data)[0]
        
        node = Node(node_id)
        
        while True:
            # Leggi lunghezza prossimo elemento (4 bytes)
            length_data = sock.recv(4)
            if len(length_data) < 4:
                raise ConnectionError("Connessione persa durante lettura lunghezza")
            length = struct.unpack('<I', length_data)[0]
            
            if length == NODE_START:
                # Nuovo nodo figlio
                child = Zusi3Protocol.read_node(sock)
                node.children.append(child)
            elif length == NODE_END:
                # Fine nodo corrente
                break
            else:
                # Attributo: length include ID (2 bytes) + data
                attr_id_data = sock.recv(2)
                if len(attr_id_data) < 2:
                    raise ConnectionError("Connessione persa durante lettura attributo")
                attr_id = struct.unpack('<H', attr_id_data)[0]
                
                data_length = length - 2
                data = b''
                if data_length > 0:
                    data = sock.recv(data_length)
                    if len(data) < data_length:
                        raise ConnectionError("Connessione persa durante lettura dati attributo")
                
                node.attributes.append(Attribute(attr_id, data))
        
        return node
    
    @staticmethod
    def read_message(sock: socket.socket) -> Node:
        """Legge un messaggio completo dal socket"""
        # Leggi header (deve essere 0x00000000)
        header_data = sock.recv(4)
        if len(header_data) < 4:
            raise ConnectionError("Connessione persa durante lettura header")
        header = struct.unpack('<I', header_data)[0]
        
        if header != 0:
            raise ValueError(f"Header messaggio invalido: {header}")
        
        return Zusi3Protocol.read_node(sock)
    
    @staticmethod
    def write_node(sock: socket.socket, node: Node):
        """Scrive un nodo sul socket"""
        # Inizio nodo
        sock.send(struct.pack('<I', NODE_START))
        sock.send(struct.pack('<H', node.id))
        
        # Attributi
        for attr in node.attributes:
            length = 2 + len(attr.data)  # ID + data
            sock.send(struct.pack('<I', length))
            sock.send(struct.pack('<H', attr.id))
            sock.send(attr.data)
        
        # Figli
        for child in node.children:
            Zusi3Protocol.write_node(sock, child)
        
        # Fine nodo
        sock.send(struct.pack('<I', NODE_END))
    
    @staticmethod
    def write_message(sock: socket.socket, node: Node):
        """Scrive un messaggio completo sul socket"""
        Zusi3Protocol.write_node(sock, node)


# ============== HELPER FUNCTIONS ==============

def create_attribute_uint8(attr_id: int, value: int) -> Attribute:
    return Attribute(attr_id, struct.pack('<B', value))

def create_attribute_uint16(attr_id: int, value: int) -> Attribute:
    return Attribute(attr_id, struct.pack('<H', value))

def create_attribute_int16(attr_id: int, value: int) -> Attribute:
    return Attribute(attr_id, struct.pack('<h', value))

def create_attribute_float(attr_id: int, value: float) -> Attribute:
    return Attribute(attr_id, struct.pack('<f', value))

def create_attribute_string(attr_id: int, value: str) -> Attribute:
    return Attribute(attr_id, value.encode('utf-8'))


# ============== TEST ==============

if __name__ == "__main__":
    print("Zusi3 Protocol Library")
    print("======================")
    print(f"FsData IDs disponibili: {len(FsData)}")
    for fs in FsData:
        print(f"  {fs.name} = {fs.value}")
