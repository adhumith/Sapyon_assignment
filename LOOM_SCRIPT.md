# 3–5 minute Loom walkthrough

**0:00–0:25 — framing**

“This is AgencyDesk, a multi-tenant client and project workspace. I focused on the hard parts of the assignment: tenant isolation, RBAC, client visibility, and the requested edge cases. It uses a React frontend, a Python FastAPI backend, and SQLite.”

**0:25–1:20 — agency view**

“I’ll sign in as Ada, Northstar’s admin. The project dashboard shows task totals by status and logged hours. The task list includes both the visible homepage review and the internal analytics task. An admin can create work, assign a project member, and log time. Attachments are independently marked client-visible, so an internal task does not accidentally make a file visible.”

**1:20–2:05 — client portal**

“Now I’ll switch to Sam, a contact for Acme at Northstar. The exact same project view contains only the client-visible task. Internal work, internal comments, internal attachments, assignee data, and time entries are absent. Sam can add a comment and approve a visible file, but there are no controls to create a task, change its status, or log time.”

**2:05–2:50 — schema and isolation**

“In the migration, tenant-owned rows include agency IDs. Foreign keys and triggers reject inconsistent tenant relationships. At the API boundary, every resource is resolved through the authenticated user’s membership or client-contact relationship; routes never accept a trusted tenant ID. This means guessing Brightwave’s project ID while logged in to Northstar cannot return it.”

**2:50–3:30 — identity and edge cases**

“Users are global and memberships are per agency, so one email can belong to multiple agencies with different roles. Invites are unique per agency and email, and acceptance is idempotent. Finally, when a member is removed from a project, their task assignments are cleared in the same transaction while tasks and historical time entries stay intact.”

**3:30–4:00 — proof**

“I’ll run the test suite. These tests prove tenant A cannot read or write tenant B data, clients cannot retrieve internal content by direct ID, and the invite and member-removal edge cases hold. The README has the exact commands to seed, run, and test the application.”
