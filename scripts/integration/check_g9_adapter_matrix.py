"""G9 production ChartBot/CLI -> real isolated HTTP, 26 variants and restart recovery."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

from copy import deepcopy
from fractions import Fraction
import hashlib,json,os,subprocess,sys,time,traceback
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from playwright.sync_api import sync_playwright
from agentrader.integration.chart_bot import ChartBot,BotError
from agentrader.api.session import COOKIE
from agentrader.chart.chart_evidence import snapshot
from agentrader.shared.market_environment import SOURCE,ENVIRONMENT
from scripts.integration.chart_bot_fixture import ChartBotFixture,ROOT
from scripts.integration.chart_tool_matrix_cases import drawing_cases,candles,START,STEP

OUT=ROOT/'reports/chart-interface-g9-20261115'


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    report=dict(passed=False,scope='PRODUCTION_ADAPTER_AND_CLI_REAL_LOOPBACK_HTTP_EXPLICIT_SYNTHETIC_MARKET_NOT_LIVE_DEMO_STRATEGY',
                checks=[],cases=[],page_errors=[],unexpected_requests=[],account_requests=0,order_requests=0)
    def check(name,value):report['checks'].append(dict(name=name,passed=bool(value)));assert value,name
    def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    try:
        with ChartBotFixture() as fixture:
            human=fixture.human;base=fixture.base;journal=fixture.folder/'adapter.db'
            def adapter(**kwargs):return ChartBot(base,fixture.bot_token,bot_id='alpha',strategy_id='synthetic',journal=journal,**kwargs)
            bot=adapter();catalog=bot.discover();check('verified_identity_catalog',bot.identify()['namespace']==bot.namespace and catalog['access_schema']=='chart-tool-access/1')
            geometry=drawing_cases()[0]['geometry']
            manual=human.post('/api/workspaces/main/drawings?format_version=9',json=dict(request_id='manual-sentinel',geometry={**geometry,'label':'Manual sentinel'})).json();mid=manual['drawing_id']
            profile=human.get('/api/workspaces/main/profile').json()
            profile['body']['view']['theme']='light'
            response=human.put('/api/workspaces/main/profile',json=dict(request_id='profile-sentinel',expected_revision=profile['revision'],body=profile['body']));assert response.status_code==200
            check('user_cookie_pairing',human.post('/api/session').status_code==200)
            policy=human.get('/api/workspaces/main/ui-sessions?policy_only=true').json()['policy']
            rows=candles();market=dict(symbol='BTCUSDT',base_asset='BTC',quote_asset='USDT',tick_size='.25',contract_type='PERPETUAL')
            identity=dict(source=SOURCE,environment=ENVIRONMENT,product='USD-M',price_type='LAST_PRICE')
            proof=snapshot(rows,market,dict(state='OK',missing_bars=0),symbol='BTCUSDT',interval='15m',epoch='d'*32,generation=1,revision=1).view()
            packet=dict(type='snapshot',symbol='BTCUSDT',interval='15m',generation=1,sequence=1,stream_epoch='d'*32,data_proof=proof,status='LIVE',received_at=1,market=market,quality=dict(state='OK',missing_bars=0),candles=rows,**identity)
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True);page=browser.new_page(viewport=dict(width=1536,height=950));page.set_default_timeout(10000)
                page.context.add_cookies([dict(name=COOKIE,value=human.cookies.get(COOKIE),url=base+'/api',httpOnly=True,sameSite='Strict')])
                page.on('pageerror',lambda e:report['page_errors'].append(str(e)));sockets=[]
                def boundary(route):
                    if not route.request.url.startswith(base+'/') or any(p in route.request.url for p in ('/api/account','/api/orders','/api/commands','/api/execution')):
                        report['unexpected_requests'].append(route.request.url);route.abort()
                    else:route.continue_()
                page.route('**/*',boundary)
                page.route('**/api/markets',lambda r:r.fulfill(json=dict(markets=[market],ui_session_bridge=policy,**identity)))
                page.route('**/api/candles*',lambda r:r.fulfill(json=dict(candles=[],has_more=False,**identity)))
                page.route_web_socket('**/api/market-stream*',lambda ws:sockets.append(ws))
                page.goto(base);until=time.monotonic()+10
                while not sockets and time.monotonic()<until:page.wait_for_timeout(50)
                assert sockets;sockets[-1].send(json.dumps(packet))
                page.get_by_text('300 mum',exact=True).wait_for();page.locator('[data-drawing="'+mid+'"]').press('Enter')
                page.get_by_label('Çizimleri göster veya gizle',exact=True).click();panel=page.locator('#drawing-panel')
                panel.get_by_label('Çizim adı').fill('Manual user undo sentinel');panel.locator('form').get_by_role('button',name='Kaydet',exact=True).click()
                page.wait_for_timeout(250);check('user_undo_available_before_bot',not page.get_by_label('Geri al',exact=True).is_disabled())
                manual=bot.get(mid)
                human.put('/api/drawings/'+mid+'/notes',json=dict(request_id='manual-note',expected_revision=0,expected_drawing_revision=manual['revision'],text='Manual 🧭\nMust remain byte-for-byte'))
                baseline=bot.get(mid);profile_before=human.get('/api/workspaces/main/profile').json();workspace_before=human.get('/api/workspaces/main').json()
                sentinels=dict(drawing=digest(baseline),profile=digest(profile_before),workspace=digest(workspace_before))
                # Every drawing and note is created by the production adapter, never by test-client CRUD.
                created=[]
                for case in drawing_cases(include_projection=True):
                    cid=case['case_id'];g=case['geometry'];item=bot.create(cid+'-create',g);did=item['drawing_id'];created.append(did)
                    note='Adapter 🧭 '+cid+'\nUnicode 日本語 and multiline.'
                    bot.save_note(cid+'-note',did,0,1,note)
                    fresh=bot.snapshot('BTCUSDT','15m');read=next(d for d in fresh['objects'] if d['drawing_id']==did)
                    assert read['geometry']==item['geometry'] and read['linked_note']['text']==note and read['origin']['bot_id']=='alpha'
                    op=('priceAt' if g['kind'] in ('text','note','price_label') else 'geometry' if g.get('schema')=='chart-channel-family/1' else 'level' if g['kind'] in ('fibonacci','fibonacci_extension','fibonacci_projection') else 'contains' if g['kind']=='zone' else 'boundsAt' if g['kind']=='parallel_channel' else 'riskReward' if g['kind'] in ('long_plan','short_plan') else 'measurement' if g['kind']=='ruler' else 'priceAt')
                    inputs={} if op in ('geometry','measurement','riskReward') else dict(time=max(START+287*STEP,g['anchors'][2]['time']) if g['kind']=='fibonacci_projection' else START+287*STEP)
                    if op=='contains':inputs['query_price']='120'
                    if op=='level':inputs['ratio']='0.618'
                    query=bot.calculate(did,1,op,inputs,symbol='BTCUSDT',interval='15m',context_id=fresh['context_id'])['results'][0]
                    if g['kind'] in ('text','note','price_label'):
                        assert query['state']=='UNSUPPORTED_OPERATION' and 'result' not in query
                    else:
                        assert query['state']=='READY',(cid,query)
                        assert query['linked_note']['text']==note
                        if op=='priceAt':
                            expected=Fraction(g['anchors'][0]['price'])
                            if len(g['anchors'])==2:expected+=(Fraction(g['anchors'][1]['price'])-expected)*Fraction(7,14)
                            value=query['result']['value'];assert Fraction(int(value['numerator']),int(value['denominator']))==expected
                    package=bot.export_package('BTCUSDT','15m',[dict(drawing_id=did,expected_revision=1,expected_note_revision=1)])
                    pasted=bot.paste_package(cid+'-package','BTCUSDT','15m',package)['drawings'][0]
                    assert pasted['drawing_id']!=did and pasted['origin']['kind']=='bot' and pasted['linked_note']['text']==note and pasted['geometry']==item['geometry']
                    bot.delete(cid+'-package-cleanup',pasted['drawing_id'],1)
                    changed=bot.update(cid+'-edit',did,1,{**item['geometry'],'label':'Adapter edited '+cid})
                    assert changed['revision']==2 and changed['linked_note']['text']==note
                    report['cases'].append(dict(case_id=cid,drawing_id=did,record_schema=g.get('schema','LEGACY_GEOMETRY_V1'),create_note_fresh_read_edit='PASS',numeric_state=query['state'],query=query,order_authority=False))
                check('all_26_variants_adapter_roundtrip',len(report['cases'])==26)
                check('23_math_ready_3_display_only',sum(c['numeric_state']=='READY' for c in report['cases'])==23 and sum(c['numeric_state']=='UNSUPPORTED_OPERATION' for c in report['cases'])==3)
                large_note='🧭'*4000;targets=[]
                for i,did in enumerate(created[:5]):
                    current=bot.get(did);bot.save_note('large-note-'+str(i),did,current['linked_note']['revision'],current['revision'],large_note)
                    targets.append(dict(drawing_id=did,expected_revision=current['revision'],expected_note_revision=current['linked_note']['revision']+1))
                bundle=bot.export_package('BTCUSDT','15m',targets)
                large_bytes=len(json.dumps(bundle,ensure_ascii=False).encode('utf-8'));assert large_bytes>65536
                large_copy=bot.paste_package('large-package','BTCUSDT','15m',bundle)['drawings']
                check('large_utf8_package_over_64k',all(bot.get(d['drawing_id'])['linked_note']['text']==large_note for d in large_copy));report['large_package_utf8_bytes']=large_bytes
                created.extend(d['drawing_id'] for d in large_copy)
                # Deliberately discard a committed create response at the transport boundary.
                uncertain=adapter(attempts=1);real=uncertain.http
                class Drop:
                    def request(self,method,path,body=None):
                        result=real.request(method,path,body)
                        if method=='POST' and '/drawings?' in path:raise BotError('CHART_TRANSPORT_UNAVAILABLE',pending=True)
                        return result
                uncertain._transport=Drop()
                try:uncertain.create('lost-once',geometry);raise AssertionError('Fault not injected')
                except BotError as error:assert error.pending
                check('unknown_commit_durably_pending',len(uncertain.journal.pending(uncertain.scope))==1)
                fixture.stop();fixture.start();bot=adapter()
                recovered=bot.resume_pending();check('server_adapter_restart_recovers_once',len(recovered)==1 and recovered[0]['duplicate'] and recovered[0]['revision']==1)
                check('restart_finds_all_own',len(bot.find_own('BTCUSDT','15m'))==len(created)+1)
                command=[sys.executable,'-m','agentrader','chart-bot','--url',base,'--bot-id','alpha','--strategy-id','synthetic','--journal',str(journal),'own','BTCUSDT','15m']
                cli=subprocess.run(command,cwd=ROOT,env=fixture.env,capture_output=True,text=True,encoding='utf-8',timeout=15)
                check('separate_cli_process_finds_own',cli.returncode==0 and len(json.loads(cli.stdout)['result'])==len(created)+1)
                did=created[0];current=bot.get(did)
                try:bot.update('stale',did,1,current['geometry']);raise AssertionError('No conflict')
                except BotError as error:check('stale_revision_rejected',error.code=='DRAWING_REVISION_CONFLICT')
                try:bot.delete('manual-denied',mid,baseline['revision']);raise AssertionError('Manual modified')
                except BotError as error:check('manual_delete_rejected',error.code=='BOT_OBJECT_PROTECTED')
                try:bot.create('wrong-source',{**geometry,'price_source':'MARK_PRICE'});raise AssertionError('Source accepted')
                except BotError as error:check('wrong_source_rejected',error.code=='SOURCE_MISMATCH')
                # Explicit identities and revisions; never delete the whole workspace.
                for did in created+[recovered[0]['drawing_id']]:
                    current=bot.get(did);bot.delete('cleanup-'+did,did,current['revision'])
                check('cleanup_only_own_objects',bot.find_own('BTCUSDT','15m')==[] and not bot.get(mid)['deleted'])
                check('manual_drawing_note_unchanged',digest(bot.get(mid))==sentinels['drawing'])
                check('saved_profile_workspace_unchanged',digest(human.get('/api/workspaces/main/profile').json())==sentinels['profile'] and digest(human.get('/api/workspaces/main').json())==sentinels['workspace'])
                check('user_undo_available_after_bot',not page.get_by_label('Geri al',exact=True).is_disabled())
                check('journal_does_not_store_credentials',fixture.bot_token.encode() not in journal.read_bytes() and fixture.human_token.encode() not in journal.read_bytes())
                check('no_execution_or_market_store',not (fixture.folder/'execution.db').exists() and not (fixture.folder/'market.db').exists())
                check('no_browser_or_external_errors',not report['page_errors'] and not report['unexpected_requests'])
                report['manual_sentinels_sha256']=sentinels;report['adapter_identity']=bot.identify();report['catalog']=catalog
                page.screenshot(path=str(OUT/'adapter-user-history.png'));browser.close();report['passed']=True
    except Exception:report['error']=traceback.format_exc()
    (OUT/'adapter-matrix.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(dict(passed=report['passed'],cases=len(report['cases']),checks=len(report['checks']),error=report.get('error')),ensure_ascii=True))
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
