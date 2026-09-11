const form = document.querySelector("#chat-form");
const input = document.querySelector("#message-input");
const messages = document.querySelector("#messages");
const sendButton = document.querySelector("#send-button");
const errorMessage = document.querySelector("#error-message");

const conversationId = crypto.randomUUID();

function addMessage(text, sender) {
  const message = document.createElement("div");
  message.className = `message ${sender}-message`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.setAttribute("aria-hidden", "true");
  avatar.textContent = sender === "user" ? "Y" : "M";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;

  message.append(avatar, bubble);
  messages.append(message);
  messages.scrollTop = messages.scrollHeight;
}

function setLoading(isLoading) {
  sendButton.disabled = isLoading;
  input.disabled = isLoading;
  sendButton.querySelector("span").textContent = isLoading ? "..." : "↑";
}

async function sendMessage(message) {
  const response = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ conversation_id: conversationId, message }),
  });

  if (!response.ok) {
    throw new Error("The receptionist is unavailable right now.");
  }

  return response.json();
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message || sendButton.disabled) return;

  errorMessage.textContent = "";
  addMessage(message, "user");
  input.value = "";
  input.style.height = "auto";
  setLoading(true);

  try {
    const result = await sendMessage(message);
    addMessage(result.response, "agent");
  } catch (error) {
    errorMessage.textContent = error.message;
  } finally {
    setLoading(false);
    input.focus();
  }
});

input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 130)}px`;
});

input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
});
