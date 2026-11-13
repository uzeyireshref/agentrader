"""W1 full offline regression plus isolated loopback HTTP/restart evidence."""
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from check_local_api import check_local_api


def protected_snapshot():
    files = [ROOT / 'risk-demo.json']
    for name in ('execution.sqlite3', 'market.sqlite3'):
        files.extend(p for p in (ROOT / 'data').glob(name + '*') if p.is_file())
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.exists()}


def main():
    before = protected_snapshot()
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=1).run(unittest.defaultTestLoader.discover(str(ROOT / 'tests')))
    smoke = {'result': 'NOT_RUN'}
    smoke_error = False
    if result.wasSuccessful():
        try:
            smoke = check_local_api()
        except Exception:
            smoke_error = True
            smoke = {'result': 'FAILED', 'error': 'LOCAL_API_CHECK_FAILED'}
    unchanged = before == protected_snapshot()
    date = datetime.now(timezone(timedelta(hours=4))).date().isoformat()
    passed = result.wasSuccessful() and not result.skipped and not smoke_error and smoke['result'] == 'PASSED' and unchanged
    report = {'date': date, 'timezone': 'Asia/Baku', 'package': 'W1',
              'test_command': 'python scripts/validate_web_foundation.py',
              'result': 'PASSED' if passed else 'FAILED', 'test_count': result.testsRun,
              'baseline_test_count': 594, 'new_test_count': result.testsRun - 594,
              'skipped_count': len(result.skipped),
              'failures': [str(case) for case, _ in result.failures + result.errors],
              'verification': 'OFFLINE_FAKE_EXCHANGE_AND_ISOLATED_LOOPBACK_HTTP',
              'local_http': smoke, 'existing_runtime_databases_and_risk_unchanged_during_validation': unchanged,
              'demo_writes_performed': 0, 'external_messages_sent': 0,
              'background_monitor_started': False, 'server_left_running': False,
              'scheduled_tasks_registered': 0, 'web_chart_implemented': False,
              'trading_http_commands_enabled': False, 'details': '20-W1-YEREL-UYGULAMA-API.md'}
    destination = ROOT / ('reports/web-foundation-validation-' + date.replace('-', '') + '.json')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(output.getvalue(), end='')
    print(json.dumps({'result': report['result'], 'test_count': result.testsRun,
                      'local_http': smoke['result'], 'report': str(destination.relative_to(ROOT))}))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
