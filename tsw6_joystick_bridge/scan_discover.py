"""Discover all components on the Vectron using /list API (Nodes/Endpoints format)."""
import requests, re, sys, json
from urllib.parse import quote

BASE = "http://localhost:31270"
KEY = "KCfgFZ38yd8hRnlol2it4/qnEy92T0cPrMQnpNGcCtA="
F0 = "CurrentFormation/0"

session = requests.Session()
session.headers.update({"DTGCommKey": KEY})

def encode_path(path):
    parts = re.split(r'([/.])', path)
    return "".join(part if part in ("/", ".") else quote(part, safe="") for part in parts)

def api_list(path=""):
    try:
        url = f"{BASE}/list"
        if path:
            url += f"/{encode_path(path)}"
        r = session.get(url, timeout=5)
        if r.status_code == 200:
            return r.json()
        return {"_error": f"HTTP_{r.status_code}"}
    except Exception as e:
        return {"_error": str(e)}

def get_val(endpoint):
    try:
        url = f"{BASE}/get/{encode_path(endpoint)}"
        r = session.get(url, timeout=1.5)
        if r.status_code == 200:
            d = r.json()
            if d.get("Result") == "Success" and "Values" in d:
                vals = d["Values"]
                if isinstance(vals, dict) and vals:
                    return list(vals.values())[0]
                return vals
        return None
    except:
        return None

lines = []
def log(msg=""):
    lines.append(msg)
    print(msg)

# ── Train ID ──
train = get_val(f"{F0}.ObjectClass") or "???"
log(f"{'='*70}")
log(f"  Train: {train}")
log(f"{'='*70}")

# ── List direct children (Nodes) of CurrentFormation/0 ──
log(f"\n--- ALL NODES under {F0} ---")
data = api_list(F0)

node_names = []
if isinstance(data, dict):
    # Extract Nodes
    nodes = data.get("Nodes", [])
    for n in nodes:
        name = n.get("Name", str(n)) if isinstance(n, dict) else str(n)
        node_names.append(name)
    
    # Extract Endpoints at this level
    endpoints = data.get("Endpoints", [])
    ep_names = []
    for e in endpoints:
        name = e.get("Name", str(e)) if isinstance(e, dict) else str(e)
        ep_names.append(name)

node_names.sort()
for name in node_names:
    log(f"  {name}")
log(f"\n  Total nodes: {len(node_names)}")

if ep_names:
    log(f"\n--- TOP-LEVEL ENDPOINTS of {F0} ({len(ep_names)}) ---")
    for name in sorted(ep_names):
        log(f"  {name}")

# ── Filter for safety system related ──
kw_safety = ["pzb", "lzb", "etcs", "mfa", "indic", "safety", "sifa", "sicher",
             "zugsicher", "vigilance", "atc", "atp", "warn", "monitor",
             "panel", "display", "lamp", "brake", "emergency", "speed",
             "restrict", "_v3", "_v2", "service", "driver_assist", "driverassist"]

log(f"\n--- SAFETY / PZB / LZB / ETCS RELATED NODES ---")
safety_nodes = []
for name in node_names:
    nl = name.lower()
    if any(k in nl for k in kw_safety):
        safety_nodes.append(name)
        log(f"  {name}")

if not safety_nodes:
    log(f"  (none found by keyword filter)")

# Show ALL nodes anyway (less than ~200 expected)
log(f"\n  All {len(node_names)} nodes listed above for manual review")

# ── Deep-scan each safety node: list its sub-nodes and endpoints ──
log(f"\n{'='*70}")
log(f"  DETAILED SCAN OF INTERESTING NODES")
log(f"{'='*70}")

# Scan ALL nodes if there are few, otherwise just safety ones
nodes_to_scan = node_names if len(node_names) < 150 else safety_nodes

for comp in nodes_to_scan:
    detail = api_list(f"{F0}/{comp}")
    if isinstance(detail, dict) and "_error" not in detail:
        sub_nodes = detail.get("Nodes", [])
        sub_eps = detail.get("Endpoints", [])
        if sub_nodes or sub_eps:
            # Only show nodes with PZB/LZB/ETCS/MFA/safety content, OR show all if few
            sub_node_names = [n.get("Name", str(n)) if isinstance(n, dict) else str(n) for n in sub_nodes]
            sub_ep_names = [e.get("Name", str(e)) if isinstance(e, dict) else str(e) for e in sub_eps]
            
            all_text = " ".join(sub_node_names + sub_ep_names).lower()
            is_interesting = any(k in all_text for k in ["pzb", "lzb", "etcs", "mfa", "indic",
                                                          "safety", "sifa", "monitor", "active",
                                                          "flash", "warn", "emerg", "speed"])
            is_interesting = is_interesting or any(k in comp.lower() for k in kw_safety)
            is_interesting = is_interesting or len(node_names) < 100  # show all if small tree
            
            if is_interesting:
                log(f"\n  >>> {comp}  ({len(sub_node_names)} nodes, {len(sub_ep_names)} endpoints)")
                for sn in sub_node_names[:30]:
                    log(f"      [N] {sn}")
                for se in sub_ep_names[:60]:
                    log(f"      [E] {se}")

# ── Write output ──
outpath = r"c:\Users\Giako\Desktop\progetto2\tsw6_joystick_bridge\scan_discover.txt"
with open(outpath, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"\n>>> Saved {len(lines)} lines to scan_discover.txt")
