import os, sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("AGENCYDESK_DB", ROOT / "data" / "agencydesk.db"))

def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

def migrate(con):
    con.executescript((ROOT / "migrations" / "001_initial.sql").read_text())
    con.commit()
