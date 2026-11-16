"""Isolated crash-test child. Only a parent-owned loopback fake exchange is allowed."""
import argparse
import json
from pathlib import Path
import sys
import time
from urllib.parse import urlparse
from urllib.request import Request,build_opener,ProxyHandler
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
from agentrader.shared.config import Config
from agentrader.shared.exchange import ExchangeError,NoRedirect
from agentrader.shared.locking import execution_lock
from agentrader.bot.plans import PlanService
from agentrader.bot.recovery_guardian import run_guardian
from agentrader.bot.reservations import ReservationBook
from agentrader.bot.risk import RiskLimits
from agentrader.shared.state import StateStore
from agentrader.bot.v2_runner import V2Runner
from test_plan_v2 import plan_v2
from test_v2_preflight import snapshot


def main():
    p=argparse.ArgumentParser();p.add_argument('role',choices=['guardian','executor'])
    p.add_argument('--database',required=True);p.add_argument('--url',required=True);p.add_argument('--stage');p.add_argument('--marker')
    args=p.parse_args();target=urlparse(args.url)
    if target.scheme!='http' or target.hostname!='127.0.0.1' or target.path not in ('','/'):
        raise ValueError('Loopback fake exchange only')
    opener=build_opener(ProxyHandler({}),NoRedirect())
    def pause(stage):
        if args.stage!=stage:return
        Path(args.marker).write_text(stage)
        while True:time.sleep(.1)
    class RemoteExchange:
        config=Config('demo-key','secret-never-output');offset_ms=0
        def sync_time(self):pass
        def get(self,path,params=None):return self.request('GET',path,params)
        def request(self,method,path,params=None):
            if method=='POST' and path=='/fapi/v1/order':pause('before_delivery')
            payload=json.dumps(dict(method=method,path=path,params=params)).encode()
            with opener.open(Request(args.url+'/exchange',data=payload,headers={'Content-Type':'application/json'}),timeout=5) as response:
                data=json.load(response)
            if data.get('error'):raise ExchangeError('Isolated fake exchange response',data['code'],delivery_status=data['delivery_status'])
            if method=='POST' and path=='/fapi/v1/order':pause('entry_accepted')
            if method=='POST' and path=='/fapi/v1/algoOrder':pause('protection_accepted')
            return data['result']
    if args.role=='guardian':
        run_guardian(Path(args.database),'local:test',RemoteExchange,RiskLimits(),execute=True)
        return
    with execution_lock():
        store=StateStore(Path(args.database))
        try:
            service=PlanService(store,'local:test');plan=plan_v2()
            plan['plan_id']='isolated-crash-plan';plan['analysis_ref']='shadow-event:'+'a'*64
            plan['entry'].update(condition='LIMIT',trigger_price='79900')
            created=service.create(plan,'local:test');service.authorize(plan['plan_id'],1,created['authorization_token'],'approve','local:test')
            original_reserve=ReservationBook.reserve;original_claim=PlanService.claim;original_save=V2Runner._save
            def reserve(self,*a,**k):
                result=original_reserve(self,*a,**k);pause('after_reserve');return result
            def claim(self,*a,**k):
                result=original_claim(self,*a,**k);pause('after_claim');return result
            def save(self,*a,**k):
                result=original_save(self,*a,**k);pause('after_session');return result
            def fresh_snapshot(*a,**k):
                s=snapshot();s.update(observed_at=time.time(),finished_at=time.time(),now_ms=int(time.time()*1000));return s
            with patch('agentrader.bot.v2_runner.guard_chart_entry',return_value=True),patch('agentrader.bot.v2_runner.collect_flat_snapshot',side_effect=fresh_snapshot),\
                 patch.object(ReservationBook,'reserve',reserve),patch.object(PlanService,'claim',claim),patch.object(V2Runner,'_save',save):
                V2Runner(service,RemoteExchange(),RiskLimits()).open(plan['plan_id'],1,True)
                pause('protected')
        finally:store.close()

if __name__=='__main__':main()
