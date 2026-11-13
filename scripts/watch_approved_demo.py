"""Monitor an already approved demo plan; never creates or renews approval."""
import argparse
import getpass
import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agentrader.config import Config
from agentrader.exchange import DemoExchange, ExchangeError
from agentrader.locking import execution_lock
from agentrader.plan_execution import run_plan
from agentrader.plans import PlanService
from agentrader.risk import RiskLimits
from agentrader.state import StateStore
from agentrader.watchdog import Watchdog, watch_loop


def emit(**result):
    # Redirected Windows processes may inherit a legacy code page. JSON escapes
    # preserve Unicode without letting logging terminate position management.
    print(json.dumps(dict(time=time.time(), **result), ensure_ascii=True), flush=True)


def restart_proof(store, session, before):
    if (session['id'] != before['session_id'] or session['entry_id'] != before['entry_id']
            or session['plan']['stop'] != before['stop'] or os.getpid() == before['pid']):
        raise ValueError('Yeniden başlatma kimlik/stop kontrolü başarısız.')
    intents = store.intents()
    entry_index = next(i for i, row in enumerate(intents) if row['client_id'] == session['entry_id'])
    buys = [row for row in intents[entry_index:] if json.loads(row['params']).get('side') == 'BUY']
    if len(buys) != 1 or buys[0]['client_id'] != session['entry_id']:
        raise ValueError('Yeniden başlatmada beklenmeyen giriş niyeti.')
    return {'session_id': session['id'], 'entry_id': session['entry_id'], 'stop': session['plan']['stop'],
            'previous_pid': before['pid'], 'current_pid': os.getpid(), 'buy_intents': len(buys)}


def manage(exchange, store, limits, service, plan_id, version, restart_after_stop=False, checkpoint=None):
    session = Watchdog(exchange, store, limits).session()
    row = service.show(plan_id, version)
    expected = {'plan_id': plan_id, 'version': version, 'digest': row['digest']}
    if session.get('plan_ref') != expected or session['id'] != row['session_id']:
        raise ValueError('Devralınacak oturum istenen onaylı plana ait değil.')
    emit(event='management_attached', session_id=session['id'], entry_id=session['entry_id'])
    for report in watch_loop(Watchdog(exchange, store, limits), execute=True,
                             iterations=0, interval=5):
        emit(event='position_monitor', result=report)
        if report['status'] == 'protected' and checkpoint:
            proof = restart_proof(store, Watchdog(exchange, store, limits).session(), checkpoint)
            store.event('stop_retest_restart_verified', proof)
            emit(event='restart_verified', proof=proof)
            checkpoint = None
        if report['status'] == 'protected' and restart_after_stop:
            current = Watchdog(exchange, store, limits).session()
            if current.get('stop_transition', {}).get('state') == 'APPLIED':
                before = {'session_id': current['id'], 'entry_id': current['entry_id'],
                          'stop': current['plan']['stop'], 'pid': os.getpid()}
                store.event('stop_retest_restart_requested', before)
                path = Path('logs') / ('restart-' + plan_id + '.json')
                path.write_text(json.dumps(before, indent=2), encoding='utf-8')
                emit(event='restart_requested', checkpoint=str(path))
                return str(path)
    service.show(plan_id, version)


def main(plan_id, version, resume_only=False, restart_after_stop=False, checkpoint=None):
    with execution_lock():
        store = StateStore()
        try:
            service = PlanService(store, 'local:' + getpass.getuser())
            exchange = DemoExchange(Config.load())
            limits = RiskLimits.load('risk-demo.json')
            emit(event='monitor_started', plan_id=plan_id, version=version)
            if resume_only:
                # No entry path is reachable from this mode, including after expiry.
                return manage(exchange, store, limits, service, plan_id, version,
                              restart_after_stop, checkpoint)
            while True:
                row = service.show(plan_id, version)
                if row['state'] != 'AUTHORIZED':
                    emit(event='entry_monitor_stopped', state=row['state'])
                    return
                try:
                    result = run_plan(service, exchange, limits, plan_id, version, execute=True)
                except ExchangeError as exc:
                    emit(event='exchange_error', message=str(exc))
                    # Never retry a claimed entry here. Protection recovery requires review.
                    if service.show(plan_id, version)['state'] != 'AUTHORIZED':
                        raise
                    time.sleep(5)
                    continue
                emit(event='entry_check', result=result)
                if result.get('executed'):
                    if service.show(plan_id, version)['state'] != 'CLOSED':
                        return manage(exchange, store, limits, service, plan_id, version, restart_after_stop)
                    return
                time.sleep(5)
        finally:
            store.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan_id')
    parser.add_argument('version', type=int)
    parser.add_argument('--resume-only', action='store_true', help='Only manage the matching existing session; never enter')
    parser.add_argument('--restart-after-stop', action='store_true', help='Restart once after exchange-verified stop transition')
    parser.add_argument('--verify-restart', help='Internal checkpoint; requires --resume-only')
    args = parser.parse_args()
    if args.verify_restart and not args.resume_only:
        parser.error('--verify-restart requires --resume-only')
    try:
        checkpoint = json.loads(Path(args.verify_restart).read_text(encoding='utf-8')) if args.verify_restart else None
        restart = main(args.plan_id, args.version, args.resume_only, args.restart_after_stop, checkpoint)
        if restart:
            # main has returned and released the execution lock. Child has no entry path.
            child = subprocess.Popen([sys.executable, '-u', str(Path(__file__).resolve()), args.plan_id,
                                      str(args.version), '--resume-only', '--verify-restart', restart],
                                     stdout=sys.stdout, stderr=sys.stderr,
                                     creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            emit(event='restart_spawned', child_pid=child.pid)
    except Exception as exc:
        emit(event='monitor_failed', error=str(exc))
        raise
