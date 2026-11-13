"""Build a shipped traceability manifest from the existing parity artifacts."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def hashed(path):return dict(path=path,sha256=hashlib.sha256((ROOT/path).read_bytes()).hexdigest())
def build():
 from agentrader.binding_catalog import definitions
 sources=['agentrader/drawings/channel_family.py','agentrader/drawings/service.py','agentrader/drawings/contracts.py','agentrader/chart_bindings.py','agentrader/binding_catalog.py','agentrader/drawings/calculations.py','agentrader/drawings/channel.py','agentrader/drawings/position.py','agentrader/drawings/fibonacci.py','agentrader/indicator_config.py','agentrader/vwap.py']
 sources+=['agentrader/binding_eligibility.py','agentrader/chart_clock.py','agentrader/chart_evidence.py','agentrader/chart_precision.py','agentrader/market_feed.py']
 sources+=['agentrader/local_chart_events.py','agentrader/chart_replay.py']
 entries=definitions();manifest=dict(schema='chart-binding-evidence/1',runtime_sources=[hashed(p) for p in sources],targets={})
 for key,entry in entries.items():manifest['targets'][key]=dict(queries=entry['queries'],numeric_basis=entry['numeric_basis'],context_requirements=entry['context_requirements'],artifacts=[hashed(p) for p in entry['artifacts']])
 target=ROOT/'agentrader/binding_evidence.json';target.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8');print(str(target))
if __name__=='__main__':build()
