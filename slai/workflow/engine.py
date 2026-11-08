import json
import traceback
from datetime import datetime, timezone

from ..db import get_connection
from ..models import WorkflowResult
from .steps import WorkflowValidationError
from .graph_adapter import run_graph
from .normalize_audit import normalize_audit
from .validate_audit import validate_audit


def _build_workflow_error(error, current_step):
    return {
        "type": type(error).__name__,
        "step": current_step,
        "message": str(error),
    }


def run_workflow(deal, documents, thread_id=None):
    context = {
        "deal": deal,
        "documents": documents,
        "rules": [],
        "result": WorkflowResult(
            status="running",
            deal_id=deal.id,
            missing_fields=[],
            documents=[],
            calculation={},
            audit={},
            errors=[],
        ),
    }

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO workflow_runs (
                deal_id,
                status,
                current_step
            )
            VALUES (?, ?, ?)
            """,
            (
                deal.id,
                "running",
                "start",
            ),
        )

        run_id = cursor.lastrowid

    current_step = "start"
    actual_thread_id = thread_id or f"workflow-{run_id}"

    context["result"].thread_id = actual_thread_id

    try:
        context, graph_state = run_graph(
            context,
            thread_id=actual_thread_id,
        )

        current_step = graph_state.get(
            "current_node",
            "completed",
        )

        context["result"].thread_id = graph_state.get(
            "run_id",
            actual_thread_id,
        )

        context["result"].status = "completed"

        finish_success(
            run_id=run_id,
            deal_id=deal.id,
            result=context["result"],
            audit=context["result"].audit,
        )

    except WorkflowValidationError as error:
        final_status = "missing_data"

        context["result"].status = final_status
        context["result"].errors.append(
            _build_workflow_error(
                error,
                current_step,
            )
        )

        finish_run(
            run_id,
            final_status,
            context["result"],
            error_message=(
                f"step={current_step}; "
                f"error={error}"
            ),
        )

    except Exception as error:
        traceback.print_exc()

        final_status = "failed"

        context["result"].status = final_status
        context["result"].errors.append(
            _build_workflow_error(
                error,
                current_step,
            )
        )

        finish_run(
            run_id,
            final_status,
            context["result"],
            error_message=(
                f"step={current_step}; "
                f"error={error}"
            ),
        )

    return context["result"]


def update_run_status(
    run_id,
    status,
    current_step,
):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE workflow_runs
            SET
                status = ?,
                current_step = ?
            WHERE id = ?
            """,
            (
                status,
                current_step,
                run_id,
            ),
        )


def finish_run(
    run_id,
    status,
    result,
    error_message=None,
):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE workflow_runs
            SET
                status = ?,
                result_json = ?,
                error_message = ?,
                finished_at = ?
            WHERE id = ?
            """,
            (
                status,
                json.dumps(
                    result.__dict__,
                    ensure_ascii=False,
                ),
                error_message,
                datetime.now(
                    timezone.utc
                ).isoformat(),
                run_id,
            ),
        )


def save_audit_result(
    deal_id,
    run_id,
    audit,
    is_valid,
):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO audit_results (
                deal_id,
                run_id,
                audit_json,
                is_valid
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                deal_id,
                run_id,
                json.dumps(
                    audit,
                    ensure_ascii=False,
                ),
                int(is_valid),
            ),
        )


def finish_success(
    run_id,
    deal_id,
    result,
    audit,
):
    normalized_audit = normalize_audit(audit)

    validation_errors = validate_audit(
        normalized_audit
    )

    is_valid = not validation_errors

    result.audit = normalized_audit

    result_json = json.dumps(
        result.__dict__,
        ensure_ascii=False,
    )

    audit_json = json.dumps(
        normalized_audit,
        ensure_ascii=False,
    )

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO audit_results (
                deal_id,
                run_id,
                audit_json,
                is_valid
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                deal_id,
                run_id,
                audit_json,
                int(is_valid),
            ),
        )

        conn.execute(
            """
            UPDATE workflow_runs
            SET
                status = ?,
                result_json = ?,
                error_message = NULL,
                finished_at = ?
            WHERE id = ?
            """,
            (
                "completed",
                result_json,
                datetime.now(
                    timezone.utc
                ).isoformat(),
                run_id,
            ),
        )
