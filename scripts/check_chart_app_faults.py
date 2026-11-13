"""CL02 full production App persistent write faults with independent Decimal recovery checks."""
import copy,json,time
from decimal import Decimal,localcontext
from measure_chart_interactions import main,INSPECT
from generate_indicator_reference import ema_reference,rsi_reference


def checks(page,sockets,unused,result):
    result.update(date='2026-11-10',task='CL02',checks=[],numeric_comparisons=0)
    def read(expr):return page.evaluate(INSPECT[:INSPECT.index('return view?')]+f'return ({expr});'+'}')
    fixture=json.loads((__import__('pathlib').Path(__file__).resolve().parents[1]/'reports/indicator-reference-20261109.json').read_text())['cases']
    source=next(c for c in fixture if c['name']=='mixed')
    seed=[{'time':t,'open':float(c),'high':float(c)+1,'low':float(c)-1,'close':float(c),'volume':10+i,'quote_volume':1000,'close_time':t*1000+899999,'closed':i<299} for i,(t,c) in enumerate(zip(source['times'],source['closes']))]
    prefix=[dict(seed[0],time=seed[0]['time']-(10-i)*900,close_time=(seed[0]['time']-(10-i)*900)*1000+899999,closed=True) for i in range(10)]
    page.route('**/api/candles*',lambda r:r.fulfill(json={'candles':prefix,'has_more':False}))
    def send(kind,seq,rows=None,candle=None):
        packet={'type':kind,'symbol':'BTCUSDT','interval':'15m','generation':100,'sequence':seq,'status':'LIVE','received_at':int(time.time()*1000)}
        if rows is not None:packet['candles']=rows
        if candle is not None:packet['candle']=candle
        sockets[-1].send(json.dumps(packet));page.wait_for_timeout(130)
    def reset():
        page.reload();page.wait_for_timeout(250);send('snapshot',1,rows=seed)
        page.get_by_role('button',name='EMA 20/50',exact=True).click();page.get_by_role('button',name='RSI 14',exact=True).click();page.wait_for_timeout(90)
    def compare():
        data=read('({rows:view.candles,candles:series.data(),volume:chart.panes()[1].getSeries()[0].data(),lines:chart.panes().flatMap(p=>p.getSeries()).filter(s=>s.seriesType()==="Line").map(s=>s.data())})')
        assert len(data['rows'])==len(data['candles'])==len(data['volume'])
        for row,candle,volume in zip(data['rows'],data['candles'],data['volume']):
            assert all(row[k]==candle[k] for k in ['time','open','high','low','close']) and row['volume']==volume['value'] and row['time']==volume['time']
        with localcontext() as ctx:
            ctx.prec=50;prices=[Decimal(str(r['close'])) for r in data['rows']]
            refs=[ema_reference(prices,20),ema_reference(prices,50),rsi_reference(prices)]
            for line,ref,warmup in zip(data['lines'],refs,[19,49,14]):
                assert len(line)==len(ref)
                for i,(point,value) in enumerate(zip(line,ref)):
                    assert point['time']==data['rows'][i+warmup]['time'] and abs(point['value']-float(value))<=1e-8
                    result['numeric_comparisons']+=1
    targets=['Candlestick','Histogram','EMA20','EMA50','RSI14']
    for target in targets:
        for mode in ['snapshot','update','history']:
            reset()
            patch="""(()=>{const all=chart.panes().flatMap(p=>p.getSeries()),lines=all.filter(s=>s.seriesType()==='Line');const name=TARGET;const s=name==='Candlestick'||name==='Histogram'?all.find(s=>s.seriesType()===name):lines[{EMA20:0,EMA50:1,RSI14:2}[name]];window.__cl02Fault={active:true,calls:0};const originals={};for(const k of ['setData','update']){originals[k]=s[k].bind(s);s[k]=(...a)=>{window.__cl02Fault.calls++;if(window.__cl02Fault.active)throw Error('CL02_INJECTED_WRITE');return originals[k](...a);};}window.__cl02Restore=()=>{for(const k of ['setData','update'])s[k]=originals[k];};return true;})()""".replace('TARGET',json.dumps(target))
            read(patch)
            changed=copy.deepcopy(seed[-1]);changed['close']+=.5;changed['high']=max(changed['high'],changed['close']+1)
            if mode=='snapshot':send('snapshot',2,rows=seed[:-1]+[changed])
            elif mode=='update':send('update',2,candle=changed)
            else:page.locator('.chart-bottom button.text-button').click();page.wait_for_timeout(160)
            assert page.locator('.terminal').count()==1 and read('view.status')=='RENDER_ERROR',{'target':target,'mode':mode,'errors':result['page_errors']}
            sequence=read('view.sequence');send('update',sequence)
            assert read('view.status')=='RENDER_ERROR' and page.evaluate('window.__cl02Fault.calls')>0
            page.evaluate('window.__cl02Fault.active=false')
            latest=read('view.candles.at(-1)');latest['close']+=.25;latest['high']=max(latest['high'],latest['close']+1)
            send('update',sequence+1,candle=latest)
            assert read('view.status')=='LIVE' and page.locator('.terminal').count()==1
            compare();page.evaluate('window.__cl02Restore()')
            result['checks'].append({'target':target,'path':mode,'passed':True,'persistent_fault_keeps_app_alive':True,'heartbeat_cannot_clear':True,'recovery_native_values_checked':True})
    result['scope']='Full production App/native series effects; persistent controlled setData/update faults, snapshot/update/history. Not arbitrary engine creation failure/native device/raster acceptance.'
    result['production_assets_changed']=True

if __name__=='__main__':raise SystemExit(main(checks,'chart-app-fault-recovery-browser-20261110.json',production=True))
