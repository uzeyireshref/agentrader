from fastapi import APIRouter,Request
from .drawings import body
from ..chart_bindings import BindingService
from ..binding_catalog import catalog
from ..binding_eligibility import inspect_binding
from ..local_chart_events import LocalChartEvents
from ..replay_report import replay_summary

def binding_router(service:BindingService,hub):
 router=APIRouter()
 events=LocalChartEvents(service.database,service.owner)
 @router.get('/api/replay-validation')
 def validation():return replay_summary()
 @router.get('/api/workspaces/{workspace_id}/local-events')
 def local_events(workspace_id:str,namespace:str='replay:local',limit:int=50):return events.list_events(workspace_id,namespace,limit)
 @router.get('/api/binding-catalog')
 def evidence():return catalog()
 @router.get('/api/workspaces/{workspace_id}/bindings')
 def listing(workspace_id:str,target_type:str|None=None,object_id:str|None=None):return service.list_bindings(workspace_id,target_type,object_id)
 @router.get('/api/workspaces/{workspace_id}/bindings/{binding_id}')
 def show(workspace_id:str,binding_id:str,revision:int=0):return service.show(workspace_id,binding_id,revision)
 @router.get('/api/workspaces/{workspace_id}/bindings/{binding_id}/eligibility')
 def eligibility(workspace_id:str,binding_id:str):return inspect_binding(service,hub,workspace_id,binding_id)
 @router.put('/api/workspaces/{workspace_id}/bindings/{binding_id}')
 async def save(workspace_id:str,binding_id:str,request:Request):
  data=await body(request,'request_id expected_binding_revision target symbol interval scale grid_times data_snapshot_hash query rule',limit=65536)
  return service.save_binding(workspace_id,binding_id,**data)
 return router
