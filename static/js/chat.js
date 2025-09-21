class ChatInterface {
  // ChatInterface class manages all chat functionality
  // Handles form submission and API calls
  // Formats responses with code block support
  // Shows loading states during API calls
  // Automatically scrolls to new messages
  // Displays source citations
  constructor() {
    this.messagesContainer = document.getElementById("messages");
    this.chatForm = document.getElementById("chat-form");
    this.questionInput = document.getElementById("question-input");
    this.sendButton = document.getElementById("send-button");
    this.loadingIndicator = document.getElementById("loading");

    this.initializeEventListeners();
    this.addWelcomeMessage();
  }

  initializeEventListeners() {
    this.chatForm.addEventListener("submit", (e) => {
      e.preventDefault();
      this.handleSubmit();
    });
  }

  addWelcomeMessage() {
    const welcomeMessage = {
      type: "assistant",
      content:
        "Hello! I'm your Python documentation assistant. Ask me anything about Python programming, and I'll help you find answers from the official documentation.",
      sources: [],
    };
    this.addMessage(welcomeMessage);
  }

  async handleSubmit() {
    const question = this.questionInput.value.trim();
    if (!question) return;

    // Add user message
    this.addMessage({
      type: "user",
      content: question,
    });

    // Clear input and disable form
    this.questionInput.value = "";
    this.setLoading(true);

    try {
      // Call the API
      const response = await fetch("/ask", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: question,
          max_results: 3,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      // Add assistant response
      this.addMessage({
        type: "assistant",
        content: data.answer,
        sources: data.sources,
      });
    } catch (error) {
      console.error("Error:", error);
      this.addMessage({
        type: "assistant",
        content:
          "Sorry, I encountered an error while processing your question. Please try again.",
        sources: [],
      });
    } finally {
      this.setLoading(false);
    }
  }

  addMessage(message) {
    const messageElement = document.createElement("div");
    messageElement.className = `message ${message.type}`;

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.textContent = message.type === "user" ? "U" : "AI";

    const content = document.createElement("div");
    content.className = "message-content";

    // Format the content (handle code blocks, etc.)
    content.innerHTML = this.formatContent(message.content);

    // Add sources if present
    if (message.sources && message.sources.length > 0) {
      const sourcesElement = this.createSourcesElement(message.sources);
      content.appendChild(sourcesElement);
    }

    messageElement.appendChild(avatar);
    messageElement.appendChild(content);

    this.messagesContainer.appendChild(messageElement);
    this.scrollToBottom();
  }

  formatContent(content) {
    // Basic formatting for code blocks and inline code
    return content
      .replace(/```python\n([\s\S]*?)\n```/g, "<pre><code>$1</code></pre>")
      .replace(/```([\s\S]*?)```/g, "<pre><code>$1</code></pre>")
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\n/g, "<br>");
  }

  createSourcesElement(sources) {
    const sourcesContainer = document.createElement("div");
    sourcesContainer.className = "sources";

    const title = document.createElement("h4");
    title.textContent = `Sources (${sources.length}):`;
    sourcesContainer.appendChild(title);

    sources.forEach((source) => {
      const sourceItem = document.createElement("div");
      sourceItem.className = "source-item";
      sourceItem.textContent = `${source.source_file} (chunk ${source.chunk_index})`;
      sourcesContainer.appendChild(sourceItem);
    });

    return sourcesContainer;
  }

  setLoading(isLoading) {
    if (isLoading) {
      this.sendButton.disabled = true;
      this.sendButton.textContent = "Sending...";
      this.loadingIndicator.classList.remove("hidden");
    } else {
      this.sendButton.disabled = false;
      this.sendButton.textContent = "Send";
      this.loadingIndicator.classList.add("hidden");
      this.questionInput.focus();
    }
  }

  scrollToBottom() {
    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
  }
}

// Initialize the chat interface when the page loads
document.addEventListener("DOMContentLoaded", () => {
  new ChatInterface();
});
