import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from slai import db
from slai.workflow.engine import finish_success
from slai.core.checkpoints import SQLiteCheckpointStore
from slai.core.events import append_event
from slai.core.state import create_initial_state

class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

        self.old_db_path = db.DB_PATH
        db.DB_PATH = Path(self.temp_dir.name) / "test.db"

        db.init_db()

    def tearDown(self):
        db.DB_PATH = self.old_db_path
        self.temp_dir.cleanup()

    def test_finish_success_persists_result_calculation_and_audit(self):
        with db.get_connection() as conn:
            deal_cursor = conn.execute(
                """
                INSERT INTO deals (
                    supplier_name,
                    product_name,
                    quantity,
                    unit_price,
                    currency,
                    incoterm,
                    payment_terms,
                    production_days,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "Test Supplier",
                    "Test Product",
                    20,
                    1400.0,
                    "CNY",
                    "EXW",
                    "40% deposit",
                    30,
                    "draft",
                ),
            )

            deal_id = deal_cursor.lastrowid

            run_cursor = conn.execute(
                """
                INSERT INTO workflow_runs (
                    deal_id,
                    status,
                    current_step
                )
                VALUES (?, ?, ?)
                """,
                (
                    deal_id,
                    "running",
                    "start",
                ),
            )

            run_id = run_cursor.lastrowid

        calculation = {
            "quantity": 20,
            "unit_price": 1400.0,
            "goods_cost": 28000.0,
            "total_cost": 28000.0,
            "unit_cost": 1400.0,
        }

        audit = {
            "risk_level": "low",
            "risks": [],
            "recommendations": ["Документы проверены"],
            "missing_information": [],
        }

        result = SimpleNamespace(
            status="completed",
            deal_id=deal_id,
            missing_fields=[],
            documents=[],
            calculation=calculation,
            audit=audit,
            errors=[],
        )

        finish_success(
            run_id=run_id,
            deal_id=deal_id,
            result=result,
            audit=audit,
        )

        with db.get_connection() as conn:
            workflow_row = conn.execute(
                """
                SELECT
                    id,
                    deal_id,
                    status,
                    result_json
                FROM workflow_runs
                WHERE id = ?
                """,
                (run_id,),
            ).fetchone()

            audit_row = conn.execute(
                """
                SELECT
                    id,
                    deal_id,
                    run_id,
                    audit_json,
                    is_valid
                FROM audit_results
                WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()

        self.assertIsNotNone(workflow_row)
        self.assertIsNotNone(audit_row)

        self.assertEqual(workflow_row["deal_id"], deal_id)
        self.assertEqual(workflow_row["status"], "completed")

        saved_result = json.loads(workflow_row["result_json"])

        self.assertEqual(
            saved_result["calculation"],
            calculation,
        )

        self.assertEqual(audit_row["deal_id"], deal_id)
        self.assertEqual(audit_row["run_id"], run_id)
        self.assertEqual(audit_row["is_valid"], 1)

        saved_audit = json.loads(audit_row["audit_json"])

        self.assertEqual(
            saved_audit,
            audit,
        )


    def test_finish_success_marks_high_risk_audit_invalid(self):
        with db.get_connection() as conn:
            deal_cursor = conn.execute(
                """
                INSERT INTO deals (
                    supplier_name,
                    product_name,
                    quantity,
                    unit_price,
                    currency,
                    incoterm,
                    payment_terms,
                    production_days,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "Risk Supplier",
                    "Risk Product",
                    20,
                    1400.0,
                    "CNY",
                    "EXW",
                    "40% deposit",
                    30,
                    "draft",
                ),
            )

            deal_id = deal_cursor.lastrowid

            run_cursor = conn.execute(
                """
                INSERT INTO workflow_runs (
                    deal_id,
                    status,
                    current_step
                )
                VALUES (?, ?, ?)
                """,
                (
                    deal_id,
                    "running",
                    "audit",
                ),
            )

            run_id = run_cursor.lastrowid

        audit = {
            "risk_level": "high",
            "risks": [
                {
                    "title": "Риск предоплаты",
                    "description": "Обнаружен существенный риск предоплаты.",
                    "severity": "high",
                    "source": "uploaded document",
                }
            ],
            "recommendations": [
                "Проверить условия оплаты до подтверждения сделки."
            ],
            "missing_information": [],
        }

        result = SimpleNamespace(
            status="completed",
            deal_id=deal_id,
            missing_fields=[],
            documents=[],
            calculation={},
            audit=audit,
            errors=[],
        )

        finish_success(
            run_id=run_id,
            deal_id=deal_id,
            result=result,
            audit=audit,
        )

        with db.get_connection() as conn:
            audit_row = conn.execute(
                """
                SELECT is_valid
                FROM audit_results
                WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()

        self.assertIsNotNone(audit_row)
        self.assertEqual(audit_row["is_valid"], 0)


    def test_checkpoint_and_event_persistence(self):
        checkpoint_path = Path(self.temp_dir.name) / "checkpoints.sqlite3"
        store = SQLiteCheckpointStore(checkpoint_path)

        state = create_initial_state(
            deal_id=77,
            run_id="thread-77",
        )
        append_event(
            state,
            event_type="workflow.started",
            payload={"deal_id": 77},
            node="start",
        )
        store.save("thread-77", state)

        loaded = store.load("thread-77")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["deal_id"], 77)
        self.assertEqual(len(loaded["events"]), 1)
        self.assertEqual(loaded["events"][0]["event_type"], "workflow.started")

        with db.get_connection() as conn:
            event_row = conn.execute(
                """
                SELECT thread_id, deal_id, event_type, node
                FROM workflow_events
                WHERE thread_id = ?
                """,
                ("thread-77",),
            ).fetchone()

        self.assertIsNotNone(event_row)
        self.assertEqual(event_row["deal_id"], 77)
        self.assertEqual(event_row["event_type"], "workflow.started")
        self.assertEqual(event_row["node"], "start")

if __name__ == "__main__":
    unittest.main()
