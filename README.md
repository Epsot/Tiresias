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
poetry install
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

- `eat` with an `amount`
- `look_for_wood` with a `location`
- `strengthen_relationship` with a known `agent_id`
- `wait` when no useful action is feasible

For every request, Tiresias builds an output schema from the current state:
food amounts cannot exceed the inventory, locations must be nearby, and
relationship targets must be known agents. Decision generation uses temperature
zero and retries once if Ollama still returns an invalid action.

The model can be overridden with the `model` query parameter:

```powershell
$state = @{
  agent_id = "agent_01"
  time = 142.5
  location = "village_north"
  health = 100
  hunger = 72
  inventory = @{ food = 1; wood = 4 }
  known_agents = @(
    @{ id = "agent_02"; location = "market"; relationship = 0.4 }
  )
  nearby_objects = @("market", "forest", "well")
  active_goal = "none"
  recent_events = @("Agent encountered agent_02", "Food supply decreased")
}

$json = $state | ConvertTo-Json -Depth 10
Invoke-RestMethod -Uri "http://127.0.0.1:8000/decision" `
  -Method Post -ContentType "application/json" -Body $json
```

The full request and response schemas are available at `/docs`.
The input format is also documented in `agent_state.yml`, including field types,
constraints, descriptions, and the example request displayed by Swagger. Edit
the top-level `example` in that file to change the request shown in `/docs`.

## Project structure

- `main.py` defines the HTTP routes and starts FastAPI.
- `settings.py` loads required configuration from the YAML files.
- `chat_models.py` defines free-form chat request and response models.
- `decision_models.py` defines agent state, available actions, and validation.
- `ollama_client.py` contains all communication with Ollama.
- `config.yml` configures the server, model, and system prompt.
- `agent_state.yml` documents the decision input and owns its Swagger example.
- `static/` contains the browser-based chat test page.

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