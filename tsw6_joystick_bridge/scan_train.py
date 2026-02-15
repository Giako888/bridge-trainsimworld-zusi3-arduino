import requests
s = requests.Session()
s.headers.update({'DTGCommKey': 'KCfgFZ38yd8hRnlol2it4/qnEy92T0cPrMQnpNGcCtA='})
base = 'http://localhost:31270'
MFA = 'CurrentFormation/0/MFA_Indicators.Property.'

def get(path):
    try:
        r = s.get(base+'/get/'+path, timeout=2)
        d = r.json()
        if d.get('Result')=='Success' and d.get('Values'):
            return list(d['Values'].values())[0]
        return 'N/A'
    except:
        return 'ERR'

sep = '='*60

# TRAIN ID
print(sep)
print('  TRAIN IDENTIFICATION')
print(sep)
print('  ObjectName  = %s' % get('CurrentFormation/0.ObjectName'))
print('  ObjectClass = %s' % get('CurrentFormation/0.ObjectClass'))

# SIFA
print('\n' + sep)
print('  SIFA')
print(sep)
for p,l in [
    ('BP_Sifa_Service.Property.WarningStateVisual','WarningVisual'),
    ('BP_Sifa_Service.Property.bActiveState','Active'),
    ('BP_Sifa_Service.Property.bIsCutIn','CutIn'),
    ('BP_Sifa_Service.Property.bEnabledState','Enabled'),
    ('BP_Sifa_Service.Property.inPenaltyBrakeApplication','Penalty'),
]:
    print('  %-20s = %s' % (l, get('CurrentFormation/0/'+p)))

# PZB
print('\n' + sep)
print('  PZB SYSTEM')
print(sep)
for p,l in [
    ('PZB_V3.Property.bIsPZB_Active','Active'),
    ('PZB_V3.Property.bIsReady','Ready'),
    ('PZB_V3.Property._isEnabled','Enabled'),
    ('PZB_V3.Property._InEmergency','Emergency'),
    ('PZB_V3.Property.ActiveMode','ActiveMode'),
    ('PZB_V3.Property.ProgramMode','ProgramMode'),
]:
    print('  %-20s = %s' % (l, get('CurrentFormation/0/'+p)))

# LZB
print('\n' + sep)
print('  LZB SYSTEM')
print(sep)
for p,l in [
    ('LZB.Property.bIsEnabled','Enabled'),
    ('LZB.Property.bIsReady','Ready'),
    ('LZB.Property.bIsActivated','Activated'),
    ('LZB.Property.bIsIsolated','Isolated'),
    ('LZB.Property.faultCode','FaultCode'),
]:
    print('  %-20s = %s' % (l, get('CurrentFormation/0/'+p)))

# MFA KEY INDICATORS
print('\n' + sep)
print('  MFA KEY INDICATORS')
print(sep)
key_eps = [
    '85_IsActive_PZB','85_IsActive_TrainData','85_IsFlashing_PZB','85_IsFlashing_LZB','85_IsFlashing_Grunddaten',
    '70_IsActive_PZB','70_IsActive_TrainData','70_IsFlashing_PZB','70_IsFlashing_Inverted','70_IsFlashing_Grunddaten',
    '55_IsActive_PZB','55_IsActive_TrainData','55_IsFlashing_PZB','55_IsFlashing_Grunddaten',
    '1000Hz_IsActive_PZB','1000Hz_IsFlashing_PZB',
    '500Hz_IsActive',
    'B_IsActive','B_IsFlashing',
    'S_IsActive_PZB',
    'G_IsActive_PZB','G_IsActive_LZB',
    'Grunddaten','IsBelowGrunddatenSpeed','PZB_GrunddatenMode',
    'ElectricalPower','LZB_IsUnisolated',
    'DisplayingTrainData','Ersatzzugdaten',
]
active = []
for ep in key_eps:
    val = get(MFA + ep)
    marker = ' <<<' if val == True else ''
    print('  %-40s = %s%s' % (ep, val, marker))
    if val == True:
        active.append(ep)

print('\n' + sep)
print('  ACTIVE (True): %d' % len(active))
for a in active:
    print('    -> %s' % a)
print(sep)
