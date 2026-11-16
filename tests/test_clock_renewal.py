import copy, threading, unittest
from types import SimpleNamespace
from unittest.mock import Mock
from agentrader.chart.chart_clock import measure_time, StreamTiming
from agentrader.chart.chart_market import candle
from agentrader.shared.market_feed import FeedState, SharedFeed, FeedUnavailable

BASE=1800000000000

class RenewalTests(unittest.TestCase):
    def setUp(self):
        self.elapsed=0.;self.wall_offset=0.
        self.wall=lambda:100.+self.elapsed+self.wall_offset
        self.mono=lambda:10.+self.elapsed
        self.client=Mock();self.client.get.side_effect=lambda *_:{'serverTime':BASE+1000+int(self.elapsed*1000)}
        self.feed=SharedFeed(SimpleNamespace(history=Mock()),'BTCUSDT','1m',clock=self.wall,monotonic=self.mono,clock_refresher=self.sample)
        self.state=self.feed.state;self.state.seed(self.history());self.advance(1)

    def sample(self):return measure_time(self.client,self.wall,self.mono)[1]
    def row(self,t,closed):
        raw=[t,'100','101','99','100','1',t+59999,'100',1,'1','100','0']
        return candle(raw,t+60000 if closed else t+1000)
    def history(self):
        stamp=BASE+1000+int(self.elapsed*1000);tail=(stamp//60000)*60000
        return dict(clock_sample=self.sample(),server_time=stamp,market={},quality=dict(state='OK',missing_bars=0),candles=[self.row(t,t+59999<stamp) for t in range(BASE-60000,tail+1,60000)])
    def advance(self,second):
        self.elapsed=float(second);stamp=BASE+1000+second*1000;t=(stamp-1)//60000*60000;volume=str((stamp-t)//1000)
        return self.state.apply(dict(e='kline',E=stamp,s='BTCUSDT',k=dict(s='BTCUSDT',i='1m',t=t,T=t+59999,x=stamp%60000==0,o='100',h='101',l='99',c='100',v=volume,q=str(int(volume)*100),n=int(volume),V=volume,Q=str(int(volume)*100))))

    def test_two_renewals_keep_epoch_and_all_eleven_closes_without_resync(self):
        epoch=self.state.stream_epoch;seen=set()
        for sec in range(2,661):
            self.advance(sec)
            if self.state.last_close:seen.add(self.state.last_close['time'])
            if sec in (240,480):
                before=copy.deepcopy((self.state.rows,self.state.sequence,self.state.generation,self.state.data_revision,self.state.last_event,self.state.last_receipt_mono,self.state.last_close))
                self.assertTrue(self.feed.refresh_clock_once())
                self.assertEqual(before,(self.state.rows,self.state.sequence,self.state.generation,self.state.data_revision,self.state.last_event,self.state.last_receipt_mono,self.state.last_close))
        self.assertEqual(self.state.stream_epoch,epoch);self.assertEqual(len(seen),11)
        self.assertEqual(sorted(seen),list(range(BASE//1000,BASE//1000+660,60)))
        self.assertEqual(self.state.clock_renewals,2);self.feed.market.history.assert_not_called()

    def test_blocking_clock_read_does_not_block_websocket_close_processing(self):
        for sec in range(2,241):self.advance(sec)
        entered,release=threading.Event(),threading.Event();result=[]
        def delayed():entered.set();release.wait(5);return self.sample()
        self.feed.clock_refresher=delayed
        thread=threading.Thread(target=lambda:result.append(self.feed.refresh_clock_once()));thread.start()
        try:
            self.assertTrue(entered.wait(2))
            for sec in range(241,300):self.advance(sec)
            self.assertEqual(self.state.last_close['time'],BASE//1000+240)
        finally:release.set();thread.join(3)
        self.assertEqual(result,[True]);self.assertFalse(thread.is_alive())

    def test_failed_or_incompatible_sample_does_not_extend_trust(self):
        for sec in range(2,241):self.advance(sec)
        old=self.state.timing.sample
        self.feed.clock_refresher=lambda:dict(schema='chart-clock-sample/1',state='MEASURED',sample_id='foreign')
        self.assertFalse(self.feed.refresh_clock_once());self.assertIs(self.state.timing.sample,old)
        self.client.get.side_effect=lambda *_:{'serverTime':BASE+9999999}
        self.feed.clock_refresher=self.sample
        self.assertFalse(self.feed.refresh_clock_once());self.assertIs(self.state.timing.sample,old)
        self.elapsed=301
        self.assertEqual(self.state.timing.proof()['reason'],'CLOCK_UNTRUSTED')

    def test_renewal_cannot_clear_wall_jump_or_resnapshot_barrier(self):
        self.wall_offset=1
        self.assertFalse(self.state.renew_clock(self.sample(),self.state.stream_epoch))
        self.wall_offset=0
        self.assertEqual(self.state.timing.proof()['reason'],'SNAPSHOT_REQUIRED')
        self.assertFalse(self.state.renew_clock(self.sample(),self.state.stream_epoch))

    def test_delayed_renewal_for_old_epoch_is_rejected(self):
        for sec in range(2,241):self.advance(sec)
        epoch=self.state.stream_epoch;sample=self.sample();self.state.seed(self.history())
        self.assertFalse(self.state.renew_clock(sample,epoch));self.assertEqual(self.state.clock_renewals,0)

    def test_rest_recovered_closes_are_audited_once_and_never_live_signals(self):
        for sec in range(2,61):self.advance(sec)
        old_close=copy.deepcopy(self.state.last_close);self.elapsed=180
        self.state.seed(self.history())
        recovered=self.state.packet()['recovery_events']
        self.assertEqual([r['time'] for r in recovered],[BASE//1000+60,BASE//1000+120])
        self.assertTrue(all(r['signal_eligible'] is False and r['origin']=='REST_RESYNC' for r in recovered))
        self.assertEqual(self.state.last_close,old_close)
        self.state.seed(self.history());self.assertEqual(len(self.state.recovery_events),2)

    def test_shutdown_discards_pending_clock_result(self):
        for sec in range(2,241):self.advance(sec)
        self.feed.clock_refresher=lambda:(self.feed.stop_event.set() or self.sample())
        self.assertFalse(self.feed.refresh_clock_once());self.assertEqual(self.state.clock_renewals,0)


    def test_shadow_close_boundary_wait_preserves_checkpoint_then_emits_once(self):
        import sys
        from pathlib import Path
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
        from scripts.chart.run_chart_p7 import Harness
        from agentrader.integration.shadow_tracking import ShadowTracking
        from agentrader.shared.market_environment import SOURCE,ENVIRONMENT
        h=Harness();self.addCleanup(h.close)
        elapsed=[0.];wall=lambda:1000.+elapsed[0];mono=lambda:1000.+elapsed[0]
        original=h.context(0);tail=original['rows'][-1]['time']*1000;origin=tail+3000
        client=Mock();client.get.side_effect=lambda *_:{'serverTime':origin+int(elapsed[0]*1000)}
        sample=lambda:measure_time(client,wall,mono)[1]
        state=FeedState('BTCUSDT','15m',wall,mono)
        state.seed(dict(server_time=origin,clock_sample=sample(),market=original['market'],quality=original['quality'],candles=original['rows']))
        def frame(sec):
            elapsed[0]=sec;stamp=origin+sec*1000;t=tail if sec<=897 else tail+900000;closing=sec==897;price='99.8' if sec>=897 else '98';high='100' if sec>=897 else '98.2';volume=str(11+sec if sec<=897 else 11)
            return dict(e='kline',E=stamp,s='BTCUSDT',k=dict(s='BTCUSDT',i='15m',t=t,T=t+899999,x=closing,o='98' if sec<=897 else '99.8',h=high,l='97.8' if sec<=897 else '99.6',c=price,v=volume,q=str(int(volume)*100),n=int(volume),V=volume,Q=str(int(volume)*100)))
        def context():return dict(identity=dict(source=SOURCE,environment=ENVIRONMENT,product='USD-M',price_type='LAST_PRICE',symbol='BTCUSDT',interval='15m'),transport_state=state.state,rows=copy.deepcopy(state.rows),market=copy.deepcopy(state.market),quality=copy.deepcopy(state.quality),stream_epoch=state.stream_epoch,generation=state.generation,data_revision=state.data_revision,data_proof=state.evidence.view(),timing=state.timing.proof())
        shadow=ShadowTracking(h.db,'fixture',clock=wall,monotonic=mono)
        shadow.command('main','binding',1,h.b['definition_hash'],'start');run=shadow.runs()[0]
        state.apply(frame(1));self.assertEqual(shadow.process(run,context(),'boot')['reason'],'SEEDED_NO_HISTORICAL_SIGNAL')
        epoch=state.stream_epoch
        for sec in range(2,898):
            state.apply(frame(sec))
            if sec in (240,480,720):self.assertTrue(state.renew_clock(sample(),epoch))
        before=shadow.status('main','binding')['run']['checkpoint']
        waiting=shadow.process(run,context(),'boot')
        self.assertEqual(waiting['reason'],'CLOSED_TIME_UNPROVEN')
        self.assertEqual(before,shadow.status('main','binding')['run']['checkpoint'])
        state.apply(frame(898));self.assertTrue(shadow.process(run,context(),'boot')['created'])
        self.assertFalse(shadow.process(run,context(),'boot')['created'])
        self.assertEqual(len(shadow.status('main','binding')['events']),1)
        self.assertEqual(state.clock_renewals,3);self.assertEqual(state.stream_epoch,epoch)
