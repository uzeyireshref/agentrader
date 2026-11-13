"""Read-only localhost P2 probe; public market only, no account API."""
import json
from pathlib import Path
import time
import websocket


def main():
    result={'task':'P2','date':'2026-11-10','passed':False,'samples':[],
            'scope':'Actual localhost/public feed clock proof; not an exchange outage test',
            'account_requests':0,'order_requests':0}
    ws=None
    try:
        ws=websocket.create_connection('ws://127.0.0.1:8765/api/market-stream?symbol=BTCUSDT&interval=15m',
                                       origin='http://127.0.0.1:8765',timeout=10)
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            packet=json.loads(ws.recv())
            timing=packet.get('timing',{})
            result['samples'].append({'type':packet.get('type'),'status':packet.get('status'),
                                      'timing':timing})
            if timing.get('state')=='FRESH':
                result['passed']=True
                break
    except Exception as error:
        result['error_type']=type(error).__name__
    finally:
        if ws is not None: ws.close()
    (Path(__file__).resolve().parents[1]/'reports/chart-p2-live-20261110.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'passed':result['passed'],'samples':len(result['samples']),
                      'timing':result['samples'][-1]['timing'] if result['samples'] else None}))
    return 0 if result['passed'] else 1


if __name__=='__main__': raise SystemExit(main())
