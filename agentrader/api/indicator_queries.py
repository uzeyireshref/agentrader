"""Bounded read-only indicator queries under the existing local API boundary."""
import asyncio
from fastapi import APIRouter, Request
from .drawings import body


def indicator_query_router(service):
    router=APIRouter()

    @router.post('/api/workspaces/{workspace_id}/indicator-queries')
    async def indicator_queries(workspace_id: str, request: Request):
        data=await body(request,'schema_version context queries',limit=65536)
        return await asyncio.to_thread(service.run,workspace_id,data['schema_version'],data['context'],data['queries'])

    return router
