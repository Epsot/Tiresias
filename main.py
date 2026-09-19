import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ollama_client import OllamaError, complete
from schemas import ChatRequest, ChatResponse
from settings import STATIC_DIR, settings

app = FastAPI(title="Tiresias", description="HTTP bridge to a local Ollama model.")


@app.get("/")
def chat_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/config")
def config() -> dict[str, str | int]:
    return {
        "server_host": settings.server.host,
        "server_port": settings.server.port,
        "ollama_host": settings.ollama.url,
        "default_model": settings.ollama.model,
        "system_prompt": settings.ollama.system_prompt.strip(),
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        model, reply = await complete(request.message, request.model)
    except OllamaError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return ChatResponse(model=model, reply=reply)


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=True,
        reload_includes=["*.py", "*.yml", "*.yaml"],
    )
