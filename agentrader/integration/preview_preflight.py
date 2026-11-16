"""Local CLI bridge from a live chart preview to read-only demo account checks."""
from dataclasses import asdict
import copy
import time

from agentrader.chart.chart_bindings import binding_hash
from agentrader.shared.exchange import PUBLIC, PRIVATE
from agentrader.shared.market_environment import SOURCE, ENVIRONMENT
from agentrader.bot.plan_v2 import validate_v2
from agentrader.bot.v2_preflight import collect_flat_snapshot, prepare_single


class ReadOnlyDemoAccount:
    """Expose only allowlisted GET requests; no settings, orders or listen keys."""
    def __init__(self, exchange):
        self._exchange = exchange

    @property
    def config(self):
        return self._exchange.config

    @property
    def offset_ms(self):
        return getattr(self._exchange,'offset_ms',0)

    def request(self, method, path, params=None):
        if method != 'GET' or path not in PUBLIC | PRIVATE:
            raise ValueError('READ_ONLY_DEMO_REQUEST_REQUIRED')
        return self._exchange.request(method, path, params)

    def get(self, path, params=None):
        return self.request('GET', path, params)

    def sync_time(self):
        # The concrete adapter's implementation performs only GET /time.
        return self._exchange.sync_time()

    def read_symbol_metadata(self,symbol):
        # Fixed GET-only metadata capability, never a general writer delegation.
        from agentrader.bot.v2_preflight import symbol_metadata
        result=symbol_metadata(self._exchange,symbol)
        if isinstance(getattr(self,'calls',None),list):
            self.calls.extend(dict(method='GET',path=p,private=p in PRIVATE) for p in
                ('/fapi/v1/symbolConfig','/fapi/v1/leverageBracket','/fapi/v1/exchangeInfo'))
        return result


def checked_preview(provider, limits, *, clock=time.time):
    """Validate the persisted preview envelope, excluding live GET annotations."""
    body = copy.deepcopy(provider())
    if (body.get('state') != 'PREVIEW_ONLY' or body.get('reasons')
            or body.get('source') != SOURCE or body.get('environment') != ENVIRONMENT
            or body.get('order_authority') is not False
            or body.get('execution_eligible') is not False
            or body.get('approval_state') != 'NOT_REQUESTED'
            or clock() >= body['expires_at']):
        raise ValueError('PREVIEW_NOT_CURRENT')
    stored = {k: v for k, v in body.items() if k not in
              ('state', 'reasons', 'current_last_price', 'content_hash')}
    if (binding_hash(stored) != body['content_hash']
            or binding_hash(body['plan']) != body['plan_digest']
            or body['risk_profile_hash'] != binding_hash({k: str(v) for k, v in asdict(limits).items()})):
        raise ValueError('PREVIEW_INTEGRITY_OR_RISK_CHANGED')
    plan = validate_v2(body['plan'])
    if plan['execution']['strategy'] != 'SINGLE' or plan['entry']['condition'] != 'LIMIT':
        raise ValueError('PREVIEW_SINGLE_LIMIT_REQUIRED')
    return body, plan


def preflight_preview(provider, exchange, limits, *, clock=time.time,
                      collect=collect_flat_snapshot, prepare=prepare_single):
    """Recheck the exact preview after account I/O. Never creates/approves a plan."""
    before, plan = checked_preview(provider, limits, clock=clock)
    snapshot = collect(ReadOnlyDemoAccount(exchange), plan['symbol'], limits)
    result = prepare(plan, snapshot, limits)
    after, _ = checked_preview(provider, limits, clock=clock)
    if before['content_hash'] != after['content_hash']:
        raise ValueError('PREVIEW_CHANGED_DURING_PREFLIGHT')
    return dict(schema='preview-account-preflight/1', event_id=before['event_id'],
                version=before['version'], preview_hash=before['content_hash'],
                plan_digest=before['plan_digest'], checked_at=clock(),
                expires_at=before['expires_at'], account_preflight=result,
                read_only=True, executed=False, order_authority=False,
                execution_eligible=False, approval_state='NOT_REQUESTED',
                warning='Anlık demo hesap kontrolüdür; işlem onayı veya yürütme yetkisi değildir.')


def local_preview_provider(workspace, event_id, version, port):
    """Fixed loopback GET only; no redirect, proxy, credentials or arbitrary URL."""
    import json
    import re
    from urllib.request import build_opener, ProxyHandler, Request
    from agentrader.chart.drawings.service import identifier
    from agentrader.shared.exchange import NoRedirect
    identifier(workspace)
    if not re.fullmatch('[a-f0-9]{64}', event_id) or version < 1 or not 1 <= port <= 65535:
        raise ValueError('INVALID_PREVIEW_REFERENCE')
    opener = build_opener(ProxyHandler({}), NoRedirect())
    url = f'http://127.0.0.1:{port}/api/workspaces/{workspace}/shadow-events/{event_id}/preview?version={version}'
    def provider():
        with opener.open(Request(url), timeout=15) as response:
            raw = response.read(131073)
        if len(raw) > 131072:
            raise ValueError('PREVIEW_RESPONSE_TOO_LARGE')
        body = json.loads(raw)
        if (body.get('event_id'), body.get('version'), body.get('workspace_id')) != (event_id, version, workspace):
            raise ValueError('PREVIEW_REFERENCE_MISMATCH')
        return body
    return provider


def local_preflight(workspace, event_id, version, port):
    """Credentials stay in this explicit local CLI process, never in the web API."""
    from agentrader.shared.config import Config
    from agentrader.shared.exchange import DemoExchange
    from agentrader.bot.risk import RiskLimits
    provider = local_preview_provider(workspace, event_id, version, port)
    try:
        return preflight_preview(provider, DemoExchange(Config.load()), RiskLimits.load('risk-demo.json'))
    except Exception:
        # Never echo signed URLs, account payloads, credentials or transport errors.
        raise ValueError('PREVIEW_ACCOUNT_PREFLIGHT_FAILED') from None
