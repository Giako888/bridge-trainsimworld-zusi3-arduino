"""Full PZB / LZB / MFA scan for the currently loaded train."""
import requests, json, sys, time, io

_buf = io.StringIO()
_orig_print = print
def print(*args, **kwargs):
    import builtins
    builtins.print(*args, **kwargs)
    _buf.write(" ".join(str(a) for a in args) + "\n")

BASE = "http://localhost:31270"
HDR = {"DTGCommKey": "KCfgFZ38yd8hRnlol2it4/qnEy92T0cPrMQnpNGcCtA=",
       "Content-Type": "application/json"}
F0 = "CurrentFormation/0"

def get(endpoint):
    try:
        r = requests.get(f"{BASE}/Query?objectPath={endpoint}", headers=HDR, timeout=2)
        if r.status_code == 200:
            d = r.json()
            return d.get("Value", d.get("value", "NO_VALUE_KEY"))
        return f"HTTP_{r.status_code}"
    except Exception as e:
        return f"ERR:{e}"

# ── Identify train ──
print("=" * 80)
print("  FULL PZB / LZB / MFA SCAN")
print("=" * 80)

train_id = get(f"{F0}.ObjectClass")
print(f"\nTrain: {train_id}")
print()

# ── PZB_V3 Properties ──
pzb_props = [
    "ProgramMode", "isReverserEngaged", "isStartup", "influenceCode",
    "ActiveMode", "SavedMode", "MaxSpeed", "OverspeedAllowance",
    "ActiveInfluence", "isOverridePressed", "isAcknowledgePressed",
    "isReleasePressed", "IsMoving", "_RequiresAcknowledge",
    "ActivationSpeed", "_restrictionID", "bIsPZB_Active", "bIsReady",
    "bIsSuppressed", "bIsGNT_Active", "RestrictionTimerStarted",
    "CorrectUseScore", "_isEnabled", "_InEmergency",
    "_IsPowerModified", "_PowerOutput"
]
pzb_funcs = [
    "SafetySystemIsUsedCorrectly", "PZB_GetRestrictionMaxSpeed",
    "PZB_GetIsReady", "PZB_GetEmergency", "PZB_GetOverspeed",
    "PZB_GetActiveState", "PZB_GetDataStruct", "PZB_GetProgramMode",
    "GetIsReady", "Get_Restriction_ActivateSpeed",
    "Get_Influence_MaxSpeed", "Get_InfluenceState", "Get_ActiveMode",
    "Get_InfluenceCode", "Get_Speed", "GetPowerInfluence",
    "IsPowerModified", "GetPowerOutput", "InEmergency",
    "IsEnabled", "IsActive"
]

print("-" * 80)
print("  PZB_V3 - Properties")
print("-" * 80)
for p in pzb_props:
    v = get(f"{F0}/PZB_V3.Property.{p}")
    print(f"  {p:40s} = {v}")

print()
print("-" * 80)
print("  PZB_V3 - Functions")
print("-" * 80)
for f in pzb_funcs:
    v = get(f"{F0}/PZB_V3.Function.{f}")
    print(f"  {f:40s} = {v}")

# ── Top-level PZB ──
print()
print("-" * 80)
print("  PZB Top-Level (CurrentFormation/0)")
print("-" * 80)
for ep in ["Property.PZB_Mode", "Function.GetPZBMode", "Function.GetIsPZBIsolated", "Function.GetPZBEmergencyState"]:
    v = get(f"{F0}.{ep}")
    print(f"  {ep:40s} = {v}")

# ── LZB Properties ──
lzb_props = [
    "LocoMaxSpeed", "FormationMaxSpeed", "DriverEnteredMaxSpeed",
    "bIsEnabled", "bIsIsolated", "bIsReady", "bIsActivated",
    "bIsOverspeedBraking", "bIsEmergencyBraking", "faultCode",
    "bIsOverrideRequired", "bIsReleaseRequired", "bIsAcknowledgeRequired",
    "bIsStopSignalPassed", "currentVelocity_ms", "EndeState",
    "E40_State", "V40_State", "currentSpeedLimit_ms",
    "maxPermisibleSpeed_ms", "expectedTargetSpeed_ms",
    "monitoringSpeed_ms", "targetSpeedDistance_m", "distanceToEnd_M",
    "OverspeedState", "DistanceToNextSignalM", "DisplayMessages",
    "bIsPermittedSpeedExpected", "bIsTargetSpeedActive",
    "OverspeedSpeed_ms", "bISTransmitFailure", "Enforcement",
    "ExitSignalDistance", "ExitSignalSpeedMs", "bSpawnedOnLZB",
    "ULightState", "AusfallGeschwinidigkeit",
    "AusfallGeschwinidigkeitBase", "bWasTransmitFailure",
    "bShowLZBDistance", "PZB Mode", "CorrectUseScore",
    "bReplicates", "bAutoActivate", "bIsEditorOnly"
]
lzb_funcs = [
    "SafetySystemIsUsedCorrectly", "LZB_GetIsBrakeDemandState",
    "LZB_GetShowLZBDistanceBare", "LZB_GetMonitoringSpeed",
    "LZB_GetTargetSpeedDistance", "LZB_GetExpectedTargetSpeed",
    "LZB_GetMaxPermissibleSpeed", "LZB_GetCurrentSpeedLimit",
    "LZB_GetIsEmergencyBraking", "LZB_GetIsOverspeedBraking",
    "LZB_GetFault", "LZB_GetIsActive", "LZB_GetIsReady",
    "LZB_GetIsIsolated", "LZB_GetIsEnabled",
    "GetMaxWeatherSpeed", "GetWasTransmitFailure",
    "GetUlightState", "IsThereASignalWeCouldEndeAt",
    "GetExpectedSpeedFromQuery", "CanResetIsOverrideRequired",
    "CanResetIsAcknowledgeRequired", "CanResetIsReleaseRequired",
    "CanSetIsReady", "GetFault", "GetIsIsolated",
    "GetIsActive", "GetIsTargetSpeedZero", "GetIsEnabled",
    "GetIsRailVehicleAboveZeroSpeed", "GetCurrentRailVehicleVelocity",
    "GetLZB_Restriction", "IsActive"
]

print()
print("-" * 80)
print("  LZB - Properties")
print("-" * 80)
for p in lzb_props:
    v = get(f"{F0}/LZB.Property.{p}")
    print(f"  {p:40s} = {v}")

print()
print("-" * 80)
print("  LZB - Functions")
print("-" * 80)
for f in lzb_funcs:
    v = get(f"{F0}/LZB.Function.{f}")
    print(f"  {f:40s} = {v}")

# ── Top-level LZB ──
print()
print("-" * 80)
print("  LZB Top-Level (CurrentFormation/0)")
print("-" * 80)
for ep in ["Function.GetIsLZBIsolated", "Function.GetLZBEmergencyState"]:
    v = get(f"{F0}.{ep}")
    print(f"  {ep:40s} = {v}")

# ── BR101_AFB LZB/PZB fields ──
afb_fields = [
    "PZB_MaximumSpeed", "LZB_MaximumSpeed", "LZB_VisibleMaximumSpeed",
    "bLZBIsActive", "bLZBEndeBrake", "bLZBWasActive",
    "bLZBEndeCountdown", "bLZBIsFault", "bLZBTMFCountdown",
    "bLZBTMFBrake", "bLZBPrepareBrake", "bLZBIsBraking",
    "Simulation_CurrentActivity_LZBPrepareBrake"
]
afb_funcs = [
    "GetIsLZBPreparingBrake", "GetIsLZBBraking",
    "GetIsLZBEndeCountdown", "GetIsLZBEndeBrake"
]

print()
print("-" * 80)
print("  BR101_AFB - Properties")
print("-" * 80)
for p in afb_fields:
    v = get(f"{F0}/BR101_AFB.Property.{p}")
    print(f"  {p:40s} = {v}")

print()
print("-" * 80)
print("  BR101_AFB - Functions")
print("-" * 80)
for f in afb_funcs:
    v = get(f"{F0}/BR101_AFB.Function.{f}")
    print(f"  {f:40s} = {v}")

# ── MFA Indicators ──
mfa = f"{F0}/MFA_Indicators.Property."
mfa_indicators = [
    # Ü
    "\u00dc_IsActive", "\u00dc_IsActive_Test",
    "\u00dc_IsInhibited_LZB_Fault", "\u00dc_IsFlashing",
    "\u00dc_IsFlashing_Test", "\u00dc_IsFlashing_LZB_Fault",
    # B
    "B_IsActive", "B_IsFlashing",
    # Ende
    "Ende_IsActive", "Ende_IsFlashing",
    # E40
    "E40_IsActive", "E40_IsFlashing",
    # V40
    "V40_IsActive", "V40_IsFlashing",
    # H
    "H_IsActive", "H_IsFlashing",
    # EL
    "EL_IsActive", "EL_IsFlashing",
    # Befehl40
    "Befehl40_IsActive_LZB", "Befehl40_IsFlashing_LZB",
    "Befehl40_IsActive_PZB",
    # 1000Hz
    "1000Hz_IsActive_PZB", "1000Hz_IsFlashing_PZB",
    "1000Hz_IsFlashing_BP", "1000Hz_IsFlashing_Cutout",
    "1000Hz_IsFlashing_FaultIsolation",
    # 500Hz
    "500Hz_IsActive",
    # G
    "G_IsActive_LZB", "G_IsFlashing_LZB",
    "G_IsActive_PZB", "G_IsFlashing_PZB",
    # S
    "S_IsActive_LZB", "S_IsFlashing_LZB",
    "S_IsActive_PZB", "S_IsActive_Test",
    # 55
    "55_IsActive_PZB", "55_IsActive_TrainData",
    "55_IsInhibited_LZB", "55_IsInhibited_Test",
    "55_IsFlashing_PZB", "55_IsFlashing_Grunddaten",
    # 70
    "70_IsActive_PZB", "70_IsActive_TrainData",
    "70_IsInhibited_LZB", "70_IsInhibited_Test",
    "70_IsFlashing_PZB", "70_IsFlashing_Inverted",
    "70_IsFlashing_Grunddaten",
    # 85
    "85_IsActive_PZB", "85_IsActive_TrainData",
    "85_IsFlashing_PZB", "85_IsFlashing_LZB",
    "85_IsFlashing_Grunddaten",
    # Stoer
    "Stoer_IsActive_LZB", "Stoer_IsActive_LZB_Fault",
    # Meta
    "DisplayingTrainData", "Ersatzzugdaten", "Grunddaten",
    "Stoer_Ersatzzugdaten", "Stoer_Grunddaten",
    "IsBelowGrunddatenSpeed", "ElectricalPower",
    "LZB_IsUnisolated", "Stoer_IsInhibited_Test",
    "Stoer_IsFlashing_FaultIsolation",
    "PZB_LZB_IndicatorTest", "LZB_IndicatorTest",
    "RefVHID_CutoutValve", "RefVHID_PZB_FaultIsolation",
    "RefVHID_LZB_FaultIsolation",
    "LZB_UseIsolationStateForB", "PZB_GrunddatenMode",
]
mfa_funcs_list = ["GetIsActivePZB", "IsActive"]

print()
print("-" * 80)
print("  MFA_Indicators - Properties")
print("-" * 80)
active_count = 0
for ind in mfa_indicators:
    v = get(f"{mfa}{ind}")
    flag = ""
    if v is True or (isinstance(v, (int, float)) and v not in (0, False)):
        flag = " <<<< ACTIVE"
        active_count += 1
    print(f"  {ind:45s} = {v}{flag}")

print()
print("-" * 80)
print("  MFA_Indicators - Functions")
print("-" * 80)
for f in mfa_funcs_list:
    v = get(f"{F0}/MFA_Indicators.Function.{f}")
    print(f"  {f:45s} = {v}")

# ── SIFA quick check ──
print()
print("-" * 80)
print("  SIFA (quick)")
print("-" * 80)
sifa_eps = [
    ("IsSifaActive", f"{F0}.Function.IsSifaActive"),
    ("IsSifaCutIn", f"{F0}.Function.IsSifaCutIn"),
    ("bEnabledState", f"{F0}/BP_Sifa_Service.Property.bEnabledState"),
    ("bActiveState", f"{F0}/BP_Sifa_Service.Property.bActiveState"),
    ("WarningState", f"{F0}/BP_Sifa_Service.Property.WarningState"),
    ("WarningStateVisual", f"{F0}/BP_Sifa_Service.Property.WarningStateVisual"),
    ("inPenaltyBrakeApplication", f"{F0}/BP_Sifa_Service.Property.inPenaltyBrakeApplication"),
]
for name, ep in sifa_eps:
    v = get(ep)
    print(f"  {name:40s} = {v}")

# ── Summary ──
print()
print("=" * 80)
print(f"  MFA Active indicators: {active_count}")
print("=" * 80)
print("\nSCAN COMPLETE")

with open(r"c:\Users\Giako\Desktop\progetto2\tsw6_joystick_bridge\scan_output.txt", "w", encoding="utf-8") as _f:
    _f.write(_buf.getvalue())
_orig_print(">>> Saved to scan_output.txt")
