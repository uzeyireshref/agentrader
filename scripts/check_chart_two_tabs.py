"""CL01: two production browser pages, real loopback FastAPI/SQLite; synthetic market only."""
import copy,hashlib,json,os,re,socket,subprocess,sys,tempfile,time,traceback
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request,build_opener,ProxyHandler
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]

def main():
    expected_bundle=re.search(r'index-[^\"/]+\.js',(ROOT/'agentrader/web_assets/index.html').read_text(encoding='utf-8')).group()
    result={'date':'2026-11-10','task':'CL01','passed':False,'checks':[],'page_errors':[],'unexpected_requests':[],'drawing_requests':[],'scope':'Two real headless production Chromium pages, same real loopback API/isolated SQLite; market REST/WebSocket synthetic; explicit refresh consistency, no cross-tab push guarantee','user_workspace_writes':0,'account_requests':0,'orders_sent':0}
    def record(name,**data):result['checks'].append(dict(name=name,passed=True,**data))
    with tempfile.TemporaryDirectory(prefix='agentrader-cl01-') as folder:
        root=Path(folder)
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        base='http://127.0.0.1:'+str(port);env=dict(os.environ,AGENTRADER_WEB_DATABASE=str(root/'app.db'),AGENTRADER_EXECUTION_DATABASE=str(root/'execution.db'),AGENTRADER_CHART_DATABASE=str(root/'market.db'),AGENTRADER_WEB_TOKEN='')
        server=subprocess.Popen([sys.executable,'-m','agentrader','web','serve','--port',str(port)],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        opener=build_opener(ProxyHandler({}))
        def api(path,body=None):
            req=Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'} if body is not None else {})
            with opener.open(req,timeout=5) as response:return json.load(response)
        try:
            for _ in range(100):
                try:api('/api/health');break
                except Exception:time.sleep(.1)
            def create(symbol):return api('/api/workspaces/main/drawings',{'request_id':'seed_'+symbol,'geometry':{'kind':'horizontal','symbol':symbol,'price_source':'LAST_PRICE','label':'CL01 '+symbol,'anchors':[{'time':1800000000,'price':'130.0'}]}})
            btc=create('BTCUSDT');eth=create('ETHUSDT');key=btc['drawing_id']
            def head():return api('/api/drawings/'+key)
            def listing(symbol):return api('/api/workspaces/main/drawings?symbol='+symbol)['drawings']
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True);result['browser']=browser.version
                context=browser.new_context(viewport={'width':1400,'height':1000});pages={};sockets={};lose={'A':False,'B':False};hold={'A':False,'B':False};held=[];attempts=[]
                markets=[{'symbol':s,'base_asset':s[:-4],'quote_asset':'USDT','contract_type':'PERPETUAL','tick_size':'0.1'} for s in ['BTCUSDT','ETHUSDT']]
                rows=[{'time':1800000000+i*900,'open':100+i*.1,'high':110+i*.1,'low':90+i*.1,'close':105+i*.1,'volume':10+i,'quote_volume':1000,'close_time':(1800000000+(i+1)*900)*1000-1,'closed':i<299} for i in range(300)]
                def pause(page):page.wait_for_timeout(200)
                def refresh(page):
                    page.get_by_role('button',name='Sunucudan yenile',exact=True).click();pause(page)
                    page.wait_for_function("!document.querySelector('.save-state')?.textContent.includes('yükleniyor')")
                def choose(page,label):page.locator('.drawing-list button').filter(has_text=label).click();pause(page)
                def edit(page,price):page.get_by_label('Çizim fiyatı',exact=True).fill(price);page.get_by_role('button',name='Kaydet',exact=True).click();pause(page)
                def undo(page):page.get_by_label('Çizim değişikliğini geri al',exact=True).click();pause(page)
                def redo(page):page.get_by_label('Çizim değişikliğini yinele',exact=True).click();pause(page)
                def value(page):return page.get_by_label('Çizim fiyatı',exact=True).input_value()
                def open_page(name):
                    p=context.new_page();pages[name]=p;sockets[name]=[]
                    def guard(r):
                        if not r.request.url.startswith(base+'/'):
                            result['unexpected_requests'].append(r.request.url);return r.abort()
                        if urlparse(r.request.url).path.startswith(('/api/account','/api/orders')):
                            result['unexpected_requests'].append(r.request.url);return r.abort()
                        r.continue_()
                    p.route('**/*',guard)
                    p.on('pageerror',lambda e:result['page_errors'].append({'tab':name,'error':str(e)}))
                    p.route('**/api/markets',lambda r:r.fulfill(json={'markets':markets}))
                    p.route('**/api/candles*',lambda r:r.fulfill(json={'candles':[],'has_more':False}))
                    p.route_web_socket('**/api/market-stream*',lambda ws:sockets[name].append(ws))
                    def drawing_route(r):
                        if r.request.method!='PATCH':return r.continue_()
                        response=r.fetch();entry={'tab':name,'body':r.request.post_data_json,'status':response.status};attempts.append(entry)
                        if lose[name]:lose[name]=False;assert response.status==200;r.abort('failed');return
                        if hold[name]:hold[name]=False;held.append((r,response));return
                        r.fulfill(response=response)
                    p.route('**/api/drawings/*',drawing_route)
                    p.goto(base);p.wait_for_timeout(700);refresh(p);choose(p,'CL01 BTCUSDT')
                    sockets[name][-1].send(json.dumps({'type':'snapshot','symbol':'BTCUSDT','interval':'15m','generation':1,'sequence':1,'status':'LIVE','received_at':int(time.time()*1000),'candles':rows}));pause(p)
                    return p
                a=open_page('A');b=open_page('B')
                assert value(a)==value(b)=='130.0';record('two_pages_read_same_revision')
                edit(a,'140.5');assert head()['revision']==2;edit(b,'141.5')
                assert attempts[-1]['status']==409 and head()['geometry']['anchors'][0]['price']=='140.5';record('stale_second_tab_write_cannot_overwrite_winner')
                retry=b.get_by_role('button',name='Aynı kaydı tekrar dene',exact=True);before=copy.deepcopy(attempts[-1]);retry.click();pause(b)
                assert attempts[-1]['status']==409 and attempts[-1]['body']==before['body'] and head()['revision']==2;record('conflict_retry_reuses_request_and_remains_safe')
                b.get_by_role('button',name='Son kaydı yükle',exact=True).click();pause(b);choose(b,'CL01 BTCUSDT');assert value(b)=='140.5';edit(b,'142.5');assert head()['revision']==3
                record('losing_tab_refreshes_and_saves_new_revision')
                undo(a);assert attempts[-1]['status']==409 and head()['revision']==3 and head()['geometry']['anchors'][0]['price']=='142.5';record('stale_undo_cannot_erase_other_tab_change')
                refresh(a);choose(a,'CL01 BTCUSDT');assert a.get_by_label('Çizim değişikliğini geri al',exact=True).is_disabled()
                undo(b);assert head()['revision']==4 and head()['geometry']['anchors'][0]['price']=='140.5';redo(b);assert head()['revision']==5 and head()['geometry']['anchors'][0]['price']=='142.5'
                record('fresh_undo_redo_each_apply_one_revision')
                refresh(a);choose(a,'CL01 BTCUSDT');lose['A']=True;edit(a,'143.5');assert head()['revision']==6
                refresh(b);choose(b,'CL01 BTCUSDT');edit(b,'144.5');assert head()['revision']==7
                first=next(x for x in reversed(attempts) if x['tab']=='A');a.get_by_role('button',name='Aynı kaydı tekrar dene',exact=True).click();pause(a)
                assert attempts[-1]['body']==first['body'] and head()['revision']==7 and head()['geometry']['anchors'][0]['price']=='144.5'
                record('lost_response_retry_after_other_tab_commit_has_no_duplicate_or_overwrite')
                edit(a,'145.5');assert attempts[-1]['status']==409 and head()['revision']==7
                refresh(a);choose(a,'CL01 BTCUSDT');assert value(a)=='144.5';record('cached_idempotent_response_requires_refresh_before_next_edit')
                a.get_by_role('button',name='Sil',exact=True).click();pause(a);assert head()['deleted'] and head()['revision']==8
                edit(b,'146.5');assert attempts[-1]['status']==409 and head()['deleted'];refresh(b);assert b.locator('.drawing-list button').count()==0
                undo(a);assert head()['revision']==9 and not head()['deleted'];refresh(b);choose(b,'CL01 BTCUSDT');assert value(b)=='144.5'
                record('delete_conflict_cannot_resurrect_and_explicit_undo_restores')
                # Hold the HTTP success after the server commit; switch market before delivery.
                hold['A']=True;edit(a,'147.5');assert held and head()['revision']==10
                a.get_by_label('Sözleşme seç',exact=True).select_option('ETHUSDT');pause(a)
                route,response=held.pop();route.fulfill(response=response);pause(a)
                assert a.get_by_label('Sözleşme seç',exact=True).input_value()=='ETHUSDT'
                assert a.locator('.drawing-list button').count()==1 and 'CL01 ETHUSDT' in a.locator('.drawing-list').inner_text()
                assert 'CL01 BTCUSDT' not in a.locator('.drawing-list').inner_text() and listing('ETHUSDT')[0]['drawing_id']==eth['drawing_id']
                record('delayed_btc_commit_response_cannot_replace_eth_drawings')
                # Workspace preferences also use optimistic revisions; explicit reload is the supported recovery.
                pause(a);a.wait_for_timeout(500)
                if a.locator('.drawing-error').count():refresh(a)
                a.get_by_label('Sözleşme seç',exact=True).select_option('BTCUSDT');pause(a);refresh(a);choose(a,'CL01 BTCUSDT')
                assert value(a)=='147.5' and head()['revision']==10 and head()['drawing_id']==key
                record('return_to_market_reads_persisted_commit_without_cross_market_mix')
                a.reload();a.wait_for_timeout(500);refresh(a)
                # A second tab may have saved preferences, so assert the intended symbol explicitly.
                if a.get_by_label('Sözleşme seç',exact=True).input_value()!='BTCUSDT':a.get_by_label('Sözleşme seç',exact=True).select_option('BTCUSDT');pause(a);refresh(a)
                choose(a,'CL01 BTCUSDT');assert value(a)=='147.5' and head()['revision']==10
                record('page_reload_keeps_winning_revision')
                assert not result['page_errors'] and not result['unexpected_requests'] and not (root/'execution.db').exists();result['drawing_requests']=attempts
                result['observed_bundle_src']={name:p.locator('script[type=module][src]').first.get_attribute('src') for name,p in pages.items()}
                assert all(expected_bundle in src for src in result['observed_bundle_src'].values())
                result['bundle']=expected_bundle
                record('both_tabs_serve_current_bundle_without_external_or_account_access')
                result['production_assets']={str(p.relative_to(ROOT/'agentrader/web_assets')):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'agentrader/web_assets').rglob('*')) if p.is_file()}
                result['passed']=True;browser.close()
        except Exception as error:result['error']=str(error);result['traceback']=traceback.format_exc()
        finally:server.terminate();server.wait(timeout=10)
    (ROOT/'reports/chart-two-tab-browser-20261110.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':result['passed'],'checks':len(result['checks']),'error':result.get('error')},ensure_ascii=True));return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
