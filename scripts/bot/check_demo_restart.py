"""Mevcut korumalı demo oturumunda devralma/stop kaybı/temiz kapanış kanıtı.

Önce: python -m agentrader managed-open --execute-demo --test-only --crash-after-ready
Bu betik yalnızca mevcut yönetilen demo oturumuyla çalışır; yeni giriş açmaz.
"""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agentrader.shared.config import Config
from agentrader.shared.exchange import DemoExchange
from agentrader.shared.locking import execution_lock
from agentrader.shared.state import StateStore
from agentrader.bot.watchdog import Watchdog
from agentrader.bot.execution import reconcile


def main():
    with execution_lock():
        store = StateStore()
        try:
            session = Watchdog(DemoExchange(Config.load()), store).session()
            before = len(store.intents())
            sid = session['id']
        finally:
            store.close()
    # Yeni işletim sistemi süreçleri; aynı SQLite kayıtlarını devralır.
    for _ in range(2):
        result = subprocess.run([sys.executable, '-m', 'agentrader', 'watchdog', '--execute-demo'],
                                cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=240)
        if result.returncode or '"status": "protected"' not in result.stdout:
            raise RuntimeError('Ayrı süreçte devralma doğrulanamadı; managed-close ile hesabı kontrol edin.')
        print(result.stdout.strip(), flush=True)
    with execution_lock():
        store = StateStore()
        x = DemoExchange(Config.load())
        watchdog = Watchdog(x, store)
        try:
            s = watchdog.session()
            if s['id'] != sid or len(store.intents()) != before:
                raise RuntimeError('Devralmada yeni emir oluştu.')
            snap = watchdog.snapshot(s)
            if snap['amount'] <= 0:
                raise RuntimeError('Test pozisyonu artık açık değil.')
            stops = [p for p in s['protections'] if p['type'] == 'STOP_MARKET'
                     and watchdog.valid_protection(s, p, snap['algos'].get(p['clientAlgoId'], {}))]
            if len(stops) != 1:
                raise RuntimeError('Stop kaybı testi için tam bir doğrulanmış stop gerekli.')
            cid = stops[0]['clientAlgoId']
            store.event('demo_fault_injection', {'session_id': sid, 'action': 'cancel_owned_stop', 'clientAlgoId': cid})
            x.request('DELETE', '/fapi/v1/algoOrder', {'clientAlgoId': cid})
            repaired = watchdog.tick(execute=True)
            if repaired['status'] != 'protected' or len(store.intents()) != before + 1:
                raise RuntimeError('Tek stop onarımı doğrulanamadı.')
            second = watchdog.tick(execute=True)
            if len(store.intents()) != before + 1:
                raise RuntimeError('Tekrarlayan kontrolde çift stop oluştu.')
            print(json.dumps({'step': 'repair', 'result': repaired, 'second_check': second}, ensure_ascii=False), flush=True)
        finally:
            # Hata olsa da yalnızca sahipliği yeniden doğrulanan pozisyon kapatılır.
            try:
                if store.sessions():
                    print(json.dumps(watchdog.tick(execute=True, close=True)), flush=True)
                final = reconcile(x, store)
                if final['position_count'] or final['open_order_count'] or final['open_algo_order_count']:
                    raise RuntimeError('Demo hesap temiz kapanmadı.')
                Path('logs').mkdir(exist_ok=True)
                Path('logs/restart-test-result.json').write_text(json.dumps(final, indent=2), encoding='utf-8')
            finally:
                store.close()


if __name__ == '__main__':
    main()
