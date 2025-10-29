import {
  getDefaultSettings,
  loadSettings,
  buildToolsArray,
  buildSystemInstructions,
  normaliseSources,
  normaliseBlocks,
  ensureArray,
  extractUserInput,
} from './TurfmappChatAdapter.js';

beforeEach(() => {
  localStorage.clear();
});

describe('TurfmappChatAdapter helpers', () => {
  it('returns default settings when storage is empty', () => {
    const defaults = getDefaultSettings();
    expect(defaults).toMatchObject({
      model: 'gpt-4o',
      toolWebSearch: true,
      storeResponses: true,
    });

    const loaded = loadSettings();
    expect(loaded.model).toBe('gpt-4o');
    expect(loaded.toolWebSearch).toBe(true);
  });

  it('merges stored preferences with defaults', () => {
    localStorage.setItem(
      'tm_chat_settings',
      JSON.stringify({ model: 'claude-3-haiku-20240307', toolWebSearch: false }),
    );

    const loaded = loadSettings();
    expect(loaded.model).toBe('claude-3-haiku-20240307');
    expect(loaded.toolWebSearch).toBe(false);
    expect(loaded.storeResponses).toBe(true);
  });

  it('builds tool configuration using settings and forced flags', () => {
    const settings = {
      ...getDefaultSettings(),
      toolMcp: true,
      toolImageGen: true,
      mcpServerLabel: 'support',
      mcpConnectorId: 'conn-123',
      imageQuality: 'high',
      webSearchContext: 'large',
    };

    const tools = buildToolsArray(settings, {
      image: false,
      search: false,
      gmail: true,
      calendar: true,
      drive: false,
    });

    const webSearchTool = tools.find((tool) => tool.type === 'web_search_preview');
    expect(webSearchTool).toMatchObject({ search_context_size: 'large' });

    const googleTool = tools.find((tool) => tool.type === 'google_mcp');
    expect(googleTool?.enabled_tools).toMatchObject({ gmail: true, calendar: true, drive: false });

    const imageTool = tools.find((tool) => tool.type === 'function' && tool.function?.name === 'generate_image');
    expect(imageTool).toBeTruthy();

    const mcpTool = tools.find((tool) => tool.type === 'mcp');
    expect(mcpTool).toMatchObject({ server_label: 'support', connector_id: 'conn-123' });
  });

  it('builds system instructions when search is enabled', () => {
    const instructions = buildSystemInstructions(getDefaultSettings(), true);
    expect(instructions).toContain('Use web search');
    expect(instructions).toContain('You have tools available.');
  });

  it('normalises sources from strings and objects', () => {
    const sources = normaliseSources([
      'https://example.com',
      { title: 'Docs', url: 'https://docs.example.com', snippet: 'Details' },
      null,
    ]);

    expect(sources).toHaveLength(2);
    expect(sources[0]).toMatchObject({
      id: expect.stringContaining('src-'),
      title: 'https://example.com',
    });
    expect(sources[1]).toMatchObject({
      title: 'Docs',
      url: 'https://docs.example.com',
      snippet: 'Details',
    });
  });

  it('normalises blocks and ensures arrays', () => {
    const blocks = normaliseBlocks([{ id: 'block-1', type: 'code', language: 'js' }]);
    expect(blocks).toEqual([{ id: 'block-1', type: 'code', language: 'js' }]);

    expect(normaliseBlocks(null)).toEqual([]);
    expect(ensureArray('hello')).toEqual(['hello']);
    expect(ensureArray(['a'])).toEqual(['a']);
  });

  it('extracts the most recent user input from message list', () => {
    const messages = [
      { role: 'assistant', content: 'Hi there' },
      { role: 'user', content: [{ type: 'text', text: 'First' }] },
      { role: 'system', content: 'System message' },
      {
        role: 'user',
        content: [
          { type: 'text', text: 'Second' },
          { type: 'text', text: 'Line two' },
        ],
      },
    ];

    const input = extractUserInput(messages);
    expect(input).toBe('Second\n\nLine two');
  });
});
