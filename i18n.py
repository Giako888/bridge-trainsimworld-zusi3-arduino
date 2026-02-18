"""
Internazionalizzazione (i18n) — Train Simulator Bridge
=======================================================
Supporta: Italiano (it), English (en), Deutsch (de).
Rileva la lingua di sistema e permette cambio manuale.
"""

import locale
import logging

logger = logging.getLogger("i18n")

LANGUAGES = {
    "it": {"name": "Italiano", "flag": "🇮🇹"},
    "en": {"name": "English",  "flag": "🇬🇧"},
    "de": {"name": "Deutsch",  "flag": "🇩🇪"},
}

_current_lang = "en"

# ============================================================
# Traduzioni
# ============================================================

TRANSLATIONS = {

    # --- Tabs ---
    "tab_connection":       {"it": "  Connessione  ",    "en": "  Connection  ",     "de": "  Verbindung  "},
    "tab_profile":          {"it": "  🚂 Profilo  ",     "en": "  🚂 Profile  ",     "de": "  🚂 Profil  "},
    "tab_profile_na":       {"it": "  🚂 Profilo (N/A)  ", "en": "  🚂 Profile (N/A)  ", "de": "  🚂 Profil (N/A)  "},

    # --- Header ---
    "language_tooltip":     {"it": "Lingua",              "en": "Language",           "de": "Sprache"},

    # --- Simulator selector ---
    "lf_simulator":         {"it": "  Simulatore  ",      "en": "  Simulator  ",      "de": "  Simulator  "},
    "rb_tsw6":              {"it": "Train Sim World (HTTP API)", "en": "Train Sim World (HTTP API)", "de": "Train Sim World (HTTP API)"},
    "rb_zusi3":             {"it": "Zusi 3 (TCP Protocol)",      "en": "Zusi 3 (TCP Protocol)",      "de": "Zusi 3 (TCP Protocol)"},
    "sim_locked":           {"it": "🔒 {sim} connesso — disconnetti per cambiare",
                             "en": "🔒 {sim} connected — disconnect to change",
                             "de": "🔒 {sim} verbunden — zum Wechseln trennen"},

    # --- TSW6 frame ---
    "lf_tsw6":              {"it": "  TSW6 (HTTP API)  ", "en": "  TSW6 (HTTP API)  ", "de": "  TSW6 (HTTP API)  "},
    "host":                 {"it": "Host:",               "en": "Host:",              "de": "Host:"},
    "port":                 {"it": "Porta:",              "en": "Port:",              "de": "Port:"},
    "connect":              {"it": "Connetti",            "en": "Connect",            "de": "Verbinden"},
    "disconnect":           {"it": "Disconnetti",         "en": "Disconnect",         "de": "Trennen"},
    "status_disconnected":  {"it": "● Disconnesso",       "en": "● Disconnected",     "de": "● Getrennt"},
    "status_connected":     {"it": "● Connesso",          "en": "● Connected",        "de": "● Verbunden"},
    "status_connecting":    {"it": "⏳ Connessione...",    "en": "⏳ Connecting...",    "de": "⏳ Verbinde..."},
    "status_failed":        {"it": "● Fallito",           "en": "● Failed",           "de": "● Fehlgeschlagen"},
    "status_error":         {"it": "● Errore",            "en": "● Error",            "de": "● Fehler"},
    "api_key":              {"it": "API Key:",             "en": "API Key:",           "de": "API Key:"},
    "api_key_auto":         {"it": "🔑 Auto",             "en": "🔑 Auto",            "de": "🔑 Auto"},

    # --- Zusi3 frame ---
    "lf_zusi3":             {"it": "  Zusi 3 (TCP Protocol)  ", "en": "  Zusi 3 (TCP Protocol)  ", "de": "  Zusi 3 (TCP Protocol)  "},

    # --- Arduino frame ---
    "lf_arduino":           {"it": "  Arduino Leonardo (12 LED Charlieplexing)  ",
                             "en": "  Arduino Leonardo (12 LED Charlieplexing)  ",
                             "de": "  Arduino Leonardo (12 LED Charlieplexing)  "},
    "port_label":           {"it": "Porta:",              "en": "Port:",              "de": "Port:"},
    "btn_test":             {"it": "🔦 Test",             "en": "🔦 Test",            "de": "🔦 Test"},
    "btn_leds_off":         {"it": "💡 Spegni",           "en": "💡 Off",             "de": "💡 Aus"},

    # --- Bridge frame ---
    "lf_bridge":            {"it": "  Bridge Simulatore → Arduino  ",
                             "en": "  Bridge Simulator → Arduino  ",
                             "de": "  Bridge Simulator → Arduino  "},
    "lf_bridge_tsw6":       {"it": "  Bridge TSW6 → Arduino  ",
                             "en": "  Bridge TSW6 → Arduino  ",
                             "de": "  Bridge TSW6 → Arduino  "},
    "lf_bridge_zusi3":      {"it": "  Bridge Zusi3 → Arduino  ",
                             "en": "  Bridge Zusi3 → Arduino  ",
                             "de": "  Bridge Zusi3 → Arduino  "},
    "btn_start_bridge":     {"it": "▶ AVVIA BRIDGE",      "en": "▶ START BRIDGE",     "de": "▶ BRIDGE STARTEN"},
    "btn_stop_bridge":      {"it": "⏹ FERMA",             "en": "⏹ STOP",             "de": "⏹ STOPP"},
    "bridge_waiting":       {"it": "In attesa connessioni...",
                             "en": "Waiting for connections...",
                             "de": "Warte auf Verbindungen..."},
    "bridge_ready":         {"it": "Pronto ({sim} + Arduino)",
                             "en": "Ready ({sim} + Arduino)",
                             "de": "Bereit ({sim} + Arduino)"},
    "bridge_ready_gui":     {"it": "Pronto (solo {sim} - LED solo in GUI)",
                             "en": "Ready ({sim} only - LED in GUI only)",
                             "de": "Bereit (nur {sim} - LED nur in GUI)"},
    "bridge_wait_sim":      {"it": "Attesa: connessione {sim}",
                             "en": "Waiting: {sim} connection",
                             "de": "Warte auf: {sim}-Verbindung"},
    "bridge_starting":      {"it": "⏳ Avvio...",          "en": "⏳ Starting...",      "de": "⏳ Starte..."},
    "bridge_active":        {"it": "● ATTIVO",             "en": "● ACTIVE",           "de": "● AKTIV"},
    "bridge_start_failed":  {"it": "● Avvio fallito",     "en": "● Start failed",     "de": "● Start fehlgeschlagen"},
    "bridge_stopped":       {"it": "Fermato",              "en": "Stopped",            "de": "Gestoppt"},

    # --- LED panel ---
    "lf_led_status":        {"it": "  Stato LED  ",       "en": "  LED Status  ",     "de": "  LED Status  "},

    # --- Debug log ---
    "lf_debug_log":         {"it": "  📋 Debug Log (dati TSW6)  ",
                             "en": "  📋 Debug Log (TSW6 data)  ",
                             "de": "  📋 Debug Log (TSW6-Daten)  "},

    # --- Train detection (Profile tab) ---
    "lf_train_detect":      {"it": "  Rilevamento Treno  ",  "en": "  Train Detection  ",  "de": "  Zugerkennung  "},
    "train_detected":       {"it": "Treno rilevato:",        "en": "Train detected:",      "de": "Zug erkannt:"},
    "train_none":           {"it": "— nessuno —",            "en": "— none —",             "de": "— keiner —"},
    "btn_detect_train":     {"it": "🔍 Rileva Treno",        "en": "🔍 Detect Train",      "de": "🔍 Zug erkennen"},
    "detecting":            {"it": "⏳ Rilevamento...",       "en": "⏳ Detecting...",       "de": "⏳ Erkennung..."},
    "train_not_detected":   {"it": "— non rilevato —",       "en": "— not detected —",     "de": "— nicht erkannt —"},

    # --- Profile selection ---
    "lf_active_profile":    {"it": "  Profilo Attivo  ",     "en": "  Active Profile  ",   "de": "  Aktives Profil  "},
    "btn_apply_profile":    {"it": "✅ Applica Profilo",      "en": "✅ Apply Profile",      "de": "✅ Profil anwenden"},
    "lf_mappings":          {"it": "  Mappature Profilo (sola lettura)  ",
                             "en": "  Profile Mappings (read-only)  ",
                             "de": "  Profil-Zuordnungen (nur Lesen)  "},
    "col_name":             {"it": "Nome",                    "en": "Name",                 "de": "Name"},
    "col_endpoint":         {"it": "Endpoint TSW6",           "en": "TSW6 Endpoint",        "de": "TSW6-Endpunkt"},
    "col_led":              {"it": "LED",                     "en": "LED",                  "de": "LED"},
    "col_action":           {"it": "Azione",                  "en": "Action",               "de": "Aktion"},

    # --- Footer ---
    "ready":                {"it": "Pronto",                  "en": "Ready",                "de": "Bereit"},

    # --- Log / status messages ---
    "log_connected_tsw6":   {"it": "Connesso a TSW6",        "en": "Connected to TSW6",    "de": "Verbunden mit TSW6"},
    "log_disconnected_tsw6":{"it": "Disconnesso da TSW6",    "en": "Disconnected from TSW6","de": "Von TSW6 getrennt"},
    "log_connected_zusi3":  {"it": "Connesso a Zusi3",       "en": "Connected to Zusi3",   "de": "Verbunden mit Zusi3"},
    "log_disconnected_zusi3":{"it": "Disconnesso da Zusi3",  "en": "Disconnected from Zusi3","de": "Von Zusi3 getrennt"},
    "log_arduino_port":     {"it": "Arduino su {port}",      "en": "Arduino on {port}",    "de": "Arduino auf {port}"},
    "log_arduino_disconnected":{"it": "Arduino disconnesso", "en": "Arduino disconnected", "de": "Arduino getrennt"},
    "log_apikey_found":     {"it": "API Key trovata ({n} caratteri)",
                             "en": "API Key found ({n} chars)",
                             "de": "API Key gefunden ({n} Zeichen)"},
    "log_apikey_not_found": {"it": "API Key non trovata - inseriscila manualmente",
                             "en": "API Key not found - enter it manually",
                             "de": "API Key nicht gefunden - manuell eingeben"},
    "log_test_leds":        {"it": "Test LED...",             "en": "Testing LEDs...",      "de": "LED-Test..."},
    "log_test_done":        {"it": "Test LED completato",    "en": "LED test complete",    "de": "LED-Test abgeschlossen"},
    "log_leds_off":         {"it": "LED spenti",              "en": "LEDs off",             "de": "LEDs aus"},
    "log_bridge_stopped":   {"it": "Bridge fermato",          "en": "Bridge stopped",       "de": "Bridge gestoppt"},
    "log_profile":          {"it": "Profilo: {name}",         "en": "Profile: {name}",      "de": "Profil: {name}"},
    "log_profile_not_found":{"it": "Profilo '{pid}' non trovato",
                             "en": "Profile '{pid}' not found",
                             "de": "Profil '{pid}' nicht gefunden"},
    "log_profile_saved":    {"it": "Profilo salvato: {pid}",
                             "en": "Profile saved: {pid}",
                             "de": "Profil gespeichert: {pid}"},
    "log_no_profile":       {"it": "Nessun profilo attivo da salvare",
                             "en": "No active profile to save",
                             "de": "Kein aktives Profil zum Speichern"},
    "log_train_not_detected":{"it": "Treno non rilevato",    "en": "Train not detected",   "de": "Zug nicht erkannt"},
    "log_bridge_tsw6_started":{"it": "Bridge TSW6 avviato ({n} endpoint, modo {mode})",
                               "en": "TSW6 bridge started ({n} endpoints, {mode} mode)",
                               "de": "TSW6-Bridge gestartet ({n} Endpunkte, Modus {mode})"},
    "log_bridge_zusi3_started":{"it": "Bridge Zusi3 avviato", "en": "Zusi3 bridge started", "de": "Zusi3-Bridge gestartet"},
    "log_found_port":       {"it": "🔍 Trovato: {port}",     "en": "🔍 Found: {port}",     "de": "🔍 Gefunden: {port}"},

    # --- Profile status ---
    "profile_active":       {"it": "● {name} attivo ({n} mappature)",
                             "en": "● {name} active ({n} mappings)",
                             "de": "● {name} aktiv ({n} Zuordnungen)"},
    "profile_changed_restart":{"it": "⚠️ Profilo cambiato — riavvia il bridge per applicare",
                               "en": "⚠️ Profile changed — restart bridge to apply",
                               "de": "⚠️ Profil geändert — Bridge neu starten zum Anwenden"},
    "train_unknown":        {"it": "⚠️ Treno '{cls}' non riconosciuto — seleziona manualmente",
                             "en": "⚠️ Train '{cls}' not recognized — select manually",
                             "de": "⚠️ Zug '{cls}' nicht erkannt — manuell auswählen"},
    "train_unknown_debug":  {"it": "⚠️ Treno '{cls}' non ha un profilo, scegli manualmente",
                             "en": "⚠️ Train '{cls}' has no profile, choose manually",
                             "de": "⚠️ Zug '{cls}' hat kein Profil, manuell wählen"},

    # --- Debug log messages ---
    "dbg_bridge_tsw6_start":{"it": "Avvio bridge TSW6 con {n} endpoint:",
                             "en": "Starting TSW6 bridge with {n} endpoints:",
                             "de": "Starte TSW6-Bridge mit {n} Endpunkten:"},
    "dbg_bridge_tsw6_active":{"it": "✅ Bridge TSW6 attivo - {mode} mode, polling ogni {ms}ms",
                              "en": "✅ TSW6 bridge active - {mode} mode, polling every {ms}ms",
                              "de": "✅ TSW6-Bridge aktiv - {mode}-Modus, Abfrage alle {ms}ms"},
    "dbg_bridge_zusi3_active":{"it": "✅ Bridge Zusi3 attivo - ricezione dati in tempo reale",
                               "en": "✅ Zusi3 bridge active - real-time data reception",
                               "de": "✅ Zusi3-Bridge aktiv - Echtzeit-Datenempfang"},
    "dbg_bridge_start_fail":{"it": "❌ Avvio bridge fallito",
                              "en": "❌ Bridge start failed",
                              "de": "❌ Bridge-Start fehlgeschlagen"},
    "dbg_zusi3_connected":  {"it": "✅ Zusi3 connesso ({host}:{port})",
                              "en": "✅ Zusi3 connected ({host}:{port})",
                              "de": "✅ Zusi3 verbunden ({host}:{port})"},
    "dbg_zusi3_conn_fail":  {"it": "❌ Connessione Zusi3 fallita",
                              "en": "❌ Zusi3 connection failed",
                              "de": "❌ Zusi3-Verbindung fehlgeschlagen"},
    "dbg_zusi3_connected_short":{"it": "Zusi3 connesso",
                                  "en": "Zusi3 connected",
                                  "de": "Zusi3 verbunden"},
    "dbg_zusi3_disconnected":{"it": "Zusi3 disconnesso",
                               "en": "Zusi3 disconnected",
                               "de": "Zusi3 getrennt"},
    "dbg_zusi3_bridge_start":{"it": "Avvio bridge Zusi3 — mappatura diretta PZB/LZB/SIFA → LED",
                               "en": "Starting Zusi3 bridge — direct PZB/LZB/SIFA → LED mapping",
                               "de": "Starte Zusi3-Bridge — direkte PZB/LZB/SIFA → LED-Zuordnung"},

    # --- Messageboxes ---
    "msgbox_warning":       {"it": "Attenzione",             "en": "Warning",              "de": "Warnung"},
    "msgbox_error_tsw6":    {"it": "Errore TSW6",            "en": "TSW6 Error",           "de": "TSW6-Fehler"},
    "msgbox_error_zusi3":   {"it": "Errore Zusi3",           "en": "Zusi3 Error",          "de": "Zusi3-Fehler"},
    "msgbox_error_arduino": {"it": "Errore Arduino",         "en": "Arduino Error",        "de": "Arduino-Fehler"},
    "msgbox_error_bridge":  {"it": "Errore Bridge",          "en": "Bridge Error",         "de": "Bridge-Fehler"},
    "msgbox_apikey_title":  {"it": "API Key",                "en": "API Key",              "de": "API Key"},
    "msgbox_apikey_empty":  {"it": "API Key vuota.\n\nInseriscila manualmente oppure clicca '🔑 Auto' per cercarla.\n"
                                   "Il file si trova in:\nDocuments\\My Games\\TrainSimWorld6\\Saved\\Config\\CommAPIKey.txt",
                             "en": "API Key is empty.\n\nEnter it manually or click '🔑 Auto' to auto-detect.\n"
                                   "The file is located at:\nDocuments\\My Games\\TrainSimWorld6\\Saved\\Config\\CommAPIKey.txt",
                             "de": "API Key ist leer.\n\nManuell eingeben oder '🔑 Auto' klicken zum Erkennen.\n"
                                   "Die Datei befindet sich unter:\nDocuments\\My Games\\TrainSimWorld6\\Saved\\Config\\CommAPIKey.txt"},
    "msgbox_connect_tsw6":  {"it": "Connettiti a TSW6 prima di avviare il bridge.",
                             "en": "Connect to TSW6 before starting the bridge.",
                             "de": "Verbinde dich mit TSW6, bevor du die Bridge startest."},
    "msgbox_connect_zusi3": {"it": "Connettiti a Zusi3 prima di avviare il bridge.",
                             "en": "Connect to Zusi3 before starting the bridge.",
                             "de": "Verbinde dich mit Zusi3, bevor du die Bridge startest."},
    "msgbox_no_mappings":   {"it": "Nessuna mappatura attiva.",
                             "en": "No active mappings.",
                             "de": "Keine aktiven Zuordnungen."},
    "msgbox_bridge_fail":   {"it": "Impossibile avviare il bridge.\n\n"
                                   "Verifica che:\n"
                                   "• TSW6 sia in esecuzione con -HTTPAPI\n"
                                   "• Stai guidando un treno\n"
                                   "• Gli endpoint delle mappature siano corretti",
                             "en": "Unable to start the bridge.\n\n"
                                   "Check that:\n"
                                   "• TSW6 is running with -HTTPAPI\n"
                                   "• You are driving a train\n"
                                   "• The mapping endpoints are correct",
                             "de": "Bridge konnte nicht gestartet werden.\n\n"
                                   "Überprüfe dass:\n"
                                   "• TSW6 mit -HTTPAPI läuft\n"
                                   "• Du einen Zug fährst\n"
                                   "• Die Zuordnungs-Endpunkte korrekt sind"},
    "msgbox_arduino_not_connected":{"it": "Arduino non connesso",
                                    "en": "Arduino not connected",
                                    "de": "Arduino nicht verbunden"},
    "msgbox_detect_first":  {"it": "Connettiti a TSW6 prima di rilevare il treno.",
                             "en": "Connect to TSW6 before detecting the train.",
                             "de": "Verbinde dich mit TSW6, bevor du den Zug erkennst."},

    # --- Error prefixes ---
    "err_apikey":           {"it": "Chiave API: {e}",        "en": "API Key: {e}",         "de": "API-Schlüssel: {e}"},
    "err_connection":       {"it": "Connessione: {e}",       "en": "Connection: {e}",      "de": "Verbindung: {e}"},

    # --- Train profile descriptions ---
    "profile_desc_br101":   {"it": "BR 101 (Expert) — PZB/LZB/SIFA con pannello MFA",
                             "en": "BR 101 (Expert) — PZB/LZB/SIFA with MFA panel",
                             "de": "BR 101 (Expert) — PZB/LZB/SIFA mit MFA-Anzeige"},
    "profile_desc_vectron": {"it": "Vectron — PZB/LZB/SIFA senza pannello MFA",
                             "en": "Vectron — PZB/LZB/SIFA without MFA panel",
                             "de": "Vectron — PZB/LZB/SIFA ohne MFA-Anzeige"},
    "profile_desc_bpmmbdzf":{"it": "Carrozza pilota — stessi indicatori MFA della BR101 (Expert)",
                             "en": "Cab car — same MFA indicators as BR101 (Expert)",
                             "de": "Steuerwagen — gleiche MFA-Anzeigen wie BR101 (Expert)"},
    "profile_desc_br146":   {"it": "BR 146.2 — PZB_V2/LZB_Service/SIFA diretto, senza MFA",
                             "en": "BR 146.2 — PZB_V2/LZB_Service/SIFA direct, no MFA",
                             "de": "BR 146.2 — PZB_V2/LZB_Service/SIFA direkt, ohne MFA"},
    "profile_desc_br114":   {"it": "BR 114 — PZB/SIFA, senza LZB, senza MFA",
                             "en": "BR 114 — PZB/SIFA, no LZB, no MFA",
                             "de": "BR 114 — PZB/SIFA, ohne LZB, ohne MFA"},
    "profile_desc_br411":   {"it": "BR 411 ICE-T — PZB_V3/LZB/SIFA, senza MFA",
                             "en": "BR 411 ICE-T — PZB_V3/LZB/SIFA, no MFA",
                             "de": "BR 411 ICE-T — PZB_V3/LZB/SIFA, ohne MFA"},
    "profile_desc_br406":   {"it": "BR 406 ICE 3 — PZB/LZB, senza SIFA/porte via API, senza MFA",
                             "en": "BR 406 ICE 3 — PZB/LZB, no SIFA/doors via API, no MFA",
                             "de": "BR 406 ICE 3 — PZB/LZB, ohne SIFA/Türen via API, ohne MFA"},
}

# Map profile IDs to description translation keys
PROFILE_DESC_KEYS = {
    "BR101":    "profile_desc_br101",
    "Vectron":  "profile_desc_vectron",
    "Bpmmbdzf": "profile_desc_bpmmbdzf",
    "BR146":    "profile_desc_br146",
    "BR114":    "profile_desc_br114",
    "BR411":    "profile_desc_br411",
    "BR406":    "profile_desc_br406",
}


# ============================================================
# API
# ============================================================

def detect_system_language() -> str:
    """Detect system language from locale. Returns 'it', 'en', or 'de'."""
    try:
        lang = locale.getdefaultlocale()[0]
        if lang:
            code = lang[:2].lower()
            if code in LANGUAGES:
                return code
    except Exception:
        pass
    return "en"


def set_language(lang: str):
    """Set the active language."""
    global _current_lang
    if lang in LANGUAGES:
        _current_lang = lang
        logger.info(f"Language set to: {lang} ({LANGUAGES[lang]['name']})")


def get_language() -> str:
    """Get the current language code."""
    return _current_lang


def t(key: str, **kwargs) -> str:
    """Get the translated string for a key in the current language.
    
    Supports {placeholder} formatting via kwargs.
    Falls back to English, then to the key itself.
    """
    entry = TRANSLATIONS.get(key)
    if not entry:
        return key
    text = entry.get(_current_lang, entry.get("en", key))
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text
