# AgencyDesk

AgencyDesk is a small multi-tenant agency/client project workspace. It demonstrates strict agency isolation, agency member project assignment, client-only portal visibility, time logging, attachments, approvals, and project dashboards.

## Run locally

Prerequisites: Python 3.11+ and Node 20+.

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload --port 8000
```

In another terminal:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Open the URL printed by Vite (normally `http://localhost:5173`). The API docs are at `http://localhost:8000/docs`.

The database is created at `backend/data/agencydesk.db`. Run `python -m app.seed --reset` to restore the deterministic demo dataset.

## Demo accounts

All demo accounts use password `demo-password`.

| Account | Role | Agency |
| --- | --- | --- |
| ada@northstar.test | agency_admin | Northstar Studio |
| maya@northstar.test | agency_member | Northstar Studio |
| sam@acme.test | client_user | Acme / Northstar Studio |
| ada@brightwave.test | agency_admin | Brightwave Agency |

The same person (Ada) exists once in `users` and has memberships at both agencies, illustrating the cross-agency identity model.

## Verification

With the virtual environment active:

```powershell
pytest
```

The tests exercise cross-tenant reads/writes, client visibility filtering, client write limits, invite idempotency, and task unassignment when a member is removed from a project.

## Project layout

`backend/migrations/001_initial.sql` contains the normalized SQLite schema and integrity triggers. `backend/app/main.py` is the API and authorization layer. `frontend/` is the React/Vite app. `DESIGN.md` explains the important access-control decisions.

## API authentication

`POST /auth/login` returns a short-lived opaque bearer token in this demo. Send it as `Authorization: Bearer <token>`. All protected endpoints independently scope database queries by the authenticated actor—not by client-provided agency IDs.
