import logging
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

logger = logging.getLogger(__name__)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class InventoryItem(StrictModel):
    item_id: str = Field(
        min_length=1,
        description="Exact item ID used by Unreal.",
    )
    quantity: int = Field(
        ge=0,
        description="Available quantity of this item.",
    )


class KnownAgent(StrictModel):
    id: str = Field(
        min_length=1,
        description="Unique identifier of the known agent.",
    )
    inventory: list[InventoryItem] = Field(
        description=(
            "Goods visible to the deciding agent. For the initial "
            "prototype, inventories are public."
        ),
    )


class TradeOffer(StrictModel):
    offer_id: str = Field(min_length=1)
    initiator_id: str = Field(min_length=1)
    recipient_id: str = Field(min_length=1)

    offered_item_id: str = Field(min_length=1)
    offered_quantity: int = Field(gt=0)

    requested_item_id: str = Field(min_length=1)
    requested_quantity: int = Field(gt=0)


class AgentState(StrictModel):
    """The deciding agent's observation, supplied by Unreal."""

    agent_id: str = Field(
        min_length=1,
        description="Unique identifier of the deciding agent.",
    )
    health: float = Field(
        ge=0,
        le=100,
        description="Health from 0 to 100.",
    )
    hunger: float = Field(
        ge=0,
        le=100,
        description="Hunger: 0 means full; 100 means starving.",
    )
    goal: str = Field(
        description="Current objective that should guide the decision.",
    )

    inventory: list[InventoryItem]
    known_agents: list[KnownAgent]
    pending_offers: list[TradeOffer] = Field(
        description="Active incoming offers this agent may respond to.",
    )


class Action(StrictModel):
    """Base class for every action an agent can take."""

    action: str
    reason: str = Field(
        min_length=1,
        description=(
            "Brief explanation for web display only. "
            "Does not authorize or execute gameplay actions."
        ),
    )


class ProposeTradeAction(Action):
    action: Literal["propose_trade"] = "propose_trade"

    partner_id: str = Field(min_length=1)
    offered_item_id: str = Field(min_length=1)
    offered_quantity: int = Field(gt=0)
    requested_item_id: str = Field(min_length=1)
    requested_quantity: int = Field(gt=0)


class RespondToTradeAction(Action):
    action: Literal["respond_to_trade"] = "respond_to_trade"

    offer_id: str = Field(
        min_length=1,
        description="ID of an active incoming offer.",
    )
    accept: bool = Field(
        description="True accepts the offer; false rejects it.",
    )


class WaitAction(Action):
    action: Literal["wait"] = "wait"


PossibleAction = Annotated[
    ProposeTradeAction | RespondToTradeAction | WaitAction,
    Field(discriminator="action"),
]


class AgentDecision(StrictModel):
    """The only output the decision endpoint permits."""

    action: PossibleAction


def item_quantity(
    inventory: list[InventoryItem],
    item_id: str,
) -> int:
    """Sum quantities in case an item occupies multiple slots."""
    return sum(
        item.quantity
        for item in inventory
        if item.item_id == item_id
    )


def build_decision_schema(state: AgentState) -> dict[str, object]:
    """Expose action choices available in this observation.

    This schema narrows the choices, but validate_decision must still
    check partner/item combinations and available quantities.
    """
    actions = [_action_schema("wait")]

    offered_ids = sorted(
        {
            item.item_id
            for item in state.inventory
            if item.quantity > 0
        }
    )

    partners = [
        agent
        for agent in state.known_agents
        if agent.id != state.agent_id
        and any(item.quantity > 0 for item in agent.inventory)
    ]

    if offered_ids and partners:
        requested_ids = sorted(
            {
                item.item_id
                for agent in partners
                for item in agent.inventory
                if item.quantity > 0
            }
        )

        actions.append(
            _action_schema(
                "propose_trade",
                partner_id={
                    "type": "string",
                    "enum": sorted({agent.id for agent in partners}),
                },
                offered_item_id={
                    "type": "string",
                    "enum": offered_ids,
                },
                offered_quantity={"type": "integer", "minimum": 1},
                requested_item_id={
                    "type": "string",
                    "enum": requested_ids,
                },
                requested_quantity={"type": "integer", "minimum": 1},
            )
        )

    incoming_offer_ids = sorted(
        {
            offer.offer_id
            for offer in state.pending_offers
            if offer.recipient_id == state.agent_id
            and offer.initiator_id != state.agent_id
        }
    )

    if incoming_offer_ids:
        actions.append(
            _action_schema(
                "respond_to_trade",
                offer_id={
                    "type": "string",
                    "enum": incoming_offer_ids,
                },
                accept={"type": "boolean"},
            )
        )

    return {
        "type": "object",
        "properties": {"action": {"anyOf": actions}},
        "required": ["action"],
        "additionalProperties": False,
    }


def _action_schema(
    action: str,
    **parameters: object,
) -> dict[str, object]:
    properties: dict[str, object] = {
        "action": {"type": "string", "enum": [action]},
        **parameters,
        "reason": {
            "type": "string",
            "minLength": 1,
            "description": "Brief explanation for web display only.",
        },
    }

    return {
        "type": "object",
        "properties": properties,
        "required": ["action", *parameters, "reason"],
        "additionalProperties": False,
    }


def validate_decision(
    decision: AgentDecision,
    state: AgentState,
) -> None:
    """Validate an action against the supplied observation.

    Unreal must revalidate the live world state before execution.
    """
    action = decision.action

    if isinstance(action, WaitAction):
        return

    if isinstance(action, ProposeTradeAction):
        if action.partner_id == state.agent_id:
            raise ValueError("An agent cannot trade with itself.")

        partner = next(
            (
                agent
                for agent in state.known_agents
                if agent.id == action.partner_id
            ),
            None,
        )

        if partner is None:
            raise ValueError("The trade partner is not a known agent.")

        available = item_quantity(
            state.inventory,
            action.offered_item_id,
        )

        if action.offered_quantity > available:
            raise ValueError(
                "The offered quantity exceeds the agent's inventory."
            )

        available = item_quantity(
            partner.inventory,
            action.requested_item_id,
        )

        if action.requested_quantity > available:
            raise ValueError(
                "The requested quantity exceeds the partner's "
                "observed inventory."
            )

        return

    if isinstance(action, RespondToTradeAction):
        offer = next(
            (
                offer
                for offer in state.pending_offers
                if offer.offer_id == action.offer_id
            ),
            None,
        )

        if offer is None:
            raise ValueError("The offer is not active or known.")

        if offer.recipient_id != state.agent_id:
            raise ValueError("The offer belongs to another recipient.")

        if offer.initiator_id == state.agent_id:
            raise ValueError("An agent cannot respond to its own offer.")

        # Rejection does not require ownership of the requested goods.
        if not action.accept:
            return

        available = item_quantity(
            state.inventory,
            offer.requested_item_id,
        )

        if offer.requested_quantity > available:
            raise ValueError(
                "The agent lacks the goods required to accept."
            )

        # The initiator's current goods are checked by Unreal.
        return

    raise ValueError("Unsupported action.")


def parse_and_validate_decision(
    model_output: str | dict[str, object],
    state: AgentState,
) -> AgentDecision:
    """Parse model output and return wait if the decision is invalid.

    Validate incoming Unreal state before calling this function.
    """
    try:
        if isinstance(model_output, str):
            decision = AgentDecision.model_validate_json(model_output)
        else:
            decision = AgentDecision.model_validate(model_output)

        validate_decision(decision, state)
        return decision

    except (ValidationError, ValueError) as exc:
        logger.warning(
            "Invalid model decision for agent %s; using wait: %s",
            state.agent_id,
            exc,
        )
        return AgentDecision(
            action=WaitAction(
                reason="No valid decision was produced; waiting safely."
            )
        )