"""Recorded physical trace replay against production chart; automated, not physical acceptance."""
import json,time
from pathlib import Path
from check_chart_navigation import checks as navigation_checks
from measure_chart_interactions import main,INSPECT

def checks(page,sockets,rows,result):
 navigation_checks(page,sockets,rows,result)
 result['task']='B5_WHEEL_INTENT_AUTOMATED'
 page.reload();page.wait_for_timeout(350)
 sockets[-1].send(json.dumps({'type':'snapshot','symbol':'BTCUSDT','interval':'15m','generation':1,'sequence':1,'status':'LIVE','received_at':int(time.time()*1000),'candles':rows}))
 page.wait_for_timeout(200)
 def read(expr):return page.evaluate(INSPECT[:INSPECT.index('return view?')]+f'return ({expr});'+'}')
 read('chart.timeScale().setVisibleLogicalRange({from:80,to:160})');page.wait_for_timeout(250)
 before=read('({spacing:chart.timeScale().options().barSpacing,range:chart.timeScale().getVisibleLogicalRange()})')
 events=json.loads((Path(__file__).resolve().parents[1]/'frontend/tests/fixtures/physical-diagonal-v1.json').read_text())
 replay=page.evaluate("""async events=>{
 const host=document.querySelector('.chart-host'),target=host.querySelector('canvas');const box=target.getBoundingClientRect();
 const first=new WheelEvent('wheel',{deltaX:0,deltaY:1,bubbles:true,cancelable:true,clientX:box.x+box.width/2,clientY:box.y+box.height/2});
 const pendingPrevented=!target.dispatchEvent(first);await new Promise(r=>setTimeout(r,250));
 let last=events[0].t;
 for(const e of events){const delay=e.t-last;if(delay>0)await new Promise(r=>setTimeout(r,delay));last=e.t;target.dispatchEvent(new WheelEvent('wheel',{deltaX:e.dx,deltaY:e.dy,ctrlKey:e.ctrl,bubbles:true,cancelable:true,clientX:box.x+box.width/2,clientY:box.y+box.height/2}));}
 await new Promise(r=>setTimeout(r,150));return {pendingPrevented,count:events.length};
 }""",events)
 after=read('({spacing:chart.timeScale().options().barSpacing,range:chart.timeScale().getVisibleLogicalRange()})')
 assert replay['pendingPrevented'],'Pending small event leaked to native handling'
 assert abs(before['spacing']-after['spacing'])<1e-8,(before,after)
 assert abs(before['range']['from']-after['range']['from'])>1,(before,after)
 result['checks'].append({'name':'recorded_502_event_diagonal_replay','passed':True,'before':before,'after':after,**replay,'scope':'automated synthetic replay; not a new physical gesture'})

if __name__=='__main__':raise SystemExit(main(checks,'chart-wheel-intent-browser-20261110.json'))
