import httpx

from settings import settings


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


async def complete(user_text: str, model: str | None = None) -> tuple[str, str]:
    """Send one user message to Ollama. Returns (model_name, reply)."""
    timeout = httpx.Timeout(120.0, connect=5.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            chosen = await resolve_model(client, model)
            response = await client.post(
                f"{settings.ollama.url}/api/chat",
                json={"model": chosen, "messages": build_messages(user_text), "stream": False},
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
