from fastapi import APIRouter, Request
from .drawings import body
from .session import authenticated
from agentrader.chart.ui_sessions import UIError


def ui_session_router(service,settings):
    router=APIRouter()
    def authorize(request):
        if settings.token and not authenticated(request,settings) and getattr(getattr(request.state,'drawing_actor',None),'kind',None)!='bot':raise UIError('UNAUTHORIZED',401)

    @router.put('/api/workspaces/{workspace_id}/ui-sessions/{ui_session_id}')
    async def publish(workspace_id:str,ui_session_id:str,request:Request):
        authorize(request)
        value=await body(request,'schema_version server_instance_id sequence client_time_ms visibility client_status snapshot',limit=32768)
        return service.put(workspace_id,ui_session_id,request.headers.get('x-ui-publisher-key'),value)

    @router.get('/api/workspaces/{workspace_id}/ui-sessions')
    def sessions(workspace_id:str,request:Request,policy_only:bool=False):
        authorize(request)
        return service.list(workspace_id,policy_only,bool(settings.token))

    @router.get('/api/workspaces/{workspace_id}/ui-sessions/{ui_session_id}')
    def session(workspace_id:str,ui_session_id:str,request:Request):
        authorize(request)
        return service.show(workspace_id,ui_session_id)

    return router
