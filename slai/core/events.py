from __future__ import annotations

import json
from typing import Any
import uuid

from ..db import get_connection
from .state import DealState, utc_now

def append_event(
    state: DealState,
    event_type: str,
    payload: dict[str, Any] | None = None,
    node: str | None = None,
) -> DealState:
    created_at = utc_now()
    actual_node = node or state.get("current_node", "")
    actual_payload = payload or {}

    event = {
        "event_id": str(uuid.uuid4()),
        "event_type": event_type,
        "node": actual_node,
        "created_at": created_at,
        "payload": actual_payload,
    }

    events = list(state.get("events", []))
    events.append(event)

    state["events"] = events
    state["updated_at"] = created_at

    try:
        with get_connection() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO workflow_events (
                    event_id,
                    thread_id,
                    deal_id,
                    event_type,
                    node,
                    payload_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event["event_id"],
                    str(state.get("run_id", "")),
                    state.get("deal_id"),
                    event_type,
                    actual_node,
                    json.dumps(actual_payload, ensure_ascii=False, default=str),
                    created_at,
                ),
            )
    except Exception:
        # Если таблица ещё не инициализирована в кастомном окружении, не прерываем работу state
        pass

    return state
