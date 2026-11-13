"""B5 responsive/keyboard/fullscreen and native-coordinate acceptance (not touch)."""
import json
from measure_chart_interactions import main, INSPECT


def checks(page,sockets,rows,result):
    result['task']='B5';result['checks']=[]
    def read(expr):return page.evaluate(INSPECT[:INSPECT.index('return view?')]+f'return ({expr});'+'}')
    def pause():page.wait_for_timeout(180)
    def record(name,**data):result['checks'].append(dict(name=name,passed=True,**data))
    # No rendering test is permitted to write the real drawing store.
    drawings=[]
    for kind in ['horizontal','zone','trend','fibonacci']:
        anchors=[{'time':rows[240]['time'],'price':str(rows[240]['close'])}]
        if kind!='horizontal':anchors.append({'time':rows[260]['time'],'price':str(rows[260]['close']+2)})
        drawings.append({'drawing_id':'b5-'+kind,'workspace_id':'main','revision':1,'deleted':False,'updated_at':0,'geometry':{'kind':kind,'symbol':'BTCUSDT','price_source':'LAST_PRICE','label':kind,'anchors':anchors}})
    page.route('**/api/workspaces/main/drawings?**',lambda route:route.fulfill(json={'drawings':drawings}))
    page.get_by_role('button',name='Sunucudan yenile',exact=True).click();pause()
    def alignment():
        expr='''(()=>{const drawings=DRAWINGS;let errors=[];for(const d of drawings){const g=document.querySelector('[data-drawing="'+d.drawing_id+'"]');const a=d.geometry.anchors.map(p=>({x:chart.timeScale().timeToCoordinate(p.time),y:series.priceToCoordinate(Number(p.price))}));const test=(selector,attrs)=>{const el=g?.querySelector(selector);if(!el)throw Error('Missing shape');for(const [k,v] of Object.entries(attrs)){if(v===null||!Number.isFinite(v))throw Error('Missing coordinate');errors.push(Math.abs(Number(el.getAttribute(k))-v));}};if(d.geometry.kind==='horizontal')test('.shape-line',{y1:a[0].y,y2:a[0].y});else if(d.geometry.kind==='zone')test('.shape-zone',{x:Math.min(a[0].x,a[1].x),y:Math.min(a[0].y,a[1].y),width:Math.abs(a[0].x-a[1].x),height:Math.abs(a[0].y-a[1].y)});else if(d.geometry.kind==='trend')test('.shape-trend',{x1:a[0].x,x2:a[1].x,y1:a[0].y,y2:a[1].y});else for(const level of [0,.236,.382,.5,.618,.786,1]){const y=series.priceToCoordinate(Number(d.geometry.anchors[0].price)+(Number(d.geometry.anchors[1].price)-Number(d.geometry.anchors[0].price))*level);test('[data-fib="'+level+'"]',{x1:Math.min(a[0].x,a[1].x),x2:Math.max(a[0].x,a[1].x),y1:y,y2:y});}}return {fields:errors.length,max_error:Math.max(...errors)};})()'''.replace('DRAWINGS',json.dumps(drawings))
        data=read(expr);assert data['max_error']<=1,data;return data
    chart=page.get_by_role('region',name='Fiyat grafiği',exact=True)
    page.get_by_label('Görünümü sıfırla',exact=True).click();pause()
    for width,height in [(1400,1000),(1024,768),(768,1024),(390,844)]:
        before=read('chart.timeScale().getVisibleLogicalRange()')
        page.set_viewport_size({'width':width,'height':height});pause()
        after=read('chart.timeScale().getVisibleLogicalRange()')
        assert max(abs(before[k]-after[k]) for k in ['from','to'])<1e-6,(before,after)
        overflow=page.evaluate('document.documentElement.scrollWidth-innerWidth')
        assert overflow<=1,('page overflow',width,overflow)
        for label in ['Otomatik fiyat ölçeği','Güncel mumlara dön','Görünümü sıfırla','Grafiği tam ekran aç']:
            control=page.get_by_label(label,exact=True);rect=control.bounding_box()
            assert control.is_visible() and rect and rect['x']>=0 and rect['x']+rect['width']<=width+1,(label,rect)
        record('responsive_view_and_four_drawings',width=width,height=height,overflow=overflow,**alignment())
    chart.focus();before=read('chart.timeScale().getVisibleLogicalRange()')
    page.keyboard.press('+');pause();zoom=read('chart.timeScale().getVisibleLogicalRange()')
    assert zoom['to']-zoom['from']<before['to']-before['from']
    page.keyboard.press('-');pause();after=read('chart.timeScale().getVisibleLogicalRange()')
    assert max(abs(before[k]-after[k]) for k in ['from','to'])<1e-6
    record('keyboard_zoom_plus_minus')
    page.keyboard.press('ArrowLeft');pause();left=read('chart.timeScale().getVisibleLogicalRange()');assert left['from']<after['from']
    page.keyboard.press('ArrowRight');pause();right=read('chart.timeScale().getVisibleLogicalRange()');assert abs(right['from']-after['from'])<1e-6
    page.keyboard.press('End');pause();end=read('chart.timeScale().getVisibleLogicalRange()');assert abs(end['to']-(read('view.candles.length')+6))<1e-6
    record('keyboard_pan_and_latest')
    assert page.evaluate('getComputedStyle(document.activeElement).outlineStyle')!='none'
    record('chart_focus_visible')
    page.set_viewport_size({'width':1400,'height':1000});pause()
    search=page.get_by_label('Coin ara',exact=True);search.focus();before=read('chart.timeScale().getVisibleLogicalRange()')
    page.keyboard.type('BTC');page.keyboard.press('ArrowLeft');page.keyboard.press('End');pause()
    assert read('chart.timeScale().getVisibleLogicalRange()')==before and search.input_value()=='BTC'
    record('input_keys_do_not_navigate_chart')
    page.emulate_media(reduced_motion='reduce');chart.focus();page.keyboard.press('ArrowLeft');pause()
    assert page.evaluate('matchMedia("(prefers-reduced-motion: reduce)").matches')
    record('reduced_motion_navigation')
    page.locator('.skip-link').focus();page.keyboard.press('Enter');pause()
    assert page.evaluate('document.activeElement.id')=='chart-main'
    record('skip_link_moves_focus_to_main')
    session=page.context.new_cdp_session(page)
    session.send('Emulation.setDeviceMetricsOverride',{'width':1400,'height':1000,'deviceScaleFactor':2,'mobile':False});pause()
    assert page.evaluate('devicePixelRatio')==2
    record('emulated_dpr2_alignment',**alignment())
    session.send('Emulation.clearDeviceMetricsOverride');session.detach();pause()
    before=read('chart.timeScale().getVisibleLogicalRange()')
    page.get_by_label('Grafiği tam ekran aç',exact=True).click();pause()
    assert page.evaluate('document.fullscreenElement?.classList.contains("chart-panel")')
    assert page.get_by_label('Tam ekrandan çık',exact=True).is_visible()
    assert max(abs(before[k]-read('chart.timeScale().getVisibleLogicalRange()')[k]) for k in ['from','to'])<1e-6
    record('fullscreen_enter_controls_and_alignment',**alignment())
    page.get_by_label('Tam ekrandan çık',exact=True).click();pause()
    assert page.evaluate('document.fullscreenElement===null')
    assert max(abs(before[k]-read('chart.timeScale().getVisibleLogicalRange()')[k]) for k in ['from','to'])<1e-6
    record('fullscreen_exit_view_and_alignment',**alignment())
    page.evaluate("()=>{document.querySelector('.chart-panel').requestFullscreen=()=>Promise.reject(new Error('B5 denied'));}")
    page.get_by_label('Grafiği tam ekran aç',exact=True).click();pause()
    assert page.get_by_text('Tam ekran açılamadı.',exact=False).count()==1
    record('fullscreen_rejection_is_visible_not_unhandled')
    assert read('chart.options().handleScroll.vertTouchDrag') is False
    result['native_touch']='NOT_VERIFIED_PHYSICAL_DEVICE_REQUIRED'
    result['visible_desktop_fullscreen']='NOT_VERIFIED_HEADLESS_API_ONLY'


if __name__=='__main__':raise SystemExit(main(checks,'chart-access-browser-20261109.json'))
