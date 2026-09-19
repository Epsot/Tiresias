from pathlib import Path

import yaml
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
CONFIG_PATH = ROOT / "config.yml"


class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000


class OllamaConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 11434
    model: str = "llama3.2:3b"
    system_prompt: str = ""

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


class Settings(BaseModel):
    server: ServerConfig = ServerConfig()
    ollama: OllamaConfig = OllamaConfig()


def load_settings() -> Settings:
    if not CONFIG_PATH.exists():
        return Settings()
    raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    return Settings.model_validate(raw or {})


settings = load_settings()
