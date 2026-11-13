"""C2 creation and cancellation: native App/mouse, synthetic interruption signals."""
import copy
from measure_chart_interactions import main, INSPECT


def checks(page,sockets,rows,result):
    result['task']='C2';result['checks']=[]
    def record(name,**data):result['checks'].append(dict(name=name,passed=True,**data))
    def pause():page.wait_for_timeout(100)
    def read(expr):return page.evaluate(INSPECT[:INSPECT.index('return view?')]+f'return ({expr});'+'}')
    items,writes=[],[]
    page.route('**/api/workspaces/main/drawings?**',lambda r:r.fulfill(json={'drawings':items}))
    def create(route):
        if route.request.method!='POST':return route.fallback()
        body=route.request.post_data_json
        item={'drawing_id':'made-'+str(len(items)+1),'workspace_id':'main','revision':1,'deleted':False,'updated_at':0,'geometry':body['geometry']}
        items.append(item);writes.append({'method':'POST','body':body});route.fulfill(json=item)
    def patch(route):
        writes.append({'method':route.request.method,'body':route.request.post_data_json});route.fulfill(status=500,json={'error':'Unexpected C2 mutation'})
    page.route('**/api/workspaces/main/drawings',create);page.route('**/api/drawings/*',patch)
    def point(fx=.35,fy=.4):
        b=page.locator('.chart-host').bounding_box();size=read('chart.paneSize(0)')
        return b['x']+size['width']*fx,b['y']+size['height']*fy
    labels={'horizontal':'Yatay çizgi','zone':'Fiyat bölgesi','trend':'Trend çizgisi','fibonacci':'Fibonacci'}
    for kind,label in labels.items():
        count=len(writes);page.locator('.drawing-tools').get_by_label(label,exact=True).click();page.wait_for_timeout(550);page.mouse.click(*point());pause()
        if kind!='horizontal':
            assert len(writes)==count
            assert page.get_by_text('İkinci nokta için farklı bir mum ve fiyat seç.',exact=True).count()==1,{'hints':page.locator('.tool-hint').all_text_contents(),'active':page.locator('.drawing-tools button.active').get_attribute('aria-label'),'chart':read('({range:chart.timeScale().getVisibleLogicalRange(),count:view.candles.length})')}
            page.wait_for_timeout(550);page.mouse.click(*point(.65,.65));pause()
        assert len(writes)==count+1 and items[-1]['geometry']['kind']==kind
        assert len(items[-1]['geometry']['anchors'])==(1 if kind=='horizontal' else 2)
        assert page.locator('.tool-hint').count()==0
        record('create_once',kind=kind,revision=items[-1]['revision'])
    baseline=copy.deepcopy(items);count=len(writes)
    for reason in ['Escape','blur','pointercancel','secondary_pointer','contextmenu','hidden','tool_change','timeframe']:
        page.locator('.drawing-tools').get_by_label('Trend çizgisi',exact=True).click();page.wait_for_timeout(550);page.mouse.click(*point());pause()
        assert page.locator('.tool-hint').count()==1
        if reason=='Escape':page.keyboard.press('Escape')
        elif reason=='blur':page.evaluate("window.dispatchEvent(new Event('blur'))")
        elif reason=='pointercancel':page.locator('.chart-stage').dispatch_event('pointercancel',{'pointerId':1,'isPrimary':True,'bubbles':True})
        elif reason=='secondary_pointer':page.locator('.chart-stage').dispatch_event('pointerdown',{'pointerId':2,'isPrimary':False,'pointerType':'touch','bubbles':True})
        elif reason=='contextmenu':page.locator('.chart-stage').dispatch_event('contextmenu')
        elif reason=='hidden':page.evaluate("()=>{Object.defineProperty(document,'hidden',{configurable:true,value:true});document.dispatchEvent(new Event('visibilitychange'));delete document.hidden;}")
        elif reason=='tool_change':page.locator('.drawing-tools').get_by_label('İmleç',exact=True).click()
        else:page.get_by_role('button',name='1 sa',exact=True).click()
        pause();assert page.locator('.tool-hint').count()==0,reason
        assert len(writes)==count and items==baseline,reason+' saved cancelled draft'
        if reason=='timeframe':
            page.get_by_role('button',name='15 dk',exact=True).click();pause()
            import json,time
            sockets[-1].send(json.dumps({'type':'snapshot','symbol':'BTCUSDT','interval':'15m','generation':1,'sequence':1,'status':'LIVE','received_at':int(time.time()*1000),'candles':rows}));pause()
        record('creation_cancel',reason=reason,signal='real keyboard/control' if reason in ['Escape','tool_change','timeframe'] else 'synthetic interruption')
    # Same point is invalid; it must keep the draft, never issue a write.
    page.locator('.drawing-tools').get_by_label('Trend çizgisi',exact=True).click();page.wait_for_timeout(550);p=point();page.mouse.click(*p);page.wait_for_timeout(550);page.mouse.click(*p);pause()
    assert len(writes)==count and page.get_by_text('İki nokta farklı zaman ve fiyatta olmalı.',exact=True).count()==1
    page.keyboard.press('Escape');record('degenerate_second_point_never_saves')
    # Existing drawing cancellation must restore exact engine options and never PATCH.
    trend=next(d for d in items if d['geometry']['kind']=='trend')
    for reason in ['Escape','blur','pointercancel','capture_loss','outside_release_after_cancel']:
        page.locator('.drawing-list button').filter(has_text='Trend çizgisi').click();pause()
        handles=page.locator('[data-drawing-handles="'+trend['drawing_id']+'"]')
        rect=handles.locator('[data-anchor="0"]').bounding_box();assert rect
        x=rect['x']+rect['width']/2;y=rect['y']+rect['height']/2
        options=read('({scroll:chart.options().handleScroll,scale:chart.options().handleScale})')
        page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+24,y-12,steps=5);pause()
        locked=read('({scroll:chart.options().handleScroll,scale:chart.options().handleScale})');assert locked!=options
        if reason in ['Escape','outside_release_after_cancel']:page.keyboard.press('Escape')
        elif reason=='blur':page.evaluate("window.dispatchEvent(new Event('blur'))")
        elif reason=='pointercancel':handles.dispatch_event('pointercancel',{'pointerId':1,'isPrimary':True,'bubbles':True})
        else:
            handles.evaluate('(e)=>{if(!e.hasPointerCapture(1))throw Error("No native mouse capture");e.releasePointerCapture(1);}');page.mouse.move(x+25,y-12)
        pause()
        if reason=='outside_release_after_cancel':page.mouse.move(5,5)
        page.mouse.up();pause()
        assert len(writes)==count and items==baseline,reason+' mutated drawing'
        assert read('({scroll:chart.options().handleScroll,scale:chart.options().handleScale})')==options,reason+' left chart locked'
        record('existing_drag_cancel',reason=reason,signal='native capture/keyboard/mouse' if reason in ['capture_loss','Escape','outside_release_after_cancel'] else 'synthetic interruption')
    page.locator('.drawing-list button').filter(has_text='Trend çizgisi').click();pause()
    handles=page.locator('[data-drawing-handles="'+trend['drawing_id']+'"]')
    rect=handles.locator('[data-anchor="0"]').bounding_box();assert rect
    x=rect['x']+rect['width']/2;y=rect['y']+rect['height']/2
    page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+24,y-12,steps=5);pause()
    locked=read('({scroll:chart.options().handleScroll,scale:chart.options().handleScale})')
    for event in ['pointerdown','pointermove','pointerup']:
        handles.dispatch_event(event,{'pointerId':2,'isPrimary':False,'pointerType':'touch','clientX':x+80,'clientY':y-50,'bubbles':True})
    pause();assert len(writes)==count
    assert read('({scroll:chart.options().handleScroll,scale:chart.options().handleScale})')==locked
    page.keyboard.press('Escape');page.mouse.up();pause()
    assert len(writes)==count and items==baseline
    record('second_pointer_cannot_complete_owner_drag',signal='synthetic non-owner PointerEvent, real owner mouse')
    result['physical_touch']='NOT_VERIFIED';result['user_workspace_writes']=0


if __name__=='__main__':raise SystemExit(main(checks,'chart-creation-browser-20261109.json'))
