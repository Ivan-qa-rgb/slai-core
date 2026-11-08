from __future__ import annotations

from typing import Any

from slai.core import (
    SQLiteCheckpointStore,
    append_event,
    create_deal_state,
)

from .steps import STEPS

def to_jsonable(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, dict):
        return {
            str(key): to_jsonable(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            to_jsonable(item)
            for item in value
        ]

    if hasattr(value, "to_dict"):
        return to_jsonable(value.to_dict())

    if hasattr(value, "__dict__"):
        return to_jsonable(value.__dict__)

    return value

def get_deal_id(
    context: dict[str, Any],
) -> int | str:
    deal = context.get("deal")

    if deal is not None:
        deal_id = getattr(deal, "id", None)

        if deal_id is not None:
            return deal_id

    return context.get(
        "deal_id",
        "unknown",
    )

def sync_state_from_context(
    state: dict[str, Any],
    context: dict[str, Any],
) -> None:
    state["documents"] = to_jsonable(
        context.get("documents", [])
    )

    state["rules"] = to_jsonable(
        context.get("rules", [])
    )

    result = context.get("result")

    if result is None:
        return

    result_data = to_jsonable(result)

    state["calculation"] = result_data.get(
        "calculation",
        {},
    )

    state["audit"] = result_data.get(
        "audit",
        {},
    )

    state["errors"] = result_data.get(
        "errors",
        [],
    )

    state["missing_information"] = result_data.get(
        "missing_fields",
        [],
    )

    audit = state.get("audit") or {}

    if isinstance(audit, dict):
        state["risks"] = audit.get(
            "risks",
            [],
        )

        state["recommendations"] = audit.get(
            "recommendations",
            [],
        )

        state["extracted_facts"] = audit.get(
            "extracted_facts",
            audit.get("facts", {}),
        )

        state["compliance_analysis"] = audit.get(
            "compliance_analysis",
            {},
        )

        state["customs_analysis"] = audit.get(
            "customs_analysis",
            {},
        )

def restore_context_from_state(
    context: dict[str, Any],
    state: dict[str, Any],
) -> None:
    if state.get("rules"):
        context["rules"] = state["rules"]

    result = context.get("result")

    if result is None:
        return

    if state.get("calculation"):
        result.calculation = state["calculation"]

    if state.get("audit"):
        result.audit = state["audit"]

    if state.get("missing_information"):
        result.missing_fields = state[
            "missing_information"
        ]

    saved_errors = state.get("errors", [])

    if saved_errors:
        result.errors = [
            item
            if isinstance(item, str)
            else str(item)
            for item in saved_errors
        ]

def get_completed_steps(
    state: dict[str, Any],
) -> set[str]:
    completed = set()

    for event in state.get("events", []):
        if event.get("event_type") != "node.completed":
            continue

        node = event.get("node")

        if node:
            completed.add(node)

    return completed

def run_graph(
    context: dict[str, Any],
    thread_id: str | None = None,
    checkpoint_store: SQLiteCheckpointStore | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if checkpoint_store is None:
        checkpoint_store = SQLiteCheckpointStore()

    existing_state = None

    if thread_id:
        existing_state = checkpoint_store.load(
            thread_id
        )

    if existing_state is not None:
        state = existing_state
        actual_thread_id = thread_id

        restore_context_from_state(
            context,
            state,
        )

        if state.get("status") == "completed":
            return context, state

        append_event(
            state,
            event_type="workflow.resumed",
            payload={
                "thread_id": actual_thread_id,
                "previous_node": state.get(
                    "current_node",
                    "",
                ),
            },
            node="resume",
        )

    else:
        deal_id = get_deal_id(context)

        state = create_deal_state(
            deal_id=deal_id,
            run_id=thread_id,
        )

        actual_thread_id = state["run_id"]

        state["current_node"] = "start"
        state["status"] = "running"

        sync_state_from_context(
            state,
            context,
        )

        append_event(
            state,
            event_type="workflow.started",
            payload={
                "deal_id": deal_id,
                "thread_id": actual_thread_id,
            },
            node="start",
        )

    state["status"] = "running"

    checkpoint_store.save(
        actual_thread_id,
        state,
    )

    completed_steps = get_completed_steps(
        state
    )

    try:
        for step_name, step_function in STEPS:
            if step_name in completed_steps:
                continue

            state["current_node"] = step_name

            append_event(
                state,
                event_type="node.started",
                payload={
                    "step": step_name,
                },
                node=step_name,
            )

            checkpoint_store.save(
                actual_thread_id,
                state,
            )

            step_function(context)

            sync_state_from_context(
                state,
                context,
            )

            append_event(
                state,
                event_type="node.completed",
                payload={
                    "step": step_name,
                },
                node=step_name,
            )

            checkpoint_store.save(
                actual_thread_id,
                state,
            )

            completed_steps.add(step_name)

        sync_state_from_context(
            state,
            context,
        )

        state["current_node"] = "completed"
        state["status"] = "completed"

        append_event(
            state,
            event_type="workflow.completed",
            payload={
                "deal_id": get_deal_id(context),
            },
            node="completed",
        )

        checkpoint_store.save(
            actual_thread_id,
            state,
        )

        return context, state

    except Exception as error:
        sync_state_from_context(
            state,
            context,
        )

        state["status"] = "failed"

        state["errors"] = [
            *state.get("errors", []),
            {
                "type": type(error).__name__,
                "message": str(error),
                "node": state.get(
                    "current_node",
                    "",
                ),
            },
        ]

        append_event(
            state,
            event_type="workflow.failed",
            payload={
                "error_type": type(error).__name__,
                "error": str(error),
            },
            node=state.get(
                "current_node",
                "",
            ),
        )

        checkpoint_store.save(
            actual_thread_id,
            state,
        )

        raise
