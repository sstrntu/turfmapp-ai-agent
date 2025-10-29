# Task Board

## Active Tasks
- [ ] Audit documentation references for outdated filenames (e.g., `enhanced_chat_service.py`, `mcp_client_simple.py`, `settings.py`) and align with current structure (2025-10-14)

## Completed Tasks
- [x] Rename `backend/app/core/simple_auth.py` to `backend/app/core/jwt_auth.py` to comply with naming guidelines (2025-10-14)
- [x] Fix Claude web search tool integration to match Anthropic web search support (2025-10-14)
- [x] Let LLM decide Google MCP usage instead of forcing direct execution (2025-10-14)

## Discovered During Work
- Documentation still mentions removed modules; consolidated into the active doc-audit task above (2025-10-14)

## Technical Debt
### Code Quality (2025-10-29)
- **TypeScript Migration**: Frontend uses JavaScript instead of TypeScript (violates code.md standards)
  - Recommendation: Gradual migration to TypeScript for type safety
  - Priority: Medium

- **Large File Refactoring** (High Priority):

  **1. chat_service.py (1,168 lines)**
  - Current structure: Single `EnhancedChatService` class with mixed responsibilities
  - Proposed split into 3 modules:
    - `chat_db_operations.py` - Database operations (conversation history, preferences, CRUD)
    - `chat_api_client.py` - API client wrappers (Claude API, OpenAI API)
    - `chat_service.py` - Main orchestration service (imports from above modules)
  - Risk: High - many imports across codebase reference this file
  - Estimated effort: 4-6 hours with full test coverage

  **2. unified_workflow.py (976 lines)**
  - Current structure: Single workflow class with tool execution logic
  - Proposed split into 2 modules:
    - `workflow_core.py` - Core workflow logic and orchestration
    - `workflow_tool_executor.py` - Tool execution handlers (web search, Google MCP, image gen)
  - Risk: Medium - primarily used by chat endpoints
  - Estimated effort: 3-4 hours with testing

  **Implementation notes:**
  - Requires comprehensive testing before/after refactoring
  - Must update all import statements across codebase
  - Should be done as dedicated task with proper code review

- **Token Usage Tracking**: Chat V2 endpoint doesn't track token usage
  - Requires implementing token tracking in LlamaIndex workflow
  - Priority: Low (informational field only)
