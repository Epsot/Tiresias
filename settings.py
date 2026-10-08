from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
CONFIG_PATH = ROOT / "config.yml"
AGENT_STATE_SCHEMA_PATH = ROOT / "agent_state.yml"


class ServerConfig(BaseModel):
    host: str
    port: int


class OllamaConfig(BaseModel):
    host: str
    port: int
    model: str
    system_prompt: str

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


class Settings(BaseModel):
    server: ServerConfig
    ollama: OllamaConfig


def read_yaml(path: Path) -> dict[str, Any]:
    """Read a YAML mapping or fail with a useful startup error."""
    if not path.exists():
        raise FileNotFoundError(f"Required configuration file not found: {path}")

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected a YAML mapping in {path}")
    return data


settings = Settings.model_validate(read_yaml(CONFIG_PATH))
agent_state_example = read_yaml(AGENT_STATE_SCHEMA_PATH)["example"]
