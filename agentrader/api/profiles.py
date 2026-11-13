from fastapi import APIRouter,Request
from .drawings import body
from ..chart_profiles import ProfileService

def profile_router(service:ProfileService):
 router=APIRouter()
 @router.get('/api/workspaces/{workspace_id}/profile')
 def profile(workspace_id:str):return service.profile(workspace_id)
 @router.put('/api/workspaces/{workspace_id}/profile')
 async def save_profile(workspace_id:str,request:Request):
  data=await body(request,'request_id expected_revision body',limit=65536)
  return service.save_profile(workspace_id,**data)
 @router.get('/api/workspaces/{workspace_id}/templates')
 def templates(workspace_id:str):return service.templates(workspace_id)
 @router.get('/api/workspaces/{workspace_id}/templates/{template_id}')
 def template(workspace_id:str,template_id:str,revision:int=0):return service.template(workspace_id,template_id,revision)
 @router.put('/api/workspaces/{workspace_id}/templates/{template_id}')
 async def save_template(workspace_id:str,template_id:str,request:Request):
  data=await body(request,'request_id expected_revision name body',limit=65536)
  return service.save_template(workspace_id,template_id,**data)
 @router.post('/api/workspaces/{workspace_id}/template-restore')
 async def restore(workspace_id:str,request:Request):
  data=await body(request,'request_id template_id template_revision expected_profile_revision expected_indicator_revision symbol interval expected_drawings apply_drawing_styles',limit=65536)
  return service.restore(workspace_id,**data)
 return router
