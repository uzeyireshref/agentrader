"""Frozen Python/TypeScript preview parity fixture, no account or network access."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
from test_signal_previews import PreviewTests
case=PreviewTests();case.setUp()
try:
    value=dict(binding=case.h.b,preview=case.create())
    (ROOT/'frontend/tests/fixtures/signal-preview.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
finally:case.doCleanups()
