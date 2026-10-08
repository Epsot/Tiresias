from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from settings import agent_state_example


class Inventory(BaseModel):
    food: int = Field(ge=0, description="Available food units.")
    wood: int = Field(ge=0, description="Available wood units.")


class KnownAgent(BaseModel):
    id: str = Field(description="Unique identifier of the known agent.")
    location: str = Field(description="Last known location of the agent.")
    relationship: float = Field(
        ge=-1,
        le=1,
        description="Relationship score from -1 (hostile) to 1 (close).",
    )


class AgentState(BaseModel):
    """Complete simulation state used to choose an action."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"example": agent_state_example},
    )

    agent_id: str = Field(description="Unique identifier of the deciding agent.")
    time: float = Field(description="Current simulation time.")
    location: str = Field(description="Current agent location.")
    health: int = Field(ge=0, le=100, description="Health from 0 to 100.")
    hunger: int = Field(ge=0, le=100, description="Hunger from 0 to 100.")
    inventory: Inventory
    known_agents: list[KnownAgent]
    nearby_objects: list[str] = Field(description="Objects or places currently nearby.")
    active_goal: str = Field(description="Current goal, or 'none'.")
    recent_events: list[str] = Field(description="Recent events relevant to the decision.")


class Action(BaseModel):
    """Base class for every action an agent can take."""

    model_config = ConfigDict(extra="forbid")

    action: str


class EatAction(Action):
    action: Literal["eat"] = "eat"
    amount: int = Field(ge=1, description="Number of food units to consume.")


class LookForWoodAction(Action):
    action: Literal["look_for_wood"] = "look_for_wood"
    location: str = Field(description="Place where the agent should search for wood.")


class StrengthenRelationshipAction(Action):
    action: Literal["strengthen_relationship"] = "strengthen_relationship"
    agent_id: str = Field(description="Known agent to interact with.")


class WaitAction(Action):
    action: Literal["wait"] = "wait"


PossibleAction = Annotated[
    EatAction | LookForWoodAction | StrengthenRelationshipAction | WaitAction,
    Field(discriminator="action"),
]


class AgentDecision(BaseModel):
    """The only output the decision endpoint permits."""

    model_config = ConfigDict(extra="forbid")

    action: PossibleAction


def build_decision_schema(state: AgentState) -> dict[str, object]:
    """Build an Ollama output schema containing only feasible actions."""
    actions: list[dict[str, object]] = []

    if state.inventory.food > 0:
        actions.append(
            _action_schema(
                "eat",
                amount={
                    "type": "integer",
                    "minimum": 1,
                    "maximum": state.inventory.food,
                },
            )
        )

    if state.nearby_objects:
        actions.append(
            _action_schema(
                "look_for_wood",
                location={"type": "string", "enum": state.nearby_objects},
            )
        )

    known_agent_ids = [agent.id for agent in state.known_agents]
    if known_agent_ids:
        actions.append(
            _action_schema(
                "strengthen_relationship",
                agent_id={"type": "string", "enum": known_agent_ids},
            )
        )

    if not actions:
        actions.append(_action_schema("wait"))

    return {
        "type": "object",
        "properties": {"action": {"oneOf": actions}},
        "required": ["action"],
        "additionalProperties": False,
    }


def _action_schema(action: str, **parameters: object) -> dict[str, object]:
    properties: dict[str, object] = {
        "action": {"type": "string", "const": action},
        **parameters,
    }
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def validate_decision(decision: AgentDecision, state: AgentState) -> None:
    """Reject an action that contradicts the state supplied by the client."""
    action = decision.action

    if isinstance(action, EatAction) and action.amount > state.inventory.food:
        raise ValueError("The eat amount exceeds the food in the inventory.")

    if isinstance(action, LookForWoodAction) and action.location not in state.nearby_objects:
        raise ValueError("The wood-search location is not nearby.")

    if isinstance(action, StrengthenRelationshipAction) and action.agent_id not in {
        agent.id for agent in state.known_agents
    }:
        raise ValueError("The relationship target is not a known agent.")
