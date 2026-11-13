import copy
import time
import unittest

from agentrader.exchange import ExchangeError
from agentrader.isolated_margin import IsolatedMarginCommands, PATH
from agentrader.risk import number
from agentrader.v2_runner import V2Runner
import test_v2_runner as fixtures


class ManagedExchange(fixtures.ExecutionExchange):
    def __init__(self):
        super().__init__();self.wallet='20';self.history=[];self.margin_lost=False

    def get(self,path,params=None):
        if path.endswith('/symbolConfig'):
            return [{'symbol':'BTCUSDT','leverage':20,'marginType':'ISOLATED'}]
        if path.endswith('/accountConfig'):return {'canTrade':True,'multiAssetsMargin':False}
        if path.endswith('/account'):return {'assets':[{'asset':'USDT','availableBalance':'5000'}]}
        if path.endswith('/positionRisk'):
            return [{'symbol':'BTCUSDT','positionSide':'BOTH','positionAmt':str(self.amount),
                     'entryPrice':'80000','isolatedWallet':self.wallet}]
        if path==PATH+'/history':return copy.deepcopy(self.history)
        if path.endswith('/leverageBracket'):
            return [{'symbol':'BTCUSDT','brackets':[{'notionalFloor':0,'notionalCap':10000,'maintMarginRatio':'.004','cum':'0'}]}]
        return super().get(path,params)

    def request(self,method,path,params):
        if path!=PATH:return super().request(method,path,params)
        self.calls.append((method,path,dict(params)))
        self.wallet=str(number(self.wallet)+number(params['amount'])*(1 if params['type']==1 else -1))
        self.history.append(dict(symbol='BTCUSDT',positionSide='BOTH',asset='USDT',deltaType='USER_ADJUST',
                                 type=params['type'],amount=params['amount'],time=int(time.time()*1000)))
        if self.margin_lost:raise ExchangeError('lost',delivery_status='UNKNOWN')
        return dict(code=200,type=params['type'],amount=params['amount'])


class ManagedMarginTests(unittest.TestCase):
    setUp=fixtures.V2RunnerTests.setUp
    tearDown=fixtures.V2RunnerTests.tearDown
    authorize=fixtures.V2RunnerTests.authorize
    open=fixtures.V2RunnerTests.open

    def start(self):
        self.x=ManagedExchange();self.plan['execution']['margin_mode']='ISOLATED'
        self.snap['settings']['marginType']='ISOLATED'
        self.runner=V2Runner(self.service,self.x,self.runner.limits)
        self.authorize();sid=self.open()['session_id']
        self.margin=IsolatedMarginCommands(self.x,self.store,'local:test',session_id=sid)
        return sid

    def test_managed_add_is_bound_to_plan_and_applied_once(self):
        sid=self.start();before=len(self.x.calls)
        prepared=self.margin.prepare('BTCUSDT','BOTH','ADD','10')
        self.assertEqual(len(self.x.calls),before)
        self.assertEqual(self.margin.apply(prepared['command_id'],prepared['digest'])['state'],'APPLIED')
        self.assertEqual(number(self.x.wallet),30)
        self.margin.apply(prepared['command_id'],prepared['digest'])
        self.assertEqual(len(self.x.calls),before+1)
        self.assertEqual(self.runner.manage(sid,False)['state'],'MANAGING')

    def test_unbound_margin_command_cannot_touch_bot_position(self):
        self.start();before=len(self.x.calls)
        with self.assertRaises(ValueError):
            IsolatedMarginCommands(self.x,self.store,'local:test').prepare('BTCUSDT','BOTH','ADD','10')
        self.assertEqual(len(self.x.calls),before)

    def test_managed_remove_requires_native_safe_stop(self):
        self.start()
        prepared=self.margin.prepare('BTCUSDT','BOTH','REMOVE','5')
        self.assertEqual(self.margin.apply(prepared['command_id'],prepared['digest'])['state'],'APPLIED')
        self.assertEqual(number(self.x.wallet),15)

    def test_lost_managed_add_is_unknown_and_not_repeated(self):
        self.start();prepared=self.margin.prepare('BTCUSDT','BOTH','ADD','10');self.x.margin_lost=True
        self.assertEqual(self.margin.apply(prepared['command_id'],prepared['digest'])['state'],'UNKNOWN')
        count=len(self.x.calls)
        service=IsolatedMarginCommands(self.x,self.store,'local:test')
        self.assertEqual(service.apply(prepared['command_id'],prepared['digest'])['state'],'UNKNOWN')
        self.assertEqual(len(self.x.calls),count)
        self.assertTrue(self.store.unresolved_account_command())

    def test_changed_position_or_wrong_session_cannot_apply(self):
        sid=self.start();prepared=self.margin.prepare('BTCUSDT','BOTH','ADD','10')
        self.x.amount+=number('.001');count=len(self.x.calls)
        with self.assertRaises(ValueError):self.margin.apply(prepared['command_id'],prepared['digest'])
        self.assertEqual(len(self.x.calls),count)
        with self.assertRaises(ValueError):
            IsolatedMarginCommands(self.x,self.store,'local:test',session_id='other').prepare('BTCUSDT','BOTH','ADD','10')
