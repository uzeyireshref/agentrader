"""Owner-scoped, revision-checked chart drawings and workspace preferences."""
from agentrader.shared.market_environment import SOURCE
from agentrader.chart.binding_lifecycle import stop_bindings
from contextlib import closing
from decimal import Decimal
from agentrader.chart.drawings.coordinates import coordinate_text
import hashlib
import json
import re
import time
import uuid

from agentrader.chart.drawings.actors import DrawingActor
from agentrader.chart.drawings.projection import SCHEMA as PROJECTION_SCHEMA,validate as validate_projection
from agentrader.shared.market_data import INTERVALS
from agentrader.migrations import connect
from agentrader.bot.plans import positive
from agentrader.chart.chart_precision import decimal_text
from agentrader.chart.drawings.position import KINDS as POSITION_KINDS, metrics as position_metrics
from agentrader.chart.drawings.channel import basis as channel_basis
from agentrader.chart.drawings.channel_family import SCHEMA as FAMILY_SCHEMA, KINDS as FAMILY_KINDS, NEW_KINDS as FAMILY_NEW_KINDS, validate as validate_family
from agentrader.chart.drawings.fibonacci import levels as fibonacci_levels
from agentrader.chart.drawings.annotations import KINDS as ANNOTATION_KINDS, annotation_text


class DrawingError(ValueError):
    status = 422
    code = 'INVALID_DRAWING'


class DrawingConflict(DrawingError):
    status = 409
    code = 'DRAWING_REVISION_CONFLICT'


class DrawingNotFound(DrawingError):
    status = 404
    code = 'DRAWING_NOT_FOUND'


class DrawingProtected(DrawingError):
    status = 403
    code = 'DRAWING_ORIGIN_PROTECTED'


class DrawingLocked(DrawingError):
    status = 423
    code = 'DRAWING_LOCKED'


def management(value=None):
    defaults = dict(schema='chart-management/1', locked=False, hidden=False, intervals=[],
                    color=None, line_width=1, line_style='default')
    if value is None or value == {}:
        return defaults
    if not isinstance(value, dict) or set(value) != set(defaults):
        raise DrawingError()
    if (value['schema'] != defaults['schema'] or type(value['locked']) is not bool
            or type(value['hidden']) is not bool or not isinstance(value['intervals'], list)
            or len(value['intervals']) > len(INTERVALS) or any(not isinstance(i, str) or i not in INTERVALS for i in value['intervals'])
            or len(set(value['intervals'])) != len(value['intervals'])
            or value['color'] not in (None, '#2962ff', '#16a085', '#d95656', '#c99432', '#9b6ed6')
            or type(value['line_width']) is not int or value['line_width'] not in (1, 2, 3)
            or value['line_style'] not in ('default', 'solid', 'dashed', 'dotted')):
        raise DrawingError()
    return {**value, 'intervals': sorted(value['intervals'])}


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', value):
        raise DrawingError()
    return value


def geometry(value):
    if not isinstance(value, dict):
        raise DrawingError()
    fields = {'kind', 'symbol', 'price_source', 'anchors', 'label'}
    family = value.get('schema') == FAMILY_SCHEMA
    if family:
        fields.update(('schema', 'options', 'text'))
        if value.get('kind') not in FAMILY_KINDS:
            raise DrawingError()
    elif value.get('kind') in FAMILY_NEW_KINDS:
        raise DrawingError()
    if value.get('kind') in ANNOTATION_KINDS:
        fields.update(('schema', 'text'))
        if value.get('schema') != 'chart-annotation/1':
            raise DrawingError()
        try:
            value = {**value, 'text': annotation_text(value['kind'], value.get('text'))}
        except ValueError:
            raise DrawingError() from None
    if value.get('kind')=='fibonacci_projection':
        fields.update(('schema','levels','time_scope','basis'))
        if value.get('schema')!=PROJECTION_SCHEMA or value.get('basis')!='PRICE_DELTA' or value.get('time_scope') not in ('bounded','right','unbounded'):raise DrawingError()
        try:value={**value,'levels':fibonacci_levels(value.get('levels'))}
        except ValueError:raise DrawingError() from None
    versioned_fib = value.get('kind') == 'fibonacci_extension' or value.get('kind') == 'fibonacci' and 'schema' in value
    if versioned_fib:
        fields.update(('schema', 'levels', 'time_scope'))
        if value.get('schema') != 'chart-fibonacci/1' or value.get('time_scope') not in ('bounded', 'right', 'unbounded'):
            raise DrawingError()
        try:
            value = {**value, 'levels': fibonacci_levels(value.get('levels'))}
        except ValueError:
            raise DrawingError() from None
    if value.get('kind') == 'parallel_channel' and not family:
        fields.add('schema')
        if value.get('schema') != 'chart-channel/1':
            raise DrawingError()
    if value.get('kind') in POSITION_KINDS:
        fields.update(('schema', 'params'))
    if value.get('kind') == 'ruler':
        fields.add('schema')
        if value.get('schema') != 'chart-ruler/1':
            raise DrawingError()
    versioned_line = value.get('kind') in ('ray', 'extended_line', 'horizontal_ray')
    if versioned_line:
        fields.add('schema')
        if value.get('schema') != 'chart-line/1':
            raise DrawingError()
    if value.get('kind') == 'zone' and 'schema' in value:
        fields.update(('schema', 'time_scope'))
        if value['schema'] != 'chart-zone/1' or value.get('time_scope') not in ('bounded', 'unbounded'):
            raise DrawingError()
    if set(value) != fields:
        raise DrawingError()
    if (value['kind'] not in ('horizontal', 'zone', 'trend', 'fibonacci', 'fibonacci_extension', 'fibonacci_projection', 'ruler', 'ray', 'extended_line', 'horizontal_ray', 'parallel_channel', *FAMILY_NEW_KINDS, *POSITION_KINDS, *ANNOTATION_KINDS) or value['price_source'] != 'LAST_PRICE'
            or not isinstance(value['symbol'], str) or not re.fullmatch(r'[A-Z0-9]{2,20}USDT', value['symbol'])
            or not isinstance(value['label'], str) or len(value['label']) > 64):
        raise DrawingError()
    anchors = value['anchors']
    count = 3 if value['kind']=='fibonacci_projection' else (2 if value['kind'] == 'regression_channel' else 3) if family else (3 if value['kind'] in (*POSITION_KINDS, 'parallel_channel') else 1 if value['kind'] in ('horizontal', 'horizontal_ray', *ANNOTATION_KINDS) else 2)
    if not isinstance(anchors, list) or len(anchors) != count:
        raise DrawingError()
    normalized = []
    for anchor in anchors:
        if (not isinstance(anchor, dict) or set(anchor) != {'time', 'price'}
                or type(anchor['time']) is not int or not 0 < anchor['time'] <= 32503680000):
            raise DrawingError()
        try:
            coordinate_text(anchor['price'])
            if value['kind'] in POSITION_KINDS:
                positive(anchor['price'], 'Çizim fiyatı')
            if value.get('schema'):
                price = format(Decimal(anchor['price']), 'f')
                if len(price) > 64:
                    raise ValueError()
            else:
                price = str(Decimal(anchor['price']))
        except ValueError:
            raise DrawingError() from None
        normalized.append({'time': anchor['time'], 'price': price})
    if value['kind'] in ('ray', 'extended_line') and normalized[0]['time'] == normalized[1]['time']:
        raise DrawingError()
    if value['kind']=='fibonacci_projection':
        try:return validate_projection({**value,'anchors':normalized})
        except ValueError:raise DrawingError() from None
    if family:
        try:
            return validate_family({**value, 'anchors': normalized})
        except (ValueError, TypeError, KeyError):
            raise DrawingError() from None
    if value['kind'] == 'parallel_channel':
        try:
            channel_basis(normalized)
        except ValueError:
            raise DrawingError() from None
    elif value['kind'] in POSITION_KINDS:
        try:
            position_metrics({**value, 'anchors': normalized})
        except (ValueError, TypeError, KeyError):
            raise DrawingError() from None
    elif value['kind'] not in ('horizontal', 'horizontal_ray', 'ray', 'extended_line', 'ruler', *ANNOTATION_KINDS):
        if normalized[0]['time'] == normalized[1]['time'] or normalized[0]['price'] == normalized[1]['price']:
            raise DrawingError()
        if coordinate_text(normalized[0]['price']) == coordinate_text(normalized[1]['price']):
            raise DrawingError()
        if value['kind'] == 'zone':
            normalized.sort(key=lambda a: a['time'])
    return {**value, 'anchors': normalized}


class DrawingService:
    def __init__(self, database, owner, clock=time.time, *, actor=None):
        self.database, self.owner, self.clock = database, owner, clock
        self.actor = actor or DrawingActor('manual',owner)

    def _origin(self,db,drawing_id):
        row=db.execute('SELECT body FROM app_drawing_origins WHERE owner=? AND drawing_id=?',(self.owner,drawing_id)).fetchone()
        return json.loads(row['body']) if row else dict(schema='drawing-origin/1',kind='manual',source='legacy',actor_id=self.owner,bot_id=None,strategy_id=None,created_at=None)

    def _assert_edit(self,db,row):
        if self.actor.kind=='bot':
            origin=self._origin(db,row['drawing_id'])
            if origin['kind']!='bot' or any(origin[k]!=getattr(self.actor,k) for k in ('actor_id','bot_id','strategy_id')):
                raise DrawingProtected()

    def _record(self,db,drawing_id,revision):
        row=self._head(db,drawing_id)
        origin=dict(schema='drawing-origin/1',**self.actor.view(),source='bot' if self.actor.kind=='bot' else 'user',created_at=row['updated_at'])
        db.execute('INSERT OR IGNORE INTO app_drawing_origins VALUES (?,?,?)',(self.owner,drawing_id,json.dumps(origin)))
        db.execute('INSERT INTO app_drawing_audit VALUES (?,?,?,?)',(self.owner,drawing_id,revision,json.dumps(self.actor.view())))

    def _note(self,db,row):
        note=db.execute('SELECT * FROM app_drawing_notes WHERE owner=? AND drawing_id=? ORDER BY revision DESC LIMIT 1',(self.owner,row['drawing_id'])).fetchone()
        return dict(schema='drawing-linked-note/1',drawing_id=row['drawing_id'],workspace_id=row['workspace_id'],
                    note_id=note['note_id'] if note else None,revision=note['revision'] if note else 0,
                    text=note['text'] if note else '',deleted=bool(note['deleted']) if note else False,
                    state='TARGET_ARCHIVED' if row['deleted'] else 'NOTE_DELETED' if note and note['deleted'] else 'ACTIVE' if note else 'EMPTY',
                    target_revision=row['revision'],saved_target_revision=note['target_revision'] if note else None,updated_at=note['updated_at'] if note else None,
                    updated_by=json.loads(note['actor']) if note else None,order_authority=False)


    def _mutation(self, request_id, action, payload, operation):
        identifier(request_id)
        if self.actor.kind=='bot' and action[0] not in ('create','update','operations','linked-note','package-paste'):
            raise DrawingProtected()
        if self.actor.kind=='bot':payload={'actor':self.actor.view(),'payload':payload}
        digest = hashlib.sha256(json.dumps([action, payload], sort_keys=True).encode()).hexdigest()
        with closing(connect(self.database)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            old = db.execute('SELECT * FROM app_drawing_requests WHERE owner=? AND request_id=?',
                             (self.owner, request_id)).fetchone()
            if old:
                if old['digest'] != digest:
                    raise DrawingConflict()
                return json.loads(old['result']) | {'duplicate': True}
            result = operation(db)
            db.execute('INSERT INTO app_drawing_requests VALUES (?,?,?,?)',
                       (self.owner, request_id, digest, json.dumps(result)))
            return result | {'duplicate': False}

    def _view(self,row,db=None):
        if db is None:
            with closing(connect(self.database)) as connection:return self._view(row,connection)
        audit=db.execute('SELECT body FROM app_drawing_audit WHERE owner=? AND drawing_id=? AND revision=?',(self.owner,row['drawing_id'],row['revision'])).fetchone()
        return {'origin':self._origin(db,row['drawing_id']),'change':dict(revision=row['revision'],updated_by=json.loads(audit['body']) if audit else None),'linked_note':self._note(db,row),'drawing_id': row['drawing_id'], 'revision': row['revision'],
                'workspace_id': row['workspace_id'], 'geometry': json.loads(row['geometry']),
                'deleted': bool(row['deleted']), 'updated_at': row['updated_at'],
                'management': management(json.loads(row['management'])),
                'product': 'USD-M', 'source': SOURCE, 'tracking': 'NOT_IMPLEMENTED'}

    def _head(self, db, drawing_id):
        identifier(drawing_id)
        row = db.execute('''SELECT r.* FROM app_drawing_revisions r JOIN app_drawing_heads h
            ON r.owner=h.owner AND r.drawing_id=h.drawing_id AND r.revision=h.revision
            WHERE r.owner=? AND r.drawing_id=?''', (self.owner, drawing_id)).fetchone()
        if row is None:
            raise DrawingNotFound()
        return row

    def list(self, workspace_id, symbol):
        identifier(workspace_id)
        if not isinstance(symbol, str) or not re.fullmatch(r'[A-Z0-9]{2,20}USDT', symbol):
            raise DrawingError()
        with closing(connect(self.database)) as db:
            rows = db.execute('''SELECT r.* FROM app_drawing_revisions r JOIN app_drawing_heads h
                ON r.owner=h.owner AND r.drawing_id=h.drawing_id AND r.revision=h.revision
                WHERE r.owner=? AND r.workspace_id=? AND r.deleted=0 ORDER BY r.updated_at,r.drawing_id''',
                (self.owner, workspace_id)).fetchall()
            return [self._view(r,db) for r in rows if json.loads(r['geometry'])['symbol'] == symbol]

    def show(self, drawing_id):
        with closing(connect(self.database)) as db:
            return self._view(self._head(db, drawing_id),db)

    def history(self,drawing_id,limit=50,offset=0):
        identifier(drawing_id)
        if type(limit) is not int or not 1<=limit<=100 or type(offset) is not int or not 0<=offset<=1000000:raise DrawingError()
        with closing(connect(self.database)) as db:
            head=self._head(db,drawing_id)
            rows=db.execute('SELECT r.revision,r.updated_at,r.deleted,a.body FROM app_drawing_revisions r LEFT JOIN app_drawing_audit a ON r.owner=a.owner AND r.drawing_id=a.drawing_id AND r.revision=a.revision WHERE r.owner=? AND r.drawing_id=? ORDER BY r.revision DESC LIMIT ? OFFSET ?',
                            (self.owner,drawing_id,limit,offset)).fetchall()
            return dict(schema='drawing-history/1',drawing_id=drawing_id,origin=self._origin(db,drawing_id),
                        head_revision=head['revision'],revisions=[dict(revision=r['revision'],updated_at=r['updated_at'],deleted=bool(r['deleted']),updated_by=json.loads(r['body']) if r['body'] else None) for r in rows],
                        next_offset=offset+limit if offset+limit<head['revision'] else None,order_authority=False)

    def create(self, workspace_id, request_id, value):
        identifier(workspace_id)
        value = geometry(value)
        def apply(db):
            count = db.execute('''SELECT COUNT(*) FROM app_drawing_revisions r JOIN app_drawing_heads h
                ON r.owner=h.owner AND r.drawing_id=h.drawing_id AND r.revision=h.revision
                WHERE r.owner=? AND r.workspace_id=? AND r.deleted=0''', (self.owner, workspace_id)).fetchone()[0]
            if count >= 200:
                raise DrawingError()
            drawing_id = uuid.uuid4().hex
            db.execute('INSERT INTO app_drawing_revisions (owner,drawing_id,revision,workspace_id,geometry,deleted,updated_at) VALUES (?,?,?,?,?,?,?)',
                       (self.owner, drawing_id, 1, workspace_id, json.dumps(value), 0, self.clock()))
            db.execute('INSERT INTO app_drawing_heads VALUES (?,?,1)', (self.owner, drawing_id))
            self._record(db,drawing_id,1)
            return self._view(self._head(db, drawing_id),db)
        return self._mutation(request_id, ['create', workspace_id], value, apply)

    def update(self, drawing_id, request_id, expected_revision, value=None, *, deleted=False):
        identifier(drawing_id)
        if type(expected_revision) is not int or expected_revision < 1:
            raise DrawingError()
        value = geometry(value) if value is not None else None
        def apply(db):
            row = self._head(db, drawing_id)
            self._assert_edit(db,row)
            if row['revision'] != expected_revision:
                raise DrawingConflict()
            previous = json.loads(row['geometry'])
            if management(json.loads(row['management']))['locked'] and (deleted or value != previous):
                raise DrawingLocked()
            if value is not None and (value['symbol'] != previous['symbol'] or value['kind'] != previous['kind']):
                raise DrawingError()
            next_geometry = value if value is not None else previous
            revision = expected_revision + 1
            db.execute('INSERT INTO app_drawing_revisions VALUES (?,?,?,?,?,?,?,?)',
                       (self.owner, drawing_id, revision, row['workspace_id'], json.dumps(next_geometry), int(deleted), self.clock(), row['management']))
            db.execute('UPDATE app_drawing_heads SET revision=? WHERE owner=? AND drawing_id=?',
                       (revision, self.owner, drawing_id))
            self._record(db,drawing_id,revision)
            stop_bindings(db,self.owner,row['workspace_id'],'drawing',{drawing_id},'TARGET_DELETED' if deleted else 'TARGET_REVISION_CHANGED')
            return self._view(self._head(db, drawing_id),db)
        return self._mutation(request_id, ['update', drawing_id],
                              {'expected_revision': expected_revision, 'geometry': value, 'deleted': deleted}, apply)

    def operations(self, workspace_id, request_id, operations):
        """One revision-checked, idempotent transaction for a selection/history entry."""
        identifier(workspace_id)
        if not isinstance(operations, list) or not 1 <= len(operations) <= 20:
            raise DrawingError()
        normalized, ids, symbols = [], set(), set()
        for op in operations:
            if not isinstance(op, dict) or set(op) != {'drawing_id', 'expected_revision', 'geometry', 'management', 'deleted'}:
                raise DrawingError()
            if not isinstance(op['management'], dict) or not op['management']:
                raise DrawingError()
            key = op['drawing_id']
            if key is not None:
                identifier(key)
                if key in ids:
                    raise DrawingError()
                ids.add(key)
            if (type(op['expected_revision']) is not int or op['expected_revision'] < (1 if key else 0)
                    or (key is None and (op['expected_revision'] != 0 or op['deleted'])) or type(op['deleted']) is not bool):
                raise DrawingError()
            g, m = geometry(op['geometry']), management(op['management'])
            symbols.add(g['symbol'])
            normalized.append({**op, 'geometry': g, 'management': m})
        if len(symbols) != 1:
            raise DrawingError()
        def apply(db):
            result = []
            for op in normalized:
                key = op['drawing_id']
                if key is None:
                    key, revision = uuid.uuid4().hex, 1
                else:
                    row = self._head(db, key)
                    self._assert_edit(db,row)
                    if row['workspace_id'] != workspace_id:
                        raise DrawingNotFound()
                    if row['revision'] != op['expected_revision']:
                        raise DrawingConflict()
                    old = json.loads(row['geometry'])
                    if old['kind'] != op['geometry']['kind'] or old['symbol'] != op['geometry']['symbol']:
                        raise DrawingError()
                    old_management = management(json.loads(row['management']))
                    if old_management['locked'] and (old != op['geometry'] or bool(row['deleted']) != op['deleted']
                            or any(old_management[k] != op['management'][k] for k in ('color', 'line_width', 'line_style'))):
                        raise DrawingLocked()
                    revision = row['revision'] + 1
                db.execute('INSERT INTO app_drawing_revisions VALUES (?,?,?,?,?,?,?,?)',
                           (self.owner, key, revision, workspace_id, json.dumps(op['geometry']), int(op['deleted']), self.clock(), json.dumps(op['management'])))
                db.execute('INSERT OR REPLACE INTO app_drawing_heads VALUES (?,?,?)', (self.owner, key, revision))
                self._record(db,key,revision)
                if op['drawing_id'] is not None:stop_bindings(db,self.owner,workspace_id,'drawing',{key},'TARGET_DELETED' if op['deleted'] else 'TARGET_REVISION_CHANGED')
                result.append(self._view(self._head(db, key),db))
            count = db.execute('''SELECT COUNT(*) FROM app_drawing_revisions r JOIN app_drawing_heads h
                ON r.owner=h.owner AND r.drawing_id=h.drawing_id AND r.revision=h.revision
                WHERE r.owner=? AND r.workspace_id=? AND r.deleted=0''', (self.owner, workspace_id)).fetchone()[0]
            if count > 200:
                raise DrawingError()
            return {'drawings': result}
        return self._mutation(request_id, ['operations', workspace_id], normalized, apply)

    def workspace(self, workspace_id):
        identifier(workspace_id)
        with closing(connect(self.database)) as db:
            row = db.execute('SELECT * FROM app_workspaces WHERE owner=? AND workspace_id=?',
                             (self.owner, workspace_id)).fetchone()
            return {'workspace_id': workspace_id, 'revision': row['revision'] if row else 0,
                    'preferences': json.loads(row['body']) if row else {'symbol': 'BTCUSDT', 'interval': '15m'}}

    def save_workspace(self, workspace_id, request_id, expected_revision, preferences):
        identifier(workspace_id)
        if (type(expected_revision) is not int or expected_revision < 0 or not isinstance(preferences, dict)
                or set(preferences) != {'symbol', 'interval'} or not isinstance(preferences['interval'], str)
                or preferences['interval'] not in INTERVALS
                or not isinstance(preferences['symbol'], str) or not re.fullmatch(r'[A-Z0-9]{2,20}USDT', preferences['symbol'])):
            raise DrawingError()
        def apply(db):
            row = db.execute('SELECT revision FROM app_workspaces WHERE owner=? AND workspace_id=?',
                             (self.owner, workspace_id)).fetchone()
            if (row['revision'] if row else 0) != expected_revision:
                raise DrawingConflict()
            db.execute('INSERT OR REPLACE INTO app_workspaces VALUES (?,?,?,?)',
                       (self.owner, workspace_id, expected_revision + 1, json.dumps(preferences)))
            return {'workspace_id': workspace_id, 'revision': expected_revision + 1, 'preferences': preferences}
        return self._mutation(request_id, ['workspace', workspace_id],
                              {'expected_revision': expected_revision, 'preferences': preferences}, apply)
