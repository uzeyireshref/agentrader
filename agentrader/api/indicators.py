from fastapi import APIRouter,Request
from .drawings import body
from ..indicator_config import IndicatorService

def indicator_router(service:IndicatorService):
 router=APIRouter()
 @router.get('/api/workspaces/{workspace_id}/indicators')
 def load(workspace_id:str,format_version:int=1):return service.load(workspace_id,format_version)
 @router.put('/api/workspaces/{workspace_id}/indicators')
 async def save(workspace_id:str,request:Request,format_version:int=1):
  data=await body(request,'request_id expected_revision indicators')
  return service.save(workspace_id,format_version=format_version,**data)
 return router
