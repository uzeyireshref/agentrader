"""P3 production App with actual WebSocket disconnect; isolated synthetic data."""
import copy
from decimal import Decimal
import hashlib
import json
import time
from measure_chart_interactions import main, INSPECT, ROOT
from agentrader.chart_market import candle
from agentrader.chart_precision import exact_tick
from agentrader.chart_evidence import snapshot


def checks(page,sockets,unused,result):
    result.update(date='2026-11-10',task='P3',checks=[])
    def read(expr):return page.evaluate(INSPECT[:INSPECT.index('return view?')]+'return ('+expr+');'+'}')
    rows=[]
    for i in range(300):
        start=1800000000000+i*900000
        base=Decimal(100)+Decimal(i)/10
        raw=[start,str(base),str(base+10),str(base-10),str(base+5),'10',start+899999,'1000',5,'5','500','0']
        rows.append(candle(raw,start+900000))
    market={'symbol':'BTCUSDT','base_asset':'BTC','quote_asset':'USDT','contract_type':'PERPETUAL','tick_size':'0.1','exact':exact_tick('0.1')}
    quality={'state':'OK','missing_bars':0,'short_history':False}
    epoch='a'*32;generation=7;sequence=100;revision=1
    def make(kind='snapshot'):
        evidence=snapshot(rows,market,quality,symbol='BTCUSDT',interval='15m',epoch=epoch,generation=generation,revision=revision)
        packet={'type':kind,'source':'binance_usdm_live_trade_price','environment':'live_public','product':'USD-M','price_type':'LAST_PRICE','symbol':'BTCUSDT','interval':'15m','stream_epoch':epoch,'generation':generation,'sequence':sequence,'status':'LIVE','received_at':int(time.time()*1000),'market':market,'quality':quality,'data_proof':evidence.view()}
        packet['candles' if kind=='snapshot' else 'tail']=rows if kind=='snapshot' else rows[-2:]
        return packet
    def send(packet):sockets[-1].send(json.dumps(packet));page.wait_for_timeout(140)
    def record(name,condition):
        assert condition,name
        result['checks'].append({'name':name,'passed':True})
    send(make());record('first_snapshot_hash_verified',read('view.stream_epoch')==epoch and read('view.data_proof.state')=='VERIFIED')
    old=make();before=read('view.sequence')
    unknown=copy.deepcopy(old);unknown['stream_epoch']='b'*32;unknown['type']='update';unknown.pop('candles');unknown['tail']=rows[-2:]
    send(unknown);record('unknown_epoch_update_ignored',read('view.sequence')==before and read('view.stream_epoch')==epoch)
    sequence=200;send(make('update'));record('sequence_jump_not_a_gap',read('view.sequence')==200 and read('view.data_proof.missing_bars')==0)
    current=make('update');send(current);record('heartbeat_keeps_revision',read('view.data_proof.data_revision')==1)
    count=len(sockets);sockets[-1].close(code=1011,reason='P3 controlled reconnect')
    page.wait_for_function('document.querySelector(".connection")?.textContent!=="Canlı"')
    deadline=time.monotonic()+5
    while len(sockets)==count and time.monotonic()<deadline:page.wait_for_timeout(100)
    record('actual_disconnect_reconnect',len(sockets)>count)
    epoch='b'*32;generation=1;sequence=1
    send(make('update'));record('restart_update_waits_for_snapshot',read('view.snapshot_required') is True and read('view.stream_epoch')=='a'*32)
    send(make());record('restart_snapshot_accepts_counter_reset',read('view.stream_epoch')==epoch and read('view.generation')==1 and read('view.snapshot_required') is False)
    send(old);record('retired_epoch_snapshot_rejected',read('view.stream_epoch')==epoch and read('view.generation')==1)
    # A corrupted current-epoch delta is never accepted and requests a fresh snapshot.
    count=len(sockets);bad=make('update');bad['sequence']=2;bad['tail']=copy.deepcopy(bad['tail']);bad['tail'][-1]['close']+=1
    send(bad)
    deadline=time.monotonic()+5
    while len(sockets)==count and time.monotonic()<deadline:page.wait_for_timeout(100)
    record('bad_hash_requests_snapshot',len(sockets)>count and read('view.snapshot_required') is True)
    send(make());record('snapshot_recovers_after_bad_hash',read('view.snapshot_required') is False and read('view.stream_epoch')==epoch)
    # A valid coalesced delta is accepted with a new immutable revision.
    rows[-1]['volume']=11.;rows[-1]['exact']['volume']='11';sequence=1000;revision=2
    send(make('update'));record('valid_delta_updates_snapshot_hash',read('view.sequence')==1000 and read('view.data_proof.data_revision')==2)
    result['assets']={str(p.relative_to(ROOT/'agentrader/web_assets')):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'agentrader/web_assets').rglob('*')) if p.is_file()}
    result['scope']='P3 production App/actual local WebSocket reconnect with synthetic upstream; not a real exchange outage or bot replay'


if __name__=='__main__':raise SystemExit(main(checks,'chart-p3-browser-20261110.json',production=True))
