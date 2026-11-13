import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agentrader.account_commands import AccountCommands
from agentrader.config import Config
from agentrader.exchange import ExchangeError
from agentrader.state import StateStore


class SettingsExchange:
    def __init__(self):
        self.config=Config('key','secret');self.calls=[];self.leverage=10
        self.margin='CROSSED';self.dual=False;self.multi=False;self.burn=False
        self.positions=[];self.lose_response=False;self.reject=False
    def sync_time(self):pass
    def get(self,path,params=None):
        if path.endswith('positionRisk'):return self.positions
        if path.endswith('openOrders') or path.endswith('openAlgoOrders'):return []
        if path.endswith('symbolConfig'):return [{'symbol':'BTCUSDT','leverage':self.leverage,'marginType':self.margin}]
        if path.endswith('leverageBracket'):return [{'symbol':'BTCUSDT','brackets':[{'initialLeverage':20}]}]
        if path.endswith('dual'):return {'dualSidePosition':self.dual}
        if path.endswith('multiAssetsMargin'):return {'multiAssetsMargin':self.multi}
        if path.endswith('feeBurn'):return {'feeBurn':self.burn}
        raise AssertionError(path)
    def request(self,method,path,params):
        self.calls.append((method,path,params))
        if self.reject:raise ExchangeError('rejected',-2019,400,delivery_status='REJECTED')
        if path.endswith('leverage'):self.leverage=params['leverage']
        elif path.endswith('marginType'):self.margin=params['marginType']
        elif path.endswith('dual'):self.dual=params['dualSidePosition']=='true'
        elif path.endswith('multiAssetsMargin'):self.multi=params['multiAssetsMargin']=='true'
        elif path.endswith('feeBurn'):self.burn=params['feeBurn']=='true'
        else:raise AssertionError(path)
        if self.lose_response:raise ExchangeError('lost',delivery_status='UNKNOWN')
        return {}


class AccountCommandTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory(dir=Path.cwd());self.path=Path(self.folder.name)/'state.sqlite3'
        self.store=StateStore(self.path);self.x=SettingsExchange();self.service=AccountCommands(self.x,self.store,'owner')
    def tearDown(self):self.store.close();self.folder.cleanup()
    def command(self,kind='LEVERAGE',value=20,symbol='BTCUSDT'):
        return self.service.prepare(kind,value,symbol)
    def apply(self,p,**kwargs):return self.service.apply(p['command_id'],p['digest'],**kwargs)

    def test_prepare_is_not_a_mutation_or_approval(self):
        p=self.command();self.assertEqual(p['state'],'PREPARED');self.assertEqual(self.x.calls,[])
        with self.assertRaises(ValueError):self.service.apply(p['command_id'],'wrong')
        self.assertEqual(self.x.calls,[])

    def test_exact_leverage_change_is_queried_and_not_repeated(self):
        p=self.command();self.assertEqual(self.apply(p)['state'],'APPLIED')
        self.apply(p);self.assertEqual(len(self.x.calls),1)

    def test_noop_current_setting_never_posts(self):
        p=self.command(value=10);self.assertEqual(self.apply(p)['state'],'APPLIED')
        self.assertEqual(self.x.calls,[])

    def test_lost_response_is_resolved_by_state_read_without_repost(self):
        self.x.lose_response=True;p=self.command()
        self.assertEqual(self.apply(p)['state'],'APPLIED')
        self.store.close();self.store=StateStore(self.path)
        restarted=AccountCommands(self.x,self.store,'owner')
        restarted.apply(p['command_id'],p['digest'])
        self.assertEqual(len(self.x.calls),1)

    def test_pending_unknown_command_blocks_new_configuration(self):
        p=self.command();self.service.set_state(p['command_id'],'UNKNOWN')
        other=self.command(value=15)
        with self.assertRaises(ValueError):self.apply(other)
        self.assertTrue(self.store.unresolved_account_command())
        self.assertEqual(self.x.calls,[])

    def test_open_position_blocks_configuration_even_if_net_hedged(self):
        self.x.positions=[{'positionAmt':'1'},{'positionAmt':'-1'}]
        p=self.command()
        with self.assertRaises(ValueError):self.apply(p)
        self.assertEqual(self.x.calls,[])

    def test_global_mode_change_requires_cross_product_checks(self):
        p=self.command('POSITION_MODE',True,None)
        with self.assertRaises(ValueError):self.apply(p)
        self.assertEqual(self.apply(p,cross_product_flat_verified=True)['state'],'APPLIED')

    def test_symbol_margin_and_fee_preferences(self):
        for kind,value,symbol in [('MARGIN_TYPE','ISOLATED','BTCUSDT'),('FEE_BURN',True,None)]:
            p=self.command(kind,value,symbol)
            self.assertEqual(self.apply(p)['state'],'APPLIED')

    def test_expired_command_does_not_mutate(self):
        p=self.command()
        with patch('agentrader.account_commands.time.time',return_value=p['expires_at']+1):
            self.assertEqual(self.apply(p)['state'],'EXPIRED')
        self.assertEqual(self.x.calls,[])

    def test_different_key_cannot_reuse_command(self):
        p=self.command();self.x.config=Config('different-key','different-secret')
        other=AccountCommands(self.x,self.store,'owner')
        with self.assertRaises(ValueError):other.apply(p['command_id'],p['digest'])

    def test_definitive_rejection_is_not_unknown_or_retried(self):
        self.x.reject=True;p=self.command()
        self.assertEqual(self.apply(p)['state'],'REJECTED')
        self.apply(p);self.assertEqual(len(self.x.calls),1)

    def test_unsupported_leverage_never_posts(self):
        p=self.command(value=100)
        with self.assertRaises(ValueError):self.apply(p)
        self.assertEqual(self.x.calls,[])
