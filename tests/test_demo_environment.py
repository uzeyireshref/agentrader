from contextlib import closing
"""Regression tests for source confusion and legacy store isolation."""
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch, Mock

from agentrader.application.environment import bind_demo_store, CONTEXT
from agentrader.application.settings import WebSettings
from agentrader.shared.market_environment import SOURCE, ENVIRONMENT, REST_URL, KLINE_WS_BASE
from agentrader.shared.market_data import CandleStore, PublicMarket
from agentrader.migrations import migrate
from agentrader.chart.price_alerts import PriceAlerts
from test_price_alerts import context


class DemoEnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_legacy_alert_database_is_rejected_unchanged(self):
        file = self.root/'legacy.db'
        migrate(file)
        with closing(sqlite3.connect(file)) as db, db:
            db.execute("INSERT INTO app_price_alerts VALUES ('owner','alert',1,'{}','ACTIVE','{}')")
        before = hashlib.sha256(file.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, 'LEGACY_APPLICATION'):
            bind_demo_store(file)
        self.assertEqual(hashlib.sha256(file.read_bytes()).hexdigest(), before)

    def test_fresh_schema_can_be_bound_and_reopened_but_live_marker_cannot(self):
        file = self.root/'demo.db'
        migrate(file)
        bind_demo_store(file)
        bind_demo_store(file)
        with closing(sqlite3.connect(file)) as db, db:
            self.assertEqual(json.loads(db.execute('SELECT body FROM app_market_context').fetchone()[0]), CONTEXT)
            db.execute('UPDATE app_market_context SET body=?', (json.dumps({**CONTEXT,'environment':'live_public'}),))
        with self.assertRaisesRegex(ValueError, 'CONTEXT_MISMATCH'):
            bind_demo_store(file)

    def test_defaults_use_new_demo_stores_and_do_not_change_execution_store(self):
        with patch.dict('os.environ', {}, clear=True), patch('getpass.getuser', return_value='test-user'):
            settings = WebSettings.load()
        self.assertEqual(settings.application_database.name, 'application-demo.sqlite3')
        self.assertEqual(settings.market_database.name, 'chart-market-demo.sqlite3')
        self.assertEqual(settings.execution_database.name, 'execution.sqlite3')

    def test_candle_store_never_loads_live_rows_as_demo(self):
        file = self.root/'market.db'
        store = CandleStore(file)
        self.addCleanup(store.close)
        row = [1800000000000,'100','101','99','100','1',1800000059999,'100',1,'1','100','0']
        with store.db:
            store.db.execute('INSERT INTO candles VALUES (?,?,?,?,?,?,?)',
                ('binance_usdm_live_trade_price','BTCUSDT','1m',row[0],row[6],json.dumps(row),row[6]+1))
        self.assertEqual(store.load('BTCUSDT','1m',row[6]+1), [])
        store.save('BTCUSDT','1m',[row],row[6]+1)
        self.assertEqual(store.load('BTCUSDT','1m',row[6]+1), [row])
        self.assertEqual(store.db.execute('SELECT COUNT(DISTINCT source) FROM candles').fetchone()[0], 2)

    def test_market_requests_pin_demo_host_and_keep_account_access_forbidden(self):
        market = PublicMarket(transport=Mock())
        market.transport.perform.return_value = {'serverTime': 1800000000000}
        market.get('/fapi/v1/time')
        args = market.transport.perform.call_args.args
        self.assertEqual(args[-1], REST_URL)
        self.assertTrue(args[1]().full_url.startswith(REST_URL+'/'))
        self.assertEqual(args[1]().get_method(), 'GET')
        self.assertNotIn('X-mbx-apikey', args[1]().headers)
        for endpoint in ('/fapi/v3/account','/fapi/v1/order','https://fapi.binance.com/fapi/v1/time'):
            with self.assertRaises(ValueError): market.get(endpoint)
        self.assertEqual(KLINE_WS_BASE, 'wss://demo-fstream.binance.com/market/ws/')

    def test_live_context_cannot_fire_demo_alert(self):
        file = self.root/'alerts.db'
        migrate(file)
        alerts = PriceAlerts(file, 'owner', clock=lambda: 1800000100.)
        alert = alerts.save(dict(name='Demo',symbol='BTCUSDT',interval='1m',operator='cross_up',price='100',frequency='bar_close',expires_at=None,message=''))
        good = context(old='99', new='99')
        alerts.process(alert['id'], good, 'boot')
        bad = context(n=1, old='99', new='101')
        bad['identity'].update(source='binance_usdm_live_trade_price', environment='live_public')
        alerts.process(alert['id'], bad, 'boot')
        self.assertEqual(alerts.events(), [])
        self.assertEqual(alerts.list()[0]['readiness'], 'WAITING_DATA')
