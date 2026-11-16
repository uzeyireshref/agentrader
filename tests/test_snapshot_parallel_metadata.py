import threading
import unittest
from unittest.mock import patch
from agentrader.shared.config import Config
from agentrader.shared.exchange import DemoExchange
from agentrader.bot.risk import RiskLimits
from agentrader.bot.v2_preflight import collect_flat_snapshot
from test_v2_preflight import SnapshotExchange


class ParallelMetadataTests(unittest.TestCase):
    def test_read_only_account_keeps_parallel_fixed_get_metadata(self):
        from agentrader.integration.preview_preflight import ReadOnlyDemoAccount
        fixture=SnapshotExchange();x=DemoExchange(Config('fixture','fixture'));barrier=threading.Barrier(3);methods=[]
        paths={'/fapi/v1/symbolConfig','/fapi/v1/leverageBracket','/fapi/v1/exchangeInfo'}
        def request(client,method,path,params=None):
            methods.append(method)
            if path in paths:barrier.wait(timeout=3)
            return fixture.get(path,params)
        with patch.object(DemoExchange,'request',request),patch.object(DemoExchange,'sync_time'):
            r=collect_flat_snapshot(ReadOnlyDemoAccount(x),'BTCUSDT',RiskLimits(),clock=lambda:1001)
        self.assertTrue(r['flat_verified']);self.assertEqual(set(methods),{'GET'})

    def test_independent_reads_overlap_with_separate_transports_same_clock_and_governor(self):
        fixture=SnapshotExchange();x=DemoExchange(Config('fixture','fixture'))
        barrier=threading.Barrier(3);seen=[]
        paths={'/fapi/v1/symbolConfig','/fapi/v1/leverageBracket','/fapi/v1/exchangeInfo'}
        def get(client,path,params=None):
            if path in paths:
                seen.append(client)
                barrier.wait(timeout=3)
            return fixture.get(path,params)
        with patch.object(DemoExchange,'get',get),patch.object(DemoExchange,'sync_time'):
            r=collect_flat_snapshot(x,'BTCUSDT',RiskLimits(),clock=lambda:1001)
        self.assertTrue(r['flat_verified']);self.assertEqual(len(seen),3)
        self.assertEqual(len({id(c.transport) for c in seen}),3)
        self.assertEqual(len({id(c.opener) for c in seen}),3)
        self.assertTrue(all(c.transport.governor is x.transport.governor for c in seen))
        self.assertTrue(all(c.offset_ms==x.offset_ms for c in seen))

    def test_any_metadata_failure_blocks_snapshot(self):
        fixture=SnapshotExchange();x=DemoExchange(Config('fixture','fixture'))
        def get(client,path,params=None):
            if path=='/fapi/v1/leverageBracket':raise ValueError('unverified tier')
            return fixture.get(path,params)
        with patch.object(DemoExchange,'get',get),patch.object(DemoExchange,'sync_time'):
            with self.assertRaisesRegex(ValueError,'unverified tier'):
                collect_flat_snapshot(x,'BTCUSDT',RiskLimits(),clock=lambda:1001)
