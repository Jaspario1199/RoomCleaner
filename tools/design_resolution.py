"""Check engineering ledger structure/closure records; human review establishes evidence quality."""
from pathlib import Path
from datetime import date
import math,json,argparse
ROOT=Path(__file__).resolve().parents[1]
LEDGER=ROOT/'docs/design_resolution/unknown_parameters.json'
TEXT_UNITS={'text','enum','state_machine','pose_set','volume','pose'}

def require(condition,message):
    if not condition:raise ValueError(message)

def nonblank(value):return isinstance(value,str) and bool(value.strip())

def valid_date(value):
    try:return nonblank(value) and date.fromisoformat(value).isoformat()==value
    except (ValueError,TypeError):return False

def numeric(value,nonnegative=False):
    if isinstance(value,bool):return False
    if isinstance(value,(int,float)):return math.isfinite(value) and (not nonnegative or value>=0)
    if isinstance(value,list):return bool(value) and all(numeric(v,nonnegative)for v in value)
    if isinstance(value,dict):return bool(value) and all(nonblank(k)and numeric(v,nonnegative)for k,v in value.items())
    return False

def evidence_valid(value):
    if isinstance(value,list):return bool(value)and all(evidence_valid(v)for v in value)
    if not nonblank(value):return False
    if value.startswith(('https://','http://')):return len(value.split('//',1)[1])>3
    return (ROOT/value).is_file()

def has_shape(value,shape):
    if not shape:return isinstance(value,(int,float)) and not isinstance(value,bool)
    return isinstance(value,list)and len(value)==shape[0]and all(has_shape(v,shape[1:])for v in value)

def value_valid(p,value):
    if isinstance(p['shape'],list):return numeric(value)and has_shape(value,p['shape'])
    if p['units'] in TEXT_UNITS:
        return nonblank(value)or(isinstance(value,(dict,list))and bool(value))
    if p['units']=='integer':return type(value)is int
    return numeric(value)

def validate(d):
    groups=d['groups'];ids=[g['id']for g in groups];by_id={g['id']:g for g in groups}
    require(len(ids)==len(set(ids)),'Duplicate group ID');keys=[]
    for g in groups:
        require(g['status']in('unresolved','closed'),g['id']+' status')
        require(g['solution_status']in('proposed','selected_for_development','implemented_pending_test','validated'),g['id']+' solution status')
        require(nonblank(g['recommendation'])and nonblank(g['acceptance_evidence'])and(ROOT/g['source']).is_file(),g['id']+' provenance')
        require(set(g['blocking_groups'])<=set(ids)and g['id']not in g['blocking_groups'],g['id']+' dependencies')
        for p in g['parameters']:
            key=g['id']+'.'+p['symbol'];keys.append(key)
            require(nonblank(p['units'])and nonblank(p['value_definition']),key+' unit/definition label')
            for field in ('resolved_value','measured_value'):
                if p[field]is not None:require(value_valid(p,p[field]),key+' invalid '+field)
            if p.get('reference_value') is not None:
                r=p['reference_value'];require(value_valid(p,r['value'])and nonblank(r['basis'])and evidence_valid(r['source']),key+' reference provenance')
            if p['resolved_value']is not None:
                require(p['resolution_basis']in('user_requirement','supplier_nominal','derived','measured','design_selection')and evidence_valid(p['evidence']),key+' resolution evidence')
            if p['measured_value']is not None:
                u=p['measurement_uncertainty']
                require(numeric(u,True)or(p['units']in TEXT_UNITS and u=='not_applicable'),key+' invalid uncertainty')
                require(valid_date(p['measurement_date'])and nonblank(p['hardware_revision'])and evidence_valid(p['evidence']),key+' measurement metadata')
        if g['status']=='closed':
            record=g.get('closure_record')
            require(isinstance(record,dict),g['id']+' closure must be structured')
            require(g['solution_status']=='validated'and nonblank(record.get('reviewer'))and valid_date(record.get('date'))and evidence_valid(record.get('evidence')),g['id']+' closure review/evidence')
            require(nonblank(record.get('dependency_review')),g['id']+' missing dependency review')
            for p in g['parameters']:
                require(p['resolved_value']is not None or p['measured_value']is not None or(p.get('applicable')is False and nonblank(p.get('not_applicable_reason'))),g['id']+'.'+p['symbol']+' unresolved at closure')
            require(all(by_id[k]['status']=='closed'for k in g['blocking_groups']),g['id']+' blocking groups remain open')
    require(len(keys)==len(set(keys)),'Duplicate parameter key')
    fields={g['id']+'.'+p['symbol']:p for g in groups for p in g['parameters']}
    for key,p in fields.items():
        alias=p.get('canonical_alias')
        if alias:
            require(alias in fields and fields[alias]['units']==p['units'],key+' invalid canonical alias')
            for attribute in ('resolved_value','measured_value'):
                if p[attribute]is not None and fields[alias][attribute]is not None:
                    require(p[attribute]==fields[alias][attribute],key+' conflicting duplicate fact')
    packages=d['work_packages'];seen={}
    for w in packages:
        require(w['id']not in seen,w['id']+' duplicate');seen[w['id']]=w
        require(set(w['parameter_groups'])<=set(ids),w['id']+' references unknown group')
    visiting=set();done=set()
    def visit(key):
        require(key in seen,'Unknown package '+key);require(key not in visiting,'Cyclic package '+key)
        if key in done:return
        visiting.add(key)
        for dep in seen[key]['depends_on']:visit(dep)
        visiting.remove(key);done.add(key)
    for key in seen:visit(key)
    covered={k for w in packages for k in w['parameter_groups']}
    require(covered==set(ids),'Unscheduled groups: '+str(set(ids)-covered))
    # Full evidence-group closure can be coupled; only explicitly declared
    # blocking groups are enforced. Contributions and final closure are distinct.
    return len(groups),len(keys)

def render(d):
    lines=['# Parameter closure register — 4 October 2026','',
    'Generated from `unknown_parameters.json`. Selected solutions do not close hardware tests. Null values remain unset. Work packages are staged contributions to shared records; completing a package does not automatically close every referenced group. Specialist audits contain alternatives, provenance and tests.','']
    references=[(g['id'],p) for g in d['groups'] for p in g['parameters'] if p.get('reference_value') is not None]
    lines+=['## Filled reference values','',f'{len(references)} fields have cited reference values. These are distinct from measured or resolved values.','',
            '| Field | Reference | Basis | Qualification |','|---|---|---|---|']
    for gid,p in references:
        ref=p['reference_value']
        lines.append('| '+gid+'.'+p['symbol']+' | '+json.dumps(ref['value'])+' '+p['units']+' | '+ref['basis']+' | '+ref['qualification']+' |')
    if d.get('progress_record'):
        lines+=['','Execution priorities and remaining user inputs: ['+d['progress_record']+'](../../'+d['progress_record']+').','']
    for w in d['work_packages']:
        lines+=['## '+w['id']+' — '+w['title'],'','Milestone dependencies: '+(', '.join(w['depends_on'])or'none')+'.', '',w['definition_of_done'],'']
    lines+=['## Parameter groups','','| ID | Named fields and unit labels | Solution state | Next action |','|---|---|---|---|']
    for g in d['groups']:
        fields='; '.join(p['symbol']+' ['+p['units']+']'for p in g['parameters'])
        lines.append('| '+g['id']+' | '+fields+' | '+g['solution_status'].replace('_',' ')+' | '+(g['next_step']or'Follow the cited audit closure method.')+' |')
    (LEDGER.parent/'parameter_register.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--render',action='store_true');args=parser.parse_args()
    d=json.loads(LEDGER.read_text());counts=validate(d)
    if args.render:render(d)
    print(f'{counts[0]} groups / {counts[1]} fields; IDs, unit labels, source paths, staged package coverage and closure-record guards checked. Evidence quality requires engineering review.')
