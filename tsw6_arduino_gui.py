"""
Train Simulator Bridge - GUI Principale
======================================
Interfaccia grafica per collegare TSW6 o Zusi3 ad Arduino Leonardo.

Funzionalità:
- Connessione a TSW6 tramite API HTTP (porta 31270)
- Connessione a Zusi3 tramite TCP (porta 1436)
- Connessione ad Arduino Leonardo tramite seriale
- Configurazione mappature: dati simulatore → 12 LED Charlieplexing
- Gestione profili (TSW6)
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
from zusi3_client import Zusi3Client, TrainState
from arduino_bridge import (
    ArduinoController, LEDS, LED_BY_NAME, LedInfo,
    find_arduino_port, list_serial_ports
)
from config_models import (
    Profile, LedMapping, LedAction, Condition,
    ConfigManager, COMMON_TSW6_ENDPOINTS, ALL_CONDITIONS,
    create_default_profile, APP_NAME, APP_VERSION,
    TRAIN_PROFILES, detect_profile_id, get_profile_by_id,
    SimulatorType,
)
from i18n import (
    t, set_language, get_language, detect_system_language,
    LANGUAGES, PROFILE_DESC_KEYS,
)
from led_panel import (
    MFAPanelWindow, MFAWebServer, get_led_state_manager,
)

# QR code (opzionale)
try:
    import qrcode
    _HAS_QRCODE = True
except ImportError:
    _HAS_QRCODE = False

import subprocess

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

        # Zusi3
        self.zusi3_client: Optional[Zusi3Client] = None
        self._zusi3_blink_visible = True  # Toggle per lampeggio Zusi3

        # Stato
        self._simulator_type = SimulatorType.TSW6
        self._active_profile_id = "BR101"
        self.current_profile = create_default_profile()
        self.mappings: List[LedMapping] = self.current_profile.get_mappings()
        self.running = False
        self.last_tsw6_data: Dict[str, Any] = {}
        self._gui_led_states: Dict[str, bool] = {}  # Stato LED nella GUI (da dati TSW6)
        self._gui_led_blink: Dict[str, float] = {}  # Intervallo blink per LED (0.0=fisso, >0=lampeggio)

        # MFA Panel (popup + web server)
        self._led_state_mgr = get_led_state_manager()
        self._mfa_panel: Optional[MFAPanelWindow] = None
        self._mfa_web_port = 8080
        self._mfa_web_server = MFAWebServer(port=self._mfa_web_port)
        self._qr_window: Optional[tk.Toplevel] = None
        self._firewall_rule_name = "TrainSimBridge_MFA"

        # Lingua: carica da config o rileva dal sistema
        self._init_language()

        # Stile
        self._setup_styles()

        # UI
        self._build_ui()

        # Carica ultimo profilo
        self._load_last_config()

        # Chiusura
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # --------------------------------------------------------
    # Lingua
    # --------------------------------------------------------

    def _init_language(self):
        """Inizializza lingua: da config salvata oppure auto-detect dal sistema."""
        config = ConfigManager().load_app_config()
        saved_lang = config.get("language")
        if saved_lang and saved_lang in LANGUAGES:
            set_language(saved_lang)
        else:
            set_language(detect_system_language())

    def _change_language(self, lang: str):
        """Cambia lingua e aggiorna tutta la UI."""
        if lang == get_language():
            return
        set_language(lang)
        self._update_lang_buttons()
        self._retranslate_ui()
        # Salva preferenza
        self._save_last_config()

    def _on_flag_hover(self, event, code: str, entering: bool):
        """Show subtle border on hover for inactive flags."""
        if code == get_language():
            return  # active flag keeps its accent border
        if entering:
            event.widget.config(highlightbackground="#45475a")
        else:
            event.widget.config(highlightbackground=BG_COLOR)

    def _create_flag_images(self):
        """Generate pixel-art flag images for the language selector."""
        W, H = 32, 22
        BORDER_CLR = "#585b70"
        self._flag_images = {}

        def make_flag(pixel_func):
            img = tk.PhotoImage(width=W, height=H)
            row_data = []
            for y in range(H):
                row = []
                for x in range(W):
                    if x == 0 or x == W - 1 or y == 0 or y == H - 1:
                        row.append(BORDER_CLR)
                    else:
                        row.append(pixel_func(x, y))
                row_data.append("{" + " ".join(row) + "}")
            img.put(" ".join(row_data))
            return img

        # Italy: green | white | red
        def italy(x, _y):
            third = W / 3
            if x < third:
                return "#009344"
            if x < 2 * third:
                return "#FFFFFF"
            return "#CF2734"
        self._flag_images["it"] = make_flag(italy)

        # Germany: black / red / gold
        def germany(_x, y):
            third = H / 3
            if y < third:
                return "#000000"
            if y < 2 * third:
                return "#DD0000"
            return "#FFCC00"
        self._flag_images["de"] = make_flag(germany)

        # UK: simplified Union Jack
        def uk(x, y):
            BLUE, WHITE, RED = "#012169", "#FFFFFF", "#C8102E"
            color = BLUE
            hyp = (H ** 2 + W ** 2) ** 0.5
            d1 = abs(H * x - W * y) / hyp
            d2 = abs(H * (W - 1 - x) - W * y) / hyp
            if d1 < 2.5 or d2 < 2.5:
                color = WHITE
            if d1 < 1.0 or d2 < 1.0:
                color = RED
            cx, cy = W / 2, H / 2
            if abs(x - cx + 0.5) < 3 or abs(y - cy + 0.5) < 3:
                color = WHITE
            if abs(x - cx + 0.5) < 1.5 or abs(y - cy + 0.5) < 1.5:
                color = RED
            return color
        self._flag_images["en"] = make_flag(uk)

    def _update_lang_buttons(self):
        """Evidenzia il flag della lingua attiva con bordo accent."""
        cur = get_language()
        for code, btn in self._lang_buttons.items():
            if code == cur:
                btn.config(highlightbackground=ACCENT_COLOR, highlightthickness=2)
            else:
                btn.config(highlightbackground=BG_COLOR, highlightthickness=2)

    def _retranslate_ui(self):
        """Aggiorna tutti i testi della UI nella lingua corrente."""
        # Tabs
        self.notebook.tab(self.tab_connect, text=t("tab_connection"))
        if self._simulator_type == SimulatorType.ZUSI3:
            self.notebook.tab(self.tab_profiles, text=t("tab_profile_na"))
        else:
            self.notebook.tab(self.tab_profiles, text=t("tab_profile"))

        # Simulator frame
        self.sim_frame.config(text=t("lf_simulator"))
        self.rb_tsw6.config(text=t("rb_tsw6"))
        self.rb_zusi3.config(text=t("rb_zusi3"))

        # TSW6 frame
        self.tsw6_frame.config(text=t("lf_tsw6"))
        self.lbl_tsw6_host.config(text=t("host"))
        self.lbl_tsw6_port.config(text=t("port"))
        self.btn_tsw6_connect.config(text=t("connect"))
        self.btn_tsw6_disconnect.config(text=t("disconnect"))
        self.lbl_tsw6_apikey.config(text=t("api_key"))
        self.btn_tsw6_apikey_auto.config(text=t("api_key_auto"))

        # Zusi3 frame
        self.zusi3_frame.config(text=t("lf_zusi3"))
        self.lbl_zusi3_host.config(text=t("host"))
        self.lbl_zusi3_port.config(text=t("port"))
        self.btn_zusi3_connect.config(text=t("connect"))
        self.btn_zusi3_disconnect.config(text=t("disconnect"))

        # Arduino frame
        self.arduino_frame_widget.config(text=t("lf_arduino"))
        self.lbl_arduino_port.config(text=t("port_label"))
        self.btn_arduino_connect.config(text=t("connect"))
        self.btn_arduino_disconnect.config(text=t("disconnect"))
        self.btn_arduino_test.config(text=t("btn_test"))
        self.btn_arduino_off.config(text=t("btn_leds_off"))

        # Bridge frame
        if self._simulator_type == SimulatorType.TSW6:
            self.bridge_frame.config(text=t("lf_bridge_tsw6"))
        elif self._simulator_type == SimulatorType.ZUSI3:
            self.bridge_frame.config(text=t("lf_bridge_zusi3"))
        else:
            self.bridge_frame.config(text=t("lf_bridge"))
        self.btn_start.config(text=t("btn_start_bridge"))
        self.btn_stop.config(text=t("btn_stop_bridge"))

        # MFA panel
        self.mfa_frame_widget.config(text=t("lf_mfa_panel"))
        self.btn_mfa_popup.config(text=t("btn_mfa_panel"))
        if self._mfa_web_server.is_running:
            self.btn_web_panel.config(text=t("btn_web_stop"))
        else:
            self.btn_web_panel.config(text=t("btn_web_panel"))
        if self.btn_qr:
            self.btn_qr.config(text=t("btn_qr_code"))

        # Debug log
        self.debug_frame_widget.config(text=t("lf_debug_log"))

        # Footer
        self.lbl_footer_status.config(text=t("ready"))

        # Profile tab
        self.detect_frame_widget.config(text=t("lf_train_detect"))
        self.lbl_train_detected.config(text=t("train_detected"))
        self.btn_detect_train.config(text=t("btn_detect_train"))
        self.select_frame_widget.config(text=t("lf_active_profile"))
        self.btn_apply_profile.config(text=t("btn_apply_profile"))
        self.mappings_frame_widget.config(text=t("lf_mappings"))

        # Treeview headings
        self.profile_mapping_tree.heading("name", text=t("col_name"))
        self.profile_mapping_tree.heading("endpoint", text=t("col_endpoint"))
        self.profile_mapping_tree.heading("led", text=t("col_led"))
        self.profile_mapping_tree.heading("action", text=t("col_action"))

        # Profile radio descriptions
        for pid, (rb_widget, desc_widget) in self._profile_radio_widgets.items():
            desc_key = PROFILE_DESC_KEYS.get(pid)
            if desc_key:
                desc_widget.config(text=f"  {t(desc_key)}")

        # Update bridge button states (translates status labels)
        self._update_bridge_button()

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
                  foreground=[("selected", ACCENT_COLOR), ("disabled", "#585b70"), ("active", "#ffffff")],
                  background=[("selected", CARD_BG), ("disabled", "#181825"), ("active", "#585b70")])

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

        # Language selector (flag buttons)
        lang_frame = ttk.Frame(header)
        lang_frame.pack(side=tk.RIGHT)
        self._lang_buttons = {}
        self._create_flag_images()
        for code in LANGUAGES:
            btn = tk.Label(
                lang_frame,
                image=self._flag_images[code],
                bg=BG_COLOR,
                cursor="hand2",
                bd=0,
                highlightthickness=2,
                highlightbackground=BG_COLOR,
            )
            btn.pack(side=tk.LEFT, padx=4)
            btn.bind("<Button-1>", lambda e, c=code: self._change_language(c))
            btn.bind("<Enter>", lambda e, c=code: self._on_flag_hover(e, c, True))
            btn.bind("<Leave>", lambda e, c=code: self._on_flag_hover(e, c, False))
            self._lang_buttons[code] = btn
        self._update_lang_buttons()

        # Notebook (tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Tab 1: Connessione + Bridge
        self.tab_connect = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_connect, text=t("tab_connection"))
        self._build_connection_tab()

        # Tab 2: Profilo Treno (solo TSW6)
        self.tab_profiles = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_profiles, text=t("tab_profile"))
        self._build_profiles_tab()

        # Footer
        self._build_footer()

    # --------------------------------------------------------
    # Tab Connessione
    # --------------------------------------------------------

    def _build_connection_tab(self):
        container = ttk.Frame(self.tab_connect)
        container.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        # --- Selettore Simulatore ---
        self.sim_frame = ttk.LabelFrame(container, text=t("lf_simulator"), padding=10)
        self.sim_frame.pack(fill=tk.X, pady=(0, 10))

        row_sim = ttk.Frame(self.sim_frame)
        row_sim.pack(fill=tk.X)

        self.sim_type_var = tk.StringVar(value=SimulatorType.TSW6)
        self.rb_tsw6 = tk.Radiobutton(
            row_sim, text=t("rb_tsw6"),
            variable=self.sim_type_var, value=SimulatorType.TSW6,
            command=self._on_simulator_changed,
            bg=CARD_BG, fg=FG_COLOR, selectcolor=ENTRY_BG,
            activebackground=CARD_BG, activeforeground=ACCENT_COLOR,
            disabledforeground="#6c7086",
            font=("Segoe UI", 10), indicatoron=True,
        )
        self.rb_tsw6.pack(side=tk.LEFT, padx=(0, 20))

        self.rb_zusi3 = tk.Radiobutton(
            row_sim, text=t("rb_zusi3"),
            variable=self.sim_type_var, value=SimulatorType.ZUSI3,
            command=self._on_simulator_changed,
            bg=CARD_BG, fg=FG_COLOR, selectcolor=ENTRY_BG,
            activebackground=CARD_BG, activeforeground=ACCENT_COLOR,
            disabledforeground="#6c7086",
            font=("Segoe UI", 10), indicatoron=True,
        )
        self.rb_zusi3.pack(side=tk.LEFT)

        # Label informativa (visibile quando un simulatore è connesso)
        self.lbl_sim_locked = ttk.Label(row_sim, text="", style="Warning.TLabel")
        self.lbl_sim_locked.pack(side=tk.LEFT, padx=(15, 0))

        # --- TSW6 (compatto) ---
        self.tsw6_frame = ttk.LabelFrame(container, text=t("lf_tsw6"), padding=10)
        self.tsw6_frame.pack(fill=tk.X, pady=(0, 10))

        row1 = ttk.Frame(self.tsw6_frame)
        row1.pack(fill=tk.X, pady=2)
        self.lbl_tsw6_host = ttk.Label(row1, text=t("host"))
        self.lbl_tsw6_host.pack(side=tk.LEFT)
        self.tsw6_host_var = tk.StringVar(value="127.0.0.1")
        ttk.Entry(row1, textvariable=self.tsw6_host_var, width=15).pack(side=tk.LEFT, padx=5)
        self.lbl_tsw6_port = ttk.Label(row1, text=t("port"))
        self.lbl_tsw6_port.pack(side=tk.LEFT, padx=(10, 0))
        self.tsw6_port_var = tk.StringVar(value="31270")
        ttk.Entry(row1, textvariable=self.tsw6_port_var, width=7).pack(side=tk.LEFT, padx=5)

        self.btn_tsw6_connect = ttk.Button(row1, text=t("connect"), command=self._connect_tsw6, style="Accent.TButton")
        self.btn_tsw6_connect.pack(side=tk.LEFT, padx=(15, 5))
        self.btn_tsw6_disconnect = ttk.Button(row1, text=t("disconnect"), command=self._disconnect_tsw6, state=tk.DISABLED)
        self.btn_tsw6_disconnect.pack(side=tk.LEFT, padx=2)
        self.lbl_tsw6_status = ttk.Label(row1, text=t("status_disconnected"), style="Disconnected.TLabel")
        self.lbl_tsw6_status.pack(side=tk.LEFT, padx=15)

        row2 = ttk.Frame(self.tsw6_frame)
        row2.pack(fill=tk.X, pady=2)
        self.lbl_tsw6_apikey = ttk.Label(row2, text=t("api_key"))
        self.lbl_tsw6_apikey.pack(side=tk.LEFT)
        self.tsw6_apikey_var = tk.StringVar(value="")
        self.tsw6_apikey_entry = ttk.Entry(row2, textvariable=self.tsw6_apikey_var, width=40, show="*")
        self.tsw6_apikey_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(row2, text="👁", width=3, command=self._toggle_apikey_visibility).pack(side=tk.LEFT)
        self.btn_tsw6_apikey_auto = ttk.Button(row2, text=t("api_key_auto"), command=self._auto_detect_apikey)
        self.btn_tsw6_apikey_auto.pack(side=tk.LEFT, padx=5)
        self._apikey_visible = False

        # Prova a caricare la chiave automaticamente all'avvio
        self._auto_detect_apikey()

        # --- Zusi3 (TCP) ---
        self.zusi3_frame = ttk.LabelFrame(container, text=t("lf_zusi3"), padding=10)
        # Non pack — verrà mostrato solo quando selezionato Zusi3

        row_z1 = ttk.Frame(self.zusi3_frame)
        row_z1.pack(fill=tk.X, pady=2)
        self.lbl_zusi3_host = ttk.Label(row_z1, text=t("host"))
        self.lbl_zusi3_host.pack(side=tk.LEFT)
        self.zusi3_host_var = tk.StringVar(value="127.0.0.1")
        ttk.Entry(row_z1, textvariable=self.zusi3_host_var, width=15).pack(side=tk.LEFT, padx=5)
        self.lbl_zusi3_port = ttk.Label(row_z1, text=t("port"))
        self.lbl_zusi3_port.pack(side=tk.LEFT, padx=(10, 0))
        self.zusi3_port_var = tk.StringVar(value="1436")
        ttk.Entry(row_z1, textvariable=self.zusi3_port_var, width=7).pack(side=tk.LEFT, padx=5)

        self.btn_zusi3_connect = ttk.Button(row_z1, text=t("connect"), command=self._connect_zusi3, style="Accent.TButton")
        self.btn_zusi3_connect.pack(side=tk.LEFT, padx=(15, 5))
        self.btn_zusi3_disconnect = ttk.Button(row_z1, text=t("disconnect"), command=self._disconnect_zusi3, state=tk.DISABLED)
        self.btn_zusi3_disconnect.pack(side=tk.LEFT, padx=2)
        self.lbl_zusi3_status = ttk.Label(row_z1, text=t("status_disconnected"), style="Disconnected.TLabel")
        self.lbl_zusi3_status.pack(side=tk.LEFT, padx=15)

        # --- Arduino ---
        self.arduino_frame_widget = ttk.LabelFrame(container, text=t("lf_arduino"), padding=10)
        self.arduino_frame_widget.pack(fill=tk.X, pady=(0, 10))

        row_a1 = ttk.Frame(self.arduino_frame_widget)
        row_a1.pack(fill=tk.X, pady=2)
        self.lbl_arduino_port = ttk.Label(row_a1, text=t("port_label"))
        self.lbl_arduino_port.pack(side=tk.LEFT)
        self.arduino_port_var = tk.StringVar(value="Auto-detect")
        self.arduino_port_combo = ttk.Combobox(row_a1, textvariable=self.arduino_port_var, width=30, state="readonly")
        self.arduino_port_combo.pack(side=tk.LEFT, padx=5)
        ttk.Button(row_a1, text="🔄", command=self._refresh_serial_ports).pack(side=tk.LEFT, padx=2)

        self.btn_arduino_connect = ttk.Button(row_a1, text=t("connect"), command=self._connect_arduino, style="Accent.TButton")
        self.btn_arduino_connect.pack(side=tk.LEFT, padx=(15, 5))
        self.btn_arduino_disconnect = ttk.Button(row_a1, text=t("disconnect"), command=self._disconnect_arduino, state=tk.DISABLED)
        self.btn_arduino_disconnect.pack(side=tk.LEFT, padx=2)
        self.btn_arduino_test = ttk.Button(row_a1, text=t("btn_test"), command=self._test_arduino_leds)
        self.btn_arduino_test.pack(side=tk.LEFT, padx=5)
        self.btn_arduino_off = ttk.Button(row_a1, text=t("btn_leds_off"), command=self._all_leds_off)
        self.btn_arduino_off.pack(side=tk.LEFT, padx=2)
        self.lbl_arduino_status = ttk.Label(row_a1, text=t("status_disconnected"), style="Disconnected.TLabel")
        self.lbl_arduino_status.pack(side=tk.LEFT, padx=15)

        # --- Bridge ---
        self.bridge_frame = ttk.LabelFrame(container, text=t("lf_bridge"), padding=10)
        self.bridge_frame.pack(fill=tk.X, pady=(0, 10))

        row_b = ttk.Frame(self.bridge_frame)
        row_b.pack(fill=tk.X)
        self.btn_start = ttk.Button(row_b, text=t("btn_start_bridge"), command=self._start_bridge,
                                     style="Accent.TButton", state=tk.DISABLED)
        self.btn_start.pack(side=tk.LEFT)
        self.btn_stop = ttk.Button(row_b, text=t("btn_stop_bridge"), command=self._stop_bridge, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=5)
        self.lbl_bridge_status = ttk.Label(row_b, text=t("bridge_waiting"), style="Status.TLabel")
        self.lbl_bridge_status.pack(side=tk.LEFT, padx=15)

        # --- Pannello MFA (pulsanti per popup e web server) ---
        self.mfa_frame_widget = ttk.LabelFrame(container, text=t("lf_mfa_panel"), padding=10)
        self.mfa_frame_widget.pack(fill=tk.X, pady=(0, 5))

        row_mfa = ttk.Frame(self.mfa_frame_widget)
        row_mfa.pack(fill=tk.X)

        self.btn_mfa_popup = ttk.Button(row_mfa, text=t("btn_mfa_panel"),
                                         command=self._toggle_mfa_panel, style="Accent.TButton")
        self.btn_mfa_popup.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_web_panel = ttk.Button(row_mfa, text=t("btn_web_panel"),
                                         command=self._toggle_web_server)
        self.btn_web_panel.pack(side=tk.LEFT, padx=(0, 5))

        # Porta web server
        ttk.Label(row_mfa, text=t("web_port_label"), font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(8, 2))
        self._web_port_var = tk.IntVar(value=self._mfa_web_port)
        self.spn_web_port = ttk.Spinbox(row_mfa, from_=1024, to=65535,
                                         textvariable=self._web_port_var, width=6,
                                         font=("Consolas", 9))
        self.spn_web_port.pack(side=tk.LEFT, padx=(0, 5))

        # QR code button (solo se qrcode installato)
        if _HAS_QRCODE:
            self.btn_qr = ttk.Button(row_mfa, text=t("btn_qr_code"), command=self._show_qr_code,
                                      state=tk.DISABLED)
            self.btn_qr.pack(side=tk.LEFT, padx=(5, 5))
        else:
            self.btn_qr = None

        self.lbl_web_url = ttk.Label(row_mfa, text=t("web_not_running"), style="Status.TLabel")
        self.lbl_web_url.pack(side=tk.LEFT, padx=10)

        # Mini LED compatti (indicatori piccoli inline)
        self.led_mini_frame = ttk.Frame(self.mfa_frame_widget)
        self.led_mini_frame.pack(fill=tk.X, pady=(8, 0))

        self.led_indicators = {}
        for i, led in enumerate(LEDS):
            cell = ttk.Frame(self.led_mini_frame)
            cell.pack(side=tk.LEFT, padx=4)

            canvas = tk.Canvas(cell, width=14, height=14, bg=CARD_BG, highlightthickness=0)
            canvas.pack(side=tk.LEFT, padx=(0, 2))
            dot = canvas.create_oval(1, 1, 13, 13, fill="#555555", outline="#333333")

            lbl = ttk.Label(cell, text=led.name, font=("Consolas", 7))
            lbl.pack(side=tk.LEFT)

            self.led_indicators[led.name] = (canvas, dot, led.color)

        # --- Debug Log (mostra dati ricevuti da TSW6) ---
        self.debug_frame_widget = ttk.LabelFrame(container, text=t("lf_debug_log"), padding=5)
        self.debug_frame_widget.pack(fill=tk.BOTH, expand=True)

        self.debug_text = tk.Text(self.debug_frame_widget, height=6, bg="#181825", fg="#a6adc8",
                                   font=("Consolas", 9), wrap=tk.WORD, state=tk.DISABLED,
                                   relief=tk.FLAT)
        debug_scroll = ttk.Scrollbar(self.debug_frame_widget, orient=tk.VERTICAL, command=self.debug_text.yview)
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
            self.lbl_arduino_status.config(text=t("log_found_port", port=auto_port), style="Warning.TLabel")

    def _on_simulator_changed(self):
        """Cambia simulatore: mostra/nascondi i frame di connessione appropriati."""
        sim = self.sim_type_var.get()
        self._simulator_type = sim

        self._repack_connection_frames()

        if sim == SimulatorType.TSW6:
            self.bridge_frame.config(text=t("lf_bridge_tsw6"))
            self.notebook.tab(self.tab_profiles, state="normal", text=t("tab_profile"))
        else:
            self.bridge_frame.config(text=t("lf_bridge_zusi3"))
            # Se siamo sul tab Profilo, torna a Connessione prima di disabilitarlo
            if self.notebook.select() == str(self.tab_profiles):
                self.notebook.select(self.tab_connect)
            self.notebook.tab(self.tab_profiles, state="disabled", text=t("tab_profile_na"))

        self._update_bridge_button()

    def _repack_connection_frames(self):
        """Rimette in ordine i frame di connessione in base al simulatore selezionato."""
        sim = self._simulator_type

        # Rimuovi i frame che cambiano
        self.tsw6_frame.pack_forget()
        self.zusi3_frame.pack_forget()

        # Rimetti il frame scelto subito dopo il selettore simulatore
        if sim == SimulatorType.TSW6:
            self.tsw6_frame.pack(fill=tk.X, pady=(0, 10), after=self.sim_frame)
        else:
            self.zusi3_frame.pack(fill=tk.X, pady=(0, 10), after=self.sim_frame)

    def _lock_simulator_selector(self):
        """Blocca il selettore simulatore quando un simulatore è connesso."""
        self.rb_tsw6.config(state=tk.DISABLED)
        self.rb_zusi3.config(state=tk.DISABLED)
        sim_name = "TSW6" if self._simulator_type == SimulatorType.TSW6 else "Zusi3"
        self.lbl_sim_locked.config(text=t("sim_locked", sim=sim_name))

    def _unlock_simulator_selector(self):
        """Sblocca il selettore simulatore quando nessun simulatore è connesso."""
        self.rb_tsw6.config(state=tk.NORMAL)
        self.rb_zusi3.config(state=tk.NORMAL)
        self.lbl_sim_locked.config(text="")

    # --------------------------------------------------------
    # Tab Profilo Treno
    # --------------------------------------------------------

    def _build_profiles_tab(self):
        container = ttk.Frame(self.tab_profiles)
        container.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        # --- Rilevamento treno ---
        self.detect_frame_widget = ttk.LabelFrame(container, text=t("lf_train_detect"), padding=10)
        self.detect_frame_widget.pack(fill=tk.X, pady=(0, 10))

        row_detect = ttk.Frame(self.detect_frame_widget)
        row_detect.pack(fill=tk.X)

        self.lbl_train_detected = ttk.Label(row_detect, text=t("train_detected"))
        self.lbl_train_detected.pack(side=tk.LEFT)
        self.detected_train_var = tk.StringVar(value=t("train_none"))
        ttk.Label(row_detect, textvariable=self.detected_train_var,
                  font=("Segoe UI", 10, "bold"), foreground=WARNING_COLOR,
                  background=CARD_BG).pack(side=tk.LEFT, padx=10)

        self.btn_detect_train = ttk.Button(row_detect, text=t("btn_detect_train"),
                                            command=self._detect_and_apply_train,
                                            style="Accent.TButton")
        self.btn_detect_train.pack(side=tk.RIGHT)

        # --- Selezione profilo ---
        self.select_frame_widget = ttk.LabelFrame(container, text=t("lf_active_profile"), padding=10)
        self.select_frame_widget.pack(fill=tk.X, pady=(0, 10))

        self.profile_radio_var = tk.StringVar(value="BR101")
        self._active_profile_id = "BR101"
        self._profile_radio_widgets = {}  # {pid: (radiobutton, desc_label)}

        for pid, info in TRAIN_PROFILES.items():
            row = ttk.Frame(self.select_frame_widget)
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

            desc_key = PROFILE_DESC_KEYS.get(pid)
            desc_text = t(desc_key) if desc_key else info.get("description", "")
            desc_lbl = ttk.Label(row, text=f"  {desc_text}",
                      font=("Segoe UI", 9, "italic"),
                      foreground="#6c7086")
            desc_lbl.pack(side=tk.LEFT)

            self._profile_radio_widgets[pid] = (rb, desc_lbl)

        row_apply = ttk.Frame(self.select_frame_widget)
        row_apply.pack(fill=tk.X, pady=(8, 0))
        self.btn_apply_profile = ttk.Button(row_apply, text=t("btn_apply_profile"),
                                             command=self._apply_selected_profile,
                                             style="Accent.TButton")
        self.btn_apply_profile.pack(side=tk.LEFT)

        self.lbl_profile_status = ttk.Label(row_apply, text="", font=("Segoe UI", 9))
        self.lbl_profile_status.pack(side=tk.LEFT, padx=15)

        # --- Visualizzazione mappature (sola lettura) ---
        self.mappings_frame_widget = ttk.LabelFrame(container, text=t("lf_mappings"), padding=5)
        self.mappings_frame_widget.pack(fill=tk.BOTH, expand=True)

        columns = ("name", "endpoint", "led", "action")
        self.profile_mapping_tree = ttk.Treeview(self.mappings_frame_widget, columns=columns,
                                                  show="headings", height=12)

        self.profile_mapping_tree.heading("name", text=t("col_name"))
        self.profile_mapping_tree.heading("endpoint", text=t("col_endpoint"))
        self.profile_mapping_tree.heading("led", text=t("col_led"))
        self.profile_mapping_tree.heading("action", text=t("col_action"))

        self.profile_mapping_tree.column("name", width=180)
        self.profile_mapping_tree.column("endpoint", width=400)
        self.profile_mapping_tree.column("led", width=120, anchor=tk.CENTER)
        self.profile_mapping_tree.column("action", width=100, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(self.mappings_frame_widget, orient=tk.VERTICAL,
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
            self._log(t("log_profile_not_found", pid=profile_id))
            return

        self._active_profile_id = profile_id
        self.current_profile = profile
        self.mappings = profile.get_mappings()
        self.profile_radio_var.set(profile_id)

        info = TRAIN_PROFILES.get(profile_id, {})
        self.lbl_profile_status.config(
            text=t("profile_active", name=info.get('name', profile_id), n=len(self.mappings)),
            style="Connected.TLabel"
        )
        self._refresh_profile_mapping_view()
        self._log(t("log_profile", name=info.get('name', profile_id)))

        # Se il bridge è attivo, avvisa che va riavviato
        if self.running:
            self._debug_log(t("profile_changed_restart"))

    def _detect_and_apply_train(self):
        """Rileva il treno e applica automaticamente il profilo corrispondente."""
        if not self.tsw6_api.is_connected():
            messagebox.showwarning(t("msgbox_warning"), t("msgbox_detect_first"))
            return

        self.detected_train_var.set(t("detecting"))
        self.root.update()

        def do_detect():
            object_class = self.tsw6_api.detect_train()
            self.root.after(0, lambda: self._on_train_detected(object_class))

        threading.Thread(target=do_detect, daemon=True).start()

    def _on_train_detected(self, object_class: Optional[str]):
        """Callback quando il treno è stato rilevato."""
        if not object_class:
            self.detected_train_var.set(t("train_not_detected"))
            self._log(t("log_train_not_detected"))
            return

        self.detected_train_var.set(object_class)
        profile_id = detect_profile_id(object_class)

        if profile_id:
            self._load_profile_by_id(profile_id)
            info = TRAIN_PROFILES[profile_id]
            self._debug_log(f"🚂 {object_class} → {info['name']}")
        else:
            self.lbl_profile_status.config(
                text=t("train_unknown", cls=object_class),
                style="Warning.TLabel"
            )
            self._debug_log(t("train_unknown_debug", cls=object_class))

    def _auto_detect_train_silent(self):
        """Rileva il treno in background senza messagebox. Chiamato dopo la connessione."""
        if not self.tsw6_api.is_connected():
            return

        def do_detect():
            object_class = self.tsw6_api.detect_train()
            self.root.after(0, lambda: self._on_train_detected(object_class))

        threading.Thread(target=do_detect, daemon=True).start()

    # --------------------------------------------------------
    # Footer
    # --------------------------------------------------------

    def _build_footer(self):
        footer = ttk.Frame(self.root)
        footer.pack(fill=tk.X, padx=10, pady=(0, 8))
        self.lbl_footer_status = ttk.Label(footer, text=t("ready"), font=("Segoe UI", 9))
        self.lbl_footer_status.pack(side=tk.LEFT)

    # --------------------------------------------------------
    # MFA Panel (popup + web server)
    # --------------------------------------------------------

    def _toggle_mfa_panel(self):
        """Apri/chiudi il pannello MFA popup."""
        if self._mfa_panel is None:
            self._mfa_panel = MFAPanelWindow(self.root)
        self._mfa_panel.toggle()

    def _toggle_web_server(self):
        """Avvia/ferma il web server per il pannello MFA su tablet."""
        if self._mfa_web_server.is_running:
            self._mfa_web_server.stop()
            self._remove_firewall_rule()
            self.btn_web_panel.config(text=t("btn_web_panel"))
            self.lbl_web_url.config(text=t("web_not_running"), style="Status.TLabel")
            self.spn_web_port.config(state="normal")
            if self.btn_qr:
                self.btn_qr.config(state=tk.DISABLED)
            self._close_qr_window()
            self._log(t("web_server_stopped"))
        else:
            # Leggi porta dal campo
            try:
                port = self._web_port_var.get()
                if port < 1024 or port > 65535:
                    raise ValueError
            except (ValueError, tk.TclError):
                port = 8080
                self._web_port_var.set(port)

            # Ricrea server con la porta scelta
            self._mfa_web_port = port
            self._mfa_web_server = MFAWebServer(port=port)

            if self._mfa_web_server.start():
                url = self._mfa_web_server.url
                self.btn_web_panel.config(text=t("btn_web_stop"))
                self.lbl_web_url.config(text=t("web_server_started", url=url), style="Connected.TLabel")
                self.spn_web_port.config(state="disabled")
                if self.btn_qr:
                    self.btn_qr.config(state=tk.NORMAL)
                self._log(t("web_server_started", url=url))
                self._debug_log(t("web_server_started", url=url))
                # Firewall
                self._add_firewall_rule(port)
            else:
                self.lbl_web_url.config(
                    text=t("web_server_error", port=self._mfa_web_server.port),
                    style="Disconnected.TLabel"
                )

    # --------------------------------------------------------
    # QR Code
    # --------------------------------------------------------

    def _show_qr_code(self):
        """Mostra una finestra popup con il QR code dell'URL del web server."""
        if not _HAS_QRCODE or not self._mfa_web_server.is_running:
            return

        # Se già aperto, portalo in primo piano
        if self._qr_window and self._qr_window.winfo_exists():
            self._qr_window.lift()
            self._qr_window.focus_force()
            return

        url = self._mfa_web_server.url

        # Genera QR code come lista di righe booleane
        qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M,
                            box_size=1, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        matrix = qr.get_matrix()  # lista di liste di bool

        # Dimensioni
        rows = len(matrix)
        cols = len(matrix[0]) if rows > 0 else 0
        px = 6  # pixel per modulo QR
        qr_w = cols * px
        qr_h = rows * px

        # Crea finestra
        win = tk.Toplevel(self.root)
        win.title(t("qr_title"))
        win.configure(bg="white")
        win.resizable(False, False)

        # Icona
        import os, sys
        icon_path = os.path.join(
            getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__))),
            "tsw6_bridge.ico"
        )
        if os.path.exists(icon_path):
            try:
                win.iconbitmap(icon_path)
            except Exception:
                pass

        # Titolo
        tk.Label(win, text=t("qr_title"), font=("Segoe UI", 11, "bold"),
                 bg="white", fg="#333").pack(padx=20, pady=(12, 4))

        # URL
        tk.Label(win, text=url, font=("Consolas", 12, "bold"),
                 bg="white", fg="#0066CC").pack(padx=20, pady=(0, 8))

        # Canvas QR
        canvas = tk.Canvas(win, width=qr_w, height=qr_h, bg="white",
                           highlightthickness=0)
        canvas.pack(padx=20, pady=(0, 16))

        # Disegna moduli QR
        for r, row in enumerate(matrix):
            for c, cell in enumerate(row):
                if cell:
                    x0 = c * px
                    y0 = r * px
                    canvas.create_rectangle(x0, y0, x0 + px, y0 + px,
                                            fill="black", outline="black")

        win.protocol("WM_DELETE_WINDOW", lambda: self._close_qr_window())
        self._qr_window = win

    def _close_qr_window(self):
        """Chiudi la finestra QR code."""
        if self._qr_window:
            try:
                self._qr_window.destroy()
            except Exception:
                pass
            self._qr_window = None

    # --------------------------------------------------------
    # Windows Firewall
    # --------------------------------------------------------

    def _add_firewall_rule(self, port: int):
        """Aggiunge una regola Windows Firewall per permettere connessioni in ingresso."""
        try:
            # Rimuovi regola esistente (se presente da sessione precedente)
            subprocess.run(
                ["netsh", "advfirewall", "firewall", "delete", "rule",
                 f"name={self._firewall_rule_name}"],
                capture_output=True, creationflags=0x08000000  # CREATE_NO_WINDOW
            )
            # Aggiungi regola
            result = subprocess.run(
                ["netsh", "advfirewall", "firewall", "add", "rule",
                 f"name={self._firewall_rule_name}",
                 "dir=in", "action=allow", "protocol=TCP",
                 f"localport={port}",
                 "profile=private,domain",
                 "description=Train Simulator Bridge MFA Web Panel"],
                capture_output=True, text=True,
                creationflags=0x08000000  # CREATE_NO_WINDOW
            )
            if result.returncode == 0:
                self._debug_log(t("firewall_ok", port=port))
            else:
                self._debug_log(t("firewall_fail", port=port))
        except Exception:
            self._debug_log(t("firewall_fail", port=port))

    def _remove_firewall_rule(self):
        """Rimuove la regola firewall all'arresto del web server."""
        try:
            subprocess.run(
                ["netsh", "advfirewall", "firewall", "delete", "rule",
                 f"name={self._firewall_rule_name}"],
                capture_output=True, creationflags=0x08000000  # CREATE_NO_WINDOW
            )
        except Exception:
            pass

    def _push_led_state(self):
        """Invia lo stato corrente dei LED al LEDStateManager (per popup + web)."""
        self._led_state_mgr.update(self._gui_led_states, self._gui_led_blink)

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
            self._log(t("log_apikey_found", n=len(key)))
        else:
            self._log(t("log_apikey_not_found"))

    def _connect_tsw6(self):
        host = self.tsw6_host_var.get().strip()
        port = int(self.tsw6_port_var.get().strip())
        api_key = self.tsw6_apikey_var.get().strip() or None

        if not api_key:
            messagebox.showwarning(t("msgbox_apikey_title"), t("msgbox_apikey_empty"))
            return

        self.tsw6_api = TSW6API(host=host, port=port, api_key=api_key)
        self.lbl_tsw6_status.config(text=t("status_connecting"), style="Warning.TLabel")
        self.root.update()

        def do_connect():
            try:
                success = self.tsw6_api.connect(api_key=api_key)
                self.root.after(0, lambda: self._on_tsw6_connected(success))
            except TSW6AuthError as e:
                self.root.after(0, lambda: self._on_tsw6_error(t("err_apikey", e=e)))
            except TSW6ConnectionError as e:
                self.root.after(0, lambda: self._on_tsw6_error(t("err_connection", e=e)))
            except Exception as e:
                self.root.after(0, lambda: self._on_tsw6_error(str(e)))

        threading.Thread(target=do_connect, daemon=True).start()

    def _on_tsw6_connected(self, success):
        if success:
            self.lbl_tsw6_status.config(text=t("status_connected"), style="Connected.TLabel")
            self.btn_tsw6_connect.config(state=tk.DISABLED)
            self.btn_tsw6_disconnect.config(state=tk.NORMAL)
            self._lock_simulator_selector()
            self._update_bridge_button()
            self._log(t("log_connected_tsw6"))
            # Auto-detect treno
            self._auto_detect_train_silent()
        else:
            self.lbl_tsw6_status.config(text=t("status_failed"), style="Disconnected.TLabel")

    def _on_tsw6_error(self, msg):
        self.lbl_tsw6_status.config(text=t("status_error"), style="Disconnected.TLabel")
        messagebox.showerror(t("msgbox_error_tsw6"), msg)

    def _disconnect_tsw6(self):
        self._stop_bridge()
        self.tsw6_api.disconnect()
        self.lbl_tsw6_status.config(text=t("status_disconnected"), style="Disconnected.TLabel")
        self.btn_tsw6_connect.config(state=tk.NORMAL)
        self.btn_tsw6_disconnect.config(state=tk.DISABLED)
        self._unlock_simulator_selector()
        self._update_bridge_button()
        self._log(t("log_disconnected_tsw6"))

    # --------------------------------------------------------
    # Connessione Zusi3
    # --------------------------------------------------------

    def _connect_zusi3(self):
        host = self.zusi3_host_var.get().strip()
        port = int(self.zusi3_port_var.get().strip())

        self.lbl_zusi3_status.config(text=t("status_connecting"), style="Warning.TLabel")
        self.root.update()

        def do_connect():
            try:
                self.zusi3_client = Zusi3Client(host, port)
                self.zusi3_client.on_state_update = self._on_zusi3_train_update
                self.zusi3_client.on_connect = lambda: self.root.after(0, self._on_zusi3_connect_cb)
                self.zusi3_client.on_disconnect = lambda: self.root.after(0, self._on_zusi3_disconnect_cb)

                success = self.zusi3_client.connect("TrainSimBridge")
                self.root.after(0, lambda: self._on_zusi3_connected(success))
            except Exception as e:
                self.root.after(0, lambda: self._on_zusi3_error(str(e)))

        threading.Thread(target=do_connect, daemon=True).start()

    def _on_zusi3_connected(self, success):
        if success:
            self.lbl_zusi3_status.config(text=t("status_connected"), style="Connected.TLabel")
            self.btn_zusi3_connect.config(state=tk.DISABLED)
            self.btn_zusi3_disconnect.config(state=tk.NORMAL)
            self._lock_simulator_selector()
            self._update_bridge_button()
            self._log(t("log_connected_zusi3"))
            self._debug_log(t("dbg_zusi3_connected", host=self.zusi3_host_var.get(), port=self.zusi3_port_var.get()))
        else:
            self.lbl_zusi3_status.config(text=t("status_failed"), style="Disconnected.TLabel")
            self._debug_log(t("dbg_zusi3_conn_fail"))

    def _on_zusi3_error(self, msg):
        self.lbl_zusi3_status.config(text=t("status_error"), style="Disconnected.TLabel")
        messagebox.showerror(t("msgbox_error_zusi3"), msg)

    def _on_zusi3_connect_cb(self):
        self.lbl_zusi3_status.config(text=t("status_connected"), style="Connected.TLabel")
        self._debug_log(t("dbg_zusi3_connected_short"))

    def _on_zusi3_disconnect_cb(self):
        self.lbl_zusi3_status.config(text=t("status_disconnected"), style="Disconnected.TLabel")
        self._debug_log(t("dbg_zusi3_disconnected"))
        # Auto-stop bridge se Zusi3 si disconnette
        if self.running and self._simulator_type == SimulatorType.ZUSI3:
            self._stop_bridge()

    def _disconnect_zusi3(self):
        self._stop_bridge()
        if self.zusi3_client:
            self.zusi3_client.disconnect()
            self.zusi3_client = None
        self.lbl_zusi3_status.config(text=t("status_disconnected"), style="Disconnected.TLabel")
        self.btn_zusi3_connect.config(state=tk.NORMAL)
        self.btn_zusi3_disconnect.config(state=tk.DISABLED)
        self._unlock_simulator_selector()
        self._update_bridge_button()
        self._log(t("log_disconnected_zusi3"))

    # --------------------------------------------------------
    # Connessione Arduino
    # --------------------------------------------------------

    def _connect_arduino(self):
        port_selection = self.arduino_port_var.get()
        port = None if port_selection == "Auto-detect" else port_selection.split(" - ")[0].strip()

        self.lbl_arduino_status.config(text=t("status_connecting"), style="Warning.TLabel")
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
            self._log(t("log_arduino_port", port=self.arduino.port_name))
        else:
            self.lbl_arduino_status.config(text=t("status_failed"), style="Disconnected.TLabel")

    def _on_arduino_error(self, msg):
        self.lbl_arduino_status.config(text=t("status_error"), style="Disconnected.TLabel")
        messagebox.showerror(t("msgbox_error_arduino"), msg)

    def _disconnect_arduino(self):
        self._stop_bridge()
        self.arduino.disconnect()
        self.lbl_arduino_status.config(text=t("status_disconnected"), style="Disconnected.TLabel")
        self.btn_arduino_connect.config(state=tk.NORMAL)
        self.btn_arduino_disconnect.config(state=tk.DISABLED)
        self._update_bridge_button()
        self._log(t("log_arduino_disconnected"))

    def _test_arduino_leds(self):
        if not self.arduino.is_connected():
            messagebox.showwarning(t("msgbox_warning"), t("msgbox_arduino_not_connected"))
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
            self.root.after(0, lambda: self._log(t("log_test_done")))

        threading.Thread(target=do_test, daemon=True).start()
        self._log(t("log_test_leds"))

    def _all_leds_off(self):
        if self.arduino.is_connected():
            self.arduino.all_off()
            self._log(t("log_leds_off"))

    def _update_bridge_button(self):
        sim = self._simulator_type

        if sim == SimulatorType.TSW6:
            sim_connected = self.tsw6_api.is_connected()
            sim_label = "TSW6"
        else:
            sim_connected = self.zusi3_client is not None and self.zusi3_client.connected
            sim_label = "Zusi3"

        if sim_connected:
            self.btn_start.config(state=tk.NORMAL)
            if self.arduino.is_connected():
                self.lbl_bridge_status.config(text=t("bridge_ready", sim=sim_label), style="Warning.TLabel")
            else:
                self.lbl_bridge_status.config(text=t("bridge_ready_gui", sim=sim_label), style="Warning.TLabel")
        else:
            self.btn_start.config(state=tk.DISABLED)
            self.lbl_bridge_status.config(text=t("bridge_wait_sim", sim=sim_label), style="Status.TLabel")

    # --------------------------------------------------------
    # Bridge
    # --------------------------------------------------------

    def _start_bridge(self):
        if self.running:
            return

        if self._simulator_type == SimulatorType.ZUSI3:
            self._start_bridge_zusi3()
        else:
            self._start_bridge_tsw6()

    def _start_bridge_tsw6(self):
        """Avvia il bridge in modalità TSW6."""
        if not self.tsw6_api.is_connected():
            messagebox.showwarning(t("msgbox_warning"), t("msgbox_connect_tsw6"))
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
            messagebox.showwarning(t("msgbox_warning"), t("msgbox_no_mappings"))
            return

        self.lbl_bridge_status.config(text=t("bridge_starting"), style="Warning.TLabel")
        self.btn_start.config(state=tk.DISABLED)
        self.root.update()
        
        # Log endpoint nel debug panel
        self._debug_log(t("dbg_bridge_tsw6_start", n=len(endpoints)))
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
        self.lbl_bridge_status.config(text=t("bridge_active"), style="Connected.TLabel")
        if self._simulator_type == SimulatorType.TSW6:
            mode = "Subscription" if self.poller._subscription_active else "GET"
            self._log(t("log_bridge_tsw6_started", n=len(endpoints), mode=mode))
            self._debug_log(t("dbg_bridge_tsw6_active", mode=mode, ms=f"{self.poller.interval*1000:.0f}"))
        else:
            self._log(t("log_bridge_zusi3_started"))
            self._debug_log(t("dbg_bridge_zusi3_active"))
        self._update_led_indicators()

    def _on_bridge_start_failed(self):
        self.btn_start.config(state=tk.NORMAL)
        self.lbl_bridge_status.config(text=t("bridge_start_failed"), style="Disconnected.TLabel")
        self._debug_log(t("dbg_bridge_start_fail"))
        messagebox.showerror(t("msgbox_error_bridge"), t("msgbox_bridge_fail"))

    def _on_bridge_message(self, msg):
        self._log(msg)
        self._debug_log(msg)
        # Se il bridge si è fermato da solo, aggiorna UI
        if self.poller and not self.poller._running and self.running:
            self.running = False
            self.btn_start.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)
        self.lbl_bridge_status.config(text=t("status_disconnected"), style="Disconnected.TLabel")

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
        self.lbl_bridge_status.config(text=t("bridge_stopped"), style="Status.TLabel")
        self._log(t("log_bridge_stopped"))
        self._debug_log(t("log_bridge_stopped"))

        # Reset contatori diagnostici per prossimo avvio
        self._on_tsw6_data_count = 0
        self._led_update_count = 0
        self._gui_led_states.clear()
        self._gui_led_blink.clear()

    # --------------------------------------------------------
    # Bridge Zusi3
    # --------------------------------------------------------

    def _start_bridge_zusi3(self):
        """Avvia il bridge in modalità Zusi3."""
        if not self.zusi3_client or not self.zusi3_client.connected:
            messagebox.showwarning(t("msgbox_warning"), t("msgbox_connect_zusi3"))
            return

        self.lbl_bridge_status.config(text=t("bridge_starting"), style="Warning.TLabel")
        self.btn_start.config(state=tk.DISABLED)
        self.root.update()

        self._debug_log(t("dbg_zusi3_bridge_start"))

        # Il Zusi3Client ha già un thread di ricezione che chiama on_state_update.
        # Basta marcare il bridge come attivo e avviare il timer blink + indicatori.
        self.running = True
        self.btn_stop.config(state=tk.NORMAL)
        self.lbl_bridge_status.config(text=t("bridge_active"), style="Connected.TLabel")
        self._log(t("log_bridge_zusi3_started"))
        self._debug_log(t("dbg_bridge_zusi3_active"))
        self._update_led_indicators()
        self._start_zusi3_blink_timer()

    def _start_zusi3_blink_timer(self):
        """Timer per lampeggio LED Zusi3 (500ms per toggle = 1s cycle)."""
        if not self.running or self._simulator_type != SimulatorType.ZUSI3:
            return
        self._zusi3_blink_visible = not self._zusi3_blink_visible
        self._update_zusi3_blink_leds()
        self.root.after(500, self._start_zusi3_blink_timer)

    def _update_zusi3_blink_leds(self):
        """Aggiorna LED che devono lampeggiare in modalità Zusi3."""
        if not self.running or self._simulator_type != SimulatorType.ZUSI3:
            return
        if not self.zusi3_client:
            return

        state = self.zusi3_client.state

        # LED con supporto lampeggio (valore >= 2)
        blink_map = [
            (state.pzb.zugart_55, "PZB55"),
            (state.pzb.zugart_70, "PZB70"),
            (state.pzb.zugart_85, "PZB85"),
            (state.pzb.lm_1000hz, "1000HZ"),
            (state.pzb.lm_500hz, "500HZ"),
            (state.lzb.lm_ende, "LZB"),
            (state.lzb.lm_ue, "LZB_UE"),
            (state.lzb.lm_g, "LZB_G"),
            (state.lzb.lm_s, "LZB_S"),
        ]

        for value, led_name in blink_map:
            if value >= 2:
                # 2=BLINKEND, 3=BLINKEND_INVERS
                vis = self._zusi3_blink_visible if value == 2 else not self._zusi3_blink_visible
                if self.arduino.is_connected():
                    self.arduino.set_led(led_name, vis)
                self._gui_led_states[led_name] = vis

    def _on_zusi3_train_update(self, state: TrainState):
        """Callback: dati ricevuti da Zusi3. Mappa TrainState → LED."""
        if not self.running or self._simulator_type != SimulatorType.ZUSI3:
            return

        # LED1: SIFA
        sifa_on = state.sifa.hupe_warning or state.sifa.hupe_zwang or state.sifa.licht
        self._gui_led_states["SIFA"] = sifa_on
        if self.arduino.is_connected():
            self.arduino.set_led("SIFA", sifa_on)

        # LED2: LZB Ende (solo se non lampeggia — il timer gestisce il blink)
        if state.lzb.lm_ende < 2:
            ende_on = state.lzb.lm_ende > 0
            self._gui_led_states["LZB"] = ende_on
            if self.arduino.is_connected():
                self.arduino.set_led("LZB", ende_on)

        # LED3: PZB 70
        if state.pzb.zugart_70 < 2:
            pzb70_on = state.pzb.zugart_70 > 0
            self._gui_led_states["PZB70"] = pzb70_on
            if self.arduino.is_connected():
                self.arduino.set_led("PZB70", pzb70_on)

        # LED4: PZB 85
        if state.pzb.zugart_85 < 2:
            pzb80_on = state.pzb.zugart_85 > 0
            self._gui_led_states["PZB85"] = pzb80_on
            if self.arduino.is_connected():
                self.arduino.set_led("PZB85", pzb80_on)

        # LED5: PZB 55
        if state.pzb.zugart_55 < 2:
            pzb50_on = state.pzb.zugart_55 > 0
            self._gui_led_states["PZB55"] = pzb50_on
            if self.arduino.is_connected():
                self.arduino.set_led("PZB55", pzb50_on)

        # LED6: 500Hz
        if state.pzb.lm_500hz < 2:
            hz500_on = state.pzb.lm_500hz > 0
            self._gui_led_states["500HZ"] = hz500_on
            if self.arduino.is_connected():
                self.arduino.set_led("500HZ", hz500_on)

        # LED7: 1000Hz
        if state.pzb.lm_1000hz < 2:
            hz1000_on = state.pzb.lm_1000hz > 0
            self._gui_led_states["1000HZ"] = hz1000_on
            if self.arduino.is_connected():
                self.arduino.set_led("1000HZ", hz1000_on)

        # LED8: Porte SX
        self._gui_led_states["TUEREN_L"] = state.doors_left
        if self.arduino.is_connected():
            self.arduino.set_led("TUEREN_L", state.doors_left)

        # LED9: Porte DX
        self._gui_led_states["TUEREN_R"] = state.doors_right
        if self.arduino.is_connected():
            self.arduino.set_led("TUEREN_R", state.doors_right)

        # LED10: LZB Ü
        if state.lzb.lm_ue < 2:
            lzb_ue_on = state.lzb.lm_ue > 0
            self._gui_led_states["LZB_UE"] = lzb_ue_on
            if self.arduino.is_connected():
                self.arduino.set_led("LZB_UE", lzb_ue_on)

        # LED11: LZB G
        if state.lzb.lm_g < 2:
            lzb_g_on = state.lzb.lm_g > 0
            self._gui_led_states["LZB_G"] = lzb_g_on
            if self.arduino.is_connected():
                self.arduino.set_led("LZB_G", lzb_g_on)

        # LED12: LZB S
        if state.lzb.lm_s < 2:
            lzb_s_on = state.lzb.lm_s > 0
            self._gui_led_states["LZB_S"] = lzb_s_on
            if self.arduino.is_connected():
                self.arduino.set_led("LZB_S", lzb_s_on)

        # LED13: Befehl 40
        bef40_on = state.pzb.lm_befehl
        self._gui_led_states["BEF40"] = bef40_on
        if self.arduino.is_connected():
            self.arduino.set_led("BEF40", bef40_on)

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

        # Push stato al LEDStateManager (per popup MFA + web server)
        self._push_led_state()

        # Quando PZB70 e PZB85 lampeggiano entrambi, sfasa PZB85 di mezzo periodo
        pzb70_blink = (self._gui_led_states.get("PZB70", False)
                       and self._gui_led_blink.get("PZB70", 0.0) > 0)
        pzb85_blink = (self._gui_led_states.get("PZB85", False)
                       and self._gui_led_blink.get("PZB85", 0.0) > 0)
        both_pzb_blink = pzb70_blink and pzb85_blink

        # Aggiorna cerchietti mini usando _gui_led_blink (intervallo in secondi)
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
            self._log(t("log_profile_saved", pid=profile_id))
        else:
            self._log(t("log_no_profile"))

    def _load_profile(self):
        """Non più necessario — i profili sono fissi e selezionati dalla tab Profilo."""
        pass

    def _load_last_config(self):
        """Carica l'ultimo profilo e simulatore usati dall'app config."""
        config = self.config_mgr.load_app_config()

        # Simulatore
        last_sim = config.get("last_simulator", SimulatorType.TSW6)
        if last_sim in (SimulatorType.TSW6, SimulatorType.ZUSI3):
            self._simulator_type = last_sim
            self.sim_type_var.set(last_sim)
            self._on_simulator_changed()

        # Profilo TSW6
        last_id = config.get("last_profile_id", "")
        if last_id and last_id in TRAIN_PROFILES:
            self._load_profile_by_id(last_id)
        else:
            # Primo avvio: carica BR101 come default
            self._load_profile_by_id("BR101")

        # Porta web server
        saved_port = config.get("web_port", 8080)
        try:
            saved_port = int(saved_port)
            if saved_port < 1024 or saved_port > 65535:
                saved_port = 8080
        except (ValueError, TypeError):
            saved_port = 8080
        self._mfa_web_port = saved_port
        self._web_port_var.set(saved_port)
        self._mfa_web_server = MFAWebServer(port=saved_port)

    def _save_last_config(self):
        """Salva l'ID del profilo attivo, simulatore, lingua e porta web."""
        profile_id = getattr(self, '_active_profile_id', 'BR101')
        self.config_mgr.save_app_config({
            "last_profile_id": profile_id,
            "last_simulator": self._simulator_type,
            "language": get_language(),
            "web_port": self._mfa_web_port,
        })

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
        # Chiudi QR window, MFA panel e web server
        self._close_qr_window()
        if self._mfa_panel and self._mfa_panel.is_open:
            self._mfa_panel.close()
        if self._mfa_web_server.is_running:
            self._mfa_web_server.stop()
            self._remove_firewall_rule()
        if self.arduino.is_connected():
            self.arduino.disconnect()
        if self.tsw6_api.is_connected():
            self.tsw6_api.disconnect()
        if self.zusi3_client and self.zusi3_client.connected:
            self.zusi3_client.disconnect()
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
