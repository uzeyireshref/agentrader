"""Frozen local-only review fixture for client integrity tests; no exchange access."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
from test_chart_approval import ChartApprovalTests

if __name__=='__main__':
    fixture=ChartApprovalTests();fixture.setUp()
    try:
        (ROOT/'frontend/tests/fixtures/chart-review.json').write_text(json.dumps(dict(
            preview=fixture.f.body,review=fixture.view),ensure_ascii=False,indent=2),encoding='utf-8')
    finally:fixture.doCleanups()
