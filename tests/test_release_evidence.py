import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from agentrader.acceptance.release import verify,DEFERRED


class ReleaseEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.docs=self.root/'docs/development/exchange-operations-20261115';self.docs.mkdir(parents=True)
        self.packages={k:dict(status='LOCAL_ACCEPTANCE_PASSED',dependencies=[]) for k in ('G03','G13','G22')}
        self.packages['G13']['dependencies']=['G03'];self.packages['G23']=dict(status='LOCAL_SCOPE_ACCEPTANCE_PASSED')
        for key in DEFERRED:self.packages[key]=dict(status='DEFERRED_BY_USER_SCOPE',implemented=False,deferred_reason='Product expansion deferred')
        self.scope=dict(runtime_execution_scope='BINANCE_USDM_DEMO_EXISTING_COMMANDS',deferred_packages=list(DEFERRED),full_exchange_coverage_claimed=False,external_acceptance='NOT_RUN')
        self.report_path=self.root/'report.json'
        self.report=dict(schema='reliability-priority-validation/1',baseline_regression_tests=1,
            full_regression=dict(tests_run=2,result='OK',skipped=0),reliability_suite=dict(status='PASSED',skipped=0),
            chart_replay=dict(passed=36,total=36),authenticated_exchange_acceptance='NOT_RUN',financial_exchange_actions_performed=False)
        self.save()

    def save(self):
        (self.docs/'packages.json').write_text(json.dumps(dict(packages=self.packages)),encoding='utf-8')
        (self.docs/'G23-scope.json').write_text(json.dumps(self.scope),encoding='utf-8')
        self.report['source_sha256']={p.relative_to(self.root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (self.docs/'packages.json',self.docs/'G23-scope.json')}
        self.report_path.write_text(json.dumps(self.report),encoding='utf-8')

    def result(self):return verify(self.root,self.report_path)

    def test_local_acceptance_never_authorizes_trading(self):
        r=self.result();self.assertEqual(r['status'],'LOCAL_SCOPE_VERIFIED_EXTERNAL_ACCEPTANCE_PENDING')
        self.assertFalse(r['financial_execution_authorized']);self.assertEqual(r['trading_readiness'],'UNPROVEN')

    def test_modified_source_invalidates_evidence(self):
        with (self.docs/'packages.json').open('a') as f:f.write(' ')
        self.assertEqual(self.result()['error'],'SOURCE_EVIDENCE_STALE')

    def test_deferred_work_cannot_be_marked_implemented(self):
        self.packages['G14']['implemented']=True;self.save()
        self.assertEqual(self.result()['error'],'DEFERRED_PACKAGE_MISREPRESENTED')

    def test_missing_dependency_blocks_closure(self):
        self.packages['G03']['status']='PENDING';self.save()
        self.assertEqual(self.result()['error'],'CRITICAL_DEPENDENCY_INCOMPLETE')

    def test_scope_cannot_claim_all_exchange_operations(self):
        self.scope['full_exchange_coverage_claimed']=True;self.save()
        self.assertEqual(self.result()['error'],'CLOSURE_SCOPE_MISMATCH')

    def test_tests_or_skips_cannot_be_hidden(self):
        self.report['full_regression']['tests_run']=0;self.save()
        self.assertEqual(self.result()['error'],'LOCAL_ACCEPTANCE_INCOMPLETE')
        self.report['full_regression']['tests_run']=2;self.report['reliability_suite']['skipped']=1;self.save()
        self.assertEqual(self.result()['error'],'LOCAL_ACCEPTANCE_INCOMPLETE')

    def test_external_claim_change_requires_separate_acceptance(self):
        self.report['authenticated_exchange_acceptance']='PASSED';self.save()
        self.assertEqual(self.result()['error'],'EXTERNAL_ACCEPTANCE_SCOPE_CHANGED')

    def test_outside_workspace_or_missing_required_evidence_is_rejected(self):
        self.report['source_sha256']={'../outside.py':'a'*64};self.report_path.write_text(json.dumps(self.report),encoding='utf-8')
        self.assertEqual(self.result()['status'],'BLOCKED')

    def test_sensitive_root_file_is_not_a_valid_evidence_source(self):
        self.report['source_sha256']['.env']='a'*64
        self.report_path.write_text(json.dumps(self.report),encoding='utf-8')
        self.assertEqual(self.result()['error'],'SOURCE_PATH_NOT_ALLOWED')

    def test_new_runtime_module_requires_fresh_acceptance_manifest(self):
        (self.root/'agentrader').mkdir();(self.root/'agentrader/new.py').write_text('# changed runtime\n',encoding='utf-8')
        self.assertEqual(self.result()['error'],'SOURCE_COVERAGE_INCOMPLETE')
