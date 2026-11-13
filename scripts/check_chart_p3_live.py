"""Read-only actual local/public P3 snapshot verification and resubscription."""
import json
from pathlib import Path
import sys
import time
import websocket
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from agentrader.chart_evidence import snapshot,require_warmup


def main():
    result={'task':'P3','date':'2026-11-10','passed':False,'snapshots':[],
            'account_requests':0,'order_requests':0,
            'scope':'Actual public feed and localhost resubscription, not an exchange/process outage'}
    try:
        for index in range(2):
            ws=websocket.create_connection('ws://127.0.0.1:8765/api/market-stream?symbol=BTCUSDT&interval=15m',origin='http://127.0.0.1:8765',timeout=10)
            try:
                deadline=time.monotonic()+15
                while time.monotonic()<deadline:
                    packet=json.loads(ws.recv())
                    if packet.get('type')!='snapshot' or not packet.get('data_proof'):continue
                    proof=packet['data_proof']
                    evidence=snapshot(packet['candles'],packet['market'],packet['quality'],symbol=packet['symbol'],interval=packet['interval'],epoch=packet['stream_epoch'],generation=packet['generation'],revision=proof['data_revision'])
                    assert evidence.view()==proof
                    warmup=require_warmup(evidence,50)
                    assert proof['state']=='VERIFIED' and warmup['state']=='DATA_PROOF_VERIFIED_NOT_ELIGIBILITY'
                    result['snapshots'].append({'subscription':index+1,'stream_epoch':packet['stream_epoch'],'generation':packet['generation'],'data_revision':proof['data_revision'],'snapshot_hash':proof['snapshot_hash'],'bars':proof['bar_count'],'warmup':warmup})
                    break
            finally:ws.close()
        result['passed']=len(result['snapshots'])==2
    except Exception as error:result['error_type']=type(error).__name__
    (Path(__file__).resolve().parents[1]/'reports/chart-p3-live-20261110.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2));return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
