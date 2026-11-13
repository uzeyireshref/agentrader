"""C1: native hit-testing and keyboard selection over overlapping drawings."""
import copy
import json
from measure_chart_interactions import main


def checks(page,sockets,rows,result):
    result['task']='C1';result['checks']=[]
    def pause():page.wait_for_timeout(150)
    def record(name,**data):result['checks'].append(dict(name=name,passed=True,**data))
    items=[]
    for kind in ['horizontal','zone','trend','fibonacci']:
        anchors=[{'time':rows[220]['time'],'price':str(rows[220]['close'])}]
        if kind!='horizontal':anchors.append({'time':rows[250]['time'],'price':str(rows[250]['close'])})
        items.append({'drawing_id':'c1-'+kind,'workspace_id':'main','revision':1,'deleted':False,'updated_at':0,'geometry':{'kind':kind,'symbol':'BTCUSDT','price_source':'LAST_PRICE','label':'C1 '+kind,'anchors':anchors}})
    writes=[]
    page.route('**/api/workspaces/main/drawings?**',lambda r:r.fulfill(json={'drawings':items}))
    def patch(route):
        key=route.request.url.rsplit('/',1)[1]
        assert route.request.method=='PATCH'
        body=route.request.post_data_json
        item=next(d for d in items if d['drawing_id']==key)
        assert body['expected_revision']==item['revision']
        item['geometry']=body['geometry'];item['revision']+=1
        writes.append({'id':key,'body':body})
        route.fulfill(json=item)
    page.route('**/api/drawings/*',patch)
    page.get_by_role('button',name='Sunucudan yenile',exact=True).click();pause()
    assert page.locator('[data-drawing]').count()==4
    for kind in ['horizontal','zone','trend','fibonacci']:
        button=page.locator('.drawing-list button').filter(has_text='C1 '+kind)
        button.focus();page.keyboard.press('Enter');pause()
        group=page.locator('[data-drawing="c1-'+kind+'"]')
        assert group.get_attribute('aria-pressed')=='true'
        assert page.locator('[data-drawing][aria-pressed="true"]').count()==1
        assert page.locator('[data-drawing-handles]').count()==(0 if kind=='horizontal' else 1)
        if kind!='horizontal':
            handles=page.locator('[data-drawing-handles="c1-'+kind+'"]')
            assert handles.locator('circle').count()==2
            assert page.locator('.drawings-overlay').evaluate('(s)=>s.lastElementChild.getAttribute("data-drawing-handles")')=='c1-'+kind
        record('keyboard_list_selection',kind=kind,unexpected_writes=len(writes))
    assert not writes
    # SVG keyboard alternative must also select the requested covered drawing.
    for key in ['Enter','Space']:
        group=page.locator('[data-drawing="c1-trend"]');group.focus();page.keyboard.press(key);pause()
        assert group.get_attribute('aria-pressed')=='true'
        assert page.locator('[data-drawing-handles="c1-trend"]').count()==1
        record('svg_keyboard_selection',key=key)
    for kind in ['trend','fibonacci','zone']:
        page.locator('.drawing-list button').filter(has_text='C1 '+kind).click();pause()
        before=copy.deepcopy(items);count=len(writes)
        second=page.locator('[data-drawing-handles="c1-'+kind+'"] [data-anchor="1"]').bounding_box();assert second
        second_hit=page.evaluate('p=>{const e=document.elementFromPoint(p.x,p.y);return {tag:e?.tagName,anchor:e?.getAttribute("data-anchor"),owner:e?.closest("[data-drawing-handles]")?.getAttribute("data-drawing-handles")};}',{'x':second['x']+second['width']/2,'y':second['y']+second['height']/2})
        assert second_hit=={'tag':'circle','anchor':'1','owner':'c1-'+kind},second_hit
        circle=page.locator('[data-drawing-handles="c1-'+kind+'"] [data-anchor="0"]')
        rect=circle.bounding_box();assert rect
        x=rect['x']+rect['width']/2;y=rect['y']+rect['height']/2
        hit=page.evaluate('p=>{const e=document.elementFromPoint(p.x,p.y);return {tag:e?.tagName,anchor:e?.getAttribute("data-anchor"),owner:e?.closest("[data-drawing-handles]")?.getAttribute("data-drawing-handles")};}',{'x':x,'y':y})
        assert hit['tag']=='circle' and hit['anchor']=='0' and hit['owner']=='c1-'+kind,hit
        page.mouse.move(x,y);page.mouse.down();page.mouse.move(x+24,y-10,steps=8);page.mouse.up();pause()
        assert len(writes)==count+1 and writes[-1]['id']=='c1-'+kind
        for old,new in zip(before,items):
            if new['drawing_id']=='c1-'+kind:
                assert new['revision']==old['revision']+1
                assert new['geometry']['anchors'][0]!=old['geometry']['anchors'][0]
                assert new['geometry']['anchors'][1]==old['geometry']['anchors'][1]
            else:assert old==new,'Overlapping drawing was changed'
        record('overlap_handle_hit_and_single_anchor_drag',kind=kind,hit=hit,second_hit=second_hit,revision_delta=1)
    # Horizontal body remains reachable away from the covered segment.
    line=page.locator('[data-drawing="c1-horizontal"] .hit-line')
    p=line.evaluate('(e)=>{const r=e.getBoundingClientRect();return {x:r.left+20,y:r.top+r.height/2}}')
    page.mouse.click(p['x'],p['y']);pause()
    assert page.locator('[data-drawing="c1-horizontal"]').get_attribute('aria-pressed')=='true'
    assert page.locator('[data-drawing-handles]').count()==0
    assert len(writes)==3
    record('horizontal_body_selection_without_revision')
    # Repeated selection must not duplicate handles or change paint/body order.
    body_order=page.locator('[data-drawing]').evaluate_all('(els)=>els.map(e=>e.getAttribute("data-drawing"))')
    for _ in range(4):
        for kind in ['trend','fibonacci']:
            page.locator('.drawing-list button').filter(has_text='C1 '+kind).click();pause()
    assert page.locator('[data-drawing-handles]').count()==1
    assert page.locator('[data-drawing]').evaluate_all('(els)=>els.map(e=>e.getAttribute("data-drawing"))')==body_order
    assert len(writes)==3
    record('selection_cycles_preserve_body_order_and_single_handle_layer')
    result['drawing_store']='Isolated mocked drawing API, no writes to user workspace'


if __name__=='__main__':raise SystemExit(main(checks,'chart-selection-browser-20261109.json'))
