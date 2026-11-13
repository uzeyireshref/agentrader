import copy,unittest,tempfile
from pathlib import Path
from decimal import Decimal
from agentrader.alert_conditions import conditions,evaluate_all,values,ConditionUnavailable
from agentrader.indicator_config import defaults_v4,series,multi_series
from agentrader.price_alerts import PriceAlerts,definition,AlertError
from agentrader.migrations import migrate
from agentrader.market_data import SOURCE
T=1800057600 # UTC midnight

def rows(prices):
    out=[]
    for i,p in enumerate(prices):
        t=T+i*60;out.append(dict(time=t,close_time=(t+60)*1000-1,open=p,high=p+1,low=p-1,close=p,volume=10+i,quote_volume=(10+i)*p,closed=True,exact=dict(state='VERIFIED',open=str(p),high=str(p+1),low=str(p-1),close=str(p),volume=str(10+i),quote_volume=str((10+i)*p))))
    return out

def op(field='close'):return dict(type='market',field=field)
def val(v):return dict(type='value',value=str(v))
def condition(operator='above',left=None,right=None,upper=None,bars=1):return dict(left=left or op(),operator=operator,right=right or val(100),upper=upper,bars=bars)
def alert(cs,match='all'):return dict(schema='technical-alert/2',name='Multi',symbol='BTCUSDT',interval='1m',match=match,conditions=cs,frequency='bar_close',expires_at=None,message='Test')
class ConditionTests(unittest.TestCase):
    def test_all_operators_independent_numeric_examples(self):
        cases=[('cross',[99,100],100,None,True),('cross_up',[100,101],100,None,False),('cross_down',[101,100],100,None,True),('above',[100,101],100,None,True),('below',[100,99],100,None,True),('equal',[99,100],100,None,True),('not_equal',[99,101],100,None,True),('inside',[99,101],100,105,True),('outside',[101,110],100,105,True),('enter',[99,100],100,105,True),('exit',[105,106],100,105,True),('move_up',[100,105],5,None,True),('move_down',[100,95],5,None,True),('move_up_pct',[100,105],5,None,True),('move_down_pct',[100,95],5,None,True),('rising',[100,101],0,None,True),('falling',[101,100],0,None,True)]
        for operator,ps,r,u,expected in cases:
            d=alert([condition(operator,right=val(r),upper=None if u is None else val(u))]);self.assertEqual(evaluate_all(definition(d),rows(ps))[0],expected,operator)
    def test_and_or_are_same_close_and_unknown_never_silently_false(self):
        cs=[condition('above',right=val(100)),condition('below',right=val(90))]
        self.assertFalse(evaluate_all(definition(alert(cs)),rows([99,101]))[0]);self.assertTrue(evaluate_all(definition(alert(cs,'any')),rows([99,101]))[0])
        cs[1]['left']=dict(type='indicator',config=defaults_v4()[2],output='value')
        with self.assertRaises(ConditionUnavailable):evaluate_all(definition(alert(cs,'any')),rows([99,101]))
    def test_moving_lookback_and_all_monotonic_steps(self):
        self.assertTrue(evaluate_all(definition(alert([condition('move_up_pct',right=val(10),bars=3)])),rows([100,101,109,110]))[0])
        self.assertFalse(evaluate_all(definition(alert([condition('rising',right=val(0),bars=3)])),rows([100,105,104,110]))[0])
    def test_indicator_outputs_reuse_existing_chart_reference(self):
        sample=rows([100+(i%13)*.7+i*.03 for i in range(180)])
        for c in defaults_v4()[:7]:
            outputs=('macd','signal','histogram') if c['kind']=='MACD' else ('basis','upper','lower') if c['kind']=='BB' else ('value',)
            for output in outputs:
                operand=dict(type='indicator',config=c,output=output);d=definition(alert([condition('above',left=operand,right=val(-1000))]));self.assertTrue(evaluate_all(d,sample)[0])
                expected=multi_series(sample,c,'1m')[output][-1]['value'] if c['kind'] in ('MACD','BB') else series(sample,c,'1m')[-1]['value']
                self.assertEqual(values(operand,sample,'1m','BTCUSDT')[-1],Decimal(str(expected)))
        fast=copy.deepcopy(defaults_v4()[0]);fast['period']=3
        a=dict(type='indicator',config=fast,output='value');self.assertEqual(values(a,rows([100,101,102,110]),'1m','BTCUSDT')[-1],Decimal('105.5'))
    def test_session_vwap_complete_and_anchor_vwap(self):
        sample=rows([100,102,104]);c=defaults_v4()[7];o=dict(type='indicator',config=c,output='value');self.assertIsNotNone(values(o,sample,'1m','BTCUSDT')[-1])
        c=defaults_v4()[8];c['params'].update(anchor_time=T,anchor_symbol='BTCUSDT');d=definition(alert([condition('above',left=dict(type='indicator',config=c,output='value'),right=val(1))]));self.assertTrue(evaluate_all(d,sample)[0])
    def test_drawing_snapshot_price_projection_and_fib(self):
        sample=rows([100,101,102]);g=dict(kind='horizontal',symbol='BTCUSDT',price_source='LAST_PRICE',label='Line',anchors=[dict(time=T,price='101')]);o=dict(type='drawing',geometry=g,output='value',ratio=None)
        self.assertTrue(evaluate_all(definition(alert([condition('cross_up',right=o)])),sample)[0] is False) # prior equality does not cross
        self.assertEqual(values(o,sample,'1m','BTCUSDT')[-1],Decimal(101))
        g=dict(kind='trend',symbol='BTCUSDT',price_source='LAST_PRICE',label='Trend',anchors=[dict(time=T,price='100'),dict(time=T+120,price='104')]);o=dict(type='drawing',geometry=g,output='value',ratio=None);self.assertEqual(values(o,sample,'1m','BTCUSDT')[-1],Decimal(104))
    def test_reject_invalid_config_future_schema_shifted_bb_and_unbounded_count(self):
        for patch in ({'match':'xor'},{'conditions':[]},{'conditions':[condition()]*9},{'conditions':[{**condition(),'bars':True}]},{'conditions':[condition('inside')]}):
            d=alert([condition()]);d.update(patch)
            with self.assertRaises(AlertError):definition(d)
        c=defaults_v4()[6];c['params']['offset']=1
        with self.assertRaises(AlertError):definition(alert([condition(left=dict(type='indicator',config=c,output='basis'))]))
    def test_engine_compound_persists_snapshot_results_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as folder:
            db=Path(folder)/'app.db';migrate(db);s=PriceAlerts(db,'owner');d=alert([condition('above'),condition('above',left=op('volume'),right=val(5))]);a=s.save(d)
            def ctx(ps):return dict(identity=dict(source=SOURCE,environment='live_public',product='USD-M',price_type='LAST_PRICE',symbol='BTCUSDT',interval='1m'),transport_state='LIVE',timing=dict(state='FRESH'),quality=dict(state='OK'),stream_epoch='a',rows=rows(ps))
            s.process(a['id'],ctx([99,100]),'b');s.process(a['id'],ctx([99,100,101]),'b');s.process(a['id'],ctx([99,100,101]),'b');self.assertEqual(len(s.events()),1);e=s.events()[0];self.assertEqual(e['conditions'],[True,True]);self.assertEqual(e['definition']['conditions'],d['conditions']);self.assertFalse(e['order_authority'])


class CompoundApiTests(unittest.TestCase):
    def test_real_compound_api_and_worker_context(self):
        from fastapi.testclient import TestClient
        from agentrader.api.app import create_app
        from agentrader.application.settings import WebSettings
        class Market:
            def selection(self,*a):pass
        class Hub:
            def acquire(self,*a):return object()
            def release(self,*a):pass
            def binding_context(self,*a):return None
            def close(self):pass
        with tempfile.TemporaryDirectory() as folder:
            settings=WebSettings(Path(folder)/'app.db',Path(folder)/'exec.db',market_database=Path(folder)/'market.db')
            with TestClient(create_app(settings,market=Market(),hub=Hub()),base_url='http://127.0.0.1') as client:
                c=copy.deepcopy(defaults_v4()[3]);c['period']=2
                d=alert([condition('above',right=dict(type='indicator',config=c,output='value')),condition('above',left=op('volume'),right=val(5))])
                r=client.post('/api/alerts',json={'definition':d});self.assertEqual(r.status_code,201);a=r.json()
                saved=client.get('/api/alerts').json()['alerts'][0];self.assertEqual(saved['definition'],d)
                service=PriceAlerts(settings.application_database,settings.owner)
                def ctx(ps):return dict(identity=dict(source=SOURCE,environment='live_public',product='USD-M',price_type='LAST_PRICE',symbol='BTCUSDT',interval='1m'),transport_state='LIVE',timing=dict(state='FRESH'),quality=dict(state='OK'),stream_epoch='a',rows=rows(ps))
                service.process(a['id'],ctx([100,101,102]),'manual');service.process(a['id'],ctx([100,101,102,105]),'manual');events=client.get('/api/alerts').json()['events'];self.assertEqual(len(events),1);self.assertEqual(events[0]['conditions'],[True,True]);self.assertFalse(settings.execution_database.exists())
                bad=alert([condition('enter')]);self.assertEqual(client.post('/api/alerts',json={'definition':bad}).status_code,422)
                self.assertEqual(client.put('/api/alerts/'+a['id'],json={'definition':d,'revision':1}).status_code,200)
                self.assertEqual(client.put('/api/alerts/'+a['id'],json={'definition':d,'revision':1}).status_code,409)
    def test_snapshot_does_not_follow_later_config_mutation(self):
        from contextlib import closing
        from agentrader.migrations import connect
        with tempfile.TemporaryDirectory() as folder:
            db=Path(folder)/'app.db';migrate(db);s=PriceAlerts(db,'x');c=copy.deepcopy(defaults_v4()[0]);d=alert([condition(left=dict(type='indicator',config=c,output='value'))]);a=s.save(d);c['period']=7
            self.assertEqual(s.list()[0]['definition']['conditions'][0]['left']['config']['period'],20)


class AdditionalConditionTests(unittest.TestCase):
    def test_decimal_exact_volume_band_transitions_and_signed_indicator_values(self):
        r=rows([100,101]);r[0]['exact']['close']='0.100000000000000001';r[1]['exact']['close']='0.100000000000000002'
        d=definition(alert([condition('cross_up',right=val('0.100000000000000002'))]));self.assertTrue(evaluate_all(d,r)[0])
        c=condition('enter',left=op('volume'),right=val(11),upper=val(15));self.assertTrue(evaluate_all(definition(alert([c])),rows([100,101]))[0])
        c=condition('above',left=val('-0.01'),right=val('-0.02'));self.assertTrue(evaluate_all(definition(alert([c])),r)[0])
    def test_bad_payload_shapes_and_static_impossible_bounds_are_422_definitions(self):
        for v in (None,[],{'symbol':[]},alert([condition('move_up',right=val(-1))]),alert([condition('inside',right=val(110),upper=val(100))])):
            with self.assertRaises(AlertError):definition(v)
        d=alert([condition()]);d['interval']=[]
        with self.assertRaises(AlertError):definition(d)
    def test_indicator_crossover_and_live_mixed_any_history_rules(self):
        fast=copy.deepcopy(defaults_v4()[3]);fast['period']=2;slow=copy.deepcopy(defaults_v4()[0]);slow['period']=3
        left=dict(type='indicator',config=fast,output='value');right=dict(type='indicator',config=slow,output='value')
        c=condition('cross_up',left=left,right=right)
        self.assertTrue(evaluate_all(definition(alert([c])),rows([106,104,102,100,110,114]))[0])
    def test_fib_and_legacy_channel_are_numeric_operands_and_display_family_rejected(self):
        sample=rows([100,101,102]);g=dict(kind='fibonacci',symbol='BTCUSDT',price_source='LAST_PRICE',label='Fib',anchors=[dict(time=T,price='100'),dict(time=T+120,price='200')]);o=dict(type='drawing',geometry=g,output='value',ratio='0.5');self.assertEqual(values(o,sample,'1m','BTCUSDT')[-1],Decimal(150));definition(alert([condition(right=o)]))
        g=dict(kind='parallel_channel',schema='chart-channel/1',symbol='BTCUSDT',price_source='LAST_PRICE',label='Channel',anchors=[dict(time=T,price='100'),dict(time=T+120,price='120'),dict(time=T,price='110')]);o=dict(type='drawing',geometry=g,output='upper',ratio=None)
        definition(alert([condition(right=o)]));self.assertEqual(values(o,sample,'1m','BTCUSDT')[-1],Decimal(130))


class WarmupReadinessTests(unittest.TestCase):
    def test_calculation_waiting_survives_heartbeat_without_false_ready(self):
        with tempfile.TemporaryDirectory() as folder:
            db=Path(folder)/'app.db';migrate(db);s=PriceAlerts(db,'x');c=defaults_v4()[2];a=s.save(alert([condition(left=dict(type='indicator',config=c,output='value'))]))
            ctx=dict(identity=dict(source=SOURCE,environment='live_public',product='USD-M',price_type='LAST_PRICE',symbol='BTCUSDT',interval='1m'),transport_state='LIVE',timing=dict(state='FRESH'),quality=dict(state='OK'),stream_epoch='a',rows=rows([100,101]))
            s.process(a['id'],ctx,'boot');self.assertEqual(s.list()[0]['readiness'],'WAITING_CALCULATION');s.process(a['id'],ctx,'boot');self.assertEqual(s.list()[0]['readiness'],'WAITING_CALCULATION');self.assertEqual(s.events(),[])
