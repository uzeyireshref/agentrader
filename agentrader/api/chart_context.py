"""Read-only chart context under the existing local API boundary."""
from fastapi import APIRouter, Query, Request
from agentrader.shared.market_environment import SOURCE, ENVIRONMENT
from .session import authenticated
from agentrader.chart.ui_sessions import UIError


def chart_context_router(service, settings=None):
    router = APIRouter()

    @router.get('/api/workspaces/{workspace_id}/chart-context')
    def chart_context(workspace_id: str, request: Request, symbol: str | None = None, interval: str | None = None,
                      source: str = SOURCE, environment: str = ENVIRONMENT,
                      product: str = 'USD-M', price_type: str = 'LAST_PRICE',
                      required_closed_bars: int = Query(2, ge=1, le=499), include_open: bool = False,
                      limit: int = Query(100, ge=1, le=200), offset: int = Query(0, ge=0, le=1000000),
                      expected_context_id: str | None = Query(None, min_length=64, max_length=64), ui_session_id: str | None = None):
        if ui_session_id is not None and settings is not None and settings.token and not authenticated(request,settings) and getattr(getattr(request.state,'drawing_actor',None),'kind',None)!='bot':
            raise UIError('UNAUTHORIZED',401)
        return service.read(workspace_id, symbol=symbol, interval=interval, source=source, environment=environment,
                            product=product, price_type=price_type, required_closed_bars=required_closed_bars,
                            include_open=include_open, limit=limit, offset=offset, expected_context_id=expected_context_id, ui_session_id=ui_session_id)

    return router
