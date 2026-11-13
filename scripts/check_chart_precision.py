"""C3 native editing, exact prices, UTC, gap drag and creation magnet."""
import copy
from datetime import datetime, timezone
import json
import time
from urllib.parse import parse_qs,urlparse
from measure_chart_interactions import main, INSPECT


def checks(page,sockets,rows,result):
    result['task']='C3';result['checks']=[]
    def record(name,**data):result['checks'].append(dict(name=name,passed=True,**data))
    def pause():page.wait_for_timeout(130)
    def read(expr):return page.evaluate(INSPECT[:INSPECT.index('return view?')]+f'return ({expr});'+'}')
    markets=[{'symbol':s,'base_asset':s[:-4],'quote_asset':'USDT','tick_size':tick,'contract_type':'PERPETUAL'} for s,tick in [('BTCUSDT','0.25'),('MICROUSDT','0.00000001')]]
    data=[{**c,'time':c['time']+(2700 if i>=240 else 0),'close_time':c['close_time']+(2700000 if i>=240 else 0),'open':100+i*.25,'close':100+i*.25+.25,'high':100+i*.25+.5,'low':100+i*.25-.5} for i,c in enumerate(rows)]
    data[250]['high']=180
    def item(key,kind,anchors,symbol='BTCUSDT'):
        return {'drawing_id':key,'workspace_id':'main','revision':1,'deleted':False,'updated_at':0,'geometry':{'kind':kind,'symbol':symbol,'price_source':'LAST_PRICE','label':key,'anchors':anchors}}
    items=[item('C3 trend','trend',[{'time':data[239]['time'],'price':'159.75'},{'time':data[244]['time'],'price':'161.00'}]),
           item('C3 reverse','fibonacci',[{'time':data[245]['time'],'price':'169.00'},{'time':data[241]['time'],'price':'168.00'}]),
           item('C3 micro','horizontal',[{'time':data[239]['time'],'price':'0.00000033'}],'MICROUSDT')]
    writes=[]
    page.route('**/api/markets',lambda r:r.fulfill(json={'markets':markets}))
    def get_drawings(route):
        symbol=parse_qs(urlparse(route.request.url).query)['symbol'][0]
        route.fulfill(json={'drawings':[d for d in items if d['geometry']['symbol']==symbol]})
    page.route('**/api/workspaces/main/drawings?**',get_drawings)
    def patch(route):
        from urllib.parse import unquote
        key=unquote(route.request.url.rsplit('/',1)[1]);body=route.request.post_data_json
        d=next(d for d in items if d['drawing_id']==key)
        assert body['expected_revision']==d['revision']
        d['geometry']=body['geometry'];d['revision']+=1;writes.append({'id':key,'body':body});route.fulfill(json=d)
    page.route('**/api/drawings/*',patch)
    def create(route):
        if route.request.method!='POST':return route.fallback()
        body=route.request.post_data_json;d=item('new-'+str(len(items)),body['geometry']['kind'],body['geometry']['anchors']);d['geometry']=body['geometry'];items.append(d);writes.append({'id':d['drawing_id'],'body':body});route.fulfill(json=d)
    page.route('**/api/workspaces/main/drawings',create)
    page.reload();page.wait_for_timeout(350)
    session=page.context.new_cdp_session(page);session.send('Emulation.setTimezoneOverride',{'timezoneId':'Asia/Baku'})
    def snapshot(symbol,candles):
        sockets[-1].send(json.dumps({'type':'snapshot','symbol':symbol,'interval':'15m','generation':1,'sequence':1,'status':'LIVE','received_at':int(time.time()*1000),'market':next(m for m in markets if m['symbol']==symbol),'candles':candles}));pause()
    snapshot('BTCUSDT',data)
    def select(key):page.locator('.drawing-list button').filter(has_text=key).click();pause()
    def save():page.get_by_role('button',name='Kaydet',exact=True).click();pause()
    def iso(t):
        value=datetime.fromtimestamp(t,timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')
        return value[:-3] if value.endswith(':00') else value
    trend=items[0];select('C3 trend')
    count=len(writes)
    page.get_by_label('Nokta 1 fiyatı',exact=True).fill('160.10');save()
    assert len(writes)==count and page.get_by_text('Fiyat 0.25 adımına uymalı.',exact=True).count()==1
    assert page.get_by_role('button',name='Kaydet',exact=True).is_enabled()
    record('off_tick_edit_rejected_locally_without_retry_lock')
    page.get_by_label('Nokta 1 fiyatı',exact=True).fill('160,25')
    page.get_by_label('Nokta 2 fiyatı',exact=True).fill('161.75')
    t0=data[239]['time'];t1=data[244]['time']+60
    page.get_by_label('Nokta 1 zamanı (UTC)',exact=True).fill(iso(t0))
    page.get_by_label('Nokta 2 zamanı (UTC)',exact=True).fill(iso(t1));save()
    assert len(writes)==count+1 and trend['geometry']['anchors']==[{'time':t0,'price':'160.25'},{'time':t1,'price':'161.75'}]
    record('quarter_tick_and_utc_save_in_non_utc_browser',timezone='Asia/Baku',anchors=copy.deepcopy(trend['geometry']['anchors']))
    page.get_by_role('button',name='Sunucudan yenile',exact=True).click();pause();select('C3 trend')
    assert page.get_by_label('Nokta 1 fiyatı',exact=True).input_value()=='160.25'
    assert page.get_by_label('Nokta 2 zamanı (UTC)',exact=True).input_value().startswith(iso(t1))
    record('reload_keeps_exact_price_and_utc')
    read('chart.timeScale().setVisibleLogicalRange({from:200,to:280})');pause()
    before=copy.deepcopy(trend['geometry']['anchors']);rect=page.locator('[data-drawing="C3 trend"] .hit-line').bounding_box();assert rect
    dx=read(f'chart.timeScale().timeToCoordinate({data[240]["time"]})-chart.timeScale().timeToCoordinate({data[239]["time"]})')
    x=rect['x']+rect['width']/2;y=rect['y']+rect['height']/2
    page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+dx,y,steps=8);page.mouse.up();pause()
    anchors=trend['geometry']['anchors'];assert anchors[0]['time']==data[240]['time'] and anchors[1]['time']==data[245]['time']+60
    assert [a['price'] for a in anchors]==[a['price'] for a in before]
    record('one_logical_bar_body_drag_across_three_missing_bars',first_utc_delta=anchors[0]['time']-before[0]['time'],second_utc_delta=anchors[1]['time']-before[1]['time'])
    read('series.priceScale().setVisibleRange({from:155,to:165})');pause()
    before=copy.deepcopy(anchors);rect=page.locator('[data-drawing-handles="C3 trend"] [data-anchor="0"]').bounding_box();assert rect
    x=rect['x']+rect['width']/2;y=rect['y']+rect['height']/2
    dy=read('series.priceToCoordinate(160.5)-series.priceToCoordinate(160.25)')
    page.mouse.move(x,y);page.mouse.down();page.mouse.move(x,y+dy,steps=6);page.mouse.up();pause()
    assert float(trend['geometry']['anchors'][0]['price'])==160.5 and trend['geometry']['anchors'][1]==before[1]
    record('single_anchor_quarter_tick_drag')
    reverse=items[1];select('C3 reverse')
    page.get_by_label('Nokta 1 fiyatı',exact=True).fill('169.25');save()
    assert reverse['geometry']['anchors'][0]['time']>reverse['geometry']['anchors'][1]['time']
    record('reverse_fibonacci_order_preserved_in_editor')
    # Spike high is far enough from other OHLC prices to distinguish magnet from tick rounding.
    control=page.get_by_label('Otomatik fiyat ölçeği',exact=True)
    if control.get_attribute('aria-pressed')!='true':control.click();pause()
    px=read(f'chart.timeScale().timeToCoordinate({data[250]["time"]})');py=read('series.priceToCoordinate(180)')
    created=[]
    for magnet in [False,True]:
        button=page.get_by_role('button',name='Mıknatıs',exact=True)
        if (button.get_attribute('aria-pressed')=='true')!=magnet:button.click()
        page.locator('.drawing-tools').get_by_label('Yatay çizgi',exact=True).click();page.wait_for_timeout(550)
        b=page.locator('.chart-host').bounding_box();count=len(writes)
        page.mouse.click(b['x']+px,b['y']+py+7);pause()
        assert len(writes)==count+1,{'error':'Magnet test did not create its isolated drawing','px':px,'py':py,'host':b,'auto':read('series.priceScale().options().autoScale'),'hit':page.evaluate('p=>document.elementFromPoint(p.x,p.y)?.outerHTML.slice(0,200)',{'x':b['x']+px,'y':b['y']+py+7})}
        created.append(items[-1]['geometry']['anchors'][0]['price'])
    assert float(created[1])==180 and created[0]!=created[1],created
    record('magnet_ohlc_snap_distinguished_from_tick_rounding',off=created[0],on=created[1])
    page.get_by_label('Sözleşme seç').select_option('MICROUSDT');pause()
    micro=[{**c,'open':1e-7+i*1e-9,'close':1e-7+i*1e-9,'high':1.1e-7+i*1e-9,'low':.9e-7+i*1e-9} for i,c in enumerate(data)]
    snapshot('MICROUSDT',micro);select('C3 micro');page.get_by_label('Çizim fiyatı',exact=True).fill('0,00000034');save()
    d=next(d for d in items if d['drawing_id']=='C3 micro');assert d['geometry']['anchors'][0]['price']=='0.00000034'
    pos=read('({y:series.priceToCoordinate(.00000034),height:chart.paneSize(0).height})');assert 0<=pos['y']<=pos['height']
    record('micro_price_editor_exact_and_visible',price=d['geometry']['anchors'][0]['price'])
    result['user_workspace_writes']=0;result['physical_touch']='NOT_VERIFIED';session.detach()


if __name__=='__main__':raise SystemExit(main(checks,'chart-precision-browser-20261109.json'))
