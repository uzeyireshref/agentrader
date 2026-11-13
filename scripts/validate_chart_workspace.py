"""W2/W3 offline regression and real isolated local HTTP/restart validation."""
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from check_local_api import check_local_api
from validate_web_foundation import protected_snapshot


def main():
    before = protected_snapshot()
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=1).run(unittest.defaultTestLoader.discover(str(ROOT/'tests')))
    http = {'result': 'NOT_RUN'}
    if result.wasSuccessful():
        try:
            http = check_local_api(include_drawings=True)
        except Exception:
            http = {'result': 'FAILED', 'error': 'LOCAL_WORKSPACE_CHECK_FAILED'}
    unchanged = before == protected_snapshot()
    passed = result.wasSuccessful() and not result.skipped and http['result'] == 'PASSED' and unchanged
    date = datetime.now(timezone(timedelta(hours=4))).date().isoformat()
    report = {'date': date, 'timezone': 'Asia/Baku', 'packages': ['W2', 'W3'],
              'result': 'PASSED' if passed else 'FAILED', 'test_count': result.testsRun,
              'baseline_test_count': 631, 'new_test_count': result.testsRun-631,
              'skipped_count': len(result.skipped),
              'failures': [str(case) for case, _ in result.failures+result.errors],
              'local_http': http, 'existing_runtime_databases_and_risk_unchanged': unchanged,
              'visual_browser_qa': 'NOT_VERIFIED', 'drawing_interaction_qa': 'NOT_VERIFIED',
              'demo_writes_performed': 0, 'external_messages_sent': 0,
              'trading_commands_enabled': False, 'strategy_tracking_implemented': False,
              'details': '21-GRAFIK-VE-KALICI-CIZIMLER.md'}
    path = ROOT/('reports/chart-workspace-validation-'+date.replace('-', '')+'.json')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(output.getvalue(), end='')
    print(json.dumps({'result': report['result'], 'tests': result.testsRun, 'http': http['result'], 'report': str(path.relative_to(ROOT))}))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
