"""Portable, strict drawing content. Identity and authority never cross the clipboard."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import uuid
from agentrader.chart.chart_market import validate_selection
from agentrader.shared.market_environment import SOURCE,ENVIRONMENT
from agentrader.chart.drawings.service import DrawingService,DrawingError,DrawingConflict,DrawingNotFound,identifier,geometry,management
from agentrader.chart.drawings.notes import note_text

SCHEMA='chart-drawing-package/1'
MAX_BYTES=524288
IDENTITY=dict(source=SOURCE,environment=ENVIRONMENT,product='USD-M',price_type='LAST_PRICE')


class PackageMismatch(DrawingError):code='PACKAGE_MARKET_MISMATCH'


def validate_package(value,symbol,interval):
    validate_selection(symbol,interval)
    if not isinstance(value,dict) or set(value)!={'schema','market','items'} or value['schema']!=SCHEMA:raise DrawingError()
    if value['market']!=dict(IDENTITY,symbol=symbol,interval=interval):raise PackageMismatch()
    if not isinstance(value['items'],list) or not 1<=len(value['items'])<=20:raise DrawingError()
    items=[]
    for item in value['items']:
        if not isinstance(item,dict) or set(item)!={'geometry','management','linked_note'}:raise DrawingError()
        if not isinstance(item['management'],dict) or set(item['management'])!=set(management()):raise DrawingError()
        g,m=geometry(item['geometry']),management(item['management'])
        if g['symbol']!=symbol:raise PackageMismatch()
        note=item['linked_note']
        if note is not None:
            if not isinstance(note,dict) or set(note)!={'text'}:raise DrawingError()
            note={'text':note_text(note['text'])}
        items.append(dict(geometry=g,management=m,linked_note=note))
    clean=dict(schema=SCHEMA,market=dict(IDENTITY,symbol=symbol,interval=interval),items=items)
    try:size=len(json.dumps(clean,ensure_ascii=False,allow_nan=False).encode('utf-8'))
    except (ValueError,UnicodeError):raise DrawingError() from None
    if size>MAX_BYTES:raise DrawingError()
    return clean


class DrawingPackages(DrawingService):
    def export(self,workspace_id,symbol,interval,targets):
        identifier(workspace_id);validate_selection(symbol,interval)
        if not isinstance(targets,list) or not 1<=len(targets)<=20:raise DrawingError()
        seen=set();items=[]
        with closing(sqlite3.connect(Path(self.database).resolve().as_uri()+'?mode=ro',uri=True,timeout=.2)) as db:
            db.row_factory=sqlite3.Row;db.execute('BEGIN')
            for target in targets:
                if not isinstance(target,dict) or set(target)!={'drawing_id','expected_revision','expected_note_revision'}:raise DrawingError()
                identifier(target['drawing_id'])
                if target['drawing_id'] in seen or type(target['expected_revision']) is not int or type(target['expected_note_revision']) is not int:raise DrawingError()
                seen.add(target['drawing_id']);row=self._head(db,target['drawing_id'])
                if row['workspace_id']!=workspace_id or row['deleted']:raise DrawingNotFound()
                item=self._view(row,db);note=item['linked_note']
                if item['revision']!=target['expected_revision'] or note['revision']!=target['expected_note_revision']:raise DrawingConflict()
                if item['geometry']['symbol']!=symbol:raise PackageMismatch()
                items.append(dict(geometry=item['geometry'],management=item['management'],linked_note={'text':note['text']} if note['state']=='ACTIVE' else None))
        return validate_package(dict(schema=SCHEMA,market=dict(IDENTITY,symbol=symbol,interval=interval),items=items),symbol,interval)

    def paste(self,workspace_id,request_id,symbol,interval,package):
        identifier(workspace_id);clean=validate_package(package,symbol,interval)
        def apply(db):
            count=db.execute('''SELECT COUNT(*) FROM app_drawing_revisions r JOIN app_drawing_heads h ON r.owner=h.owner AND r.drawing_id=h.drawing_id AND r.revision=h.revision WHERE r.owner=? AND r.workspace_id=? AND r.deleted=0''',(self.owner,workspace_id)).fetchone()[0]
            if count+len(clean['items'])>200:raise DrawingError()
            results=[]
            for item in clean['items']:
                did=uuid.uuid4().hex;now=self.clock()
                db.execute('INSERT INTO app_drawing_revisions VALUES (?,?,?,?,?,?,?,?)',(self.owner,did,1,workspace_id,json.dumps(item['geometry']),0,now,json.dumps(item['management'])))
                db.execute('INSERT INTO app_drawing_heads VALUES (?,?,1)',(self.owner,did));self._record(db,did,1)
                if item['linked_note'] is not None:
                    db.execute('INSERT INTO app_drawing_notes VALUES (?,?,?,?,?,?,?,?,?)',(self.owner,did,uuid.uuid4().hex,1,item['linked_note']['text'],0,now,json.dumps(self.actor.view()),1))
                results.append(self._view(self._head(db,did),db))
            return dict(schema='chart-package-paste/1',drawings=results,order_authority=False)
        return self._mutation(request_id,['package-paste',workspace_id],dict(symbol=symbol,interval=interval,package=clean),apply)
