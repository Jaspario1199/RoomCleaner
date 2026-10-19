"""Check source anchors for quick resolutions; this does not qualify hardware."""
from pathlib import Path
import json, math, re
from design_resolution import validate
ROOT=Path(__file__).resolve().parents[1]
d=json.loads((ROOT/'docs/design_resolution/quick_resolutions.json').read_text())
ids=set()
selectors={
 'Q01': [('EXTENSION',1)], 'Q02':[('MODULE',1)], 'Q03':[('BACKLASH',1)],
 'Q04':[('OPEN_ANGLE',1),('CLOSED_ANGLE',1)],
 'Q06':[('TILT',1)], 'Q07':[('trackingTolerance',1)],
 'Q08':[('trackingDwellUs',1e-6)], 'Q09':[('arrivalTolerance',1)],
 'Q10':[('arrivalDwellUs',1e-6)], 'Q11':[('heartbeatTimeoutUs',1e-6)],
}
for item in d['items']:
    if item['id'] in ids: raise ValueError('Duplicate quick resolution')
    ids.add(item['id'])
    source=(ROOT/item['source']).read_text()
    if item['source_anchor'] not in source: raise ValueError(item['id']+' source changed; review required')
    if item['id'] in selectors:
        actual=[]
        for name,scale in selectors[item['id']]:
            match=re.search(r'\b'+name+r'\s*=\s*((?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+))',source)
            if match is None: raise ValueError('Missing numeric definition '+name)
            actual.append(float(match[1])*scale)
        expected=item['value'] if isinstance(item['value'],list) else [item['value']]
        if len(actual)!=len(expected) or any(not math.isclose(a,b,abs_tol=1e-12)for a,b in zip(actual,expected)):
            raise ValueError(item['id']+' recorded value differs from source')
    elif item['id']=='Q05':
        match=re.search(r'shape=box\((\d+),(\d+),(\d+),\(-JAW_X',source)
        if match is None or list(map(int,match.groups()))!=item['value']: raise ValueError('Pad dimensions changed')
    elif item['id']=='Q12':
        match=re.search(r'millis\(\)-stationarySince>=(\d+)',source)
        if match is None or not math.isclose(int(match[1])/1000,item['value']): raise ValueError('Quiet interval changed')
    if item['status']!='source_verified' or not item['qualification']: raise ValueError('Missing scope')
ledger=json.loads((ROOT/'docs/design_resolution/unknown_parameters.json').read_text())
validate(ledger)
if any(g['status']=='closed' for g in ledger['groups']): raise ValueError('Review scope changed: closed parent group')
if any(p['measured_value'] is not None for g in ledger['groups'] for p in g['parameters']): raise ValueError('Review physical evidence before accepting measurements')
clamp=(ROOT/'cad/clamp_v1.py').read_text()
def constant(name): return float(re.search(r'\b'+name+r'\s*=\s*((?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+))',clamp)[1])
travel=(constant('MODULE')*constant('N')/2)*math.radians(constant('CLOSED_ANGLE')-constant('OPEN_ANGLE'))
print(f'{len(ids)} source entries checked; nominal rack travel {travel:.6f} mm; relative closure {2*travel:.6f} mm.')
print('16 quick subtasks documented; parent groups remain open. No physical measurements invented.')
