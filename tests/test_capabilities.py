import copy
import io
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from agentrader.capabilities import load_catalog, list_capabilities, probe_capabilities, save_probe, latest_probe, PROBES
from agentrader.capability_cli import main as capability_main
from agentrader.config import Config
from agentrader.exchange import ExchangeError, allowed_requests
from agentrader.state import StateStore


class ReadOnlyExchange:
    def __init__(self, key='api-key-canary'):
        self.config = Config(key, 'api-secret-canary' if key else '')
        self.offset_ms = 0
        self.calls = []
        self.error_path = None
        self.error = None
        self.account_flag = True
        self.mark_age = 0

    def get(self, path, params=None):
        self.calls.append(('GET',path,params))
        if path == self.error_path: raise self.error
        if path.endswith('/ping'): return {}
        if path.endswith('/time'): return {'serverTime': int(time.time()*1000)}
        if path.endswith('/exchangeInfo'):
            return {'symbols':[{'symbol':'BTCUSDT','status':'TRADING','quoteAsset':'USDT',
                    'contractType':'PERPETUAL','filters':[
                    {'filterType':'PRICE_FILTER','tickSize':'.1'},
                    {'filterType':'LOT_SIZE','stepSize':'.0001'},
                    {'filterType':'MIN_NOTIONAL','notional':'50'}]}]}
        if path.endswith('/premiumIndex'):
            return {'symbol':'BTCUSDT','markPrice':'75000','time':int(time.time()*1000)-self.mark_age}
        if path.endswith('/account'):
            return {'canTrade':self.account_flag,'assets':[],'positions':[],'availableBalance':'5000',
                    'secret':'api-secret-canary','apiKey':'api-key-canary'}
        if path.endswith('/dual'): return {'dualSidePosition':False}
        if path.endswith('/accountConfig'): return {'canTrade':True,'multiAssetsMargin':False}
        if path.endswith('/symbolConfig'):
            return [{'symbol':'BTCUSDT','leverage':20,'marginType':'CROSSED'}]
        if path.endswith('/leverageBracket'):
            return [{'symbol':'BTCUSDT','brackets':[{'initialLeverage':20,'notionalCap':'10000'}]}]
        return []

    def request(self, *args):
        raise AssertionError('Probe must never mutate the exchange')


class CapabilityTests(unittest.TestCase):
    def test_catalog_has_95_unique_entries_and_runtime_adapter_status(self):
        report = list_capabilities()
        self.assertEqual(report['count'],95)
        self.assertEqual(len({r['id'] for r in report['operations']}),95)
        for row in report['operations']:
            self.assertEqual(row['adapter_allowed'],(row['method'],row['path']) in allowed_requests())
            self.assertEqual(row['write_permission'],'NOT_VERIFIED')
        self.assertEqual(list_capabilities('trade')['count'],32)
        with self.assertRaises(ValueError): list_capabilities('not-a-category')

    def test_stale_snapshot_flags_never_grant_adapter_permission(self):
        catalog = load_catalog()
        for row in catalog['operations']: row['adapter_allowed'] = True
        with patch('agentrader.capabilities.load_catalog',return_value=catalog):
            report = list_capabilities()
        missing = next(r for r in report['operations'] if (r['method'],r['path'])not in allowed_requests())
        self.assertFalse(missing['adapter_allowed'])

    def test_public_probe_never_reads_private_account(self):
        x = ReadOnlyExchange()
        report = probe_capabilities(x)
        self.assertEqual(report['status'],'READ_CHECKS_PASSED')
        self.assertEqual(len(x.calls),4)
        self.assertIsNone(report['credential_ref'])
        self.assertEqual(report['check_counts']['ACCOUNT_NOT_REQUESTED'],8)

    def test_account_read_success_does_not_prove_trade_permission(self):
        x = ReadOnlyExchange()
        report = probe_capabilities(x,include_account=True)
        self.assertEqual(report['check_counts']['READ_VERIFIED'],len(PROBES))
        self.assertEqual(report['write_permission'],'NOT_VERIFIED')
        self.assertEqual(report['exchange_mutations'],0)
        self.assertTrue(next(r for r in report['checks'] if r['name']=='account')['summary']['account_can_trade_flag'])
        for row in report['operations']:
            if row['method']!='GET': self.assertEqual(row['current_read_access'],'NOT_PROBED')
        encoded = json.dumps(report)
        self.assertNotIn('api-secret-canary',encoded)
        self.assertNotIn('api-key-canary',encoded)

    def test_missing_keys_does_not_make_signed_calls(self):
        x = ReadOnlyExchange('')
        report = probe_capabilities(x,include_account=True)
        self.assertEqual(len(x.calls),4)
        self.assertEqual(report['check_counts']['CREDENTIALS_MISSING'],8)
        self.assertEqual(report['status'],'INCOMPLETE')

    def test_auth_error_is_not_treated_as_confirmed_missing_permission(self):
        x = ReadOnlyExchange();x.error_path='/fapi/v3/account'
        x.error=ExchangeError('api-secret-canary should never be printed',-2015,401)
        report=probe_capabilities(x,include_account=True)
        self.assertEqual(report['check_counts']['AUTH_OR_PERMISSION_DENIED'],1)
        self.assertEqual(len(x.calls),5)
        self.assertEqual(report['check_counts']['SKIPPED_AFTER_PRIVATE_ERROR'],7)
        self.assertNotIn('api-secret-canary',json.dumps(report))

    def test_rate_limit_or_access_block_stops_all_remaining_probes(self):
        for http in (403,418,429,451):
            x=ReadOnlyExchange();x.error_path='/fapi/v1/ping';x.error=ExchangeError('hidden',http_status=http)
            with self.subTest(http=http):
                report=probe_capabilities(x,include_account=True)
                self.assertEqual(len(x.calls),1)
                self.assertEqual(report['check_counts']['SKIPPED_AFTER_ERROR'],11)
                self.assertEqual(report['status'],'INCOMPLETE')

    def test_network_error_never_retries_or_grants_access(self):
        x=ReadOnlyExchange();x.error_path='/fapi/v1/ping';x.error=ExchangeError('offline')
        report=probe_capabilities(x,include_account=True)
        self.assertEqual(len(x.calls),1)
        self.assertEqual(report['checks'][0]['status'],'NETWORK_OR_SERVER_ERROR')

    def test_malformed_account_flag_is_not_a_success(self):
        x=ReadOnlyExchange();x.account_flag='true'
        report=probe_capabilities(x,include_account=True)
        self.assertEqual(next(r for r in report['checks'] if r['name']=='account')['status'],'INVALID_RESPONSE')

    def test_real_account_v3_schema_without_can_trade_is_valid_but_permission_unknown(self):
        x=ReadOnlyExchange()
        original=x.get
        def account_v3(path,params=None):
            result=original(path,params)
            if path.endswith('/account'): result.pop('canTrade')
            return result
        x.get=account_v3
        report=probe_capabilities(x,include_account=True)
        account=next(r for r in report['checks'] if r['name']=='account')
        self.assertEqual(account['status'],'READ_VERIFIED')
        self.assertIsNone(account['summary']['account_can_trade_flag'])
        self.assertEqual(account['summary']['trade_flag_status'],'NOT_EXPOSED_BY_ACCOUNT_V3')
        self.assertEqual(report['write_permission'],'NOT_VERIFIED')

    def test_stale_price_is_separate_from_read_access(self):
        x=ReadOnlyExchange();x.mark_age=60000
        report=probe_capabilities(x)
        mark=next(r for r in report['checks'] if r['name']=='mark')
        self.assertEqual(mark['status'],'READ_VERIFIED')
        self.assertFalse(mark['summary']['fresh_for_execution'])

    def test_invalid_symbol_is_rejected_before_network(self):
        x=ReadOnlyExchange()
        with self.assertRaises(ValueError): probe_capabilities(x,'BTCUSDT&secret=bad')
        self.assertEqual(x.calls,[])

    def test_capability_evidence_is_persistent_idempotent_and_preserves_intents(self):
        report=probe_capabilities(ReadOnlyExchange(),include_account=True)
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            path=Path(folder)/'state.sqlite3';store=StateStore(path)
            try:
                store.reserve('legacy','/fapi/v1/order',{'symbol':'BTCUSDT'})
                self.assertTrue(save_probe(store,report))
                self.assertFalse(save_probe(store,report))
                changed=copy.deepcopy(report);changed['symbol']='ETHUSDT'
                with self.assertRaises(ValueError): save_probe(store,changed)
            finally: store.close()
            reopened=StateStore(path)
            try:
                row=reopened.db.execute('SELECT * FROM capability_runs').fetchone()
                self.assertEqual(row['credential_ref'],report['credential_ref'])
                self.assertEqual(json.loads(row['body'])['run_id'],report['run_id'])
                self.assertEqual(reopened.intents()[0]['client_id'],'legacy')
            finally: reopened.close()

    def test_offline_cli_does_not_read_credentials_or_create_exchange(self):
        with patch('agentrader.capability_cli.Config.load',side_effect=AssertionError('credentials read')), \
             patch('agentrader.capability_cli.DemoExchange',side_effect=AssertionError('network created')), \
             patch('sys.stdout',new_callable=io.StringIO) as output:
            self.assertEqual(capability_main(['list','--category','trade']),0)
            self.assertEqual(json.loads(output.getvalue())['count'],32)

    def test_saved_evidence_is_bound_to_key_symbol_and_age(self):
        report=probe_capabilities(ReadOnlyExchange(),include_account=True)
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            store=StateStore(Path(folder)/'db.sqlite3')
            try:
                self.assertEqual(latest_probe(store,'BTCUSDT')['evidence_status'],'NOT_FOUND')
                save_probe(store,report)
                stamp=report['finished_at_ms']
                self.assertEqual(latest_probe(store,'BTCUSDT','other-key')['evidence_status'],'NOT_FOUND')
                self.assertEqual(latest_probe(store,'ETHUSDT',report['credential_ref'])['evidence_status'],'NOT_FOUND')
                self.assertEqual(latest_probe(store,'BTCUSDT',report['credential_ref'],now_ms=stamp+1000)['evidence_status'],'FRESH')
                self.assertEqual(latest_probe(store,'BTCUSDT',report['credential_ref'],now_ms=stamp+301000)['evidence_status'],'STALE')
                self.assertEqual(latest_probe(store,'BTCUSDT',report['credential_ref'],now_ms=stamp-1000)['evidence_status'],'STALE')
            finally: store.close()

    def test_cli_public_probe_does_not_load_env_and_saves_incomplete_report(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            path=Path(folder)
            with patch('agentrader.capability_cli.Config.load',side_effect=AssertionError('credentials read')), \
                 patch('agentrader.capability_cli.DemoExchange',return_value=ReadOnlyExchange('')), \
                 patch('sys.stdout',new_callable=io.StringIO):
                code=capability_main(['probe','--database',str(path/'db.sqlite3'),'--output',str(path/'report.json')])
            self.assertEqual(code,0)
            self.assertTrue((path/'report.json').exists())
