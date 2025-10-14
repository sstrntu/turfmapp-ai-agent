'use strict';

/**
 * UI utilities (globals under window.UI)
 */
window.UI = window.UI || {};

/**
 * Position a floating popover element relative to a toggle button.
 * Uses fixed positioning to avoid clipping in scrollable containers.
 *
 * @param {HTMLElement} toggle - The anchor element that triggers the popover
 * @param {HTMLElement} pop - The popover element to position
 * @param {number} spacing - Gap in pixels between toggle and popover
 */
window.UI.positionPopover = function positionPopover(toggle, pop, spacing) {
    if (!toggle || !pop) return;
    const gap = typeof spacing === 'number' ? spacing : 8;

    // Prepare for measurement
    const prevDisplay = pop.style.display;
    const prevVisibility = pop.style.visibility;
    const prevPosition = pop.style.position;
    pop.style.position = 'fixed';
    pop.style.visibility = 'hidden';
    pop.style.display = 'block';

    const rect = toggle.getBoundingClientRect();
    let left = rect.left;
    let top = rect.top - pop.offsetHeight - gap; // place above by default

    // If off top, place below
    if (top < 8) top = rect.bottom + gap;

    // Constrain horizontally within viewport
    const vw = Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0);
    const maxLeft = vw - pop.offsetWidth - 8;
    if (left > maxLeft) left = Math.max(8, maxLeft);
    if (left < 8) left = 8;

    pop.style.left = left + 'px';
    pop.style.top = top + 'px';

    // Restore
    pop.style.visibility = prevVisibility || 'visible';
    pop.style.display = prevDisplay || 'block';
    pop.style.position = prevPosition || 'fixed';
};

/**
 * Initialize sidebar/left panel toggle functionality
 */
window.UI.initSidebar = function initSidebar() {
    const lpToggle = document.getElementById('left-panel-toggle');
    const lpClose = document.getElementById('left-panel-close');
    const lp = document.getElementById('left-panel');

    if (!lpToggle || !lp) return;

    function setLeftPanel(open) {
        lp.classList.toggle('open', open);
        lp.setAttribute('aria-hidden', open ? 'false' : 'true');
        lpToggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        document.body.classList.toggle('panel-open', open);
    }

    lpToggle.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        const isCurrentlyOpen = lp.classList.contains('open');
        setLeftPanel(!isCurrentlyOpen);
    });

    if (lpClose) {
        lpClose.addEventListener('click', function() {
            setLeftPanel(false);
        });
    }

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            setLeftPanel(false);
        }
    });
};

/**
 * Load and render conversation history
 */
window.UI.loadConversationHistory = async function loadConversationHistory(retryCount = 0) {
    const histList = document.getElementById('history-list');
    if (!histList) return;

    try {
        const token = window.supabase?.getAccessToken?.();
        if (!token) {
            // Retry up to 5 times with exponential backoff if auth not ready
            if (retryCount < 5) {
                const delay = Math.pow(2, retryCount) * 300; // 300ms, 600ms, 1.2s, 2.4s, 4.8s
                setTimeout(() => window.UI.loadConversationHistory(retryCount + 1), delay);
                histList.innerHTML = '<li class="history-placeholder">Loading history...</li>';
                return;
            }
            histList.innerHTML = '<li class="history-placeholder">Please log in to view history</li>';
            return;
        }

        const response = await fetch('/api/v1/chat/conversations', {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        const conversations = data.conversations || [];

        if (conversations.length === 0) {
            histList.innerHTML = '<li class="history-placeholder">No conversations yet</li>';
            return;
        }

        // Group by date
        const groupedByDate = {};
        conversations.forEach(conv => {
            const date = new Date(conv.updated_at || conv.created_at);
            const today = new Date();
            const yesterday = new Date(today);
            yesterday.setDate(yesterday.getDate() - 1);

            let dateStr;
            if (date.toDateString() === today.toDateString()) {
                dateStr = 'Today';
            } else if (date.toDateString() === yesterday.toDateString()) {
                dateStr = 'Yesterday';
            } else {
                dateStr = date.toLocaleDateString();
            }

            if (!groupedByDate[dateStr]) {
                groupedByDate[dateStr] = [];
            }
            groupedByDate[dateStr].push(conv);
        });

        // Render
        histList.innerHTML = '';
        Object.keys(groupedByDate).forEach(dateStr => {
            const dateHeader = document.createElement('li');
            dateHeader.className = 'date-group-header';
            dateHeader.textContent = dateStr;
            histList.appendChild(dateHeader);

            groupedByDate[dateStr].forEach(conv => {
                const li = document.createElement('li');
                li.className = 'conversation-item';

                // Conversation header container
                const header = document.createElement('div');
                header.className = 'conversation-header';

                // Conversation button
                const button = document.createElement('button');
                button.className = 'conversation-btn';
                button.textContent = conv.title || 'Untitled conversation';
                button.setAttribute('data-conversation-id', conv.id);

                button.addEventListener('click', async function() {
                    // Close sidebar
                    const lp = document.getElementById('left-panel');
                    if (lp) {
                        lp.classList.remove('open');
                        lp.setAttribute('aria-hidden', 'true');
                        document.body.classList.remove('panel-open');
                    }

                    // Load conversation
                    try {
                        if (!window.loadConversation) {
                            console.error('loadConversation function not available');
                            return;
                        }

                        await window.loadConversation(conv.id);
                    } catch (error) {
                        console.error('Failed to load conversation:', error);
                        alert('Failed to load conversation. Please try again.');
                    }
                });

                // Delete button
                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'conversation-delete-btn';
                deleteBtn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>';
                deleteBtn.title = 'Delete conversation';
                deleteBtn.setAttribute('aria-label', 'Delete conversation');

                deleteBtn.addEventListener('click', async function(e) {
                    e.stopPropagation();
                    if (!confirm('Are you sure you want to delete this conversation? This action cannot be undone.')) {
                        return;
                    }

                    try {
                        const token = window.supabase?.getAccessToken?.();
                        if (!token) {
                            alert('Authentication required');
                            return;
                        }

                        const response = await fetch(`/api/v1/chat/conversations/${conv.id}`, {
                            method: 'DELETE',
                            headers: {
                                'Authorization': `Bearer ${token}`,
                                'Content-Type': 'application/json'
                            }
                        });

                        if (!response.ok) {
                            throw new Error(`HTTP ${response.status}`);
                        }

                        // If current conversation was deleted, start a new one
                        if (window.chatAdapter && window.chatAdapter.conversationId === conv.id) {
                            window.location.reload();
                        } else {
                            // Refresh history
                            await window.UI.loadConversationHistory();
                        }
                    } catch (error) {
                        console.error('Failed to delete conversation:', error);
                        alert('Failed to delete conversation. Please try again.');
                    }
                });

                header.appendChild(button);
                header.appendChild(deleteBtn);
                li.appendChild(header);
                histList.appendChild(li);
            });
        });

    } catch (error) {
        console.error('Failed to load conversation history:', error);
        histList.innerHTML = '<li class="history-placeholder error">Failed to load history</li>';
    }
};

/**
 * Handle new chat button
 */
window.UI.initNewChat = function initNewChat() {
    const newChatBtn = document.getElementById('btn-new-chat');
    if (!newChatBtn) return;

    newChatBtn.addEventListener('click', function() {
        // Reload page to start fresh conversation
        window.location.reload();
    });
};

// Initialize sidebar and load history on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        window.UI.initSidebar();
        window.UI.initNewChat();
        window.UI.loadConversationHistory();
    });
} else {
    window.UI.initSidebar();
    window.UI.initNewChat();
    window.UI.loadConversationHistory();
}


