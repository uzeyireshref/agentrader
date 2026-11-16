"""Single and batch geometry queries share service, errors and resource limits."""
import asyncio
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from .drawings import body


def chart_query_router(service):
    router = APIRouter()

    @router.post('/api/workspaces/{workspace_id}/chart-queries')
    async def batch(workspace_id: str, request: Request):
        data = await body(request, 'schema_version context queries', limit=65536)
        return await asyncio.to_thread(service.run, workspace_id, data['schema_version'], data['context'], data['queries'])

    @router.post('/api/drawings/{drawing_id}/queries')
    async def single(drawing_id: str, request: Request):
        data = await body(request, 'schema_version context query', limit=8192)
        result = await asyncio.to_thread(service.single, drawing_id, data['schema_version'], data['context'], data['query'])
        return JSONResponse(result, status_code=result['results'][0]['http_status'])

    return router
