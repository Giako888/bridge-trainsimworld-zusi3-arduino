"""
EBuLa Display Panel — Elektronischer Buchfahrplan
===================================================
Display EBuLa per Train Simulator Bridge.

Due modalità:
1. Popup Tkinter — finestra separata con display EBuLa scorrevole
2. Web Server — pagina HTML accessibile da tablet via browser
   (HTTP + Server-Sent Events per aggiornamento in tempo reale)

Il display replica il formato EBuLa tedesco con:
- Colonne: km, Stazione, Arrivo, Partenza, Binario, Vzul, Pendenza
- Riga attiva evidenziata in base alla posizione del treno
- Profilo velocità grafico
- Indicatore ritardo
"""

import json
import socket
import logging
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Dict, Optional, List, Any

logger = logging.getLogger("EBuLaPanel")


# ============================================================
# EBuLa State Manager (importato da ebula_data)
# ============================================================

from ebula_data import (
    EBuLaStateManager, EBuLaTimetable, EBuLaEntry, TrainPosition,
    PositionTracker, EntryType, load_timetable, list_timetables,
    format_delay, get_ebula_state_manager, EBULA_DIR,
)


# ============================================================
# Colori EBuLa
# ============================================================

EBULA_BG = "#1a1a2e"          # Sfondo scuro (come display LCD)
EBULA_FG = "#e0e0e0"          # Testo principale
EBULA_HEADER_BG = "#16213e"   # Sfondo intestazione
EBULA_HEADER_FG = "#a0c4ff"   # Testo intestazione
EBULA_ROW_BG = "#1a1a2e"      # Sfondo riga normale
EBULA_ROW_ALT_BG = "#1f1f3a"  # Sfondo riga alternata
EBULA_ACTIVE_BG = "#0f3460"   # Sfondo riga attiva (posizione treno)
EBULA_ACTIVE_FG = "#ffffff"   # Testo riga attiva
EBULA_STATION_FG = "#ffffff"  # Testo stazioni
EBULA_PASS_FG = "#808080"     # Testo transiti
EBULA_SPEED_HIGH = "#a6e3a1"  # Velocità alta (verde)
EBULA_SPEED_MED = "#f9e2af"   # Velocità media (giallo)
EBULA_SPEED_LOW = "#f38ba8"   # Velocità bassa (rosso)
EBULA_DELAY_POS = "#f38ba8"   # Ritardo positivo (rosso)
EBULA_DELAY_NEG = "#a6e3a1"   # Anticipo (verde)
EBULA_DELAY_OK = "#a0a0a0"    # In orario (grigio)
EBULA_TUNNEL_FG = "#666666"   # Tunnel
EBULA_GRADIENT_UP = "#f9e2af" # Salita
EBULA_GRADIENT_DN = "#89b4fa" # Discesa


# ============================================================
# Tkinter EBuLa Panel Popup
# ============================================================

try:
    import tkinter as tk
    from tkinter import ttk
    _HAS_TK = True
except ImportError:
    _HAS_TK = False


class EBuLaPanelWindow:
    """
    Finestra popup con display EBuLa scorrevole.
    
    Layout come EBuLa reale:
    ┌──────────────────────────────────────────────────────────┐
    │  ICE 123  │  Köln Hbf → Frankfurt Hbf  │  08:42  +2min │
    ├────┬──────────┬───────┬────────┬────┬──────┬────────────┤
    │ km │ Station  │ Ank   │ Abf    │ Gl │ Vzul │   Neigung  │
    ├────┼──────────┼───────┼────────┼────┼──────┼────────────┤
    │  0 │ Köln Hbf │       │ 10:00  │  5 │  60  │     ─      │
    │  2 │          │       │        │    │ 160  │    -2‰     │
    │ 29 │ Siegburg │ 10:12 │ 10:12  │    │ 250  │            │
    │ ▶▶ │ ════════ │ HIER  │ ═══════│════│══════│════════════ │  ← train
    │ 71 │ Montabaur│ 10:24 │ 10:24  │    │ 300  │            │
    │ 99 │ Limburg S│ 10:32 │ 10:32  │    │ 300  │            │
    │177 │ Frankf.  │ 11:02 │        │ 12 │  30  │            │
    └────┴──────────┴───────┴────────┴────┴──────┴────────────┘
    """

    UPDATE_MS = 200  # Refresh rate 5 fps

    def __init__(self, parent: Optional[tk.Tk] = None):
        self._parent = parent
        self._window: Optional[tk.Toplevel] = None
        self._canvas: Optional[tk.Canvas] = None
        self._running = False
        self._state_mgr = get_ebula_state_manager()
        
        # Display state
        self._visible_entries: List[EBuLaEntry] = []
        self._current_km: float = 0.0
        self._train_number: str = ""
        self._route_name: str = ""
        self._sim_time: str = ""
        self._delay_str: str = ""
        self._speed_kmh: float = 0.0
        self._speed_limit: Optional[float] = None

    def show(self):
        """Mostra la finestra EBuLa"""
        if not _HAS_TK:
            return
        
        if self._window and self._window.winfo_exists():
            self._window.lift()
            return
        
        self._window = tk.Toplevel(self._parent)
        self._window.title("EBuLa — Elektronischer Buchfahrplan")
        self._window.geometry("750x500")
        self._window.minsize(600, 350)
        self._window.configure(bg=EBULA_BG)
        
        # Canvas per il disegno
        self._canvas = tk.Canvas(
            self._window, bg=EBULA_BG, highlightthickness=0
        )
        self._canvas.pack(fill=tk.BOTH, expand=True)
        self._canvas.bind("<Configure>", lambda e: self._draw())
        
        self._running = True
        self._schedule_update()
        
        self._window.protocol("WM_DELETE_WINDOW", self.hide)
    
    def hide(self):
        """Nasconde la finestra"""
        self._running = False
        if self._window:
            self._window.destroy()
            self._window = None
    
    @property
    def is_visible(self) -> bool:
        return self._window is not None and self._window.winfo_exists()
    
    def _schedule_update(self):
        """Pianifica il prossimo aggiornamento"""
        if not self._running or not self._window:
            return
        self._update()
        try:
            self._window.after(self.UPDATE_MS, self._schedule_update)
        except tk.TclError:
            pass
    
    def _update(self):
        """Aggiorna i dati dal state manager"""
        state = self._state_mgr.get_state()
        
        self._train_number = state.get("train_number", "")
        self._route_name = state.get("route_name", "")
        
        pos = state.get("position", {})
        self._current_km = pos.get("km", 0.0)
        self._speed_kmh = pos.get("speed_kmh", 0.0)
        self._sim_time = pos.get("sim_time", "")
        self._speed_limit = pos.get("current_speed_limit")
        self._delay_str = format_delay(pos.get("delay_seconds", 0))
        
        # Entries nella finestra visibile
        entries_data = state.get("entries", [])
        self._visible_entries = []
        for ed in entries_data:
            entry = EBuLaEntry(**{
                k: v for k, v in ed.items()
                if k in EBuLaEntry.__dataclass_fields__
            })
            self._visible_entries.append(entry)
        
        self._draw()
    
    def _draw(self):
        """Disegna il display EBuLa sul canvas"""
        if not self._canvas:
            return
        
        c = self._canvas
        c.delete("all")
        
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 10 or h < 10:
            return
        
        # Margini
        mx = 8
        my = 4
        
        # === HEADER BAR ===
        header_h = 36
        c.create_rectangle(0, 0, w, header_h, fill=EBULA_HEADER_BG, outline="")
        
        # Train number (left)
        c.create_text(mx + 4, header_h // 2, anchor="w",
                     text=self._train_number or "—",
                     fill=EBULA_HEADER_FG, font=("Consolas", 13, "bold"))
        
        # Route name (center)
        c.create_text(w // 2, header_h // 2, anchor="center",
                     text=self._route_name or "Kein Fahrplan geladen",
                     fill=EBULA_HEADER_FG, font=("Consolas", 10))
        
        # Time + delay (right)
        time_str = self._sim_time or "--:--"
        delay_color = EBULA_DELAY_OK
        if self._delay_str.startswith("+"):
            delay_color = EBULA_DELAY_POS
        elif self._delay_str.startswith("-"):
            delay_color = EBULA_DELAY_NEG
        
        right_text = f"{time_str} {self._delay_str}"
        c.create_text(w - mx - 4, header_h // 2, anchor="e",
                     text=right_text, fill=delay_color,
                     font=("Consolas", 12, "bold"))
        
        # === SPEED INDICATOR ===
        speed_bar_h = 24
        c.create_rectangle(0, header_h, w, header_h + speed_bar_h,
                          fill="#111122", outline="")
        
        speed_text = f"V: {self._speed_kmh:.0f} km/h"
        if self._speed_limit is not None:
            speed_text += f"  │  Vzul: {self._speed_limit:.0f} km/h"
            # Speed bar
            if self._speed_limit > 0:
                ratio = min(self._speed_kmh / self._speed_limit, 1.5)
                bar_w = int((w - 2 * mx) * ratio / 1.5)
                if ratio > 1.0:
                    bar_color = EBULA_SPEED_LOW
                elif ratio > 0.85:
                    bar_color = EBULA_SPEED_MED
                else:
                    bar_color = EBULA_SPEED_HIGH
                c.create_rectangle(mx, header_h + 2, mx + bar_w, 
                                  header_h + speed_bar_h - 2,
                                  fill=bar_color, outline="")
        
        c.create_text(w // 2, header_h + speed_bar_h // 2, anchor="center",
                     text=speed_text, fill=EBULA_FG,
                     font=("Consolas", 10, "bold"))
        
        km_text = f"km {self._current_km:.1f}"
        c.create_text(mx + 4, header_h + speed_bar_h // 2, anchor="w",
                     text=km_text, fill="#888888",
                     font=("Consolas", 9))
        
        # === COLUMN HEADERS ===
        table_top = header_h + speed_bar_h
        col_header_h = 22
        c.create_rectangle(0, table_top, w, table_top + col_header_h,
                          fill=EBULA_HEADER_BG, outline=EBULA_HEADER_FG)
        
        # Colonne: km | Stazione | Ank | Abf | Gl | Vzul | Neigung
        cols = self._get_columns(w, mx)
        headers = ["km", "Station", "Ank", "Abf", "Gl", "Vzul", "‰"]
        for i, (x, cw, anchor) in enumerate(cols):
            c.create_text(x, table_top + col_header_h // 2, anchor=anchor,
                         text=headers[i], fill=EBULA_HEADER_FG,
                         font=("Consolas", 9, "bold"))
        
        # === TABLE ROWS ===
        row_top = table_top + col_header_h
        row_h = 26
        available_h = h - row_top
        max_rows = max(1, available_h // row_h)
        
        # Disegna righe
        for i, entry in enumerate(self._visible_entries[:max_rows]):
            y = row_top + i * row_h
            
            # Riga attiva?
            is_active = False
            if entry.km is not None:
                dist = abs(entry.km - self._current_km)
                if dist < 0.5:
                    is_active = True
            
            # Sfondo riga
            if is_active:
                bg = EBULA_ACTIVE_BG
            elif i % 2 == 0:
                bg = EBULA_ROW_BG
            else:
                bg = EBULA_ROW_ALT_BG
            
            c.create_rectangle(0, y, w, y + row_h, fill=bg, outline="")
            
            # Colori testo
            if is_active:
                fg = EBULA_ACTIVE_FG
            elif entry.type in (EntryType.STATION, EntryType.HALT):
                fg = EBULA_STATION_FG if entry.is_stopping else EBULA_PASS_FG
            elif entry.type == EntryType.TUNNEL_START:
                fg = EBULA_TUNNEL_FG
            else:
                fg = EBULA_FG
            
            # Indicatore riga attiva
            if is_active:
                c.create_text(mx, y + row_h // 2, anchor="w",
                             text="▶", fill="#00ff88",
                             font=("Consolas", 10, "bold"))
            
            # Disegna celle
            self._draw_row(c, entry, y, row_h, cols, fg, is_active)
        
        # Se no entries
        if not self._visible_entries:
            c.create_text(w // 2, row_top + 40, anchor="center",
                         text="Kein Fahrplan geladen\n\n"
                              "Lade einen .ebula.json Fahrplan\n"
                              "oder verbinde dich mit Zusi 3",
                         fill="#666666", font=("Consolas", 11),
                         justify="center")
    
    def _get_columns(self, w: int, mx: int) -> list:
        """Ritorna posizioni colonne: [(x, width, anchor), ...]"""
        # km | Station | Ank | Abf | Gl | Vzul | Neigung
        km_x = mx + 28
        station_x = mx + 60
        ank_x = w * 0.50
        abf_x = w * 0.60
        gl_x = w * 0.70
        vzul_x = w * 0.80
        neig_x = w * 0.92
        
        return [
            (km_x, 50, "e"),         # km (right-aligned)
            (station_x, 180, "w"),   # Station
            (ank_x, 50, "center"),   # Ank
            (abf_x, 50, "center"),   # Abf
            (gl_x, 30, "center"),    # Gl
            (vzul_x, 50, "center"),  # Vzul
            (neig_x, 50, "center"),  # Neigung
        ]
    
    def _draw_row(self, c: tk.Canvas, entry: EBuLaEntry, y: int, h: int,
                  cols: list, fg: str, is_active: bool):
        """Disegna una riga della tabella"""
        cy = y + h // 2
        font = ("Consolas", 10)
        font_bold = ("Consolas", 10, "bold")
        
        # km
        km_str = f"{entry.km:.1f}" if entry.km >= 0 else ""
        c.create_text(cols[0][0], cy, anchor=cols[0][2],
                     text=km_str, fill=fg, font=font)
        
        # Station name
        name = entry.name
        if entry.type == EntryType.TUNNEL_START:
            name = f"⬛ {name}"
        elif entry.type == EntryType.TUNNEL_END:
            name = "⬛ Ende"
        elif entry.type == EntryType.BRIDGE:
            name = f"🌉 {name}"
        
        st_font = font_bold if entry.is_stopping else font
        c.create_text(cols[1][0], cy, anchor=cols[1][2],
                     text=name, fill=fg, font=st_font)
        
        # Ank (arrival)
        if entry.arrival:
            c.create_text(cols[2][0], cy, anchor=cols[2][2],
                         text=entry.arrival, fill=fg, font=font)
        
        # Abf (departure)
        if entry.departure:
            c.create_text(cols[3][0], cy, anchor=cols[3][2],
                         text=entry.departure, fill=fg, font=font)
        
        # Gl (track)
        if entry.track:
            c.create_text(cols[4][0], cy, anchor=cols[4][2],
                         text=entry.track, fill=fg, font=font)
        
        # Vzul (speed limit)
        if entry.speed_limit is not None:
            speed_fg = fg
            if not is_active:
                if entry.speed_limit >= 200:
                    speed_fg = EBULA_SPEED_HIGH
                elif entry.speed_limit >= 100:
                    speed_fg = EBULA_SPEED_MED
                else:
                    speed_fg = EBULA_SPEED_LOW
            c.create_text(cols[5][0], cy, anchor=cols[5][2],
                         text=f"{entry.speed_limit:.0f}",
                         fill=speed_fg, font=font_bold)
        
        # Neigung (gradient)
        if entry.gradient is not None:
            grad_fg = fg
            if not is_active:
                if entry.gradient > 0:
                    grad_fg = EBULA_GRADIENT_UP
                elif entry.gradient < 0:
                    grad_fg = EBULA_GRADIENT_DN
            grad_str = f"{entry.gradient:+.0f}" if entry.gradient != 0 else "─"
            c.create_text(cols[6][0], cy, anchor=cols[6][2],
                         text=grad_str, fill=grad_fg, font=font)


# ============================================================
# Web Server — EBuLa HTML + SSE
# ============================================================

def _build_ebula_html() -> str:
    """Costruisce la pagina HTML EBuLa (self-contained, no external deps)"""
    return '''<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>EBuLa — Elektronischer Buchfahrplan</title>
<style>
:root {
  --bg: #1a1a2e;
  --fg: #e0e0e0;
  --header-bg: #16213e;
  --header-fg: #a0c4ff;
  --row-bg: #1a1a2e;
  --row-alt: #1f1f3a;
  --active-bg: #0f3460;
  --active-fg: #ffffff;
  --station-fg: #ffffff;
  --pass-fg: #808080;
  --speed-high: #a6e3a1;
  --speed-med: #f9e2af;
  --speed-low: #f38ba8;
  --delay-pos: #f38ba8;
  --delay-neg: #a6e3a1;
  --delay-ok: #a0a0a0;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  background: var(--bg); color: var(--fg);
  font-family: 'Consolas', 'Courier New', monospace;
  font-size: 14px; overflow: hidden; height: 100vh;
}
.header {
  display: flex; justify-content: space-between; align-items: center;
  background: var(--header-bg); padding: 8px 16px;
  border-bottom: 1px solid #333;
}
.header .train { font-size: 18px; font-weight: bold; color: var(--header-fg); }
.header .route { font-size: 12px; color: var(--header-fg); opacity: 0.8; }
.header .time { font-size: 16px; font-weight: bold; }
.speed-bar {
  display: flex; align-items: center; justify-content: space-between;
  background: #111122; padding: 6px 16px; position: relative;
  border-bottom: 1px solid #222;
}
.speed-bar .km { color: #888; font-size: 12px; }
.speed-bar .speed { font-size: 14px; font-weight: bold; }
.speed-bar .bar {
  position: absolute; left: 0; top: 0; bottom: 0;
  opacity: 0.15; transition: width 0.3s;
}
.table-header {
  display: grid;
  grid-template-columns: 60px 1fr 65px 65px 40px 60px 55px;
  background: var(--header-bg); padding: 4px 8px;
  border-bottom: 1px solid var(--header-fg);
  font-size: 11px; font-weight: bold; color: var(--header-fg);
}
.table-header > div { text-align: center; }
.table-header > div:nth-child(1) { text-align: right; }
.table-header > div:nth-child(2) { text-align: left; padding-left: 8px; }
.rows { overflow-y: auto; height: calc(100vh - 120px); }
.row {
  display: grid;
  grid-template-columns: 60px 1fr 65px 65px 40px 60px 55px;
  padding: 5px 8px; align-items: center; min-height: 32px;
  border-bottom: 1px solid #222;
  transition: background 0.3s;
}
.row:nth-child(even) { background: var(--row-alt); }
.row.active {
  background: var(--active-bg) !important;
  color: var(--active-fg);
  border-left: 3px solid #00ff88;
  font-weight: bold;
}
.row.station .name { color: var(--station-fg); font-weight: bold; }
.row.pass .name { color: var(--pass-fg); }
.row .km { text-align: right; color: #888; font-size: 12px; }
.row .name { text-align: left; padding-left: 8px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.row .arr, .row .dep, .row .gl, .row .vzul, .row .grad { text-align: center; }
.row .vzul { font-weight: bold; }
.vzul.high { color: var(--speed-high); }
.vzul.med { color: var(--speed-med); }
.vzul.low { color: var(--speed-low); }
.grad.up { color: #f9e2af; }
.grad.dn { color: #89b4fa; }
.time.delayed { color: var(--delay-pos); }
.time.early { color: var(--delay-neg); }
.time.ontime { color: var(--delay-ok); }
.no-data {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; height: 60vh; color: #666;
  font-size: 16px; text-align: center; line-height: 2;
}
.status { position: fixed; bottom: 4px; right: 8px; font-size: 10px; color: #444; }

/* Tablet landscape optimization */
@media (min-width: 768px) and (orientation: landscape) {
  body { font-size: 16px; }
  .row { min-height: 38px; }
}

/* Phone portrait */
@media (max-width: 480px) {
  .table-header, .row {
    grid-template-columns: 45px 1fr 55px 55px 30px 50px 45px;
  }
  body { font-size: 12px; }
}
</style>
</head>
<body>

<div class="header">
  <span class="train" id="trainNumber">—</span>
  <span class="route" id="routeName">Kein Fahrplan geladen</span>
  <span class="time" id="timeDisplay">--:--</span>
</div>

<div class="speed-bar">
  <div class="bar" id="speedBar"></div>
  <span class="km" id="kmDisplay">km 0.0</span>
  <span class="speed" id="speedDisplay">V: 0 km/h</span>
</div>

<div class="table-header">
  <div>km</div>
  <div>Station</div>
  <div>Ank</div>
  <div>Abf</div>
  <div>Gl</div>
  <div>Vzul</div>
  <div>‰</div>
</div>

<div class="rows" id="rows">
  <div class="no-data">
    Kein Fahrplan geladen<br>
    Lade einen .ebula.json Fahrplan<br>
    oder verbinde dich mit Zusi 3
  </div>
</div>

<div class="status" id="status">Connecting...</div>

<script>
const $ = id => document.getElementById(id);

let lastVersion = -1;
let activeKm = 0;

function formatDelay(seconds) {
  if (Math.abs(seconds) < 30) return '±0';
  const min = Math.floor(seconds / 60);
  return min > 0 ? '+' + min : '' + min;
}

function speedClass(v) {
  if (v >= 200) return 'high';
  if (v >= 100) return 'med';
  return 'low';
}

function gradClass(g) {
  if (g > 0) return 'up';
  if (g < 0) return 'dn';
  return '';
}

function updateDisplay(data) {
  if (!data) return;
  
  const pos = data.position || {};
  const entries = data.entries || [];
  
  // Header
  $('trainNumber').textContent = data.train_number || '—';
  $('routeName').textContent = data.route_name || 'Kein Fahrplan geladen';
  
  // Time + delay
  const simTime = pos.sim_time || '--:--';
  const delay = pos.delay_seconds || 0;
  const delayStr = formatDelay(delay);
  const timeEl = $('timeDisplay');
  timeEl.textContent = simTime + ' ' + delayStr;
  timeEl.className = 'time ' + (delay > 30 ? 'delayed' : delay < -30 ? 'early' : 'ontime');
  
  // Speed
  const speed = pos.speed_kmh || 0;
  const limit = pos.current_speed_limit;
  let speedText = 'V: ' + speed.toFixed(0) + ' km/h';
  if (limit != null) speedText += '  │  Vzul: ' + limit.toFixed(0) + ' km/h';
  $('speedDisplay').textContent = speedText;
  
  // Speed bar
  const bar = $('speedBar');
  if (limit && limit > 0) {
    const ratio = Math.min(speed / limit, 1.5);
    bar.style.width = (ratio / 1.5 * 100) + '%';
    bar.style.background = ratio > 1 ? '#f38ba8' : ratio > 0.85 ? '#f9e2af' : '#a6e3a1';
  } else {
    bar.style.width = '0%';
  }
  
  // km
  activeKm = pos.km || 0;
  $('kmDisplay').textContent = 'km ' + activeKm.toFixed(1);
  
  // Rows
  const rowsEl = $('rows');
  
  if (entries.length === 0) {
    rowsEl.innerHTML = '<div class="no-data">Kein Fahrplan geladen<br>Lade einen .ebula.json Fahrplan<br>oder verbinde dich mit Zusi 3</div>';
    return;
  }
  
  let html = '';
  entries.forEach((e, i) => {
    const isActive = Math.abs((e.km || 0) - activeKm) < 0.5;
    const isStation = e.type === 'station' || e.type === 'halt';
    const isStopping = e.is_stopping;
    
    let cls = 'row';
    if (isActive) cls += ' active';
    if (isStation && isStopping) cls += ' station';
    else if (isStation) cls += ' pass';
    
    let name = e.name || '';
    if (e.type === 'tunnel_start') name = '⬛ ' + name;
    else if (e.type === 'tunnel_end') name = '⬛ Ende';
    else if (e.type === 'bridge') name = '🌉 ' + name;
    
    const km = e.km != null ? e.km.toFixed(1) : '';
    const arr = e.arrival || '';
    const dep = e.departure || '';
    const gl = e.track || '';
    
    let vzulHtml = '';
    if (e.speed_limit != null) {
      vzulHtml = '<div class="vzul ' + speedClass(e.speed_limit) + '">' + e.speed_limit.toFixed(0) + '</div>';
    } else {
      vzulHtml = '<div class="vzul"></div>';
    }
    
    let gradHtml = '';
    if (e.gradient != null && e.gradient !== 0) {
      const sign = e.gradient > 0 ? '+' : '';
      gradHtml = '<div class="grad ' + gradClass(e.gradient) + '">' + sign + e.gradient.toFixed(0) + '</div>';
    } else if (e.gradient === 0) {
      gradHtml = '<div class="grad">─</div>';
    } else {
      gradHtml = '<div class="grad"></div>';
    }
    
    html += '<div class="' + cls + '">';
    html += '<div class="km">' + km + '</div>';
    html += '<div class="name">' + (isActive ? '▶ ' : '') + name + '</div>';
    html += '<div class="arr">' + arr + '</div>';
    html += '<div class="dep">' + dep + '</div>';
    html += '<div class="gl">' + gl + '</div>';
    html += vzulHtml;
    html += gradHtml;
    html += '</div>';
  });
  
  rowsEl.innerHTML = html;
  
  // Scroll to active row
  const activeRow = rowsEl.querySelector('.active');
  if (activeRow) {
    activeRow.scrollIntoView({ block: 'center', behavior: 'smooth' });
  }
}

// SSE connection
function connect() {
  $('status').textContent = 'Connecting...';
  
  const es = new EventSource('/ebula/events');
  
  es.onopen = () => {
    $('status').textContent = 'Connected ✓';
  };
  
  es.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      updateDisplay(data);
      $('status').textContent = 'Live ✓';
    } catch (e) {
      console.error('Parse error:', e);
    }
  };
  
  es.onerror = () => {
    $('status').textContent = 'Reconnecting...';
    es.close();
    setTimeout(connect, 2000);
  };
}

// Wake Lock (keep screen on)
async function requestWakeLock() {
  try {
    if ('wakeLock' in navigator) {
      await navigator.wakeLock.request('screen');
    }
  } catch (e) {}
}

// Init
connect();
requestWakeLock();
document.addEventListener('visibilitychange', () => {
  if (!document.hidden) requestWakeLock();
});
</script>
</body>
</html>'''


class _EBuLaRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler per EBuLa web server"""
    
    def log_message(self, format, *args):
        pass  # Silenzioso
    
    def do_GET(self):
        if self.path == "/ebula" or self.path == "/ebula/":
            self._serve_html()
        elif self.path == "/ebula/events":
            self._serve_sse()
        elif self.path == "/ebula/api/state":
            self._serve_api()
        else:
            self.send_error(404)
    
    def _serve_html(self):
        html = _build_ebula_html()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))
    
    def _serve_api(self):
        mgr = get_ebula_state_manager()
        state = mgr.get_state()
        payload = json.dumps(state, default=str)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload.encode("utf-8"))
    
    def _serve_sse(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        
        mgr = get_ebula_state_manager()
        last_version = -1
        
        try:
            while True:
                new_version = mgr.wait_for_change(last_version, timeout=1.0)
                if new_version != last_version:
                    last_version = new_version
                    state = mgr.get_state()
                    payload = json.dumps(state, default=str)
                    self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                    self.wfile.flush()
                else:
                    # Heartbeat
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass


class _ThreadedEBuLaServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class EBuLaWebServer:
    """Web server per EBuLa display via browser"""
    
    def __init__(self, port: int = 8081):
        self.port = port
        self._server: Optional[_ThreadedEBuLaServer] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
    
    @property
    def is_running(self) -> bool:
        return self._running and self._server is not None
    
    @property
    def url(self) -> str:
        ip = _get_local_ip()
        return f"http://{ip}:{self.port}/ebula"
    
    def start(self) -> bool:
        if self._running:
            return True
        try:
            self._server = _ThreadedEBuLaServer(("0.0.0.0", self.port), _EBuLaRequestHandler)
            self._thread = threading.Thread(target=self._run, daemon=True, name="EBuLaWebServer")
            self._thread.start()
            self._running = True
            logger.info(f"EBuLa Web Server started on {self.url}")
            return True
        except OSError as e:
            logger.error(f"Cannot start EBuLa Web Server on port {self.port}: {e}")
            self._server = None
            return False
    
    def _run(self):
        try:
            self._server.serve_forever()
        except Exception as e:
            logger.error(f"EBuLa Web Server error: {e}")
        finally:
            self._running = False
    
    def stop(self):
        if self._server:
            try:
                self._server.shutdown()
            except Exception:
                pass
            self._server = None
        self._running = False
        logger.info("EBuLa Web Server stopped")


# ============================================================
# Utility
# ============================================================

def _get_local_ip() -> str:
    """Trova l'indirizzo IP locale"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"
