"""Compatibility entry point for the replacement signed-coordinate regression."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

from scripts.chart.check_chart_navigation_signed import main
if __name__=="__main__": main()
