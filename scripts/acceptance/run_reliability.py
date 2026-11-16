"""Run the fixed offline reliability suite, including actual killed processes.

Only loopback fake exchanges and temporary stores are used. No Config.load,
authenticated Binance action, cleanup of user journals, or live acceptance.
"""
import argparse
from contextlib import redirect_stdout,redirect_stderr
import io
import json
import os
from pathlib import Path
import sys
import time
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
FILES=(
    'test_reliability_sequences.py','test_order_journal.py','test_exchange_commands.py',
    'test_shared_rate_ws.py','test_recovery_process.py','test_recovery_guardian.py',
    'test_stream_recovery.py','test_order_amend.py','test_batch_commands.py',
    'test_cancel_scope_commands.py','test_cancel_timers.py','test_product_discovery.py',
    'test_history_reconciliation.py','test_operations_status.py','test_release_evidence.py',
)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed',type=int,default=20261116)
    parser.add_argument('--cases',type=int,default=64)
    parser.add_argument('--steps',type=int,default=100)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args(argv)
    if not 0<=args.seed<2**32-args.cases or not 1<=args.cases<=200 or not 1<=args.steps<=500:
        parser.error('seed/cases/steps out of bounded acceptance range')
    if any(not (ROOT/'tests'/name).is_file() for name in FILES):
        print(json.dumps(dict(status='BLOCKED',error='ACCEPTANCE_SUITE_MISSING')));return 2
    keys={'AGENTRADER_ACCEPTANCE_SEED':str(args.seed),'AGENTRADER_ACCEPTANCE_CASES':str(args.cases),'AGENTRADER_ACCEPTANCE_STEPS':str(args.steps)}
    old={k:os.environ.get(k) for k in keys};os.environ.update(keys)
    started=time.monotonic();capture=io.StringIO()
    try:
        loader=unittest.TestLoader();suite=unittest.TestSuite()
        for name in FILES:suite.addTests(loader.discover(str(ROOT/'tests'),pattern=name,top_level_dir=str(ROOT/'tests')))
        with redirect_stdout(capture),redirect_stderr(capture):
            result=unittest.TextTestRunner(stream=capture,verbosity=0).run(suite)
        failures=[test.id() for test,_ in result.failures];errors=[test.id() for test,_ in result.errors]
        status='PASSED' if result.wasSuccessful() and not result.skipped else 'INCOMPLETE' if result.wasSuccessful() else 'FAILED'
        report=dict(schema='offline-reliability-acceptance/1',status=status,tests_run=result.testsRun,
            seconds=round(time.monotonic()-started,3),seed=args.seed,model_cases=args.cases,steps_per_case=args.steps,
            modules=list(FILES),failures=failures,errors=errors,skipped=len(result.skipped),
            authenticated_exchange_acceptance='NOT_RUN',financial_exchange_actions_performed=False,
            exchange_transport='ISOLATED_FAKE_AND_LOOPBACK',shrinking='BOUNDED_SAME_INVARIANT_DELTA_DEBUGGING',
            failure_details='Use the recorded seed/cases/steps to reproduce locally; raw exception messages are not exported')
        if args.output:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(json.dumps(report,ensure_ascii=True,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(report,ensure_ascii=True,indent=2))
        return 0 if status=='PASSED' else 1
    finally:
        for k,v in old.items():
            if v is None:os.environ.pop(k,None)
            else:os.environ[k]=v


if __name__=='__main__':raise SystemExit(main())
