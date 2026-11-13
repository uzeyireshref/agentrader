import json,time
from playwright.sync_api import sync_playwright
from qa_chart_fixture import Fixture,ROOT
from check_chart_qa01 import native_point
f=Fixture();r={'page_errors':[],'unexpected_requests':[]};events=[];done=[]
try:
 with sync_playwright() as pw:
  b=pw.chromium.launch(headless=True);p=b.new_page(viewport={'width':1536,'height':900});f.setup(p,r);f.pin_view(p);c=p.context.new_cdp_session(p);c.on('Tracing.dataCollected',lambda e:events.extend(e['value']));c.on('Tracing.tracingComplete',lambda e:done.append(True));c.send('Tracing.start',{'categories':'input,latencyInfo,benchmark,cc,devtools.timeline','transferMode':'ReportEvents'})
  for i in range(5):
   x,y=native_point(f,p);p.mouse.move(x,y);p.mouse.wheel(0,-80 if i%2==0 else 80);p.wait_for_timeout(200)
  c.send('Tracing.end')
  for _ in range(100):
   if done:break
   p.wait_for_timeout(50)
  (ROOT/'reports/qa01-wheel-trace.json').write_text(json.dumps({'traceEvents':events}),encoding='utf-8');names={e['name'] for e in events if 'Latency' in e['name'] or 'latency' in e['name']};print(sorted(names))
  for name in sorted(names):
   found=[e for e in events if e['name']==name];print(name,len(found),str(found[:2])[:1400])
  b.close()
finally:f.close()
