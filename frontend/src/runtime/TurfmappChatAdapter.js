/**
 * Assistant UI chat adapter for the TURFMAPP backend.
 * Bridges assistant-ui's ChatModelAdapter interface with the existing
 * `/api/v1/chat/send` FastAPI endpoint while preserving tool knobs
 * that are stored in localStorage by the rest of the dashboard.
 */

const CHAT_ENDPOINT = "/api/v1/chat/send";

const DEFAULT_STATUS = {
  type: "complete",
  reason: "stop",
};

const EMPTY_METADATA = Object.freeze({
  unstable_state: null,
  unstable_annotations: [],
  unstable_data: [],
  steps: [],
  custom: {},
});

const getDefaultSettings = () => ({
  model: "gpt-4o",
  developerInstructions: "",
  assistantContext: "",
  textFormat: "text",
  textVerbosity: "medium",
  reasoningEffort: "medium",
  reasoningSummary: "auto",
  toolWebSearch: true,  // Enable web search by default
  webSearchContext: "medium",
  toolImageGen: false,
  imageQuality: "auto",
  toolMcp: false,
  mcpServerLabel: "",
  mcpConnectorId: "",
  storeResponses: true,
});

const loadSettings = () => {
  try {
    const raw = localStorage.getItem("tm_chat_settings");
    if (!raw) {
      return getDefaultSettings();
    }

    const parsed = JSON.parse(raw);
    return {
      ...getDefaultSettings(),
      ...parsed,
    };
  } catch (err) {
    console.warn("Failed to load chat settings from storage", err);
    return getDefaultSettings();
  }
};

const buildToolsArray = (
  settings,
  forceFlags = { image: false, search: false, gmail: false, calendar: false, drive: false },
) => {
  const tools = [];

  if (settings.toolWebSearch || forceFlags.search) {
    tools.push({
      type: "web_search_preview",
      user_location: { type: "approximate" },
      search_context_size: settings.webSearchContext || "medium",
    });
  }

  if (settings.toolImageGen || forceFlags.image) {
    tools.push({
      type: "image_generation",
      size: "auto",
      quality: settings.imageQuality || "auto",
      output_format: "png",
      background: "auto",
      moderation: "auto",
      partial_images: 3,
    });
  }

  if (forceFlags.gmail || forceFlags.calendar || forceFlags.drive) {
    tools.push({
      type: "google_mcp",
      enabled_tools: {
        gmail: Boolean(forceFlags.gmail),
        calendar: Boolean(forceFlags.calendar),
        drive: Boolean(forceFlags.drive),
      },
    });
  }

  if (settings.toolMcp && settings.mcpServerLabel && settings.mcpConnectorId) {
    tools.push({
      type: "mcp",
      server_label: settings.mcpServerLabel,
      connector_id: settings.mcpConnectorId,
      allowed_tools: ["fetch", "get_profile", "list_drives", "recent_documents", "search"],
      require_approval: "always",
    });
  }

  return tools;
};

const buildSystemInstructions = (settings, forceSearch = false) => {
  const instructions = [];

  if (settings.toolWebSearch || forceSearch) {
    instructions.push(
      "Use web search for current or real-time information including sports scores, news, weather, seasonal data, and recent facts.",
    );
  }

  if (settings.toolImageGen) {
    instructions.push("Generate images for creative requests or when the user explicitly asks for visuals.");
  }

  if (instructions.length > 0) {
    instructions.unshift(
      "You have tools available. Use them whenever they provide fresher or higher quality information than your training data.",
    );
  }

  return instructions.join(" ");
};

const extractUserInput = (messages) => {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const message = messages[i];
    if (message.role !== "user") {
      continue;
    }

    if (!Array.isArray(message.content)) {
      return typeof message.content === "string" ? message.content : "";
    }

    const textParts = message.content
      .filter((part) => part?.type === "text" && typeof part.text === "string")
      .map((part) => part.text.trim())
      .filter(Boolean);

    if (textParts.length > 0) {
      return textParts.join("\n\n");
    }
  }

  return "";
};

const normaliseSources = (maybeSources) => {
  if (!Array.isArray(maybeSources)) {
    return [];
  }

  return maybeSources
    .map((source, index) => {
      if (!source) return null;
      if (typeof source === "string") {
        return {
          id: `src-${index}`,
          title: source,
          url: source,
        };
      }

      const title = source.title || source.url || source.name || `Source ${index + 1}`;
      const url = source.url || source.link || null;

      if (!title && !url) return null;
      return {
        id: source.id || `src-${index}`,
        title,
        url,
        favicon: source.favicon || null,
        snippet: source.snippet || source.description || null,
      };
    })
    .filter(Boolean);
};

const normaliseBlocks = (blocks) => {
  if (!Array.isArray(blocks)) return [];
  return blocks
    .map((block, index) => {
      if (!block || typeof block !== "object") return null;
      return {
        id: block.id || `block-${index}`,
        ...block,
      };
    })
    .filter(Boolean);
};

const ensureArray = (value) => {
  if (!value) return [];
  return Array.isArray(value) ? value : [value];
};

export class TurfmappChatAdapter {
  constructor(getAuthToken) {
    this.getAuthToken = getAuthToken;
    this.conversationId = null;
  }

  /**
   * Load an existing conversation by ID
   * @param {string} conversationId
   * @returns {Promise<Array>} Array of messages
   */
  async loadConversation(conversationId) {
    const authToken = this.getAuthToken?.();
    if (!authToken) {
      throw new Error("Authentication required");
    }

    const response = await fetch(`/api/v1/chat/conversations/${conversationId}`, {
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      throw new Error(`Failed to load conversation: ${response.status}`);
    }

    const data = await response.json();
    this.conversationId = conversationId;

    // Transform backend messages to assistant-ui format
    return data.messages.map(msg => {
      const parsedMetadata = typeof msg.metadata === 'string'
        ? JSON.parse(msg.metadata || '{}')
        : (msg.metadata || {});

      if (msg.role === 'user') {
        return {
          role: 'user',
          content: [{ type: 'text', text: msg.content }]
        };
      } else if (msg.role === 'assistant') {
        return {
          role: 'assistant',
          content: [{ type: 'text', text: msg.content }],
          metadata: {
            custom: {
              sources: normaliseSources(parsedMetadata.sources),
              reasoning: ensureArray(parsedMetadata.reasoning),
              blocks: normaliseBlocks(parsedMetadata.blocks)
            }
          }
        };
      }
      return null;
    }).filter(Boolean);
  }

  /**
   * @param {import("@assistant-ui/react").ChatModelRunOptions} options
   * @returns {Promise<import("@assistant-ui/react").ChatModelRunResult>}
   */
  async run(options) {
    const authToken = this.getAuthToken?.();
    if (!authToken) {
      throw new Error("Authentication required");
    }

    const userText = extractUserInput(options.messages);
    if (!userText) {
      throw new Error("Unable to locate user message to send");
    }

    const settings = loadSettings();
    const forceFlags = {
      image: localStorage.getItem("tm_force_image_tool") === "true",
      search: localStorage.getItem("tm_force_search_tool") === "true",
      gmail: localStorage.getItem("tm_force_gmail_tool") === "true",
      calendar: localStorage.getItem("tm_force_calendar_tool") === "true",
      drive: localStorage.getItem("tm_force_drive_tool") === "true",
    };
    const tools = buildToolsArray(settings, forceFlags);
    const systemInstructions = buildSystemInstructions(settings, forceFlags.search);

    // Get attachments from global window object if available
    const attachments = window.pendingAttachments || null;

    // Use the selected model from the dropdown if available
    const selectedModel = window.selectedModel || settings.model || "gpt-4o";
    console.log('🔍 Adapter: Using model:', selectedModel);
    console.log('🔍 Adapter: window.selectedModel =', window.selectedModel);
    console.log('🔍 Adapter: settings.model =', settings.model);

    const payload = {
      message: userText,
      conversation_id: this.conversationId,
      model: selectedModel,
      tools: tools.length > 0 ? tools : null,
      tool_choice: forceFlags.search ? "required" : "auto",
      assistant_context: systemInstructions || settings.assistantContext || null,
      attachments: attachments,
    };

    console.log('🔍 Adapter: Full payload:', JSON.stringify(payload, null, 2));

    const response = await fetch(CHAT_ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${authToken}`,
      },
      body: JSON.stringify(payload),
      signal: options.abortSignal,
    });

    if (!response.ok) {
      const errorBody = await response.text();
      throw new Error(`Chat request failed (${response.status}): ${errorBody}`);
    }

    const data = await response.json();
    console.log("🔍 Backend response:", data);

    if (data?.conversation_id) {
      this.conversationId = data.conversation_id;
    }

    const assistantMessage = data?.assistant_message ?? {};
    const metadataFromBackend = data?.metadata ?? {};

    const rawContent = assistantMessage?.content ?? "";
    console.log("📝 Raw content from backend:", rawContent);
    const textParts = ensureArray(
      typeof rawContent === "string"
        ? [{ type: "text", text: rawContent }]
        : rawContent,
    )
      .filter((part) => Boolean(part))
      .map((part) => {
        if (typeof part === "string") {
          return { type: "text", text: part };
        }
        if (part.type === "text") {
          return { type: "text", text: part.text ?? "" };
        }
        if (part.type && part.text) {
          return { type: part.type, ...part };
        }
        return { type: "text", text: JSON.stringify(part) };
      });

    if (textParts.length === 0 && typeof rawContent === "string") {
      textParts.push({ type: "text", text: rawContent });
    }

    const sources =
      normaliseSources(data?.sources) ||
      normaliseSources(metadataFromBackend?.sources) ||
      normaliseSources(assistantMessage?.sources);

    const reasoning =
      ensureArray(data?.reasoning)
        .map((item) => (typeof item === "string" ? item : JSON.stringify(item)))
        .filter(Boolean) ||
      ensureArray(metadataFromBackend?.reasoning)
        .map((item) => (typeof item === "string" ? item : JSON.stringify(item)))
        .filter(Boolean);

    const blocksFromBackend =
      normaliseBlocks(metadataFromBackend?.blocks) ||
      normaliseBlocks(data?.blocks) ||
      normaliseBlocks(assistantMessage?.blocks);

    const customMetadata = {
      ...metadataFromBackend?.custom,
      sources,
      reasoning,
      blocks: blocksFromBackend,
      raw_response: data,
    };

    const result = {
      content: textParts,
      status: assistantMessage?.status ?? DEFAULT_STATUS,
      metadata: {
        ...EMPTY_METADATA,
        ...metadataFromBackend,
        custom: customMetadata,
      },
    };

    console.log("✅ Returning to assistant-ui:", result);
    return result;
  }
}
