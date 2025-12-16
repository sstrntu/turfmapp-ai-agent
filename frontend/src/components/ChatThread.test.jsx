import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';

const threadState = {
  messages: [],
  isRunning: false,
  suggestions: [],
};

const composerState = {
  text: '',
  isEmpty: true,
};

const runtimeComposer = {
  setText: vi.fn(),
  send: vi.fn(),
};

vi.mock('@assistant-ui/react', () => ({
  useThread: (selector) => selector(threadState),
  useThreadComposer: (selector) => selector(composerState),
  useThreadRuntime: () => ({
    composer: runtimeComposer,
  }),
}));

vi.mock('./MessageBubble.jsx', () => ({
  MessageBubble: ({ message }) => (
    <div data-testid="message-bubble">{message.content}</div>
  ),
}));

vi.mock('./TypingIndicator.jsx', () => ({
  TypingIndicator: () => <div data-testid="typing-indicator" />,
}));

import { ChatThread } from './ChatThread.jsx';

describe('ChatThread component', () => {
  beforeEach(() => {
    threadState.messages = [];
    threadState.isRunning = false;
    threadState.suggestions = [];

    composerState.text = '';
    composerState.isEmpty = true;

    runtimeComposer.setText.mockClear();
    runtimeComposer.send.mockClear();

    localStorage.clear();
    window.supabase = {
      getAccessToken: vi.fn().mockReturnValue('token-123'),
    };
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      url: 'https://files.example.com/upload',
      json: () => Promise.resolve({ ok: true, url: 'https://files.example.com/upload' }),
    });
  });

  it('renders messages and suggestions from thread state', () => {
    threadState.messages = [{ id: 'm1', content: 'Hello from UI' }];
    threadState.suggestions = [{ id: 's1', text: 'Say hello back' }];

    render(<ChatThread />);

    expect(screen.getByTestId('message-bubble')).toHaveTextContent('Hello from UI');
    expect(screen.getByRole('button', { name: 'Say hello back' })).toBeInTheDocument();
  });

  it('updates composer text when user types in textarea', () => {
    render(<ChatThread />);

    const textarea = screen.getByLabelText('Message');
    fireEvent.change(textarea, { target: { value: 'Draft message' } });

    expect(runtimeComposer.setText).toHaveBeenCalledWith('Draft message');
  });

  it('submits a composed message and resets attachments', () => {
    composerState.isEmpty = false;

    render(<ChatThread />);

    const sendButton = screen.getByRole('button', { name: 'Send' });
    fireEvent.click(sendButton);

    expect(runtimeComposer.send).toHaveBeenCalledTimes(1);
  });

  it('uploads attachments and displays them before send', async () => {
    render(<ChatThread />);

    const fileInput = document.querySelector('input[type="file"]');
    const file = new File(['content'], 'report.pdf', { type: 'application/pdf' });
    await fireEvent.change(fileInput, { target: { files: [file] } });

    const attachmentChip = await screen.findByText('report.pdf');
    expect(attachmentChip).toBeInTheDocument();
  });

  it('submits message when pressing Enter without shift', () => {
    composerState.isEmpty = false;

    render(<ChatThread />);

    const textarea = screen.getByLabelText('Message');
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false, preventDefault: vi.fn() });

    expect(runtimeComposer.send).toHaveBeenCalled();
  });

  it('persists model preference changes and saves to backend', async () => {
    render(<ChatThread />);

    const select = screen.getByLabelText('Select AI model');
    fireEvent.change(select, { target: { value: 'claude-3-haiku-20240307' } });

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith('/api/v1/settings/preferences', expect.any(Object));
    });
    expect(localStorage.getItem('tm_model')).toBe('claude-3-haiku-20240307');

    const [_, requestInit] = fetch.mock.calls[0];
    expect(requestInit.method).toBe('PUT');
    expect(JSON.parse(requestInit.body)).toEqual({ default_model: 'claude-3-haiku-20240307' });
  });
});
