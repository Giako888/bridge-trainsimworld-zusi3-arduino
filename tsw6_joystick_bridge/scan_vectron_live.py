"""Read live values from Vectron PZB_Service_V3, LZB_Service, BP_Sifa_Service"""
import requests, urllib.parse, time

BASE = "http://127.0.0.1:31270"
HDR = {"DTGCommKey": "KCfgFZ38yd8hRnlol2it4/qnEy92T0cPrMQnpNGcCtA="}

def encode_path(path: str) -> str:
    parts, result, sep = [], [], ""
    for ch in path:
        if ch in ("/", "."):
            if parts:
                result.append(urllib.parse.quote("".join(parts), safe=""))
                parts = []
            result.append(ch)
        else:
            parts.append(ch)
    if parts:
        result.append(urllib.parse.quote("".join(parts), safe=""))
    return "".join(result)

def get_val(path):
    try:
        r = requests.get(f"{BASE}/get/{encode_path(path)}", headers=HDR, timeout=2)
        if r.status_code == 200:
            j = r.json()
            if j.get("Result") == "Success":
                return j.get("Values", {})
        return f"HTTP_{r.status_code}"
    except:
        return "ERR"

PREFIX = "CurrentFormation/0/"

# PZB_Service_V3 key properties
pzb_props = [
    "PZB_Service_V3.Property.ProgramMode",
    "PZB_Service_V3.Property.ActiveMode",
    "PZB_Service_V3.Property.bIsPZB_Active",
    "PZB_Service_V3.Property.bIsLZB_Active", 
    "PZB_Service_V3.Property.bIsReady",
    "PZB_Service_V3.Property.bIsSuppressed",
    "PZB_Service_V3.Property.bIsGNT_Active",
    "PZB_Service_V3.Property._isEnabled",
    "PZB_Service_V3.Property._InEmergency",
    "PZB_Service_V3.Property._RequiresAcknowledge",
    "PZB_Service_V3.Property._restrictionID",
    "PZB_Service_V3.Property.Handle_OverspeedMaxSpeed",
    "PZB_Service_V3.Property.Handle_RestrictionSpeed",
    "PZB_Service_V3.Property.ActivationSpeed",
    "PZB_Service_V3.Property.IsMoving",
    "PZB_Service_V3.Property.isOverridePressed",
    "PZB_Service_V3.Property.isAcknowledgePressed",
    "PZB_Service_V3.Property.isReleasePressed",
    "PZB_Service_V3.Property.DebugModeState",
]

# PZB_Service_V3 functions
pzb_funcs = [
    "PZB_Service_V3.Function.Get_ActiveMode",
    "PZB_Service_V3.Function.Get_InfluenceCode",
    "PZB_Service_V3.Function.Get_InfluenceState",
    "PZB_Service_V3.Function.PZB_GetProgramMode",
    "PZB_Service_V3.Function.PZB_GetActiveState",
    "PZB_Service_V3.Function.PZB_GetIsReady",
    "PZB_Service_V3.Function.PZB_GetIsLZBActive",
    "PZB_Service_V3.Function.PZB_GetEmergency",
    "PZB_Service_V3.Function.PZB_GetOverspeed",
    "PZB_Service_V3.Function.PZB_GetDataStruct",
    "PZB_Service_V3.Function.GetPowerInfluence",
]

# LZB_Service key properties
lzb_props = [
    "LZB_Service.Property.bIsEnabled",
    "LZB_Service.Property.bIsIsolated",
    "LZB_Service.Property.bIsReady",
    "LZB_Service.Property.bIsActivated",
    "LZB_Service.Property.faultCode",
    "LZB_Service.Property.currentVelocity_ms",
    "LZB_Service.Property.EndeState",
    "LZB_Service.Property.E40_State",
    "LZB_Service.Property.V40_State",
    "LZB_Service.Property.ULightState",
    "LZB_Service.Property.BlueColour",
    "LZB_Service.Property.RedColour",
    "LZB_Service.Property.YellowColour",
    "LZB_Service.Property.bIsPermittedSpeedExpected",
    "LZB_Service.Property.bIsTargetSpeedActive",
    "LZB_Service.Property.OverspeedSpeed_ms",
    "LZB_Service.Property.Enforcement",
    "LZB_Service.Property.bSpawnedOnLZB",
    "LZB_Service.Property.bISTransmitFailure",
]

# Top-level PZB/LZB/SIFA
top_props = [
    "Property.PZB_Mode",
    "Property.LZB_TargetSetPoint",
    "Property.MonitoringSpeed_LZB",
    "Property.maxSpeed_LZB",
    "Property.RegionSafetySystem",
    "Property.SifaPenaltyState",
    "Property.PenaltyBrakeActive",
    "Function.GetExpectedPZBMode",
]

# BP_Sifa_Service
sifa_props = [
    "BP_Sifa_Service.Property.WarningState",
    "BP_Sifa_Service.Property.WarningStateVisual",
    "BP_Sifa_Service.Property.WarningStateAuditory",
    "BP_Sifa_Service.Property.bEnabledState",
    "BP_Sifa_Service.Property.bActiveState",
    "BP_Sifa_Service.Property.bPedalIsPressed",
    "BP_Sifa_Service.Property.inPenaltyBrakeApplication",
    "BP_Sifa_Service.Property.bIsCutIn",
    "BP_Sifa_Service.Property.MinimumSpeedMet",
]

print("=" * 70)
print("  VECTRON LIVE VALUES")
print("=" * 70)

for label, endpoints in [
    ("PZB_Service_V3 Properties", pzb_props),
    ("PZB_Service_V3 Functions", pzb_funcs),
    ("LZB_Service Properties", lzb_props),
    ("Top-Level PZB/LZB/SIFA", top_props),
    ("BP_Sifa_Service", sifa_props),
]:
    print(f"\n--- {label} ---")
    for ep in endpoints:
        path = PREFIX + ep
        val = get_val(path)
        name = ep.split(".")[-1]
        print(f"  {name:40s} = {val}")
        time.sleep(0.05)

print("\n" + "=" * 70)
print("Done!")
