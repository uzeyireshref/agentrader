"""C4: real App + isolated FastAPI/SQLite drawing API through intercepted HTTP."""
import copy
import json
from pathlib import Path
import tempfile
import time
from urllib.parse import urlparse
import uuid
from fastapi.testclient import TestClient
from measure_chart_interactions import main, ROOT
import sys
sys.path.insert(0,str(ROOT))
from agentrader.api.app import create_app
from agentrader.application.settings import WebSettings


def checks(page,sockets,rows,result):
    result['task']='C4';result['checks']=[]
    def pause():page.wait_for_timeout(160)
    def record(name,**data):result['checks'].append(dict(name=name,passed=True,**data))
    with tempfile.TemporaryDirectory(prefix='agentrader-c4-') as folder:
        settings=WebSettings(Path(folder)/'app.db',Path(folder)/'execution.db',market_database=Path(folder)/'market.db')
        def client():
            c=TestClient(create_app(settings),base_url='http://127.0.0.1');c.__enter__();return c
        api=[client()];attempts=[];lose=[False];delay=[False];result['api_attempts']=attempts
        try:
            def route(r):
                req=r.request;u=urlparse(req.url)
                headers={'host':u.netloc}
                if 'origin' in req.headers:headers['origin']=req.headers['origin']
                if 'content-type' in req.headers:headers['content-type']=req.headers['content-type']
                if delay[0] and req.method=='PATCH':
                    delay[0]=False;time.sleep(.35)
                response=api[0].request(req.method,u.path+('?' +u.query if u.query else ''),content=req.post_data,headers=headers)
                if req.method in ['POST','PATCH','DELETE']:
                    attempts.append({'method':req.method,'path':u.path,'body':req.post_data_json,'status':response.status_code})
                if lose[0] and req.method=='PATCH':
                    lose[0]=False;assert response.status_code==200;r.abort('failed');return
                r.fulfill(status=response.status_code,json=response.json())
            page.route('**/api/workspaces/main*',route);page.route('**/api/workspaces/main/drawings*',route);page.route('**/api/drawings/*',route)
            page.get_by_role('button',name='Sunucudan yenile',exact=True).click();pause()
            def listing():
                response=api[0].get('/api/workspaces/main/drawings?symbol=BTCUSDT');assert response.status_code==200;return response.json()['drawings']
            def current():
                values=listing();assert len(values)==1,{'drawings':values,'attempts':attempts,'errors':page.locator('.drawing-error').all_text_contents()};return values[0]
            undo=page.get_by_label('Çizim değişikliğini geri al',exact=True)
            redo=page.get_by_label('Çizim değişikliğini yinele',exact=True)
            def click(button):button.click();pause()
            def field():return page.get_by_label('Çizim fiyatı',exact=True)
            def edit(price):field().fill(price);click(page.get_by_role('button',name='Kaydet',exact=True))
            def create_drawing():
                page.locator('.drawing-tools').get_by_label('Yatay çizgi',exact=True).click();page.wait_for_timeout(550)
                rect=page.locator('.chart-host').bounding_box()
                page.mouse.click(rect['x']+rect['width']*.55,rect['y']+rect['height']*.45);pause()
            create_drawing();original=current();original_price=original['geometry']['anchors'][0]['price']
            assert original['revision']==1 and undo.is_enabled()
            record('create_persisted_as_one_drawing')
            delay[0]=True;edit('140.5');page.wait_for_timeout(400);assert current()['revision']==2
            record('delayed_edit_creates_one_revision',response_delay_ms=350)
            click(undo);assert current()['geometry']['anchors'][0]['price']==original_price and current()['revision']==3
            record('undo_edit_restores_previous_geometry')
            click(redo);assert float(current()['geometry']['anchors'][0]['price'])==140.5 and current()['revision']==4
            record('redo_edit_reapplies_once')
            click(page.get_by_role('button',name='Sil',exact=True));assert not listing()
            record('delete_is_persisted')
            click(undo);assert float(current()['geometry']['anchors'][0]['price'])==140.5 and current()['revision']==6
            record('undo_delete_restores_same_id',id_preserved=current()['drawing_id']==original['drawing_id'])
            click(redo);assert not listing();record('redo_delete_removes_once')
            click(undo);edit('141.5');assert redo.is_disabled() and current()['revision']==9
            record('new_edit_discards_redo_branch')
            lose[0]=True;before=len(attempts);edit('142.5')
            committed=copy.deepcopy(current());assert committed['revision']==10
            assert page.get_by_role('button',name='Kaydet',exact=True).is_disabled()
            retry=page.get_by_role('button',name='Aynı kaydı tekrar dene',exact=True);assert retry.is_visible()
            record('lost_response_keeps_ui_locked_and_server_commit')
            click(retry);assert current()==committed
            first,second=attempts[before:];assert first['body']==second['body'] and first['path']==second['path']
            assert field().input_value()=='142.5' and page.get_by_role('button',name='Kaydet',exact=True).is_enabled()
            record('retry_is_idempotent_same_request_and_no_extra_revision')
            # An independent writer produces a genuine optimistic revision conflict.
            winner={**committed['geometry'],'anchors':[dict(committed['geometry']['anchors'][0],price='143.5')]}
            response=api[0].patch('/api/drawings/'+committed['drawing_id'],json={'request_id':str(uuid.uuid4()),'expected_revision':10,'geometry':winner})
            assert response.status_code==200
            edit('144.5');assert attempts[-1]['status']==409
            assert float(current()['geometry']['anchors'][0]['price'])==143.5 and current()['revision']==11
            assert page.get_by_text('Çizim başka bir ekranda değişmiş.',exact=False).count()==1
            record('revision_conflict_cannot_overwrite_independent_writer')
            click(page.get_by_role('button',name='Son kaydı yükle',exact=True))
            assert undo.is_disabled() and redo.is_disabled()
            page.locator('.drawing-list button').first.click();pause();assert field().input_value()=='143.5'
            record('conflict_reload_resets_unsafe_history')
            page.reload();page.wait_for_timeout(350)
            assert page.locator('.drawing-list button').count()==1 and undo.is_disabled()
            record('page_reload_preserves_server_drawing_not_session_undo_stack')
            api[0].__exit__(None,None,None);api[0]=client()
            click(page.get_by_role('button',name='Sunucudan yenile',exact=True));assert current()['revision']==11
            record('api_lifespan_restart_preserves_sqlite_drawing')
            sockets[-1].send(json.dumps({'type':'snapshot','symbol':'BTCUSDT','interval':'15m','generation':1,'sequence':1,'status':'LIVE','received_at':int(time.time()*1000),'candles':rows}));pause()
            create_drawing();assert len(listing())==2
            created=listing();new_id=next(d['drawing_id'] for d in created if d['drawing_id']!=original['drawing_id'])
            click(undo);assert len(listing())==1
            click(redo);assert len(listing())==2
            assert next(d for d in listing() if d['drawing_id']==new_id)['revision']==3
            record('create_undo_redo_preserves_id_and_single_revisions')
            assert not settings.execution_database.exists()
            result['api_transport']='Intercepted browser HTTP forwarded to real in-process FastAPI TestClient, not TCP outage/multi-tab browser proof'
            result['persistence']='Real isolated SQLite; API lifespan restarted once'
            result['account_access']=False;result['user_workspace_writes']=0
        finally:api[0].__exit__(None,None,None)


if __name__=='__main__':raise SystemExit(main(checks,'chart-history-actions-browser-20261109.json'))
