"""Restricted chart bot adapter over official local HTTP; no exchange or SQL app writes."""
from contextlib import closing,contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import socket
import sqlite3
from urllib.error import HTTPError,URLError
from urllib.parse import urlencode,urlsplit
from urllib.request import Request,build_opener,ProxyHandler,HTTPRedirectHandler

from agentrader.chart.drawings.actors import DrawingActor
from agentrader.shared.market_environment import SOURCE,ENVIRONMENT

IDENTITY=dict(source=SOURCE,environment=ENVIRONMENT,product='USD-M',price_type='LAST_PRICE')
JOURNAL_ID=0x43423831
MAX_RESPONSE=4*1024*1024


class BotError(ValueError):
    def __init__(self,code,status=None,*,pending=False):
        self.code,self.status,self.pending=code,status,pending
        super().__init__(code)


def canonical(value):
    try:
        wire=json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False);wire.encode('utf-8');return wire
    except (ValueError,TypeError,UnicodeError,RecursionError):raise BotError('INVALID_BOT_PAYLOAD') from None


def operation_key(value):
    if not isinstance(value,str) or not 1<=len(value)<=128 or any(ord(c)<33 or ord(c)==127 for c in value):raise BotError('INVALID_OPERATION_KEY')
    try:value.encode('utf-8')
    except UnicodeError:raise BotError('INVALID_OPERATION_KEY') from None
    return value


def identifier(value):
    if not isinstance(value,str) or not re.fullmatch('[A-Za-z0-9_-]{1,64}',value):raise BotError('INVALID_BOT_IDENTIFIER')
    return value


def revision(value,zero=False):
    if type(value) is not int or not (0 if zero else 1)<=value<=1000000000:raise BotError('INVALID_BOT_REVISION')
    return value


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,request,*args,**kwargs):raise BotError('BOT_REDIRECT_FORBIDDEN',pending=request.get_method()!='GET')


class LocalHTTP:
    """No proxy, redirects, remote hosts, cookie jar or credential-bearing repr."""
    def __init__(self,base_url,token,namespace,timeout=5):
        try:parsed=urlsplit(base_url)
        except (ValueError,TypeError):raise BotError('LOCAL_CHART_URL_REQUIRED') from None
        if (parsed.scheme!='http' or parsed.hostname not in ('127.0.0.1','localhost') or parsed.username is not None
                or parsed.password is not None or parsed.path not in ('','/') or parsed.query or parsed.fragment):raise BotError('LOCAL_CHART_URL_REQUIRED')
        try:port=parsed.port
        except ValueError:raise BotError('LOCAL_CHART_URL_REQUIRED') from None
        if port is not None and not 1<=port<=65535:raise BotError('LOCAL_CHART_URL_REQUIRED')
        if not isinstance(token,str) or not re.fullmatch('[A-Za-z0-9_-]{32,256}',token):raise BotError('BOT_CREDENTIAL_REQUIRED')
        if type(timeout) not in (int,float) or not .1<=timeout<=30:raise BotError('INVALID_BOT_TIMEOUT')
        self.base_url=base_url.rstrip('/');self._token=token;self.namespace=namespace;self.timeout=timeout
        self.opener=build_opener(ProxyHandler({}),NoRedirect())

    def request(self,method,path,body=None):
        if not path.startswith('/api/') or path.startswith('//') or '#' in path:raise BotError('BOT_PATH_FORBIDDEN')
        try:data=canonical(body).encode('utf-8') if body is not None else None
        except UnicodeError:raise BotError('INVALID_BOT_PAYLOAD') from None
        if data is not None and len(data)>(528384 if path.endswith('/drawing-packages/paste') else 65536):raise BotError('BOT_REQUEST_TOO_LARGE')
        headers={'Authorization':'Bearer '+self._token,'X-Chart-Bot-Namespace':self.namespace,'Accept':'application/json'}
        if data is not None:headers['Content-Type']='application/json'
        request=Request(self.base_url+path,data=data,headers=headers,method=method)
        try:
            try:response=self.opener.open(request,timeout=self.timeout)
            except HTTPError as error:response=error
            with response:
                status=response.code;raw=response.read(MAX_RESPONSE+1)
                if len(raw)>MAX_RESPONSE:raise BotError('BOT_RESPONSE_TOO_LARGE',status,pending=method!='GET')
                if response.headers.get_content_type()!='application/json':raise BotError('INVALID_BOT_RESPONSE',status,pending=method!='GET')
            def invalid(*args):raise ValueError()
            def pairs(items):
                result={}
                for k,v in items:
                    if k in result:raise ValueError()
                    result[k]=v
                return result
            try:value=json.loads(raw.decode('utf-8'),parse_constant=invalid,object_pairs_hook=pairs)
            except (ValueError,UnicodeError,RecursionError):raise BotError('INVALID_BOT_RESPONSE',status,pending=method!='GET') from None
            if not isinstance(value,dict):raise BotError('INVALID_BOT_RESPONSE',status,pending=method!='GET')
            return status,value
        except (URLError,OSError,TimeoutError,socket.timeout):raise BotError('CHART_TRANSPORT_UNAVAILABLE',pending=method!='GET') from None


class BotJournal:
    """Durable operation intent/results; never opens the application/execution store."""
    def __init__(self,path):
        self.path=Path(path).resolve();self.path.parent.mkdir(parents=True,exist_ok=True)
        with self._connection() as db:
            appid=db.execute('PRAGMA application_id').fetchone()[0]
            tables=db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            if appid not in (0,JOURNAL_ID) or appid==0 and tables:raise BotError('NOT_A_BOT_JOURNAL')
            version=db.execute('PRAGMA user_version').fetchone()[0]
            if appid==JOURNAL_ID and version!=1:raise BotError('BOT_JOURNAL_VERSION_UNSUPPORTED')
            db.execute('PRAGMA application_id='+str(JOURNAL_ID));db.execute('PRAGMA user_version=1')
            db.execute('''CREATE TABLE IF NOT EXISTS chart_bot_operations (
                scope TEXT NOT NULL,operation_key TEXT NOT NULL,digest TEXT NOT NULL,intent TEXT NOT NULL,
                state TEXT NOT NULL,result TEXT,error_code TEXT,status INTEGER,
                PRIMARY KEY(scope,operation_key))''')

    @contextmanager
    def _connection(self,*,pending=False):
        try:
            with closing(sqlite3.connect(self.path,timeout=10)) as db,db:
                db.execute('PRAGMA synchronous=FULL');yield db
        except sqlite3.Error:raise BotError('BOT_JOURNAL_UNAVAILABLE',pending=pending) from None

    def prepare(self,scope,key,intent):
        operation_key(key)
        wire=canonical(intent);digest=hashlib.sha256(wire.encode()).hexdigest()
        with self._connection() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('INSERT OR IGNORE INTO chart_bot_operations VALUES (?,?,?,?,?,NULL,NULL,NULL)',(scope,key,digest,wire,'PENDING'))
            row=db.execute('SELECT digest,intent,state,result,error_code,status FROM chart_bot_operations WHERE scope=? AND operation_key=?',(scope,key)).fetchone()
            if row[0]!=digest:raise BotError('OPERATION_KEY_CONFLICT',409)
            return dict(intent=json.loads(row[1]),state=row[2],result=json.loads(row[3]) if row[3] else None,error_code=row[4],status=row[5])

    def finish(self,scope,key,*,result=None,error=None,status=None):
        with self._connection(pending=True) as db:
            db.execute("UPDATE chart_bot_operations SET state=?,result=?,error_code=?,status=? WHERE scope=? AND operation_key=? AND state='PENDING'",
                       ('REJECTED' if error else 'SUCCEEDED',canonical(result) if result is not None else None,error,status,scope,key))

    def pending(self,scope):
        with self._connection() as db:
            return [(key,json.loads(intent)) for key,intent in db.execute("SELECT operation_key,intent FROM chart_bot_operations WHERE scope=? AND state='PENDING' ORDER BY operation_key",(scope,))]


class ChartBot:
    """Library entry point used by a strategy/agent and the chart-bot CLI."""
    def __init__(self,base_url,token,*,bot_id,strategy_id,journal,workspace_id='main',timeout=5,attempts=2,transport=None):
        identifier(bot_id);identifier(strategy_id);identifier(workspace_id)
        if type(attempts) is not int or not 1<=attempts<=3:raise BotError('INVALID_BOT_ATTEMPTS')
        self.actor=DrawingActor('bot','bot:'+bot_id,bot_id,strategy_id);self.namespace=self.actor.namespace
        self.http=LocalHTTP(base_url,token,self.namespace,timeout);self._transport=transport or self.http
        self.workspace_id,self.attempts=workspace_id,attempts
        self.scope=hashlib.sha256(canonical([self.http.base_url,self.namespace,workspace_id]).encode()).hexdigest()
        self.journal=BotJournal(journal);self._verified=False

    def _request(self,method,path,body=None,*,query_result=False):
        status,value=self._transport.request(method,path,deepcopy(body))
        if 200<=status<300 or query_result and value.get('schema_version')=='chart-query-response/1':return value
        code=value.get('error',{}).get('code','CHART_HTTP_ERROR')
        if not isinstance(code,str) or not re.fullmatch('[A-Z0-9_]{1,80}',code):code='CHART_HTTP_ERROR'
        raise BotError(code,status,pending=status==429 or status>=500)

    def identify(self):
        result=self._request('GET','/api/chart-actor')
        if (result.get('schema_version')!='chart-actor/1' or result.get('actor')!=self.actor.view()
                or result.get('namespace')!=self.namespace or result.get('order_authority') is not False):raise BotError('BOT_IDENTITY_MISMATCH')
        self._market(result.get('market'))
        self._verified=True;return result

    def _connect(self):
        if not self._verified:self.identify()

    def discover(self):
        self._connect();result=self._request('GET','/api/chart-tools')
        if result.get('access_schema')!='chart-tool-access/1' or not isinstance(result.get('tools'),list):raise BotError('INVALID_BOT_CATALOG')
        return result

    def _market(self,market):
        if not isinstance(market,dict) or any(market.get(k)!=v for k,v in IDENTITY.items()):raise BotError('SOURCE_MISMATCH')

    def _geometry(self,value):
        if not isinstance(value,dict) or value.get('price_source')!='LAST_PRICE' or not isinstance(value.get('symbol'),str) or not re.fullmatch('[A-Z0-9]{2,20}USDT',value['symbol']):raise BotError('SOURCE_MISMATCH')
        return json.loads(canonical(value))

    def _object(self,item):
        if not isinstance(item,dict) or item.get('source')!=SOURCE or item.get('product')!='USD-M':raise BotError('SOURCE_MISMATCH')
        self._geometry(item.get('geometry'))

    def _owned(self,item):
        if not isinstance(item,dict) or not isinstance(item.get('origin'),dict):return False
        origin=item.get('origin',{})
        return origin.get('kind')=='bot' and all(origin.get(k)==getattr(self.actor,k) for k in ('actor_id','bot_id','strategy_id'))

    def get(self,drawing_id):
        self._connect();identifier(drawing_id)
        item=self._request('GET','/api/drawings/'+drawing_id+'?format_version=10')
        if item.get('drawing_id')!=drawing_id or item.get('workspace_id')!=self.workspace_id:raise BotError('BOT_WORKSPACE_MISMATCH')
        self._object(item)
        return item

    def _own(self,drawing_id):
        item=self.get(drawing_id)
        if not self._owned(item):raise BotError('BOT_OBJECT_PROTECTED',403)
        return item

    def snapshot(self,symbol,interval,*,limit=100,offset=0,expected_context_id=None,ui_session_id=None):
        self._connect();params=dict(symbol=symbol,interval=interval,limit=limit,offset=offset)
        if expected_context_id is not None:params['expected_context_id']=expected_context_id
        if ui_session_id is not None:params['ui_session_id']=identifier(ui_session_id)
        result=self._request('GET','/api/workspaces/'+self.workspace_id+'/chart-context?'+urlencode(params))
        if result.get('schema_version')!='chart-context/1' or result.get('workspace',{}).get('workspace_id')!=self.workspace_id or result.get('order_authority') is not False:raise BotError('INVALID_BOT_CONTEXT')
        self._market(result.get('market'))
        if result['market'].get('symbol')!=symbol or result['market'].get('interval')!=interval:raise BotError('SOURCE_MISMATCH')
        return result

    def find_own(self,symbol,interval):
        items=[];offset=0;context_id=None
        while True:
            page=self.snapshot(symbol,interval,offset=offset,expected_context_id=context_id)
            context_id=page['context_id'];items.extend(d for d in page['objects'] if self._owned(d))
            next_offset=page['pagination']['next_offset']
            if next_offset is None:return items
            if type(next_offset) is not int or not offset<next_offset<=1000000:raise BotError('INVALID_BOT_CONTEXT')
            offset=next_offset

    def notes(self,drawing_id,revision_number=0):
        self.get(drawing_id)
        return self._request('GET','/api/drawings/'+identifier(drawing_id)+'/notes?'+urlencode(dict(revision=revision_number)))

    def history(self,drawing_id,limit=50,offset=0):
        self.get(drawing_id)
        return self._request('GET','/api/drawings/'+identifier(drawing_id)+'/history?'+urlencode(dict(limit=limit,offset=offset)))

    def calculate(self,drawing_id,expected_revision,operation,inputs,*,symbol,interval,scale='LINEAR',context_id=None,query_id='q'):
        self._connect();identifier(drawing_id);identifier(query_id);revision(expected_revision)
        context=dict(IDENTITY,symbol=symbol,interval=interval)
        if context_id is not None:context['expected_context_id']=context_id
        body=dict(schema_version='chart-query-request/1',context=context,query=dict(query_id=query_id,expected_revision=expected_revision,operation=operation,inputs=inputs,scale=scale))
        result=self._request('POST','/api/drawings/'+drawing_id+'/queries',body,query_result=True)
        if result.get('schema_version')!='chart-query-response/1' or result.get('order_authority') is not False:raise BotError('INVALID_BOT_QUERY_RESPONSE')
        self._market(result.get('market'));return result

    def indicator_queries(self,symbol,interval,queries,*,context_id=None):
        self._connect();context=dict(IDENTITY,symbol=symbol,interval=interval)
        if context_id is not None:context['expected_context_id']=context_id
        result=self._request('POST','/api/workspaces/'+self.workspace_id+'/indicator-queries',dict(schema_version='indicator-query-request/1',context=context,queries=queries))
        if result.get('schema_version')!='indicator-query-response/1' or result.get('order_authority') is not False:raise BotError('INVALID_BOT_QUERY_RESPONSE')
        self._market(result.get('market'));return result

    def _write(self,key,kind,method,path,payload):
        operation_key(key);self._connect();payload=deepcopy(payload)
        payload['request_id']=self.namespace+'-'+hashlib.sha256((self.workspace_id+':'+key).encode()).hexdigest()[:32]
        intent=dict(kind=kind,method=method,path=path,payload=payload)
        record=self.journal.prepare(self.scope,key,intent)
        if record['state']=='REJECTED':raise BotError(record['error_code'],record['status'])
        if record['state']=='SUCCEEDED':return self._result(record['result'],key,payload['request_id'],True)
        return self._execute(key,intent)

    def _result(self,value,key,request_id,replayed=False):
        return {**deepcopy(value),'adapter':dict(namespace=self.namespace,operation_key=key,request_id=request_id,replayed=replayed,order_authority=False)}

    def _validate_intent(self,intent):
        if not isinstance(intent,dict) or set(intent)!={'kind','method','path','payload'} or not isinstance(intent['payload'],dict):raise BotError('INVALID_BOT_INTENT')
        kind,method,path=intent['kind'],intent['method'],intent['path'];payload=intent['payload']
        drawing='/api/drawings/[A-Za-z0-9_-]+'
        expected={'create':('POST','/api/workspaces/'+self.workspace_id+'/drawings?format_version=9'),
                  'operations':('POST','/api/workspaces/'+self.workspace_id+'/drawing-operations?format_version=9')}
        expected['package-paste']=('POST','/api/workspaces/'+self.workspace_id+'/drawing-packages/paste')
        if kind in expected:
            if (method,path.replace('format_version=10','format_version=9'))!=expected[kind]:raise BotError('INVALID_BOT_INTENT')
        elif kind in ('update','delete','note','delete-note'):
            if method!={'update':'PATCH','delete':'DELETE','note':'PUT','delete-note':'DELETE'}[kind] or not re.fullmatch(drawing+('/notes' if kind in ('note','delete-note') else r'\?format_version=(?:9|10)'),path):raise BotError('INVALID_BOT_INTENT')
            self._own(urlsplit(path).path.split('/')[3])
        else:raise BotError('INVALID_BOT_INTENT')
        if kind=='operations':
            for op in payload['operations']:
                if op['drawing_id'] is not None:self._own(op['drawing_id'])

    def _validate_ack(self,intent,value):
        kind,payload=intent['kind'],intent['payload']
        if kind in ('note','delete-note'):
            if (value.get('schema')!='drawing-linked-note/1' or value.get('revision')!=payload['expected_revision']+1 or value.get('target_revision')!=payload['expected_drawing_revision']
                    or value.get('drawing_id')!=urlsplit(intent['path']).path.split('/')[3] or value.get('workspace_id')!=self.workspace_id
                    or value.get('updated_by')!=self.actor.view() or kind=='note' and value.get('text')!=payload['text']
                    or value.get('deleted')!=(kind=='delete-note')):raise BotError('INVALID_BOT_WRITE_ACK',pending=True)
        else:
            expected_operations=payload['operations'] if kind=='operations' else [dict(expected_revision=0,deleted=False,**item) for item in payload['package']['items']] if kind=='package-paste' else None
            items=value.get('drawings') if expected_operations is not None else [value]
            if not isinstance(items,list) or len(items)!=(len(expected_operations) if expected_operations is not None else 1):raise BotError('INVALID_BOT_WRITE_ACK',pending=True)
            for index,item in enumerate(items):
                expected=expected_operations[index] if expected_operations is not None else payload
                if not self._owned(item) or item.get('workspace_id')!=self.workspace_id or item.get('revision')!=expected.get('expected_revision',0)+1:raise BotError('INVALID_BOT_WRITE_ACK',pending=True)
                did=expected.get('drawing_id') if expected_operations is not None else urlsplit(intent['path']).path.split('/')[3] if kind in ('update','delete') else None
                if (did is not None and item.get('drawing_id')!=did or not isinstance(item.get('drawing_id'),str)
                        or item.get('deleted')!=expected.get('deleted',kind=='delete')):raise BotError('INVALID_BOT_WRITE_ACK',pending=True)
                self._object(item)

    def _execute(self,key,intent):
        try:self._validate_intent(intent)
        except BotError as error:
            if error.pending or error.code=='CHART_TRANSPORT_UNAVAILABLE':raise BotError(error.code,error.status,pending=True) from None
            self.journal.finish(self.scope,key,error=error.code,status=error.status);raise
        for attempt in range(self.attempts):
            try:
                value=self._request(intent['method'],intent['path'],intent['payload'])
                try:self._validate_ack(intent,value)
                except BotError as error:raise BotError(error.code,error.status,pending=True) from None
                self.journal.finish(self.scope,key,result=value)
                return self._result(value,key,intent['payload']['request_id'])
            except BotError as error:
                if not error.pending:
                    self.journal.finish(self.scope,key,error=error.code,status=error.status)
                    raise
                if attempt==self.attempts-1:raise

    def resume_pending(self):
        self._connect();results=[]
        for key,intent in self.journal.pending(self.scope):results.append(self._execute(key,intent))
        return results

    def create(self,key,geometry):
        return self._write(key,'create','POST','/api/workspaces/'+self.workspace_id+'/drawings?format_version='+('10' if isinstance(geometry,dict) and geometry.get('schema')=='chart-fibonacci-projection/1' else '9'),dict(geometry=self._geometry(geometry)))

    def update(self,key,drawing_id,expected_revision,geometry):
        return self._write(key,'update','PATCH','/api/drawings/'+identifier(drawing_id)+'?format_version='+('10' if isinstance(geometry,dict) and geometry.get('schema')=='chart-fibonacci-projection/1' else '9'),dict(expected_revision=revision(expected_revision),geometry=self._geometry(geometry)))

    def delete(self,key,drawing_id,expected_revision):
        return self._write(key,'delete','DELETE','/api/drawings/'+identifier(drawing_id)+'?format_version='+('10' if self.get(drawing_id)['geometry'].get('schema')=='chart-fibonacci-projection/1' else '9'),dict(expected_revision=revision(expected_revision)))

    def save_note(self,key,drawing_id,expected_revision,expected_drawing_revision,text):
        return self._write(key,'note','PUT','/api/drawings/'+identifier(drawing_id)+'/notes',dict(expected_revision=revision(expected_revision,True),expected_drawing_revision=revision(expected_drawing_revision),text=text))

    def delete_note(self,key,drawing_id,expected_revision,expected_drawing_revision):
        return self._write(key,'delete-note','DELETE','/api/drawings/'+identifier(drawing_id)+'/notes',dict(expected_revision=revision(expected_revision),expected_drawing_revision=revision(expected_drawing_revision)))

    def operations(self,key,operations):
        if not isinstance(operations,list) or not 1<=len(operations)<=20:raise BotError('INVALID_BOT_OPERATIONS')
        for op in operations:
            if not isinstance(op,dict) or set(op)!={'drawing_id','expected_revision','geometry','management','deleted'}:raise BotError('INVALID_BOT_OPERATIONS')
            if op['drawing_id'] is not None:identifier(op['drawing_id'])
            revision(op['expected_revision'],op['drawing_id'] is None);self._geometry(op['geometry'])
        return self._write(key,'operations','POST','/api/workspaces/'+self.workspace_id+'/drawing-operations?format_version='+('10' if any(op['geometry'].get('schema')=='chart-fibonacci-projection/1' for op in operations) else '9'),dict(operations=operations))

    def export_package(self,symbol,interval,targets):
        self._connect()
        value=self._request('POST','/api/workspaces/'+self.workspace_id+'/drawing-packages/export',dict(symbol=symbol,interval=interval,targets=targets))
        if value.get('schema')!='chart-drawing-package/1':raise BotError('INVALID_BOT_PACKAGE')
        self._market(value.get('market'));return value

    def paste_package(self,key,symbol,interval,package):
        return self._write(key,'package-paste','POST','/api/workspaces/'+self.workspace_id+'/drawing-packages/paste',dict(symbol=symbol,interval=interval,package=package))
