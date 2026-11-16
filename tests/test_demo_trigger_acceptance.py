import copy
from contextlib import closing
from datetime import datetime,timezone
from decimal import Decimal
import time
import unittest
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
from unittest.mock import Mock,patch
from scripts.bot.run_demo_trigger_acceptance import trigger_plan,native_result,inherited_limits,verify_generated_fill
from scripts.bot.run_bounded_demo_acceptance import test_limits as limits_for_test
from agentrader.bot.v2_preflight import prepare_single
from test_v2_preflight import snapshot


class TriggerAcceptanceTests(unittest.TestCase):
    def test_both_trigger_candidates_pass_small_budget_engine_preflight(self):
        for kind in ('STOP','TARGET'):
            s=snapshot();s.update(observed_at=time.time(),daily_loss='529.75247855')
            p=trigger_plan(s,kind,'fixture')
            result=prepare_single(p,s,limits_for_test('529.69467203'))
            self.assertEqual(result['state'],'READY')
            self.assertLessEqual(Decimal(p['sizing']['amount']),60)

    def test_same_account_day_and_original_fixed_budget_required(self):
        now=time.time();r=dict(state='PASSED',final_flat=True,account_ref='fixture',started_at=now,initial_daily_loss='529.69467203',limits=dict(max_daily_loss='532.69467203'))
        self.assertEqual(inherited_limits(r,'fixture',int(now*1000)).max_daily_loss,Decimal('532.69467203'))
        for changed,ref,stamp in [({**r,'state':'STOPPED'},'fixture',now), (r,'other',now),(r,'fixture',now+86400),({**r,'limits':dict(max_daily_loss='999')},'fixture',now)]:
            with self.assertRaises(ValueError):inherited_limits(changed,ref,int(stamp*1000))

    def proposal(self):
        return dict(params=dict(clientAlgoId='owned',symbol='BTCUSDT',side='SELL',positionSide='BOTH',type='STOP_MARKET',triggerPrice='79000'))

    def response(self):
        return dict(clientAlgoId='owned',symbol='BTCUSDT',side='SELL',positionSide='BOTH',orderType='STOP_MARKET',triggerPrice='79000',closePosition=True,workingType='MARK_PRICE',algoStatus='NEW')

    def test_active_cancelled_or_expired_algo_is_not_native_trigger_success(self):
        for state in ('NEW','CANCELED','EXPIRED','FINISHED'):
            r=self.response();r['algoStatus']=state
            self.assertEqual(native_result([self.proposal()],[r]),[])

    def test_native_success_requires_generated_order_and_exact_identity_content(self):
        r=self.response();r.update(algoStatus='FINISHED',actualOrderId=123,algoId=456)
        self.assertEqual(native_result([self.proposal()],[r])[0]['order_id'],123)
        for key,value in [('clientAlgoId','foreign'),('triggerPrice','78000'),('workingType','CONTRACT_PRICE'),('closePosition',False)]:
            with self.assertRaises(ValueError):native_result([self.proposal()],[{**r,key:value}])

    def test_generated_fill_checks_order_symbol_side_and_max_owned_quantity(self):
        s=dict(symbol='BTCUSDT',prepared=dict(entry=dict(params=dict(side='BUY',positionSide='BOTH',quantity='.0008'))))
        o=dict(orderId=123,symbol='BTCUSDT',side='SELL',positionSide='BOTH',status='FILLED',executedQty='.0008')
        verify_generated_fill(dict(order_id=123),o,s)
        for key,value in [('orderId',124),('symbol','ETHUSDT'),('side','BUY'),('executedQty','.0016'),('status','NEW')]:
            with self.assertRaises(ValueError):verify_generated_fill(dict(order_id=123),{**o,key:value},s)

    def test_post_cleanup_verifier_is_get_only_and_timeout_stays_unproven(self):
        from agentrader.shared.config import Config
        from scripts.bot.verify_demo_trigger_evidence import verify
        ref=hashlib.sha256(b'fixture').hexdigest();plan=dict(plan_id='owned-test')
        proposal=self.proposal();proposal['path']='/fapi/v1/algoOrder';response=self.response();response['algoStatus']='CANCELED'
        session=dict(account_ref=ref,active=False,plan=plan,symbol='BTCUSDT',protections=[proposal])
        exchange=Mock(config=Config('fixture','fixture'),offset_ms=0)
        exchange.request.return_value=response
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder);database=path/'execution.sqlite3';report=path/'report.json'
            with closing(sqlite3.connect(database)) as db:
                with db:
                    db.execute('CREATE TABLE managed_sessions(body TEXT)');db.execute('INSERT INTO managed_sessions VALUES (?)',(json.dumps(session),))
            report.write_text(json.dumps(dict(state='PARTIAL',final_flat=True,account_ref=ref,cases=[dict(plan=plan,requested_trigger='STOP',state='TIMEOUT_CLEANED')])),encoding='utf-8')
            with patch('scripts.bot.verify_demo_trigger_evidence.DemoExchange',return_value=exchange):r=verify(report,database)
        self.assertTrue(r['read_only']);self.assertEqual(r['order_requests'],0)
        self.assertFalse(r['cases'][0]['requested_native_proven'])
        self.assertEqual(exchange.request.call_args.args[0],'GET')
