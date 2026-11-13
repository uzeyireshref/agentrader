import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class PlanCLITests(unittest.TestCase):
    def test_local_create_approve_show_cancel_without_network_or_real_database(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=root) as folder:
            env = os.environ.copy()
            env['PYTHONPATH'] = str(root)
            def cli(*args, success=True):
                result = subprocess.run([sys.executable, '-m', 'agentrader', *args],
                                        cwd=folder, env=env, capture_output=True, text=True,
                                        encoding='utf-8', timeout=20)
                if success:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    return json.loads(result.stdout)
                self.assertNotEqual(result.returncode, 0)
                return result
            example = cli('plans', 'example')
            staged = cli('plans', 'example', '--staged')
            self.assertEqual(len(staged['targets']), 2)
            self.assertEqual(staged['management']['break_even_after_target'], 1)
            Path(folder, 'plan.json').write_text(json.dumps(example), encoding='utf-8')
            request = cli('plans', 'create', 'plan.json')
            self.assertEqual(request['state'], 'PENDING_APPROVAL')
            token = request['authorization_token']
            authorized = cli('plans', 'approve', 'demo-example', '1', '--token='+token)
            self.assertEqual(authorized['state'], 'AUTHORIZED')
            shown = cli('plans', 'show', 'demo-example', '1')
            self.assertNotIn('token_hash', shown)
            self.assertNotIn('authorization_token', shown)
            self.assertEqual(cli('plans', 'cancel', 'demo-example', '1')['state'], 'CANCELED')
            # Eski genel demo giriş komutu açık deney bayrağı olmadan bile API'ye ulaşmaz.
            result = cli('managed-open', '--execute-demo', success=False)
            self.assertIn('--test-only', result.stderr)
