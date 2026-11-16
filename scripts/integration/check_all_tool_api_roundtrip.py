"""P1: real production routes, isolated SQLite, no exchange/account access."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

from contextlib import closing
from copy import deepcopy
from decimal import Decimal
from fractions import Fraction
import argparse,hashlib,json,sys,tempfile,traceback
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from fastapi.testclient import TestClient
from agentrader.api.app import create_app
from agentrader.application.settings import WebSettings
from agentrader.chart.chart_profiles import KINDS
from agentrader.chart.drawings.service import management,DrawingService,DrawingNotFound
from agentrader.chart.drawings.calculations import query,measure_ruler,CalculationBlocked
from agentrader.chart.drawings.position import metrics
from scripts.integration.chart_tool_matrix_cases import drawing_cases,candles,START,STEP

OUT=Path('reports/all-chart-tools-20261114')


def computation(g):
    kind=g['kind'];kw=dict(time=g['anchors'][0]['time'],times=[START+i*STEP for i in range(300)],interval='15m')
    if g.get('schema')=='chart-channel-family/1':
        return dict(state='PASS',result=query(g,'geometry',rows=candles(),**kw),access='PYTHON_LIBRARY_CHECK_HTTP_TESTED_SEPARATELY')
    if kind in ('text','note','price_label'):
        expected='DISPLAY_ONLY_ANNOTATION'
        try:query(g,'priceAt',**kw)
        except CalculationBlocked as exc:
            assert exc.code==expected;return dict(state='EXPECTED_BLOCK',reason=exc.code,raw_geometry_readable=True)
        raise AssertionError('Display-only acquired numeric authority')
    if kind=='ruler':
        v=measure_ruler(g,tick_size='.25',times=kw['times'],interval='15m')
        assert v['elapsed_seconds']==14*STEP
        return dict(state='PASS',result=v,access='PYTHON_LIBRARY_CHECK_HTTP_TESTED_SEPARATELY')
    if kind in ('long_plan','short_plan'):
        v=metrics(g);assert v['gross_risk']>0 and v['gross_reward']>0
        return dict(state='PASS',result={k:str(x) for k,x in v.items()},access='PYTHON_LIBRARY_CHECK_HTTP_TESTED_SEPARATELY')
    if kind=='fibonacci_projection':kw['time']=g['anchors'][2]['time']
    op='contains' if kind=='zone' else 'level' if kind in ('fibonacci','fibonacci_extension','fibonacci_projection') else 'boundsAt' if kind=='parallel_channel' else 'priceAt'
    v=query(g,op,query_price='120.25',ratio='0.618' if op=='level' else None,**kw)
    def frac(x):return Fraction(int(x['numerator']),int(x['denominator']))
    if op=='priceAt':assert frac(v['value'])==Fraction(g['anchors'][0]['price'])
    if op=='contains':assert v['value'] is True
    if op=='level':assert frac(v['value'])==Fraction(g['anchors'][2]['price'] if kind=='fibonacci_projection' else g['anchors'][0]['price'])+(Fraction(g['anchors'][1]['price'])-Fraction(g['anchors'][0]['price']))*Fraction('0.618')
    if op=='boundsAt':
        b={k:frac(x) for k,x in v['value'].items()};assert b['lower']<b['upper'] and b['middle']==(b['lower']+b['upper'])/2 and b['width']==b['upper']-b['lower']
    return dict(state='PASS',result=v,access='PYTHON_LIBRARY_CHECK_HTTP_TESTED_SEPARATELY')


def main():
    global OUT
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',type=Path,default=OUT);args=parser.parse_args();OUT=args.output_dir.resolve()
    OUT.mkdir(parents=True,exist_ok=True);report=dict(package='P1',passed=False,cases=[],account_requests=0,order_requests=0,scope='Isolated API/SQLite; browser not tested in P1')
    cases=drawing_cases(include_projection=True);assert len(cases)==26 and {c['geometry']['kind'] for c in cases}==set(KINDS)
    with tempfile.TemporaryDirectory(prefix='all-tool-api-') as tmp:
        folder=Path(tmp);execution=folder/'execution.db';execution.write_bytes(b'NO_EXECUTION_ACCESS');baseline=hashlib.sha256(execution.read_bytes()).hexdigest()
        settings=WebSettings(application_database=folder/'app.db',execution_database=execution,market_database=folder/'market.db',owner='tool-matrix')
        try:
            with TestClient(create_app(settings),base_url='http://127.0.0.1') as client:
                for case in cases:
                    row=dict(case_id=case['case_id'],kind=case['geometry']['kind'],schema=case['geometry'].get('schema','LEGACY'),state='RUNNING');report['cases'].append(row)
                    g=case['geometry'];prefix=case['case_id']
                    response=client.post('/api/workspaces/main/drawings?format_version=10',json=dict(request_id=prefix+'-create',geometry=g))
                    assert response.status_code==201,(prefix,response.text)
                    d=response.json();did=d['drawing_id'];url='/api/drawings/'+did+'?format_version=10';row['drawing_id']=did
                    read=client.get(url).json();assert read=={k:v for k,v in d.items() if k!='duplicate'}
                    assert len(read['geometry']['anchors'])==len(g['anchors'])
                    for a,b in zip(g['anchors'],read['geometry']['anchors']):assert a['time']==b['time'] and Decimal(a['price'])==Decimal(b['price'])
                    for key in ('label','text','options','params'):
                        if key in g:assert read['geometry'][key]==g[key],(prefix,key)
                    for key in ('kind','schema','symbol','price_source','time_scope'):
                        if key in g:assert read['geometry'][key]==g[key]
                    if 'levels' in g:assert list(map(Fraction,g['levels']))==list(map(Fraction,read['geometry']['levels']))
                    if 'text' not in g:
                        unsupported_note={**g,'text':'Bu araçta ayrı not alanı var mı?'}
                        assert client.post('/api/workspaces/main/drawings?format_version=10',json=dict(request_id=prefix+'-extra-note',geometry=unsupported_note)).status_code==422
                        row['note_access']='LABEL_ONLY_USE_SEPARATE_NOTE_OBJECT'
                    else:row['note_access']='FULL_TEXT_FIELD'
                    contract=client.get('/api/drawings/'+did+'/contract').json()
                    assert contract['anchors']==read['geometry']['anchors'] and contract['label']==g['label']
                    if 'text' in g:assert contract['params']['text']==g['text']
                    row['create_read_contract']='PASS';row['computation']=computation(read['geometry'])
                    note='Linked note 🧭\n'+case['case_id']
                    saved_note=client.put('/api/drawings/'+did+'/notes',json=dict(request_id=prefix+'-linked-note',expected_revision=0,expected_drawing_revision=1,text=note))
                    assert saved_note.status_code==200,saved_note.text
                    read=client.get(url).json();assert read['linked_note']['text']==note
                    row['note_access']='GEOMETRY_TEXT_AND_LINKED_NOTE_HTTP' if 'text' in g else 'LABEL_AND_LINKED_NOTE_HTTP'
                    fresh=DrawingService(settings.application_database,settings.owner).show(did);assert fresh==read
                    try:DrawingService(settings.application_database,'other-owner').show(did);raise AssertionError('Owner leak')
                    except DrawingNotFound:pass
                    other=client.get('/api/workspaces/other/drawings?symbol=BTCUSDT&format_version=10').json();assert not other['drawings']
                    row['persistence_owner_workspace']='PASS'
                    invalid=deepcopy(read['geometry']);invalid['anchors'][0]['time']*=1000
                    assert client.post('/api/workspaces/main/drawings?format_version=10',json=dict(request_id=prefix+'-bad-time',geometry=invalid)).status_code==422
                    invalid=deepcopy(read['geometry']);invalid['anchors'][0]['price']='NaN'
                    assert client.post('/api/workspaces/main/drawings?format_version=10',json=dict(request_id=prefix+'-bad-price',geometry=invalid)).status_code==422
                    edited=deepcopy(read['geometry']);edited['label']='Güncel ✓ '+prefix
                    for anchor in edited['anchors']:
                        anchor['time']+=225;anchor['price']=str(Decimal(anchor['price'])+Decimal('0.12345678'))
                    response=client.patch(url,json=dict(request_id=prefix+'-edit',expected_revision=1,geometry=edited))
                    assert response.status_code==200,response.text;d=response.json();assert d['revision']==2 and d['geometry']['label']==edited['label']
                    assert d['geometry']['anchors']==edited['anchors'];row.update(coordinate_edit_exact='PASS',invalid_coordinates_rejected='PASS')
                    stale=client.patch(url,json=dict(request_id=prefix+'-stale',expected_revision=1,geometry=edited));assert stale.status_code==409
                    def manage(d,m,suffix):
                        response=client.post('/api/workspaces/main/drawing-operations?format_version=10',json=dict(request_id=prefix+suffix,operations=[dict(drawing_id=did,expected_revision=d['revision'],geometry=d['geometry'],management=m,deleted=False)]))
                        assert response.status_code==200,response.text;return response.json()['drawings'][0]
                    m={**management(), 'locked':True,'hidden':True,'color':'#9b6ed6','line_width':2,'line_style':'dashed','intervals':['15m','1h']}
                    d=manage(d,m,'-lock');assert client.get(url).json()['management']==m
                    locked=client.patch(url,json=dict(request_id=prefix+'-locked-edit',expected_revision=d['revision'],geometry={**edited,'label':'Not allowed'}));assert locked.status_code==423
                    d=manage(d,{**m,'locked':False,'hidden':False},'-unlock');row['edit_stale_lock_visibility_style']='PASS'
                    response=client.request('DELETE',url,json=dict(request_id=prefix+'-delete',expected_revision=d['revision']));assert response.status_code==200
                    assert client.get(url).json()['deleted'] is True
                    listing=client.get('/api/workspaces/main/drawings?symbol=BTCUSDT&format_version=10').json()['drawings'];assert all(x['drawing_id']!=did for x in listing)
                    row.update(state='PASS',delete='PASS')
                    (OUT/'p1-api.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
                declared=client.get('/api/chart-tools/drawing/fibonacci_projection').json()
                assert declared['readable'] is True and declared['computable'] is True and declared['format_version']==10
                unsupported={**cases[0]['geometry'],'kind':'fibonacci_projection'}
                assert client.post('/api/workspaces/main/drawings?format_version=10',json=dict(request_id='declared-only-tool',geometry=unsupported)).status_code==422
                report['projection_legacy_shape_without_schema']='EXPECTED_BLOCK_422'
                report['execution_unchanged']=hashlib.sha256(execution.read_bytes()).hexdigest()==baseline;assert report['execution_unchanged']
                report['passed']=all(c['state']=='PASS' for c in report['cases']) and len(report['cases'])==26
        except Exception:report['error']=traceback.format_exc()
    (OUT/'p1-api.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(dict(package='P1',passed=report['passed'],cases=len(report['cases']),error=report.get('error')),ensure_ascii=True))
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
