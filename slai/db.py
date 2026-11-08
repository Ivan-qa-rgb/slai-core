import sqlite3
from contextlib import contextmanager


from .config import DB_PATH



@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")


    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    else:
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS deals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                supplier_name TEXT NOT NULL,
                product_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                currency TEXT NOT NULL,
                incoterm TEXT,
                payment_terms TEXT,
                production_days INTEGER,
                status TEXT NOT NULL DEFAULT 'draft',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );


            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id INTEGER NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL DEFAULT '',
                document_type TEXT,
                extracted_text TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (deal_id) REFERENCES deals(id)
            );


            CREATE TABLE IF NOT EXISTS workflow_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                current_step TEXT,
                result_json TEXT,
                error_message TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                finished_at TEXT,
                FOREIGN KEY (deal_id) REFERENCES deals(id)
            );


            CREATE TABLE IF NOT EXISTS audit_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                deal_id INTEGER NOT NULL,
                run_id INTEGER NOT NULL,
                audit_json TEXT NOT NULL,
                is_valid INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (deal_id) REFERENCES deals(id),
                FOREIGN KEY (run_id) REFERENCES workflow_runs(id)
            );


            CREATE INDEX IF NOT EXISTS idx_documents_deal_id
            ON documents(deal_id);


            CREATE INDEX IF NOT EXISTS idx_workflow_runs_deal_id
            ON workflow_runs(deal_id);


            CREATE INDEX IF NOT EXISTS idx_audit_results_deal_id
            ON audit_results(deal_id);


            CREATE INDEX IF NOT EXISTS idx_audit_results_run_id
            ON audit_results(run_id);


            CREATE TABLE IF NOT EXISTS workflow_checkpoints (
                thread_id TEXT PRIMARY KEY,
                state_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );


            CREATE TABLE IF NOT EXISTS workflow_events (
                event_id TEXT PRIMARY KEY,
                thread_id TEXT,
                deal_id INTEGER,
                event_type TEXT NOT NULL,
                node TEXT,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );


            CREATE INDEX IF NOT EXISTS idx_workflow_events_thread_id
            ON workflow_events(thread_id);


            CREATE INDEX IF NOT EXISTS idx_workflow_events_deal_id
            ON workflow_events(deal_id);


            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'viewer',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_users_email
            ON users(email);

            """
        )



def get_documents_for_deal(deal_id):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, file_name, document_type, extracted_text
            FROM documents
            WHERE deal_id = ?
            ORDER BY id
            """,
            (deal_id,),
        ).fetchall()


    return [
        {
            "id": row["id"],
            "file_name": row["file_name"],
            "document_type": row["document_type"],
            "extracted_text": row["extracted_text"] or "",
        }
        for row in rows
    ]
