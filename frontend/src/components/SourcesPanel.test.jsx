import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';

import { SourcesPanel } from './SourcesPanel.jsx';

const sources = [
  { id: '1', title: 'Example', url: 'https://example.com' },
  { id: '2', title: 'Docs', url: 'https://docs.example.com' },
];

describe('SourcesPanel', () => {
  beforeEach(() => {
    document.body.innerHTML = '';
  });

  it('renders nothing when no sources are provided', () => {
    const { container } = render(<SourcesPanel sources={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it('toggles popover visibility when button clicked', () => {
    render(<SourcesPanel sources={sources} />);

    const button = screen.getByRole('button', { name: /sources/i });
    Object.defineProperty(button, 'getBoundingClientRect', {
      value: () => ({ left: 10, top: 100, bottom: 120, width: 100, height: 20 }),
    });

    fireEvent.click(button);

    const popover = document.body.querySelector('.sources-popover');
    expect(popover).toBeInTheDocument();
    expect(popover.style.display).toBe('block');

    fireEvent.click(button);
    expect(popover.style.display).toBe('none');
  });
});
