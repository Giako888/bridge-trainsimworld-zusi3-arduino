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
    create_default_profile, APP_NAME, APP_VERSION,
    TRAIN_PROFILES, detect_profile_id, get_profile_by_id,
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
        self._active_profile_id = "BR101"
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

        # Tab 2: Profilo Treno
        self.tab_profiles = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_profiles, text="  🚂 Profilo  ")
        self._build_profiles_tab()

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
    # Tab Profilo Treno
    # --------------------------------------------------------

    def _build_profiles_tab(self):
        container = ttk.Frame(self.tab_profiles)
        container.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        # --- Rilevamento treno ---
        detect_frame = ttk.LabelFrame(container, text="  Rilevamento Treno  ", padding=10)
        detect_frame.pack(fill=tk.X, pady=(0, 10))

        row_detect = ttk.Frame(detect_frame)
        row_detect.pack(fill=tk.X)

        ttk.Label(row_detect, text="Treno rilevato:").pack(side=tk.LEFT)
        self.detected_train_var = tk.StringVar(value="— nessuno —")
        ttk.Label(row_detect, textvariable=self.detected_train_var,
                  font=("Segoe UI", 10, "bold"), foreground=WARNING_COLOR,
                  background=CARD_BG).pack(side=tk.LEFT, padx=10)

        self.btn_detect_train = ttk.Button(row_detect, text="🔍 Rileva Treno",
                                            command=self._detect_and_apply_train,
                                            style="Accent.TButton")
        self.btn_detect_train.pack(side=tk.RIGHT)

        # --- Selezione profilo ---
        select_frame = ttk.LabelFrame(container, text="  Profilo Attivo  ", padding=10)
        select_frame.pack(fill=tk.X, pady=(0, 10))

        self.profile_radio_var = tk.StringVar(value="BR101")
        self._active_profile_id = "BR101"

        for pid, info in TRAIN_PROFILES.items():
            row = ttk.Frame(select_frame)
            row.pack(fill=tk.X, pady=2)

            rb = tk.Radiobutton(
                row, text=info["name"],
                variable=self.profile_radio_var, value=pid,
                command=self._on_profile_radio_changed,
                bg=CARD_BG, fg=FG_COLOR, selectcolor=ENTRY_BG,
                activebackground=CARD_BG, activeforeground=ACCENT_COLOR,
                font=("Segoe UI", 10),
                indicatoron=True,
            )
            rb.pack(side=tk.LEFT)

            ttk.Label(row, text=f"  {info['description']}",
                      font=("Segoe UI", 9, "italic"),
                      foreground="#6c7086").pack(side=tk.LEFT)

        row_apply = ttk.Frame(select_frame)
        row_apply.pack(fill=tk.X, pady=(8, 0))
        self.btn_apply_profile = ttk.Button(row_apply, text="✅ Applica Profilo",
                                             command=self._apply_selected_profile,
                                             style="Accent.TButton")
        self.btn_apply_profile.pack(side=tk.LEFT)

        self.lbl_profile_status = ttk.Label(row_apply, text="", font=("Segoe UI", 9))
        self.lbl_profile_status.pack(side=tk.LEFT, padx=15)

        # --- Visualizzazione mappature (sola lettura) ---
        mappings_frame = ttk.LabelFrame(container, text="  Mappature Profilo (sola lettura)  ", padding=5)
        mappings_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("name", "endpoint", "led", "action")
        self.profile_mapping_tree = ttk.Treeview(mappings_frame, columns=columns,
                                                  show="headings", height=12)

        self.profile_mapping_tree.heading("name", text="Nome")
        self.profile_mapping_tree.heading("endpoint", text="Endpoint TSW6")
        self.profile_mapping_tree.heading("led", text="LED")
        self.profile_mapping_tree.heading("action", text="Azione")

        self.profile_mapping_tree.column("name", width=180)
        self.profile_mapping_tree.column("endpoint", width=400)
        self.profile_mapping_tree.column("led", width=120, anchor=tk.CENTER)
        self.profile_mapping_tree.column("action", width=100, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(mappings_frame, orient=tk.VERTICAL,
                                   command=self.profile_mapping_tree.yview)
        self.profile_mapping_tree.configure(yscrollcommand=scrollbar.set)

        self.profile_mapping_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._refresh_profile_mapping_view()

    def _refresh_profile_mapping_view(self):
        """Aggiorna la treeview sola lettura delle mappature del profilo attivo."""
        for item in self.profile_mapping_tree.get_children():
            self.profile_mapping_tree.delete(item)

        for i, m in enumerate(self.mappings):
            action_names = {
                LedAction.ON: "ON",
                LedAction.OFF: "OFF",
                LedAction.BLINK: f"BLINK {m.blink_interval_sec}s",
            }
            led_info = LED_BY_NAME.get(m.led_name)
            led_label = led_info.label if led_info else m.led_name

            ep = m.tsw6_endpoint
            for prefix in ["CurrentFormation/0/MFA_Indicators.Property.",
                           "CurrentFormation/0/PZB_Service_V3.",
                           "CurrentFormation/0/LZB_Service.",
                           "CurrentFormation/0/BP_Sifa_Service.",
                           "CurrentFormation/0."]:
                if ep.startswith(prefix):
                    ep = "..." + ep[len(prefix):]
                    break
            if m.value_key:
                ep += f" [{m.value_key}]"

            self.profile_mapping_tree.insert("", tk.END, iid=str(i), values=(
                m.name, ep, led_label,
                action_names.get(m.action, m.action),
            ))

    def _on_profile_radio_changed(self):
        """L'utente ha cambiato la selezione radio."""
        pass  # L'azione avviene su "Applica Profilo"

    def _apply_selected_profile(self):
        """Applica il profilo selezionato dall'utente."""
        pid = self.profile_radio_var.get()
        self._load_profile_by_id(pid)

    def _load_profile_by_id(self, profile_id: str):
        """Carica un profilo dal registro TRAIN_PROFILES."""
        profile = get_profile_by_id(profile_id)
        if not profile:
            self._log(f"Profilo '{profile_id}' non trovato")
            return

        self._active_profile_id = profile_id
        self.current_profile = profile
        self.mappings = profile.get_mappings()
        self.profile_radio_var.set(profile_id)

        info = TRAIN_PROFILES.get(profile_id, {})
        self.lbl_profile_status.config(
            text=f"● {info.get('name', profile_id)} attivo ({len(self.mappings)} mappature)",
            style="Connected.TLabel"
        )
        self._refresh_profile_mapping_view()
        self._log(f"Profilo: {info.get('name', profile_id)}")

        # Se il bridge è attivo, avvisa che va riavviato
        if self.running:
            self._debug_log("⚠️ Profilo cambiato — riavvia il bridge per applicare")

    def _detect_and_apply_train(self):
        """Rileva il treno e applica automaticamente il profilo corrispondente."""
        if not self.tsw6_api.is_connected():
            messagebox.showwarning("Attenzione", "Connettiti a TSW6 prima di rilevare il treno.")
            return

        self.detected_train_var.set("⏳ Rilevamento...")
        self.root.update()

        def do_detect():
            object_class = self.tsw6_api.detect_train()
            self.root.after(0, lambda: self._on_train_detected(object_class))

        threading.Thread(target=do_detect, daemon=True).start()

    def _on_train_detected(self, object_class: Optional[str]):
        """Callback quando il treno è stato rilevato."""
        if not object_class:
            self.detected_train_var.set("— non rilevato —")
            self._log("Treno non rilevato")
            return

        self.detected_train_var.set(object_class)
        profile_id = detect_profile_id(object_class)

        if profile_id:
            self._load_profile_by_id(profile_id)
            info = TRAIN_PROFILES[profile_id]
            self._debug_log(f"🚂 Treno: {object_class} → {info['name']}")
        else:
            self.lbl_profile_status.config(
                text=f"⚠️ Treno '{object_class}' non riconosciuto — seleziona manualmente",
                style="Warning.TLabel"
            )
            self._debug_log(f"⚠️ Treno '{object_class}' non ha un profilo, scegli manualmente")

    def _auto_detect_train_silent(self):
        """Rileva il treno in background senza messagebox. Chiamato dopo la connessione."""
        if not self.tsw6_api.is_connected():
            return

        def do_detect():
            object_class = self.tsw6_api.detect_train()
            self.root.after(0, lambda: self._on_train_detected(object_class))

        threading.Thread(target=do_detect, daemon=True).start()

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
        self._log(f"Copiato: {ep_path}")

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
            # Auto-detect treno
            self._auto_detect_train_silent()
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
        # Aggiungi anche i requires_endpoint (condizioni AND)
        for m in self.mappings:
            req = getattr(m, 'requires_endpoint', '')
            if m.enabled and req:
                endpoints.append(req)
            req_f = getattr(m, 'requires_endpoint_false', '')
            if m.enabled and req_f:
                endpoints.append(req_f)
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

        # Subscription mode: intervallo più basso possibile (1 sola GET per ciclo)
        poll_interval_sec = self.current_profile.poll_interval_ms / 1000.0
        if poll_interval_sec >= 0.1:
            poll_interval_sec = 0.05  # 50ms default per subscription
        poll_interval = max(poll_interval_sec, 0.05)
        self.poller = TSW6Poller(self.tsw6_api, interval=poll_interval, use_subscription=True)

        # Il callback del poller gira nel thread di polling.
        # _on_tsw6_data() è thread-safe: aggiorna dicts (GIL protetti)
        # e invia comandi Arduino (lock interno). Evitiamo root.after()
        # per ridurre la latenza ~10-50ms del dispatch Tkinter.
        # Solo gli update GUI (cerchietti LED) girano nel main thread
        # tramite _update_led_indicators() già schedulato con after().
        self.poller.add_callback(self._on_tsw6_data)

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
        mode = "Subscription" if self.poller._subscription_active else "GET"
        self._log(f"Bridge avviato ({len(endpoints)} endpoint, modo {mode})")
        self._debug_log(f"✅ Bridge attivo - {mode} mode, polling ogni {self.poller.interval*1000:.0f}ms")
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

        # Accumula stati LED: {led_name: (action, priority)}
        # Mappature con priority più alta vincono; a parità BLINK > ON > OFF
        led_accumulator: Dict[str, tuple] = {}  # {led_name: ("blink"|"on"|"off", priority)}
        
        for mapping in self.mappings:
            if not mapping.enabled or not mapping.tsw6_endpoint:
                continue

            # Controlla requires_endpoint (condizione AND): se impostato, deve essere True nei dati
            req_ep = getattr(mapping, 'requires_endpoint', '')
            if req_ep:
                req_val = data.get(req_ep)
                if req_val is None:
                    # Fallback case-insensitive
                    req_lower = req_ep.lower()
                    for k, v in data.items():
                        if k.lower() == req_lower:
                            req_val = v
                            break
                if not req_val:
                    continue  # requires_endpoint non soddisfatto, skip

            # Controlla requires_endpoint_false (condizione AND-NOT): se impostato, deve essere False nei dati
            req_ep_false = getattr(mapping, 'requires_endpoint_false', '')
            if req_ep_false:
                req_val_f = data.get(req_ep_false)
                if req_val_f is None:
                    req_lower_f = req_ep_false.lower()
                    for k, v in data.items():
                        if k.lower() == req_lower_f:
                            req_val_f = v
                            break
                if req_val_f:
                    continue  # requires_endpoint_false è True, skip

            # 1) Match diretto
            value = data.get(mapping.tsw6_endpoint)
            
            # 2) Fallback: match case-insensitive esatto
            if value is None:
                ep_lower = mapping.tsw6_endpoint.lower()
                
                for key, val in data.items():
                    if key.lower() == ep_lower:
                        value = val
                        break
            
            if value is None:
                continue

            # 3) Estrazione value_key per endpoint Function (valori nested dict)
            vk = getattr(mapping, 'value_key', '')
            if vk and isinstance(value, dict):
                value = self._extract_value_key(value, vk)
                if value is None:
                    continue

            matched_count += 1
            try:
                led_on = self._evaluate_mapping(mapping, value)
                led_name = mapping.led_name
                m_priority = getattr(mapping, 'priority', 0)
                current_action, current_prio = led_accumulator.get(led_name, ("off", -1))
                
                if led_on:
                    new_action = "blink" if mapping.action == LedAction.BLINK else "on"
                    # Priority più alta vince sempre; a parità: blink > on > off
                    if m_priority > current_prio:
                        led_accumulator[led_name] = (new_action, m_priority)
                    elif m_priority == current_prio:
                        if new_action == "blink" and current_action != "blink":
                            led_accumulator[led_name] = (new_action, m_priority)
                        elif new_action == "on" and current_action == "off":
                            led_accumulator[led_name] = (new_action, m_priority)
                elif led_name not in led_accumulator:
                    led_accumulator[led_name] = ("off", -1)

                debug_matches.append(f"{led_name}={led_accumulator.get(led_name, ('off', -1))[0].upper()}")
            except Exception as e:
                logger.error(f"Errore mappatura '{mapping.name}': {e}")
                debug_matches.append(f"{mapping.led_name}=ERR:{e}")

        # Applica gli stati accumulati alla GUI e ad Arduino
        for led_name, (state, _prio) in led_accumulator.items():
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



    def _extract_value_key(self, data: Any, key_pattern: str) -> Any:
        """Estrae un valore da un dict (anche nested) cercando una chiave che contiene key_pattern.
        Gestisce le chiavi UE4 con suffisso GUID (es. '1000Hz_Active_93_200CCC...')."""
        if isinstance(data, dict):
            # Prima cerca match diretto
            if key_pattern in data:
                return data[key_pattern]
            # Poi cerca match parziale (chiave contiene il pattern)
            for k, v in data.items():
                if key_pattern in k:
                    return v
            # Ricorsione nei valori nested
            for k, v in data.items():
                result = self._extract_value_key(v, key_pattern)
                if result is not None:
                    return result
        return None

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
        """Salva il profilo attivo (solo l'ID del profilo selezionato)."""
        profile_id = getattr(self, '_active_profile_id', None)
        if profile_id:
            self._save_last_config()
            self._log(f"Profilo salvato: {profile_id}")
        else:
            self._log("Nessun profilo attivo da salvare")

    def _load_profile(self):
        """Non più necessario — i profili sono fissi e selezionati dalla tab Profilo."""
        pass

    def _load_last_config(self):
        """Carica l'ultimo profilo usato dall'app config."""
        config = self.config_mgr.load_app_config()
        last_id = config.get("last_profile_id", "")
        if last_id and last_id in TRAIN_PROFILES:
            self._load_profile_by_id(last_id)
            return

        # Primo avvio: carica BR101 come default
        self._load_profile_by_id("BR101")

    def _save_last_config(self):
        """Salva l'ID del profilo attivo nella configurazione."""
        profile_id = getattr(self, '_active_profile_id', 'BR101')
        self.config_mgr.save_app_config({"last_profile_id": profile_id})

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
# Entry Point
# ============================================================

def main():
    app = TSW6ArduineBridgeApp()
    app.run()


if __name__ == "__main__":
    main()
