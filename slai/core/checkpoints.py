from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

class SQLiteCheckpointStore:
    def __init__(
        self,
        database_path: str | Path = "data/slai_checkpoints.sqlite3",
    ):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
        except Exception:
            connection.rollback()
            raise
        else:
            connection.commit()
        finally:
            connection.close()

    def _initialize(self):
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_checkpoints (
                    thread_id TEXT PRIMARY KEY,
                    state_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def save(
        self,
        thread_id: str,
        state: dict[str, Any],
    ) -> None:
        state_json = json.dumps(
            state,
            ensure_ascii=False,
            default=str,
        )
        updated_at = state.get("updated_at", "")

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO workflow_checkpoints (
                    thread_id,
                    state_json,
                    updated_at
                )
                VALUES (?, ?, ?)
                ON CONFLICT(thread_id)
                DO UPDATE SET
                    state_json = excluded.state_json,
                    updated_at = excluded.updated_at
                """,
                (
                    thread_id,
                    state_json,
                    updated_at,
                ),
            )

    def load(
        self,
        thread_id: str,
    ) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT state_json
                FROM workflow_checkpoints
                WHERE thread_id = ?
                """,
                (thread_id,),
            ).fetchone()

        if row is None:
            return None

        return json.loads(row["state_json"])

    def delete(
        self,
        thread_id: str,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                DELETE FROM workflow_checkpoints
                WHERE thread_id = ?
                """,
                (thread_id,),
            )
