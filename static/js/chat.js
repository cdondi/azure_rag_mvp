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

    // Validate question first
    try {
      const validationResponse = await fetch("/chat/validate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question: question }),
      });

      const validation = await validationResponse.json();
      if (!validation.valid) {
        this.addMessage({
          type: "assistant",
          content: `Sorry, there's an issue with your question: ${validation.errors.join(
            ", "
          )}`,
          sources: [],
        });
        return;
      }
    } catch (error) {
      console.error("Validation error:", error);
    }

    // Add user message
    this.addMessage({
      type: "user",
      content: question,
    });

    // Clear input and disable form
    this.questionInput.value = "";
    this.setLoading(true);

    try {
      // Call the enhanced chat API
      const response = await fetch("/chat", {
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
        const errorData = await response.json();
        throw new Error(
          errorData.detail || `HTTP error! status: ${response.status}`
        );
      }

      const data = await response.json();

      // Add assistant response with enhanced information
      this.addMessage({
        type: "assistant",
        content: data.answer,
        sources: data.sources,
        responseTime: data.response_time_ms,
      });
    } catch (error) {
      console.error("Error:", error);
      this.addMessage({
        type: "assistant",
        content: `Sorry, I encountered an error: ${error.message}. Please try again.`,
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

    // Format the content
    content.innerHTML = this.formatContent(message.content);

    // Add sources if present (now with response time)
    if (message.sources && message.sources.length > 0) {
      const sourcesElement = this.createSourcesElement(
        message.sources,
        message.responseTime
      );
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

  createSourcesElement(sources, responseTime) {
    const sourcesContainer = document.createElement("div");
    sourcesContainer.className = "sources";

    const title = document.createElement("h4");
    title.textContent = `Sources (${sources.length})`;

    // Add response time if available
    if (responseTime) {
      const timeSpan = document.createElement("span");
      timeSpan.style.fontSize = "12px";
      timeSpan.style.color = "#6b7280";
      timeSpan.style.fontWeight = "normal";
      timeSpan.textContent = ` • Generated in ${responseTime}ms`;
      title.appendChild(timeSpan);
    }
    title.textContent += ":";

    sourcesContainer.appendChild(title);

    sources.forEach((source, index) => {
      const sourceItem = document.createElement("div");
      sourceItem.className = "source-item";

      // Create header with citation number and relevance
      const sourceHeader = document.createElement("div");
      sourceHeader.className = "source-header";

      // Left side: citation number and source name
      const leftSide = document.createElement("div");
      leftSide.style.display = "flex";
      leftSide.style.alignItems = "center";

      const citationNum = document.createElement("span");
      citationNum.className = "citation-number";
      citationNum.textContent = index + 1;

      const sourceText = document.createElement("span");
      sourceText.textContent = `${source.source_file} (chunk ${source.chunk_index})`;

      leftSide.appendChild(citationNum);
      leftSide.appendChild(sourceText);

      // Right side: relevance badge
      const relevanceBadge = document.createElement("span");
      const relevance =
        source.relevance ||
        (index === 0 ? "high" : index === 1 ? "medium" : "low");
      relevanceBadge.className = `source-relevance relevance-${relevance}`;
      relevanceBadge.textContent = relevance;

      sourceHeader.appendChild(leftSide);
      sourceHeader.appendChild(relevanceBadge);

      // Add preview text
      const preview = document.createElement("div");
      preview.className = "source-preview";
      preview.textContent = source.preview || "No preview available";

      // Add expandable details
      const details = document.createElement("div");
      details.className = "source-details";
      details.innerHTML = `
            <strong>📄 Chunk:</strong> ${source.chunk_index} | 
            <strong>📊 Relevance:</strong> ${relevance.toUpperCase()} | 
            <strong>📍 File:</strong> ${source.source_file}.py<br>
            <em>Click to collapse details</em>
        `;

      // Click handler for expansion
      sourceItem.addEventListener("click", () => {
        const isExpanded = details.classList.contains("expanded");
        if (isExpanded) {
          details.classList.remove("expanded");
          sourceItem.style.backgroundColor = "white";
        } else {
          details.classList.add("expanded");
          sourceItem.style.backgroundColor = "#f8fafc";
        }
      });

      sourceItem.appendChild(sourceHeader);
      sourceItem.appendChild(preview);
      sourceItem.appendChild(details);

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
