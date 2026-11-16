"""Regenerate demo-context parity fixtures; historical reports are not rewritten."""

# Allow direct execution from any working directory.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))

import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from agentrader.chart.chart_bindings import binding_hash
from agentrader.chart.drawings.calculations import canonical_hash
from agentrader.chart.chart_evidence import digest
from agentrader.chart.binding_catalog import catalog
from agentrader.shared.market_environment import SOURCE, ENVIRONMENT


def main():
    file=ROOT/'frontend/tests/fixtures/binding-parity.json'
    data=json.loads(file.read_text(encoding='utf-8'))
    evidence=catalog()
    assert evidence['state']=='VERIFIED_TRACEABILITY'
    for b in data['bindings']:
        d=b['definition'];t=d['target']
        d['market'].update(source=SOURCE, environment=ENVIRONMENT)
        if t['type']=='drawing':
            t['content_hash']=canonical_hash(t['snapshot'],times=d['grid']['times'],interval=d['market']['interval'],scale=d['scale'])
        entry=evidence['targets'][t['type']+':'+t['kind']]
        descriptor=next(q for q in entry['queries'] if q['operation']==d['query']['operation'] and q['output']==d['query']['output'])
        d['query_evidence']={**entry,'descriptor':descriptor,'hash':digest(entry)}
        d['evaluation_state']='SEPARATE_READ_ONLY_P5'
        b['definition_hash']=binding_hash(d)
    file.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

if __name__=='__main__': main()
