"""Offline growth probes; temporary stores only, no credentials or exchange access."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import statistics
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from agentrader.application.settings import WebSettings
from agentrader.application.service import ApplicationService
from agentrader.application.bot_inbox import BotInbox, checksum, encoded
from agentrader.shared.state import StateStore
from agentrader.chart.drawings.service import DrawingService
from agentrader.chart.chart_context import ChartContext
from agentrader.migrations import connect


def measured(call, repeats=5):
    values = []
    for _ in range(repeats):
        start = time.perf_counter(); value = call(); values.append((time.perf_counter()-start)*1000)
    return dict(median_ms=round(statistics.median(values), 3), max_ms=round(max(values), 3)), value


def run():
    result = dict(schema='hardening-growth/1', network=False, samples=[])
    with tempfile.TemporaryDirectory() as temp:
        base = Path(temp)
        for size in (100, 1000, 10000):
            store = StateStore(base/f'intents-{size}.db')
            with store.db:
                store.db.executemany('INSERT INTO intents(client_id,path,params,state) VALUES(?,?,?,?)',
                    ((f'id-{i}', '/fapi/v1/order', '{}', 'UNKNOWN') for i in range(size)))
            stats, _ = measured(lambda: next(r for r in store.intents() if r['client_id']==f'id-{size-1}'))
            direct, _ = measured(lambda: store.intent(f'id-{size-1}'))
            result['samples'].append(dict(kind='intent_lookup', size=size, historical_scan=stats, keyed=direct))
            store.close()
        for size in (10, 100, 1000):
            settings = WebSettings(application_database=base/f'app-{size}.db', execution_database=base/'exec.db', market_database=base/'market.db', token='a'*40, owner='bench', bot_enabled=True)
            ApplicationService(settings).initialize(); inbox=BotInbox(settings)
            payload={}; body=encoded({'state':'APPLIED','data':'x'*10000})
            with closing(connect(settings.application_database)) as db, db:
                db.executemany('INSERT INTO app_bot_jobs VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                    ((f'job-{i}',settings.owner,'CONTEXT',encoded(payload),checksum([settings.owner,'CONTEXT',payload]),'SUCCEEDED',i,i,body,checksum(json.loads(body)),None) for i in range(size)))
            count=[0,0]
            def traced(path):
                count[0]+=1; db=connect(path); db.set_trace_callback(lambda sql: count.__setitem__(1,count[1]+1) if sql.startswith('SELECT') else None); return db
            with patch('agentrader.application.bot_inbox.connect', side_effect=traced):
                stats, rows=measured(inbox.recent, repeats=1)
            result['samples'].append(dict(kind='job_list',size=size,**stats,connections=count[0],selects=count[1],response_bytes=len(encoded(rows).encode())))
            if 'summary' in __import__('inspect').signature(inbox.recent).parameters:
                count[:]=[0,0]
                with patch('agentrader.application.bot_inbox.connect', side_effect=traced):
                    stats, rows=measured(lambda:inbox.recent(summary=True),repeats=1)
                result['samples'].append(dict(kind='job_summary',size=size,**stats,connections=count[0],selects=count[1],response_bytes=len(encoded(rows).encode())))
        settings = WebSettings(application_database=base/'chart.db', execution_database=base/'exec.db', market_database=base/'market.db', owner='bench')
        ApplicationService(settings).initialize()
        with closing(connect(settings.application_database)) as db,db:
            for i in range(500):
                geometry=dict(kind='horizontal',symbol='BTCUSDT',price_source='LAST_PRICE',label='',anchors=[dict(time=1800000000,price='90000')])
                db.execute('INSERT INTO app_drawing_revisions VALUES(?,?,?,?,?,?,?,?)',('bench',str(i),1,'main',json.dumps(geometry),0,0,'{}'))
                db.execute('INSERT INTO app_drawing_heads VALUES(?,?,?)',('bench',str(i),1))
        class Hub:
            def binding_context(self,*args):return None
        context=ChartContext(settings.application_database,'bench',Hub())
        for size in (10,100,500):
            with closing(connect(settings.application_database)) as db,db:
                db.execute('UPDATE app_drawing_revisions SET workspace_id=CASE WHEN CAST(drawing_id AS INTEGER)<? THEN ? ELSE ? END',(size,'main','other'))
            counts=[0]
            real=sqlite3.connect
            def traced_sqlite(*args,**kwargs):
                db=real(*args,**kwargs);db.set_trace_callback(lambda sql:counts.__setitem__(0,counts[0]+1) if sql.startswith('SELECT') else None);return db
            with patch('sqlite3.connect',side_effect=traced_sqlite):
                stats, _=measured(lambda:context.read('main',symbol='BTCUSDT',interval='1m'),repeats=1)
            result['samples'].append(dict(kind='chart_context',size=size,selects=counts[0],**stats))
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);args=parser.parse_args();report=run()
    text=json.dumps(report,indent=2)
    if args.output:args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(text+'\n',encoding='utf-8')
    print(text)
