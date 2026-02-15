"""Test porte: singolo snapshot di tutti gli endpoint porte.
Uso: python _test_doors.py [LABEL]
Eseguilo con porte chiuse, poi con porte aperte, e confronta."""
import requests
import re
import sys
import time
from urllib.parse import quote

BASE = "http://localhost:31270"
KEY  = "KCfgFZ38yd8hRnlol2it4/qnEy92T0cPrMQnpNGcCtA="
HDR  = {"DTGCommKey": KEY}


def encode_path(path: str) -> str:
    """URL-encode segmenti preservando / e . come separatori."""
    parts = re.split(r'([/.])', path)
    return ''.join(part if part in ('/', '.') else quote(part, safe='') for part in parts)


endpoints = [
    "CurrentFormation/0/PassengerDoorSelector_F.InputValue",
    "CurrentFormation/0/PassengerDoorSelector_F.Function.GetCurrentOutputValue",
    "CurrentFormation/0/PassengerDoorSelector_F.Function.GetCurrentInputValue",
    "CurrentFormation/0/PassengerDoorSelector_R.InputValue",
    "CurrentFormation/0/PassengerDoorSelector_R.Function.GetCurrentOutputValue",
    "CurrentFormation/0/PassengerDoorSelector_R.Function.GetCurrentInputValue",
    "CurrentFormation/0/PassengerDoorSelector_B.InputValue",
    "CurrentFormation/0/PassengerDoorSelector_B.Function.GetCurrentOutputValue",
    "CurrentFormation/0/PassengerDoorSelector_B.Function.GetCurrentInputValue",
    "CurrentFormation/0/DoorControl.InputValue",
    "CurrentFormation/0/DoorControl.Function.GetCurrentOutputValue",
    "CurrentFormation/0/DoorControl.Function.GetCurrentInputValue",
    "CurrentFormation/0.Property.DoorLockSignal",
    "CurrentFormation/0.Property.bDoorsOpenLeft",
    "CurrentFormation/0.Property.bDoorsOpenRight",
    "CurrentFormation/0.Property.bDoorsClosedLeft",
    "CurrentFormation/0.Property.bDoorsClosedRight",
    "CurrentFormation/0.Property.bDoorLeftIndicator",
    "CurrentFormation/0.Property.bDoorRightIndicator",
    "CurrentFormation/0.Property.bPassengerDoorsLocked",
    "CurrentFormation/0.Property.bPassengerDoorsOpen",
    "CurrentFormation/0.Function.IsDoorCable_Enabled",
    "CurrentFormation/0/LSS_46F100_UIC-BGT_DoorControl.InputValue",
]

label = sys.argv[1] if len(sys.argv) > 1 else "SNAPSHOT"
ts = time.strftime("%H:%M:%S")
print(f"=== {label} ({ts}) ===")

session = requests.Session()
session.headers.update(HDR)

for ep in endpoints:
    url = BASE + "/get/" + encode_path(ep)
    short = ep.split("/")[-1] if "/" in ep else ep
    try:
        r = session.get(url, timeout=5)
        j = r.json()
        if j.get("Result") == "Success":
            val = list(j.get("Values", {}).values())[0] if j.get("Values") else "?"
        else:
            val = "N/A"
    except Exception:
        val = "ERR"
    marker = ""
    if val is True or (isinstance(val, (int, float)) and val > 0 and val != 0.5):
        marker = " <-- ATTIVO"
    print(f"  {short:55s} = {str(val):10s}{marker}")

print(f"\nDone ({time.strftime('%H:%M:%S')})")
