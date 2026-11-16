"""G9 real mouse projection/render and native clipboard with isolated authenticated HTTP."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import argparse,json,math,sys,time,traceback
from fractions import Fraction
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from playwright.sync_api import sync_playwright
from agentrader.integration.chart_bot import ChartBot
from agentrader.api.session import COOKIE
from agentrader.chart.chart_evidence import snapshot
from agentrader.shared.market_environment import SOURCE,ENVIRONMENT
from scripts.integration.chart_bot_fixture import ChartBotFixture,ROOT
from scripts.integration.chart_tool_matrix_cases import candles,drawing_cases
from scripts.chart.measure_chart_interactions import INSPECT
OUT=ROOT/'reports/chart-interface-g9-20261115'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dpr',type=int,choices=(1,2),default=1);args=parser.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    report=dict(passed=False,dpr=args.dpr,checks=[],page_errors=[],unexpected_requests=[],scope='Production App, real mouse/native clipboard, isolated HTTP, synthetic market')
    def check(name,value):report['checks'].append(dict(name=name,passed=bool(value)));assert value,name
    try:
        with ChartBotFixture() as fixture, sync_playwright() as pw:
            human=fixture.human;base=fixture.base;bot=ChartBot(base,fixture.bot_token,bot_id='alpha',strategy_id='synthetic',journal=fixture.folder/'bot.db')
            human.post('/api/session');policy=human.get('/api/workspaces/main/ui-sessions?policy_only=true').json()['policy']
            manual=human.post('/api/workspaces/main/drawings?format_version=9',json=dict(request_id='sentinel',geometry=drawing_cases()[0]['geometry'])).json();mid=manual['drawing_id'];baseline=bot.get(mid)
            browser=pw.chromium.launch(headless=True);context=browser.new_context(viewport=dict(width=1536,height=1000),device_scale_factor=args.dpr,permissions=['clipboard-read','clipboard-write'])
            context.add_cookies([dict(name=COOKIE,value=human.cookies.get(COOKIE),url=base+'/api',httpOnly=True,sameSite='Strict')]);page=context.new_page();page.set_default_timeout(10000)
            page.on('pageerror',lambda e:report['page_errors'].append(str(e)));report['writes']=[]
            page.on('response',lambda r:report['writes'].append(dict(url=r.url.split('/api/')[-1],status=r.status,body=r.text())) if r.request.method in ('POST','PATCH') and '/api/' in r.url else None)
            def boundary(route):
                if not route.request.url.startswith(base+'/') or any(p in route.request.url for p in ('/api/account','/api/orders','/api/commands','/api/execution')):report['unexpected_requests'].append(route.request.url);route.abort()
                else:route.continue_()
            page.route('**/*',boundary);sockets=[];rows=candles();market=dict(symbol='BTCUSDT',base_asset='BTC',quote_asset='USDT',tick_size='.25',contract_type='PERPETUAL');identity=dict(source=SOURCE,environment=ENVIRONMENT,product='USD-M',price_type='LAST_PRICE')
            page.route('**/api/markets',lambda r:r.fulfill(json=dict(markets=[market],ui_session_bridge=policy,**identity)))
            page.route('**/api/candles*',lambda r:r.fulfill(json=dict(candles=[],has_more=False,**identity)));page.route_web_socket('**/api/market-stream*',lambda ws:sockets.append(ws))
            proof=snapshot(rows,market,dict(state='OK',missing_bars=0),symbol='BTCUSDT',interval='15m',epoch='d'*32,generation=1,revision=1).view()
            packet=dict(type='snapshot',symbol='BTCUSDT',interval='15m',generation=1,sequence=1,stream_epoch='d'*32,data_proof=proof,status='LIVE',received_at=int(time.time()*1000),market=market,quality=dict(state='OK',missing_bars=0),candles=rows,**identity)
            def feed():
                until=time.monotonic()+5
                while not sockets and time.monotonic()<until:page.wait_for_timeout(30)
                assert sockets;sockets[-1].send(json.dumps(packet));page.get_by_text('300 mum',exact=True).wait_for()
            def read(expr):return page.evaluate(INSPECT[:INSPECT.index('return view?')]+'return ('+expr+');}')
            def frame():read('(chart.timeScale().setVisibleLogicalRange({from:265,to:315}),series.applyOptions({autoscaleInfoProvider:()=>({priceRange:{minValue:80,maxValue:200}})}),series.priceScale().applyOptions({autoScale:true}),true)');page.wait_for_timeout(150)
            def listing():return human.get('/api/workspaces/main/drawings?format_version=10').json()['drawings']
            def until(fn):
                end=time.monotonic()+7
                while time.monotonic()<end:
                    result=fn()
                    if result:return result
                    page.wait_for_timeout(80)
                report['ui_excerpt']=page.locator('.terminal').inner_text()[-5000:];page.screenshot(path=str(OUT/'g9-failure.png'));raise AssertionError('State publication timed out')
            page.goto(base);feed();frame();page.get_by_label('Fibonacci araçları',exact=True).click();page.locator('.drawing-tools').get_by_label('Fibonacci projection',exact=True).click()
            for index,price in ((280,110),(294,130),(288,120)):
                p=read('({x:chart.timeScale().logicalToCoordinate('+str(index)+'),y:series.priceToCoordinate('+str(price)+')})');box=page.locator('.chart-host').bounding_box();page.mouse.click(box['x']+p['x'],box['y']+p['y']);page.wait_for_timeout(650);report.setdefault('clicks',[]).append(dict(index=index,price=price,point=p,text=page.locator('.terminal').inner_text()[-1600:]))
            until(lambda:len(listing())==2);item=next(d for d in listing() if d['drawing_id']!=mid);did=item['drawing_id'];g=item['geometry']
            check('three_click_projection_schema',g['schema']=='chart-fibonacci-projection/1' and g['basis']=='PRICE_DELTA' and len(g['anchors'])==3)
            node=page.locator('[data-drawing="'+did+'"]');node.press('Enter')
            def verify(mode):
                errors=[]
                for i,a in enumerate(g['anchors']):
                    native=read('({x:chart.timeScale().logicalToCoordinate(('+str(a['time'])+'-'+str(rows[0]['time'])+')/900),y:series.priceToCoordinate('+a['price']+')})')
                    handle=page.locator('[data-drawing-handles="'+did+'"] [data-anchor="'+str(i)+'"]')
                    errors.extend([abs(float(handle.get_attribute('cx'))-native['x']),abs(float(handle.get_attribute('cy'))-native['y'])])
                for ratio in g['levels']:
                    expected=Fraction(g['anchors'][2]['price'])+Fraction(ratio)*(Fraction(g['anchors'][1]['price'])-Fraction(g['anchors'][0]['price']))
                    y=read('series.priceToCoordinate('+str(float(expected))+')');line=node.locator('[data-fib="'+ratio+'"]').first
                    errors.append(abs(float(line.get_attribute('y1'))-y));start=read('chart.timeScale().logicalToCoordinate(('+str(g['anchors'][2]['time'])+'-'+str(rows[0]['time'])+')/900)');width=read('chart.paneSize(0).width');errors.extend([abs(float(line.get_attribute('x1'))-max(0,start)),abs(float(line.get_attribute('x2'))-width)])
                    query=bot.calculate(did,item['revision'],'level',dict(time=g['anchors'][2]['time'],ratio=ratio),symbol='BTCUSDT',interval='15m',scale=mode)['results'][0]
                    value=query['result']['value'];assert Fraction(int(value['numerator']),int(value['denominator']))==expected
                check(mode.lower()+'_three_anchors_levels_http_exact',all(math.isfinite(e) and e<=1 for e in errors));return max(errors)
            report['linear_max_css_px']=verify('LINEAR')
            page.get_by_label('Fiyat ekseni türü',exact=True).select_option('LOG');frame();report['log_max_css_px']=verify('LOG')
            for mode in ('LINEAR','LOG'):
                page.get_by_label('Fiyat ekseni türü',exact=True).select_option(mode);frame()
                handle=page.locator('[data-drawing-handles="'+did+'"] [data-anchor="2"]');box=handle.bounding_box();old=bot.get(did);target=float(old['geometry']['anchors'][2]['price'])+1.25
                y=read('series.priceToCoordinate('+str(target)+')');host=page.locator('.chart-host').bounding_box()
                page.mouse.move(box['x']+box['width']/2,box['y']+box['height']/2);page.mouse.down();page.mouse.move(box['x']+box['width']/2,host['y']+y,steps=8);page.mouse.up()
                until(lambda:bot.get(did)['revision']>old['revision']);item=bot.get(did);g=item['geometry']
                check(mode.lower()+'_third_anchor_drag',g['anchors'][:2]==old['geometry']['anchors'][:2] and abs(float(g['anchors'][2]['price'])-target)<1e-9);verify(mode)
            page.get_by_label('Fiyat ekseni türü',exact=True).select_option('LINEAR');frame()
            page.get_by_label('Çizimleri göster veya gizle',exact=True).click();panel=page.locator('#drawing-panel')
            panel.get_by_label('Çizgi rengi',exact=True).select_option('#2962ff');until(lambda:bot.get(did)['management']['color']=='#2962ff')
            panel.get_by_label('Çizgi kalınlığı',exact=True).select_option('2');until(lambda:bot.get(did)['management']['line_width']==2)
            panel.get_by_label('Çizgi stili',exact=True).select_option('dashed');until(lambda:bot.get(did)['management']['line_style']=='dashed')
            note='Uzun not 🧭\n日本語\n<script>literal</script>\n'+('Açıklama '*80)
            panel.get_by_label('Çizimin uzun notu').fill(note);panel.get_by_role('button',name='Notu kaydet',exact=True).click();until(lambda:bot.notes(did)['revision']==1)
            page.get_by_label('Çizimleri kopyala',exact=True).click();dialog=page.get_by_role('dialog',name='Çizimleri kopyala');textarea=dialog.get_by_label('Çizim paketi JSON')
            until(lambda:bool(textarea.input_value()));package=json.loads(textarea.input_value())
            check('copy_package_no_identity_and_long_note',set(package['items'][0])=={'geometry','management','linked_note'} and package['items'][0]['linked_note']['text']==note and package['items'][0]['management']['color']=='#2962ff' and package['items'][0]['management']['line_width']==2 and package['items'][0]['management']['line_style']=='dashed')
            until(lambda:page.evaluate('navigator.clipboard.readText()')==textarea.input_value());check('native_clipboard_written',True)
            dialog.get_by_label('Paket penceresini kapat').click()
            page.get_by_label('Çizimleri yapıştır',exact=True).click();dialog=page.get_by_role('dialog',name='Çizimleri yapıştır')
            dialog.get_by_label('Çizim paketi JSON').fill('{');dialog.get_by_role('button',name='Yeni çizimler olarak yapıştır').click();check('malformed_clipboard_rejected',len(listing())==2)
            mismatch=json.loads(json.dumps(package));mismatch['market']['interval']='1h';dialog.get_by_label('Çizim paketi JSON').fill(json.dumps(mismatch));dialog.get_by_role('button',name='Yeni çizimler olarak yapıştır').click()
            check('interval_mismatch_explained',dialog.get_by_role('status').text_content().find('zaman dilimine geç')>=0 and len(listing())==2)
            dialog.get_by_role('button',name='Panodan oku').click();until(lambda:bool(dialog.get_by_label('Çizim paketi JSON').input_value().startswith('{"schema"')))
            dropped=[False];committed=[]
            def lose_ack(route):
                if not dropped[0]:
                    response=route.fetch();committed.extend(response.json()['drawings']);dropped[0]=True;route.abort()
                else:route.continue_()
            page.route('**/drawing-packages/paste',lose_ack)
            dialog.get_by_role('button',name='Yeni çizimler olarak yapıştır').click();dialog.get_by_role('button',name='Aynı kaydı yeniden dene').wait_for();check('paste_unknown_ack_one_object',len(listing())==3 and len(committed)==1)
            dialog.get_by_role('button',name='Aynı kaydı yeniden dene').click();dialog.wait_for(state='hidden');copy=committed[0];cid=copy['drawing_id']
            check('paste_retry_same_id_note_origin',len(listing())==3 and bot.get(cid)['origin']['kind']=='manual' and bot.notes(cid)['text']==note and bot.get(cid)['management']==package['items'][0]['management'] and cid!=did)
            page.get_by_label('Geri al',exact=True).click();until(lambda:bot.get(cid)['deleted']);check('paste_undo_archives_note',bot.notes(cid)['state']=='TARGET_ARCHIVED')
            page.get_by_label('Yeniden yap',exact=True).click();until(lambda:not bot.get(cid)['deleted']);check('paste_redo_same_note_id',bot.notes(cid)['note_id']==copy['linked_note']['note_id'])
            page.get_by_label('Çizimleri yapıştır',exact=True).click();dialog=page.get_by_role('dialog',name='Çizimleri yapıştır');dialog.get_by_role('button',name='Panodan oku').click();until(lambda:bool(dialog.get_by_label('Çizim paketi JSON').input_value()));dialog.get_by_role('button',name='Yeni çizimler olarak yapıştır').click();dialog.wait_for(state='hidden')
            check('repeat_paste_new_identity',len(listing())==4)
            latest=page.locator('[data-drawing-handles]').get_attribute('data-drawing-handles')
            panel.get_by_label('Fibonacci oran listesi').fill('0; 1; 2');panel.get_by_label('Fibonacci zaman kapsamı').select_option('bounded')
            panel.locator('form').get_by_role('button',name='Kaydet',exact=True).click()
            until(lambda:bot.get(latest)['geometry']['levels']==['0','1','2'])
            bounded=bot.get(latest)['geometry'];end=bounded['anchors'][2]['time']+abs(bounded['anchors'][1]['time']-bounded['anchors'][0]['time'])
            expected_x=read('chart.timeScale().logicalToCoordinate(('+str(end)+'-'+str(rows[0]['time'])+')/900)')
            bounded_line=page.locator('[data-drawing="'+latest+'"] [data-fib="1"]').first
            check('bounded_extent_from_C_plus_impulse_duration',abs(float(bounded_line.get_attribute('x2'))-min(read('chart.paneSize(0).width'),expected_x))<=1)
            page.get_by_label('Çalışma alanı şablonları',exact=True).click();templates=page.get_by_role('dialog',name='Çalışma alanı ve şablonlar')
            templates.get_by_role('button',name='Seçili aracı varsayılan yap',exact=True).click()
            until(lambda:human.get('/api/workspaces/main/profile').json()['body']['drawing_defaults'].get('fibonacci_projection',{}).get('options',{}).get('levels')==['0','1','2'])
            templates.get_by_label('Şablonları kapat').click();frame()
            before_ids={d['drawing_id'] for d in listing()};page.get_by_label('Fibonacci araçları',exact=True).click();page.locator('.drawing-tools').get_by_label('Fibonacci projection',exact=True).click()
            for index,price in ((267,100),(277,110),(275,105)):
                p=read('({x:chart.timeScale().logicalToCoordinate('+str(index)+'),y:series.priceToCoordinate('+str(price)+')})');box=page.locator('.chart-host').bounding_box();page.mouse.click(box['x']+p['x'],box['y']+p['y']);page.wait_for_timeout(650)
            until(lambda:len(listing())==5);with_defaults=next(d for d in listing() if d['drawing_id'] not in before_ids)
            check('projection_tool_defaults_applied',with_defaults['geometry']['levels']==['0','1','2'] and with_defaults['geometry']['basis']=='PRICE_DELTA' and with_defaults['management']['color']=='#2962ff' and with_defaults['management']['line_width']==2 and with_defaults['management']['line_style']=='dashed')
            sockets.clear();page.reload();feed();frame();check('reload_preserves_projection_and_note',bot.notes(did)['text']==note and len(listing())==5)
            check('manual_sentinel_unchanged',bot.get(mid)==baseline)
            check('no_browser_financial_external_errors',not report['page_errors'] and not report['unexpected_requests'] and not (fixture.folder/'execution.db').exists())
            page.screenshot(path=str(OUT/('projection-clipboard-dpr'+str(args.dpr)+'.png')));browser.close();report['passed']=True
    except Exception:report['error']=traceback.format_exc()
    if report['passed']:
        report['write_count']=len(report.pop('writes',[]));report.pop('clicks',None)
    (OUT/('browser-dpr'+str(args.dpr)+'.json')).write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(dict(passed=report['passed'],checks=len(report['checks']),error=report.get('error')),ensure_ascii=True));return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
