"""Independent fill-accounting oracle over generated real SQLite projections."""
import json
import os
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest

from agentrader.acceptance.sequences import generate,minimize
from agentrader.bot.order_journal import OrderJournal
from agentrader.shared.state import StateStore


class InvariantFailure(AssertionError):
    pass


def run_trace(trace):
    with tempfile.TemporaryDirectory(prefix='agentrader-model-') as folder:
        path=Path(folder)/'execution.db';store=StateStore(path);journal=OrderJournal(store)
        expected=[0,0,0];events=[None,None,None];sides=['BUY','SELL','BUY'];symbols=['BTCUSDT','BTCUSDT','ETHUSDT']
        for i in range(3):journal.register(f'order-{i}','owner',symbols[i],sides[i],'0.0010')
        try:
            for step in trace:
                i=step['order'];cid=f'order-{i}';kind=step['kind'];before=journal.get(cid)
                if kind=='restart':
                    store.close();store=StateStore(path);journal=OrderJournal(store)
                elif kind=='observe':
                    args=dict(status=step['status'],cumulative_filled=str(Decimal(step['fill'])/10000),observed_ms=step['at'])
                    journal.observe(cid,step['event'],**args);events[i]=(step['event'],args)
                    expected[i]=max(expected[i],step['fill'])
                elif kind in ('duplicate','conflict') and events[i]:
                    eid,args=events[i];args=dict(args)
                    if kind=='conflict':
                        args['observed_ms']+=1
                        try:journal.observe(cid,eid,**args)
                        except ValueError:pass
                        else:raise InvariantFailure('CONFLICTING_EVENT_ACCEPTED')
                    else:
                        result=journal.observe(cid,eid,**args)
                        if Decimal(result['fill_delta'])!=0:raise InvariantFailure('DUPLICATE_INCREASED_FILL')
                elif kind=='foreign':
                    try:journal.observe('unowned','foreign',status='FILLED',cumulative_filled='1',observed_ms=1)
                    except ValueError:pass
                    else:raise InvariantFailure('FOREIGN_ORDER_ADOPTED')
                elif kind=='identity':
                    try:journal.register(cid,'other-owner',symbols[i],sides[i],'0.0010')
                    except ValueError:pass
                    else:raise InvariantFailure('OWNER_IDENTITY_REPLACED')
                after=journal.get(cid)
                if Decimal(after['filled'])!=Decimal(expected[i])/10000:raise InvariantFailure('CUMULATIVE_FILL_ORACLE_MISMATCH')
                if Decimal(after['remaining'])+Decimal(after['filled'])!=Decimal('0.0010'):raise InvariantFailure('QUANTITY_NOT_CONSERVED')
                if after['status']=='REJECTED' and Decimal(after['filled'])>0:raise InvariantFailure('FILLED_ORDER_REMAINS_REJECTED')
                if before['status'] in ('CANCELED','EXPIRED','FILLED') and after['status'] not in ('CANCELED','EXPIRED','FILLED'):
                    raise InvariantFailure('TERMINAL_ORDER_REOPENED')
                btc=Decimal(expected[0]-expected[1])/10000
                if journal.inventory('owner','BTCUSDT')!=btc:raise InvariantFailure('INVENTORY_ORACLE_MISMATCH')
                if journal.inventory('other-owner','BTCUSDT')!=0:raise InvariantFailure('FOREIGN_OWNER_INVENTORY')
        finally:store.close()


class ReliabilitySequenceTests(unittest.TestCase):
    def test_seeded_state_sequences_preserve_accounting_and_identity(self):
        start=int(os.environ.get('AGENTRADER_ACCEPTANCE_SEED','20261116'))
        cases=int(os.environ.get('AGENTRADER_ACCEPTANCE_CASES','24'))
        steps=int(os.environ.get('AGENTRADER_ACCEPTANCE_STEPS','60'))
        self.assertTrue(1<=cases<=200)
        for seed in range(start,start+cases):
            trace=generate(seed,steps)
            try:run_trace(trace)
            except InvariantFailure as exc:
                code=str(exc)
                def same_failure(candidate):
                    try:run_trace(candidate)
                    except InvariantFailure as other:return str(other)==code
                    return False
                minimal=minimize(trace,same_failure)
                self.fail(json.dumps(dict(seed=seed,invariant=code,original_steps=len(trace),reduced=minimal),sort_keys=True))

    def test_rejection_cannot_erase_a_known_partial_execution(self):
        run_trace([dict(kind='observe',order=0,event='partial',status='PARTIALLY_FILLED',fill=5,at=2),
                   dict(kind='observe',order=0,event='reject',status='REJECTED',fill=0,at=3)])

    def test_execution_evidence_cannot_remain_a_terminal_rejection(self):
        run_trace([dict(kind='observe',order=0,event='reject',status='REJECTED',fill=0,at=3),
                   dict(kind='observe',order=0,event='partial',status='PARTIALLY_FILLED',fill=5,at=2)])

    def test_seed_replay_is_identical(self):
        self.assertEqual(generate(7),generate(7));self.assertNotEqual(generate(7),generate(8))

    def test_failure_shrinker_preserves_trigger_with_bounded_runs(self):
        trace=['noise']*12+['lost-response','restart']+['noise']*12
        result=minimize(trace,lambda t:'lost-response' in t and 'restart' in t)
        self.assertEqual(result['trace'],['lost-response','restart']);self.assertLessEqual(result['attempts'],128)

    def test_generator_rejects_unbounded_or_invalid_work(self):
        for seed,steps in ((True,3),(-1,3),(2,501),(2,0)):
            with self.assertRaises(ValueError):generate(seed,steps)
