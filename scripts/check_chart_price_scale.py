"""B3 visible native price-scale state, keyboard reset and price extremes."""
import json
import time
from measure_chart_interactions import main, INSPECT


def checks(page,sockets,rows,result):
    result['task']='B3';result['checks']=[]
    def record(name,**data):result['checks'].append(dict(name=name,passed=True,**data))
    def read(expr):return page.evaluate(INSPECT[:INSPECT.index('return view?')]+f'return ({expr});'+'}')
    control=page.get_by_label('Otomatik fiyat ölçeği',exact=True)
    def state(expected):
        page.wait_for_timeout(100)
        assert read('series.priceScale().options().autoScale')==expected
        assert control.get_attribute('aria-pressed')==str(expected).lower()
        assert ('Otomatik' if expected else 'Manuel') in control.inner_text()
    state(True);record('initial_label_matches_native_auto')
    before=read('({range:chart.timeScale().getVisibleLogicalRange(),data:series.data()})')
    control.focus();page.keyboard.press('Enter');state(False)
    page.keyboard.press('Space');state(True)
    after=read('({range:chart.timeScale().getVisibleLogicalRange(),data:series.data()})')
    assert before==after
    record('keyboard_toggle_preserves_time_range_and_ohlc')
    box=page.locator('.chart-host').bounding_box();height=read('chart.paneSize(0).height')
    x=box['x']+box['width']-30;y=box['y']+height*.5
    page.mouse.move(x,y);page.mouse.down();page.mouse.move(x,y+80,steps=10);page.mouse.up();state(False)
    record('axis_drag_updates_visible_manual_state')
    before=read('chart.timeScale().getVisibleLogicalRange()')
    control.click();state(True)
    assert before==read('chart.timeScale().getVisibleLogicalRange()')
    record('button_returns_to_auto_without_time_zoom_change')
    control.click();state(False)
    page.mouse.dblclick(x,y);state(True)
    record('axis_double_click_updates_visible_auto_state')
    control.click();state(False)
    page.get_by_role('button',name='RSI 14',exact=True).click();state(False)
    page.get_by_role('button',name='EMA 20/50',exact=True).click();state(False)
    page.get_by_role('button',name='RSI 14',exact=True).click();state(False)
    record('indicator_pane_changes_preserve_manual_state')
    control.click();state(True)
    # Add isolated markets with correct tick metadata; user stores are never used.
    markets=[{'symbol':s,'base_asset':s[:-4],'quote_asset':'USDT','tick_size':tick,'contract_type':'PERPETUAL'} for s,tick in [('BTCUSDT','0.1'),('MICROUSDT','0.00000001'),('BIGUSDT','0.1')]]
    page.route('**/api/markets',lambda route:route.fulfill(json={'markets':markets}))
    page.reload();page.wait_for_timeout(350)
    for symbol,base,step,tick in [('MICROUSDT',1e-7,1e-9,1e-8),('BIGUSDT',1e6,10000,.1)]:
        page.get_by_label('Sözleşme seç').select_option(symbol);page.wait_for_timeout(150)
        data=[{**c,'open':base+i*step,'close':base+i*step,'high':base+i*step+step*2,'low':base+i*step-step*2,'quote_volume':1} for i,c in enumerate(rows)]
        sockets[-1].send(json.dumps({'type':'snapshot','symbol':symbol,'interval':'15m','generation':1,'sequence':1,'status':'LIVE','received_at':int(time.time()*1000),'candles':data}))
        page.wait_for_timeout(150);state(True)
        native=read('series.data()');assert len(native)==len(data)
        probe=read('({y:series.priceToCoordinate(view.candles.at(-1).close),height:chart.paneSize(0).height,formatted:series.priceFormatter().format(view.candles.at(-1).close)})')
        assert 0<=probe['y']<=probe['height'],probe
        if symbol=='MICROUSDT':assert any(ch in probe['formatted'] for ch in '123456789'),probe
        record('auto_scale_price_extreme',symbol=symbol,**probe)
        control.click();state(False)
        page.get_by_role('button',name='1 sa',exact=True).click();page.wait_for_timeout(150)
        state(True);record('timeframe_change_resets_price_scale',symbol=symbol)
        page.get_by_role('button',name='15 dk',exact=True).click();page.wait_for_timeout(120)
    # Last market had a fresh context; no stale price-scale label remains.
    result['scale_control_scope']='main candlestick price scale; RSI/volume controls unchanged'


if __name__=='__main__':raise SystemExit(main(checks,'chart-price-scale-browser-20261109.json'))
