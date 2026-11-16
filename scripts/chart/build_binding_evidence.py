"""Build a shipped traceability manifest from the existing parity artifacts."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
def hashed(path):return dict(path=path,sha256=hashlib.sha256((ROOT/path).read_bytes()).hexdigest())
def build():
 from agentrader.chart.binding_catalog import definitions
 sources=['agentrader/chart/drawings/coordinates.py','agentrader/chart/drawings/channel_family.py','agentrader/chart/drawings/service.py','agentrader/chart/drawings/contracts.py','agentrader/chart/chart_bindings.py','agentrader/chart/binding_catalog.py','agentrader/chart/drawings/calculations.py','agentrader/chart/drawings/channel.py','agentrader/chart/drawings/position.py','agentrader/chart/drawings/fibonacci.py','agentrader/chart/indicator_config.py','agentrader/chart/vwap.py']
 sources+=['agentrader/chart/binding_eligibility.py','agentrader/chart/chart_clock.py','agentrader/chart/chart_evidence.py','agentrader/chart/chart_precision.py','agentrader/shared/market_feed.py']
 sources+=['agentrader/chart/local_chart_events.py','agentrader/chart/chart_replay.py']
 sources+=['agentrader/shared/market_environment.py','agentrader/integration/shadow_tracking.py','agentrader/chart/chart_market.py']
 sources+=['agentrader/chart/drawings/tool_access.py']
 sources+=['agentrader/chart/chart_context.py','agentrader/api/chart_context.py']
 sources+=['agentrader/chart/chart_queries.py','agentrader/api/chart_queries.py']
 sources+=['agentrader/chart/drawings/family_math.py']
 sources+=['agentrader/chart/indicator_queries.py','agentrader/api/indicator_queries.py']
 sources+=['agentrader/chart/ui_sessions.py','agentrader/api/ui_sessions.py']
 sources+=['agentrader/chart/drawings/actors.py','agentrader/chart/drawings/notes.py','agentrader/api/drawings.py','agentrader/chart/chart_profiles.py','agentrader/migrations/__init__.py','agentrader/application/settings.py','agentrader/api/app.py']
 sources+=['agentrader/integration/chart_bot.py','agentrader/cli/chart_bot_cli.py','agentrader/__main__.py']
 sources+=['agentrader/chart/drawings/projection.py','agentrader/chart/drawings/packages.py']
 sources+=['agentrader/integration/chart_strategy.py']
 entries=definitions();manifest=dict(schema='chart-binding-evidence/1',runtime_sources=[hashed(p) for p in sources],targets={})
 for key,entry in entries.items():manifest['targets'][key]=dict(queries=entry['queries'],numeric_basis=entry['numeric_basis'],context_requirements=entry['context_requirements'],artifacts=[hashed(p) for p in entry['artifacts']])
 target=ROOT/'agentrader/binding_evidence.json';target.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8');print(str(target))
if __name__=='__main__':build()
