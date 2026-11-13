"""CL03: actual screenshot pixel checks against native time/price coordinates."""
import io,json,math,time
from pathlib import Path
from PIL import Image
from measure_chart_interactions import main,INSPECT,ROOT


def checks(page,sockets,rows,result):
    result.update(date='2026-11-10',task='CL03',checks=[],screenshots=[])
    def read(expr):return page.evaluate(INSPECT[:INSPECT.index('return view?')]+f'return ({expr});'+'}')
    drawings=[]
    for kind,p0,p1,i0,i1 in [('horizontal',115,115,210,270),('zone',145,155,210,230),('trend',170,180,235,270),('fibonacci',190,210,210,270)]:
        anchors=[{'time':rows[i0]['time'],'price':str(p0)}]
        if kind!='horizontal':anchors.append({'time':rows[i1]['time'],'price':str(p1)})
        drawings.append({'drawing_id':'visual-'+kind,'workspace_id':'main','revision':1,'deleted':False,'updated_at':0,'geometry':{'kind':kind,'symbol':'BTCUSDT','price_source':'LAST_PRICE','label':kind,'anchors':anchors}})
    page.route('**/api/workspaces/main/drawings?**',lambda r:r.fulfill(json={'drawings':drawings}))
    page.get_by_role('button',name='Sunucudan yenile',exact=True).click();page.wait_for_timeout(200)
    output=ROOT/'reports/chart-visual-20261110';output.mkdir(exist_ok=True)
    browser=page.context.browser;base=page.url.split('?')[0];owned=[]
    def gold(rgb):r,g,b=rgb[:3];return r-b>=15 and g-b>=12 and 0<=r-g<=55
    def green(rgb):r,g,b=rgb[:3];return g-r>=25 and g-b>=10
    def measure(width,height,dpr,name,rsi=False,fullscreen=False):
        nonlocal page
        if owned:owned.pop().close()
        ctx=browser.new_context(viewport={'width':width,'height':height},device_scale_factor=dpr);owned.append(ctx);page=ctx.new_page();ws=[]
        page.on('pageerror',lambda e:result['page_errors'].append(str(e)))
        def route(r):
            from urllib.parse import urlparse
            path=urlparse(r.request.url).path
            responses={'/api/markets':{'markets':[{'symbol':'BTCUSDT','base_asset':'BTC','quote_asset':'USDT','tick_size':'0.1','contract_type':'PERPETUAL'}]},'/api/workspaces/main':{'revision':0,'preferences':{'symbol':'BTCUSDT','interval':'15m'}},'/api/workspaces/main/drawings':{'drawings':drawings},'/api/candles':{'candles':[],'has_more':False}}
            if path in responses:return r.fulfill(json=responses[path])
            if not r.request.url.startswith(base):result['unexpected_requests'].append(r.request.url);return r.abort()
            r.continue_()
        page.route('**/*',route);page.route_web_socket('**/api/market-stream*',lambda w:ws.append(w));page.goto(base);page.wait_for_timeout(250)
        ws[-1].send(json.dumps({'type':'snapshot','symbol':'BTCUSDT','interval':'15m','generation':1,'sequence':1,'status':'LIVE','received_at':int(time.time()*1000),'candles':rows}));page.wait_for_timeout(180)
        if rsi:page.get_by_role('button',name='RSI 14',exact=True).click();page.wait_for_timeout(90)
        if fullscreen:page.get_by_label('Grafiği tam ekran aç',exact=True).click();page.wait_for_timeout(120)
        assert page.evaluate('devicePixelRatio')==dpr
        read('chart.timeScale().setVisibleLogicalRange({from:200,to:280})');read('series.priceScale().setVisibleRange({from:100,to:230})');page.wait_for_timeout(180)
        page.locator('.chart-stage').scroll_into_view_if_needed();page.wait_for_timeout(90)
        assert page.evaluate('document.documentElement.scrollWidth-innerWidth')<=1
        b=page.locator('.chart-host').bounding_box();offset=page.evaluate('({x:scrollX,y:scrollY})');pane=read('chart.paneSize(0)')
        labels=page.locator('[data-drawing="visual-fibonacci"] [data-fib-label]').evaluate_all("els=>els.filter(e=>Number(getComputedStyle(e).opacity)>0).map(e=>{const b=e.getBoundingClientRect();return {top:b.top,bottom:b.bottom};}).sort((a,b)=>a.top-b.top)")
        assert all(b['top']>=a['bottom'] for a,b in zip(labels,labels[1:])),(name,labels)
        path=output/(name+'.png');raw=page.screenshot(path=str(path),full_page=True);im=Image.open(io.BytesIO(raw)).convert('RGB');scale=im.width/width;assert abs(scale-dpr)<.01
        ox=(b['x']+offset['x'])*scale;oy=(b['y']+offset['y'])*scale
        def pixel_error(x,y,axis='y',predicate=gold):
            # Native reference determines center. Tangential scan spans dashed-line gaps.
            best=math.inf
            normal=math.ceil(4*scale);tangent=math.ceil(6*scale)
            cx=ox+x*scale;cy=oy+y*scale
            for dy in range(-normal if axis=='y' else -tangent,normal+1 if axis=='y' else tangent+1):
                for dx in range(-tangent if axis=='y' else -normal,tangent+1 if axis=='y' else normal+1):
                    px=round(cx)+dx;py=round(cy)+dy
                    if 0<=px<im.width and 0<=py<im.height and predicate(im.getpixel((px,py))):
                        error=abs((py+.5-cy)/scale) if axis=='y' else abs((px+.5-cx)/scale)
                        best=min(best,error)
            return best
        probes=[]
        def probe(kind,x,y,axis='y'):
            assert 0<x<pane['width'] and 0<y<pane['height'],(name,kind,x,y,pane)
            error=pixel_error(x,y,axis);assert error<=1,{'name':name,'kind':kind,'x':x,'y':y,'error':error}
            probes.append({'kind':kind,'x':x,'y':y,'error_css_px':error})
        for d in drawings:
            kind=d['geometry']['kind'];a=d['geometry']['anchors'];coords=read('('+json.dumps(a)+').map(p=>({x:chart.timeScale().timeToCoordinate(p.time),y:series.priceToCoordinate(Number(p.price))}))')
            if kind=='horizontal':
                for f in [.2,.35,.5,.65,.8]:probe(kind,pane['width']*f,coords[0]['y'])
            elif kind=='zone':
                for f in [.25,.5,.75]:
                    x=coords[0]['x']+(coords[1]['x']-coords[0]['x'])*f
                    probe(kind,x,coords[0]['y']);probe(kind,x,coords[1]['y'])
                y=(coords[0]['y']+coords[1]['y'])/2;probe(kind,coords[0]['x'],y,'x');probe(kind,coords[1]['x'],y,'x')
            elif kind=='trend':
                for f in [.15,.3,.5,.7,.85]:probe(kind,coords[0]['x']+(coords[1]['x']-coords[0]['x'])*f,coords[0]['y']+(coords[1]['y']-coords[0]['y'])*f)
            else:
                for ratio in [0,.236,.382,.5,.618,.786,1]:
                    y=read('series.priceToCoordinate('+str(190+20*ratio)+')');probe(kind,(coords[0]['x']+coords[1]['x'])/2,y)
        candle=rows[245];x=read('chart.timeScale().timeToCoordinate('+str(candle['time'])+')')
        for field in ['high','low']:
            y=read('series.priceToCoordinate('+str(candle[field])+')');err=pixel_error(x,y,predicate=green);assert err<=1,(name,field,err)
            probes.append({'kind':'native_candle_'+field,'error_css_px':err})
        # Negative control: a 3 CSS px shifted horizontal reference must not pass.
        y=read('series.priceToCoordinate(115)');assert pixel_error(pane['width']*.35,y+3)>1
        result['checks'].append({'name':name,'viewport':[width,height],'dpr':dpr,'raster_probes':len(probes),'max_error_css_px':max(p['error_css_px'] for p in probes),'negative_shift_rejected':True,'visible_fib_labels':len(labels),'labels_do_not_overlap':True,'passed':True})
        result['screenshots'].append(str(path.relative_to(ROOT)).replace('\\','/'))
    for w,h,dpr,name in [(1400,1000,1,'wide-dpr1'),(1400,1000,1.25,'wide-dpr125'),(1400,1000,2,'wide-dpr2'),(1024,768,1,'medium-dpr1'),(768,1024,2,'portrait-dpr2'),(390,844,1,'narrow-dpr1')]:measure(w,h,dpr,name)
    measure(1400,1000,1.25,'rsi-dpr125',rsi=True)
    measure(1400,1000,1,'fullscreen-dpr1',fullscreen=True)
    page.get_by_label('Tam ekrandan çık',exact=True).click();page.wait_for_timeout(120)
    assert page.evaluate('document.fullscreenElement===null')
    measure(1400,1000,1,'fullscreen-exit-dpr1')
    if owned:owned.pop().close()
    result['scope']='Actual production screenshot pixel colors vs independent native coordinates; headless/emulated DPR/viewport, not physical display/native touch/screen-reader acceptance'
    result['user_workspace_writes']=0

if __name__=='__main__':raise SystemExit(main(checks,'chart-visual-raster-browser-20261110.json',production=True))
