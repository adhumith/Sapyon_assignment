import hashlib, secrets, sqlite3
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from .db import connect, migrate

app=FastAPI(title='AgencyDesk API')
app.add_middleware(CORSMiddleware, allow_origins=['https://sapyon-assignment.vercel.app'], allow_methods=['*'], allow_headers=['*'])
TOKENS={}
@app.on_event('startup')
def startup():
    c=connect(); migrate(c); c.close()
def fail(code=403, detail='Not permitted'): raise HTTPException(code,detail)
def current(authorization: str|None=Header(None)):
    if not authorization or not authorization.startswith('Bearer '): fail(401,'Sign in required')
    user=TOKENS.get(authorization[7:])
    if not user or user['expires'] < datetime.utcnow(): fail(401,'Session expired')
    return user
def qone(c, sql, args=()): return c.execute(sql,args).fetchone()
def project_for(c, pid, actor):
    p=qone(c,'SELECT * FROM projects WHERE id=?',(pid,))
    if not p: fail(404,'Project not found')
    staff=qone(c,"SELECT m.* FROM agency_memberships m WHERE m.agency_id=? AND m.user_id=? AND m.active=1",(p['agency_id'],actor['id']))
    contact=qone(c,'SELECT cc.* FROM client_contacts cc WHERE cc.client_id=? AND cc.user_id=? AND cc.active=1',(p['client_id'],actor['id']))
    if not staff and not contact: fail(404,'Project not found')
    if staff and staff['role']=='agency_member' and not qone(c,'SELECT 1 FROM project_members WHERE project_id=? AND membership_id=?',(pid,staff['id'])): fail(403,'Not assigned to project')
    return p,staff,contact
def task_for(c, tid, actor, visible=True):
    t=qone(c,'SELECT * FROM tasks WHERE id=?',(tid,))
    if not t: fail(404,'Task not found')
    p,staff,contact=project_for(c,t['project_id'],actor)
    if contact and visible and not t['is_client_visible']: fail(404,'Task not found')
    return t,p,staff,contact
class Login(BaseModel): email:str; password:str
class TaskIn(BaseModel): title:str; description:str=''; status:str='todo'; priority:str='medium'; due_date:str|None=None; assignee_membership_id:int|None=None; is_client_visible:bool=False
class CommentIn(BaseModel): body:str=Field(min_length=1); is_client_visible:bool=False
class TimeIn(BaseModel): minutes:int=Field(gt=0); note:str=''; entry_date:str
class ApprovalIn(BaseModel): status:str; note:str=''
class InviteIn(BaseModel): email:str; role:str='agency_member'
class InviteAccept(BaseModel): token:str; display_name:str='New member'; password:str=Field(min_length=8)
@app.post('/auth/login')
def login(body:Login):
    c=connect(); u=qone(c,'SELECT * FROM users WHERE email=?',(body.email,)); c.close()
    if not u or u['password_hash']!=hashlib.sha256(body.password.encode()).hexdigest(): fail(401,'Invalid email or password')
    token=secrets.token_urlsafe(32); TOKENS[token]={'id':u['id'],'email':u['email'],'name':u['display_name'],'expires':datetime.utcnow()+timedelta(hours=8)}
    return {'token':token,'user':{'id':u['id'],'email':u['email'],'name':u['display_name']}}
@app.get('/me')
def me(actor=Depends(current)):
    c=connect(); staff=c.execute("SELECT a.id,a.name,m.id membership_id,m.role FROM agency_memberships m JOIN agencies a ON a.id=m.agency_id WHERE m.user_id=? AND m.active=1",(actor['id'],)).fetchall(); clients=c.execute('SELECT cl.id,cl.name,a.id agency_id,a.name agency_name FROM client_contacts cc JOIN clients cl ON cl.id=cc.client_id JOIN agencies a ON a.id=cl.agency_id WHERE cc.user_id=? AND cc.active=1',(actor['id'],)).fetchall(); c.close(); return {'user':actor,'staff_agencies':[dict(x) for x in staff],'client_accounts':[dict(x) for x in clients]}
@app.get('/projects')
def projects(actor=Depends(current)):
    c=connect(); rows=c.execute("SELECT DISTINCT p.* FROM projects p LEFT JOIN agency_memberships m ON m.agency_id=p.agency_id AND m.user_id=? AND m.active=1 LEFT JOIN project_members pm ON pm.project_id=p.id AND pm.membership_id=m.id LEFT JOIN client_contacts cc ON cc.client_id=p.client_id AND cc.user_id=? AND cc.active=1 WHERE (m.role='agency_admin') OR (m.role='agency_member' AND pm.membership_id IS NOT NULL) OR cc.id IS NOT NULL ORDER BY p.id",(actor['id'],actor['id'])).fetchall(); c.close(); return [dict(x) for x in rows]
@app.get('/projects/{project_id}/dashboard')
def dashboard(project_id:int,actor=Depends(current)):
    c=connect(); p,staff,contact=project_for(c,project_id,actor); clause=' AND is_client_visible=1' if contact else ''; counts=c.execute('SELECT status,count(*) n FROM tasks WHERE project_id=?'+clause+' GROUP BY status',(project_id,)).fetchall(); hours=0 if contact else qone(c,'SELECT COALESCE(sum(te.minutes),0) n FROM time_entries te JOIN tasks t ON t.id=te.task_id WHERE t.project_id=?',(project_id,))['n']; c.close(); return {'project':dict(p),'task_counts':{r['status']:r['n'] for r in counts},'hours_logged':round(hours/60,2)}
@app.get('/projects/{project_id}/tasks')
def list_tasks(project_id:int, search:str='', actor=Depends(current)):
    c=connect(); _,_,contact=project_for(c,project_id,actor); sql='SELECT * FROM tasks WHERE project_id=?'; args=[project_id]
    if contact: sql+=' AND is_client_visible=1'
    if search: sql+=' AND (title LIKE ? OR description LIKE ?)'; args += [f'%{search}%',f'%{search}%']
    rows=c.execute(sql+' ORDER BY id',args).fetchall(); c.close(); return [dict(x) for x in rows]
@app.post('/projects/{project_id}/tasks')
def create_task(project_id:int,body:TaskIn,actor=Depends(current)):
    c=connect(); p,staff,contact=project_for(c,project_id,actor)
    if not staff or staff['role'] not in ('agency_admin','agency_member'): fail()
    if staff['role']=='agency_member' and not qone(c,'SELECT 1 FROM project_members WHERE project_id=? AND membership_id=?',(project_id,staff['id'])): fail()
    try: cur=c.execute('INSERT INTO tasks(agency_id,project_id,title,description,status,priority,due_date,assignee_membership_id,is_client_visible) VALUES(?,?,?,?,?,?,?,?,?)',(p['agency_id'],project_id,body.title,body.description,body.status,body.priority,body.due_date,body.assignee_membership_id,int(body.is_client_visible))); c.commit()
    except sqlite3.IntegrityError as e: fail(422,str(e))
    return {'id':cur.lastrowid}
@app.get('/tasks/{task_id}')
def task(task_id:int,actor=Depends(current)):
    c=connect(); t,_,_,contact=task_for(c,task_id,actor); result=dict(t); result['comments']=[dict(x) for x in c.execute('SELECT * FROM comments WHERE task_id=?'+(' AND is_client_visible=1' if contact else ''),(task_id,)).fetchall()]; result['attachments']=[dict(x) for x in c.execute('SELECT * FROM attachments WHERE task_id=?'+(' AND is_client_visible=1' if contact else ''),(task_id,)).fetchall()]; c.close(); return result
@app.post('/tasks/{task_id}/comments')
def comment(task_id:int,body:CommentIn,actor=Depends(current)):
    c=connect(); _,_,staff,contact=task_for(c,task_id,actor)
    if contact: body.is_client_visible=True
    if not staff and not contact: fail()
    cur=c.execute('INSERT INTO comments(task_id,author_user_id,body,is_client_visible) VALUES(?,?,?,?)',(task_id,actor['id'],body.body,int(body.is_client_visible))); c.commit(); return {'id':cur.lastrowid}
@app.post('/tasks/{task_id}/time')
def log_time(task_id:int,body:TimeIn,actor=Depends(current)):
    c=connect(); _,_,staff,contact=task_for(c,task_id,actor)
    if not staff: fail()
    cur=c.execute('INSERT INTO time_entries(task_id,membership_id,minutes,note,entry_date) VALUES(?,?,?,?,?)',(task_id,staff['id'],body.minutes,body.note,body.entry_date)); c.commit(); return {'id':cur.lastrowid}
@app.post('/attachments/{attachment_id}/approval')
def approval(attachment_id:int,body:ApprovalIn,actor=Depends(current)):
    if body.status not in ('approved','needs_changes'): fail(422,'Invalid approval status')
    c=connect(); a=qone(c,'SELECT * FROM attachments WHERE id=?',(attachment_id,));
    if not a: fail(404,'Attachment not found')
    _,_,_,contact=task_for(c,a['task_id'],actor)
    if not contact or not a['is_client_visible']: fail()
    c.execute('UPDATE attachments SET approval_status=?,approval_note=?,approved_by_user_id=?,approved_at=? WHERE id=?',(body.status,body.note,actor['id'],datetime.utcnow().isoformat(),attachment_id)); c.commit(); return {'ok':True}
@app.post('/agencies/{agency_id}/invites')
def invite(agency_id:int,body:InviteIn,actor=Depends(current)):
    c=connect(); m=qone(c,"SELECT * FROM agency_memberships WHERE agency_id=? AND user_id=? AND role='agency_admin' AND active=1",(agency_id,actor['id']))
    if not m: fail()
    token=secrets.token_urlsafe(16); c.execute("INSERT INTO invites(agency_id,email,role,token) VALUES(?,?,?,?) ON CONFLICT(agency_id,email) DO UPDATE SET role=excluded.role,token=excluded.token,state='pending',created_at=CURRENT_TIMESTAMP",(agency_id,body.email,body.role,token)); c.commit(); return {'token':token}
@app.post('/invites/accept')
def accept_invite(body:InviteAccept):
    c=connect(); invite=qone(c,"SELECT * FROM invites WHERE token=?",(body.token,))
    if not invite: fail(404,'Invite not found')
    user=qone(c,'SELECT * FROM users WHERE email=?',(invite['email'],))
    if not user:
        cur=c.execute('INSERT INTO users(email,display_name,password_hash) VALUES(?,?,?)',(invite['email'],body.display_name,hashlib.sha256(body.password.encode()).hexdigest())); user=qone(c,'SELECT * FROM users WHERE id=?',(cur.lastrowid,))
    # This is deliberately idempotent: a second accept uses the membership unique key.
    c.execute('INSERT OR IGNORE INTO agency_memberships(agency_id,user_id,role) VALUES(?,?,?)',(invite['agency_id'],user['id'],invite['role']))
    c.execute("UPDATE invites SET state='accepted',accepted_at=COALESCE(accepted_at,?) WHERE id=?",(datetime.utcnow().isoformat(),invite['id']))
    c.commit(); return {'agency_id':invite['agency_id'],'user_id':user['id']}
@app.delete('/projects/{project_id}/members/{membership_id}')
def remove_member(project_id:int,membership_id:int,actor=Depends(current)):
    c=connect(); _,staff,_=project_for(c,project_id,actor)
    if not staff or staff['role']!='agency_admin': fail()
    c.execute('BEGIN'); c.execute('DELETE FROM project_members WHERE project_id=? AND membership_id=?',(project_id,membership_id)); c.execute('UPDATE tasks SET assignee_membership_id=NULL WHERE project_id=? AND assignee_membership_id=?',(project_id,membership_id)); c.commit(); return {'ok':True}
