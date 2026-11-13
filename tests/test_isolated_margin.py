import copy
import tempfile
import unittest
from pathlib import Path

from agentrader.account_commands import AccountCommands
from agentrader.config import Config
from agentrader.exchange import ExchangeError
from agentrader.isolated_margin import IsolatedMarginCommands,PATH
from agentrader.risk import number
from agentrader.state import StateStore


class MarginExchange:
    config=Config('demo-key','not-a-real-secret')
    offset_ms=0
    def __init__(self):
        self.wallet='20';self.quantity='.001';self.entry='75000';self.available='1000'
        self.margin='ISOLATED';self.dual=False;self.ps='BOTH';self.multi=False;self.rows=[];self.calls=[]
        self.lost=False;self.reject=False;self.hide_history=False;self.malformed=False;self.protect=True
    def sync_time(self):pass
    def get(self,path,params=None):
        if path.endswith('accountConfig'):return {'canTrade':True,'multiAssetsMargin':self.multi}
        if path.endswith('dual'):return {'dualSidePosition':self.dual}
        if path.endswith('symbolConfig'):return [{'symbol':'BTCUSDT','marginType':self.margin,'leverage':20}]
        if path.endswith('positionRisk'):return [{'symbol':'BTCUSDT','positionSide':self.ps,'positionAmt':self.quantity,'entryPrice':self.entry,'isolatedWallet':self.wallet}]
        if path.endswith('openOrders'):return []
        if path.endswith('account'):return {'assets':[{'asset':'USDT','availableBalance':self.available}]}
        if path.endswith('premiumIndex'):return {'symbol':'BTCUSDT','markPrice':'75000','time':1000000}
        if path.endswith('leverageBracket'):return [{'symbol':'BTCUSDT','brackets':[{'notionalFloor':0,'notionalCap':10000,'maintMarginRatio':'.004','cum':0}]}]
        if path.endswith('openAlgoOrders'):
            if not self.protect:return []
            return [{'symbol':'BTCUSDT','positionSide':self.ps,'side':'SELL'if number(self.quantity)>0 else'BUY','algoStatus':'NEW',
                     'orderType':'STOP_MARKET','closePosition':True,'workingType':'MARK_PRICE','triggerPrice':'74000'if number(self.quantity)>0 else'76000'}]
        if path==PATH+'/history':return []if self.hide_history else copy.deepcopy(self.rows)
        raise AssertionError(path)
    def request(self,method,path,params):
        self.calls.append((method,path,dict(params)))
        if self.reject:raise ExchangeError('reject',-2019,400,delivery_status='REJECTED')
        self.wallet=str(number(self.wallet)+number(params['amount'])*(1 if params['type']==1 else -1))
        self.rows.append({'symbol':'BTCUSDT','positionSide':self.ps,'asset':'USDT','deltaType':'USER_ADJUST',
                          'type':params['type'],'amount':params['amount'],'time':1000000})
        if self.lost:raise ExchangeError('lost',delivery_status='UNKNOWN')
        return {'code':200,'type':params['type'],'amount':'broken'if self.malformed else params['amount']}


class IsolatedMarginTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'state.db'
        self.store=StateStore(self.path);self.x=MarginExchange()
        self.service=IsolatedMarginCommands(self.x,self.store,'owner',clock=lambda:1000)
    def tearDown(self):self.store.close();self.temp.cleanup()
    def prepare(self,action='ADD',amount='10'):return self.service.prepare('BTCUSDT',self.x.ps,action,amount)
    def apply(self,p):return self.service.apply(p['command_id'],p['digest'])

    def test_prepare_is_read_only_and_digest_bound(self):
        p=self.prepare();self.assertEqual(self.x.calls,[])
        with self.assertRaises(ValueError):self.service.apply(p['command_id'],'wrong')
        self.assertEqual(self.x.calls,[])
    def test_add_is_acknowledged_and_history_verified_once(self):
        p=self.prepare();self.assertEqual(self.apply(p)['state'],'APPLIED')
        self.assertEqual(number(self.x.wallet),30)
        self.apply(p);self.assertEqual(len(self.x.calls),1)
    def test_lost_response_remains_unknown_even_with_matching_history(self):
        p=self.prepare();self.x.lost=True
        self.assertEqual(self.apply(p)['state'],'UNKNOWN')
        result=self.service.reconcile(p['command_id'])
        self.assertEqual(result['state'],'UNKNOWN');self.assertEqual(result['result']['matching_history_count'],1)
        self.apply(p);self.assertEqual(len(self.x.calls),1)
        self.assertTrue(self.store.unresolved_account_command())
    def test_restart_never_reposts_uncertain_additive_command(self):
        p=self.prepare();self.x.lost=True;self.apply(p)
        self.store.close();self.store=StateStore(self.path)
        self.service=IsolatedMarginCommands(self.x,self.store,'owner',clock=lambda:1000)
        self.assertEqual(self.apply(p)['state'],'UNKNOWN');self.assertEqual(len(self.x.calls),1)
    def test_delayed_history_preserves_ack_and_resolves_by_read(self):
        p=self.prepare();self.x.hide_history=True
        self.assertEqual(self.apply(p)['state'],'ACKNOWLEDGED')
        self.x.hide_history=False
        self.assertEqual(self.service.reconcile(p['command_id'])['state'],'APPLIED')
        self.assertEqual(len(self.x.calls),1)
    def test_remove_requires_verified_stop_and_liquidation_buffer(self):
        p=self.prepare('REMOVE');self.assertEqual(self.apply(p)['state'],'APPLIED')
        self.assertEqual(number(self.x.wallet),10)
    def test_removal_without_stop_or_with_unsafe_margin_never_posts(self):
        self.x.protect=False
        with self.assertRaises(ValueError):self.prepare('REMOVE')
        self.x.protect=True
        with self.assertRaises(ValueError):self.prepare('REMOVE','19')
        self.assertEqual(self.x.calls,[])
    def test_short_hedge_margin_targets_correct_position_side(self):
        self.x.quantity='-.001';self.x.ps='SHORT';self.x.dual=True
        p=self.prepare('REMOVE');self.assertEqual(self.apply(p)['state'],'APPLIED')
        self.assertEqual(self.x.calls[0][2]['positionSide'],'SHORT')
    def test_cross_or_multi_asset_mode_is_rejected(self):
        self.x.margin='CROSSED'
        with self.assertRaises(ValueError):self.prepare()
        self.x.margin='ISOLATED';self.x.multi=True
        with self.assertRaises(ValueError):self.prepare()
    def test_changed_wallet_or_position_does_not_mutate(self):
        p=self.prepare();self.x.wallet='19'
        with self.assertRaises(ValueError):self.apply(p)
        self.assertEqual(self.x.calls,[])
    def test_history_changed_before_apply_is_rejected(self):
        p=self.prepare();self.x.rows.append({'symbol':'BTCUSDT','positionSide':'BOTH','asset':'USDT','deltaType':'USER_ADJUST','type':1,'amount':'1','time':1000000})
        with self.assertRaises(ValueError):self.apply(p)
        self.assertEqual(self.x.calls,[])
    def test_invalid_amount_and_insufficient_balance_never_post(self):
        for amount in ('0','-1','NaN','broken','1001'):
            with self.assertRaises(ValueError):self.prepare(amount=amount)
        self.assertEqual(self.x.calls,[])
    def test_definitive_rejection_is_terminal_not_retried(self):
        p=self.prepare();self.x.reject=True
        self.assertEqual(self.apply(p)['state'],'REJECTED');self.apply(p)
        self.assertEqual(len(self.x.calls),1)
    def test_malformed_success_response_remains_unknown(self):
        p=self.prepare();self.x.malformed=True
        self.assertEqual(self.apply(p)['state'],'UNKNOWN')
        self.assertEqual(len(self.x.calls),1)
    def test_expired_or_other_account_command_never_posts(self):
        p=self.prepare();self.service.clock=lambda:p['expires_at']+1
        self.assertEqual(self.apply(p)['state'],'EXPIRED')
        self.service.clock=lambda:1000;p=self.prepare();self.x.config=Config('other','secret')
        self.service=IsolatedMarginCommands(self.x,self.store,'owner',clock=lambda:1000)
        with self.assertRaises(ValueError):self.apply(p)
        self.assertEqual(self.x.calls,[])
    def test_uncertain_margin_blocks_other_account_settings(self):
        p=self.prepare();self.x.lost=True;self.apply(p)
        settings=AccountCommands(self.x,self.store,'owner');other=settings.prepare('FEE_BURN',True)
        with self.assertRaises(ValueError):settings.apply(other['command_id'],other['digest'])
        self.assertEqual(len(self.x.calls),1)
    def test_active_bot_session_prevents_independent_margin_change(self):
        self.store.save_session({'id':'active','active':True,'status':'PROTECTED'})
        with self.assertRaises(ValueError):self.prepare()
        self.assertEqual(self.x.calls,[])

    def test_signed_reduce_history_still_requires_wallet_and_post_ack(self):
        p=self.prepare('REMOVE');original=self.x.request
        def request(*args):
            reply=original(*args);self.x.rows[-1]['amount']='-10';reply['amount']='-10';return reply
        from unittest.mock import patch
        with patch.object(self.x,'request',side_effect=request):self.assertEqual(self.apply(p)['state'],'APPLIED')
        self.assertEqual(number(self.x.wallet),10)
