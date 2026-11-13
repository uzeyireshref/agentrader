"""Regenerate P3 shared transport parity fixtures in an isolated pure calculation."""
import copy
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
from test_chart_evidence import fixture,capture

rows,market,quality=fixture()
cases=[]
for name in ('complete','gap','precision_unproven','short_history'):
    r,m,q=copy.deepcopy((rows,market,quality))
    if name=='gap':r.pop(20)
    if name=='precision_unproven':r[-1].pop('exact')
    if name=='short_history':r=r[-2:];q['short_history']=True
    cases.append({'name':name,'rows':r,'market':m,'quality':q,'proof':capture(r,m,q).view()})
path=Path(__file__).resolve().parents[1]/'frontend/tests/fixtures/data-evidence.json'
path.write_text(json.dumps({'schema':'chart-evidence-reference/1','cases':cases},indent=2))
print(json.dumps({'cases':len(cases),'file':str(path)}))
