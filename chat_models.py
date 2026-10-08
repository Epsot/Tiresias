from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Free-form chat request sent to Ollama."""

    message: str = Field(examples=["Say hello in one sentence."])
    model: str | None = Field(
        default=None,
        examples=["llama3.2:3b"],
        description="Optional model override. The configured model is used when omitted.",
    )


class ChatResponse(BaseModel):
    """Free-form response returned by Ollama."""

    model: str
    reply: str
