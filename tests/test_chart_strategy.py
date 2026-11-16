"""Runtime strategy: durable intent, closed-only provenance and restart with real HTTP."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile,unittest
from unittest.mock import patch
from agentrader.integration.chart_bot import ChartBot,BotError
from agentrader.integration.chart_strategy import DrawingStrategy
from scripts.integration.chart_bot_fixture import ChartBotFixture

class DrawingStrategyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.fixture=ChartBotFixture().start()
    @classmethod
    def tearDownClass(cls):cls.fixture.close()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.folder=Path(self.temp.name)
        import uuid
        self.workspace='strategy-'+uuid.uuid4().hex[:10]
    def bot(self):return ChartBot(self.fixture.base,self.fixture.bot_token,bot_id='alpha',strategy_id='synthetic',workspace_id=self.workspace,journal=self.folder/'bot.db')
    def strategy(self,bot=None):return DrawingStrategy(bot or self.bot(),self.folder/'state.json',interval='15m')
    def test_real_http_closed_indicator_note_exact_query_and_restart_no_duplicate(self):
        result=self.strategy().step();self.assertEqual(result['state'],'APPLIED')
        self.assertFalse(result['indicator']['open_candle_used']);self.assertEqual(result['indicator']['effective_time'],result['bar_time'])
        item=self.bot().get(result['drawing_id']);self.assertEqual(item['linked_note']['text'],result['note'])
        self.assertEqual(self.strategy().step()['state'],'NO_CHANGE');self.assertEqual(len(self.bot().find_own('BTCUSDT','15m')),1)
    def test_stale_stops_even_pending_recovery_without_writes(self):
        bot=self.bot();strategy=self.strategy(bot);fresh=bot.snapshot('BTCUSDT','15m');fresh['derived']['readiness']['state']='STALE'
        with patch.object(bot,'snapshot',return_value=fresh),patch.object(bot,'create',side_effect=AssertionError('write')):
            self.assertEqual(strategy.step()['state'],'PAUSED')
        self.assertFalse(strategy.path.exists())
    def test_committed_create_lost_response_recovers_once(self):
        bot=self.bot();real=bot.http
        class Drop:
            def request(self,method,path,body=None):
                value=real.request(method,path,body)
                if method=='POST' and '/drawings?' in path:raise BotError('CHART_TRANSPORT_UNAVAILABLE',pending=True)
                return value
        bot._transport=Drop();bot.attempts=1
        with self.assertRaises(BotError):self.strategy(bot).step()
        result=self.strategy().step();self.assertEqual(result['state'],'APPLIED');self.assertEqual(len(self.bot().find_own('BTCUSDT','15m')),1)
    def test_source_change_and_configuration_change_do_not_choose_price(self):
        bot=self.bot();fresh=bot.snapshot('BTCUSDT','15m')
        fresh['indicators']['indicators'][0]['period']=21
        with patch.object(bot,'snapshot',return_value=fresh),self.assertRaisesRegex(BotError,'STRATEGY_CONFIGURATION_CHANGED'):self.strategy(bot).step()
        fresh['derived']['readiness']['proof']['state']='BLOCKED'
        with patch.object(bot,'snapshot',return_value=fresh):self.assertEqual(self.strategy(bot).step()['state'],'PAUSED')
    def test_state_is_scoped_and_not_adapter_database(self):
        bot=self.bot()
        with self.assertRaisesRegex(BotError,'STRATEGY_STATE_MUST_BE_SEPARATE'):DrawingStrategy(bot,bot.journal.path)
        self.strategy(bot).step()
        with self.assertRaisesRegex(BotError,'STRATEGY_STATE_SCOPE_MISMATCH'):DrawingStrategy(bot,self.folder/'state.json',symbol='ETHUSDT',interval='15m').step()
    def test_pause_after_committed_create_resumes_same_pending_intent(self):
        bot=self.bot();strategy=self.strategy(bot);original=bot.snapshot;count=[0]
        def snapshot(*args,**kwargs):
            result=original(*args,**kwargs);count[0]+=1
            if count[0]==3:result['derived']['readiness']['state']='STALE'
            return result
        with patch.object(bot,'snapshot',side_effect=snapshot):self.assertEqual(strategy.step()['state'],'PAUSED')
        before=strategy.path.read_bytes();stale=original('BTCUSDT','15m');stale['derived']['readiness']['state']='STALE'
        with patch.object(bot,'snapshot',return_value=stale):self.assertEqual(strategy.step()['state'],'PAUSED')
        self.assertEqual(strategy.path.read_bytes(),before)
        result=self.strategy().step();self.assertEqual(result['state'],'APPLIED');self.assertEqual(len(bot.find_own('BTCUSDT','15m')),1)
    def test_concurrent_writer_fails_before_http(self):
        from agentrader.shared.locking import execution_lock,ExecutionBusy
        bot=self.bot();strategy=self.strategy(bot)
        with execution_lock(strategy.path.with_suffix('.json.lock')),patch.object(bot,'snapshot',side_effect=AssertionError('HTTP')):
            with self.assertRaises(ExecutionBusy):strategy.step()

if __name__=='__main__':unittest.main()
