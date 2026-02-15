import requests

s = requests.Session()
s.headers.update({'DTGCommKey': 'KCfgFZ38yd8hRnlol2it4/qnEy92T0cPrMQnpNGcCtA='})
base = 'http://127.0.0.1:31270'

sifa_eps = [
    'CurrentFormation/0/BP_Sifa_Service.Property.WarningStateVisual',
    'CurrentFormation/0/BP_Sifa_Service.Property.WarningState',
    'CurrentFormation/0/BP_Sifa_Service.Property.WarningStateAuditory',
    'CurrentFormation/0/BP_Sifa_Service.Property.inPenaltyBrakeApplication',
    'CurrentFormation/0/BP_Sifa_Service.Property.bActiveState',
    'CurrentFormation/0/BP_Sifa_Service.Property.bEnabledState',
    'CurrentFormation/0/BP_Sifa_Service.Property.bPedalIsPressed',
    'CurrentFormation/0/BP_Sifa_Service.Property.MinimumSpeedMet',
    'CurrentFormation/0/BP_Sifa_Service.Function.WarningDevices_GetPenaltyBrakeState',
    'CurrentFormation/0/BP_Sifa_Service.Function.WarningDevices_GetIsWarningActive',
    'CurrentFormation/0.Function.GetSifaEmergencyState',
]

pzb85_eps = [
    'CurrentFormation/0/MFA_Indicators.Property.85_IsActive_PZB',
    'CurrentFormation/0/MFA_Indicators.Property.85_IsActive_TrainData',
    'CurrentFormation/0/MFA_Indicators.Property.85_IsFlashing_PZB',
    'CurrentFormation/0/MFA_Indicators.Property.85_IsFlashing_LZB',
    'CurrentFormation/0/MFA_Indicators.Property.85_IsFlashing_Grunddaten',
    'CurrentFormation/0/MFA_Indicators.Property.Grunddaten',
    'CurrentFormation/0/MFA_Indicators.Property.PZB_GrunddatenMode',
    'CurrentFormation/0/MFA_Indicators.Property.IsBelowGrunddatenSpeed',
    'CurrentFormation/0/MFA_Indicators.Property.DisplayingTrainData',
]

pzb70_eps = [
    'CurrentFormation/0/MFA_Indicators.Property.70_IsActive_PZB',
    'CurrentFormation/0/MFA_Indicators.Property.70_IsActive_TrainData',
    'CurrentFormation/0/MFA_Indicators.Property.70_IsFlashing_PZB',
    'CurrentFormation/0/MFA_Indicators.Property.70_IsFlashing_Inverted',
    'CurrentFormation/0/MFA_Indicators.Property.70_IsFlashing_Grunddaten',
]

pzb55_eps = [
    'CurrentFormation/0/MFA_Indicators.Property.55_IsActive_PZB',
    'CurrentFormation/0/MFA_Indicators.Property.55_IsActive_TrainData',
    'CurrentFormation/0/MFA_Indicators.Property.55_IsFlashing_PZB',
    'CurrentFormation/0/MFA_Indicators.Property.55_IsFlashing_Grunddaten',
]

def read_ep(ep):
    try:
        r = s.get(f'{base}/get/{ep}', timeout=2)
        data = r.json()
        vals = data.get('Values', {})
        v = list(vals.values())[0] if vals else data
        return v
    except Exception as e:
        return f'ERR: {e}'

print('=== SIFA ===')
for ep in sifa_eps:
    name = ep.rsplit('.', 1)[-1]
    print(f'  {name} = {read_ep(ep)}')

print('\n=== PZB 85 ===')
for ep in pzb85_eps:
    name = ep.rsplit('.', 1)[-1]
    print(f'  {name} = {read_ep(ep)}')

print('\n=== PZB 70 ===')
for ep in pzb70_eps:
    name = ep.rsplit('.', 1)[-1]
    print(f'  {name} = {read_ep(ep)}')

print('\n=== PZB 55 ===')
for ep in pzb55_eps:
    name = ep.rsplit('.', 1)[-1]
    print(f'  {name} = {read_ep(ep)}')
