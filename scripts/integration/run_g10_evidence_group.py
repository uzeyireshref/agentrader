"""Run existing isolated acceptance helpers into G10 without rewriting historic evidence."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import importlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))

if __name__=='__main__':
    name,folder,*args=sys.argv[1:]
    module=importlib.import_module('scripts.'+name)
    module.OUT=ROOT/'reports/chart-interface-g10-20261115'/folder
    sys.argv=[name,*args]
    raise SystemExit(module.main())
