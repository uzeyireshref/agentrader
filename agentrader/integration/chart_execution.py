"""Explicit local review handoff. Source binding is durable and checked by V2Runner.

This module never approves a plan or submits an exchange request. Caller holds
execution_lock when importing; the existing plans approve/run CLI remains explicit.
"""
import copy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import time

from agentrader.chart.chart_bindings import binding_hash
from agentrader.shared.market_environment import SOURCE, ENVIRONMENT
from agentrader.bot.plans import digest, timestamp
from agentrader.integration.preview_preflight import checked_preview, local_preview_provider, preflight_preview

PREFIX = 'shadow-event:'


def require_demo_acceptance(root=Path(__file__).resolve().parents[2]):
    """Fail closed on missing/failed evidence or changed observed source files."""
    try:
        receipt = json.loads((root / 'reports/continuity-delivery-20261113.json').read_text(encoding='utf-8'))
        report = json.loads((root / 'reports/demo-continuity-observation-20261113.json').read_text(encoding='utf-8'))
        closes = report['closed_events']
        if (report['state'] != 'COMPLETED' or report['passed'] is not True
                or report['source'] != SOURCE or report['environment'] != ENVIRONMENT
                or report['elapsed_seconds'] < 1800 or len(closes) < 29
                or report['violations'] or report['account_requests'] != 0 or report['order_requests'] != 0
                or any(o['seconds'] > 30 or o['end'] is None for o in report['outages'])
                or any(b['time'] - a['time'] != 60 for a, b in zip(closes, closes[1:]))):
            raise ValueError()
        required = {'agentrader/chart/chart_clock.py', 'agentrader/chart/chart_market.py',
                    'agentrader/shared/market_feed.py', 'agentrader/integration/shadow_tracking.py',
                    'scripts/chart/build_binding_evidence.py', 'scripts/chart/observe_demo_continuity.py',
                    'tests/test_clock_renewal.py'}
        if set(receipt['sources']) != required or any(
                hashlib.sha256((root / name).read_bytes()).hexdigest() != receipt['sources'][name]
                for name in required):
            raise ValueError()
        return True
    except (OSError, ValueError, KeyError, TypeError):
        raise ValueError('DEMO_CONTINUITY_ACCEPTANCE_REQUIRED') from None


def _account(exchange):
    key = exchange.config.api_key
    if not key:
        raise ValueError('DEMO_ACCOUNT_IDENTITY_REQUIRED')
    return hashlib.sha256(key.encode()).hexdigest()


def _key(plan):
    return f"chart_entry:{plan['plan_id']}:{plan['version']}"


def execution_plan(preview, owner):
    # Each semantic event owns exactly one execution plan, independent of how many
    # preview revisions existed before review. Preview revision remains in binding.
    plan = copy.deepcopy(preview['plan'])
    plan['plan_id'] = 'chart-' + digest([owner, preview['workspace_id'], preview['event_id']])[:32]
    plan['version'] = 1
    return plan


def review_preview(service, provider, exchange, limits, *, workspace, event_id,
                   version, port=8765, clock=time.time, preflight=preflight_preview,
                   acceptance=require_demo_acceptance):
    """Create PENDING_APPROVAL only, with one-time token. Never implicitly approve."""
    acceptance()
    before, _ = checked_preview(provider, limits, clock=clock)
    if (before['workspace_id'], before['event_id'], before['version']) != (workspace, event_id, version):
        raise ValueError('PREVIEW_REFERENCE_MISMATCH')
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError('INVALID_LOCAL_PREVIEW_PORT')
    account_ref = _account(exchange)
    report = preflight(provider, exchange, limits, clock=clock)
    after, _ = checked_preview(provider, limits, clock=clock)
    if before['content_hash'] != after['content_hash'] or report['preview_hash'] != before['content_hash']:
        raise ValueError('PREVIEW_CHANGED_DURING_REVIEW')
    if report['account_preflight']['state'] != 'READY':
        raise ValueError('DEMO_ACCOUNT_NOT_READY')
    if service.store.sessions():
        raise ValueError('CHART_REVIEW_REQUIRES_IDLE_RUNTIME')
    plan = execution_plan(before, service.owner)
    binding = dict(schema='chart-entry-binding/1', owner=service.owner,
                   workspace=workspace, event_id=event_id, preview_version=version,
                   preview_hash=before['content_hash'], preview_plan_digest=before['plan_digest'],
                   execution_digest=digest(plan), account_ref=account_ref,
                   risk_profile_hash=before['risk_profile_hash'], expires_at=before['expires_at'], port=port)
    binding['content_hash'] = binding_hash(binding)
    db = service.store.db
    old = db.execute('SELECT value FROM control WHERE name=?', (_key(plan),)).fetchone()
    if old and json.loads(old[0]) != binding:
        raise ValueError('EVENT_ALREADY_REVIEWED_WITH_DIFFERENT_PREVIEW')
    existing = db.execute('SELECT 1 FROM plan_versions WHERE plan_id=? AND version=1', (plan['plan_id'],)).fetchone()
    if existing:
        if not old:
            raise ValueError('CHART_BINDING_MISSING')
        row = service.show(plan['plan_id'], 1, now=clock())
        if row['digest'] != digest(plan):
            raise ValueError('CHART_PLAN_CONTENT_CHANGED')
        return dict(state=row['state'], plan=plan, digest=row['digest'], duplicate=True,
                    authorization_token=None, order_authority=False,
                    warning='Önceki tek kullanımlık onay kimliği yeniden üretilmez; kayıpsa planı iptal edip yeni olay kullanın.')
    # Persist source binding first. A crash can leave an unapproved orphan binding,
    # never an approved unbound plan. Lost response never rotates the approval token.
    with db:
        db.execute('INSERT OR IGNORE INTO control VALUES (?,?)', (_key(plan), json.dumps(binding, sort_keys=True)))
        db.execute('INSERT OR IGNORE INTO control VALUES (?,?)',
                   ('chart_review:'+plan['plan_id'], json.dumps(report, sort_keys=True)))
    created = service.create(plan, service.owner, now=clock())
    service.store.event('chart_preview_reviewed', dict(plan_id=plan['plan_id'], version=1,
                        event_id=event_id, preview_version=version, preview_hash=before['content_hash'],
                        account_ref=account_ref, execution_digest=digest(plan)))
    return {**created, 'duplicate': False, 'source_binding': binding,
            'account_preflight': report['account_preflight'], 'order_authority': False,
            'warning': 'Demo planı onay bekliyor. Bu komut onay veya emir oluşturmaz; approve ve run --execute-demo ayrı yerel işlemlerdir.'}


def guard_chart_entry(service, exchange, limits, plan, *, provider_factory=local_preview_provider,
                      clock=time.time, acceptance=require_demo_acceptance):
    """All entry paths use this guard, including ordinary plans run and restarts.

    No source check is required for protective exits. Missing source evidence must
    stop new entries, never stop an existing position's protection.
    """
    if not plan.get('analysis_ref', '').startswith(PREFIX):
        return False
    try:
        acceptance()
        if any(s['plan_ref']['plan_id'] != plan['plan_id'] for s in service.store.sessions()):
            raise ValueError()
        row = service.store.db.execute('SELECT value FROM control WHERE name=?', (_key(plan),)).fetchone()
        if row is None:
            raise ValueError()
        b = json.loads(row[0])
        if (b['content_hash'] != binding_hash({k: v for k, v in b.items() if k != 'content_hash'})
                or b['schema'] != 'chart-entry-binding/1' or b['owner'] != service.owner
                or b['account_ref'] != _account(exchange) or b['execution_digest'] != digest(plan)
                or b['risk_profile_hash'] != binding_hash({k: str(v) for k, v in asdict(limits).items()})
                or clock() >= min(b['expires_at'], timestamp(plan['expires_at']))
                or plan['analysis_ref'] != PREFIX + b['event_id']):
            raise ValueError()
        body, _ = checked_preview(provider_factory(b['workspace'], b['event_id'], b['preview_version'], b['port']),
                                  limits, clock=clock)
        if (body['content_hash'] != b['preview_hash'] or body['plan_digest'] != b['preview_plan_digest']
                or (body['workspace_id'], body['event_id'], body['version']) != (b['workspace'], b['event_id'], b['preview_version'])
                or execution_plan(body, service.owner) != plan):
            raise ValueError()
        return True
    except Exception:
        raise ValueError('CHART_ENTRY_SOURCE_NOT_CURRENT') from None


def local_review(settings, workspace, event_id, version, port):
    from agentrader.shared.config import Config
    from agentrader.shared.exchange import DemoExchange
    from agentrader.shared.locking import execution_lock
    from agentrader.bot.plans import PlanService
    from agentrader.bot.risk import RiskLimits
    from agentrader.shared.state import StateStore
    provider = local_preview_provider(workspace, event_id, version, port)
    try:
        # Account credentials never enter the API process. Store and global runtime
        # lock are the same ones used by the existing local plans commands.
        with execution_lock():
            store = StateStore(settings.execution_database)
            try:
                return review_preview(PlanService(store, settings.owner), provider,
                                      DemoExchange(Config.load()), RiskLimits.load('risk-demo.json'),
                                      workspace=workspace, event_id=event_id, version=version, port=port)
            finally:
                store.close()
    except Exception:
        raise ValueError('CHART_PREVIEW_REVIEW_FAILED') from None
