import json
import logging
from collections import deque
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any, Iterator

from decision_models import (
    AgentDecision,
    AgentState,
    RespondToTradeAction,
    validate_decision,
)
from settings import ROOT

logger = logging.getLogger(__name__)

TRADE_MEMORY_PATH = ROOT / "trade_memory.jsonl"
MAX_RECENT_DECISIONS = 10

_lock = Lock()


def _read_records(path: Path) -> Iterator[dict[str, Any]]:
    if not path.exists():
        return

    with path.open(encoding="utf-8") as memory_file:
        for line_number, line in enumerate(memory_file, start=1):
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                logger.warning(
                    "Skipping malformed trade memory record at %s:%d",
                    path,
                    line_number,
                )
                continue

            if not isinstance(record, dict):
                logger.warning(
                    "Skipping non-object trade memory record at %s:%d",
                    path,
                    line_number,
                )
                continue
            yield record


def get_recent_trade_decisions(
    responder_id: str,
    path: Path = TRADE_MEMORY_PATH,
) -> list[dict[str, Any]]:
    """Return the newest validated trade responses for one NPC."""
    recent: deque[dict[str, Any]] = deque(maxlen=MAX_RECENT_DECISIONS)
    with _lock:
        for record in _read_records(path):
            if record.get("responder_id") == responder_id:
                recent.append(record)
    return list(reversed(recent))


def record_validated_trade_decision(
    state: AgentState,
    decision: AgentDecision,
    path: Path = TRADE_MEMORY_PATH,
) -> bool:
    """Append a validated response once per offer and responding NPC."""
    action = decision.action
    if not isinstance(action, RespondToTradeAction):
        return False

    validate_decision(decision, state)
    offer = next(
        offer
        for offer in state.pending_offers
        if offer.offer_id == action.offer_id
    )
    record = {
        "offer_id": offer.offer_id,
        "responder_id": state.agent_id,
        "initiator_id": offer.initiator_id,
        "offered_item_id": offer.offered_item_id,
        "offered_quantity": offer.offered_quantity,
        "requested_item_id": offer.requested_item_id,
        "requested_quantity": offer.requested_quantity,
        "accepted": action.accept,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    with _lock:
        if any(
            existing.get("offer_id") == record["offer_id"]
            and existing.get("responder_id") == record["responder_id"]
            for existing in _read_records(path)
        ):
            return False

        with path.open("a", encoding="utf-8") as memory_file:
            memory_file.write(json.dumps(record, separators=(",", ":")) + "\n")
    return True
