"""Current accessible UI gestures plus explicit bot-readability boundaries."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

from copy import deepcopy
from decimal import Decimal
import time


def run_controls(page,client,read,feed,frame,rows,ui_read=None):
    checks=[]
    def record(name,**extra):checks.append(dict(name=name,state='PASS',**extra))
    def listing():return client.get('/api/workspaces/main/drawings?symbol=BTCUSDT&format_version=9').json()['drawings']
    def count(n):
        until=time.time()+4
        while time.time()<until:
            if len(listing())==n:return
            page.wait_for_timeout(50)
        raise AssertionError(('drawing count',n,len(listing())))
    favorite=page.get_by_label('BTCUSDT favorisi',exact=True)
    favorite.click();assert favorite.get_attribute('aria-pressed')=='true'
    workspace=client.get('/api/workspaces/main').json()
    assert 'favorites' not in workspace.get('preferences',{})
    if ui_read:assert 'BTCUSDT' in ui_read(lambda v:'BTCUSDT' in v['favorites'])['snapshot']['favorites']
    record('favorite_ui_and_local_only_read_boundary',bot_api='CLIENT_REPORTED_UI' if ui_read else 'FIXTURE_PUBLISHER_DISABLED')
    data=deepcopy(rows);data[280].update(open=165,high=180,low=160,close=175,quote_volume=1750)
    data[280]['exact']={**data[280]['exact'],**{k:str(data[280][k]) for k in ('open','high','low','close','volume','quote_volume')}}
    feed(data);frame()
    page.get_by_label('Veri penceresini göster veya gizle',exact=True).click();frame()
    point=read('({x:chart.timeScale().logicalToCoordinate(280),y:series.priceToCoordinate(175)})');box=page.locator('.chart-host').bounding_box()
    page.mouse.move(box['x']+point['x'],box['y']+point['y']);page.wait_for_timeout(150)
    assert page.locator('.data-window').is_visible()
    assert '175' in page.locator('.data-window').inner_text()
    if ui_read:assert ui_read(lambda v:v['crosshair']['time']==data[280]['time'])['snapshot']['crosshair']['hover_candle']['close']=='175'
    record('crosshair_data_window_reads_requested_fixture_candle',bot_hover_api='CLIENT_REPORTED_UI' if ui_read else 'FIXTURE_PUBLISHER_DISABLED')
    magnet=page.get_by_label('Mıknatıs',exact=True);magnet.click();assert magnet.get_attribute('aria-pressed')=='true'
    page.get_by_label('Çizgi araçları',exact=True).click();page.get_by_role('button',name='Yatay çizgi',exact=True).click()
    frame();point=read('({x:chart.timeScale().logicalToCoordinate(280),y:series.priceToCoordinate(175)})');box=page.locator('.chart-host').bounding_box()
    page.mouse.click(box['x']+point['x'],box['y']+point['y']+2);count(1)
    d=listing()[0];assert Decimal(d['geometry']['anchors'][0]['price'])==175
    assert d['geometry']['anchors'][0]['time']==data[280]['time']
    if ui_read:assert ui_read(lambda v:v['magnet'])['snapshot']['magnet']
    record('magnet_actual_pointer_snaps_to_known_ohlc_instead_of_raw_price',anchor=d['geometry']['anchors'][0],bot_setting_api='CLIENT_REPORTED_UI' if ui_read else 'FIXTURE_PUBLISHER_DISABLED')
    page.get_by_label('Geri al',exact=True).click();count(0)
    page.get_by_label('Yeniden yap',exact=True).click();count(1)
    assert listing()[0]['drawing_id']==d['drawing_id'];record('current_header_undo_redo_preserves_identity')
    baseline=listing()[0]['geometry']
    control=page.get_by_label('Otomatik fiyat ölçeği',exact=True)
    if control.get_attribute('aria-pressed')!='false':control.click()
    assert read('series.priceScale().options().autoScale') is False
    read('chart.timeScale().setVisibleLogicalRange({from:100,to:180})');page.wait_for_timeout(80)
    before=read('chart.timeScale().getVisibleLogicalRange()')
    page.get_by_role('button',name='Güncel',exact=True).click();page.wait_for_timeout(100)
    after=read('chart.timeScale().getVisibleLogicalRange()')
    assert after['to']>before['to'] and abs((after['to']-after['from'])-(before['to']-before['from']))<1e-5
    assert read('series.priceScale().options().autoScale') is False
    page.get_by_label('Görünümü sıfırla',exact=True).click();page.wait_for_timeout(100)
    assert read('series.priceScale().options().autoScale') is True
    assert listing()[0]['geometry']==baseline
    record('latest_preserves_manual_scale_and_zoom_width_reset_restores_auto_without_geometry_writes',bot_viewport_api='CLIENT_REPORTED_UI' if ui_read else 'FIXTURE_PUBLISHER_DISABLED')
    def toggle_volume():
        menu=page.get_by_label('Paneller',exact=True)
        if menu.locator('..').get_attribute('open') is None:menu.click()
        page.get_by_label('Hacim paneli',exact=True).click();page.wait_for_timeout(120)
    assert read("chart.panes().flatMap(p=>p.getSeries()).filter(s=>s.seriesType()==='Histogram').length")==1
    toggle_volume();assert read("chart.panes().flatMap(p=>p.getSeries()).filter(s=>s.seriesType()==='Histogram'&&s.options().visible).length")==0
    toggle_volume();assert read("chart.panes().flatMap(p=>p.getSeries()).filter(s=>s.seriesType()==='Histogram'&&s.options().visible).length")==1
    assert read("chart.panes().flatMap(p=>p.getSeries()).filter(s=>s.seriesType()==='Histogram').length")==1
    record('volume_toggle_changes_native_visibility_without_duplicate_series')
    page.get_by_label('Açık temaya geç',exact=True).click();page.wait_for_timeout(100)
    assert page.locator('.terminal').get_attribute('data-theme')=='light'
    saved=client.get('/api/workspaces/main/profile').json()['body']['view']
    if ui_read:assert ui_read(lambda v:v['theme']=='light')['snapshot']['theme']=='light'
    record('theme_ui_state_is_separate_from_saved_profile',current_theme='light',saved_theme=saved['theme'],bot_current_ui_api='CLIENT_REPORTED_UI' if ui_read else 'FIXTURE_PUBLISHER_DISABLED')
    page.get_by_label('Koyu temaya geç',exact=True).click()
    frame();page.get_by_label('Fiyat ekseni türü',exact=True).select_option('LOG');page.wait_for_timeout(120)
    assert read('series.priceScale().options().mode')==1
    assert listing()[0]['geometry']==baseline
    page.get_by_label('Fiyat ekseni türü',exact=True).select_option('LINEAR');frame()
    record('view_mode_changes_leave_persisted_tool_coordinates_intact')
    # Persistent workspace and explicit leased UI session are separate resources.
    assert not {'cursor','selection','current_tool','magnet','visible_range'}&set(workspace)
    if ui_read:
        current=ui_read()['snapshot'];assert all(k in current for k in ('crosshair','selection','magnet','viewport','history'));assert not {'undo_stack','redo_stack'}&set(current['history'])
    record('persistent_workspace_and_ui_bridge_are_separate',ui_bridge='VERIFIED_CLIENT_REPORTED' if ui_read else 'FIXTURE_PUBLISHER_DISABLED',raw_history_stacks='NOT_EXPOSED')
    return checks
