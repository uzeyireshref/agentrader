"""P3 configuration API roundtrip, separate from browser numerical acceptance."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

from copy import deepcopy
from pathlib import Path
import argparse,hashlib,json,sys,tempfile,traceback
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from fastapi.testclient import TestClient
from agentrader.api.app import create_app
from agentrader.application.settings import WebSettings
from agentrader.chart.indicator_config import defaults_v4,IndicatorService

OUT=Path('reports/all-chart-tools-20261114')


def main():
    global OUT
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',type=Path,default=OUT);args=parser.parse_args();OUT=args.output_dir.resolve();OUT.mkdir(parents=True,exist_ok=True)
    r=dict(package='P3-API',passed=False,indicators=[],account_requests=0,order_requests=0)
    with tempfile.TemporaryDirectory(prefix='indicator-bot-') as tmp:
        folder=Path(tmp);execution=folder/'execution.db';execution.write_bytes(b'NO_EXECUTION_ACCESS');baseline=hashlib.sha256(execution.read_bytes()).hexdigest()
        s=WebSettings(application_database=folder/'app.db',execution_database=execution,market_database=folder/'market.db',owner='indicator-matrix')
        app=create_app(s)
        try:
            with TestClient(app,base_url='http://127.0.0.1') as c:
                url='/api/workspaces/main/indicators?format_version=4'
                original=c.get(url).json();assert len(original['indicators'])==9
                items=deepcopy(original['indicators'])
                for index,item in enumerate(items):
                    item['enabled']=True
                    if item['kind'] in ('EMA','SMA','RSI','ATR'):item['period']=5+index
                    if item['kind']=='ANCHORED_VWAP':item['params'].update(anchor_time=1800000000,anchor_symbol='BTCUSDT')
                response=c.put(url,json=dict(request_id='configure-all-nine',expected_revision=0,indicators=items));assert response.status_code==200,response.text
                written=response.json();read=c.get(url).json();assert read=={k:v for k,v in written.items() if k!='duplicate'}
                for sent,stored in zip(items,read['indicators']):
                    assert stored['revision']>=1
                    assert {k:v for k,v in sent.items() if k!='revision'}=={k:v for k,v in stored.items() if k!='revision'}
                    r['indicators'].append(dict(id=stored['indicator_id'],kind=stored['kind'],configuration_write_read='PASS',configuration=stored,
                        numeric_http_endpoint='AVAILABLE_SEPARATE_G5_NUMERIC_ACCEPTANCE',numeric_library='AVAILABLE_WITH_CONTEXT',arbitrary_note='SEPARATE_ANNOTATION_OBJECT'))
                fresh=IndicatorService(s.application_database,s.owner).load('main',4);assert fresh==read
                other=IndicatorService(s.application_database,'other-owner').load('main',4);assert other['revision']==0
                other_workspace=c.get('/api/workspaces/other/indicators?format_version=4').json();assert other_workspace['revision']==0
                stale=c.put(url,json=dict(request_id='stale',expected_revision=0,indicators=items));assert stale.status_code==409
                invalid=deepcopy(read['indicators']);invalid[0]['period']=0
                rejected=c.put(url,json=dict(request_id='invalid-period',expected_revision=read['revision'],indicators=invalid));assert rejected.status_code==422
                assert c.get(url).json()==read
                r.update(persistence='PASS',owner_workspace_isolation='PASS',stale_revision='PASS',invalid_config_unchanged='PASS',
                    computed_values_http='AVAILABLE_SEPARATE_G5_NUMERIC_ACCEPTANCE',browser_numeric_reference='NOT_RUN_IN_THIS_PACKAGE',
                    transient_viewport_cursor_hover='NOT_EXPOSED_TO_BOT',execution_unchanged=hashlib.sha256(execution.read_bytes()).hexdigest()==baseline)
                assert r['execution_unchanged'];r['passed']=True
        except Exception:r['error']=traceback.format_exc()
    (OUT/'p3-indicator-api.json').write_text(json.dumps(r,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(dict(package=r['package'],passed=r['passed'],indicators=len(r['indicators']),error=r.get('error')),ensure_ascii=True))
    return 0 if r['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
