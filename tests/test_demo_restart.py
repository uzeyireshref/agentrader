import os
import io
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from agentrader.state import StateStore
from scripts.watch_approved_demo import restart_proof, emit


class DemoRestartTests(unittest.TestCase):
    def test_redirected_legacy_windows_log_keeps_turkish_text(self):
        buffer = io.BytesIO()
        stream = io.TextIOWrapper(buffer, encoding='cp1252')
        with patch('scripts.watch_approved_demo.sys.stdout', stream):
            emit(event='işlem', reason='Giriş koşulu sağlandı')
        stream.flush()
        result = json.loads(buffer.getvalue().decode('ascii'))
        self.assertEqual(result['reason'], 'Giriş koşulu sağlandı')

    def test_separate_process_checkpoint_keeps_entry_and_stop(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()) as folder:
            store = StateStore(Path(folder) / 'state.sqlite3')
            try:
                store.reserve('entry', '/fapi/v1/order', {'side': 'BUY'})
                store.reserve('partial', '/fapi/v1/order', {'side': 'SELL', 'reduceOnly': 'true'})
                session = {'id': 'session', 'entry_id': 'entry', 'plan': {'stop': '80000'}}
                before = {'session_id': 'session', 'entry_id': 'entry', 'stop': '80000', 'pid': -1}
                self.assertEqual(restart_proof(store, session, before)['buy_intents'], 1)
                for change in ({'pid': os.getpid()}, {'stop': '79999'}, {'session_id': 'other'}):
                    with self.subTest(change=change), self.assertRaises(ValueError):
                        restart_proof(store, session, before | change)
                store.reserve('duplicate', '/fapi/v1/order', {'side': 'BUY'})
                with self.assertRaises(ValueError):
                    restart_proof(store, session, before)
            finally:
                store.close()
