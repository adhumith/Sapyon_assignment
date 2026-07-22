import os, sys, tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
fd,path=tempfile.mkstemp(); os.close(fd); os.unlink(path); os.environ['AGENCYDESK_DB']=path
from app.seed import seed
seed(True)
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def token(email): return client.post('/auth/login',json={'email':email,'password':'demo-password'}).json()['token']
def h(email): return {'Authorization':'Bearer '+token(email)}
def test_cross_tenant_project_is_hidden():
    # Maya is Northstar-only; Ada intentionally belongs to both agencies.
    assert client.get('/projects/2/tasks',headers=h('maya@northstar.test')).status_code in (403,404)
def test_client_never_sees_internal_content_even_by_id_or_search():
    headers=h('sam@acme.test')
    assert [x['id'] for x in client.get('/projects/1/tasks?search=Analytics',headers=headers).json()] == []
    assert client.get('/tasks/2',headers=headers).status_code == 404
    assert client.get('/tasks/1',headers=headers).json()['comments'][0]['is_client_visible'] == 1
def test_client_cannot_create_task_or_log_time():
    headers=h('sam@acme.test')
    assert client.post('/projects/1/tasks',json={'title':'No'},headers=headers).status_code == 403
    assert client.post('/tasks/1/time',json={'minutes':5,'entry_date':'2026-07-22'},headers=headers).status_code == 403
def test_invite_resend_is_idempotent_and_removal_unassigns():
    headers=h('ada@northstar.test')
    first=client.post('/agencies/1/invites',json={'email':'new@test.dev'},headers=headers)
    second=client.post('/agencies/1/invites',json={'email':'new@test.dev'},headers=headers)
    from app.db import connect
    c=connect(); assert c.execute("select count(*) from invites where agency_id=1 and email='new@test.dev'").fetchone()[0] == 1
    payload={'token':second.json()['token'],'password':'a-safe-password'}
    assert client.post('/invites/accept',json=payload).status_code == 200
    assert client.post('/invites/accept',json=payload).status_code == 200
    assert c.execute("select count(*) from agency_memberships m join users u on u.id=m.user_id where m.agency_id=1 and u.email='new@test.dev'").fetchone()[0] == 1
    assert client.delete('/projects/1/members/2',headers=headers).status_code == 200
    assert c.execute('select assignee_membership_id from tasks where id=1').fetchone()[0] is None
