import re
from fastapi import APIRouter, Request
from .drawings import body
from agentrader.integration.chart_approval import ApprovalInbox, ApprovalError, plan_view
from agentrader.chart.drawings.service import identifier
from agentrader.bot.plans import digest


def chart_approval_router(settings):
    router=APIRouter();inbox=ApprovalInbox(settings)

    @router.get('/api/chart-plans')
    def review(workspace:str,event_id:str):
        identifier(workspace)
        if not re.fullmatch('[a-f0-9]{64}',event_id):raise ApprovalError('INVALID_PREVIEW_REFERENCE')
        plan_id='chart-'+digest([settings.owner,workspace,event_id])[:32]
        return dict(review=plan_view(settings,plan_id),**inbox.status())

    @router.post('/api/chart-plans/{plan_id}/approval-requests')
    async def approve(plan_id:str,request:Request):
        data=await body(request,'request_id review_hash plan_digest preview_hash account_ref ttl_seconds',limit=4096)
        return inbox.accept(plan_id,data)

    @router.get('/api/chart-approvals/{request_id}')
    def approval(request_id:str):return inbox.show(request_id)

    return router
