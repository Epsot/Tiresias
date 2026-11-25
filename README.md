# Tiresias
An HTTP bridge between self-hosted Ollama agents and Unreal Engine simulations.

## Prerequisites

Install the following before running Tiresias:

- Python 3.14 or newer
- [Poetry](https://python-poetry.org/docs/#installation)
- [Ollama](https://ollama.com/download)
- An Ollama model matching `ollama.model` in `config.yml`

Install the Python dependencies and download the default model and run the ollama server:

```powershell
poetry config virtualenvs.in-project true
poetry install 
```

ctrl + shift + p > Python: Select Interpreter > select the .venv that was just created.


```powershell
ollama pull llama3.2:3b
ollama run llama3.2:3b
```

### Start Ollama

Tiresias does not start Ollama itself. An Ollama server must be running at the
host and port configured under `ollama` in `config.yml`. The default is:

```yaml
ollama:
  host: 127.0.0.1
  port: 11434
  model: llama3.2:3b
```


The Ollama desktop application may already be running this server. If
`ollama serve` reports that port `11434` is already in use, check the existing
server instead of starting a second one:




### Start Tiresias

Keep Ollama running, then start the API in another terminal:

```powershell
poetry run python main.py
```

By default, the API is available at `http://127.0.0.1:8000` and Swagger UI is
available at `http://127.0.0.1:8000/docs`.

## Agent decisions

`POST /decision` accepts the current state of an agent and asks Ollama to choose
one of the available actions. The response is schema-constrained JSON:

```json
{
  "action": {
    "action": "eat",
    "amount": 1
  }
}
```

The available actions are:

- `eat`
- `look_for_wood`
- `strengthen_relationship`
- `wait` when no useful action is feasible

The temporary test input contains only `agent_id`, `health`, `hunger`, and
`goal`. Detailed inventory, location, and relationship fields are preserved as
comments in `agent_state.yml` and `decision_models.py` for future restoration.
Tiresias retries once if Ollama returns an invalid action.

The model can be overridden with the `model` query parameter:

```powershell
$state = @{
  agent_id = "agent_01"
  health = 100
  hunger = 72
  goal = "strengthen relationships"
}

$json = $state | ConvertTo-Json -Depth 10
Invoke-RestMethod -Uri "http://127.0.0.1:8000/decision" `
  -Method Post -ContentType "application/json" -Body $json
```

The full request and response schemas are available at `/docs`.
The input format is also documented in `agent_state.yml`, including field types,
constraints, descriptions, and the example request displayed by Swagger. Edit
the top-level `example` in that file to change the request shown in `/docs`.

### Decision conversation viewer

Open `http://127.0.0.1:8000/decisions` to see the requests and responses passing
through `POST /decision`. The page refreshes automatically and renders nested
JSON without depending on specific field names or payload shapes.

The most recent 100 exchanges are available as JSON from
`GET /decision-history`. This history is held in memory and is cleared whenever
the Tiresias server restarts. Failed Ollama requests are included with their HTTP
status and error response.

## Project structure

- `main.py` defines the HTTP routes and starts FastAPI.
- `decision_history.py` stores the recent in-memory decision exchanges.
- `trade_memory.py` stores validated trade responses in JSONL format.
- `settings.py` loads required configuration from the YAML files.
- `chat_models.py` defines free-form chat request and response models.
- `decision_models.py` defines agent state, available actions, and validation.
- `ollama_client.py` contains all communication with Ollama.
- `config.yml` configures the server, model, and system prompt.
- `agent_state.yml` documents the decision input and owns its Swagger example.
- `static/` contains the browser-based chat and decision conversation pages.

## Why Tiresias?

Tiresias was a prophet from Greek mythology who experienced life as both a man
and a woman.

Because he had lived through both perspectives, Zeus and Hera asked him to judge
which sex experienced greater pleasure. His answer angered Hera, who blinded
him, while Zeus granted him prophetic sight and the ability to perceive truths
hidden from others.

This project takes its name from that combination of transformation, multiple
perspectives, blindness, and insight: an AI-powered API designed to turn
questions and information into useful, interpretable answers.