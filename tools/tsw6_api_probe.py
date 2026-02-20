"""
TSW6 API Probe — Investigazione endpoint per EBuLa
===================================================
Script di ricerca per scoprire quali dati TSW6 espone 
che potrebbero essere utilizzati per un display EBuLa.

Uso: python tools/tsw6_api_probe.py
(TSW6 deve essere in esecuzione con -HTTPAPI e un treno in guida)
"""

import sys
import os
import json
import time

# Aggiungi parent dir al path per importare tsw6_api
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tsw6_api import TSW6API, TSW6APIError, TSW6ConnectionError


def probe_endpoint(api: TSW6API, path: str, label: str = "") -> dict:
    """Prova un endpoint e stampa il risultato raw"""
    try:
        raw = api.get_raw(path)
        display = label or path
        print(f"\n{'='*60}")
        print(f"📍 {display}")
        print(f"   Path: {path}")
        print(f"   Raw:  {json.dumps(raw, indent=2, default=str)}")
        return raw
    except TSW6ConnectionError as e:
        print(f"\n❌ {label or path}: Connessione fallita — {e}")
        return {}
    except TSW6APIError as e:
        print(f"\n⚠️  {label or path}: API Error — {e}")
        return {}


def probe_list(api: TSW6API, path: str, label: str = "") -> dict:
    """Lista nodi sotto un path"""
    try:
        raw = api.list_nodes(path)
        display = label or path
        print(f"\n{'='*60}")
        print(f"📂 {display}")
        print(f"   Path: /list/{path}")
        
        nodes = raw.get("Nodes", [])
        endpoints = raw.get("Endpoints", [])
        
        if nodes:
            print(f"   Nodi ({len(nodes)}):")
            for n in nodes[:30]:
                if isinstance(n, dict):
                    print(f"     📁 {n.get('Name', n)}")
                else:
                    print(f"     📁 {n}")
        
        if endpoints:
            print(f"   Endpoint ({len(endpoints)}):")
            for ep in endpoints[:50]:
                if isinstance(ep, dict):
                    name = ep.get("Name", ep)
                    writable = " [W]" if ep.get("Writable") else ""
                    print(f"     📌 {name}{writable}")
                else:
                    print(f"     📌 {ep}")
        
        return raw
    except TSW6APIError as e:
        print(f"\n⚠️  {label or path}: {e}")
        return {}


def main():
    print("=" * 60)
    print("TSW6 API Probe — Investigazione EBuLa")
    print("=" * 60)
    
    api = TSW6API()
    try:
        api.connect()
        print(f"✅ Connesso a TSW6 su {api.base_url}")
    except Exception as e:
        print(f"❌ Connessione fallita: {e}")
        print("   Assicurati che TSW6 sia in esecuzione con -HTTPAPI")
        return
    
    # ===== 1. INFO TRENO =====
    print("\n\n" + "=" * 60)
    print("1️⃣  INFO TRENO")
    print("=" * 60)
    
    probe_endpoint(api, "CurrentFormation/0.ObjectClass", "Classe treno")
    
    # ===== 2. DRIVER AID (sistema aiuto macchinista) =====
    print("\n\n" + "=" * 60)
    print("2️⃣  DRIVER AID")
    print("=" * 60)
    
    probe_list(api, "DriverAid", "DriverAid — nodi disponibili")
    probe_endpoint(api, "DriverAid.Data", "DriverAid.Data")
    probe_endpoint(api, "DriverAid.PlayerInfo", "DriverAid.PlayerInfo")
    probe_endpoint(api, "DriverAid.TrackData", "DriverAid.TrackData")
    
    # ===== 3. TIME OF DAY =====
    print("\n\n" + "=" * 60)
    print("3️⃣  TIME OF DAY")
    print("=" * 60)
    
    probe_list(api, "TimeOfDay", "TimeOfDay — nodi")
    probe_endpoint(api, "TimeOfDay.Data", "TimeOfDay.Data")
    
    # ===== 4. SPEED & POSITION =====
    print("\n\n" + "=" * 60)
    print("4️⃣  SPEED & POSITION")
    print("=" * 60)
    
    probe_endpoint(api, "CurrentDrivableActor.Function.HUD_GetSpeed", "Velocità (m/s)")
    
    # Prova endpoint di posizione/distanza comuni
    position_endpoints = [
        "CurrentDrivableActor.Function.HUD_GetDistanceTravelled",
        "CurrentDrivableActor.Function.GetDistanceTravelled",
        "CurrentDrivableActor.Function.HUD_GetGradient",
        "CurrentDrivableActor.Function.GetGradient",
        "CurrentDrivableActor.Function.HUD_GetNextSpeedLimit",
        "CurrentDrivableActor.Function.GetNextSpeedLimit",
        "CurrentDrivableActor.Function.HUD_GetTrackKilometre",
        "CurrentDrivableActor.Function.GetTrackKilometre",
        "CurrentDrivableActor.Function.HUD_GetNextSignal",
        "CurrentDrivableActor.Function.HUD_GetCurrentSpeedLimit",
        "CurrentDrivableActor.Function.GetCurrentSpeedLimit",
        "CurrentDrivableActor.Function.HUD_GetNextStopDistance",
        "CurrentDrivableActor.Function.GetNextStopDistance",
        "CurrentDrivableActor.Function.HUD_GetNextStation",
        "CurrentDrivableActor.Function.HUD_GetSchedule",
        "CurrentDrivableActor.Function.HUD_GetTimetable",
    ]
    
    for ep in position_endpoints:
        probe_endpoint(api, ep, ep.split(".")[-1])
    
    # ===== 5. ESPLORAZIONE CurrentDrivableActor =====
    print("\n\n" + "=" * 60)
    print("5️⃣  ESPLORAZIONE CurrentDrivableActor")
    print("=" * 60)
    
    probe_list(api, "CurrentDrivableActor", "CurrentDrivableActor — nodi top-level")
    
    # Cerca nodi interessanti
    interesting_paths = [
        "CurrentDrivableActor/Simulation",
        "CurrentDrivableActor/HUD",
        "CurrentDrivableActor/Journey",
        "CurrentDrivableActor/Route",
        "CurrentDrivableActor/Schedule",
        "CurrentDrivableActor/Timetable",
        "CurrentDrivableActor/Navigation",
    ]
    
    for path in interesting_paths:
        probe_list(api, path, path)
    
    # ===== 6. ESPLORAZIONE ROOT =====
    print("\n\n" + "=" * 60)
    print("6️⃣  ESPLORAZIONE ROOT")
    print("=" * 60)
    
    root_data = probe_list(api, "", "Root — nodi top-level")
    
    # Se troviamo nodi interessanti al root, esploriamoli
    nodes = root_data.get("Nodes", [])
    interesting_keywords = ["route", "track", "journey", "timetable", "schedule", 
                          "station", "signal", "distance", "position", "kilomet",
                          "driver", "hud", "navigation", "service"]
    
    for node in nodes:
        name = node.get("Name", node) if isinstance(node, dict) else str(node)
        name_lower = name.lower()
        if any(kw in name_lower for kw in interesting_keywords):
            probe_list(api, name, f"Root/{name}")
    
    # ===== 7. CURRENTFORMATION ESPLORAZIONE =====
    print("\n\n" + "=" * 60)
    print("7️⃣  CURRENT FORMATION")
    print("=" * 60)
    
    probe_list(api, "CurrentFormation", "CurrentFormation — nodi")
    probe_list(api, "CurrentFormation/0", "CurrentFormation/0 — locomotiva")
    
    # ===== 8. MONITORAGGIO POSIZIONE — 5 secondi =====
    print("\n\n" + "=" * 60)
    print("8️⃣  MONITORAGGIO VELOCITÀ/POSIZIONE (5 secondi)")
    print("=" * 60)
    
    for i in range(5):
        try:
            speed_ms = api.get("CurrentDrivableActor.Function.HUD_GetSpeed")
            speed_kmh = float(speed_ms) * 3.6 if speed_ms is not None else 0
            
            time_data = api.get_raw("TimeOfDay.Data")
            
            # Prova DriverAid
            player_info = None
            try:
                player_info = api.get_raw("DriverAid.PlayerInfo")
            except:
                pass
            
            track_data = None
            try:
                track_data = api.get_raw("DriverAid.TrackData")
            except:
                pass
            
            print(f"\n  [{i+1}/5] Velocità: {speed_kmh:.1f} km/h")
            if time_data:
                print(f"          TimeOfDay: {json.dumps(time_data, default=str)[:200]}")
            if player_info:
                print(f"          PlayerInfo: {json.dumps(player_info, default=str)[:200]}")
            if track_data:
                print(f"          TrackData: {json.dumps(track_data, default=str)[:200]}")
            
        except Exception as e:
            print(f"  [{i+1}/5] Errore: {e}")
        
        time.sleep(1)
    
    # ===== 9. RICERCA PROFONDA ENDPOINT =====
    print("\n\n" + "=" * 60)
    print("9️⃣  RICERCA ENDPOINT (parole chiave)")
    print("=" * 60)
    
    keywords = ["Speed", "Distance", "Position", "Station", "Signal",
                "Gradient", "Kilomet", "Schedule", "Time", "Route", "Track",
                "Journey", "Timetable", "Stop", "Next", "HUD"]
    
    print(f"Ricerca in corso per: {', '.join(keywords)}")
    print("(Potrebbe richiedere 30-60 secondi...)")
    
    try:
        results = api.search_endpoints(
            path="CurrentDrivableActor",
            keywords=keywords,
            max_depth=3,
            progress_callback=lambda p: print(f"  Scansione: {p}", end="\r")
        )
        
        print(f"\n\nTrovati {len(results)} endpoint rilevanti:")
        for ep in sorted(results, key=lambda x: x["path"]):
            w = " [W]" if ep.get("writable") else ""
            print(f"  📌 {ep['path']}{w}")
    except Exception as e:
        print(f"Errore durante ricerca: {e}")
    
    # ===== RIEPILOGO =====
    print("\n\n" + "=" * 60)
    print("📋 RIEPILOGO")
    print("=" * 60)
    print("""
    Questo script ha esplorato gli endpoint TSW6 rilevanti per EBuLa.
    
    Dati necessari per EBuLa:
    ✅ Velocità attuale (HUD_GetSpeed) — disponibile
    ✅ Ora simulazione (TimeOfDay.Data) — disponibile
    ❓ Posizione treno (km/distanza) — da verificare (DriverAid?)
    ❓ Limite velocità corrente — da verificare
    ❓ Prossimo segnale/fermata — da verificare
    ❓ Dati orario/timetable — probabilmente NON disponibile via API
    
    Per TSW6: potrebbe servire un sistema a profili/timetable esterni
    dove gli utenti creano file JSON con i dati della tratta.
    """)
    
    api.disconnect()


if __name__ == "__main__":
    main()
