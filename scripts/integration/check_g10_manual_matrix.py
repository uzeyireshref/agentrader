"""Every current variant: manual raw/note read and independent server write protection."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import json,sys,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from agentrader.integration.chart_bot import ChartBot,BotError
from scripts.integration.chart_bot_fixture import ChartBotFixture,ROOT
from scripts.integration.chart_tool_matrix_cases import drawing_cases

OUT=ROOT/'reports/chart-interface-g10-20261115'

def main():
    report=dict(passed=False,scope='ISOLATED_SYNTHETIC_REAL_HTTP_NOT_LIVE_DEMO',cases=[])
    try:
        with ChartBotFixture() as f:
            bot=ChartBot(f.base,f.bot_token,bot_id='alpha',strategy_id='synthetic',journal=f.folder/'manual.db')
            bot.identify()
            for case in drawing_cases(include_projection=True):
                cid=case['case_id'];g=case['geometry']
                response=f.human.post('/api/workspaces/main/drawings?format_version=10',json=dict(request_id=cid+'-manual',geometry=g))
                assert response.status_code==201,response.text
                did=response.json()['drawing_id'];note='Manual 🧭 '+cid+'\n日本語'
                response=f.human.put('/api/drawings/'+did+'/notes',json=dict(request_id=cid+'-note',expected_revision=0,expected_drawing_revision=1,text=note))
                assert response.status_code==200,response.text
                before=bot.get(did);assert before['linked_note']['text']==note
                operations=[dict(drawing_id=did,expected_revision=1,geometry=g,management=before['management'],deleted=True)]
                local=[lambda:bot.update(cid+'-update',did,1,g),lambda:bot.delete(cid+'-delete',did,1),lambda:bot.save_note(cid+'-edit-note',did,1,1,'changed'),lambda:bot.delete_note(cid+'-del-note',did,1,1),lambda:bot.operations(cid+'-bulk',operations)]
                for call in local:
                    try:call();raise AssertionError('manual write accepted')
                    except BotError as error:assert error.code=='BOT_OBJECT_PROTECTED',(cid,error.code)
                path='/api/drawings/'+did
                requests=[('PATCH',path+'?format_version=10',dict(expected_revision=1,geometry=g)),('DELETE',path+'?format_version=10',dict(expected_revision=1)),('PUT',path+'/notes',dict(expected_revision=1,expected_drawing_revision=1,text='changed')),('DELETE',path+'/notes',dict(expected_revision=1,expected_drawing_revision=1)),('POST','/api/workspaces/main/drawing-operations?format_version=10',dict(operations=operations))]
                for index,(method,path,body) in enumerate(requests):
                    status,value=bot.http.request(method,path,dict(request_id=cid+'-raw-'+str(index),**body))
                    assert status==403 and value.get('error',{}).get('code')=='DRAWING_ORIGIN_PROTECTED',(cid,status,value)
                package=bot.export_package('BTCUSDT','15m',[dict(drawing_id=did,expected_revision=1,expected_note_revision=1)])
                copied=bot.paste_package(cid+'-paste','BTCUSDT','15m',package)['drawings'][0]
                assert copied['drawing_id']!=did and copied['origin']['kind']=='bot' and copied['geometry']==before['geometry'] and copied['linked_note']['text']==note
                bot.delete(cid+'-cleanup',copied['drawing_id'],1)
                assert bot.get(did)==before
                report['cases'].append(dict(case_id=cid,raw_read='PASS',text_note_read='PASS',adapter_protection_checks=5,server_http_403_checks=5,copy_new_bot_identity='PASS',manual_unchanged='PASS',cleanup='OWN_COPY_ONLY'))
            assert len(report['cases'])==26 and bot.find_own('BTCUSDT','15m')==[]
            assert not (f.folder/'execution.db').exists() and not (f.folder/'market.db').exists()
            report['passed']=True
    except Exception:report['error']=traceback.format_exc()
    OUT.mkdir(parents=True,exist_ok=True);(OUT/'manual-matrix.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=report['passed'],cases=len(report['cases']),error=report.get('error'))));return 0 if report['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
