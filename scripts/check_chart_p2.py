"""Current production App P2 status checks; synthetic public packets only."""
import hashlib
import json
import time
from measure_chart_interactions import main, ROOT


def checks(page, sockets, rows, result):
    result.update(date='2026-11-10', task='P2', checks=[])
    generation, sequence = 2, 1
    stamp = 1800000003000
    proof = {'schema':'chart-time-proof/1','policy':{'schema':'chart-time-policy/1'},
             'state':'FRESH','reason':None,'data_age_ms':0,'upstream_age_upper_ms':1,
             'uncertainty_ms':1,'upstream_event_time':stamp}
    def send(timing, snapshot=False):
        nonlocal sequence
        packet = {'type':'snapshot' if snapshot else 'update','symbol':'BTCUSDT','interval':'15m',
                  'status':'LIVE','generation':generation,'sequence':sequence,
                  'received_at':int(time.time()*1000),'timing':timing}
        if snapshot: packet['candles']=[dict(row,closed=True) for row in rows]
        sockets[-1].send(json.dumps(packet));page.wait_for_timeout(100)
    def expect(name, label):
        page.wait_for_function('(label)=>document.querySelector(".connection")?.textContent===label', arg=label)
        result['checks'].append({'name':name,'passed':True,'label':label})
    send(proof, True);expect('fresh_proof_display', 'Canlı')
    send(dict(proof,data_age_ms=11000,upstream_age_upper_ms=11001));expect('old_upstream_fresh_heartbeat', 'Veri gecikiyor')
    send(proof);expect('replayed_heartbeat_does_not_restore', 'Veri gecikiyor')
    generation+=1;proof=dict(proof,upstream_event_time=stamp+1000)
    send(proof, True);expect('fresh_snapshot_and_event_recovers', 'Canlı')
    page.evaluate('window.__p2originalNow=Date.now;Date.now=()=>window.__p2originalNow()+100000')
    send(proof);expect('browser_wall_jump_blocks', 'Veri gecikiyor')
    page.evaluate('Date.now=window.__p2originalNow')
    send(proof);expect('clock_block_stays_until_snapshot', 'Veri gecikiyor')
    generation+=1;proof=dict(proof,upstream_event_time=stamp+2000)
    send(proof, True);expect('snapshot_after_clock_jump_recovers', 'Canlı')
    sequence+=1
    send(dict(proof,state='BLOCKED',reason='SNAPSHOT_REQUIRED'));expect('long_outage_barrier_display', 'Veri gecikiyor')
    sequence+=1
    send(dict(proof,state='BLOCKED',reason='CLOCK_UNTRUSTED'));expect('missing_clock_proof_display', 'Veri gecikiyor')
    result['assets']={str(p.relative_to(ROOT/'agentrader/web_assets')):hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in sorted((ROOT/'agentrader/web_assets').rglob('*')) if p.is_file()}
    result['scope']='P2 controlled producer timing and actual App status transitions; no real exchange outage or physical acceptance'


if __name__=='__main__':
    raise SystemExit(main(checks,'chart-p2-browser-20261110.json',production=True))
