import React from 'react';
import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';

vi.mock('./blocks/MarkdownBlock.jsx', () => ({
  MarkdownBlock: ({ text }) => <div data-testid="markdown">{text}</div>,
}));

vi.mock('./blocks/CodeBlock.jsx', () => ({
  CodeBlock: ({ code }) => <pre data-testid="code">{code}</pre>,
}));

vi.mock('./blocks/WeatherBlock.jsx', () => ({
  WeatherBlock: ({ data }) => <div data-testid="weather">{data.summary}</div>,
}));

vi.mock('./blocks/TableBlock.jsx', () => ({
  TableBlock: ({ rows }) => (
    <table data-testid="table">
      <tbody>
        {rows.map((row, index) => (
          <tr key={index}>
            {row.map((cell, idx) => (
              <td key={idx}>{cell}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  ),
}));

vi.mock('./blocks/SearchResultsBlock.jsx', () => ({
  SearchResultsBlock: ({ results }) => (
    <div data-testid="search">{results.length}</div>
  ),
}));

vi.mock('./blocks/KeyValueBlock.jsx', () => ({
  KeyValueBlock: ({ pairs }) => (
    <ul data-testid="key-value">
      {pairs.map((pair, index) => (
        <li key={index}>{pair.label}</li>
      ))}
    </ul>
  ),
}));

import { BlockRenderer } from './BlockRenderer.jsx';

describe('BlockRenderer', () => {
  it('renders markdown block', () => {
    render(<BlockRenderer block={{ type: 'markdown', text: 'Hello' }} />);
    expect(screen.getByTestId('markdown')).toHaveTextContent('Hello');
  });

  it('renders code block', () => {
    render(<BlockRenderer block={{ type: 'code', code: 'print(1)' }} />);
    expect(screen.getByTestId('code')).toHaveTextContent('print(1)');
  });

  it('falls back to tool response rendering', () => {
    render(<BlockRenderer block={{ type: 'tool-call', toolName: 'demo', result: { value: 1 } }} />);
    expect(screen.getByText('demo')).toBeInTheDocument();
    expect(screen.getByText(/"value": 1/)).toBeInTheDocument();
  });

  it('renders image block when image data is present', () => {
    render(
      <BlockRenderer
        block={{
          type: 'image',
          title: 'Generated Image',
          imageBase64: 'ZmFrZQ==',
          format: 'png',
        }}
      />,
    );

    const img = screen.getByRole('img', { name: /generated image/i });
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute('src', expect.stringContaining('data:image/png;base64,ZmFrZQ=='));
  });
});
