"""Authenticated queue-only terminal routes. No credential loading in HTTP."""
from fastapi import APIRouter,Request
from fastapi.responses import JSONResponse
from .drawings import body
from agentrader.application.bot_inbox import BotInbox


def bot_router(settings):
    router=APIRouter();inbox=BotInbox(settings)

    @router.get('/api/bot/status')
    def status():return inbox.status()

    @router.get('/api/bot/jobs')
    def recent(summary:bool=False,include_snapshots:bool=True):return {'jobs':inbox.recent(summary=summary,include_snapshots=include_snapshots)}

    @router.post('/api/bot/jobs')
    async def submit(request:Request):
        data=await body(request,'request_id action payload',limit=40000)
        result=inbox.accept(data)
        return JSONResponse(result,status_code=200 if result['duplicate'] else 202)

    @router.get('/api/bot/jobs/{job_id}')
    def show(job_id:str):return inbox.show(job_id)

    return router
