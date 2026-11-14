const historyElement = document.getElementById("history");
const emptyState = document.getElementById("empty-state");
const connectionDot = document.getElementById("connection-dot");
const connectionLabel = document.getElementById("connection-label");

let loading = false;
let renderedSignature = null;

function renderPrimitive(value) {
  const element = document.createElement("span");
  element.className = `json-value json-${value === null ? "null" : typeof value}`;
  element.textContent = value === null ? "null" : JSON.stringify(value);
  return element;
}

function renderJson(value) {
  if (value === null || typeof value !== "object") {
    return renderPrimitive(value);
  }

  const entries = Array.isArray(value)
    ? value.map((item, index) => [index, item])
    : Object.entries(value);
  const container = document.createElement("div");
  container.className = Array.isArray(value) ? "json-array" : "json-object";

  if (entries.length === 0) {
    container.classList.add("json-empty");
    container.textContent = Array.isArray(value) ? "[ ]" : "{ }";
    return container;
  }

  for (const [key, childValue] of entries) {
    const row = document.createElement("div");
    row.className = "json-row";

    const keyElement = document.createElement("span");
    keyElement.className = "json-key";
    keyElement.textContent = Array.isArray(value) ? `[${key}]` : key;

    const child = document.createElement("div");
    child.className = "json-child";
    child.append(renderJson(childValue));

    row.append(keyElement, child);
    container.append(row);
  }

  return container;
}

function renderMessage(label, payload, direction) {
  const message = document.createElement("section");
  message.className = `message message-${direction}`;

  const heading = document.createElement("h3");
  heading.textContent = label;

  const payloadElement = document.createElement("div");
  payloadElement.className = "payload";
  payloadElement.append(renderJson(payload));

  message.append(heading, payloadElement);
  return message;
}

function renderExchange(entry) {
  const exchange = document.createElement("article");
  const successful = entry.status_code >= 200 && entry.status_code < 300;
  exchange.className = `exchange ${successful ? "exchange-success" : "exchange-error"}`;

  const header = document.createElement("header");
  header.className = "exchange-header";

  const title = document.createElement("h2");
  title.textContent = `Exchange #${entry.id}`;

  const metadata = document.createElement("div");
  metadata.className = "exchange-meta";

  const time = document.createElement("time");
  const timestamp = new Date(entry.timestamp);
  time.dateTime = entry.timestamp;
  time.textContent = Number.isNaN(timestamp.getTime())
    ? entry.timestamp
    : timestamp.toLocaleString();

  const status = document.createElement("span");
  status.className = `status ${successful ? "status-success" : "status-error"}`;
  status.textContent = String(entry.status_code);

  metadata.append(time, status);
  header.append(title, metadata);

  const messages = document.createElement("div");
  messages.className = "messages";
  messages.append(
    renderMessage("Request", entry.request, "request"),
    renderMessage("Response", entry.response, "response"),
  );

  exchange.append(header, messages);
  return exchange;
}

function showConnection(connected) {
  connectionDot.classList.toggle("offline", !connected);
  connectionLabel.textContent = connected ? "Live" : "Connection lost";
}

function showLoadError(error) {
  renderedSignature = null;
  historyElement.replaceChildren();
  const card = document.createElement("div");
  card.className = "state-card state-error";
  const heading = document.createElement("h2");
  heading.textContent = "Could not load conversations";
  const message = document.createElement("p");
  message.textContent = error instanceof Error ? error.message : String(error);
  card.append(heading, message);
  historyElement.append(card);
}

async function loadHistory() {
  if (loading) {
    return;
  }
  loading = true;

  try {
    const response = await fetch("/decision-history", { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`History endpoint returned ${response.status}`);
    }

    const entries = await response.json();
    if (!Array.isArray(entries)) {
      throw new Error("History endpoint returned an unexpected response");
    }

    showConnection(true);
    const signature = entries.map((entry) => `${entry.id}:${entry.status_code}`).join(",");
    if (signature === renderedSignature) {
      return;
    }
    renderedSignature = signature;
    historyElement.replaceChildren();

    if (entries.length === 0) {
      historyElement.append(emptyState.content.cloneNode(true));
    } else {
      const fragment = document.createDocumentFragment();
      entries.forEach((entry) => fragment.append(renderExchange(entry)));
      historyElement.append(fragment);
    }
  } catch (error) {
    showConnection(false);
    if (!historyElement.querySelector(".exchange")) {
      showLoadError(error);
    }
  } finally {
    historyElement.setAttribute("aria-busy", "false");
    loading = false;
  }
}

loadHistory();
window.setInterval(loadHistory, 2000);
