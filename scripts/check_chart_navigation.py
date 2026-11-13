"""B2 native wheel/zoom, view preservation and creation/gesture integration."""
import json
import time
from measure_chart_interactions import main, INSPECT


def checks(page,sockets,rows,result):
    result['task']='B2';result['checks']=[]
    def record(name,**data):result['checks'].append(dict(name=name,passed=True,**data))
    def read(expr):
        return page.evaluate(INSPECT) if expr is None else page.evaluate(INSPECT[:INSPECT.index('return view?')]+f'return ({expr});'+'}')
    def set_range(start,end):
        read(f'chart.timeScale().setVisibleLogicalRange({{from:{start},to:{end}}})');page.wait_for_timeout(80)
    def box():return page.locator('.chart-host').bounding_box()
    def reset():page.get_by_label('Görünümü sıfırla',exact=True).click();page.wait_for_timeout(250)
    def fresh(data):
        page.reload();page.wait_for_timeout(300)
        sockets[-1].send(json.dumps({'type':'snapshot','symbol':'BTCUSDT','interval':'15m','generation':1,'sequence':1,'status':'LIVE','received_at':int(time.time()*1000),'candles':data}))
        page.wait_for_timeout(150)
    def wheel(dx,dy,x=None):
        b=box();size=read('chart.paneSize(0)');page.mouse.move(b['x']+(x if x is not None else size['width']*.5),b['y']+size['height']*.5)
        page.mouse.wheel(dx,dy);page.wait_for_timeout(100)
    for fraction in [.2,.5,.8]:
        for delta in [-240,240]:
            reset();before=read('chart.timeScale().getVisibleLogicalRange()')
            index=round(before['from']+(before['to']-before['from'])*fraction)
            x=read(f'chart.timeScale().logicalToCoordinate({index})')
            wheel(0,delta,x)
            after=read(f'chart.timeScale().logicalToCoordinate({index})')
            error=abs(after-x);assert error<=1,('zoom anchor',fraction,delta,error)
            record('zoom_anchor',fraction=fraction,delta=delta,error_css_px=error)
    for dx,dy in [(200,70),(70,-240)]:
        reset();wheel(dx if abs(dx)>abs(dy) else 0,dy if abs(dy)>=abs(dx) else 0)
        expected=read('chart.timeScale().getVisibleLogicalRange()')
        reset();wheel(dx,dy);actual=read('chart.timeScale().getVisibleLogicalRange()')
        error=max(abs(actual[k]-expected[k]) for k in ['from','to']);assert error<1e-6,('diagonal wheel doubled',error)
        record('dominant_axis_once',dx=dx,dy=dy,logical_error=error)
    # A real trackpad gesture is a sequence, not a single diagonal event.
    for name,events,axis in [('horizontal_noise',[(80,10),(8,35),(0,12),(40,-5)],'horizontal'),('vertical_noise',[(10,-80),(35,-8),(12,0),(-5,-40)],'vertical')]:
        reset();b=box();size=read('chart.paneSize(0)');page.mouse.move(b['x']+size['width']/2,b['y']+size['height']/2)
        before=read('chart.timeScale().getVisibleLogicalRange()')
        for dx,dy in events:page.mouse.wheel(dx,dy)
        page.wait_for_timeout(100);after=read('chart.timeScale().getVisibleLogicalRange()')
        if axis=='horizontal':assert abs((after['to']-after['from'])-(before['to']-before['from']))<1e-6,'Horizontal gesture changed zoom'
        else:
            assert after['to']-after['from']<before['to']-before['from'],'Vertical gesture did not zoom'
        record('multi_event_'+name)
    for direction,target in [(-1,50),(1,2)]:
        reset();b=box();size=read('chart.paneSize(0)');page.mouse.move(b['x']+size['width']/2,b['y']+size['height']/2)
        for _ in range(45):page.mouse.wheel(0,direction*800)
        page.wait_for_timeout(150)
        spacing=read('chart.timeScale().options().barSpacing');assert abs(spacing-target)<1e-6,spacing
        record('zoom_limit',bar_spacing=spacing)
    # Keep an actual UTC/price anchor in the same CSS position through history prepend.
    fresh(rows);reset();set_range(40,156)
    reference_time=rows[100]['time'];reference_price=rows[100]['close']
    before=read(f'({{x:chart.timeScale().timeToCoordinate({reference_time}),y:series.priceToCoordinate({reference_price})}})')
    older=[{**rows[0],'time':rows[0]['time']-(50-i)*900,'close_time':rows[0]['close_time']-(50-i)*900000,'closed':True} for i in range(50)]
    def history(route):route.fulfill(json={'candles':older,'has_more':False})
    page.route('**/api/candles?**',history)
    page.locator('.chart-bottom button.text-button').click();page.wait_for_timeout(180)
    after=read(f'({{x:chart.timeScale().timeToCoordinate({reference_time}),y:series.priceToCoordinate({reference_price})}})')
    assert read('view.candles.length')==350
    error=max(abs(before[k]-after[k]) for k in ['x','y']);assert error<=1,('history view jumped',before,after)
    record('history_prepend_view_preserved',error_css_px=error)
    # Test-only drawing store handles POST without writing user state.
    writes=[]
    def drawings(route):
        if route.request.method!='POST':return route.fallback()
        body=route.request.post_data_json;writes.append(body)
        route.fulfill(json={'drawing_id':'navigation-test','workspace_id':'main','revision':1,'deleted':False,'updated_at':0,'geometry':body['geometry']})
    page.route('**/api/workspaces/main/drawings',drawings)
    reset();page.get_by_label('Yatay çizgi',exact=True).click();b=box();size=read('chart.paneSize(0)')
    x=b['x']+size['width']*.45;y=b['y']+size['height']*.5
    page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+130,y,steps=10);page.mouse.up();page.wait_for_timeout(150)
    assert len(writes)==0,'Pan created a drawing';record('creation_pan_does_not_save')
    page.keyboard.press('Escape');page.get_by_label('Trend çizgisi',exact=True).click()
    index=round(read('chart.timeScale().getVisibleLogicalRange().from')+35)
    local_x=read(f'chart.timeScale().logicalToCoordinate({index})')
    expected_time=read(f'chart.timeScale().coordinateToTime({local_x})')
    expected_price=read(f'series.coordinateToPrice({size["height"]*.5})')
    page.mouse.click(b['x']+local_x,y);page.wait_for_timeout(80)
    wheel(0,-240);page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+80,y,steps=10);page.mouse.up();page.wait_for_timeout(100)
    assert len(writes)==0,'Navigation completed a draft'
    page.mouse.click(x+200,y-40);page.wait_for_timeout(150)
    assert len(writes)==1,'Two-point drawing did not save exactly once'
    anchor=writes[0]['geometry']['anchors'][0]
    assert anchor['time']==expected_time and abs(float(anchor['price'])-expected_price)<=.051,anchor
    record('draft_anchor_preserved_through_zoom_pan',time=anchor['time'],price=anchor['price'])
    page.keyboard.press('Escape')
    # The SVG drawing overlay must not swallow wheel or bypass an active drag lock.
    line=page.locator('[data-drawing="navigation-test"] .hit-line')
    rect=line.bounding_box();assert rect
    mx=rect['x']+rect['width']/2;my=rect['y']+rect['height']/2
    hit=page.evaluate('p=>document.elementFromPoint(p.x,p.y)?.closest("[data-drawing]")?.getAttribute("data-drawing")',{'x':mx,'y':my})
    assert hit=='navigation-test',('drawing wheel target',hit)
    spacing=read('chart.timeScale().options().barSpacing')
    page.mouse.move(mx,my);page.mouse.wheel(0,-240);page.wait_for_timeout(100)
    assert read('chart.timeScale().options().barSpacing')>spacing,'SVG swallowed wheel'
    record('wheel_over_drawing_reaches_native_engine')
    # A fresh hit point is needed after zoom reprojects the line.
    rect=line.bounding_box();mx=rect['x']+rect['width']/2;my=rect['y']+rect['height']/2
    page.mouse.move(mx,my);page.mouse.down();page.wait_for_timeout(50)
    locked=read('chart.timeScale().getVisibleLogicalRange()')
    page.mouse.wheel(100,-240);page.wait_for_timeout(100)
    assert read('chart.timeScale().getVisibleLogicalRange()')==locked,'Wheel bypassed drawing drag lock'
    page.keyboard.press('Escape');page.mouse.up();page.wait_for_timeout(80)
    assert len(writes)==1,'Cancelled drag saved'
    record('diagonal_wheel_honors_drawing_drag_lock')
    # Wheel events outside the chart must retain normal page scrolling.
    page.evaluate('window.scrollTo(0,0)');page.mouse.move(20,400);page.mouse.wheel(0,300);page.wait_for_timeout(100)
    assert page.evaluate('window.scrollY')>0,'Chart wheel handler trapped outside page scroll'
    record('outside_chart_page_scroll')
    page.evaluate('window.scrollTo(0,0)')
    # Bounded zoom and valid native coordinates with both short and large datasets.
    page.unroute('**/api/candles?**',history)
    for count in [20,4000]:
        data=[{**rows[0],'time':rows[0]['time']+i*900,'close_time':rows[0]['close_time']+i*900000,'closed':True} for i in range(count)]
        fresh(data);reset();wheel(0,-500)
        info=read('({count:view.candles.length,spacing:chart.timeScale().options().barSpacing,x:chart.timeScale().timeToCoordinate(view.candles.at(-1).time)})')
        assert info['count']==count and 2<=info['spacing']<=50 and isinstance(info['x'],(int,float)),info
        record('bounded_dataset',requested_candles=count,actual_candles=info['count'],bar_spacing=info['spacing'])


if __name__=='__main__':raise SystemExit(main(checks,'chart-navigation-browser-20261109.json'))
