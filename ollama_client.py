import httpx

from decision_models import (
    AgentDecision,
    AgentState,
    build_decision_schema,
    validate_decision,
)
from settings import settings

REQUEST_TIMEOUT = httpx.Timeout(120.0, connect=5.0)
MAX_DECISION_ATTEMPTS = 2


class OllamaError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def build_messages(user_text: str) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    prompt = settings.ollama.system_prompt.strip()
    if prompt:
        messages.append({"role": "system", "content": prompt})
    messages.append({"role": "user", "content": user_text})
    return messages


async def resolve_model(client: httpx.AsyncClient, requested: str | None) -> str:
    if requested:
        return requested
    if settings.ollama.model:
        return settings.ollama.model

    tags = await client.get(f"{settings.ollama.url}/api/tags")
    tags.raise_for_status()
    models = tags.json().get("models") or []
    if not models:
        raise OllamaError(503, "No Ollama models found. Set ollama.model in config.yml.")
    return models[0]["name"]


async def request_chat(
    user_text: str,
    model: str | None = None,
    response_format: dict[str, object] | None = None,
    options: dict[str, object] | None = None,
) -> tuple[str, str]:
    """Send a chat request and return the selected model and response content."""
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            chosen = await resolve_model(client, model)
            body: dict[str, object] = {
                "model": chosen,
                "messages": build_messages(user_text),
                "stream": False,
            }
            if response_format:
                body["format"] = response_format
            if options:
                body["options"] = options
            response = await client.post(
                f"{settings.ollama.url}/api/chat",
                json=body,
            )
    except httpx.ConnectError as exc:
        raise OllamaError(
            503,
            f"Could not reach Ollama at {settings.ollama.url}. Is `ollama serve` running?",
        ) from exc
    except httpx.HTTPError as exc:
        raise OllamaError(502, f"Ollama request failed: {exc}") from exc

    if response.status_code >= 400:
        raise OllamaError(502, f"Ollama returned {response.status_code}: {response.text}")

    payload = response.json()
    reply = (payload.get("message") or {}).get("content")
    if not reply:
        raise OllamaError(502, f"Unexpected Ollama response: {payload}")

    return payload.get("model", chosen), reply


async def complete(user_text: str, model: str | None = None) -> tuple[str, str]:
    """Send one free-form user message to Ollama."""
    return await request_chat(user_text, model)


async def decide(state: AgentState, model: str | None = None) -> tuple[str, AgentDecision]:
    """Ask Ollama to choose an action for the supplied agent state."""
    decision_schema = build_decision_schema(state)
    prompt = (
        "Choose the best action for this agent from the actions allowed by the provided "
        "JSON schema. Return only valid JSON. Use wait if no useful action is feasible.\n\n"
        f"Agent state:\n{state.model_dump_json(indent=2)}"
    )

    last_error: ValueError | None = None
    for _ in range(MAX_DECISION_ATTEMPTS):
        chosen, content = await request_chat(
            prompt,
            model,
            response_format=decision_schema,
            options={"temperature": 0.5},
        )
        try:
            decision = AgentDecision.model_validate_json(content)
            validate_decision(decision, state)
            return chosen, decision
        except ValueError as exc:
            last_error = exc
            prompt += (
                "\n\nYour previous response was invalid. Correct it using only the allowed "
                f"schema values. Validation error: {exc}"
            )

    raise OllamaError(
        502,
        f"Ollama failed to return a valid feasible decision after "
        f"{MAX_DECISION_ATTEMPTS} attempts: {last_error}",
    )
