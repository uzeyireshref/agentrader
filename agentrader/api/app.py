from ..price_alerts import PriceAlerts, PriceAlertWorker
from .alerts import alert_router
"""Local FastAPI adapter; no account credentials or exchange writes."""
from contextlib import asynccontextmanager
import asyncio
import hmac
import json
import re
import sqlite3

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from ..chart_market import ChartMarket, InvalidMarket, MarketUnavailable
from ..market_feed import MarketFeedHub
from .market import market_router
from .bindings import binding_router
from ..chart_bindings import BindingService
from .profiles import profile_router
from ..chart_profiles import ProfileService
from .indicators import indicator_router
from ..indicator_config import IndicatorService
from .drawings import drawing_router
from .session import authenticated, session_router
from ..drawings.service import DrawingError, DrawingService

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


def create_app(settings=None, *, service=None, market=None, hub=None):
    settings = settings or WebSettings.load()
    service = service or ApplicationService(settings)
    market = market or ChartMarket(settings.market_database)
    hub = hub or MarketFeedHub(market)

    alerts = PriceAlerts(settings.application_database, settings.owner)
    alert_worker = PriceAlertWorker(alerts, hub)

    @asynccontextmanager
    async def lifespan(app):
        service.initialize()
        alert_worker.start()
        try:
            yield
        finally:
            await asyncio.to_thread(alert_worker.close)
            await asyncio.to_thread(hub.close)

    app = FastAPI(title='Agentrader local API', version='1', lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.include_router(alert_router(alerts, market, alert_worker))
    app.state.alert_worker = alert_worker
    app.state.service = service
    app.state.market = market
    app.state.market_hub = hub
    app.include_router(market_router(market, hub))
    app.include_router(session_router(settings))
    app.include_router(drawing_router(DrawingService(settings.application_database, settings.owner)))
    app.include_router(indicator_router(IndicatorService(settings.application_database, settings.owner)))
    app.include_router(profile_router(ProfileService(settings.application_database, settings.owner)))
    app.include_router(binding_router(BindingService(settings.application_database, settings.owner), hub))

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
        private = (request.url.path.startswith('/api/commands')
                   or request.url.path == '/api/status')
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

    @app.get('/api/health')
    def health():
        return service.health() | {'market_feed': 'AVAILABLE_ON_DEMAND', 'web_chart_available': (settings.frontend_directory / 'index.html').is_file()}

    @app.get('/api/capabilities')
    def capabilities():
        return service.capabilities()

    @app.get('/api/status')
    def status():
        return service.status()

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
