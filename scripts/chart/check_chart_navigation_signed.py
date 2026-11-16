"""Current production UI, isolated stores; native gestures and signed drawing roundtrip."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import json
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from scripts.chart.qa_chart_fixture import Fixture
ROOT=Path(__file__).resolve().parents[2]

def main():
 f=Fixture();result=dict(passed=False,checks=[],page_errors=[],unexpected_requests=[])
 def record(name,**kw):result['checks'].append(dict(name=name,passed=True,**kw))
 try:
  item=f.items['BTCUSDT'][-1]
  f.api('/api/workspaces/main/drawing-operations?format_version=10',dict(request_id='free-one-slot',operations=[dict(drawing_id=item['drawing_id'],expected_revision=item['revision'],geometry=item['geometry'],management=item['management'],deleted=True)]),'POST')
  with sync_playwright() as pw:
   browser=pw.chromium.launch();p=browser.new_page(viewport=dict(width=1536,height=900));p.set_default_timeout(8000);f.setup(p,result,wait=False);expect(p.get_by_text('1001 mum',exact=True)).to_be_visible();expect(p.locator('[data-drawing]')).to_have_count(199)
   f.pin_view(p);box=p.locator('.chart-host').bounding_box();size=f.read(p,'chart.paneSize(0)')
   def point(x,y):return box['x']+x,box['y']+y
   def range_():return f.read(p,'series.priceScale().getVisibleRange()')
   def tool(name):
    p.get_by_label('Hızlı erişimi aç',exact=True).click();p.get_by_role('button',name='Araçlar',exact=True).click();q=p.get_by_role('combobox',name='Hızlı erişimde ara');q.fill(name);q.press('Enter');p.wait_for_timeout(150)
   # Manual price axis changes span smoothly about the grab point, independently of time zoom.
   before=range_();time_before=f.read(p,'chart.timeScale().getVisibleLogicalRange()');x,y=point(size['width']+35,size['height']*.5)
   p.mouse.move(x,y);p.mouse.down();p.mouse.move(x,y+70,steps=12);p.mouse.up();p.wait_for_timeout(180);after=range_();factor=(after['to']-after['from'])/(before['to']-before['from']);assert 1.3<factor<1.8,factor
   assert f.read(p,'chart.timeScale().getVisibleLogicalRange()')==time_before;record('price_axis_exponential_zoom_without_time_zoom',span_factor=factor)
   p.mouse.dblclick(x,y);p.wait_for_timeout(100);assert f.read(p,'series.priceScale().options().autoScale');record('axis_double_click_restores_auto')
   # Empty plot vertical drag leaves auto only when actual vertical intent exists.
   # Dense 199-object fixture covers the plot; hide its hit targets for this empty-plot gesture.
   style=p.add_style_tag(content='.drawings-overlay{display:none!important}')
   start=f.read(p,'series.priceToCoordinate(120)');x,y=point(size['width']*.2,size['height']*.2)
   p.mouse.move(x,y);p.mouse.down();p.mouse.move(x+10,y+65,steps=12);p.mouse.up();p.wait_for_timeout(150)
   assert not f.read(p,'series.priceScale().options().autoScale');assert abs(f.read(p,'series.priceToCoordinate(120)')-start)>20;record('plot_drag_releases_auto_and_pans_vertically');style.evaluate('(el)=>el.remove()')
   # Tool changes must NEVER translate a user's negative visible range.
   f.read(p,'series.priceScale().setVisibleRange({from:-80,to:155})');p.wait_for_timeout(150);before=range_()
   tool('Yatay çizgi');assert range_()==before
   x,y=point(size['width']*.7,size['height']*.94);p.mouse.move(x,y);p.wait_for_timeout(150)
   assert p.get_by_test_id('drawing-mouse-price').is_visible();assert float(p.get_by_test_id('drawing-mouse-price').inner_text().replace(',','.'))<0
   line=p.locator('.creation-preview .shape-line');assert line.count()==1;assert abs(float(line.get_attribute('y1'))-size['height']*.94)<2
   with p.expect_response(lambda r:'/api/workspaces/main/' in r.url and r.request.method=='POST') as response:p.mouse.click(x,y)
   assert response.value.status in (200,201);expect(p.locator('[data-drawing]')).to_have_count(200);record('negative_horizontal_created_without_viewport_jump')
   heads=f.api('/api/workspaces/main/drawings?format_version=10')['drawings'];created=next(d for d in heads if d['drawing_id'] not in {d['drawing_id'] for d in f.items['BTCUSDT']});assert float(created['geometry']['anchors'][0]['price'])<0
   # Actual drawing anchor drag goes through zero and saves once; not a domain helper test.
   p.get_by_role('button',name='Geri al',exact=True).click();expect(p.locator('[data-drawing]')).to_have_count(199)
   tool('Trend çizgisi');assert p.locator('button[aria-label="Trend çizgisi"]').get_attribute('aria-pressed')=='true'
   x1,y1=point(size['width']*.3,size['height']*.75);x2,y2=point(size['width']*.6,size['height']*.95)
   p.mouse.click(x1,y1);p.wait_for_timeout(650)
   assert 'İkinci' in p.locator('.tool-hint').inner_text(),p.locator('.tool-hint').inner_text()
   f.read(p,'(window.__navClicks=[],chart.subscribeClick(e=>window.__navClicks.push({point:e.point,pane:e.paneIndex})))')
   p.mouse.move(x2,y2);p.wait_for_timeout(120);p.mouse.click(x2,y2,delay=60);p.wait_for_timeout(300)
   print(json.dumps(dict(clicks=p.evaluate('window.__navClicks'),hint=p.locator('.tool-hint').all_inner_texts(),range=range_(),target=p.evaluate('([x,y])=>document.elementFromPoint(x,y)?.outerHTML.slice(0,250)',[x2,y2])),ensure_ascii=True))
   expect(p.locator('[data-drawing]')).to_have_count(200);record('trend_crossing_zero_created')
   p.reload();expect(p.get_by_text('1001 mum',exact=True)).to_be_visible();expect(p.locator('[data-drawing]')).to_have_count(200)
   heads=f.api('/api/workspaces/main/drawings?format_version=10')['drawings'];saved=next(d for d in heads if d['geometry']['kind']=='trend' and any(float(a['price'])<0 for a in d['geometry']['anchors']));assert saved;record('negative_geometry_survives_real_reload')
   assert not result['page_errors'] and not result['unexpected_requests'];result.update(passed=True,assets=f.read(p,'document.querySelector("script[type=module]").getAttribute("src")'),scope='Synthetic feed and isolated SQLite; actual Chromium pointer/API/reload, no user database writes');browser.close()
 finally:
  f.close();(ROOT/'reports/chart-navigation-signed-20261115.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(result,ensure_ascii=True))
if __name__=='__main__':main()
