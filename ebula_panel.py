"""
EBuLa Panel — Train Simulator Bridge
=====================================
Elektronischer Buchfahrplan (EBuLa) display replicating the real
German railway electronic timetable screen.

Shows live data from TSW6 API:
  Col 1 — Speed profile (Geschwindigkeitsprofil) step graph
  Col 2 — Train position with prism/diamond marker on track line
  Col 3 — Distance markers (km)
  Col 4 — Stations, signals, tunnels

Header: train number | route name | date | game clock

Two themes: Light (realistic day) and Dark (night mode).
Right-click on the panel to toggle theme.
"""

import tkinter as tk
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger("EBuLa")

# ============================================================
# Themes — matched to real EBuLa displays
# ============================================================

THEMES = {
    "light": {
        "bg":               "#C8C8C8",
        "header_bg":        "#707070",
        "header_fg":        "#FFFFFF",
        "subheader_bg":     "#B8B8B0",
        "subheader_fg":     "#000000",
        "text":             "#000000",
        "text_dim":         "#555555",
        "text_station":     "#000000",
        "grid_line":        "#AAAAAA",
        "col_sep":          "#888888",
        "speed_fill":       "#707070",
        "speed_outline":    "#FFFFFF",
        "speed_text":       "#000000",
        "track_line":       "#555555",
        "diamond_fill":     "#404040",
        "diamond_outline":  "#000000",
        "station_line":     "#666666",
        "signal_color":     "#444444",
        "tunnel_fill":      "#A0A098",
        "bottom_bg":        "#A0A098",
        "bottom_fg":        "#000000",
        "btn_bg":           "#B0B0A8",
        "btn_fg":           "#000000",
        "btn_border":       "#808080",
        "border":           "#606060",
        "distance_text":    "#333333",
    },
    "dark": {
        "bg":               "#1A1A1E",
        "header_bg":        "#2A2A30",
        "header_fg":        "#E0E0E0",
        "subheader_bg":     "#222228",
        "subheader_fg":     "#C0C0C0",
        "text":             "#D0D0D0",
        "text_dim":         "#707070",
        "text_station":     "#FFFFFF",
        "grid_line":        "#2E2E34",
        "col_sep":          "#3A3A40",
        "speed_fill":       "#48484E",
        "speed_outline":    "#FFFFFF",
        "speed_text":       "#D0D0D0",
        "track_line":       "#70707A",
        "diamond_fill":     "#C0C0C0",
        "diamond_outline":  "#FFFFFF",
        "station_line":     "#50505A",
        "signal_color":     "#9090A0",
        "tunnel_fill":      "#30303A",
        "bottom_bg":        "#252530",
        "bottom_fg":        "#B0B0B0",
        "btn_bg":           "#333340",
        "btn_fg":           "#A0A0A0",
        "btn_border":       "#50505A",
        "border":           "#3A3A40",
        "distance_text":    "#909090",
    },
}


# ============================================================
# Signal aspect names (DB Ks-signal system)
# ============================================================

SIGNAL_ASPECT_NAMES = {
    "Clear":        "Ks 1",
    "Caution":      "Ks 2",
    "Stop":         "Hp 0",
    "Shunting":     "Sh 1",
    "Permissive":   "Vorsig",
}

# Signal type labels based on sequential index
# 0=Asig (main), 1+=Bk (block signal)
SIGNAL_TYPE_LABELS = ["Asig", "Bk", "Bk", "Bk", "Bk", "Bk", "Bk", "Bk"]


# ============================================================
# Data containers
# ============================================================

@dataclass
class SpeedLimit:
    """A speed limit at a given distance ahead."""
    distance_km: float
    speed_kmh: float


@dataclass
class Station:
    """A station ahead on the route."""
    distance_km: float
    name: str


@dataclass
class Signal:
    """A signal ahead on the route."""
    distance_km: float
    name: str = ""
    aspect: int = 0


@dataclass
class Tunnel:
    """A tunnel section detected in track heights."""
    distance_km: float


@dataclass
class EBuLaData:
    """All data needed for the EBuLa display."""
    train_number: str = ""
    route_name: str = ""
    date_str: str = ""
    time_str: str = ""

    current_speed_limit_kmh: float = 0.0
    max_speed_kmh: float = 200.0
    next_stop: str = ""
    gradient: float = 0.0

    speed_limits: List[SpeedLimit] = field(default_factory=list)
    stations: List[Station] = field(default_factory=list)
    signals: List[Signal] = field(default_factory=list)
    tunnels: List[Tunnel] = field(default_factory=list)


# ============================================================
# Layout constants
# ============================================================

EBULA_W = 720
EBULA_H = 540

HEADER_H = 34
SUBHEADER_H = 20
BOTTOM_H = 50

MAIN_TOP = HEADER_H + SUBHEADER_H
MAIN_BOT = EBULA_H - BOTTOM_H
MAIN_H = MAIN_BOT - MAIN_TOP

# Column boundaries (x coordinates)
COL_SPEED_R = 110         # Speed profile: 0 → 110
COL_TRACK_L = 110         # Track line starts
COL_TRACK_R = 145         # Track line ends
COL_DIST_L = 145          # Distance column
COL_DIST_R = 195          # Distance column ends
COL_INFO_L = 195          # Route info starts
COL_INFO_R = EBULA_W      # Route info ends

# Speed column left margin (for speed labels)
SPEED_MARGIN_L = 30

# Diamond position — fixed at ~80% from top of main area
DIAMOND_Y = MAIN_TOP + int(MAIN_H * 0.80)

# View range (km shown ahead/behind train)
# VIEW_AHEAD_KM is a minimum; actual range adapts to fill the display
VIEW_AHEAD_KM = 5.0
VIEW_AHEAD_MAX_KM = 50.0   # accept all events up to 50 km from API
VIEW_BEHIND_KM = 0.8

# Font configuration
FONT_FAMILY = "Consolas"
FONT_HEADER = (FONT_FAMILY, 11, "bold")
FONT_HEADER_SM = (FONT_FAMILY, 9)
FONT_SUBHEADER = (FONT_FAMILY, 8)
FONT_SPEED = (FONT_FAMILY, 10, "bold")
FONT_DISTANCE = (FONT_FAMILY, 8)
FONT_STATION = (FONT_FAMILY, 10, "bold")
FONT_SIGNAL = (FONT_FAMILY, 9)
FONT_BOTTOM = (FONT_FAMILY, 8)
FONT_BTN = (FONT_FAMILY, 8)

# Fixed row height for signal/station rows
ROW_H = 22


# ============================================================
# API data parser
# ============================================================

def parse_api_to_ebula(
    driver_aid_data: Optional[dict],
    track_data: Optional[dict],
    player_info: Optional[dict],
    time_data: Optional[dict],
) -> EBuLaData:
    """
    Parse raw TSW6 API responses into an EBuLaData object.

    Args:
        driver_aid_data: Response from api.get_driver_aid_data()
        track_data:      Response from api.get_track_data()
        player_info:     Response from api.get_player_info()
        time_data:       Response from api.get_time_of_day()

    Returns:
        Populated EBuLaData ready for display.
    """
    data = EBuLaData()

    # -- PlayerInfo --
    if player_info:
        v = _extract_value(player_info)
        if isinstance(v, dict):
            data.route_name = v.get("currentServiceName", "")
        elif isinstance(v, str):
            data.route_name = v

    # Parse train_number from service name (e.g. "RE1-26813" → "26813")
    if data.route_name and "-" in data.route_name:
        parts = data.route_name.split("-")
        data.train_number = parts[-1].strip()
    elif data.route_name:
        data.train_number = data.route_name

    # -- TimeOfDay --
    if time_data:
        v = _extract_value(time_data)
        if isinstance(v, dict):
            iso = v.get("LocalTimeISO8601", "")
        elif isinstance(v, str):
            iso = v
        else:
            iso = ""
        if iso:
            try:
                dt = datetime.fromisoformat(iso)
                data.date_str = dt.strftime("%d.%m.%Y")
                data.time_str = dt.strftime("%H:%M:%S")
            except (ValueError, TypeError):
                pass

    # -- DriverAid.Data --
    # Real API format:
    #   speedLimit: {"value": 11.11}          (m/s wrapped in dict)
    #   serviceMaxSpeed: {"value": 44.44}     (m/s wrapped in dict)
    #   gradient: 0                           (plain int/float)
    #   nextSpeedLimits: [{"value": {"value": 27.78}, "distanceToNextSpeedLimit": 55652, ...}]
    #   nextSignals: [{"value": "Clear", "distanceToNextSignal": 4645, ...}]
    if driver_aid_data:
        v = _extract_value(driver_aid_data)
        if isinstance(v, dict):
            data.current_speed_limit_kmh = _unwrap_value(v.get("speedLimit", 0)) * 3.6
            data.max_speed_kmh = max(_unwrap_value(v.get("serviceMaxSpeed", 0)) * 3.6, 80)
            data.gradient = v.get("gradient", 0)

            for sl in v.get("nextSpeedLimits", []):
                dist_cm = sl.get("distanceToNextSpeedLimit", 0)
                speed_ms = _unwrap_value(sl.get("value", 0))
                dist_km = dist_cm / 100_000  # cm → km
                speed_kmh = speed_ms * 3.6   # m/s → km/h
                if dist_km >= 0:
                    data.speed_limits.append(SpeedLimit(dist_km, speed_kmh))

            raw_signals = v.get("nextSignals", [])
            for idx, sig in enumerate(raw_signals):
                dist_cm = sig.get("distanceToNextSignal", 0)
                dist_km = dist_cm / 100_000
                # Use signal type label (Asig, Bk) based on position in list
                name = SIGNAL_TYPE_LABELS[idx] if idx < len(SIGNAL_TYPE_LABELS) else "Bk"
                if dist_km >= 0:
                    data.signals.append(Signal(dist_km, name, 0))

    # -- DriverAid.TrackData --
    # Real API format:
    #   stations: [{"stationName": "...", "distanceToStationCM": 4244, ...}]
    #   trackHeights: [{"distanceToHeight": 14505, "bTunnelFound": false, ...}]
    if track_data:
        v = _extract_value(track_data)
        if isinstance(v, dict):
            for st in v.get("stations", []):
                name = st.get("stationName", "")
                dist_cm = st.get("distanceToStationCM", 0)
                dist_km = dist_cm / 100_000
                if name and dist_km >= 0:
                    data.stations.append(Station(dist_km, name))

            # Tunnels from trackHeights
            for th in v.get("trackHeights", []):
                if th.get("bTunnelFound", False):
                    dist_cm = th.get("distanceToHeight", 0)
                    dist_km = dist_cm / 100_000
                    data.tunnels.append(Tunnel(dist_km))

    # Sort everything by distance
    data.speed_limits.sort(key=lambda s: s.distance_km)
    data.stations.sort(key=lambda s: s.distance_km)
    data.signals.sort(key=lambda s: s.distance_km)
    data.tunnels.sort(key=lambda s: s.distance_km)

    # Next stop = nearest station with distance > 0
    for st in data.stations:
        if st.distance_km > 0.01 and st.name:
            data.next_stop = st.name
            break

    return data


def _extract_value(response: dict):
    """Extract the inner value from a TSW6 API response.

    For compound endpoints (DriverAid.Data, PlayerInfo, TimeOfDay.Data, TrackData),
    Values is a flat dict with many keys — return it as-is.
    For simple endpoints (Property.X), Values is {"PropertyName": value} — unwrap.
    """
    if not isinstance(response, dict):
        return response
    vals = response.get("Values", {})
    if isinstance(vals, dict):
        if len(vals) == 1:
            # Single-value wrapper: unwrap (e.g. {"Value": 42})
            return list(vals.values())[0]
        # Multi-key dict: return as-is (e.g. DriverAid.Data with 20 fields)
        return vals
    return vals


def _unwrap_value(val):
    """Unwrap a TSW6 value that may be wrapped in {"value": X} or plain."""
    if isinstance(val, dict):
        inner = val.get("value", 0)
        # Double-wrap: {"value": {"value": 27.78}}
        if isinstance(inner, dict):
            return inner.get("value", 0)
        return inner
    if isinstance(val, (int, float)):
        return val
    return 0


# ============================================================
# EBuLa Panel Window
# ============================================================

class EBuLaPanel(tk.Toplevel):
    """
    EBuLa display window — Elektronischer Buchfahrplan.

    Opens as a separate Toplevel window. Toggle visibility with toggle().
    Update data with update_data(ebula_data).
    Right-click to switch theme.
    """

    def __init__(self, parent, theme: str = "dark"):
        super().__init__(parent)
        self.title("EBuLa — Elektronischer Buchfahrplan")
        self.geometry(f"{EBULA_W}x{EBULA_H}")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._theme_name = theme
        self._theme = THEMES[theme]
        self._data = EBuLaData()
        self._visible = False

        # Cumulative km odometer — tracks distance traveled from start
        self._km_traveled: float = 0.0
        self._prev_stations: dict[str, float] = {}  # name → relative dist_km

        # Absolute event registry — events with fixed km positions
        # Each: {'type': str, 'abs_km': float, 'name': str, 'speed_kmh': float}
        self._abs_events: list[dict] = []
        self._known_station_names: set[str] = set()
        self._known_signal_keys: set[str] = set()  # "idx:abs_km_rounded"

        self.canvas = tk.Canvas(
            self, width=EBULA_W, height=EBULA_H,
            highlightthickness=0, bd=0,
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-3>", self._on_right_click)

        self._draw()
        self.withdraw()

    # -- Visibility --

    def toggle(self):
        if self._visible:
            self.withdraw()
            self._visible = False
        else:
            self.deiconify()
            self._visible = True
            self._draw()

    def show(self):
        if not self._visible:
            self.deiconify()
            self._visible = True
            self._draw()

    def hide(self):
        if self._visible:
            self.withdraw()
            self._visible = False

    @property
    def is_visible(self) -> bool:
        return self._visible

    # -- Theme --

    def set_theme(self, theme: str):
        if theme in THEMES:
            self._theme_name = theme
            self._theme = THEMES[theme]
            self._draw()

    def toggle_theme(self):
        self.set_theme("dark" if self._theme_name == "light" else "light")

    # -- Data --

    def update_data(self, data: EBuLaData):
        self._update_km_odometer(data)
        self._register_absolute_events(data)
        self._data = data
        if self._visible:
            self._draw()

    def _register_absolute_events(self, data: EBuLaData):
        """Register new events with fixed absolute km positions.

        When a station/signal/speed-change first appears from the API,
        compute its absolute km = _km_traveled + relative_distance
        and store it permanently. These positions never change.
        """
        # Stations — keyed by name (unique)
        for st in data.stations:
            if st.name and st.name not in self._known_station_names and st.distance_km >= 0:
                abs_km = self._km_traveled + st.distance_km
                self._abs_events.append({
                    'type': 'station', 'abs_km': abs_km,
                    'name': st.name, 'speed_kmh': 0
                })
                self._known_station_names.add(st.name)

        # Signals — keyed by rounded absolute km
        for idx, sig in enumerate(data.signals):
            if sig.distance_km < 0:
                continue
            abs_km = self._km_traveled + sig.distance_km
            key = f"{round(abs_km, 2)}"
            if key not in self._known_signal_keys:
                self._abs_events.append({
                    'type': 'signal', 'abs_km': abs_km,
                    'name': sig.name, 'speed_kmh': 0
                })
                self._known_signal_keys.add(key)

        # Speed changes — detect actual changes, keyed by rounded abs km
        cur_speed = data.current_speed_limit_kmh
        if cur_speed <= 0 and data.speed_limits:
            cur_speed = data.speed_limits[0].speed_kmh
        running = cur_speed
        for sl in data.speed_limits:
            if sl.distance_km < 0:
                running = sl.speed_kmh
                continue
            if int(round(sl.speed_kmh)) != int(round(running)):
                abs_km = self._km_traveled + sl.distance_km
                key = f"spd:{round(abs_km, 2)}"
                if key not in self._known_signal_keys:
                    self._abs_events.append({
                        'type': 'speed_change', 'abs_km': abs_km,
                        'name': '', 'speed_kmh': sl.speed_kmh
                    })
                    self._known_signal_keys.add(key)
            running = sl.speed_kmh

        # Sort by absolute km
        self._abs_events.sort(key=lambda e: e['abs_km'])

    def _update_km_odometer(self, data: EBuLaData):
        """Track cumulative km by comparing station distances between polls."""
        current = {st.name: st.distance_km for st in data.stations if st.name}
        if self._prev_stations and current:
            deltas: list[float] = []
            for name, cur_dist in current.items():
                if name in self._prev_stations:
                    delta = self._prev_stations[name] - cur_dist
                    # Reasonable movement in 500ms at max ~300 km/h = ~0.042 km
                    if 0 < delta < 0.1:
                        deltas.append(delta)
            if deltas:
                self._km_traveled += sum(deltas) / len(deltas)
        elif not self._prev_stations and current:
            # First poll — reset
            pass
        self._prev_stations = current

    def reset_odometer(self):
        """Reset cumulative km counter and event registry (e.g. new service)."""
        self._km_traveled = 0.0
        self._prev_stations = {}
        self._abs_events = []
        self._known_station_names = set()
        self._known_signal_keys = set()

    # -- Events --

    def _on_close(self):
        self.withdraw()
        self._visible = False

    def _on_right_click(self, event):
        menu = tk.Menu(self, tearoff=0)
        lbl = "☀ Light" if self._theme_name == "dark" else "🌙 Dark"
        menu.add_command(label=lbl, command=self.toggle_theme)
        menu.tk_popup(event.x_root, event.y_root)

    # ========================================================
    # Coordinate helpers
    # ========================================================

    def _effective_view_ahead(self) -> float:
        """Return the effective km range shown, based on the farthest row.
        Cached per draw cycle via _cached_view_ahead."""
        if hasattr(self, '_cached_view_ahead') and self._cached_view_ahead is not None:
            return self._cached_view_ahead
        rows = self._build_rows()
        if rows:
            max_dist = max(r['dist_km'] for r in rows)
            val = max(max_dist * 1.05, VIEW_AHEAD_KM)  # 5% margin
        else:
            val = VIEW_AHEAD_KM
        self._cached_view_ahead = val
        return val

    def _y_for_dist(self, dist_km: float) -> float:
        """Distance ahead (km) → canvas Y. Positive = above diamond."""
        total = self._effective_view_ahead() + VIEW_BEHIND_KM
        px_per_km = MAIN_H / total
        return DIAMOND_Y - dist_km * px_per_km

    def _x_for_speed(self, speed_kmh: float) -> float:
        """Speed (km/h) → X coordinate within the speed column.
        Fixed scale: 0–250 km/h mapped to column width."""
        frac = min(speed_kmh / 250.0, 1.0)
        return SPEED_MARGIN_L + frac * (COL_SPEED_R - SPEED_MARGIN_L - 2)

    # ========================================================
    # Main draw
    # ========================================================

    def _draw(self):
        c = self.canvas
        c.delete("all")
        t = self._theme
        self._cached_view_ahead = None  # invalidate cache for this draw cycle

        # Background
        c.create_rectangle(0, 0, EBULA_W, EBULA_H, fill=t["bg"], outline="")

        self._draw_header()
        self._draw_subheader()
        self._draw_grid()
        self._draw_speed_profile()
        self._draw_track_line()
        self._draw_diamond()
        self._draw_distances()
        self._draw_route_info()
        self._draw_bottom()

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    def _draw_header(self):
        c = self.canvas
        t = self._theme
        d = self._data

        c.create_rectangle(0, 0, EBULA_W, HEADER_H,
                           fill=t["header_bg"], outline=t["border"])

        qw = EBULA_W / 4

        # Train number
        num = d.train_number or "-----"
        c.create_text(qw * 0.5, HEADER_H / 2, text=num,
                      font=FONT_HEADER, fill=t["header_fg"], anchor="center")

        # Route name
        route = d.route_name or ""
        c.create_text(qw * 1.5, HEADER_H / 2, text=route,
                      font=FONT_HEADER_SM, fill=t["header_fg"], anchor="center")

        # Date
        date = d.date_str or "--.--.----"
        c.create_text(qw * 2.5, HEADER_H / 2, text=date,
                      font=FONT_HEADER_SM, fill=t["header_fg"], anchor="center")

        # Game clock
        tm = d.time_str or "--:--:--"
        c.create_text(qw * 3.5, HEADER_H / 2, text=tm,
                      font=FONT_HEADER, fill=t["header_fg"], anchor="center")

        # Vertical separators
        for i in (1, 2, 3):
            x = qw * i
            c.create_line(x, 0, x, HEADER_H, fill=t["col_sep"])

    # --------------------------------------------------------
    # Sub-header
    # --------------------------------------------------------

    def _draw_subheader(self):
        c = self.canvas
        t = self._theme
        d = self._data

        y0 = HEADER_H
        y1 = y0 + SUBHEADER_H
        c.create_rectangle(0, y0, EBULA_W, y1,
                           fill=t["subheader_bg"], outline=t["border"])

        # Left: current speed limit
        if d.current_speed_limit_kmh > 0:
            txt = f"{int(round(d.current_speed_limit_kmh))} km/h"
        else:
            txt = ""
        c.create_text(8, (y0 + y1) / 2, text=txt,
                      font=FONT_SUBHEADER, fill=t["subheader_fg"], anchor="w")

        # Right: next stop
        if d.next_stop:
            txt = f"Nächster Halt: {d.next_stop}"
            c.create_text(EBULA_W - 8, (y0 + y1) / 2, text=txt,
                          font=FONT_SUBHEADER, fill=t["subheader_fg"], anchor="e")

    # --------------------------------------------------------
    # Grid lines and column separators
    # --------------------------------------------------------

    def _collect_event_distances(self) -> list[float]:
        """Collect all event distances (km) for grid lines and distance labels.

        Events: stations, signals, speed changes.  If a gap > 2 km exists
        between consecutive events, insert filler markers every ~2 km.
        Returns a sorted, deduplicated list of distances.
        """
        d = self._data
        raw: list[float] = []
        for st in d.stations:
            raw.append(st.distance_km)
        for sig in d.signals:
            raw.append(sig.distance_km)
        for sl in d.speed_limits:
            raw.append(sl.distance_km)
        # Keep only visible range
        view_ahead = self._effective_view_ahead()
        raw = [x for x in raw if -VIEW_BEHIND_KM <= x <= view_ahead]
        raw.sort()
        # Deduplicate (merge events within 0.03 km)
        deduped: list[float] = []
        for v in raw:
            if not deduped or v - deduped[-1] > 0.03:
                deduped.append(v)
        # Fill gaps > 2 km with intermediate markers
        filled: list[float] = []
        prev = -VIEW_BEHIND_KM
        for v in deduped:
            gap = v - prev
            if gap > 2.0:
                n = int(gap / 2.0)
                step = gap / (n + 1)
                for i in range(1, n + 1):
                    filled.append(prev + step * i)
            filled.append(v)
            prev = v
        # Fill trailing gap
        gap = view_ahead - prev
        if gap > 2.0:
            n = int(gap / 2.0)
            step = gap / (n + 1)
            for i in range(1, n + 1):
                filled.append(prev + step * i)
        return filled

    def _draw_grid(self):
        c = self.canvas
        t = self._theme

        # Column separators (full height of main area)
        for x in (COL_SPEED_R, COL_TRACK_R, COL_DIST_R):
            c.create_line(x, MAIN_TOP, x, MAIN_BOT, fill=t["col_sep"], width=1)

    # --------------------------------------------------------
    # Speed profile (column 1) — continuous step polygon
    # --------------------------------------------------------

    def _draw_speed_profile(self):
        c = self.canvas
        t = self._theme
        d = self._data

        if not d.speed_limits and d.current_speed_limit_kmh <= 0:
            return

        view_bot = -VIEW_BEHIND_KM
        view_top = self._effective_view_ahead()

        # Current speed at train position
        cur_speed = d.current_speed_limit_kmh
        if cur_speed <= 0 and d.speed_limits:
            cur_speed = d.speed_limits[0].speed_kmh

        # Collect visible transitions where speed ACTUALLY changes
        # Use row positions from _build_rows for Y alignment
        transitions: list[tuple[float, float]] = []
        running_speed = cur_speed
        for sl in d.speed_limits:
            if sl.distance_km < view_bot:
                running_speed = sl.speed_kmh
                continue
            if sl.distance_km > view_top:
                break
            new_spd = int(round(sl.speed_kmh))
            old_spd = int(round(running_speed))
            if new_spd != old_spd:
                transitions.append((sl.distance_km, sl.speed_kmh))
            running_speed = sl.speed_kmh

        # If a speed change happened behind the view, adopt it
        if int(round(running_speed)) != int(round(cur_speed)) and not transitions:
            cur_speed = running_speed

        # Build row lookup: map transition distance → row border Y
        rows = self._build_rows()
        row_y_lookup: dict[float, float] = {}
        for row in rows:
            row_y_lookup[round(row['dist_km'], 3)] = row['y_bot']

        # Y limits (clamped to main area)
        y_bottom = min(self._y_for_dist(view_bot), MAIN_BOT)
        y_top = max(self._y_for_dist(view_top), MAIN_TOP)
        left_x = SPEED_MARGIN_L

        # ---- Build step polygon (clockwise) ----
        # Left edge is constant (left_x), right edge follows speed profile.
        pts: list[tuple[float, float]] = []

        # 1. Bottom-left
        pts.append((left_x, y_bottom))

        # 2. Bottom-right at current speed
        x_cur = self._x_for_speed(cur_speed) if cur_speed > 0 else left_x
        pts.append((x_cur, y_bottom))

        # 3. Step through each transition (snap to row borders if available)
        active_speed = cur_speed
        for (dist, new_speed) in transitions:
            # Try to snap to a row border
            y = row_y_lookup.get(round(dist, 3), None)
            if y is None:
                # Fallback: find closest row
                best_y = None
                best_delta = 999
                for rd, ry in row_y_lookup.items():
                    delta = abs(rd - dist)
                    if delta < best_delta and delta < 0.05:
                        best_delta = delta
                        best_y = ry
                y = best_y if best_y is not None else self._y_for_dist(dist)
            y = max(MAIN_TOP, min(MAIN_BOT, y))
            x_old = self._x_for_speed(active_speed) if active_speed > 0 else left_x
            x_new = self._x_for_speed(new_speed) if new_speed > 0 else left_x
            # Vertical to transition height at old speed width
            pts.append((x_old, y))
            # Horizontal step to new speed width
            pts.append((x_new, y))
            active_speed = new_speed

        # 4. Extend to top of view at last speed
        x_last = self._x_for_speed(active_speed) if active_speed > 0 else left_x
        pts.append((x_last, y_top))

        # 5. Top-left corner
        pts.append((left_x, y_top))

        # ---- Right-side step contour — 2px white ----
        if len(pts) >= 4:
            outline_pts = pts[1:-1]
            for i in range(len(outline_pts) - 1):
                x1, y1 = outline_pts[i]
                x2, y2 = outline_pts[i + 1]
                # Horizontal segments = speed transition steps
                if abs(y1 - y2) < 1:
                    continue  # skip horizontal (drawn separately)
                # Vertical segments = speed bar sides — 7px
                c.create_line(x1, y1, x2, y2,
                              fill=t["speed_outline"], width=7)

        # ---- Horizontal lines at each speed transition — 2px white ----
        for (dist, _spd) in transitions:
            y = row_y_lookup.get(round(dist, 3), None)
            if y is None:
                best_y = None
                best_delta = 999
                for rd, ry in row_y_lookup.items():
                    delta = abs(rd - dist)
                    if delta < best_delta and delta < 0.05:
                        best_delta = delta
                        best_y = ry
                y = best_y if best_y is not None else self._y_for_dist(dist)
            y = max(MAIN_TOP, min(MAIN_BOT, y))
            c.create_line(0, y, COL_SPEED_R, y,
                          fill=t["speed_outline"], width=2)

        # ---- Speed labels — bottom-right corner of each step block ----
        # Each label goes at the bottom of its block (just above the next transition)
        label_positions: list[float] = []
        min_label_gap = 18
        CURRENT_SPEED_BG = "#0066FF"  # electric blue background for current speed

        def _place_label(y_bottom_of_block: float, speed_val: float,
                         is_current: bool = False):
            """Place a speed label at the bottom-right of a speed block."""
            ly = y_bottom_of_block - 4  # just above the bottom line
            if ly < MAIN_TOP + 8 or ly > MAIN_BOT - 4:
                return
            if any(abs(ly - prev) < min_label_gap for prev in label_positions):
                return
            label_positions.append(ly)
            lx = COL_SPEED_R - 3
            txt = str(int(round(speed_val)))
            if is_current:
                # Measure text size for background rectangle
                tmp_id = c.create_text(0, 0, text=txt, font=FONT_SPEED, anchor="se")
                bbox = c.bbox(tmp_id)
                c.delete(tmp_id)
                if bbox:
                    pad = 2
                    tw = bbox[2] - bbox[0]
                    th = bbox[3] - bbox[1]
                    c.create_rectangle(lx - tw - pad, ly - th - pad,
                                       lx + pad, ly + pad,
                                       fill=CURRENT_SPEED_BG, outline="")
            c.create_text(lx, ly, text=txt,
                          font=FONT_SPEED,
                          fill="#FFFFFF" if is_current else t["speed_text"],
                          anchor="se")

        # Build list of blocks: (speed, y_top_of_block, y_bottom_of_block, is_current)
        block_list: list[tuple[float, float, float, bool]] = []
        prev_y = y_top
        prev_spd = transitions[-1][1] if transitions else cur_speed
        # Walk transitions top-to-bottom (reverse order since y increases downward)
        sorted_trans = sorted(transitions, key=lambda t: t[0], reverse=True)
        for (dist, new_speed) in sorted_trans:
            y = row_y_lookup.get(round(dist, 3), None)
            if y is None:
                best_y = None
                best_delta = 999
                for rd, ry in row_y_lookup.items():
                    delta = abs(rd - dist)
                    if delta < best_delta and delta < 0.05:
                        best_delta = delta
                        best_y = ry
                y = best_y if best_y is not None else self._y_for_dist(dist)
            y = max(MAIN_TOP, min(MAIN_BOT, y))
            block_list.append((new_speed, prev_y, y, False))
            prev_y = y
        # Final block from last transition down to bottom = cur_speed (this is the current block)
        block_list.append((cur_speed, prev_y, y_bottom, True))

        for (spd, _yt, yb, is_cur) in block_list:
            if spd > 0:
                _place_label(yb, spd, is_current=is_cur)

    # --------------------------------------------------------
    # Track line (column 2)
    # --------------------------------------------------------

    def _draw_track_line(self):
        c = self.canvas
        t = self._theme

        mid_x = (COL_TRACK_L + COL_TRACK_R) / 2

        # Main vertical track line
        c.create_line(mid_x, MAIN_TOP, mid_x, MAIN_BOT,
                      fill=t["track_line"], width=2)

    # --------------------------------------------------------
    # Diamond / prism (train position)
    # --------------------------------------------------------

    def _draw_diamond(self):
        c = self.canvas
        t = self._theme

        mid_x = (COL_TRACK_L + COL_TRACK_R) / 2
        sz = 9
        pts = [
            mid_x, DIAMOND_Y - sz,    # top
            mid_x + sz, DIAMOND_Y,     # right
            mid_x, DIAMOND_Y + sz,     # bottom
            mid_x - sz, DIAMOND_Y,     # left
        ]
        c.create_polygon(pts, fill=t["diamond_fill"], outline=t["diamond_outline"], width=1)

    # --------------------------------------------------------
    # Distance markers (column 3)
    # --------------------------------------------------------

    def _build_rows(self) -> list[dict]:
        """Build fixed-height rows from the absolute event registry.

        Each row is a dict with keys:
          'type': 'station' | 'signal' | 'speed_change' | 'spacer'
          'abs_km': float       (fixed absolute km from start)
          'dist_km': float      (relative distance from current train position)
          'name': str           (empty for speed_change/spacer)
          'speed_kmh': float    (only for speed_change)
          'y_top': float        (canvas Y of row top border)
          'y_bot': float        (canvas Y of row bottom border)
          'y_center': float     (canvas Y center)

        Uses _abs_events (absolute km positions) and _km_traveled.
        Rows stack upward from DIAMOND_Y (ahead) and downward (behind).
        """
        train_km = self._km_traveled
        SPACER_INTERVAL = 0.6

        # Compute relative distance for each absolute event
        events: list[dict] = []
        for ae in self._abs_events:
            rel = ae['abs_km'] - train_km  # positive = ahead, negative = behind
            events.append({
                'type': ae['type'], 'abs_km': ae['abs_km'],
                'dist_km': rel, 'name': ae['name'], 'speed_kmh': ae['speed_kmh']
            })

        # Split ahead / behind
        ahead = [e for e in events if e['dist_km'] >= 0]
        behind = [e for e in events if e['dist_km'] < 0]
        ahead.sort(key=lambda e: e['dist_km'])
        behind.sort(key=lambda e: e['dist_km'], reverse=True)

        # Fill spacers in ahead events (every 0.6 km)
        filled: list[dict] = []
        prev_abs = train_km
        for ev in ahead:
            gap = ev['abs_km'] - prev_abs
            if gap > SPACER_INTERVAL * 1.2:
                n_spacers = int(gap / SPACER_INTERVAL)
                step = gap / (n_spacers + 1)
                for j in range(1, n_spacers + 1):
                    sp_abs = prev_abs + step * j
                    if abs(sp_abs - ev['abs_km']) > 0.1:
                        filled.append({
                            'type': 'spacer', 'abs_km': sp_abs,
                            'dist_km': sp_abs - train_km,
                            'name': '', 'speed_kmh': 0
                        })
            filled.append(ev)
            prev_abs = ev['abs_km']

        # Fill trailing spacers to fill the page
        max_rows_available = int((DIAMOND_Y - MAIN_TOP) / ROW_H)
        remaining = max_rows_available - len(filled)
        if remaining > 0:
            last_abs = filled[-1]['abs_km'] if filled else train_km
            for k in range(1, remaining + 1):
                sp_abs = last_abs + SPACER_INTERVAL * k
                filled.append({
                    'type': 'spacer', 'abs_km': sp_abs,
                    'dist_km': sp_abs - train_km,
                    'name': '', 'speed_kmh': 0
                })

        # Build ahead rows — stack upward from DIAMOND_Y
        rows: list[dict] = []
        for i, ev in enumerate(filled):
            y_bot = DIAMOND_Y - i * ROW_H
            y_top = y_bot - ROW_H
            if y_top < MAIN_TOP:
                break
            ev['y_bot'] = y_bot
            ev['y_top'] = y_top
            ev['y_center'] = (y_top + y_bot) / 2
            rows.append(ev)

        # Build behind rows — stack downward from DIAMOND_Y
        for i, ev in enumerate(behind):
            y_top = DIAMOND_Y + i * ROW_H
            y_bot = y_top + ROW_H
            if y_bot > MAIN_BOT:
                break
            ev['y_bot'] = y_bot
            ev['y_top'] = y_top
            ev['y_center'] = (y_top + y_bot) / 2
            rows.append(ev)

        return rows

    def _draw_distances(self):
        c = self.canvas
        t = self._theme
        pad = 2

        mid_x = (COL_DIST_L + COL_DIST_R) / 2
        rows = self._build_rows()

        for row in rows:
            y_top = row['y_top']
            y_bot = row['y_bot']
            y_center = row['y_center']

            # Top and bottom border lines
            c.create_line(COL_DIST_L, y_top, EBULA_W, y_top,
                          fill=t["grid_line"], width=1)
            c.create_line(COL_DIST_L, y_bot, EBULA_W, y_bot,
                          fill=t["grid_line"], width=1)

            # Distance text — fixed absolute km milestone
            txt = f"{row['abs_km']:.1f}"
            c.create_text(mid_x, y_center, text=txt,
                          font=FONT_DISTANCE, fill=t["distance_text"],
                          anchor="center")

    # --------------------------------------------------------
    # Route info — stations, signals, tunnels (column 4)
    # --------------------------------------------------------

    def _draw_route_info(self):
        c = self.canvas
        t = self._theme
        d = self._data

        # --- Stations and Signals via fixed rows ---
        rows = self._build_rows()
        for row in rows:
            yc = row['y_center']
            if row['type'] in ('speed_change', 'spacer'):
                continue  # empty row — no content in info column
            elif row['type'] == 'station':
                c.create_text(COL_INFO_L + 8, yc, text=row['name'],
                              font=FONT_STATION, fill=t["text_station"], anchor="w")
            else:  # signal
                mx = COL_INFO_L + 8
                c.create_text(mx, yc, text="¥",
                              font=(FONT_FAMILY, 10), fill=t["signal_color"],
                              anchor="center")
                c.create_text(mx + 14, yc, text=row['name'],
                              font=FONT_SIGNAL, fill=t["text"], anchor="w")

    # --------------------------------------------------------
    # Bottom status bar
    # --------------------------------------------------------

    def _draw_bottom(self):
        c = self.canvas
        t = self._theme
        d = self._data

        y0 = MAIN_BOT
        y1 = EBULA_H

        # Background
        c.create_rectangle(0, y0, EBULA_W, y1, fill=t["bottom_bg"], outline=t["border"])

        # Status line
        info_y = y0 + 14
        parts = []
        if d.max_speed_kmh > 0:
            parts.append(f"Vmax {int(round(d.max_speed_kmh))} km/h")
        if abs(d.gradient) > 0.1:
            parts.append(f"Steigung {d.gradient:+.1f}‰")
        status = "    ".join(parts) if parts else ""
        c.create_text(10, info_y, text=status,
                      font=FONT_BOTTOM, fill=t["bottom_fg"], anchor="w")

        # Theme hint
        c.create_text(EBULA_W - 10, info_y, text="Rechtsklick → Theme",
                      font=FONT_BOTTOM, fill=t["text_dim"], anchor="e")

        # Decorative button bar
        btn_y = y0 + 36
        btn_labels = ["Zug", "FSD", "", "LW", "GW", "Zeit", "", "G", "", "E"]
        btn_count = len(btn_labels)
        btn_w = EBULA_W / btn_count

        for i, label in enumerate(btn_labels):
            if label:
                x_center = i * btn_w + btn_w / 2
                c.create_rectangle(
                    x_center - 24, btn_y - 8, x_center + 24, btn_y + 8,
                    fill=t["btn_bg"], outline=t["btn_border"],
                )
                c.create_text(x_center, btn_y, text=label,
                              font=FONT_BTN, fill=t["btn_fg"], anchor="center")


# ============================================================
# Convenience: open/manage from GUI
# ============================================================

class EBuLaManager:
    """
    Manages the EBuLa panel lifecycle.

    Usage in GUI:
        self._ebula_mgr = EBuLaManager(self.root)
        self._ebula_mgr.toggle()             # show/hide
        self._ebula_mgr.update(ebula_data)   # push new data
    """

    def __init__(self, parent: tk.Tk, theme: str = "dark"):
        self._parent = parent
        self._theme = theme
        self._panel: Optional[EBuLaPanel] = None

    def toggle(self):
        if self._panel is None:
            self._panel = EBuLaPanel(self._parent, self._theme)
        self._panel.toggle()

    def update(self, data: EBuLaData):
        if self._panel is not None and self._panel.is_visible:
            self._panel.update_data(data)

    def set_theme(self, theme: str):
        self._theme = theme
        if self._panel is not None:
            self._panel.set_theme(theme)

    @property
    def is_visible(self) -> bool:
        return self._panel is not None and self._panel.is_visible
