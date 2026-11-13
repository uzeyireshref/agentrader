import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from agentrader.application.settings import WebSettings
from agentrader.web_cli import main


class WebCLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        folder = Path(self.temp.name)
        self.settings = WebSettings(folder / 'app.db', folder / 'exec.db', 't' * 40)

    def test_migration_and_one_shot_worker_start_without_binance_environment(self):
        with patch.object(WebSettings, 'load', return_value=self.settings), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(['migrate']), 0)
            self.assertEqual(main(['worker', '--once']), 0)
        self.assertIn('IDLE', out.getvalue())
        self.assertFalse(self.settings.execution_database.exists())

    @unittest.skipUnless(importlib.util.find_spec('uvicorn') and importlib.util.find_spec('fastapi'), 'optional web dependencies')
    def test_server_is_loopback_single_worker_and_does_not_trust_proxies(self):
        with patch.object(WebSettings, 'load', return_value=self.settings), patch('uvicorn.run') as serve:
            self.assertEqual(main(['serve', '--port', '8766']), 0)
        self.assertEqual(serve.call_args.kwargs['host'], '127.0.0.1')
        self.assertEqual(serve.call_args.kwargs['workers'], 1)
        self.assertFalse(serve.call_args.kwargs['proxy_headers'])
        self.assertFalse(self.settings.application_database.exists())

    def test_existing_cli_help_and_worker_help_do_not_import_web_framework(self):
        script = """import importlib.abc
import sys
class DenyWeb(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('fastapi','uvicorn','httpx'):
            raise ImportError('web dependencies unavailable')
sys.meta_path.insert(0, DenyWeb())
from agentrader.__main__ import main
sys.argv=['agentrader']+sys.argv[1:]
raise SystemExit(main())
"""
        for args in [('market', '--help'), ('web', 'worker', '--help')]:
            result = subprocess.run([sys.executable, '-c', script, *args], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run([sys.executable, '-c', script, 'web', 'serve'], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        self.assertIn('WEB_DEPENDENCIES_MISSING', result.stdout)

    def test_invalid_configuration_error_does_not_echo_secret(self):
        with patch.object(WebSettings, 'load', side_effect=ValueError('private-secret')), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(['migrate']), 1)
        self.assertNotIn('private-secret', out.getvalue())
