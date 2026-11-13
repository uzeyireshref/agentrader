"""C4: real App + isolated FastAPI/SQLite drawing API through intercepted HTTP."""
import copy
import json
from pathlib import Path
import tempfile
import time
from urllib.parse import urlparse
import uuid
from fastapi.testclient import TestClient
from measure_chart_interactions import main, ROOT, INSPECT
import sys
sys.path.insert(0,str(ROOT))
from agentrader.api.app import create_app
from agentrader.application.settings import WebSettings


def checks(page,sockets,rows,result):
    result['task']='C5';result['checks']=[]
    def record(name,**data):result['checks'].append(dict(name=name,passed=True,**data))
    def pause():page.wait_for_timeout(180)
    def read(expr):return page.evaluate(INSPECT[:INSPECT.index('return view?')]+f'return ({expr});'+'}')
    with tempfile.TemporaryDirectory(prefix='agentrader-c5-') as folder:
        settings=WebSettings(Path(folder)/'app.db',Path(folder)/'execution.db',market_database=Path(folder)/'market.db')
        with TestClient(create_app(settings),base_url='http://127.0.0.1') as api:
            writes=[]
            def route(r):
                req=r.request;u=urlparse(req.url);headers={'host':u.netloc}
                for key in ['origin','content-type']:
                    if key in req.headers:headers[key]=req.headers[key]
                response=api.request(req.method,u.path+('?' +u.query if u.query else ''),content=req.post_data,headers=headers)
                if req.method in ['POST','PATCH','DELETE']:writes.append(response.status_code)
                r.fulfill(status=response.status_code,json=response.json())
            for pattern in ['**/api/workspaces/main*','**/api/workspaces/main/drawings*','**/api/drawings/*']:page.route(pattern,route)
            page.get_by_role('button',name='Sunucudan yenile',exact=True).click();pause()
            def listing():return api.get('/api/workspaces/main/drawings?symbol=BTCUSDT').json()['drawings']
            def point(fx,fy):
                b=page.locator('.chart-host').bounding_box();size=read('chart.paneSize(0)')
                return b['x']+size['width']*fx,b['y']+size['height']*fy
            labels={'horizontal':'Yatay çizgi','zone':'Fiyat bölgesi','trend':'Trend çizgisi','fibonacci':'Fibonacci'}
            expected={}
            for index,(kind,label) in enumerate(labels.items()):
                # Cancel before a complete creation: horizontal has no intermediate anchor.
                before=len(writes);tool=page.locator('.drawing-tools').get_by_label(label,exact=True)
                tool.click();page.wait_for_timeout(550)
                if kind!='horizontal':page.mouse.click(*point(.3,.3));pause()
                page.keyboard.press('Escape');pause();assert len(writes)==before and page.locator('.tool-hint').count()==0
                record('cancel_creation_without_write',kind=kind)
                tool.click();page.wait_for_timeout(550);page.mouse.click(*point(.32,.3+index*.08));pause()
                if kind!='horizontal':page.wait_for_timeout(550);page.mouse.click(*point(.68,.65+index*.04));pause()
                assert len(writes)==before+1 and writes[-1] in [200,201],writes
                d=next(d for d in listing() if d['geometry']['kind']==kind);key=d['drawing_id']
                assert d['revision']==1 and page.locator('[data-drawing="'+key+'"]').count()==1
                record('create_and_render_persisted',kind=kind)
                page.get_by_label('Çizim adı',exact=True).fill('C5 '+kind)
                count=len(d['geometry']['anchors'])
                for i in range(count):
                    field='Çizim fiyatı' if count==1 else f'Nokta {i+1} fiyatı'
                    page.get_by_label(field,exact=True).fill(str(125+index*2+i)+'.5')
                page.get_by_role('button',name='Kaydet',exact=True).click();pause()
                d=next(d for d in listing() if d['drawing_id']==key);assert d['revision']==2 and d['geometry']['label']=='C5 '+kind
                assert [float(a['price']) for a in d['geometry']['anchors']]==[125+index*2+i+.5 for i in range(count)]
                expected[key]=copy.deepcopy(d);record('edit_exact_and_persist',kind=kind)
                # Real mouse drag, Escape and release must leave storage untouched.
                handle=page.locator('[data-drawing="'+key+'"] .hit-line') if kind=='horizontal' else page.locator('[data-drawing-handles="'+key+'"] [data-anchor="0"]');b=handle.bounding_box();assert b
                x=b['x']+b['width']/2;y=b['y']+b['height']/2;before=len(writes)
                options=read('({scroll:chart.options().handleScroll,scale:chart.options().handleScale})')
                page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+20,y-12,steps=5);pause()
                assert read('({scroll:chart.options().handleScroll,scale:chart.options().handleScale})')!=options,kind+' drag never started'
                page.keyboard.press('Escape');page.mouse.up();pause()
                assert read('({scroll:chart.options().handleScroll,scale:chart.options().handleScale})')==options
                assert len(writes)==before and next(d for d in listing() if d['drawing_id']==key)==expected[key]
                record('cancel_saved_drag_without_write',kind=kind)
            page.reload();page.wait_for_timeout(500)
            assert len(listing())==4 and page.locator('.drawing-list button').count()==4
            for key,d in expected.items():
                assert next(x for x in listing() if x['drawing_id']==key)==d
                page.locator('.drawing-list button').filter(has_text=d['geometry']['label']).press('Enter');pause()
                assert page.get_by_label('Çizim adı',exact=True).input_value()==d['geometry']['label']
                assert page.locator('[data-drawing="'+key+'"]').count()==1
                record('reopen_and_keyboard_select',kind=d['geometry']['kind'])
            assert not settings.execution_database.exists()
            result['scope']='Headless App/native mouse and keyboard; drawing requests forwarded to real isolated FastAPI/SQLite; no physical touch or raster acceptance'
            result['user_workspace_writes']=0;result['account_access']=False


if __name__=='__main__':raise SystemExit(main(checks,'chart-drawing-acceptance-browser-20261110.json'))
