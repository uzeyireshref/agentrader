"""Declared offline query coverage. This is traceability, never market-data eligibility."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MANIFEST=Path(__file__).with_name('binding_evidence.json')
def definitions():
 result={}
 def entry(name,queries,artifacts,basis='RATIONAL_CANONICAL'):
  result[name]=dict(queries=[dict(operation=op,output=out,output_type=typ,rules=['observe','approach','touch','close_cross'] if typ=='PRICE' else ['observe']) for op,out,typ in queries],artifacts=artifacts,numeric_basis=basis,context_requirements=['verified_market_identity','closed_data_reference','fresh_clock','verified_grid']+(['native_tick_size'] if name=='drawing:ruler' else ['native_ohlcv','calculation_version','warmup','volume_provenance_or_seed'] if name.startswith('indicator:') else []))
 basic=['frontend/tests/fixtures/geometry-parity.json','tests/test_chart_calculations.py']
 for kind in ['horizontal','trend','horizontal_ray','ray','extended_line']:
  entry('drawing:'+kind,[('priceAt','value','PRICE'),('distance','value','METRIC')],basic if kind in ('horizontal','trend') else ['frontend/tests/lineGeometry.test.ts','tests/test_line_extensions.py'])
 entry('drawing:zone',[('contains','value','BOOLEAN'),('distance','value','METRIC')],basic)
 for kind in ['fibonacci','fibonacci_extension']:entry('drawing:'+kind,[('level','value','PRICE')],['frontend/tests/fibonacciConfig.test.ts','tests/test_configurable_fibonacci.py'])
 entry('drawing:parallel_channel',[('boundsAt',out,'PRICE' if out!='width' else 'METRIC') for out in ['lower','middle','upper','width']]+[('contains','value','BOOLEAN'),('distance','value','METRIC')],['frontend/tests/channel.test.ts','tests/test_parallel_channel.py'])
 for kind in ['long_plan','short_plan']:entry('drawing:'+kind,[('riskReward',out,'HYPOTHETICAL_METRIC') for out in ['entry_fill','stop_fill','target_fill','gross_rr','net_rr','quantity']],['frontend/tests/position.test.ts','tests/test_chart_position.py'])
 entry('drawing:ruler',[('measurement',out,'METRIC') for out in ['price_change','percent_change','tick_change','duration_seconds']],['frontend/tests/fixtures/ruler-parity.json','tests/test_ruler.py'])
 for kind in ['EMA','SMA','RSI','ATR','MACD','BB','SESSION_VWAP','ANCHORED_VWAP']:
  outputs=['macd','signal','histogram'] if kind=='MACD' else ['basis','upper','lower'] if kind=='BB' else ['value']
  files=['frontend/tests/fixtures/g05-multi-parity.json'] if kind in ('MACD','BB') else ['frontend/tests/fixtures/vwap-parity.json'] if 'VWAP' in kind else ['frontend/tests/fixtures/indicators-v2-parity.json']
  entry('indicator:'+kind,[('valueAt',out,'DISPLAY_NUMBER') for out in outputs],files,'RATIONAL_RATIO_OR_BAR_DISPLAY' if 'VWAP' in kind else 'FLOAT_DISPLAY')
 return result

def catalog():
 try:
  data=json.loads(MANIFEST.read_text(encoding='utf-8'))
  good=data.get('schema')=='chart-binding-evidence/1' and all(hashlib.sha256((ROOT/x['path']).read_bytes()).hexdigest()==x['sha256'] for x in data['runtime_sources'])
 except (OSError,ValueError,KeyError,TypeError):data={};good=False
 return dict(schema='chart-binding-catalog/1',state='VERIFIED_TRACEABILITY' if good else 'BLOCKED',reason=None if good else 'QUERY_EVIDENCE_STALE_OR_MISSING',targets=data.get('targets',{}) if good else {},evaluation_state='SEPARATE_READ_ONLY_P5',order_authority=False)
