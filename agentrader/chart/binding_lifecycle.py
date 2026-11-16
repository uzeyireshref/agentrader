"""Revision invalidation in the same application-store transaction as the edit."""
import json

def stop_bindings(db,owner,workspace_id,target_type,object_ids,reason):
 if not object_ids or not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='app_chart_binding_heads'").fetchone():return
 rows=db.execute('SELECT r.* FROM app_chart_binding_revisions r JOIN app_chart_binding_heads h ON r.owner=h.owner AND r.binding_id=h.binding_id AND r.revision=h.revision WHERE r.owner=? AND r.workspace_id=? AND r.state=?',(owner,workspace_id,'DISABLED')).fetchall()
 for row in rows:
  target=json.loads(row['definition'])['target']
  if target['type']!=target_type or target['object_id'] not in object_ids:continue
  revision=row['revision']+1
  db.execute('INSERT INTO app_chart_binding_revisions VALUES (?,?,?,?,?,?,?)',(owner,workspace_id,row['binding_id'],revision,'STOPPED',reason,row['definition']))
  db.execute('UPDATE app_chart_binding_heads SET revision=? WHERE owner=? AND binding_id=?',(revision,owner,row['binding_id']))
