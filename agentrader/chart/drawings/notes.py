"""Revisioned long notes attached to existing drawing identity, outside geometry."""
from contextlib import closing
import json
import uuid
from agentrader.migrations import connect
from agentrader.chart.drawings.service import DrawingService,DrawingError,DrawingConflict,DrawingLocked,DrawingProtected,identifier,management


def note_text(text):
    if not isinstance(text,str) or len(text)>4000:raise DrawingError()
    try:encoded=text.encode('utf-8')
    except UnicodeError:raise DrawingError() from None
    if len(encoded)>16000 or any(ord(c)<32 and c not in '\n\r\t' or ord(c)==127 for c in text):raise DrawingError()
    return text


class DrawingNotes(DrawingService):
    def show_note(self,drawing_id,revision=0):
        identifier(drawing_id)
        if type(revision) is not int or not 0<=revision<=1000000000:raise DrawingError()
        with closing(connect(self.database)) as db:
            target=self._head(db,drawing_id)
            result=self._note(db,target)
            if revision and revision!=result['revision']:
                row=db.execute('SELECT * FROM app_drawing_notes WHERE owner=? AND drawing_id=? AND revision=?',(self.owner,drawing_id,revision)).fetchone()
                if row is None:raise DrawingConflict()
                result.update(note_id=row['note_id'],revision=row['revision'],text=row['text'],deleted=bool(row['deleted']),
                              updated_at=row['updated_at'],updated_by=json.loads(row['actor']),saved_target_revision=row['target_revision'])
                result['state']='TARGET_ARCHIVED' if target['deleted'] else 'NOTE_DELETED' if row['deleted'] else 'ACTIVE'
            return result

    def save_note(self,drawing_id,request_id,expected_revision,expected_drawing_revision,text,*,deleted=False):
        identifier(drawing_id)
        if (type(expected_revision) is not int or not 0<=expected_revision<1000000000 or type(expected_drawing_revision) is not int or not 1<=expected_drawing_revision<=1000000000
                or not isinstance(text,str) or len(text)>4000 or type(deleted) is not bool):raise DrawingError()
        note_text(text)
        def apply(db):
            target=self._head(db,drawing_id);self._assert_edit(db,target)
            if target['deleted']:raise DrawingProtected()
            if management(json.loads(target['management']))['locked']:raise DrawingLocked()
            previous=self._note(db,target)
            if target['revision']!=expected_drawing_revision or previous['revision']!=expected_revision:raise DrawingConflict()
            if deleted and not previous['revision']:raise DrawingConflict()
            db.execute('INSERT INTO app_drawing_notes VALUES (?,?,?,?,?,?,?,?,?)',
                       (self.owner,drawing_id,previous['note_id'] or uuid.uuid4().hex,expected_revision+1,
                        previous['text'] if deleted else text,int(deleted),self.clock(),json.dumps(self.actor.view()),expected_drawing_revision))
            return self._note(db,target)
        return self._mutation(request_id,['linked-note',drawing_id],dict(expected_revision=expected_revision,
                              expected_drawing_revision=expected_drawing_revision,text=text,deleted=deleted),apply)
