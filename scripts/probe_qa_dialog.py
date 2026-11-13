import json
from playwright.sync_api import sync_playwright,expect
from qa_chart_fixture import Fixture,ROOT
from check_chart_qa01 import menu
f=Fixture();result={'page_errors':[],'unexpected_requests':[]}
try:
 with sync_playwright() as pw:
  b=pw.chromium.launch(headless=True);p=b.new_page(viewport={'width':1536,'height':900});p.on('console',lambda m:print('console',m.type,m.text[:350],flush=True));f.setup(p,result);c=p.context.new_cdp_session(p)
  for i in range(4):
   menu(p,'Paneller','Kuru çalışma sonuçları');expect(p.get_by_text('36 / 36 senaryo geçti',exact=True)).to_be_visible();p.get_by_role('button',name='Kuru çalışma sonuçlarını kapat',exact=True).click();p.wait_for_timeout(150);c.send('Runtime.discardConsoleEntries');c.send('HeapProfiler.collectGarbage');c.send('HeapProfiler.collectGarbage');print(i,c.send('Memory.getDOMCounters'),flush=True)
  chunks=[];c.on('HeapProfiler.addHeapSnapshotChunk',lambda e:chunks.append(e['chunk']));c.send('HeapProfiler.takeHeapSnapshot',{'reportProgress':False});(ROOT/'reports/qa01-dialog.heapsnapshot').write_text(''.join(chunks),encoding='utf-8');b.close()
finally:f.close()
