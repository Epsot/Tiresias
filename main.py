import uvicorn
import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from chat_models import ChatRequest, ChatResponse
from decision_history import get_history, record_exchange
from decision_models import AgentDecision, AgentState
from ollama_client import OllamaError, complete, decide
from settings import STATIC_DIR, settings
from trade_memory import record_validated_trade_decision

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Tiresias",
    description="HTTP bridge between Unreal Engine agents and a local Ollama model.",
)


@app.get("/", include_in_schema=False)
def chat_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/decisions", include_in_schema=False)
def decisions_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "decisions.html")


@app.get("/config", tags=["Service"])
def config() -> dict[str, str | int]:
    return {
        "server_host": settings.server.host,
        "server_port": settings.server.port,
        "ollama_host": settings.ollama.url,
        "default_model": settings.ollama.model,
        "system_prompt": settings.ollama.system_prompt.strip(),
    }


@app.get("/health", tags=["Service"])
def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/decision-history", tags=["Agent decisions"])
def decision_history() -> list[dict[str, object]]:
    """Return recent decision request/response pairs, newest first."""
    return get_history()


@app.post("/chat", response_model=ChatResponse, tags=["Ollama"])
async def chat(request: ChatRequest) -> ChatResponse:
    """Send a free-form message to the configured Ollama model."""
    try:
        model, reply = await complete(request.message, request.model)
    except OllamaError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return ChatResponse(model=model, reply=reply)


@app.post("/decision", response_model=AgentDecision, tags=["Agent decisions"])
async def decision(
    state: AgentState,
    model: str | None = None,
) -> AgentDecision:
    """Choose one feasible action for an agent from its current state."""
    request_payload = state.model_dump(mode="json")
    try:
        _, result = await decide(state, model)
    except OllamaError as exc:
        record_exchange(
            request=request_payload,
            response={"detail": exc.detail},
            status_code=exc.status_code,
        )
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    try:
        record_validated_trade_decision(state, result)
    except OSError as exc:
        logger.exception("Could not save trade decision memory")
        raise HTTPException(
            status_code=500,
            detail="Could not save trade decision memory.",
        ) from exc
    record_exchange(
        request=request_payload,
        response=result.model_dump(mode="json"),
        status_code=200,
    )
    return result


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=True,
        reload_includes=["*.py", "*.yml", "*.yaml"],
    )
