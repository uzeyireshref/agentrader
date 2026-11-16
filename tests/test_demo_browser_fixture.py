import copy
import unittest
from scripts.chart.demo_browser_fixture import fixture_packet,fixture_response,_snapshots
from scripts.integration.chart_tool_matrix_cases import candles


class DemoBrowserFixtureTests(unittest.TestCase):
    def setUp(self):_snapshots.clear()

    def packet(self,**changes):
        return {**dict(type='snapshot',symbol='BTCUSDT',interval='15m',generation=1,sequence=1,
            candles=candles(3),market=dict(symbol='BTCUSDT',tick_size='.25')),**changes}

    def test_missing_precision_stays_blocked_without_inventing_exact_data(self):
        p=self.packet();p['candles'][0].pop('exact');before=copy.deepcopy(p)
        r=fixture_packet(p)
        self.assertEqual(p,before);self.assertNotIn('exact',r['candles'][0])
        self.assertIn('PRICE_PRECISION_UNPROVEN',r['data_proof']['blocked_reasons'])
        self.assertFalse(r['data_proof']['live_eligible']);self.assertFalse(r['data_proof']['order_authority'])

    def test_invalid_identity_or_explicit_bad_proof_is_not_repaired(self):
        r=fixture_response('http://127.0.0.1/api/markets',dict(markets=[],source='wrong-source'))
        self.assertEqual(r['source'],'wrong-source')
        p=self.packet(data_proof=dict(corrupt=True),stream_epoch='invalid')
        r=fixture_packet(p);self.assertEqual(r['data_proof'],dict(corrupt=True));self.assertEqual(r['stream_epoch'],'invalid')

    def test_heartbeat_reuses_data_proof_and_new_revision_changes_hash(self):
        first=fixture_packet(self.packet())
        beat=fixture_packet(dict(type='update',symbol='BTCUSDT',interval='15m',generation=1,sequence=1))
        self.assertEqual(first['data_proof'],beat['data_proof'])
        changed=self.packet(sequence=2);changed['candles'][-1]['volume']+=1
        second=fixture_packet(changed)
        self.assertNotEqual(first['data_proof']['snapshot_hash'],second['data_proof']['snapshot_hash'])
        self.assertEqual(second['data_proof']['data_revision'],2)

    def test_history_context_comes_from_requested_symbol_and_interval(self):
        r=fixture_response('http://127.0.0.1/api/candles?symbol=ETHUSDT&interval=5m',dict(candles=[],has_more=False))
        self.assertEqual((r['symbol'],r['interval']),('ETHUSDT','5m'))

    def test_large_display_history_keeps_a_bounded_proof_window(self):
        r=fixture_packet(self.packet(candles=candles(1001)))
        self.assertEqual(len(r['candles']),1001)
        self.assertEqual(r['data_proof']['bar_count'],499)
