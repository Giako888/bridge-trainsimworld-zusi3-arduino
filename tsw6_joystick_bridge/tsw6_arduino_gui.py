"""
TSW6 Arduino Bridge - GUI Principale
======================================
Interfaccia grafica per collegare TSW6 ad Arduino Leonardo.

Funzionalità:
- Connessione a TSW6 tramite API HTTP (porta 31270)
- Connessione ad Arduino Leonardo tramite seriale
- Configurazione mappature: dati TSW6 → 12 LED Charlieplexing
- Gestione profili
- Scoperta endpoint TSW6 (con scansione e salvataggio)
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
import json
import logging
import os
from typing import Dict, List, Optional, Any
from dataclasses import asdict

from tsw6_api import TSW6API, TSW6Poller, TSW6APIError, TSW6ConnectionError, TSW6AuthError
from arduino_bridge import (
    ArduinoController, LEDS, LED_BY_NAME, LedInfo,
    find_arduino_port, list_serial_ports
)
from config_models import (
    Profile, LedMapping, LedAction, Condition,
    ConfigManager, COMMON_TSW6_ENDPOINTS, ALL_CONDITIONS,
    create_default_profile, APP_NAME, APP_VERSION
)

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("GUI")


# ============================================================
# Costanti GUI
# ============================================================

WINDOW_WIDTH = 1100
WINDOW_HEIGHT = 700
POLL_GUI_MS = 100   # Refresh GUI LED ogni 100ms per blink fluido
BG_COLOR = "#1e1e2e"
FG_COLOR = "#cdd6f4"
ACCENT_COLOR = "#89b4fa"
SUCCESS_COLOR = "#a6e3a1"
WARNING_COLOR = "#f9e2af"
ERROR_COLOR = "#f38ba8"
CARD_BG = "#313244"
ENTRY_BG = "#45475a"

LED_GUI_COLORS = {
    "giallo": "#f9e2af",
    "blu": "#89b4fa",
    "rosso": "#f38ba8",
}


# ============================================================
# Applicazione principale
# ============================================================

class TSW6ArduineBridgeApp:
    """Applicazione GUI principale"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.minsize(900, 550)

        # Icona finestra
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tsw6_bridge.ico")
        if not os.path.exists(icon_path):
            # Fallback per PyInstaller (sys._MEIPASS)
            import sys
            base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
            icon_path = os.path.join(base, "tsw6_bridge.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

        # Moduli
        self.tsw6_api = TSW6API()
        self.arduino = ArduinoController()
        self.config_mgr = ConfigManager()
        self.poller: Optional[TSW6Poller] = None

        # Stato
        self.current_profile = create_default_profile()
        self.mappings: List[LedMapping] = self.current_profile.get_mappings()
        self.running = False
        self.last_tsw6_data: Dict[str, Any] = {}
        self._gui_led_states: Dict[str, bool] = {}  # Stato LED nella GUI (da dati TSW6)
        self._gui_led_blink: Dict[str, float] = {}  # Intervallo blink per LED (0.0=fisso, >0=lampeggio)

        # Stile
        self._setup_styles()

        # UI
        self._build_ui()

        # Carica ultimo profilo
        self._load_last_config()

        # Chiusura
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # --------------------------------------------------------
    # Stili
    # --------------------------------------------------------

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(".", background=BG_COLOR, foreground=FG_COLOR, font=("Segoe UI", 10))
        style.configure("TFrame", background=BG_COLOR)
        style.configure("Card.TFrame", background=CARD_BG)
        style.configure("TLabel", background=BG_COLOR, foreground=FG_COLOR)
        style.configure("Card.TLabel", background=CARD_BG, foreground=FG_COLOR)
        style.configure("Title.TLabel", font=("Segoe UI", 14, "bold"), foreground=ACCENT_COLOR, background=BG_COLOR)
        style.configure("Status.TLabel", font=("Segoe UI", 9), foreground=FG_COLOR, background=CARD_BG)

        # Entry / Combobox: testo chiaro su sfondo scuro
        style.configure("TEntry",
                        foreground=FG_COLOR,
                        fieldbackground=ENTRY_BG,
                        insertcolor=FG_COLOR,
                        font=("Segoe UI", 10))
        style.configure("TCombobox",
                        foreground=FG_COLOR,
                        fieldbackground=ENTRY_BG,
                        selectbackground=ACCENT_COLOR,
                        selectforeground="#1e1e2e",
                        font=("Segoe UI", 10))
        style.map("TCombobox",
                  fieldbackground=[("readonly", ENTRY_BG)],
                  foreground=[("readonly", FG_COLOR)])

        # Buttons
        style.configure("TButton",
                        font=("Segoe UI", 10),
                        foreground=FG_COLOR,
                        background=ENTRY_BG)
        style.map("TButton",
                  foreground=[("disabled", "#6c7086"), ("active", "#ffffff")],
                  background=[("active", "#585b70")])
        style.configure("Accent.TButton",
                        font=("Segoe UI", 10, "bold"),
                        foreground="#1e1e2e",
                        background=ACCENT_COLOR)
        style.map("Accent.TButton",
                  background=[("active", "#b4d0fb")])

        # Tabs notebook
        style.configure("TNotebook", background=BG_COLOR)
        style.configure("TNotebook.Tab",
                        font=("Segoe UI", 10),
                        padding=[12, 4],
                        foreground=FG_COLOR,
                        background=ENTRY_BG)
        style.map("TNotebook.Tab",
                  foreground=[("selected", ACCENT_COLOR), ("active", "#ffffff")],
                  background=[("selected", CARD_BG), ("active", "#585b70")])

        style.configure("Connected.TLabel", foreground=SUCCESS_COLOR, background=CARD_BG, font=("Segoe UI", 10, "bold"))
        style.configure("Disconnected.TLabel", foreground=ERROR_COLOR, background=CARD_BG, font=("Segoe UI", 10, "bold"))
        style.configure("Warning.TLabel", foreground=WARNING_COLOR, background=CARD_BG, font=("Segoe UI", 10, "bold"))

        style.configure("Green.TLabel", foreground=SUCCESS_COLOR, background=CARD_BG)
        style.configure("Red.TLabel", foreground=ERROR_COLOR, background=CARD_BG)

        # Treeview: sfondo scuro, testo chiaro e leggibile
        style.configure("Treeview",
                        background="#1e1e2e",
                        foreground="#cdd6f4",
                        fieldbackground="#1e1e2e",
                        font=("Segoe UI", 9),
                        rowheight=24)
        style.configure("Treeview.Heading",
                        background="#45475a",
                        foreground="#89b4fa",
                        font=("Segoe UI", 9, "bold"))
        style.map("Treeview",
                  background=[("selected", "#45475a")],
                  foreground=[("selected", "#ffffff")])
        style.map("Treeview.Heading",
                  background=[("active", "#585b70")])

        # LabelFrame: titolo chiaro e leggibile
        style.configure("TLabelframe", background=BG_COLOR)
        style.configure("TLabelframe.Label",
                        background=BG_COLOR,
                        foreground=ACCENT_COLOR,
                        font=("Segoe UI", 9, "bold"))

        self.root.configure(bg=BG_COLOR)

    # --------------------------------------------------------
    # Costruzione UI
    # --------------------------------------------------------

    def _build_ui(self):
        # Header
        header = ttk.Frame(self.root)
        header.pack(fill=tk.X, padx=10, pady=(10, 5))

        ttk.Label(header, text=f"🚂 {APP_NAME}", style="Title.TLabel").pack(side=tk.LEFT)
        ttk.Label(header, text=f"v{APP_VERSION}", style="TLabel").pack(side=tk.LEFT, padx=(10, 0))

        # Notebook (tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Tab 1: Connessione + Bridge
        self.tab_connect = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_connect, text="  Connessione  ")
        self._build_connection_tab()

        # Tab 2: Mappature
        self.tab_mappings = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_mappings, text="  Mappature  ")
        self._build_mappings_tab()

        # Tab 3: Scoperta Endpoint
        self.tab_discover = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_discover, text="  🔍 Scopri Endpoint  ")
        self._build_discover_tab()

        # Footer
        self._build_footer()

    # --------------------------------------------------------
    # Tab Connessione
    # --------------------------------------------------------

    def _build_connection_tab(self):
        container = ttk.Frame(self.tab_connect)
        container.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        # --- TSW6 (compatto) ---
        tsw6_frame = ttk.LabelFrame(container, text="  TSW6 (HTTP API)  ", padding=10)
        tsw6_frame.pack(fill=tk.X, pady=(0, 10))

        row1 = ttk.Frame(tsw6_frame)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="Host:").pack(side=tk.LEFT)
        self.tsw6_host_var = tk.StringVar(value="127.0.0.1")
        ttk.Entry(row1, textvariable=self.tsw6_host_var, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Label(row1, text="Porta:").pack(side=tk.LEFT, padx=(10, 0))
        self.tsw6_port_var = tk.StringVar(value="31270")
        ttk.Entry(row1, textvariable=self.tsw6_port_var, width=7).pack(side=tk.LEFT, padx=5)

        self.btn_tsw6_connect = ttk.Button(row1, text="Connetti", command=self._connect_tsw6, style="Accent.TButton")
        self.btn_tsw6_connect.pack(side=tk.LEFT, padx=(15, 5))
        self.btn_tsw6_disconnect = ttk.Button(row1, text="Disconnetti", command=self._disconnect_tsw6, state=tk.DISABLED)
        self.btn_tsw6_disconnect.pack(side=tk.LEFT, padx=2)
        self.lbl_tsw6_status = ttk.Label(row1, text="● Disconnesso", style="Disconnected.TLabel")
        self.lbl_tsw6_status.pack(side=tk.LEFT, padx=15)

        row2 = ttk.Frame(tsw6_frame)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text="API Key:").pack(side=tk.LEFT)
        self.tsw6_apikey_var = tk.StringVar(value="")
        self.tsw6_apikey_entry = ttk.Entry(row2, textvariable=self.tsw6_apikey_var, width=40, show="*")
        self.tsw6_apikey_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(row2, text="👁", width=3, command=self._toggle_apikey_visibility).pack(side=tk.LEFT)
        ttk.Button(row2, text="🔑 Auto", command=self._auto_detect_apikey).pack(side=tk.LEFT, padx=5)
        self._apikey_visible = False

        # Prova a caricare la chiave automaticamente all'avvio
        self._auto_detect_apikey()

        # --- Arduino ---
        arduino_frame = ttk.LabelFrame(container, text="  Arduino Leonardo (12 LED Charlieplexing)  ", padding=10)
        arduino_frame.pack(fill=tk.X, pady=(0, 10))

        row_a1 = ttk.Frame(arduino_frame)
        row_a1.pack(fill=tk.X, pady=2)
        ttk.Label(row_a1, text="Porta:").pack(side=tk.LEFT)
        self.arduino_port_var = tk.StringVar(value="Auto-detect")
        self.arduino_port_combo = ttk.Combobox(row_a1, textvariable=self.arduino_port_var, width=30, state="readonly")
        self.arduino_port_combo.pack(side=tk.LEFT, padx=5)
        ttk.Button(row_a1, text="🔄", command=self._refresh_serial_ports).pack(side=tk.LEFT, padx=2)

        self.btn_arduino_connect = ttk.Button(row_a1, text="Connetti", command=self._connect_arduino, style="Accent.TButton")
        self.btn_arduino_connect.pack(side=tk.LEFT, padx=(15, 5))
        self.btn_arduino_disconnect = ttk.Button(row_a1, text="Disconnetti", command=self._disconnect_arduino, state=tk.DISABLED)
        self.btn_arduino_disconnect.pack(side=tk.LEFT, padx=2)
        ttk.Button(row_a1, text="🔦 Test", command=self._test_arduino_leds).pack(side=tk.LEFT, padx=5)
        ttk.Button(row_a1, text="💡 Spegni", command=self._all_leds_off).pack(side=tk.LEFT, padx=2)
        self.lbl_arduino_status = ttk.Label(row_a1, text="● Disconnesso", style="Disconnected.TLabel")
        self.lbl_arduino_status.pack(side=tk.LEFT, padx=15)

        # --- Bridge ---
        bridge_frame = ttk.LabelFrame(container, text="  Bridge TSW6 → Arduino  ", padding=10)
        bridge_frame.pack(fill=tk.X, pady=(0, 10))

        row_b = ttk.Frame(bridge_frame)
        row_b.pack(fill=tk.X)
        self.btn_start = ttk.Button(row_b, text="▶ AVVIA BRIDGE", command=self._start_bridge,
                                     style="Accent.TButton", state=tk.DISABLED)
        self.btn_start.pack(side=tk.LEFT)
        self.btn_stop = ttk.Button(row_b, text="⏹ FERMA", command=self._stop_bridge, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=5)
        self.lbl_bridge_status = ttk.Label(row_b, text="In attesa connessioni...", style="Status.TLabel")
        self.lbl_bridge_status.pack(side=tk.LEFT, padx=15)

        # --- Pannello LED live ---
        led_frame = ttk.LabelFrame(container, text="  Stato LED  ", padding=10)
        led_frame.pack(fill=tk.X, pady=(0, 5))

        self.led_indicators = {}
        for i, led in enumerate(LEDS):
            row = i // 6
            col = i % 6

            cell = ttk.Frame(led_frame)
            cell.grid(row=row, column=col, padx=8, pady=5, sticky=tk.W)

            canvas = tk.Canvas(cell, width=18, height=18, bg=CARD_BG, highlightthickness=0)
            canvas.pack(side=tk.LEFT, padx=(0, 5))
            dot = canvas.create_oval(2, 2, 16, 16, fill="#555555", outline="#333333")

            lbl = ttk.Label(cell, text=led.label, font=("Segoe UI", 9))
            lbl.pack(side=tk.LEFT)

            self.led_indicators[led.name] = (canvas, dot, led.color)

        for col in range(6):
            led_frame.grid_columnconfigure(col, weight=1)

        # --- Debug Log (mostra dati ricevuti da TSW6) ---
        debug_frame = ttk.LabelFrame(container, text="  📋 Debug Log (dati TSW6)  ", padding=5)
        debug_frame.pack(fill=tk.BOTH, expand=True)

        self.debug_text = tk.Text(debug_frame, height=6, bg="#181825", fg="#a6adc8",
                                   font=("Consolas", 9), wrap=tk.WORD, state=tk.DISABLED,
                                   relief=tk.FLAT)
        debug_scroll = ttk.Scrollbar(debug_frame, orient=tk.VERTICAL, command=self.debug_text.yview)
        self.debug_text.configure(yscrollcommand=debug_scroll.set)
        debug_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.debug_text.pack(fill=tk.BOTH, expand=True)

        # Popola porte
        self._refresh_serial_ports()

    def _refresh_serial_ports(self):
        ports = list_serial_ports()
        auto_port = find_arduino_port()

        values = ["Auto-detect"]
        for p in ports:
            values.append(f"{p['port']} - {p['description']}")

        self.arduino_port_combo["values"] = values
        if not self.arduino_port_var.get() or self.arduino_port_var.get() not in values:
            self.arduino_port_combo.current(0)

        if auto_port:
            self.lbl_arduino_status.config(text=f"🔍 Trovato: {auto_port}", style="Warning.TLabel")

    # --------------------------------------------------------
    # Tab Mappature
    # --------------------------------------------------------

    def _build_mappings_tab(self):
        container = ttk.Frame(self.tab_mappings)
        container.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        # Toolbar
        toolbar = ttk.Frame(container)
        toolbar.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(toolbar, text="+ Aggiungi", command=self._add_mapping).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Rimuovi", command=self._remove_mapping).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="Predefinite", command=self._load_default_mappings).pack(side=tk.LEFT, padx=5)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, padx=10, fill=tk.Y)

        ttk.Button(toolbar, text="💾 Salva Profilo", command=self._save_profile).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="📂 Carica Profilo", command=self._load_profile).pack(side=tk.LEFT, padx=5)

        ttk.Label(toolbar, text="Profilo:").pack(side=tk.LEFT, padx=(15, 5))
        self.profile_name_var = tk.StringVar(value=self.current_profile.name)
        ttk.Entry(toolbar, textvariable=self.profile_name_var, width=25).pack(side=tk.LEFT)

        # Tabella mappature
        columns = ("name", "endpoint", "condition", "action", "led", "enabled")
        self.mapping_tree = ttk.Treeview(container, columns=columns, show="headings", height=15)

        self.mapping_tree.heading("name", text="Nome")
        self.mapping_tree.heading("endpoint", text="Endpoint TSW6")
        self.mapping_tree.heading("condition", text="Condizione")
        self.mapping_tree.heading("action", text="Azione")
        self.mapping_tree.heading("led", text="LED")
        self.mapping_tree.heading("enabled", text="Attivo")

        self.mapping_tree.column("name", width=150)
        self.mapping_tree.column("endpoint", width=300)
        self.mapping_tree.column("condition", width=140)
        self.mapping_tree.column("action", width=100)
        self.mapping_tree.column("led", width=130, anchor=tk.CENTER)
        self.mapping_tree.column("enabled", width=60, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL, command=self.mapping_tree.yview)
        self.mapping_tree.configure(yscrollcommand=scrollbar.set)

        self.mapping_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.mapping_tree.bind("<Double-1>", self._edit_mapping)
        self._refresh_mapping_list()

    def _refresh_mapping_list(self):
        for item in self.mapping_tree.get_children():
            self.mapping_tree.delete(item)

        for i, m in enumerate(self.mappings):
            if m.condition == Condition.BETWEEN:
                cond_str = f"{m.threshold_min} ↔ {m.threshold_max}"
            elif m.condition in (Condition.TRUE, Condition.FALSE):
                cond_str = m.condition
            else:
                cond_str = f"{m.condition} {m.threshold}"

            action_names = {
                LedAction.ON: "Accendi",
                LedAction.OFF: "Spegni",
                LedAction.BLINK: f"Blink {m.blink_interval_sec}s",
            }

            led_info = LED_BY_NAME.get(m.led_name)
            led_label = led_info.label if led_info else m.led_name

            ep = m.tsw6_endpoint
            # Abbrevia percorsi lunghi
            for prefix in ["CurrentFormation/0/MFA_Indicators.Property.", "CurrentFormation/0.", "CurrentDrivableActor."]:
                if ep.startswith(prefix):
                    ep = "..." + ep[len(prefix):]
                    break

            self.mapping_tree.insert("", tk.END, iid=str(i), values=(
                m.name, ep, cond_str,
                action_names.get(m.action, m.action),
                led_label,
                "✅" if m.enabled else "❌",
            ))

    def _add_mapping(self):
        dialog = MappingDialog(self.root, "Nuova Mappatura")
        self.root.wait_window(dialog.window)
        if dialog.result:
            self.mappings.append(dialog.result)
            self._refresh_mapping_list()

    def _edit_mapping(self, event=None):
        selection = self.mapping_tree.selection()
        if not selection:
            return
        idx = int(selection[0])
        dialog = MappingDialog(self.root, "Modifica Mappatura", self.mappings[idx])
        self.root.wait_window(dialog.window)
        if dialog.result:
            self.mappings[idx] = dialog.result
            self._refresh_mapping_list()

    def _remove_mapping(self):
        selection = self.mapping_tree.selection()
        if not selection:
            messagebox.showwarning("Attenzione", "Seleziona una mappatura da rimuovere")
            return
        idx = int(selection[0])
        name = self.mappings[idx].name
        if messagebox.askyesno("Conferma", f"Rimuovere '{name}'?"):
            del self.mappings[idx]
            self._refresh_mapping_list()

    def _load_default_mappings(self):
        if messagebox.askyesno("Conferma", "Caricare le mappature predefinite?\nLe attuali saranno sostituite."):
            default = create_default_profile()
            self.mappings = default.get_mappings()
            self._refresh_mapping_list()

    # --------------------------------------------------------
    # Tab Scoperta Endpoint
    # --------------------------------------------------------

    def _build_discover_tab(self):
        container = ttk.Frame(self.tab_discover)
        container.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        info_lbl = ttk.Label(container,
            text="Connettiti a TSW6, guida un treno e clicca 'Scansiona' per scoprire gli endpoint.\n"
                 "Usa i filtri rapidi per trovare PZB, SIFA, LZB, ecc. Doppio click per creare una mappatura.",
            wraplength=900, font=("Segoe UI", 9, "italic"),
            foreground=FG_COLOR)
        info_lbl.pack(anchor=tk.W, pady=(0, 8))

        # Toolbar
        toolbar = ttk.Frame(container)
        toolbar.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(toolbar, text="Radice:").pack(side=tk.LEFT)
        self.discover_root_var = tk.StringVar(value="CurrentFormation")
        root_combo = ttk.Combobox(toolbar, textvariable=self.discover_root_var, width=25,
            values=["CurrentFormation", "CurrentDrivableActor", "VirtualRailDriver",
                    "WeatherManager", "TimeOfDay", "DriverAid", ""])
        root_combo.pack(side=tk.LEFT, padx=5)

        ttk.Label(toolbar, text="Prof:").pack(side=tk.LEFT, padx=(5, 0))
        self.discover_depth_var = tk.StringVar(value="4")
        ttk.Spinbox(toolbar, textvariable=self.discover_depth_var, from_=1, to=8, width=3).pack(side=tk.LEFT, padx=3)

        self.btn_discover = ttk.Button(toolbar, text="🔍 Scansiona", command=self._run_discovery,
                                        style="Accent.TButton")
        self.btn_discover.pack(side=tk.LEFT, padx=5)

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)

        ttk.Button(toolbar, text="💾 JSON", command=self._export_endpoints_json).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="📄 TXT", command=self._export_endpoints_txt).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="📊 +Valori", command=self._export_endpoints_with_values).pack(side=tk.LEFT, padx=2)

        self.discover_progress_var = tk.StringVar(value="")
        ttk.Label(toolbar, textvariable=self.discover_progress_var, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=10)

        # Filtro
        filter_frame = ttk.Frame(container)
        filter_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(filter_frame, text="Filtra:").pack(side=tk.LEFT)
        self.discover_filter_var = tk.StringVar()
        filter_entry = ttk.Entry(filter_frame, textvariable=self.discover_filter_var, width=40)
        filter_entry.pack(side=tk.LEFT, padx=5)
        filter_entry.bind("<Return>", lambda e: self._filter_discovered())
        ttk.Button(filter_frame, text="Cerca", command=self._filter_discovered).pack(side=tk.LEFT, padx=2)
        ttk.Button(filter_frame, text="Tutti", command=self._show_all_discovered).pack(side=tk.LEFT, padx=2)

        self.discover_count_var = tk.StringVar(value="")
        ttk.Label(filter_frame, textvariable=self.discover_count_var, font=("Segoe UI", 9, "bold")).pack(side=tk.RIGHT)

        # Filtri rapidi
        quick_frame = ttk.Frame(container)
        quick_frame.pack(fill=tk.X, pady=(0, 8))
        for kw in ["PZB", "SIFA", "LZB", "MFA", "Safety", "Brake", "Speed", "Door", "Signal", "Horn", "Light", "Indicator"]:
            ttk.Button(quick_frame, text=kw,
                       command=lambda k=kw: self._quick_filter(k)).pack(side=tk.LEFT, padx=2)

        # Tabella
        columns = ("path", "name", "node", "writable")
        self.discover_tree = ttk.Treeview(container, columns=columns, show="headings", height=16)

        self.discover_tree.heading("path", text="Percorso Completo")
        self.discover_tree.heading("name", text="Nome")
        self.discover_tree.heading("node", text="Nodo Padre")
        self.discover_tree.heading("writable", text="W")

        self.discover_tree.column("path", width=500)
        self.discover_tree.column("name", width=200)
        self.discover_tree.column("node", width=200)
        self.discover_tree.column("writable", width=40, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(container, orient=tk.VERTICAL, command=self.discover_tree.yview)
        self.discover_tree.configure(yscrollcommand=scrollbar.set)

        self.discover_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.discover_tree.bind("<Double-1>", self._use_discovered_endpoint)
        self._discovered_endpoints = []

    def _run_discovery(self):
        if not self.tsw6_api.is_connected():
            messagebox.showwarning("Attenzione", "Connettiti a TSW6 prima di scansionare.")
            return

        root = self.discover_root_var.get().strip()
        depth = int(self.discover_depth_var.get())

        self.btn_discover.config(state=tk.DISABLED)
        self.discover_progress_var.set("Scansione in corso...")
        self.root.update()

        def do_discover():
            def progress(path):
                self.root.after(0, lambda p=path: self.discover_progress_var.set(f"Scansione: {p}"))
            try:
                endpoints = self.tsw6_api.discover_endpoints(root, max_depth=depth,
                                                              progress_callback=progress)
                self.root.after(0, lambda: self._on_discovery_done(endpoints))
            except Exception as e:
                self.root.after(0, lambda: self._on_discovery_error(str(e)))

        threading.Thread(target=do_discover, daemon=True).start()

    def _on_discovery_done(self, endpoints):
        self._discovered_endpoints = endpoints
        self._populate_discover_tree(endpoints)
        self.btn_discover.config(state=tk.NORMAL)
        self.discover_progress_var.set(f"Trovati {len(endpoints)} endpoint")

    def _on_discovery_error(self, msg):
        self.btn_discover.config(state=tk.NORMAL)
        self.discover_progress_var.set("Errore")
        messagebox.showerror("Errore Scansione", msg)

    def _populate_discover_tree(self, endpoints):
        for item in self.discover_tree.get_children():
            self.discover_tree.delete(item)
        for i, ep in enumerate(endpoints):
            self.discover_tree.insert("", tk.END, iid=str(i), values=(
                ep["path"], ep["name"], ep.get("node", ""),
                "✅" if ep.get("writable") else "",
            ))
        self.discover_count_var.set(f"{len(endpoints)} risultati")

    def _filter_discovered(self):
        query = self.discover_filter_var.get().strip().lower()
        if not query:
            self._show_all_discovered()
            return
        keywords = query.split()
        filtered = [ep for ep in self._discovered_endpoints
                     if all(kw in f"{ep['path']} {ep['name']} {ep.get('node', '')}".lower()
                            for kw in keywords)]
        self._populate_discover_tree(filtered)

    def _show_all_discovered(self):
        self.discover_filter_var.set("")
        self._populate_discover_tree(self._discovered_endpoints)

    def _quick_filter(self, keyword):
        self.discover_filter_var.set(keyword)
        self._filter_discovered()

    def _use_discovered_endpoint(self, event=None):
        selection = self.discover_tree.selection()
        if not selection:
            return
        ep_path = self.discover_tree.item(selection[0], "values")[0]

        self.root.clipboard_clear()
        self.root.clipboard_append(ep_path)

        if messagebox.askyesno("Endpoint",
                                f"{ep_path}\n\nCopiato negli appunti.\nCreare una nuova mappatura?"):
            m = LedMapping(name=ep_path.split('.')[-1], tsw6_endpoint=ep_path)
            dialog = MappingDialog(self.root, "Nuova Mappatura", m)
            self.root.wait_window(dialog.window)
            if dialog.result:
                self.mappings.append(dialog.result)
                self._refresh_mapping_list()
                self.notebook.select(self.tab_mappings)

    # --------------------------------------------------------
    # Export endpoint
    # --------------------------------------------------------

    def _get_export_endpoints(self):
        visible = []
        for item in self.discover_tree.get_children():
            vals = self.discover_tree.item(item, "values")
            visible.append({
                "path": vals[0], "name": vals[1],
                "node": vals[2], "writable": vals[3] == "✅",
            })
        return visible

    def _export_endpoints_json(self):
        endpoints = self._get_export_endpoints()
        if not endpoints:
            messagebox.showwarning("Nessun Dato", "Esegui prima una scansione.")
            return

        filepath = filedialog.asksaveasfilename(
            title="Salva endpoint JSON", defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("Tutti", "*.*")],
            initialfile="tsw6_endpoints.json",
        )
        if not filepath:
            return

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump({
                    "source": "TSW6 Arduino Bridge - Endpoint Discovery",
                    "root_node": self.discover_root_var.get(),
                    "filter": self.discover_filter_var.get() or None,
                    "total_count": len(endpoints),
                    "endpoints": endpoints,
                }, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("Salvato", f"{len(endpoints)} endpoint salvati in:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore salvataggio: {e}")

    def _export_endpoints_txt(self):
        endpoints = self._get_export_endpoints()
        if not endpoints:
            messagebox.showwarning("Nessun Dato", "Esegui prima una scansione.")
            return

        filepath = filedialog.asksaveasfilename(
            title="Salva endpoint TXT", defaultextension=".txt",
            filetypes=[("Testo", "*.txt"), ("Tutti", "*.*")],
            initialfile="tsw6_endpoints.txt",
        )
        if not filepath:
            return

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"TSW6 Endpoint Discovery\n{'='*40}\n")
                f.write(f"Radice: {self.discover_root_var.get()}\n")
                filtro = self.discover_filter_var.get()
                if filtro:
                    f.write(f"Filtro: {filtro}\n")
                f.write(f"Totale: {len(endpoints)}\n\n")

                by_node = {}
                for ep in endpoints:
                    by_node.setdefault(ep.get("node", "(root)"), []).append(ep)
                for node, eps in sorted(by_node.items()):
                    f.write(f"\n--- {node} ---\n")
                    for ep in eps:
                        w = " [W]" if ep.get("writable") else ""
                        f.write(f"  {ep['path']}{w}\n")

            messagebox.showinfo("Salvato", f"{len(endpoints)} endpoint salvati in:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Errore", f"Errore salvataggio: {e}")

    def _export_endpoints_with_values(self):
        endpoints = self._get_export_endpoints()
        if not endpoints:
            messagebox.showwarning("Nessun Dato", "Esegui prima una scansione.")
            return
        if not self.tsw6_api.is_connected():
            messagebox.showwarning("Attenzione", "Connettiti a TSW6 per leggere i valori.")
            return
        if len(endpoints) > 200:
            if not messagebox.askyesno("Attenzione",
                    f"{len(endpoints)} endpoint.\nPotrebbe richiedere tempo. Continuare?"):
                return

        filepath = filedialog.asksaveasfilename(
            title="Salva con valori", defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("Testo", "*.txt"), ("Tutti", "*.*")],
            initialfile="tsw6_endpoints_valori.json",
        )
        if not filepath:
            return

        self.discover_progress_var.set("Lettura valori...")
        self.root.update()

        def do_read():
            results = []
            total = len(endpoints)
            for i, ep in enumerate(endpoints):
                entry = dict(ep)
                try:
                    entry["value"] = self.tsw6_api.get_raw(ep["path"])
                    entry["error"] = None
                except Exception as ex:
                    entry["value"] = None
                    entry["error"] = str(ex)
                results.append(entry)
                if (i + 1) % 10 == 0 or i == total - 1:
                    self.root.after(0, lambda n=i+1: self.discover_progress_var.set(f"Valori: {n}/{total}"))
            self.root.after(0, lambda: self._save_with_values(filepath, results))

        threading.Thread(target=do_read, daemon=True).start()

    def _save_with_values(self, filepath, results):
        is_json = filepath.lower().endswith(".json")
        try:
            if is_json:
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump({
                        "source": "TSW6 Arduino Bridge - Endpoint + Values",
                        "root_node": self.discover_root_var.get(),
                        "total_count": len(results),
                        "endpoints": results,
                    }, f, indent=2, ensure_ascii=False)
            else:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(f"TSW6 Endpoint + Valori\n{'='*40}\n")
                    f.write(f"Totale: {len(results)}\n\n")
                    by_node = {}
                    for ep in results:
                        by_node.setdefault(ep.get("node", "(root)"), []).append(ep)
                    for node, eps in sorted(by_node.items()):
                        f.write(f"\n--- {node} ---\n")
                        for ep in eps:
                            w = " [W]" if ep.get("writable") else ""
                            val = ep.get("value", "?")
                            err = ep.get("error")
                            f.write(f"  {ep['path']}{w} = {f'ERRORE: {err}' if err else val}\n")

            self.discover_progress_var.set(f"Salvato ({len(results)} valori)")
            messagebox.showinfo("Salvato", f"{len(results)} endpoint con valori in:\n{filepath}")
        except Exception as e:
            self.discover_progress_var.set("Errore")
            messagebox.showerror("Errore", f"{e}")

    # --------------------------------------------------------
    # Footer
    # --------------------------------------------------------

    def _build_footer(self):
        footer = ttk.Frame(self.root)
        footer.pack(fill=tk.X, padx=10, pady=(0, 8))
        self.lbl_footer_status = ttk.Label(footer, text="Pronto", font=("Segoe UI", 9))
        self.lbl_footer_status.pack(side=tk.LEFT)

    # --------------------------------------------------------
    # Connessione TSW6
    # --------------------------------------------------------

    def _toggle_apikey_visibility(self):
        self._apikey_visible = not self._apikey_visible
        self.tsw6_apikey_entry.config(show="" if self._apikey_visible else "*")

    def _auto_detect_apikey(self):
        from tsw6_api import _find_comm_api_key
        key = _find_comm_api_key()
        if key:
            self.tsw6_apikey_var.set(key)
            self._log(f"API Key trovata ({len(key)} caratteri)")
        else:
            self._log("API Key non trovata - inseriscila manualmente")

    def _connect_tsw6(self):
        host = self.tsw6_host_var.get().strip()
        port = int(self.tsw6_port_var.get().strip())
        api_key = self.tsw6_apikey_var.get().strip() or None

        if not api_key:
            messagebox.showwarning("API Key",
                "API Key vuota.\n\n"
                "Inseriscila manualmente oppure clicca '🔑 Auto' per cercarla.\n"
                "Il file si trova in:\n"
                "Documents\\My Games\\TrainSimWorld6\\Saved\\Config\\CommAPIKey.txt")
            return

        self.tsw6_api = TSW6API(host=host, port=port, api_key=api_key)
        self.lbl_tsw6_status.config(text="⏳ Connessione...", style="Warning.TLabel")
        self.root.update()

        def do_connect():
            try:
                success = self.tsw6_api.connect(api_key=api_key)
                self.root.after(0, lambda: self._on_tsw6_connected(success))
            except TSW6AuthError as e:
                self.root.after(0, lambda: self._on_tsw6_error(f"Chiave API: {e}"))
            except TSW6ConnectionError as e:
                self.root.after(0, lambda: self._on_tsw6_error(f"Connessione: {e}"))
            except Exception as e:
                self.root.after(0, lambda: self._on_tsw6_error(str(e)))

        threading.Thread(target=do_connect, daemon=True).start()

    def _on_tsw6_connected(self, success):
        if success:
            self.lbl_tsw6_status.config(text="● Connesso", style="Connected.TLabel")
            self.btn_tsw6_connect.config(state=tk.DISABLED)
            self.btn_tsw6_disconnect.config(state=tk.NORMAL)
            self._update_bridge_button()
            self._log("Connesso a TSW6")
        else:
            self.lbl_tsw6_status.config(text="● Fallito", style="Disconnected.TLabel")

    def _on_tsw6_error(self, msg):
        self.lbl_tsw6_status.config(text="● Errore", style="Disconnected.TLabel")
        messagebox.showerror("Errore TSW6", msg)

    def _disconnect_tsw6(self):
        self._stop_bridge()
        self.tsw6_api.disconnect()
        self.lbl_tsw6_status.config(text="● Disconnesso", style="Disconnected.TLabel")
        self.btn_tsw6_connect.config(state=tk.NORMAL)
        self.btn_tsw6_disconnect.config(state=tk.DISABLED)
        self._update_bridge_button()
        self._log("Disconnesso da TSW6")

    # --------------------------------------------------------
    # Connessione Arduino
    # --------------------------------------------------------

    def _connect_arduino(self):
        port_selection = self.arduino_port_var.get()
        port = None if port_selection == "Auto-detect" else port_selection.split(" - ")[0].strip()

        self.lbl_arduino_status.config(text="⏳ Connessione...", style="Warning.TLabel")
        self.root.update()

        def do_connect():
            try:
                success = self.arduino.connect(port)
                self.root.after(0, lambda: self._on_arduino_connected(success))
            except Exception as e:
                self.root.after(0, lambda: self._on_arduino_error(str(e)))

        threading.Thread(target=do_connect, daemon=True).start()

    def _on_arduino_connected(self, success):
        if success:
            self.lbl_arduino_status.config(text=f"● {self.arduino.port_name}", style="Connected.TLabel")
            self.btn_arduino_connect.config(state=tk.DISABLED)
            self.btn_arduino_disconnect.config(state=tk.NORMAL)
            self._update_bridge_button()
            self._log(f"Arduino su {self.arduino.port_name}")
        else:
            self.lbl_arduino_status.config(text="● Fallito", style="Disconnected.TLabel")

    def _on_arduino_error(self, msg):
        self.lbl_arduino_status.config(text="● Errore", style="Disconnected.TLabel")
        messagebox.showerror("Errore Arduino", msg)

    def _disconnect_arduino(self):
        self._stop_bridge()
        self.arduino.disconnect()
        self.lbl_arduino_status.config(text="● Disconnesso", style="Disconnected.TLabel")
        self.btn_arduino_connect.config(state=tk.NORMAL)
        self.btn_arduino_disconnect.config(state=tk.DISABLED)
        self._update_bridge_button()
        self._log("Arduino disconnesso")

    def _test_arduino_leds(self):
        if not self.arduino.is_connected():
            messagebox.showwarning("Attenzione", "Arduino non connesso")
            return

        def do_test():
            for led in LEDS:
                if not self.arduino.is_connected():
                    break
                self.arduino.set_led(led.name, True)
                time.sleep(0.15)
            time.sleep(0.5)
            for led in reversed(LEDS):
                if not self.arduino.is_connected():
                    break
                self.arduino.set_led(led.name, False)
                time.sleep(0.15)
            self.root.after(0, lambda: self._log("Test LED completato"))

        threading.Thread(target=do_test, daemon=True).start()
        self._log("Test LED...")

    def _all_leds_off(self):
        if self.arduino.is_connected():
            self.arduino.all_off()
            self._log("LED spenti")

    def _update_bridge_button(self):
        if self.tsw6_api.is_connected():
            self.btn_start.config(state=tk.NORMAL)
            if self.arduino.is_connected():
                self.lbl_bridge_status.config(text="Pronto (TSW6 + Arduino)", style="Warning.TLabel")
            else:
                self.lbl_bridge_status.config(text="Pronto (solo TSW6 - LED solo in GUI)", style="Warning.TLabel")
        else:
            self.btn_start.config(state=tk.DISABLED)
            self.lbl_bridge_status.config(text="Attesa: connessione TSW6", style="Status.TLabel")

    # --------------------------------------------------------
    # Bridge
    # --------------------------------------------------------

    def _start_bridge(self):
        if self.running:
            return
        if not self.tsw6_api.is_connected():
            messagebox.showwarning("Attenzione", "Connettiti a TSW6 prima di avviare il bridge.")
            return

        endpoints = [m.tsw6_endpoint for m in self.mappings
                     if m.enabled and m.tsw6_endpoint]
        endpoints = list(dict.fromkeys(endpoints))  # deduplica mantenendo ordine

        if not endpoints:
            messagebox.showwarning("Attenzione", "Nessuna mappatura attiva.")
            return

        self.lbl_bridge_status.config(text="⏳ Avvio...", style="Warning.TLabel")
        self.btn_start.config(state=tk.DISABLED)
        self.root.update()
        
        # Log endpoint nel debug panel
        self._debug_log(f"Avvio bridge con {len(endpoints)} endpoint:")
        for ep in endpoints:
            self._debug_log(f"  → {ep}")

        poll_interval = max(self.current_profile.poll_interval_ms / 1000.0, 0.1)
        self.poller = TSW6Poller(self.tsw6_api, interval=poll_interval)

        # IMPORTANTE: il callback del poller gira nel thread di polling.
        # Tutte le modifiche a GUI e stato condiviso devono essere
        # dispatched al main thread Tkinter tramite root.after().
        def on_tsw6_data_threadsafe(data):
            self.root.after(0, lambda d=data: self._on_tsw6_data(d))
        self.poller.add_callback(on_tsw6_data_threadsafe)

        def on_poller_msg(msg):
            self.root.after(0, lambda m=msg: self._on_bridge_message(m))
        
        def on_poller_data(msg):
            self.root.after(0, lambda m=msg: self._debug_log(m))

        self.poller.set_error_callback(on_poller_msg)
        self.poller.set_data_callback(on_poller_data)

        def do_start():
            self.poller.start(endpoints)
            if self.poller._running:
                self.root.after(0, lambda: self._on_bridge_started(endpoints))
            else:
                self.root.after(0, self._on_bridge_start_failed)

        threading.Thread(target=do_start, daemon=True).start()

    def _on_bridge_started(self, endpoints):
        self.running = True
        self.btn_stop.config(state=tk.NORMAL)
        self.lbl_bridge_status.config(text="● ATTIVO", style="Connected.TLabel")
        self._log(f"Bridge avviato ({len(endpoints)} endpoint)")
        self._debug_log(f"✅ Bridge attivo - polling ogni {self.poller.interval:.1f}s")
        self._update_led_indicators()

    def _on_bridge_start_failed(self):
        self.btn_start.config(state=tk.NORMAL)
        self.lbl_bridge_status.config(text="● Avvio fallito", style="Disconnected.TLabel")
        self._debug_log("❌ Avvio bridge fallito")
        messagebox.showerror("Errore Bridge",
            "Impossibile avviare il bridge.\n\n"
            "Verifica che:\n"
            "• TSW6 sia in esecuzione con -HTTPAPI\n"
            "• Stai guidando un treno\n"
            "• Gli endpoint delle mappature siano corretti")

    def _on_bridge_message(self, msg):
        self._log(msg)
        self._debug_log(msg)
        # Se il bridge si è fermato da solo, aggiorna UI
        if self.poller and not self.poller._running and self.running:
            self.running = False
            self.btn_start.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)
            self.lbl_bridge_status.config(text="● Disconnesso", style="Disconnected.TLabel")

    def _stop_bridge(self):
        if not self.running:
            return
        self.running = False

        if self.poller:
            self.poller.stop()
            self.poller = None

        try:
            if self.arduino.is_connected():
                self.arduino.stop_all_blinks()
                self.arduino.all_off()
        except Exception:
            pass

        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.lbl_bridge_status.config(text="Fermato", style="Status.TLabel")
        self._log("Bridge fermato")
        self._debug_log("Bridge fermato")

        # Reset contatori diagnostici per prossimo avvio
        self._on_tsw6_data_count = 0
        self._led_update_count = 0
        self._gui_led_states.clear()
        self._gui_led_blink.clear()

    def _on_tsw6_data(self, data: Dict[str, Any]):
        """
        Callback: dati ricevuti da TSW6. Matcha con mappature e aggiorna LED.
        
        Gira nel MAIN THREAD Tkinter (dispatched via root.after).
        
        Logica OR con priorità BLINK > ON > OFF:
        - Più mappature possono puntare allo stesso LED (es. IsActive + IsFlashing)
        - Se QUALSIASI mappatura valuta True → LED ON
        - Se una mappatura BLINK valuta True → LED BLINK (ha priorità su ON fisso)
        """
        self.last_tsw6_data = data
        
        if not data:
            return

        self._on_tsw6_data_count = getattr(self, '_on_tsw6_data_count', 0) + 1

        matched_count = 0
        debug_matches = []

        # Accumula stati LED: {led_name: "blink" | "on" | "off"}
        # Priorità: blink > on > off
        led_accumulator: Dict[str, str] = {}
        
        for mapping in self.mappings:
            if not mapping.enabled or not mapping.tsw6_endpoint:
                continue

            # 1) Match diretto
            value = data.get(mapping.tsw6_endpoint)
            
            # 2) Fallback flessibile
            if value is None:
                ep_lower = mapping.tsw6_endpoint.lower()
                ep_tail = ep_lower.rsplit('.', 1)[-1]
                
                for key, val in data.items():
                    key_lower = key.lower()
                    
                    if key_lower == ep_lower:
                        value = val
                        break
                    
                    key_tail = key_lower.rsplit('.', 1)[-1]
                    if ep_tail == key_tail and ep_tail:
                        value = val
                        break
                    
                    if ep_lower in key_lower or key_lower in ep_lower:
                        value = val
                        break
            
            if value is None:
                continue

            matched_count += 1
            try:
                led_on = self._evaluate_mapping(mapping, value)
                led_name = mapping.led_name
                current = led_accumulator.get(led_name, "off")
                
                if led_on:
                    if mapping.action == LedAction.BLINK:
                        # BLINK ha sempre priorità
                        led_accumulator[led_name] = "blink"
                    elif current != "blink":
                        # ON solo se non c'è già un BLINK
                        led_accumulator[led_name] = "on"
                elif led_name not in led_accumulator:
                    led_accumulator[led_name] = "off"

                debug_matches.append(f"{led_name}={led_accumulator.get(led_name, 'off').upper()}")
            except Exception as e:
                logger.error(f"Errore mappatura '{mapping.name}': {e}")
                debug_matches.append(f"{mapping.led_name}=ERR:{e}")

        # Applica gli stati accumulati alla GUI e ad Arduino
        for led_name, state in led_accumulator.items():
            is_on = state in ("on", "blink")
            is_blink = state == "blink"
            self._gui_led_states[led_name] = is_on
            if is_blink:
                # Salva l'intervallo blink dalla prima mappatura BLINK per questo LED
                interval = 1.0
                for m in self.mappings:
                    if m.enabled and m.led_name == led_name and m.action == LedAction.BLINK:
                        interval = m.blink_interval_sec
                        break
                self._gui_led_blink[led_name] = interval
            else:
                self._gui_led_blink[led_name] = 0.0
            self._send_led_to_arduino(led_name, is_on, is_blink)



    def _evaluate_mapping(self, mapping: LedMapping, value: Any) -> bool:
        """Valuta una mappatura e ritorna True se il LED dovrebbe essere ON."""
        condition_met = mapping.evaluate(value)
        if mapping.action == LedAction.OFF:
            return not condition_met
        return condition_met

    def _send_led_to_arduino(self, led_name: str, led_on: bool, is_blink: bool = False):
        """Invia stato LED ad Arduino (se connesso). Usa is_blink per decidere se lampeggiare."""
        if not self.arduino.is_connected():
            return
        try:
            if is_blink and led_on:
                # Cerca intervallo dalla prima mappatura BLINK trovata per questo LED
                interval = 1.0  # default
                for m in self.mappings:
                    if m.enabled and m.led_name == led_name and m.action == LedAction.BLINK:
                        interval = m.blink_interval_sec
                        break
                self.arduino.set_blink(led_name, interval)
            else:
                self.arduino.set_blink(led_name, 0)
                self.arduino.set_led(led_name, led_on)
        except Exception as e:
            logger.error(f"Errore invio Arduino '{led_name}': {e}")

    def _update_led_indicators(self):
        """Aggiorna indicatori LED nella UI (con supporto blink visivo basato su tempo)"""
        if not self.running:
            return

        now = time.monotonic()

        # Quando PZB70 e PZB85 lampeggiano entrambi, sfasa PZB85 di mezzo periodo
        pzb70_blink = (self._gui_led_states.get("PZB70", False)
                       and self._gui_led_blink.get("PZB70", 0.0) > 0)
        pzb85_blink = (self._gui_led_states.get("PZB85", False)
                       and self._gui_led_blink.get("PZB85", 0.0) > 0)
        both_pzb_blink = pzb70_blink and pzb85_blink

        # Aggiorna cerchietti usando _gui_led_blink (intervallo in secondi)
        for name, (canvas, dot, color) in self.led_indicators.items():
            is_on = self._gui_led_states.get(name, False)
            blink_interval = self._gui_led_blink.get(name, 0.0)

            if is_on and blink_interval > 0:
                # Blink basato su tempo reale: on per interval, off per interval
                phase = int(now / blink_interval) % 2
                # Se entrambi PZB70/85 lampeggiano, PZB85 usa fase opposta (alternati)
                if both_pzb_blink and name == "PZB85":
                    phase = 1 - phase
                show_on = phase == 0
            else:
                show_on = is_on

            fill = LED_GUI_COLORS.get(color, "#ffffff") if show_on else "#555555"
            canvas.itemconfig(dot, fill=fill)

        self.root.after(POLL_GUI_MS, self._update_led_indicators)

    # --------------------------------------------------------
    # Profili
    # --------------------------------------------------------

    def _save_profile(self):
        self.current_profile.name = self.profile_name_var.get().strip() or "Senza Nome"
        self.current_profile.set_mappings(self.mappings)
        self.current_profile.tsw6_host = self.tsw6_host_var.get().strip()
        self.current_profile.tsw6_port = int(self.tsw6_port_var.get().strip())

        self.config_mgr.save_profile(self.current_profile)
        self._log(f"Profilo salvato: {self.current_profile.name}")
        messagebox.showinfo("Salvataggio", f"Profilo '{self.current_profile.name}' salvato.")

    def _load_profile(self):
        profiles = self.config_mgr.list_profiles()

        if not profiles:
            filepath = filedialog.askopenfilename(
                title="Carica Profilo",
                filetypes=[("JSON", "*.json"), ("Tutti", "*.*")],
            )
            if not filepath:
                return
        else:
            dialog = ProfileListDialog(self.root, profiles)
            self.root.wait_window(dialog.window)
            filepath = dialog.selected_path
            if not filepath:
                return

        try:
            self.current_profile = self.config_mgr.load_profile(filepath)
            self.mappings = self.current_profile.get_mappings()
            self.profile_name_var.set(self.current_profile.name)
            self.tsw6_host_var.set(self.current_profile.tsw6_host)
            self.tsw6_port_var.set(str(self.current_profile.tsw6_port))
            self._refresh_mapping_list()
            self._log(f"Profilo: {self.current_profile.name}")
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile caricare: {e}")

    def _load_last_config(self):
        # Conta le mappature predefinite correnti come riferimento
        default_profile = create_default_profile()
        default_count = len(default_profile.get_mappings())

        config = self.config_mgr.load_app_config()
        if config.get("last_profile"):
            try:
                filepath = config["last_profile"]
                if os.path.exists(filepath):
                    saved = self.config_mgr.load_profile(filepath)
                    saved_mappings = saved.get_mappings()
                    # Se il profilo salvato ha meno mappature dei predefiniti aggiornati,
                    # usa i predefiniti (le mappature sono state aggiornate nel codice)
                    if len(saved_mappings) >= default_count:
                        self.current_profile = saved
                        self.mappings = saved_mappings
                        self.profile_name_var.set(self.current_profile.name)
                        self._refresh_mapping_list()
                        return
            except Exception:
                pass

        # Primo avvio o profilo obsoleto: usa i predefiniti
        self.current_profile = default_profile
        self.mappings = default_profile.get_mappings()
        self._refresh_mapping_list()

    def _save_last_config(self):
        self.current_profile.name = self.profile_name_var.get().strip() or "Ultimo"
        self.current_profile.set_mappings(self.mappings)
        filepath = self.config_mgr.save_profile(self.current_profile, "last_session.json")
        self.config_mgr.save_app_config({"last_profile": filepath})

    # --------------------------------------------------------
    # Utilità
    # --------------------------------------------------------

    def _log(self, msg: str):
        if hasattr(self, 'lbl_footer_status'):
            self.lbl_footer_status.config(text=msg)

    def _debug_log(self, msg: str):
        """Scrive nel pannello debug visibile nella tab Connessione"""
        if not hasattr(self, 'debug_text'):
            return
        try:
            ts = time.strftime("%H:%M:%S")
            self.debug_text.config(state=tk.NORMAL)
            self.debug_text.insert(tk.END, f"[{ts}] {msg}\n")
            # Limita a 200 righe
            lines = int(self.debug_text.index('end-1c').split('.')[0])
            if lines > 200:
                self.debug_text.delete('1.0', f'{lines-200}.0')
            self.debug_text.see(tk.END)
            self.debug_text.config(state=tk.DISABLED)
        except Exception:
            pass

    def _on_close(self):
        self._stop_bridge()
        self._save_last_config()
        if self.arduino.is_connected():
            self.arduino.disconnect()
        if self.tsw6_api.is_connected():
            self.tsw6_api.disconnect()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


# ============================================================
# Dialog Mappatura
# ============================================================

class MappingDialog:
    def __init__(self, parent, title: str, mapping: LedMapping = None):
        self.result: Optional[LedMapping] = None
        m = mapping or LedMapping()

        self.window = tk.Toplevel(parent)
        self.window.title(title)
        self.window.geometry("620x520")
        self.window.transient(parent)
        self.window.grab_set()
        self.window.configure(bg=BG_COLOR)

        main = ttk.Frame(self.window, padding=15)
        main.pack(fill=tk.BOTH, expand=True)

        # Nome
        ttk.Label(main, text="Nome:").pack(anchor=tk.W)
        self.name_var = tk.StringVar(value=m.name)
        ttk.Entry(main, textvariable=self.name_var, width=50).pack(fill=tk.X, pady=(0, 8))

        self.enabled_var = tk.BooleanVar(value=m.enabled)
        ttk.Checkbutton(main, text="Attiva", variable=self.enabled_var).pack(anchor=tk.W, pady=(0, 8))

        # Sorgente
        src_frame = ttk.LabelFrame(main, text="  Endpoint TSW6  ", padding=10)
        src_frame.pack(fill=tk.X, pady=(0, 8))

        self.endpoint_var = tk.StringVar(value=m.tsw6_endpoint)
        ep_values = [ep for cat in COMMON_TSW6_ENDPOINTS for ep, _, _ in cat["endpoints"] if ep]
        ep_combo = ttk.Combobox(src_frame, textvariable=self.endpoint_var, values=ep_values, width=60)
        ep_combo.pack(fill=tk.X, pady=(0, 5))

        row_mult = ttk.Frame(src_frame)
        row_mult.pack(fill=tk.X)
        ttk.Label(row_mult, text="Moltiplicatore:").pack(side=tk.LEFT)
        self.multiplier_var = tk.StringVar(value=str(m.value_multiplier))
        ttk.Entry(row_mult, textvariable=self.multiplier_var, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Label(row_mult, text="Offset:").pack(side=tk.LEFT, padx=(15, 0))
        self.offset_var = tk.StringVar(value=str(m.value_offset))
        ttk.Entry(row_mult, textvariable=self.offset_var, width=10).pack(side=tk.LEFT, padx=5)

        # Condizione
        cond_frame = ttk.LabelFrame(main, text="  Condizione  ", padding=10)
        cond_frame.pack(fill=tk.X, pady=(0, 8))

        row_cond = ttk.Frame(cond_frame)
        row_cond.pack(fill=tk.X)

        self.condition_var = tk.StringVar(value=m.condition)
        ttk.Label(row_cond, text="Tipo:").pack(side=tk.LEFT)
        ttk.Combobox(row_cond, textvariable=self.condition_var, values=ALL_CONDITIONS,
                     width=12, state="readonly").pack(side=tk.LEFT, padx=5)

        ttk.Label(row_cond, text="Soglia:").pack(side=tk.LEFT, padx=(15, 0))
        self.threshold_var = tk.StringVar(value=str(m.threshold))
        ttk.Entry(row_cond, textvariable=self.threshold_var, width=10).pack(side=tk.LEFT, padx=5)

        ttk.Label(row_cond, text="Min:").pack(side=tk.LEFT, padx=(15, 0))
        self.threshold_min_var = tk.StringVar(value=str(m.threshold_min))
        ttk.Entry(row_cond, textvariable=self.threshold_min_var, width=8).pack(side=tk.LEFT, padx=5)

        ttk.Label(row_cond, text="Max:").pack(side=tk.LEFT, padx=(5, 0))
        self.threshold_max_var = tk.StringVar(value=str(m.threshold_max))
        ttk.Entry(row_cond, textvariable=self.threshold_max_var, width=8).pack(side=tk.LEFT, padx=5)

        # LED
        act_frame = ttk.LabelFrame(main, text="  LED Arduino  ", padding=10)
        act_frame.pack(fill=tk.X, pady=(0, 8))

        row_act = ttk.Frame(act_frame)
        row_act.pack(fill=tk.X)

        ttk.Label(row_act, text="LED:").pack(side=tk.LEFT)
        led_values = [f"{led.name} ({led.label} - {led.color})" for led in LEDS]
        self.led_combo = ttk.Combobox(row_act, values=led_values, width=35, state="readonly")
        self.led_combo.pack(side=tk.LEFT, padx=5)
        for i, led in enumerate(LEDS):
            if led.name == m.led_name:
                self.led_combo.current(i)
                break

        row_act2 = ttk.Frame(act_frame)
        row_act2.pack(fill=tk.X, pady=(8, 0))

        actions = [LedAction.ON, LedAction.OFF, LedAction.BLINK]
        action_labels = ["Accendi (ON)", "Spegni (OFF)", "Lampeggio (BLINK)"]
        self._actions_list = actions
        ttk.Label(row_act2, text="Azione:").pack(side=tk.LEFT)
        self.action_combo = ttk.Combobox(row_act2, values=action_labels, width=20, state="readonly")
        self.action_combo.pack(side=tk.LEFT, padx=5)
        for i, a in enumerate(actions):
            if a == m.action:
                self.action_combo.current(i)
                break

        ttk.Label(row_act2, text="Blink (s):").pack(side=tk.LEFT, padx=(15, 0))
        self.blink_var = tk.StringVar(value=str(m.blink_interval_sec))
        ttk.Entry(row_act2, textvariable=self.blink_var, width=8).pack(side=tk.LEFT, padx=5)

        # Pulsanti
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(btn_frame, text="Salva", command=self._save, style="Accent.TButton").pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Annulla", command=self.window.destroy).pack(side=tk.LEFT, padx=5)

    def _save(self):
        try:
            led_selection = self.led_combo.get()
            led_name = led_selection.split(" (")[0] if " (" in led_selection else led_selection
            action_idx = self.action_combo.current()
            action = self._actions_list[action_idx] if action_idx >= 0 else LedAction.ON

            self.result = LedMapping(
                name=self.name_var.get().strip(),
                enabled=self.enabled_var.get(),
                tsw6_endpoint=self.endpoint_var.get().strip(),
                value_multiplier=float(self.multiplier_var.get()),
                value_offset=float(self.offset_var.get()),
                condition=self.condition_var.get(),
                threshold=float(self.threshold_var.get()),
                threshold_min=float(self.threshold_min_var.get()),
                threshold_max=float(self.threshold_max_var.get()),
                led_name=led_name,
                action=action,
                blink_interval_sec=float(self.blink_var.get()),
            )
            self.window.destroy()
        except ValueError as e:
            messagebox.showerror("Errore", f"Valore non valido: {e}")


# ============================================================
# Dialog Profili
# ============================================================

class ProfileListDialog:
    def __init__(self, parent, profiles: List[Dict[str, str]]):
        self.selected_path: Optional[str] = None
        self.profiles = profiles

        self.window = tk.Toplevel(parent)
        self.window.title("Seleziona Profilo")
        self.window.geometry("500x350")
        self.window.transient(parent)
        self.window.grab_set()
        self.window.configure(bg=BG_COLOR)

        main = ttk.Frame(self.window, padding=15)
        main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main, text="Profili salvati:", style="Title.TLabel").pack(anchor=tk.W, pady=(0, 10))

        self.listbox = tk.Listbox(main, font=("Segoe UI", 11), bg=ENTRY_BG, fg=FG_COLOR,
                                   selectbackground=ACCENT_COLOR, height=10)
        self.listbox.pack(fill=tk.BOTH, expand=True)

        for p in profiles:
            desc = f" - {p['description']}" if p.get('description') else ""
            self.listbox.insert(tk.END, f"{p['name']}{desc}")

        self.listbox.bind("<Double-1>", lambda e: self._select())

        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(btn_frame, text="Carica", command=self._select, style="Accent.TButton").pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Annulla", command=self.window.destroy).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="📂 Da file...", command=self._from_file).pack(side=tk.RIGHT)

    def _select(self):
        sel = self.listbox.curselection()
        if sel:
            self.selected_path = self.profiles[sel[0]]["filepath"]
            self.window.destroy()

    def _from_file(self):
        filepath = filedialog.askopenfilename(
            title="Carica Profilo",
            filetypes=[("JSON", "*.json"), ("Tutti", "*.*")],
        )
        if filepath:
            self.selected_path = filepath
            self.window.destroy()


# ============================================================
# Entry Point
# ============================================================

def main():
    app = TSW6ArduineBridgeApp()
    app.run()


if __name__ == "__main__":
    main()
