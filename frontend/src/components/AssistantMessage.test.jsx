import React from 'react';
import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';

vi.mock('./BlockRenderer.jsx', () => ({
  BlockRenderer: ({ block }) => (
    <div data-testid="block" data-type={block.type}>
      {block.text || block.title || block.toolName}
    </div>
  ),
}));

vi.mock('./ReasoningPanel.jsx', () => ({
  ReasoningPanel: ({ reasoning }) => (
    <div data-testid="reasoning">{reasoning.join('|')}</div>
  ),
}));

vi.mock('./SourcesPanel.jsx', () => ({
  SourcesPanel: ({ sources }) => (
    <ul data-testid="sources">
      {sources.map((source) => (
        <li key={source.id}>{source.title}</li>
      ))}
    </ul>
  ),
}));

vi.mock('./MemoryConsentPrompt.jsx', () => ({
  MemoryConsentPrompt: ({ facts }) => (
    <div data-testid="memory-consent">{facts.map((fact) => fact.key).join(',')}</div>
  ),
}));

import { AssistantMessage } from './AssistantMessage.jsx';

const baseMessage = {
  id: 'assistant-1',
  content: [
    { type: 'text', text: 'Primary response' },
    { type: 'reasoning', text: 'step 1' },
    { type: 'source', title: 'Doc', url: 'https://example.com' },
    {
      type: 'tool-call',
      toolName: 'weather_lookup',
      result: { temperature: '30C' },
    },
  ],
  metadata: {
    custom: {
      reasoning: ['metadata step'],
      blocks: [{ type: 'markdown', text: 'Metadata block' }],
    },
  },
};

describe('AssistantMessage', () => {
  it('renders markdown block, reasoning and sources', () => {
    render(<AssistantMessage message={baseMessage} />);

    const blocks = screen.getAllByTestId('block');
    expect(blocks).toHaveLength(3); // markdown + tool-call + metadata block
    expect(blocks[0]).toHaveAttribute('data-type', 'markdown');

    expect(screen.getByTestId('reasoning')).toHaveTextContent('step 1|metadata step');
    expect(screen.getByTestId('sources')).toHaveTextContent('Doc');
  });

  it('handles empty content gracefully', () => {
    render(<AssistantMessage message={{ id: 'empty', content: [] }} />);
    expect(screen.queryByTestId('block')).not.toBeInTheDocument();
  });

  it('renders memory consent prompt when metadata includes request', () => {
    const messageWithMemory = {
      ...baseMessage,
      metadata: {
        custom: {
          memory_request: { facts: [{ key: 'profession', value: 'Engineer' }] },
        },
        conversation_id: 'conv-123',
      },
    };

    render(<AssistantMessage message={messageWithMemory} />);
    expect(screen.getByTestId('memory-consent')).toHaveTextContent('profession');
  });
});
