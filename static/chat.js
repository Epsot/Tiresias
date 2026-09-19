const form = document.getElementById("chat-form");
const reply = document.getElementById("reply");
const send = document.getElementById("send");
const modelInput = document.getElementById("model");
const hostLabel = document.getElementById("ollama-host");
const systemPrompt = document.getElementById("system-prompt");

async function loadConfig() {
  const response = await fetch("/config");
  if (!response.ok) {
    return;
  }
  const config = await response.json();
  if (config.ollama_host) {
    hostLabel.textContent = config.ollama_host;
  }
  if (config.default_model) {
    modelInput.value = config.default_model;
  }
  if (config.system_prompt) {
    systemPrompt.value = config.system_prompt;
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  reply.className = "";
  reply.textContent = "Waiting for Ollama...";
  send.disabled = true;

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: document.getElementById("message").value,
        model: modelInput.value || null,
      }),
    });
    const data = await response.json();
    if (!response.ok) {
      reply.className = "error";
      reply.textContent = data.detail || JSON.stringify(data, null, 2);
      return;
    }
    reply.textContent = data.reply;
  } catch (error) {
    reply.className = "error";
    reply.textContent = String(error);
  } finally {
    send.disabled = false;
  }
});

loadConfig();
