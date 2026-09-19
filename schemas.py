from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., examples=["Say hello in one sentence."])
    model: str | None = Field(default=None, examples=["llama3.2:3b"])


class ChatResponse(BaseModel):
    model: str
    reply: str
