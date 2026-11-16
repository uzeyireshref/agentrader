import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class PlanCLITests(unittest.TestCase):
    def test_v2_response_preference_is_imported_and_visible_in_normal_cli(self):
        from test_plan_v2 import plan_v2
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=root) as folder:
            env=os.environ.copy();env['PYTHONPATH']=str(root)
            env['AGENTRADER_EXECUTION_DATABASE']=str(Path(folder)/'selected.sqlite3')
            plan=plan_v2();plan['entry']['order_response_type']='RESULT'
            Path(folder,'plan.json').write_text(json.dumps(plan),encoding='utf-8')
            for args in (['create','plan.json'],['show',plan['plan_id'],'1']):
                result=subprocess.run([sys.executable,'-m','agentrader','plans',*args],
                                      cwd=folder,env=env,capture_output=True,text=True,encoding='utf-8',timeout=20)
                self.assertEqual(result.returncode,0,result.stderr)
                shown=json.loads(result.stdout)
                self.assertEqual(shown['plan']['entry']['order_response_type'],'RESULT')

    def test_configured_execution_database_is_shared_with_web_review(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=root) as folder:
            env = os.environ.copy()
            env['PYTHONPATH'] = str(root)
            selected = Path(folder) / 'selected.sqlite3'
            env['AGENTRADER_EXECUTION_DATABASE'] = str(selected)
            result = subprocess.run([sys.executable, '-m', 'agentrader', 'plans', 'list'],
                                    cwd=folder, env=env, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(selected.is_file())
            self.assertFalse((Path(folder) / 'data/execution.sqlite3').exists())

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
