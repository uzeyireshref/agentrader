"""Authenticated metadata CRUD; never invokes exchange execution."""
import json

from fastapi import APIRouter, Request

from agentrader.chart.drawings.service import DrawingError, DrawingService, management
from agentrader.chart.drawings.contracts import registry, legacy_contract, capability, LEGACY_KINDS
from agentrader.chart.drawings.channel_family import SCHEMA as FAMILY_SCHEMA
from agentrader.chart.drawings.notes import DrawingNotes
from agentrader.chart.drawings.packages import DrawingPackages,MAX_BYTES


class DrawingFormatRequired(DrawingError):
    code = 'DRAWING_FORMAT_VERSION_REQUIRED'


def format_check(item, version):
    if type(version) is not int or version not in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10):
        raise DrawingFormatRequired()
    if item['geometry'].get('schema')=='chart-fibonacci-projection/1' and version<10:raise DrawingFormatRequired()
    if item['geometry'].get('schema') == FAMILY_SCHEMA and version < 9:
        raise DrawingFormatRequired()
    if item['geometry'].get('schema') == 'chart-annotation/1' and version < 8:
        raise DrawingFormatRequired()
    if item['geometry'].get('schema') == 'chart-fibonacci/1' and version < 7:
        raise DrawingFormatRequired()
    if item['geometry'].get('schema') == 'chart-channel/1' and version < 6:
        raise DrawingFormatRequired()
    if item['geometry'].get('schema') == 'chart-position/1' and version < 5:
        raise DrawingFormatRequired()
    if item.get('management', management()) != management() and version < 4:
        raise DrawingFormatRequired()
    if item['geometry']['kind'] == 'ruler' and version < 2:
        raise DrawingFormatRequired()
    if item['geometry'].get('schema') in ('chart-line/1', 'chart-zone/1') and version < 3:
        raise DrawingFormatRequired()
    return item



async def body(request, fields, limit=8192):
    if request.headers.get('content-type', '').split(';')[0].strip().lower() != 'application/json':
        raise DrawingError()
    data = bytearray()
    async for chunk in request.stream():
        data.extend(chunk)
        if len(data) > limit:
            raise DrawingError()
    def object_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise DrawingError()
            result[key] = value
        return result
    def invalid_constant(value):
        raise DrawingError()
    try:
        value = json.loads(data.decode('utf-8'), object_pairs_hook=object_pairs, parse_constant=invalid_constant)
    except (ValueError, UnicodeError, RecursionError):
        raise DrawingError() from None
    if not isinstance(value, dict) or set(value) != set(fields.split()):
        raise DrawingError()
    return value


def drawing_router(service: DrawingService):
    router = APIRouter()
    def acting(request):
        return DrawingService(service.database,service.owner,service.clock,actor=request.state.drawing_actor)
    def notes(request):
        return DrawingNotes(service.database,service.owner,service.clock,actor=request.state.drawing_actor)

    @router.post('/api/workspaces/{workspace_id}/drawing-packages/export')
    async def export_package(workspace_id:str,request:Request):
        data=await body(request,'symbol interval targets')
        return DrawingPackages(service.database,service.owner,service.clock).export(workspace_id,**data)

    @router.post('/api/workspaces/{workspace_id}/drawing-packages/paste')
    async def paste_package(workspace_id:str,request:Request):
        data=await body(request,'request_id symbol interval package',limit=MAX_BYTES+4096)
        return DrawingPackages(service.database,service.owner,service.clock,actor=request.state.drawing_actor).paste(workspace_id,**data)

    @router.get('/api/drawings/{drawing_id}/history')
    def drawing_history(drawing_id:str,limit:int=50,offset:int=0):
        return service.history(drawing_id,limit,offset)

    @router.get('/api/drawings/{drawing_id}/notes')
    def linked_note(drawing_id:str,revision:int=0):
        return DrawingNotes(service.database,service.owner,service.clock).show_note(drawing_id,revision)

    @router.put('/api/drawings/{drawing_id}/notes')
    async def save_note(drawing_id:str,request:Request):
        data=await body(request,'request_id expected_revision expected_drawing_revision text',limit=24576)
        return notes(request).save_note(drawing_id,**data)

    @router.delete('/api/drawings/{drawing_id}/notes')
    async def delete_note(drawing_id:str,request:Request):
        data=await body(request,'request_id expected_revision expected_drawing_revision')
        return notes(request).save_note(drawing_id,text='',deleted=True,**data)

    @router.get('/api/chart-tools')
    def chart_tools():
        return registry()

    @router.get('/api/chart-tools/{category}/{kind}')
    def chart_tool(category: str, kind: str, version: int = 1, record_schema: str | None = None):
        return capability(category, kind, version, record_schema)

    @router.get('/api/drawings/{drawing_id}/contract')
    def contract(drawing_id: str):
        return legacy_contract(service.show(drawing_id))

    @router.get('/api/workspaces/{workspace_id}')
    def workspace(workspace_id: str):
        return service.workspace(workspace_id)

    @router.put('/api/workspaces/{workspace_id}')
    async def save_workspace(workspace_id: str, request: Request):
        data = await body(request, 'request_id expected_revision preferences')
        return service.save_workspace(workspace_id, **data)

    @router.get('/api/workspaces/{workspace_id}/drawings')
    def drawings(workspace_id: str, symbol: str = 'BTCUSDT', format_version: int = 1):
        if format_version not in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10):
            raise DrawingFormatRequired()
        return {'drawings': [item for item in service.list(workspace_id, symbol)
                             if (format_version>=10 or item['geometry'].get('schema')!='chart-fibonacci-projection/1') and (format_version >= 9 or item['geometry'].get('schema') != FAMILY_SCHEMA) and (format_version >= 8 or item['geometry'].get('schema') != 'chart-annotation/1') and (format_version >= 7 or item['geometry'].get('schema') != 'chart-fibonacci/1') and (format_version >= 6 or item['geometry'].get('schema') != 'chart-channel/1') and (format_version >= 5 or item['geometry'].get('schema') != 'chart-position/1') and (format_version >= 4 or item['management'] == management()) and (format_version >= 3 or
                                 item['geometry'].get('schema') not in ('chart-line/1', 'chart-zone/1') and
                                 (format_version == 2 or item['geometry']['kind'] in LEGACY_KINDS))]}

    @router.post('/api/workspaces/{workspace_id}/drawing-operations')
    async def operations(workspace_id: str, request: Request, format_version: int = 1):
        if format_version not in (4, 5, 6, 7, 8, 9, 10):
            raise DrawingFormatRequired()
        data = await body(request, 'request_id operations', limit=65536)
        if isinstance(data['operations'], list):
            for op in data['operations']:
                if isinstance(op, dict) and op.get('drawing_id') is not None:
                    format_check(service.show(op['drawing_id']), format_version)
                if isinstance(op, dict) and isinstance(op.get('geometry'), dict):
                    format_check({'geometry': op['geometry']}, format_version)
        return acting(request).operations(workspace_id, **data)

    @router.post('/api/workspaces/{workspace_id}/drawings', status_code=201)
    async def create(workspace_id: str, request: Request, format_version: int = 1):
        if format_version not in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10):
            raise DrawingFormatRequired()
        data = await body(request, 'request_id geometry')
        if isinstance(data['geometry'], dict) and data['geometry'].get('schema') in ('chart-fibonacci-projection/1', FAMILY_SCHEMA, 'chart-line/1', 'chart-zone/1', 'chart-position/1', 'chart-channel/1', 'chart-fibonacci/1', 'chart-annotation/1'):
            format_check({'geometry': data['geometry']}, format_version)
        return acting(request).create(workspace_id, data['request_id'], data['geometry'])

    @router.get('/api/drawings/{drawing_id}')
    def show(drawing_id: str, format_version: int = 1):
        return format_check(service.show(drawing_id), format_version)

    @router.patch('/api/drawings/{drawing_id}')
    async def update(drawing_id: str, request: Request, format_version: int = 1):
        format_check(service.show(drawing_id), format_version)
        data = await body(request, 'request_id expected_revision geometry')
        if isinstance(data['geometry'], dict) and data['geometry'].get('schema') in ('chart-fibonacci-projection/1', FAMILY_SCHEMA, 'chart-line/1', 'chart-zone/1', 'chart-position/1', 'chart-channel/1', 'chart-fibonacci/1', 'chart-annotation/1'):
            format_check({'geometry': data['geometry']}, format_version)
        return acting(request).update(drawing_id, data['request_id'], data['expected_revision'], data['geometry'])

    @router.delete('/api/drawings/{drawing_id}')
    async def delete(drawing_id: str, request: Request, format_version: int = 1):
        format_check(service.show(drawing_id), format_version)
        data = await body(request, 'request_id expected_revision')
        return acting(request).update(drawing_id, data['request_id'], data['expected_revision'], deleted=True)

    return router
