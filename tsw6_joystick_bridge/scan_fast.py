"""Fast PZB / LZB / MFA scan using correct /get/ API format."""
import requests, re, sys
from urllib.parse import quote

BASE = "http://localhost:31270"
KEY = "KCfgFZ38yd8hRnlol2it4/qnEy92T0cPrMQnpNGcCtA="
F0 = "CurrentFormation/0"

session = requests.Session()
session.headers.update({"DTGCommKey": KEY})

lines = []

def encode_path(path):
    parts = re.split(r'([/.])', path)
    return "".join(part if part in ("/", ".") else quote(part, safe="") for part in parts)

def log(msg=""):
    lines.append(msg)

def get(endpoint):
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
            return d.get("Value", "NO_VALUE")
        return f"HTTP_{r.status_code}"
    except requests.exceptions.Timeout:
        return "TIMEOUT"
    except requests.exceptions.ConnectionError:
        return "CONN_ERR"
    except Exception as e:
        return f"ERR:{type(e).__name__}"

# ── Quick connectivity test ──
test = get(f"{F0}.ObjectClass")
if isinstance(test, str) and ("ERR" in test or "CONN" in test or "TIMEOUT" in test):
    print(f"ERRORE: API non raggiungibile -> {test}")
    print("Assicurati che TSW6 sia in esecuzione con un treno caricato.")
    sys.exit(1)

# ── Train ID ──
log("=" * 70)
log(f"  Train: {test}")
log(f"  Name:  {get(f'{F0}.ObjectName')}")
log("=" * 70)

# ── PZB_V3 Properties ──
pzb_props = [
    "ProgramMode", "ActiveMode", "SavedMode", "MaxSpeed",
    "bIsPZB_Active", "bIsReady", "_isEnabled", "_InEmergency",
    "bIsSuppressed", "bIsGNT_Active", "influenceCode", "ActiveInfluence",
    "isReverserEngaged", "IsMoving", "ActivationSpeed",
]
log("\n--- PZB_V3 Properties ---")
for p in pzb_props:
    v = get(f"{F0}/PZB_V3.Property.{p}")
    flag = " <<<<" if v is True or (isinstance(v, (int, float)) and v not in (0, 0.0, False)) else ""
    log(f"  {p:35s} = {v}{flag}")

pzb_funcs = ["PZB_GetActiveState", "PZB_GetIsReady", "PZB_GetEmergency",
             "PZB_GetProgramMode", "IsEnabled", "IsActive", "InEmergency"]
log("\n--- PZB_V3 Functions ---")
for f in pzb_funcs:
    v = get(f"{F0}/PZB_V3.Function.{f}")
    flag = " <<<<" if v is True else ""
    log(f"  {f:35s} = {v}{flag}")

# ── PZB Top-level ──
log("\n--- PZB Top-Level ---")
for ep in ["Property.PZB_Mode", "Function.GetPZBMode", "Function.GetIsPZBIsolated", "Function.GetPZBEmergencyState"]:
    v = get(f"{F0}.{ep}")
    flag = " <<<<" if v is True or (isinstance(v, (int, float)) and v not in (0, 0.0, False)) else ""
    log(f"  {ep:40s} = {v}{flag}")

# ── LZB Properties ──
lzb_props = [
    "bIsEnabled", "bIsIsolated", "bIsReady", "bIsActivated",
    "bIsOverspeedBraking", "bIsEmergencyBraking", "faultCode",
    "currentVelocity_ms", "currentSpeedLimit_ms", "EndeState",
    "E40_State", "V40_State", "ULightState", "PZB Mode",
    "LocoMaxSpeed", "FormationMaxSpeed",
]
log("\n--- LZB Properties ---")
for p in lzb_props:
    v = get(f"{F0}/LZB.Property.{p}")
    flag = " <<<<" if v is True or (isinstance(v, (int, float)) and v not in (0, 0.0, False)) else ""
    log(f"  {p:35s} = {v}{flag}")

lzb_funcs = ["LZB_GetIsActive", "LZB_GetIsReady", "LZB_GetIsEnabled",
             "LZB_GetIsIsolated", "LZB_GetFault", "IsActive"]
log("\n--- LZB Functions ---")
for f in lzb_funcs:
    v = get(f"{F0}/LZB.Function.{f}")
    flag = " <<<<" if v is True else ""
    log(f"  {f:35s} = {v}{flag}")

# ── LZB Top-Level ──
log("\n--- LZB Top-Level ---")
for ep in ["Function.GetIsLZBIsolated", "Function.GetLZBEmergencyState"]:
    v = get(f"{F0}.{ep}")
    log(f"  {ep:40s} = {v}")

# ── BR101_AFB ──
log("\n--- BR101_AFB ---")
for p in ["PZB_MaximumSpeed", "LZB_MaximumSpeed", "bLZBIsActive", "bLZBIsFault"]:
    v = get(f"{F0}/BR101_AFB.Property.{p}")
    log(f"  {p:35s} = {v}")

# ── MFA Indicators (ALL) ──
mfa = f"{F0}/MFA_Indicators.Property."
mfa_eps = [
    "\u00dc_IsActive", "\u00dc_IsActive_Test", "\u00dc_IsInhibited_LZB_Fault",
    "\u00dc_IsFlashing", "\u00dc_IsFlashing_Test", "\u00dc_IsFlashing_LZB_Fault",
    "B_IsActive", "B_IsFlashing",
    "Ende_IsActive", "Ende_IsFlashing",
    "E40_IsActive", "E40_IsFlashing",
    "V40_IsActive", "V40_IsFlashing",
    "H_IsActive", "H_IsFlashing",
    "EL_IsActive", "EL_IsFlashing",
    "Befehl40_IsActive_LZB", "Befehl40_IsFlashing_LZB", "Befehl40_IsActive_PZB",
    "1000Hz_IsActive_PZB", "1000Hz_IsFlashing_PZB", "1000Hz_IsFlashing_BP",
    "1000Hz_IsFlashing_Cutout", "1000Hz_IsFlashing_FaultIsolation",
    "500Hz_IsActive",
    "G_IsActive_LZB", "G_IsFlashing_LZB", "G_IsActive_PZB", "G_IsFlashing_PZB",
    "S_IsActive_LZB", "S_IsFlashing_LZB", "S_IsActive_PZB", "S_IsActive_Test",
    "55_IsActive_PZB", "55_IsActive_TrainData", "55_IsInhibited_LZB",
    "55_IsInhibited_Test", "55_IsFlashing_PZB", "55_IsFlashing_Grunddaten",
    "70_IsActive_PZB", "70_IsActive_TrainData", "70_IsInhibited_LZB",
    "70_IsInhibited_Test", "70_IsFlashing_PZB", "70_IsFlashing_Inverted",
    "70_IsFlashing_Grunddaten",
    "85_IsActive_PZB", "85_IsActive_TrainData",
    "85_IsFlashing_PZB", "85_IsFlashing_LZB", "85_IsFlashing_Grunddaten",
    "Stoer_IsActive_LZB", "Stoer_IsActive_LZB_Fault",
    "DisplayingTrainData", "Ersatzzugdaten", "Grunddaten",
    "Stoer_Ersatzzugdaten", "Stoer_Grunddaten",
    "IsBelowGrunddatenSpeed", "ElectricalPower", "LZB_IsUnisolated",
    "Stoer_IsInhibited_Test", "Stoer_IsFlashing_FaultIsolation",
    "PZB_LZB_IndicatorTest", "LZB_IndicatorTest",
    "RefVHID_CutoutValve", "RefVHID_PZB_FaultIsolation",
    "RefVHID_LZB_FaultIsolation",
    "LZB_UseIsolationStateForB", "PZB_GrunddatenMode",
]

log("\n--- MFA Indicators ---")
active_mfa = []
for ep in mfa_eps:
    v = get(f"{mfa}{ep}")
    flag = ""
    if v is True or (isinstance(v, (int, float)) and v not in (0, 0.0, False)):
        flag = " <<<< ACTIVE"
        active_mfa.append(ep)
    log(f"  {ep:45s} = {v}{flag}")

# MFA Functions
log("\n--- MFA Functions ---")
for f in ["GetIsActivePZB", "IsActive"]:
    v = get(f"{F0}/MFA_Indicators.Function.{f}")
    log(f"  {f:35s} = {v}")

# ── SIFA ──
log("\n--- SIFA ---")
sifa_eps = [
    ("IsSifaActive", f"{F0}.Function.IsSifaActive"),
    ("IsSifaCutIn", f"{F0}.Function.IsSifaCutIn"),
    ("bEnabledState", f"{F0}/BP_Sifa_Service.Property.bEnabledState"),
    ("bActiveState", f"{F0}/BP_Sifa_Service.Property.bActiveState"),
    ("WarningState", f"{F0}/BP_Sifa_Service.Property.WarningState"),
    ("WarningStateVisual", f"{F0}/BP_Sifa_Service.Property.WarningStateVisual"),
    ("inPenaltyBrake", f"{F0}/BP_Sifa_Service.Property.inPenaltyBrakeApplication"),
]
for name, ep in sifa_eps:
    v = get(ep)
    log(f"  {name:35s} = {v}")

# ── Summary ──
log(f"\n{'='*70}")
log(f"  ACTIVE MFA INDICATORS: {len(active_mfa)}")
for a in active_mfa:
    log(f"    >>> {a}")
log("=" * 70)

# Write file
outpath = r"c:\Users\Giako\Desktop\progetto2\tsw6_joystick_bridge\scan_output.txt"
with open(outpath, "w", encoding="utf-8") as fout:
    fout.write("\n".join(lines))

print(f"\nSCAN COMPLETE - {len(lines)} lines -> scan_output.txt")
print(f"Train: {test}")
print(f"Active MFA: {len(active_mfa)}")
for a in active_mfa:
    print(f"  >>> {a}")
