from agentrader.integration.signal_previews import SignalPreviews
from agentrader.integration.shadow_tracking import ShadowTracking, ShadowWorker
from agentrader.chart.price_alerts import PriceAlerts, PriceAlertWorker
from .alerts import alert_router
"""Local FastAPI adapter; no account credentials or exchange writes."""
from contextlib import asynccontextmanager
import asyncio
import hmac
import json
import re
import sqlite3

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from agentrader.chart.chart_market import ChartMarket, InvalidMarket, MarketUnavailable
from agentrader.shared.market_feed import MarketFeedHub
from .market import market_router
from .bindings import binding_router
from .chart_approvals import chart_approval_router
from agentrader.chart.chart_bindings import BindingService
from .profiles import profile_router
from agentrader.chart.chart_profiles import ProfileService
from .indicators import indicator_router
from .chart_context import chart_context_router
from agentrader.chart.chart_context import ChartContext
from .chart_queries import chart_query_router
from agentrader.chart.chart_queries import ChartQueries
from .indicator_queries import indicator_query_router
from agentrader.chart.indicator_queries import IndicatorQueries
from .ui_sessions import ui_session_router
from agentrader.chart.ui_sessions import UISessions
from agentrader.chart.indicator_config import IndicatorService
from .drawings import drawing_router
from .session import authenticated, session_router
from agentrader.chart.drawings.service import DrawingError, DrawingService
from agentrader.chart.drawings.actors import DrawingActor

from ..application.commands import InvalidCommand, CommandConflict, CommandNotFound
from ..application.queries import StorageUnavailable
from ..application.service import ApplicationService
from ..application.settings import WebSettings


MAX_BODY = 8192


def _error(code, status):
    return JSONResponse({'error': {'code': code}}, status_code=status)


def _object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('Duplicate field')
        value[key] = item
    return value


def _constant(value):
    raise ValueError('Non-finite JSON')


def create_app(settings=None, *, service=None, market=None, hub=None, previews=None):
    settings = settings or WebSettings.load()
    service = service or ApplicationService(settings)
    market = market or ChartMarket(settings.market_database)
    hub = hub or MarketFeedHub(market)

    alerts = PriceAlerts(settings.application_database, settings.owner)
    alert_worker = PriceAlertWorker(alerts, hub)
    shadow = ShadowTracking(settings.application_database, settings.owner)
    shadow_worker = ShadowWorker(shadow, hub)
    previews = previews or SignalPreviews(settings.application_database,settings.owner,hub)

    @asynccontextmanager
    async def lifespan(app):
        service.initialize()
        shadow_worker.start()
        alert_worker.start()
        try:
            yield
        finally:
            await asyncio.to_thread(shadow_worker.close)
            await asyncio.to_thread(alert_worker.close)
            await asyncio.to_thread(hub.close)

    app = FastAPI(title='Agentrader local API', version='1', lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.include_router(alert_router(alerts, market, alert_worker))
    app.state.shadow_worker = shadow_worker
    app.state.alert_worker = alert_worker
    app.state.service = service
    app.state.market = market
    app.state.market_hub = hub
    app.state.ui_sessions = UISessions(settings.application_database, settings.owner)
    app.include_router(ui_session_router(app.state.ui_sessions, settings))
    app.include_router(market_router(market, hub, ui_policy=app.state.ui_sessions.policy(bool(settings.token))))
    app.include_router(session_router(settings))
    app.include_router(drawing_router(DrawingService(settings.application_database, settings.owner)))
    app.include_router(indicator_router(IndicatorService(settings.application_database, settings.owner)))
    app.state.chart_context = ChartContext(settings.application_database, settings.owner, hub, ui_sessions=app.state.ui_sessions)
    app.include_router(chart_context_router(app.state.chart_context, settings))
    app.state.chart_queries = ChartQueries(app.state.chart_context)
    app.include_router(chart_query_router(app.state.chart_queries))
    app.state.indicator_queries = IndicatorQueries(app.state.chart_context)
    app.include_router(indicator_query_router(app.state.indicator_queries))
    app.include_router(profile_router(ProfileService(settings.application_database, settings.owner)))
    app.include_router(binding_router(BindingService(settings.application_database, settings.owner), hub, shadow=shadow, previews=previews))
    app.include_router(chart_approval_router(settings))

    @app.middleware('http')
    async def local_boundary(request, call_next):
        # Host validation also prevents a hostile DNS name reaching localhost.
        authority = request.headers.get('host', '')
        if not re.fullmatch(r'(?:127\.0\.0\.1|localhost)(?::[0-9]{1,5})?', authority):
            return _error('INVALID_HOST', 400)
        if request.url.scheme != 'http':
            return _error('LOCAL_HTTP_REQUIRED', 400)
        origin = request.headers.get('origin')
        if origin is not None and origin != 'http://' + authority:
            return _error('CROSS_ORIGIN_DENIED', 403)
        request.state.drawing_actor=DrawingActor('manual',settings.owner)
        supplied=request.headers.get('authorization','')
        is_bot=bool(settings.bot_token) and hmac.compare_digest(supplied.encode(),('Bearer '+settings.bot_token).encode())
        claimed_namespace=request.headers.get('x-chart-bot-namespace')
        expected_actor=DrawingActor('bot','bot:'+settings.bot_id,settings.bot_id,settings.strategy_id) if is_bot else None
        if claimed_namespace is not None and (expected_actor is None or not hmac.compare_digest(claimed_namespace.encode(),expected_actor.namespace.encode())):
            return _error('BOT_NAMESPACE_MISMATCH',403)
        if is_bot:
            request.state.drawing_actor=DrawingActor('bot','bot:'+settings.bot_id,settings.bot_id,settings.strategy_id)
            path=request.url.path;method=request.method
            read_allowed=method=='GET' and bool(re.fullmatch(r'/api/(?:chart-actor|chart-tools(?:/[^/]+/[^/]+)?|drawings/[A-Za-z0-9_-]+(?:/(?:contract|notes|history))?|workspaces/[A-Za-z0-9_-]+/(?:drawings|chart-context|indicators|ui-sessions(?:/[A-Za-z0-9_-]+)?))',path))
            write_allowed=(method in ('PATCH','DELETE') and bool(re.fullmatch(r'/api/drawings/[A-Za-z0-9_-]+',path))
                           or method in ('PUT','DELETE') and bool(re.fullmatch(r'/api/drawings/[A-Za-z0-9_-]+/notes',path))
                           or method=='POST' and bool(re.fullmatch(r'/api/(?:workspaces/[A-Za-z0-9_-]+/(?:drawings|drawing-operations|drawing-packages/(?:export|paste)|chart-queries|indicator-queries)|drawings/[A-Za-z0-9_-]+/queries)',path)))
            if not (read_allowed or write_allowed):return _error('BOT_ROUTE_FORBIDDEN',403)
        elif settings.bot_token and request.method not in ('GET','HEAD','OPTIONS') and request.url.path.startswith('/api/') and request.url.path!='/api/session' and not authenticated(request,settings):
            return _error('UNAUTHORIZED',401)
        private = (request.url.path.startswith('/api/commands')
                   or request.url.path.startswith('/api/chart-plans')
                   or request.url.path.startswith('/api/chart-approvals')
                   or request.url.path == '/api/status'
                   or request.url.path in ('/api/operations','/api/operations/metrics'))
        if private:
            if not settings.token:
                return _error('PRIVATE_API_DISABLED', 503)
            if not authenticated(request, settings):
                response = _error('UNAUTHORIZED', 401)
                response.headers['WWW-Authenticate'] = 'Bearer'
                return response
        try:
            response = await call_next(request)
        except DrawingError as exc:
            response = _error(exc.code, exc.status)
        except InvalidMarket:
            response = _error('INVALID_MARKET_SELECTION', 422)
        except MarketUnavailable:
            response = _error('MARKET_UNAVAILABLE', 503)
        except (StorageUnavailable, sqlite3.Error, OSError):
            response = _error('LOCAL_STORAGE_UNAVAILABLE', 503)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    @app.get('/api/chart-actor')
    def chart_actor(request:Request):
        actor=request.state.drawing_actor
        from agentrader.shared.market_environment import SOURCE,ENVIRONMENT
        return dict(schema_version='chart-actor/1',actor=actor.view(),namespace=actor.namespace,
                    market=dict(source=SOURCE,environment=ENVIRONMENT,product='USD-M',price_type='LAST_PRICE'),
                    manual_writes_allowed=actor.kind=='manual',order_authority=False)

    @app.get('/api/health')
    def health():
        return service.health() | {'market_feed': 'AVAILABLE_ON_DEMAND', 'web_chart_available': (settings.frontend_directory / 'index.html').is_file(), 'signal_previews': {'mode': 'PREVIEW_ONLY', 'order_authority': False}, 'shadow_tracking': {'mode': 'SHADOW_ONLY', 'worker_running': bool(shadow_worker.thread and shadow_worker.thread.is_alive()), 'worker_error': shadow_worker.error, 'order_authority': False}}

    @app.get('/api/capabilities')
    def capabilities():
        return service.capabilities()

    @app.get('/api/status')
    def status():
        return service.status()

    @app.get('/api/operations')
    def operations():
        return service.operations()

    @app.get('/api/operations/metrics')
    def operation_metrics():
        from agentrader.application.operations import prometheus
        return PlainTextResponse(prometheus(service.operations()),media_type='text/plain; version=0.0.4')

    @app.post('/api/commands')
    async def accept(request: Request):
        if request.headers.get('content-type', '').split(';', 1)[0].strip().lower() != 'application/json':
            return _error('JSON_REQUIRED', 415)
        data = bytearray()
        async for chunk in request.stream():
            data.extend(chunk)
            if len(data) > MAX_BODY:
                return _error('BODY_TOO_LARGE', 413)
        try:
            command = json.loads(bytes(data).decode('utf-8'), object_pairs_hook=_object, parse_constant=_constant)
            result = service.accept_command(command)
        except (ValueError, UnicodeError, RecursionError) as exc:
            return _error('COMMAND_CONFLICT' if isinstance(exc, CommandConflict) else 'INVALID_COMMAND',
                          409 if isinstance(exc, CommandConflict) else 422)
        return JSONResponse(result, status_code=200 if result['duplicate'] else 202)

    @app.get('/api/commands/{request_id}')
    def command(request_id: str):
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', request_id):
            return _error('COMMAND_NOT_FOUND', 404)
        try:
            return service.command(request_id)
        except CommandNotFound:
            return _error('COMMAND_NOT_FOUND', 404)

    @app.get('/')
    def terminal():
        index = settings.frontend_directory / 'index.html'
        if not index.is_file():
            return _error('FRONTEND_NOT_BUILT', 503)
        return FileResponse(index)

    for name in ('assets', 'licenses'):
        directory = settings.frontend_directory / name
        if directory.is_dir():
            app.mount('/' + name, StaticFiles(directory=directory), name=name)

    return app
