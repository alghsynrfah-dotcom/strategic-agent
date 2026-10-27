import sqlite3
import time
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "agent.db"


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _execute(sql, params=(), fetch=None):
    DATA_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        if fetch == "one":
            row = cur.fetchone()
            return dict(row) if row else None
        if fetch == "all":
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def _ensure_columns():
    """بيضيف أعمدة الخطة والمخاطر للجدول الموجود بدون ما يمسح البيانات."""
    for column in ("plan", "risks"):
        try:
            _execute(f"ALTER TABLE projects ADD COLUMN {column} TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass  # العمود موجود أصلاً


def init_db():
    _execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            domain TEXT NOT NULL,
            created_at TEXT NOT NULL,
            initial_problem TEXT DEFAULT '',
            statement TEXT DEFAULT '',
            statement_status TEXT DEFAULT 'none',
            confirmed_statement TEXT DEFAULT ''
        )
    """)
    _execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    _ensure_columns()


def create_project(project_id: str, domain: str):
    _execute(
        "INSERT INTO projects (id, domain, created_at) VALUES (?, ?, ?)",
        (project_id, domain, _now()),
    )


def get_project(project_id: str):
    return _execute("SELECT * FROM projects WHERE id = ?", (project_id,), fetch="one")


def add_message(project_id: str, role: str, content: str):
    _execute(
        "INSERT INTO messages (project_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (project_id, role, content, _now()),
    )


def list_messages(project_id: str):
    return _execute(
        "SELECT role, content, created_at FROM messages WHERE project_id = ? ORDER BY id",
        (project_id,),
        fetch="all",
    )


def update_project(project_id: str, initial_problem: str, statement: str, status: str,
                   plan: str = "", risks: str = ""):
    # البيان المؤكد صراحة بيتخزن لحاله، وبينمسح إذا البيان رجع للتعديل
    confirmed = statement if status == "confirmed" else ""
    _execute(
        "UPDATE projects SET initial_problem = ?, statement = ?, statement_status = ?, "
        "confirmed_statement = ?, plan = ?, risks = ? WHERE id = ?",
        (initial_problem, statement, status, confirmed, plan, risks, project_id),
    )
