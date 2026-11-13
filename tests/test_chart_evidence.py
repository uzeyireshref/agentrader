import copy
from dataclasses import FrozenInstanceError
import hashlib
import json
from pathlib import Path
import unittest

from agentrader.chart_evidence import snapshot, canonical, require_warmup
from agentrader.chart_market import candle
from agentrader.chart_precision import exact_tick
from agentrader.market_feed import FeedState
from test_chart_feed import START, STEP, row, event


def fixture(count=60):
    rows = [candle(row(START+(i-count+1)*STEP), START+2000) for i in range(count)]
    market = {'symbol':'BTCUSDT','base_asset':'BTC','quote_asset':'USDT','contract_type':'PERPETUAL',
              'tick_size':'0.1','exact':exact_tick('0.1')}
    quality = {'state':'OK','missing_bars':0,'short_history':False}
    return rows, market, quality


def capture(rows, market, quality, epoch='a'*32, generation=1, revision=1):
    return snapshot(rows, market, quality, symbol='BTCUSDT', interval='15m', epoch=epoch,
                    generation=generation, revision=revision)


class ChartEvidenceTests(unittest.TestCase):
    def test_snapshot_is_frozen_and_detached_from_rows_market_quality_and_views(self):
        rows, market, quality = fixture(); evidence = capture(rows,market,quality)
        original=evidence.payload_json; view=evidence.view(); view['state']='changed'
        rows[0]['close']=106.; market['tick_size']='1'; quality['state']='GAP'
        self.assertEqual(evidence.payload_json,original)
        self.assertEqual(evidence.view()['state'],'VERIFIED')
        with self.assertRaises(FrozenInstanceError): evidence.payload_json='changed'
        self.assertEqual(evidence.view()['snapshot_hash'],hashlib.sha256(original.encode()).hexdigest())

    def test_restart_and_reseed_have_distinct_epochs_and_snapshot_barrier(self):
        rows,market,quality=fixture(2)
        history={'candles':rows,'market':market,'quality':quality,'server_time':START+2000}
        one,two=FeedState('BTCUSDT','15m'),FeedState('BTCUSDT','15m')
        one.seed(history);two.seed(history)
        self.assertNotEqual(one.stream_epoch,two.stream_epoch)
        old=one.stream_epoch;old_proof=one.evidence
        one.seed(history)
        self.assertNotEqual(one.stream_epoch,old)
        self.assertEqual(one.packet(one.generation,old)['type'],'snapshot')
        self.assertEqual(one.packet(one.generation,one.stream_epoch)['type'],'update')
        self.assertEqual(old_proof.view()['stream_epoch'],old)
        self.assertIsNone(one.last_close)

    def test_heartbeat_status_and_sequence_changes_do_not_change_data_revision(self):
        rows,market,quality=fixture(2); state=FeedState('BTCUSDT','15m')
        state.seed({'candles':rows,'market':market,'quality':quality,'server_time':START+2000})
        before=state.evidence.view()
        state.status('RECONNECTING');state.packet(state.generation);state.packet(state.generation)
        self.assertGreater(state.sequence,1)
        self.assertEqual(state.evidence.view(),before)
        state.apply(event());accepted=state.evidence.view()
        self.assertGreater(accepted['data_revision'],before['data_revision'])
        self.assertNotEqual(accepted['snapshot_hash'],before['snapshot_hash'])
        self.assertIsNone(state.apply(event()))
        self.assertEqual(state.evidence.view(),accepted)

    def test_actual_grid_gap_blocks_even_when_upstream_quality_claims_ok(self):
        rows,market,quality=fixture();rows.pop(20)
        proof=capture(rows,market,quality).view()
        self.assertEqual(proof['missing_bars'],1)
        self.assertIn('GRID_GAP',proof['blocked_reasons'])
        self.assertEqual(proof['state'],'BLOCKED')

    def test_warmup_requires_explicit_closed_contiguous_history(self):
        rows,market,quality=fixture()
        self.assertEqual(require_warmup(capture(rows,market,quality),50)['state'],'DATA_PROOF_VERIFIED_NOT_ELIGIBILITY')
        for required in (None,0,True,-1):
            self.assertEqual(require_warmup(capture(rows,market,quality),required)['reason'],'WARMUP_REQUIREMENT_UNSPECIFIED')
        self.assertEqual(require_warmup(capture(rows[-2:],market,quality),50)['reason'],'INSUFFICIENT_WARMUP')
        rows.pop(20)
        self.assertLess(capture(rows,market,quality).view()['warmup_available_closed_bars'],50)

    def test_invalid_order_duplicate_buckets_and_closed_flags_do_not_verify(self):
        rows,market,quality=fixture()
        for mutate in ('reverse','duplicate','off_bucket','open_middle'):
            changed=copy.deepcopy(rows)
            if mutate=='reverse':changed.reverse()
            if mutate=='duplicate':changed[1]=copy.deepcopy(changed[0])
            if mutate=='off_bucket':changed[0]['time']+=1
            if mutate=='open_middle':changed[10]['closed']=False
            with self.subTest(mutate=mutate):self.assertEqual(capture(changed,market,quality).view()['state'],'BLOCKED')

    def test_missing_precision_identity_and_quality_are_explicitly_blocked(self):
        rows,market,quality=fixture()
        rows[0].pop('exact')
        self.assertIn('PRICE_PRECISION_UNPROVEN',capture(rows,market,quality).view()['blocked_reasons'])
        market['symbol']='ETHUSDT';quality['state']='UNKNOWN'
        reasons=capture(rows,market,quality).view()['blocked_reasons']
        self.assertIn('MARKET_IDENTITY_UNPROVEN',reasons)
        self.assertIn('QUALITY_UNPROVEN',reasons)

    def test_hash_binds_exact_subfloat_price_grid_context_and_quality(self):
        rows,market,quality=fixture();original=capture(rows,market,quality).view()
        changed=copy.deepcopy(rows);changed[-1]['exact']['close']='105.000000000000000000001'
        self.assertNotEqual(capture(changed,market,quality).view()['snapshot_hash'],original['snapshot_hash'])
        self.assertNotEqual(capture(rows,market,quality,epoch='b'*32).view()['snapshot_hash'],original['snapshot_hash'])
        self.assertNotEqual(capture(rows,market,dict(quality,short_history=True)).view()['snapshot_hash'],original['snapshot_hash'])
        self.assertEqual(capture(rows,market,quality).view()['grid_hash'],original['grid_hash'])

    def test_saved_cross_language_fixture_matches_independent_hashlib(self):
        data=json.loads((Path(__file__).resolve().parents[1]/'frontend/tests/fixtures/data-evidence.json').read_text())
        for case in data['cases']:
            evidence=capture(case['rows'],case['market'],case['quality'],epoch=case['proof']['stream_epoch'],
                             generation=case['proof']['generation'],revision=case['proof']['data_revision'])
            self.assertEqual(evidence.view(),case['proof'])
            self.assertEqual(hashlib.sha256(canonical(evidence.payload()).encode()).hexdigest(),case['proof']['snapshot_hash'])

    def test_real_websocket_restart_sends_snapshot_even_when_counters_match(self):
        import tempfile
        from types import SimpleNamespace
        from unittest.mock import Mock
        from fastapi.testclient import TestClient
        from agentrader.api.app import create_app
        from agentrader.application.settings import WebSettings
        rows,market,quality=fixture(2)
        history={'candles':rows,'market':market,'quality':quality,'server_time':START+2000}
        one,two=FeedState('BTCUSDT','15m'),FeedState('BTCUSDT','15m')
        one.seed(history);two.seed(history)
        self.assertEqual((one.generation,one.sequence),(two.generation,two.sequence))
        feed=SimpleNamespace(state=one);hub=Mock();hub.acquire.return_value=feed
        with tempfile.TemporaryDirectory() as folder:
            settings=WebSettings(Path(folder)/'app.db',Path(folder)/'execution.db',market_database=Path(folder)/'market.db')
            with TestClient(create_app(settings,market=Mock(),hub=hub),base_url='http://127.0.0.1') as client:
                with client.websocket_connect('ws://127.0.0.1/api/market-stream?symbol=BTCUSDT&interval=15m',headers={'origin':'http://127.0.0.1'}) as ws:
                    initial=ws.receive_json();feed.state=two;restarted=ws.receive_json()
                    self.assertNotEqual(initial['stream_epoch'],restarted['stream_epoch'])
                    self.assertEqual(restarted['type'],'snapshot')
                    self.assertEqual(restarted['data_proof'],two.evidence.view())
                    self.assertEqual(initial['generation'],restarted['generation'])
                    ws.send_text('finish-test')
                    self.assertEqual(ws.receive()['type'],'websocket.close')
            hub.release.assert_called_once_with(feed)
            self.assertFalse(settings.execution_database.exists())

    def test_idle_feed_retirement_compares_only_monotonic_times(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        from agentrader.chart_clock import measure_time
        from agentrader.market_feed import SharedFeed
        rows,market,quality=fixture(2)
        clock=Mock(return_value=1000000.);mono=Mock(return_value=10.)
        client=Mock();client.get.return_value={'serverTime':START+2000}
        sample=measure_time(client,clock,mono)[1]
        history={'candles':rows,'market':market,'quality':quality,'server_time':START+2000,'clock_sample':sample}
        socket=Mock();service=SimpleNamespace(history=Mock(return_value=history))
        feed=SharedFeed(service,'BTCUSDT','15m',socket_factory=lambda *_:socket,clock=clock,monotonic=mono)
        socket.receive.side_effect=lambda:(feed.stop_event.set() or None)
        feed.run()
        socket.receive.assert_called_once()
