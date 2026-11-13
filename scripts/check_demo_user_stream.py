"""Check demo stream resources and handshake; never manage sessions or orders."""
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agentrader.config import Config
from agentrader.exchange import DemoExchange
from agentrader.user_stream import DemoUserStream


def main():
    report = dict(environment='demo', product='USD-M', trade_mutations=0,
                  account_setting_mutations=0, stream_resource_post=False,
                  stream_resource_put=False, socket_connected=False,
                  remote_key_deleted=False, session_management_started=False)
    stream = None
    try:
        exchange = DemoExchange(Config.load(ROOT/'.env'))
        stream = DemoUserStream(exchange)
        info = stream.connect()
        report.update(stream_resource_post=True, socket_connected=True,
                      stream_generation=info['generation'])
        response = exchange.request('PUT', '/fapi/v1/listenKey')
        report.update(stream_resource_put=True,
                      keepalive_key_verified=isinstance(response, dict) and
                      response.get('listenKey', stream._key) == stream._key)
        # A solicited pong proves the upgraded socket is exchanging frames.
        stream.socket.connection.ping(b'agentrader')
        stream.socket.last_ping = time.monotonic()
        stream.socket.awaiting_pong = True
        event = stream.wait(3)
        report.update(event_observed=event is not None,
                      heartbeat_verified=not stream.socket.awaiting_pong)
        report['status'] = ('PASSED' if report['keepalive_key_verified'] and report['heartbeat_verified']
                            else 'NOT_FULLY_VERIFIED')
    except Exception as exc:
        report.update(status='FAILED', error_type=type(exc).__name__)
    finally:
        if stream is not None:
            stream.close()
        report['socket_closed'] = True
    # Only metadata above is written: no keys, private URLs or account payloads.
    (ROOT/'reports/user-stream-connection-20261106.json').write_text(
        json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report))
    return 0 if report['status'] == 'PASSED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
