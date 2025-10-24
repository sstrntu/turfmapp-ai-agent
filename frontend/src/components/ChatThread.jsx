import React from "react";
import {
  useThread,
  useThreadComposer,
  useThreadRuntime,
} from "@assistant-ui/react";
import { MessageBubble } from "./MessageBubble.jsx";
import { TypingIndicator } from "./TypingIndicator.jsx";

const clampTextareaHeight = (textarea) => {
  const maxHeight = 240;
  textarea.style.height = "auto";
  textarea.style.height = `${Math.min(textarea.scrollHeight + 2, maxHeight)}px`;
};

const preventShiftEnter = (event) => {
  if (event.key === "Enter" && event.shiftKey) {
    return;
  }

  if (event.key === "Enter") {
    event.preventDefault();
  }
};

export const ChatThread = () => {
  const messages = useThread((state) => state.messages);
  const isRunning = useThread((state) => state.isRunning);
  const suggestions = useThread((state) => state.suggestions);
  const runtime = useThreadRuntime();
  const composerText = useThreadComposer((state) => state.text);
  const composerIsEmpty = useThreadComposer((state) => state.isEmpty);

  const listRef = React.useRef(null);
  const textareaRef = React.useRef(null);
  const fileInputRef = React.useRef(null);
  const [attachments, setAttachments] = React.useState([]);
  const [selectedModel, setSelectedModel] = React.useState(() => {
    return localStorage.getItem('tm_model') || 'gpt-4o';
  });

  // Available models (must match backend MODEL_REGISTRY)
  const models = [
    { id: 'gpt-4o', name: 'GPT-4O', provider: 'OpenAI' },
    { id: 'gpt-4o-mini', name: 'GPT-4O Mini', provider: 'OpenAI' },
    { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', provider: 'OpenAI' },
    { id: 'claude-sonnet-4-5-20250929', name: 'Claude Sonnet 4.5', provider: 'Anthropic' },
    { id: 'claude-3-5-sonnet-20241022', name: 'Claude 3.5 Sonnet', provider: 'Anthropic' },
    { id: 'claude-3-haiku-20240307', name: 'Claude 3 Haiku', provider: 'Anthropic' },
  ];

  React.useEffect(() => {
    const node = listRef.current;
    if (!node) return;
    node.scrollTop = node.scrollHeight;
  }, [messages.length, isRunning]);

  React.useEffect(() => {
    if (textareaRef.current) {
      clampTextareaHeight(textareaRef.current);
    }
  }, [composerText]);

  const handleInputChange = (event) => {
    runtime.composer.setText(event.target.value);
    clampTextareaHeight(event.target);
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    if (composerIsEmpty) {
      return;
    }

    // Store model selection globally so adapter can access it
    window.selectedModel = selectedModel;
    console.log('🔍 Frontend: Selected model for this request:', selectedModel);

    // Store attachments globally so adapter can access them
    if (attachments.length > 0) {
      window.pendingAttachments = attachments.map(att => ({
        url: att.url,
        type: att.type,
        name: att.file.name
      }));
    }

    runtime.composer.send();

    // Clear attachments after sending
    setAttachments([]);
    delete window.pendingAttachments;
  };

  const handleModelChange = async (event) => {
    const newModel = event.target.value;
    setSelectedModel(newModel);
    localStorage.setItem('tm_model', newModel);
    console.log('🔍 Frontend: Model changed to:', newModel);

    // Also save to database
    try {
      const token = window?.supabase?.getAccessToken?.();
      if (token) {
        await fetch('/api/v1/settings/preferences', {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ default_model: newModel })
        });
        console.log('✅ Model preference saved to database');
      }
    } catch (error) {
      console.error('Failed to save model preference:', error);
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      preventShiftEnter(event);
      if (!composerIsEmpty) {
        // Store model selection globally so adapter can access it
        window.selectedModel = selectedModel;
        console.log('🔍 Frontend (Enter key): Selected model for this request:', selectedModel);

        // Store attachments globally so adapter can access them
        if (attachments.length > 0) {
          window.pendingAttachments = attachments.map(att => ({
            url: att.url,
            type: att.type,
            name: att.file.name
          }));
        }

        runtime.composer.send();

        // Clear attachments after sending
        setAttachments([]);
        delete window.pendingAttachments;
      }
    }
  };

  const handleSuggestion = (suggestion) => {
    // Store model selection globally so adapter can access it
    window.selectedModel = selectedModel;
    console.log('🔍 Frontend (Suggestion): Selected model for this request:', selectedModel);

    runtime.composer.setText(suggestion.text);
    runtime.composer.send();
  };

  const getFileType = (filename) => {
    const ext = filename.split('.').pop().toLowerCase();
    if (['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg'].includes(ext)) return 'image';
    if (['mp4', 'webm', 'ogg', 'mov'].includes(ext)) return 'video';
    if (['mp3', 'wav', 'ogg', 'm4a'].includes(ext)) return 'audio';
    if (['pdf'].includes(ext)) return 'pdf';
    if (['doc', 'docx', 'txt', 'rtf'].includes(ext)) return 'document';
    if (['csv', 'xls', 'xlsx'].includes(ext)) return 'data';
    return 'file';
  };

  const getFileEmoji = (type) => {
    const emojiMap = {
      image: '🖼️',
      video: '🎥',
      audio: '🎵',
      pdf: '📄',
      document: '📝',
      data: '📊',
      file: '📎'
    };
    return emojiMap[type] || '📎';
  };

  const uploadFile = async (file) => {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('/api/uploads/', {
        method: 'POST',
        body: formData
      });
      return await response.json();
    } catch (error) {
      console.error('Upload failed:', error);
      return { ok: false, error: error.message };
    }
  };

  const handleFileSelect = async (e) => {
    const files = Array.from(e.target.files || []);

    for (const file of files) {
      const response = await uploadFile(file);
      if (response.ok) {
        const attachment = {
          file: file,
          url: response.url,
          type: getFileType(file.name),
          id: Date.now() + Math.random()
        };
        setAttachments(prev => [...prev, attachment]);
      } else {
        console.error('Failed to upload file:', file.name);
        alert(`Failed to upload ${file.name}`);
      }
    }

    // Clear input
    if (e.target) {
      e.target.value = '';
    }
  };

  const removeAttachment = (id) => {
    setAttachments(prev => prev.filter(a => a.id !== id));
  };

  const handleAttachClick = () => {
    fileInputRef.current?.click();
  };

  const disabled = composerIsEmpty && isRunning;

  return (
    <>
      <div
        ref={listRef}
        className="chat-list"
        role="log"
        aria-live="polite"
        aria-busy={isRunning}
      >
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
      </div>

      {suggestions?.length > 0 && (
        <div className="assistant-suggestions">
          {suggestions.map((suggestion) => (
            <button
              key={suggestion.id}
              type="button"
              className="assistant-suggestion-chip"
              onClick={() => handleSuggestion(suggestion)}
            >
              {suggestion.text}
            </button>
          ))}
        </div>
      )}

      <form className="chat-form" onSubmit={handleSubmit} autoComplete="off">
        <div className="input-container">
          <input
            ref={fileInputRef}
            type="file"
            multiple
            style={{ display: 'none' }}
            onChange={handleFileSelect}
            accept="image/*,video/*,audio/*,.pdf,.doc,.docx,.txt,.csv,.xls,.xlsx"
          />
          {attachments.length > 0 && (
            <div className="attachment-area" id="attachment-area">
              {attachments.map((att) => (
                <div key={att.id} className="attachment-item">
                  <span className="attachment-emoji">{getFileEmoji(att.type)}</span>
                  <span className="attachment-name">{att.file.name}</span>
                  <button
                    type="button"
                    className="attachment-remove"
                    onClick={() => removeAttachment(att.id)}
                    aria-label="Remove attachment"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}
          <div className="input-row">
            <textarea
              ref={textareaRef}
              className="chat-input"
              placeholder="Type your message…"
              aria-label="Message"
              rows={1}
              value={composerText}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
            />
            <button
              type="submit"
              className="chat-send-btn"
              aria-label="Send"
              disabled={disabled}
            >
              ➤
            </button>
          </div>

          <div className="input-actions input-actions-below">
            <div className="model-selector-container">
              <select
                className="model-selector"
                value={selectedModel}
                onChange={handleModelChange}
                aria-label="Select AI model"
              >
                {models.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name} • {model.provider}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="button"
              className="tool-btn"
              title="Attach file"
              aria-label="Attach file"
              onClick={handleAttachClick}
              disabled
            >
              +
            </button>
          </div>
        </div>
      </form>
    </>
  );
};
