import { describe, it, expect, vi, beforeEach } from 'vitest';

import { TurfmappChatAdapter } from './TurfmappChatAdapter.js';

const encoder = new TextEncoder();

describe('TurfmappChatAdapter.run', () => {
  beforeEach(() => {
    window.chatRuntime = {};
    window.pendingAttachments = undefined;
    window.selectedModel = undefined;
  });

  it('fails when authentication token is missing', async () => {
    const adapter = new TurfmappChatAdapter(() => null);
    await expect(
      adapter.run({ messages: [{ role: 'user', content: [{ type: 'text', text: 'Hello' }] }], abortSignal: new AbortController().signal })
    ).rejects.toThrow('Authentication required');
  });

  it('streams events and returns assistant result', async () => {
    const adapter = new TurfmappChatAdapter(() => 'token-1');
    adapter._updateProgressOverlay = vi.fn();

    const stream = new ReadableStream({
      start(controller) {
        const events = [
          'data: {"type":"thought","content":"Thinking"}\n\n',
          'data: {"type":"tool_call","tool":"search"}\n\n',
          'data: {"type":"content","delta":"Hello "}\n\n',
          'data: {"type":"content","delta":"world"}\n\n',
          'data: {"type":"done","conversation_id":"conv-1","assistant_message":{"content":"Hello world"},"metadata":{},"sources":[{"title":"Example","url":"https://example.com"}],"tools_used":["search"],"reasoning":["step"]}\n\n',
        ];
        events.forEach((entry) => controller.enqueue(encoder.encode(entry)));
        controller.close();
      },
    });

    const responses = [
      {
        ok: true,
        json: () => Promise.resolve({ data: { has_tokens: false } }),
      },
      new Response(stream, { status: 200 }),
    ];

    global.fetch = vi.fn()
      .mockResolvedValueOnce(responses[0])
      .mockResolvedValueOnce(responses[1]);

    const result = await adapter.run({
      messages: [{ role: 'user', content: [{ type: 'text', text: 'Hello world' }] }],
      abortSignal: new AbortController().signal,
    });

    expect(result.content[0].text).toBe('Hello world');
    expect(result.metadata.custom.sources[0].title).toBe('Example');
    expect(adapter.conversationId).toBe('conv-1');
  });
});
