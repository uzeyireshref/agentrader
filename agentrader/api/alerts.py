from fastapi import APIRouter,Request
from .drawings import body
from ..price_alerts import definition

def alert_router(service,market,worker):
    router=APIRouter()
    @router.get('/api/alerts')
    def listing():return dict(schema='price-alerts/1',alerts=service.list(),events=service.events(),scope='CLOSED_AND_SAMPLED_LIVE_CANDLE_LOCAL_HISTORY',runtime_error=worker.error,order_authority=False)
    @router.post('/api/alerts',status_code=201)
    async def create(request:Request):
        data=await body(request,'definition',limit=65536);value=definition(data['definition']);market.selection(value['symbol'],value['interval']);return service.save(value)
    @router.put('/api/alerts/{alert_id}')
    async def edit(alert_id:str,request:Request):
        data=await body(request,'definition revision',limit=65536);value=definition(data['definition']);market.selection(value['symbol'],value['interval']);return service.save(value,alert_id,data['revision'])
    @router.post('/api/alerts/{alert_id}/action')
    async def action(alert_id:str,request:Request):
        data=await body(request,'revision action');service.action(alert_id,**data);return {'ok':True}
    return router
