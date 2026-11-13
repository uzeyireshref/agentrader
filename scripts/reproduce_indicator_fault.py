"""CL02 diagnostic: persistent native indicator writer fault inside real App effect."""
import json,time
from measure_chart_interactions import main,INSPECT

def checks(page,sockets,rows,result):
    def read(expr):return page.evaluate(INSPECT[:INSPECT.index('return view?')]+f'return ({expr});'+'}')
    page.get_by_role('button',name='EMA 20/50',exact=True).click();page.get_by_role('button',name='RSI 14',exact=True).click();page.wait_for_timeout(100)
    current=read('view.candles');current[-1]['close']+=.1
    read("(()=>{const line=chart.panes().flatMap(p=>p.getSeries()).find(s=>s.seriesType()==='Line');for(const k of ['setData','update'])line[k]=()=>{throw Error('CL02_INJECTED_INDICATOR_WRITE');};return true;})()")
    sockets[-1].send(json.dumps({'type':'snapshot','symbol':'BTCUSDT','interval':'15m','generation':3,'sequence':10,'status':'LIVE','received_at':int(time.time()*1000),'candles':current}));page.wait_for_timeout(300)
    result['task']='CL02_REPRO';result['app_alive_after_indicator_failure']=page.locator('.terminal').count()==1;result['visible_status']=page.locator('.connection').all_text_contents()

if __name__=='__main__':raise SystemExit(main(checks,'chart-full-app-fault-repro-20261110.json',production=True))
