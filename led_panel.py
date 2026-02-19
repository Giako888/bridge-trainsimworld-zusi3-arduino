"""
MFA LED Panel — Train Simulator Bridge
=======================================
Pannello MFA (Modulares Führerraum-Anzeigegerät) che replica
le spie luminose di un vero pannello MFA tedesco.

Due modalità:
1. Popup Tkinter — finestra separata con pannello realistico
2. Web Server — pagina HTML accessibile da tablet via browser
   (HTTP + Server-Sent Events per latenza quasi zero)
"""

import json
import socket
import logging
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from typing import Dict, Optional, Tuple

import tkinter as tk

logger = logging.getLogger("MFAPanel")

# ============================================================
# Colori
# ============================================================

PANEL_BG = "#0a0a0a"         # Sfondo pannello (quasi nero)
PANEL_BORDER = "#2a2a2a"     # Bordo pannello
GROUP_BG = "#111111"          # Sfondo gruppi
GROUP_BORDER = "#333333"      # Bordo gruppi
LABEL_FG = "#aaaaaa"          # Testo etichette
HEADER_FG = "#888888"         # Testo intestazioni gruppo

# Colori blocchi MFA — come il vero pannello: blocchi rettangolari colorati
BLOCK_COLORS = {
    "giallo": {
        "bg_on": "#FFD000", "fg_on": "#000000",
        "bg_off": "#5a5a5a", "fg_off": "#404040",
        "border_on": "#b89800", "border_off": "#4a4a4a",
    },
    "blu": {
        "bg_on": "#2266EE", "fg_on": "#FFFFFF",
        "bg_off": "#5a5a5a", "fg_off": "#404040",
        "border_on": "#1a4eaa", "border_off": "#4a4a4a",
    },
    "rosso": {
        "bg_on": "#DD2020", "fg_on": "#FFFFFF",
        "bg_off": "#5a5a5a", "fg_off": "#404040",
        "border_on": "#aa1818", "border_off": "#4a4a4a",
    },
    "bianco": {
        "bg_on": "#E8E8E8", "fg_on": "#000000",
        "bg_off": "#5a5a5a", "fg_off": "#404040",
        "border_on": "#aaaaaa", "border_off": "#4a4a4a",
    },
}

# Override colore pannello MFA: il SIFA nel vero MFA è bianco, non giallo
MFA_COLOR_OVERRIDES = {
    "SIFA": "bianco",
}

# LED con label grande (numeri/lettere singole come nel vero MFA)
BIG_LABEL_LEDS = {"PZB55", "PZB70", "PZB85", "LZB_UE", "LZB_G", "LZB_S"}
# LED con label media (parole corte)
MID_LABEL_LEDS = {"SIFA", "LZB", "500HZ", "1000HZ", "BEF40"}
# LED porte (layout speciale T + freccia)
DOOR_LEDS = {"TUEREN_L", "TUEREN_R"}

# Colori per il web (CSS, supporta rgba)
WEB_BLOCK_COLORS = {
    "giallo": {
        "bg_on": "#FFD000", "fg_on": "#000",
        "glow": "rgba(255,208,0,0.35)",
        "bg_off": "#5a5a5a", "fg_off": "#404040",
    },
    "blu": {
        "bg_on": "#2266EE", "fg_on": "#fff",
        "glow": "rgba(34,102,238,0.35)",
        "bg_off": "#5a5a5a", "fg_off": "#404040",
    },
    "rosso": {
        "bg_on": "#DD2020", "fg_on": "#fff",
        "glow": "rgba(221,32,32,0.35)",
        "bg_off": "#5a5a5a", "fg_off": "#404040",
    },
    "bianco": {
        "bg_on": "#E8E8E8", "fg_on": "#000",
        "glow": "rgba(232,232,232,0.3)",
        "bg_off": "#5a5a5a", "fg_off": "#404040",
    },
}

# ============================================================
# Layout MFA — Disposizione come il vero pannello MFA tedesco
# ============================================================

# Importa definizioni LED da arduino_bridge
from arduino_bridge import LEDS, LED_BY_NAME

# Layout MFA a due sezioni come nell'immagine originale
# Left: Fahrzeugstatus | Right: Zugbeeinflussung (PZB / LZB)
MFA_SECTIONS = {
    "left": {
        "header": "Fahrzeugstatus",
        "grid": [
            # Riga 1
            [{"name": "TUEREN_L", "label": "T ◀"}, {"name": "SIFA", "label": "Sifa"}],
            # Riga 2
            [{"name": "TUEREN_R", "label": "T ▶"}, None],
        ],
    },
    "right": {
        "header": "Zugbeeinflussung (PZB / LZB)",
        "grid": [
            # Riga 1: Zugart + LZB
            [
                {"name": "PZB55", "label": "55"},
                {"name": "PZB70", "label": "70"},
                {"name": "PZB85", "label": "85"},
                {"name": "LZB",   "label": "Ende"},
                {"name": "LZB_UE","label": "Ü"},
            ],
            # Riga 2: Befehl 40 + Beeinflussung + LZB
            [
                {"name": "BEF40",  "label": "Bef\n40"},
                {"name": "500HZ",  "label": "500\nHz"},
                {"name": "1000HZ", "label": "1000\nHz"},
                {"name": "LZB_G",  "label": "G"},
                {"name": "LZB_S",  "label": "S"},
            ],
        ],
    },
}


# ============================================================
# Shared LED State Manager
# ============================================================

class LEDStateManager:
    """Gestore thread-safe dello stato LED, condiviso tra GUI, popup e web server."""

    def __init__(self):
        self._condition = threading.Condition()
        self._states: Dict[str, bool] = {}
        self._blinks: Dict[str, float] = {}
        self._version: int = 0

    def update(self, states: Dict[str, bool], blinks: Dict[str, float]):
        """Aggiorna stato LED (thread-safe). Notifica tutti i listeners."""
        with self._condition:
            self._states = dict(states)
            self._blinks = dict(blinks)
            self._version += 1
            self._condition.notify_all()

    def get(self) -> Tuple[Dict[str, bool], Dict[str, float], int]:
        """Ritorna (states, blinks, version)."""
        with self._condition:
            return dict(self._states), dict(self._blinks), self._version

    def wait_for_change(self, last_version: int, timeout: float = 1.0) -> Tuple[Dict[str, bool], Dict[str, float], int]:
        """Attende un cambio di stato o timeout. Ritorna stato corrente."""
        with self._condition:
            if self._version == last_version:
                self._condition.wait(timeout=timeout)
            return dict(self._states), dict(self._blinks), self._version


# Istanza globale condivisa
_led_state_mgr = LEDStateManager()


def get_led_state_manager() -> LEDStateManager:
    return _led_state_mgr


# ============================================================
# Tkinter MFA Panel Popup
# ============================================================

class MFAPanelWindow:
    """Finestra popup con pannello MFA realistico — blocchi rettangolari come il vero MFA."""

    BLOCK_W = 72           # Larghezza blocco LED (base)
    BLOCK_H = 56           # Altezza blocco LED (base)
    BLOCK_GAP = 2          # Gap tra blocchi
    UPDATE_MS = 80         # Refresh rate ~12 fps

    # Dimensioni riferimento per scaling proporzionale
    REF_WIDTH = 820
    REF_HEIGHT = 360

    # Font base alle dimensioni di riferimento
    _FONT_SIZES = {
        "door": 20,
        "big": 28,
        "mid": 18,
        "default": 13,
    }

    def __init__(self, parent: tk.Tk):
        self.parent = parent
        self.window: Optional[tk.Toplevel] = None
        self._led_widgets: Dict[str, dict] = {}
        self._all_blocks: list = []  # tutti i blocchi (inclusi vuoti) per resize
        self._running = False
        self._last_scale = 1.0

    @property
    def is_open(self) -> bool:
        return self.window is not None and self.window.winfo_exists()

    def toggle(self):
        """Apri o chiudi il pannello."""
        if self.is_open:
            self.close()
        else:
            self.open()

    def open(self):
        """Apri la finestra MFA Panel."""
        if self.is_open:
            self.window.lift()
            self.window.focus_force()
            return

        self.window = tk.Toplevel(self.parent)
        self.window.title("MFA Panel — Train Simulator Bridge")
        self.window.configure(bg=PANEL_BG)
        self.window.resizable(True, True)
        self.window.minsize(680, 300)
        self.window.geometry("820x360")

        # Icona (stessa della finestra principale)
        import os, sys
        icon_path = os.path.join(
            getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__))),
            "tsw6_bridge.ico"
        )
        if os.path.exists(icon_path):
            try:
                self.window.iconbitmap(icon_path)
            except Exception:
                pass

        self.window.protocol("WM_DELETE_WINDOW", self.close)

        self._build_panel()
        self._running = True
        self._update_loop()

    def close(self):
        """Chiudi la finestra."""
        self._running = False
        if self.window:
            try:
                self.window.destroy()
            except Exception:
                pass
            self.window = None
        self._led_widgets.clear()
        self._all_blocks.clear()

    def _build_panel(self):
        """Costruisce il pannello MFA con blocchi rettangolari come nell'immagine."""
        # Frame esterno effetto metallico
        outer = tk.Frame(self.window, bg="#1a1a1a", padx=2, pady=2)
        outer.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        panel = tk.Frame(outer, bg=PANEL_BG, padx=8, pady=6)
        panel.pack(fill=tk.BOTH, expand=True)

        # Titolo
        tk.Label(
            panel, text="M  F  A", font=("Consolas", 12, "bold"),
            fg="#444444", bg=PANEL_BG
        ).pack(pady=(4, 8))

        # Container principale centrato (mantiene proporzioni)
        main_row = tk.Frame(panel, bg=PANEL_BG)
        main_row.pack(expand=True)  # centrato, non fill

        # Sezione sinistra: Fahrzeugstatus
        left_section = self._build_section(main_row, MFA_SECTIONS["left"])
        left_section.pack(side=tk.LEFT, padx=(0, 4))

        # Separatore verticale rosso (come nel vero MFA)
        sep = tk.Frame(main_row, bg="#882222", width=3)
        sep.pack(side=tk.LEFT, fill=tk.Y, padx=4)

        # Sezione destra: Zugbeeinflussung PZB/LZB
        right_section = self._build_section(main_row, MFA_SECTIONS["right"])
        right_section.pack(side=tk.LEFT, padx=(4, 0))

        # Ridimensionamento proporzionale (stessa scala per tutti)
        self.window.bind("<Configure>", self._on_resize)

    def _build_section(self, parent: tk.Widget, section: dict) -> tk.Frame:
        """Costruisce una sezione MFA con header e griglia di blocchi."""
        frame = tk.Frame(parent, bg=PANEL_BG)

        # Header sezione
        tk.Label(
            frame, text=section["header"],
            font=("Consolas", 8, "bold"), fg=HEADER_FG, bg=PANEL_BG
        ).pack(pady=(0, 4))

        # Griglia di blocchi (dimensioni esplicite, proporzionali)
        grid_frame = tk.Frame(frame, bg="#3a3a3a", padx=1, pady=1)
        grid_frame.pack()

        for r, row_data in enumerate(section["grid"]):
            for c, cell_def in enumerate(row_data):
                if cell_def is None:
                    # Slot vuoto (placeholder)
                    empty = tk.Frame(
                        grid_frame, width=self.BLOCK_W, height=self.BLOCK_H,
                        bg="#4a4a4a", highlightthickness=1, highlightbackground="#444444"
                    )
                    empty.grid(row=r, column=c, padx=self.BLOCK_GAP//2, pady=self.BLOCK_GAP//2)
                    empty.grid_propagate(False)
                    self._all_blocks.append({"frame": empty, "is_empty": True})
                    continue

                led_info = LED_BY_NAME.get(cell_def["name"])
                base_color = led_info.color if led_info else "giallo"
                color_key = MFA_COLOR_OVERRIDES.get(cell_def["name"], base_color)
                colors = BLOCK_COLORS.get(color_key, BLOCK_COLORS["giallo"])

                # Blocco LED (Frame con Label dentro)
                block = tk.Frame(
                    grid_frame, width=self.BLOCK_W, height=self.BLOCK_H,
                    bg=colors["bg_off"],
                    highlightthickness=1, highlightbackground=colors["border_off"]
                )
                block.grid(row=r, column=c, padx=self.BLOCK_GAP//2, pady=self.BLOCK_GAP//2)
                block.grid_propagate(False)

                # Categoria font per scaling proporzionale
                led_name = cell_def["name"]
                if led_name in DOOR_LEDS:
                    font_cat = "door"
                elif led_name in BIG_LABEL_LEDS:
                    font_cat = "big"
                elif led_name in MID_LABEL_LEDS:
                    font_cat = "mid"
                else:
                    font_cat = "default"

                font_size = self._FONT_SIZES[font_cat]
                label = tk.Label(
                    block, text=cell_def["label"],
                    font=("Consolas", font_size, "bold"), fg=colors["fg_off"], bg=colors["bg_off"],
                    justify=tk.CENTER
                )
                label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

                self._led_widgets[cell_def["name"]] = {
                    "block": block,
                    "label": label,
                    "color_key": color_key,
                    "font_cat": font_cat,
                }
                self._all_blocks.append({"frame": block, "is_empty": False})

        return frame

    def _on_resize(self, event=None):
        """Riscala blocchi e font proporzionalmente, mantenendo il rapporto 72:56."""
        if not self.is_open:
            return
        if event and event.widget is not self.window:
            return
        w = self.window.winfo_width()
        h = self.window.winfo_height()
        scale = min(w / self.REF_WIDTH, h / self.REF_HEIGHT)
        scale = max(0.5, min(scale, 2.5))
        if abs(scale - self._last_scale) < 0.03:
            return
        self._last_scale = scale

        # Ridimensiona TUTTI i blocchi mantenendo le proporzioni
        new_w = max(32, int(self.BLOCK_W * scale))
        new_h = max(24, int(self.BLOCK_H * scale))
        for blk in self._all_blocks:
            try:
                blk["frame"].configure(width=new_w, height=new_h)
            except tk.TclError:
                pass

        # Ridimensiona i font
        for info in self._led_widgets.values():
            base = self._FONT_SIZES.get(info.get("font_cat", "default"), 13)
            new_size = max(8, int(base * scale))
            try:
                info["label"].configure(font=("Consolas", new_size, "bold"))
            except tk.TclError:
                pass

    def _update_loop(self):
        """Aggiornamento periodico dei LED dal LEDStateManager."""
        if not self._running or not self.is_open:
            return

        states, blinks, _ = _led_state_mgr.get()
        now = time.monotonic()

        # Wechselblinken detection
        pzb70_blinking = states.get("PZB70", False) and blinks.get("PZB70", 0.0) > 0
        pzb85_blinking = states.get("PZB85", False) and blinks.get("PZB85", 0.0) > 0
        both_pzb_blink = pzb70_blinking and pzb85_blinking

        for name, w in self._led_widgets.items():
            is_on = states.get(name, False)
            blink_interval = blinks.get(name, 0.0)

            if is_on and blink_interval > 0:
                phase = int(now / blink_interval) % 2
                if both_pzb_blink and name == "PZB85":
                    phase = 1 - phase
                show_on = (phase == 0)
            else:
                show_on = is_on

            colors = BLOCK_COLORS.get(w["color_key"], BLOCK_COLORS["giallo"])
            block = w["block"]
            label = w["label"]

            if show_on:
                block.config(bg=colors["bg_on"], highlightbackground=colors["border_on"])
                label.config(bg=colors["bg_on"], fg=colors["fg_on"])
            else:
                block.config(bg=colors["bg_off"], highlightbackground=colors["border_off"])
                label.config(bg=colors["bg_off"], fg=colors["fg_off"])

        try:
            self.window.after(self.UPDATE_MS, self._update_loop)
        except Exception:
            pass


# ============================================================
# HTML/CSS/JS per Web Panel (embedded)
# ============================================================

def _build_html() -> str:
    """Genera la pagina HTML del pannello MFA per browser/tablet — stile blocchi rettangolari."""

    # Genera dati LED per JS
    led_data = {}
    for section in MFA_SECTIONS.values():
        for row in section["grid"]:
            for cell_def in row:
                if cell_def is None:
                    continue
                info = LED_BY_NAME.get(cell_def["name"])
                base_color = info.color if info else "giallo"
                color_key = MFA_COLOR_OVERRIDES.get(cell_def["name"], base_color)
                web_colors = WEB_BLOCK_COLORS.get(color_key, WEB_BLOCK_COLORS["giallo"])
                led_data[cell_def["name"]] = {
                    "label": cell_def["label"],
                    "bg_on": web_colors["bg_on"],
                    "fg_on": web_colors["fg_on"],
                    "glow": web_colors["glow"],
                    "bg_off": web_colors["bg_off"],
                    "fg_off": web_colors["fg_off"],
                }

    def _cell_html(cell_def):
        if cell_def is None:
            return '<div class="mfa-block empty"></div>'
        # Multiline label: replace \n with <br>
        label_html = cell_def["label"].replace("\n", "<br>")
        name = cell_def["name"]
        if name in DOOR_LEDS:
            extra_cls = " door-text"
        elif name in BIG_LABEL_LEDS:
            extra_cls = " big-text"
        elif name in MID_LABEL_LEDS:
            extra_cls = " mid-text"
        else:
            extra_cls = ""
        return (f'<div class="mfa-block{extra_cls}" id="block-{name}">'
                f'<span class="mfa-text">{label_html}</span></div>')

    def _section_html(section_id, section):
        rows_html = ""
        for row_data in section["grid"]:
            cells = "".join(_cell_html(c) for c in row_data)
            rows_html += f'<div class="mfa-row">{cells}</div>'
        return (f'<div class="mfa-section" id="section-{section_id}">'
                f'<div class="section-header">{section["header"]}</div>'
                f'<div class="mfa-grid">{rows_html}</div></div>')

    left_html = _section_html("left", MFA_SECTIONS["left"])
    right_html = _section_html("right", MFA_SECTIONS["right"])

    led_data_json = json.dumps(led_data)

    return f'''<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<title>MFA Panel — Train Simulator Bridge</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}

    body {{
        background: #050505;
        color: #aaa;
        font-family: 'Consolas', 'Courier New', monospace;
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 100vh;
        overflow: hidden;
        -webkit-user-select: none;
        user-select: none;
    }}

    #panel {{
        background: #0a0a0a;
        border: 3px solid #1a1a1a;
        border-radius: 8px;
        padding: 16px 20px;
        box-shadow: 0 0 40px rgba(0,0,0,0.8), inset 0 0 20px rgba(0,0,0,0.5);
        max-width: 860px;
        width: 98vw;
    }}

    #panel-title {{
        text-align: center;
        font-size: 14px;
        font-weight: bold;
        color: #444;
        letter-spacing: 6px;
        margin-bottom: 12px;
    }}

    #mfa-body {{
        display: flex;
        gap: 8px;
        justify-content: center;
        align-items: flex-start;
    }}

    .mfa-separator {{
        width: 3px;
        background: #882222;
        align-self: stretch;
        margin: 18px 6px 0;
        border-radius: 2px;
    }}

    .mfa-section {{
        display: flex;
        flex-direction: column;
        align-items: center;
    }}

    .section-header {{
        font-size: 9px;
        font-weight: bold;
        color: #555;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-bottom: 6px;
        text-align: center;
        white-space: nowrap;
    }}

    .mfa-grid {{
        display: flex;
        flex-direction: column;
        gap: 2px;
        background: #3a3a3a;
        padding: 2px;
        border-radius: 4px;
    }}

    .mfa-row {{
        display: flex;
        gap: 2px;
    }}

    .mfa-block {{
        width: 72px;
        height: 56px;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 1px solid #4a4a4a;
        border-radius: 2px;
        transition: background 0.06s ease, color 0.06s ease, box-shadow 0.06s ease, border-color 0.06s ease;
        background: #5a5a5a;
    }}

    .mfa-block.empty {{
        background: #4a4a4a;
        border-color: #444;
    }}

    .mfa-text {{
        font-family: 'Consolas', 'Menlo', 'DejaVu Sans Mono', monospace;
        font-size: 14px;
        font-weight: bold;
        text-align: center;
        line-height: 1.15;
        color: #404040;
        transition: color 0.06s ease;
    }}

    .mid-text .mfa-text {{
        font-size: 22px;
    }}

    .big-text .mfa-text {{
        font-size: 34px;
    }}

    .door-text .mfa-text {{
        font-size: 24px;
        letter-spacing: 2px;
    }}

    .mfa-block.on {{
        border-color: transparent;
    }}

    /* Status bar */
    #status-bar {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 10px;
        padding-top: 6px;
        border-top: 1px solid #1a1a1a;
        font-size: 9px;
    }}

    #status-dot {{
        display: inline-block;
        width: 6px; height: 6px;
        border-radius: 50%;
        background: #333;
        margin-right: 5px;
        transition: background 0.3s;
    }}

    #status-dot.connected {{ background: #4a4; }}
    #status-dot.disconnected {{ background: #a44; }}
    #status-text {{ color: #555; }}
    #status-latency {{ color: #444; }}

    /* Blink: applichiamo a .mfa-block */
    @keyframes block-blink {{
        0%, 49% {{ opacity: 1; }}
        50%, 100% {{ opacity: 0; }}
    }}

    .mfa-block.blink {{
        animation: block-blink var(--blink-duration, 1s) step-start infinite;
    }}

    .mfa-block.blink-offset {{
        animation: block-blink var(--blink-duration, 1s) step-start infinite;
        animation-delay: calc(var(--blink-duration, 1s) / 2);
    }}

    /* Landscape tablet */
    @media (max-height: 450px) {{
        body {{ align-items: flex-start; padding-top: 8px; }}
        #panel {{ padding: 8px 10px; }}
        #panel-title {{ font-size: 12px; margin-bottom: 6px; }}
        .mfa-block {{ width: 58px; height: 44px; }}
        .mfa-text {{ font-size: 11px; }}
        .mid-text .mfa-text {{ font-size: 17px; }}
        .big-text .mfa-text {{ font-size: 24px; }}
        .door-text .mfa-text {{ font-size: 18px; }}
        .section-header {{ font-size: 8px; }}
    }}

    /* Large screens */
    @media (min-width: 900px) {{
        .mfa-block {{ width: 84px; height: 64px; }}
        .mfa-text {{ font-size: 16px; }}
        .mid-text .mfa-text {{ font-size: 26px; }}
        .big-text .mfa-text {{ font-size: 40px; }}
        .door-text .mfa-text {{ font-size: 28px; }}
    }}
</style>
</head>
<body>
<div id="panel">
    <div id="panel-title">M  F  A</div>
    <div id="mfa-body">
        {left_html}
        <div class="mfa-separator"></div>
        {right_html}
    </div>
    <div id="status-bar">
        <span><span id="status-dot"></span><span id="status-text">Connecting...</span></span>
        <span id="status-latency"></span>
    </div>
</div>

<script>
const LED_DATA = {led_data_json};

let eventSource = null;
let reconnectTimer = null;

function connect() {{
    if (eventSource) eventSource.close();
    const dot = document.getElementById('status-dot');
    const text = document.getElementById('status-text');
    dot.className = 'disconnected';
    text.textContent = 'Connecting...';

    eventSource = new EventSource('/events');

    eventSource.onopen = function() {{
        dot.className = 'connected';
        text.textContent = 'Connected';
        if (reconnectTimer) {{ clearTimeout(reconnectTimer); reconnectTimer = null; }}
    }};

    eventSource.onmessage = function(event) {{
        const data = JSON.parse(event.data);
        updateBlocks(data.states, data.blinks);
        document.getElementById('status-latency').textContent = new Date().toLocaleTimeString();
    }};

    eventSource.onerror = function() {{
        dot.className = 'disconnected';
        text.textContent = 'Disconnected';
        eventSource.close();
        eventSource = null;
        if (!reconnectTimer) reconnectTimer = setTimeout(connect, 1000);
    }};
}}

function updateBlocks(states, blinks) {{
    const pzb70Blink = states['PZB70'] && (blinks['PZB70'] || 0) > 0;
    const pzb85Blink = states['PZB85'] && (blinks['PZB85'] || 0) > 0;
    const wechsel = pzb70Blink && pzb85Blink;

    for (const [name, info] of Object.entries(LED_DATA)) {{
        const block = document.getElementById('block-' + name);
        if (!block) continue;
        const textEl = block.querySelector('.mfa-text');

        const isOn = states[name] || false;
        const blinkInterval = blinks[name] || 0;
        const isBlink = isOn && blinkInterval > 0;

        block.classList.remove('on', 'blink', 'blink-offset');

        if (isOn) {{
            block.style.background = info.bg_on;
            block.style.borderColor = 'transparent';
            block.style.boxShadow = '0 0 12px ' + info.glow + ', inset 0 0 8px rgba(255,255,255,0.1)';
            block.classList.add('on');
            if (textEl) textEl.style.color = info.fg_on;

            if (isBlink) {{
                block.style.setProperty('--blink-duration', (blinkInterval * 2) + 's');
                block.classList.add(wechsel && name === 'PZB85' ? 'blink-offset' : 'blink');
            }}
        }} else {{
            block.style.background = info.bg_off;
            block.style.borderColor = '#4a4a4a';
            block.style.boxShadow = 'none';
            block.classList.remove('on');
            if (textEl) textEl.style.color = info.fg_off;
        }}
    }}
}}

connect();

// Prevent zoom on double tap (tablet)
document.addEventListener('touchstart', function(e) {{
    if (e.touches.length > 1) e.preventDefault();
}}, {{ passive: false }});

// Keep screen awake
if ('wakeLock' in navigator) {{
    navigator.wakeLock.request('screen').catch(() => {{}});
}}
</script>
</body>
</html>'''


# Pre-build HTML (cached)
_cached_html: Optional[str] = None


def _get_html() -> str:
    global _cached_html
    if _cached_html is None:
        _cached_html = _build_html()
    return _cached_html


# ============================================================
# Web Server (HTTP + SSE)
# ============================================================

class _MFARequestHandler(BaseHTTPRequestHandler):
    """Handler HTTP per il pannello MFA web."""

    def log_message(self, format, *args):
        """Silenzia i log HTTP standard."""
        pass

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self._serve_html()
        elif self.path == "/events":
            self._serve_sse()
        elif self.path == "/api/leds":
            self._serve_json()
        else:
            self.send_error(404)

    def _serve_html(self):
        html = _get_html().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(html)

    def _serve_json(self):
        states, blinks, _ = _led_state_mgr.get()
        data = json.dumps({"states": states, "blinks": blinks}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def _serve_sse(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        last_version = -1
        try:
            while True:
                states, blinks, version = _led_state_mgr.wait_for_change(
                    last_version, timeout=1.0
                )
                if version != last_version:
                    last_version = version
                    payload = json.dumps({"states": states, "blinks": blinks})
                    self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                    self.wfile.flush()
                else:
                    # Heartbeat (mantiene la connessione viva)
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass


class _ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """HTTP Server con threading per gestire più client SSE contemporaneamente."""
    daemon_threads = True
    allow_reuse_address = True


class MFAWebServer:
    """Web server integrato per servire il pannello MFA via browser."""

    def __init__(self, port: int = 8080):
        self.port = port
        self._server: Optional[_ThreadedHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running and self._server is not None

    @property
    def url(self) -> str:
        """URL per accedere al pannello dal browser."""
        ip = get_local_ip()
        return f"http://{ip}:{self.port}"

    def start(self) -> bool:
        """Avvia il web server. Ritorna True se avviato con successo."""
        if self._running:
            return True

        try:
            self._server = _ThreadedHTTPServer(("0.0.0.0", self.port), _MFARequestHandler)
            self._thread = threading.Thread(target=self._run, daemon=True, name="MFAWebServer")
            self._thread.start()
            self._running = True
            logger.info(f"MFA Web Server started on {self.url}")
            return True
        except OSError as e:
            logger.error(f"Cannot start MFA Web Server on port {self.port}: {e}")
            self._server = None
            return False

    def _run(self):
        try:
            self._server.serve_forever()
        except Exception as e:
            logger.error(f"MFA Web Server error: {e}")
        finally:
            self._running = False

    def stop(self):
        """Ferma il web server."""
        if self._server:
            try:
                self._server.shutdown()
            except Exception:
                pass
            self._server = None
        self._running = False
        logger.info("MFA Web Server stopped")


# ============================================================
# Utility
# ============================================================

def get_local_ip() -> str:
    """Trova l'indirizzo IP locale (LAN) di questa macchina."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"
