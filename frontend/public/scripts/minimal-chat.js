/**
 * Minimal Vanilla JS Chat with Real Streaming Support
 * No frameworks, no bullshit, just works.
 */

class MinimalChat {
  constructor(rootElement) {
    this.root = rootElement;
    this.messages = [];
    this.conversationId = null;
    this.isStreaming = false;
    this.init();
  }

  init() {
    this.root.innerHTML = `
      <div class="minimal-chat">
        <div class="messages-container" id="messages"></div>
        <div class="input-container">
          <div class="input-wrapper">
            <textarea
              id="chat-input"
              placeholder="Type your message..."
              rows="1"
            ></textarea>
            <button id="send-btn" class="send-btn">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </button>
          </div>
          <div class="model-selector">
            <select id="model-select" class="model-select">
              <option value="gpt-4o">GPT-4O</option>
              <option value="gpt-4o-mini">GPT-4O Mini</option>
              <option value="claude-sonnet-4-5-20250929">Claude Sonnet 4.5</option>
              <option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet</option>
            </select>
          </div>
        </div>
      </div>
    `;

    this.messagesEl = document.getElementById('messages');
    this.inputEl = document.getElementById('chat-input');
    this.sendBtn = document.getElementById('send-btn');
    this.modelSelect = document.getElementById('model-select');

    // Load saved model
    const savedModel = localStorage.getItem('tm_model') || 'gpt-4o';
    this.modelSelect.value = savedModel;

    // Event listeners
    this.sendBtn.addEventListener('click', () => this.sendMessage());
    this.inputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.sendMessage();
      }
    });
    this.modelSelect.addEventListener('change', (e) => {
      localStorage.setItem('tm_model', e.target.value);
    });

    // Auto-resize textarea
    this.inputEl.addEventListener('input', () => {
      this.inputEl.style.height = 'auto';
      this.inputEl.style.height = Math.min(this.inputEl.scrollHeight, 200) + 'px';
    });
  }

  async sendMessage() {
    const text = this.inputEl.value.trim();
    if (!text || this.isStreaming) return;

    const model = this.modelSelect.value;

    // Add user message
    this.addMessage('user', text);
    this.inputEl.value = '';
    this.inputEl.style.height = 'auto';

    // Start streaming
    this.isStreaming = true;
    this.sendBtn.disabled = true;

    try {
      await this.streamResponse(text, model);
    } catch (error) {
      console.error('Streaming error:', error);
      this.addMessage('error', `Error: ${error.message}`);
    } finally {
      this.isStreaming = false;
      this.sendBtn.disabled = false;
    }
  }

  async streamResponse(message, model) {
    const token = window?.supabase?.getAccessToken?.() ?? null;
    if (!token) {
      throw new Error('Not authenticated');
    }

    // Create assistant message placeholder
    const assistantMsgEl = this.createMessageElement('assistant');
    const progressEl = assistantMsgEl.querySelector('.message-progress');
    const contentEl = assistantMsgEl.querySelector('.message-content');
    this.messagesEl.appendChild(assistantMsgEl);
    this.scrollToBottom();

    const response = await fetch('http://localhost:8000/api/v2/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({
        message,
        conversation_id: this.conversationId,
        model,
        temperature: 0.7,
        include_memory: true
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let content = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const event = JSON.parse(line.slice(6));

            if (event.type === 'start') {
              this.conversationId = event.conversation_id;
            }
            else if (event.type === 'thought') {
              // Show progress in real-time!
              progressEl.textContent = event.content;
              progressEl.style.display = 'block';
              this.scrollToBottom();
            }
            else if (event.type === 'tool_call') {
              progressEl.textContent = `🔧 Using tool: ${event.tool}`;
              this.scrollToBottom();
            }
            else if (event.type === 'content') {
              // Hide progress when content starts
              progressEl.style.display = 'none';

              // Stream content word by word
              content += event.delta;
              contentEl.textContent = content;
              this.scrollToBottom();
            }
            else if (event.type === 'done') {
              // Final content with markdown rendering
              progressEl.style.display = 'none';
              const finalContent = event.assistant_message?.content || content;
              contentEl.innerHTML = this.renderMarkdown(finalContent);

              // Show sources popup if available
              if (event.sources && event.sources.length > 0) {
                const sourcesEl = this.createSourcesPopup(event.sources);
                assistantMsgEl.appendChild(sourcesEl);
              }

              // Show metadata
              if (event.tools_used && event.tools_used.length > 0) {
                const metaEl = document.createElement('div');
                metaEl.className = 'message-meta';
                metaEl.textContent = `🔧 Tools: ${event.tools_used.join(', ')}`;
                assistantMsgEl.appendChild(metaEl);
              }

              this.scrollToBottom();
            }
            else if (event.type === 'error') {
              progressEl.style.display = 'none';
              contentEl.textContent = `Error: ${event.error}`;
              contentEl.style.color = '#ff4444';
            }
          } catch (e) {
            console.error('Parse error:', e, line);
          }
        }
      }
    }
  }

  addMessage(role, text) {
    const msgEl = this.createMessageElement(role, text);
    this.messagesEl.appendChild(msgEl);
    this.scrollToBottom();
  }

  createMessageElement(role, text = '') {
    const div = document.createElement('div');
    div.className = `message message-${role}`;

    if (role === 'assistant' && !text) {
      // Streaming message with progress indicator
      div.innerHTML = `
        <div class="message-progress" style="display: block; font-style: italic; color: #666; margin-bottom: 8px;">
          Starting...
        </div>
        <div class="message-content"></div>
      `;
    } else {
      // Complete message with markdown rendering
      const content = role === 'assistant' ? this.renderMarkdown(text) : this.escapeHtml(text);
      div.innerHTML = `<div class="message-content">${content}</div>`;
    }

    return div;
  }

  renderMarkdown(text) {
    if (!text) return '';

    let html = text;

    // Code blocks (```)
    html = html.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
      const escaped = this.escapeHtml(code.trim());
      return `<pre><code>${escaped}</code></pre>`;
    });

    // Inline code (`)
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Headers
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

    // Bold
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/__(.+?)__/g, '<strong>$1</strong>');

    // Italic
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    html = html.replace(/_(.+?)_/g, '<em>$1</em>');

    // Links
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');

    // Unordered lists
    html = html.replace(/^\* (.+)$/gm, '<li>$1</li>');
    html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');

    // Ordered lists
    html = html.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');

    // Paragraphs
    html = html.split('\n\n').map(para => {
      para = para.trim();
      if (!para) return '';
      if (para.startsWith('<')) return para; // Already HTML
      return `<p>${para.replace(/\n/g, '<br>')}</p>`;
    }).join('\n');

    return html;
  }

  createSourcesPopup(sources) {
    const wrapper = document.createElement('div');
    wrapper.className = 'sources-toggle-wrap';

    // Create button with favicons
    const button = document.createElement('button');
    button.className = 'sources-toggle';
    button.type = 'button';
    button.setAttribute('aria-expanded', 'false');

    const faviconStack = document.createElement('span');
    faviconStack.className = 'favicon-stack';

    sources.slice(0, 3).forEach(source => {
      const url = source.url || source.link;
      if (url) {
        try {
          const domain = new URL(url).hostname;
          const img = document.createElement('img');
          img.src = `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
          img.width = 16;
          img.height = 16;
          img.loading = 'lazy';
          img.onerror = () => { img.style.display = 'none'; };
          faviconStack.appendChild(img);
        } catch (e) {}
      }
    });

    const label = document.createElement('span');
    label.textContent = 'Sources';

    button.appendChild(faviconStack);
    button.appendChild(label);

    // Create popover
    const popover = document.createElement('div');
    popover.className = 'sources-popover';
    popover.role = 'dialog';
    popover.setAttribute('aria-label', 'Citations');
    popover.style.display = 'none';

    const list = document.createElement('ul');
    list.className = 'sources-list';

    sources.slice(0, 10).forEach((source, index) => {
      const url = source.url || source.link;
      const title = source.title || source.name || (url ? new URL(url).hostname : `Source ${index + 1}`);

      const li = document.createElement('li');

      if (url) {
        const link = document.createElement('a');
        link.href = url;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.textContent = title;
        li.appendChild(link);

        const meta = document.createElement('div');
        meta.className = 'source-meta';

        try {
          const domain = new URL(url).hostname;
          const favicon = document.createElement('img');
          favicon.src = `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
          favicon.width = 16;
          favicon.height = 16;
          favicon.onerror = () => { favicon.style.display = 'none'; };
          meta.appendChild(favicon);

          const host = document.createElement('span');
          host.className = 'source-host';
          host.textContent = domain.replace(/^www\./, '');
          meta.appendChild(host);
        } catch (e) {}

        li.appendChild(meta);

        if (source.snippet) {
          const snippet = document.createElement('p');
          snippet.className = 'source-snippet';
          snippet.textContent = source.snippet;
          li.appendChild(snippet);
        }
      } else {
        const span = document.createElement('span');
        span.className = 'source-title';
        span.textContent = title;
        li.appendChild(span);
      }

      list.appendChild(li);
    });

    popover.appendChild(list);

    // Toggle functionality
    button.addEventListener('click', () => {
      const isOpen = popover.style.display !== 'none';
      if (isOpen) {
        popover.style.display = 'none';
        button.setAttribute('aria-expanded', 'false');
      } else {
        // Position popover
        if (!popover.parentElement || popover.parentElement.tagName !== 'BODY') {
          document.body.appendChild(popover);
        }

        popover.style.position = 'fixed';
        popover.style.display = 'block';

        const rect = button.getBoundingClientRect();
        const spacing = 8;
        let left = rect.left;
        let top = rect.top - popover.offsetHeight - spacing;

        if (top < 8) top = rect.bottom + spacing;

        const vw = window.innerWidth;
        const maxLeft = vw - popover.offsetWidth - 8;
        if (left > maxLeft) left = Math.max(8, maxLeft);
        if (left < 8) left = 8;

        popover.style.left = `${left}px`;
        popover.style.top = `${top}px`;

        button.setAttribute('aria-expanded', 'true');

        // Close on outside click
        setTimeout(() => {
          document.addEventListener('mousedown', function closePopover(e) {
            if (!popover.contains(e.target) && !button.contains(e.target)) {
              popover.style.display = 'none';
              button.setAttribute('aria-expanded', 'false');
              document.removeEventListener('mousedown', closePopover);
            }
          });
        }, 0);
      }
    });

    wrapper.appendChild(button);
    wrapper.appendChild(popover);

    return wrapper;
  }

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  scrollToBottom() {
    requestAnimationFrame(() => {
      this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
    });
  }

  newChat() {
    this.conversationId = null;
    this.messages = [];
    this.messagesEl.innerHTML = '';
  }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    const root = document.getElementById('react-chat-root');
    if (root) {
      window.minimalChat = new MinimalChat(root);
    }
  });
} else {
  const root = document.getElementById('react-chat-root');
  if (root) {
    window.minimalChat = new MinimalChat(root);
  }
}
