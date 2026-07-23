import argparse
import hashlib

from .db import DB_PATH, connect, migrate


def pw(value):
    return hashlib.sha256(value.encode()).hexdigest()


def seed(reset=False):
    if reset and DB_PATH.exists():
        DB_PATH.unlink()

    con = connect()
    migrate(con)

    if con.execute("SELECT count(*) FROM agencies").fetchone()[0]:
        return

    cur = con.cursor()

    cur.executemany(
        "INSERT INTO agencies(id, name) VALUES(?, ?)",
        [
            (1, "Northstar Studio"),
            (2, "Brightwave Agency"),
        ],
    )

    users = [
        (1, "ada@northstar.test", "Ada Admin"),
        (2, "maya@northstar.test", "Maya Member"),
        (3, "sam@acme.test", "Sam Client"),
        (4, "ada@brightwave.test", "Ada Brightwave"),
        (5, "liam@brightwave.test", "Liam Member"),
        (6, "grace@globex.test", "Grace Client"),
    ]

    cur.executemany(
        "INSERT INTO users(id, email, display_name, password_hash) VALUES(?, ?, ?, ?)",
        [(user_id, email, name, pw("demo-password")) for user_id, email, name in users],
    )

    cur.executemany(
        "INSERT INTO agency_memberships(id, agency_id, user_id, role) VALUES(?, ?, ?, ?)",
        [
            (1, 1, 1, "agency_admin"),   # Ada - Northstar admin
            (2, 1, 2, "agency_member"), # Maya - Northstar member
            (3, 2, 1, "agency_admin"),  # Ada - Brightwave admin
            (4, 2, 4, "agency_admin"),  # Ada Brightwave - Brightwave admin
            (5, 2, 5, "agency_member"), # Liam - Brightwave member
        ],
    )

    cur.executemany(
        "INSERT INTO clients(id, agency_id, name) VALUES(?, ?, ?)",
        [
            (1, 1, "Acme Corporation"),
            (2, 2, "Globex"),
        ],
    )

    cur.executemany(
        "INSERT INTO client_contacts(client_id, user_id) VALUES(?, ?)",
        [
            (1, 3),  # Sam is Acme client user
            (2, 6),  # Grace is Globex client user
        ],
    )

    cur.executemany(
        "INSERT INTO projects(id, agency_id, client_id, name, description) VALUES(?, ?, ?, ?, ?)",
        [
            (1, 1, 1, "Acme Website Refresh", "A client website redesign"),
            (2, 2, 2, "Globex Brand Work", "A separate tenant project"),
        ],
    )

    cur.executemany(
        "INSERT INTO project_members(project_id, membership_id) VALUES(?, ?)",
        [
            (1, 1),
            (1, 2),
            (2, 3),
            (2, 5),
        ],
    )

    cur.executemany(
        """
        INSERT INTO tasks(
            id, agency_id, project_id, title, description, status,
            priority, assignee_membership_id, due_date, is_client_visible
        )
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                1, 1, 1,
                "Homepage design review",
                "Client may review this design",
                "in_progress",
                "high",
                2,
                "2026-08-01",
                1,
            ),
            (
                2, 1, 1,
                "Analytics instrumentation",
                "Internal tracking plan",
                "todo",
                "medium",
                2,
                "2026-08-05",
                0,
            ),
            (
                3, 2, 2,
                "Globex moodboard",
                "Client can review this moodboard",
                "todo",
                "high",
                5,
                "2026-08-03",
                1,
            ),
        ],
    )

    cur.executemany(
        "INSERT INTO comments(task_id, author_user_id, body, is_client_visible) VALUES(?, ?, ?, ?)",
        [
            (1, 1, "Please review the latest draft.", 1),
            (2, 2, "Do not expose vendor credentials.", 0),
            (3, 5, "Moodboard is ready for review.", 1),
        ],
    )

    cur.execute(
        """
        INSERT INTO time_entries(task_id, membership_id, minutes, note, entry_date)
        VALUES(1, 2, 90, 'Initial design pass', '2026-07-20')
        """
    )

    cur.executemany(
        """
        INSERT INTO attachments(
            task_id, uploader_user_id, filename, storage_key, is_client_visible
        )
        VALUES(?, ?, ?, ?, ?)
        """,
        [
            (1, 1, "homepage-v2.pdf", "demo/homepage-v2.pdf", 1),
            (2, 2, "tracking-plan.txt", "demo/tracking-plan.txt", 0),
            (3, 5, "globex-moodboard.pdf", "demo/globex-moodboard.pdf", 1),
        ],
    )

    con.commit()
    con.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    seed(args.reset)
    print(f"Seeded {DB_PATH}")