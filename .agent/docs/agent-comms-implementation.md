# Agent Comms Widget - Implementation Guide

> **Status**: UI mockup complete. Backend integration pending.

## Overview

The **Agent Comms Summary** widget displays inter-agent communications—messages that other users have sent to the current user via their AI agents. These messages serve as persistent context for the user's chat sessions.

## Current State (Demo)

### Frontend Components

**Files Modified:**
- `frontend/public/home.html` - Widget HTML structure
- `frontend/public/styles/home.css` - Widget styling

**HTML Structure:**
```html
<div class="widget-card glass-panel agent-summary-widget">
    <div class="widget-header">
        <h3>📋 Agent Comms - Summary</h3>
    </div>
    <div class="agent-summary-content">
        <div class="agent-message" data-message-id="xxx">
            <div class="message-sender">
                <span class="sender-avatar">T</span>
                <span class="sender-name">From Trisikh's Agent</span>
                <span class="message-type priority">Priority</span>
                <button class="message-dismiss-btn">×</button>
            </div>
            <p class="message-content">"Message content..."</p>
        </div>
    </div>
</div>
```

**Message Types (CSS Classes):**
- `.priority` - Red badge (urgent items)
- `.instruction` - Purple badge (standing instructions)
- `.reminder` - Blue badge (reminders/notes)

---

## Backend Integration Plan

### 1. Data Model

Create a new table for agent communications:

```sql
CREATE TABLE agent_comms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recipient_user_id UUID NOT NULL REFERENCES users(id),
    sender_user_id UUID NOT NULL REFERENCES users(id),
    sender_name TEXT NOT NULL,
    message_type TEXT NOT NULL CHECK (message_type IN ('priority', 'instruction', 'reminder', 'announcement')),
    content TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    dismissed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT now(),
    expires_at TIMESTAMP  -- Optional expiration
);

CREATE INDEX idx_agent_comms_recipient ON agent_comms(recipient_user_id, is_active);
```

### 2. API Endpoints

**File:** `backend/app/api/v2/agent_comms.py`

```python
# GET /api/v2/agent-comms
# Returns active agent comms for the current user

# POST /api/v2/agent-comms
# Create a new agent comm (sender's agent sends to recipient)

# DELETE /api/v2/agent-comms/{id}
# Dismiss/deactivate an agent comm

# PATCH /api/v2/agent-comms/{id}/dismiss
# Mark as dismissed (soft delete, keeps record)
```

### 3. Chat Context Integration

**Key Integration Point:** `backend/app/services/chat_instructions.py`

The `build_system_instructions()` function already accepts an `assistant_context` parameter:

```python
def build_system_instructions(
    *,
    tools: Optional[List[Dict[str, Any]]] = None,
    developer_instructions: Optional[str] = None,
    assistant_context: Optional[str] = None,  # <-- USE THIS
) -> str:
```

**Implementation in `chat_service.py`:**

```python
# In process_chat_request(), before calling the AI:

# 1. Fetch active agent comms for this user
agent_comms = await self.get_active_agent_comms(user_id)

# 2. Format as context string
agent_comms_context = self._format_agent_comms_context(agent_comms)

# 3. Pass to build_system_instructions()
system_instructions = build_system_instructions(
    tools=tools_to_include,
    assistant_context=agent_comms_context
)
```

**Context Format Example:**
```
AGENT COMMUNICATIONS CONTEXT:
The following are active directives from other users' agents that should influence your responses:

[PRIORITY] From Trisikh: "Prioritize Project Alpha for now. Push back other tasks until Thursday."
[INSTRUCTION] From Mike: "Always factor in Q4 revenue projections when preparing summaries."
[REMINDER] From Sarah: "Client prefers visual data; include charts in all research outputs."

Consider these directives when responding to the user.
```

### 4. Frontend JavaScript

**File:** `frontend/public/scripts/agent-comms.js` (new file)

```javascript
const AgentComms = {
    async load() {
        const response = await fetch('/api/v2/agent-comms', {
            headers: { 'Authorization': `Bearer ${await GoogleAuth.getAccessToken()}` }
        });
        const comms = await response.json();
        this.render(comms);
    },

    render(comms) {
        const container = document.querySelector('.agent-summary-content');
        container.innerHTML = comms.map(comm => this.renderMessage(comm)).join('');
    },

    renderMessage(comm) {
        return `
            <div class="agent-message" data-message-id="${comm.id}">
                <div class="message-sender">
                    <span class="sender-avatar">${comm.sender_name[0]}</span>
                    <span class="sender-name">From ${comm.sender_name}'s Agent</span>
                    <span class="message-type ${comm.message_type}">${comm.message_type}</span>
                    <button class="message-dismiss-btn" onclick="AgentComms.dismiss('${comm.id}')">×</button>
                </div>
                <p class="message-content">"${comm.content}"</p>
            </div>
        `;
    },

    async dismiss(id) {
        await fetch(`/api/v2/agent-comms/${id}/dismiss`, {
            method: 'PATCH',
            headers: { 'Authorization': `Bearer ${await GoogleAuth.getAccessToken()}` }
        });
        document.querySelector(`[data-message-id="${id}"]`).remove();
    }
};
```

---

## User Flow

1. **User A** (e.g., a manager) tells their AI agent:
   > "Tell User B to prioritize Project Alpha"

2. **User A's Agent** creates an `agent_comm` record:
   - `recipient_user_id`: User B's ID
   - `sender_user_id`: User A's ID
   - `sender_name`: "Trisikh"
   - `message_type`: "priority"
   - `content`: "Prioritize Project Alpha for now"

3. **User B** sees this in their Agent Comms Summary widget

4. **User B's AI** receives this as context in every chat session

5. **User B** can dismiss the directive when it's no longer relevant

---

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `backend/app/api/v2/agent_comms.py` | CREATE | API endpoints |
| `backend/app/database/agent_comms.py` | CREATE | Database operations |
| `backend/app/services/chat_service.py` | MODIFY | Fetch and inject context |
| `frontend/public/scripts/agent-comms.js` | CREATE | Frontend JS module |
| `frontend/public/home.html` | MODIFY | Add script include |

---

## Testing Checklist

- [ ] Agent comms persist in database
- [ ] Widget loads comms on page load
- [ ] Dismiss button removes comm from widget
- [ ] Dismissed comms no longer appear in chat context
- [ ] Chat AI references active comms appropriately
- [ ] Expired comms auto-deactivate
