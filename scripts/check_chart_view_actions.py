"""B4 separate latest-candle navigation and full view reset in real App."""
import json
import time
from measure_chart_interactions import main, INSPECT

INSPECT=INSPECT.replace('view,candles,volume,chart,series;', 'view,candles,volume,chart,series,stored=[];').replace('const ref=v?.current;', 'if(Array.isArray(v)&&v.length&&v.every(d=>d?.drawing_id&&d?.geometry))stored=v;const ref=v?.current;')


def checks(page,sockets,rows,result):
    result['task']='B4';result['checks']=[]
    def read(expr):return page.evaluate(INSPECT[:INSPECT.index('return view?')]+f'return ({expr});'+'}')
    def record(name,**data):result['checks'].append(dict(name=name,passed=True,**data))
    latest=page.get_by_label('Güncel mumlara dön',exact=True)
    reset=page.get_by_label('Görünümü sıfırla',exact=True)
    control=page.get_by_label('Otomatik fiyat ölçeği',exact=True)
    def pause():page.wait_for_timeout(120)
    def camera():return read('({range:chart.timeScale().getVisibleLogicalRange(),spacing:chart.timeScale().options().barSpacing,auto:series.priceScale().options().autoScale,y:series.priceToCoordinate(135),count:view.candles.length})')
    for width in [30,116,300]:
        for auto in [True,False]:
            read(f'chart.timeScale().setVisibleLogicalRange({{from:{160-width},to:160}})');pause()
            if (control.get_attribute('aria-pressed')=='true')!=auto:control.click();pause()
            before=camera();latest.click();pause();after=camera()
            assert abs(before['spacing']-after['spacing'])<1e-8
            assert abs((before['range']['to']-before['range']['from'])-(after['range']['to']-after['range']['from']))<1e-8
            assert after['auto']==auto and abs(after['range']['to']-(after['count']+6))<1e-6,after
            if not auto:assert abs(before['y']-after['y'])<=1e-6
            record('latest_preserves_zoom_and_price_mode',requested_width=width,automatic=auto,spacing=after['spacing'])
    # History view stays put; explicit return then resumes new-bar follow.
    read('chart.timeScale().setVisibleLogicalRange({from:40,to:156})');pause();before=camera()
    def append(sequence):
        current=read('view.candles.at(-1)')
        new={**current,'time':current['time']+900,'close_time':current['close_time']+900000,'volume':1,'closed':False}
        sockets[-1].send(json.dumps({'type':'update','symbol':'BTCUSDT','interval':'15m','generation':1,'sequence':sequence,'status':'LIVE','received_at':int(time.time()*1000),'tail':[{**current,'closed':True},new]}));pause()
    append(3);after=camera();assert before['range']==after['range']
    record('new_bar_does_not_pull_history_view')
    latest.click();pause();before=camera();append(4);after=camera()
    assert abs(after['range']['from']-before['range']['from']-1)<1e-6 and abs(after['range']['to']-before['range']['to']-1)<1e-6
    record('latest_action_resumes_new_bar_follow')
    drawing={'drawing_id':'b4-test','workspace_id':'main','revision':1,'deleted':False,'updated_at':0,'geometry':{'kind':'horizontal','symbol':'BTCUSDT','price_source':'LAST_PRICE','anchors':[{'time':rows[250]['time'],'price':'130'}],'label':'B4 preserved drawing'}}
    page.route('**/api/workspaces/main/drawings?**',lambda route:route.fulfill(json={'drawings':[drawing]}))
    page.get_by_role('button',name='Sunucudan yenile',exact=True).click();pause()
    assert len(read('stored'))==1
    page.get_by_role('button',name='EMA 20/50',exact=True).click()
    page.get_by_role('button',name='RSI 14',exact=True).click();pause()
    # Deliberately customized pane proportions must survive reset.
    read('chart.panes()[0].setStretchFactor(3)');read('chart.panes()[1].setStretchFactor(2)');read('chart.panes()[2].setStretchFactor(2)');pause()
    if control.get_attribute('aria-pressed')=='true':control.click();pause()
    read('chart.timeScale().setVisibleLogicalRange({from:130,to:170})');pause()
    before=read('({candles:view.candles,stored,heights:chart.panes().map(p=>p.getHeight())})')
    reset.focus();page.keyboard.press('Enter');pause();after=camera()
    assert after['auto'] and control.get_attribute('aria-pressed')=='true'
    assert abs(after['range']['from']-(after['count']-110))<1e-6 and abs(after['range']['to']-(after['count']+6))<1e-6
    final=read('({candles:view.candles,stored,heights:chart.panes().map(p=>p.getHeight())})')
    assert before==final,'Reset changed data/drawing/pane heights'
    assert page.get_by_role('button',name='EMA 20/50',exact=True).get_attribute('aria-pressed')=='true'
    assert page.get_by_role('button',name='RSI 14',exact=True).get_attribute('aria-pressed')=='true'
    record('keyboard_reset_defaults_without_data_indicator_drawing_or_pane_changes',pane_heights=final['heights'])
    # Short history and no-data controls use fresh isolated contexts.
    page.reload();pause();pause()
    assert latest.is_disabled() and reset.is_disabled();record('empty_chart_actions_disabled')
    short=[{**c,'closed':True} for c in rows[:20]]
    sockets[-1].send(json.dumps({'type':'snapshot','symbol':'BTCUSDT','interval':'15m','generation':1,'sequence':1,'status':'LIVE','received_at':int(time.time()*1000),'candles':short}));pause()
    reset.click();pause();after=camera()
    assert after['count']==20 and after['auto'] and abs(after['range']['from'])<1e-6 and abs(after['range']['to']-26)<1e-6
    record('short_history_reset',candles=20,range=after['range'])
    latest.focus();page.keyboard.press('Space');pause();after=camera()
    assert abs(after['range']['to']-26)<1e-6
    record('latest_action_keyboard_access')
    page.set_viewport_size({'width':390,'height':844});pause()
    read('chart.timeScale().applyOptions({barSpacing:50})');pause()
    latest.focus();page.keyboard.press('Enter');pause()
    narrow=read('({x:chart.timeScale().timeToCoordinate(view.candles.at(-1).time),width:chart.paneSize(0).width,spacing:chart.timeScale().options().barSpacing})')
    assert 0<=narrow['x']<=narrow['width'],'Latest candle outside narrow zoomed view: '+str(narrow)
    assert abs(narrow['spacing']-50)<1e-6
    record('narrow_zoom_latest_remains_visible',**narrow)


if __name__=='__main__':raise SystemExit(main(checks,'chart-view-actions-browser-20261109.json'))
