# TURFMAPP AI Agent - Backend Service

## 🏗️ Architecture Overview

The backend is built as a sophisticated **FastAPI-based agentic AI system** featuring intelligent tool selection, Google services integration, and advanced conversational AI capabilities.

### **Core Architecture Pattern**
```
API Layer → Service Layer → Integration Layer
    ↓           ↓              ↓
FastAPI    Agentic Chat    OpenAI/Google APIs
Endpoints   Intelligence    Database Storage
```

## 🤖 Agentic Intelligence System

### **Enhanced Chat Service (`app/services/enhanced_chat_service.py`)**
The core orchestration service implementing the agentic workflow:

#### **AI-Driven Tool Selection**
```python
# Instead of hardcoded keywords, uses AI to select tools:
user_query: "What's my latest email about?"
    ↓
AI Analysis: Determines intent = "get recent email" 
    ↓
Tool Selection: gmail_recent(max_results=1)
    ↓
AI Analysis: Raw email → conversational summary
```

#### **Multi-Step Processing Pipeline**
1. **Request Classification**: Determine if Google tools are needed
2. **Function Definition Generation**: Create rich tool descriptions for AI
3. **Tool Selection**: AI chooses appropriate tools with optimal parameters
4. **Execution**: MCP client calls real Google APIs
5. **Response Analysis**: AI transforms raw data into conversational responses

### **Google MCP Integration (`app/services/mcp_client_simple.py`)**
Model Context Protocol implementation for Google services:

- **Gmail Tools**: `gmail_recent`, `gmail_search`, `gmail_get_message`, `gmail_important`
- **Calendar Tools**: `calendar_upcoming_events`, `calendar_list_events`
- **Drive Tools**: `drive_list_files`, `drive_create_folder`, `drive_list_folder_files`

#### **Key Features**
- OAuth 2.0 authentication with token management
- Comprehensive error handling and debugging
- Response formatting for AI analysis
- Rate limiting and API quota management

### **Agent Orchestration (`app/services/master_agent.py`)**
High-level agent coordination and decision making:

- **Intent Recognition**: Determines user goals from natural language
- **Context Management**: Maintains conversation state and history
- **Tool Coordination**: Orchestrates multiple tools when needed
- **Response Optimization**: Ensures coherent and helpful responses

## 📁 Directory Structure

```
backend/
├── app/
│   ├── api/v1/                    # API Endpoints
│   │   ├── admin.py               # Admin management
│   │   ├── auth.py                # Authentication
│   │   ├── chat.py                # Chat interface
│   │   ├── google_api.py          # Google services endpoints
│   │   ├── preferences.py         # User preferences
│   │   └── settings.py            # Settings management
│   │
│   ├── core/                      # Core Functionality
│   │   ├── auth.py                # Supabase authentication
│   │   ├── config.py              # Configuration management
│   │   └── jwt_auth.py            # Development JWT fallback auth
│   │
│   ├── services/                  # Business Logic Layer (Refactored Phase 3)
│   │   ├── chat_service.py                 # 🤖 Core chat service (facade)
│   │   ├── chat_source_extractor.py        # URL/source extraction
│   │   ├── chat_block_builder.py           # UI block building
│   │   ├── chat_response_parser.py         # Response parsing
│   │   │
│   │   ├── chat_tool_handler.py            # 🛠️ Tool handler (facade)
│   │   ├── chat_tool_definitions.py        # Google tool schemas
│   │   ├── chat_mcp_handler.py             # AI-driven tool selection
│   │   ├── chat_tool_executor.py           # Generic tool routing
│   │   │
│   │   ├── mcp_client.py                   # 🔗 MCP client (facade)
│   │   ├── mcp/                            # MCP handler modules
│   │   │   ├── mcp_gmail_handler.py        # Gmail operations
│   │   │   ├── mcp_drive_handler.py        # Drive operations
│   │   │   └── mcp_calendar_handler.py     # Calendar operations
│   │   │
│   │   ├── google_oauth.py                 # Google OAuth (facade)
│   │   ├── google_oauth_core.py            # OAuth & authentication
│   │   ├── google_gmail_ops.py             # Gmail API operations
│   │   ├── google_drive_ops.py             # Drive API operations
│   │   ├── google_calendar_ops.py          # Calendar API operations
│   │   │
│   │   └── tool_manager.py                 # Traditional tool manager
│   │
│   ├── database/                  # Data Layer
│   │   ├── __init__.py            # Service exports
│   │   ├── conversation_service.py # Conversation management
│   │   └── user_service.py        # User data management
│   │
│   └── utils/                     # Utilities
│       ├── chat_utils.py          # Chat processing helpers
│       └── sources_utils.py       # Source extraction utilities
│
├── tests/                         # Comprehensive Test Suite
│   ├── test_enhanced_chat_service_ai_analysis.py  # Agentic AI tests
│   ├── test_enhanced_chat_service_fixed.py        # Core functionality
│   ├── test_mcp_client_simple_debugging.py        # Google MCP tests
│   ├── test_google_mcp_integration.py             # Integration tests
│   ├── test_api_ping/                             # API endpoint tests
│   └── test_integration/                          # End-to-end tests
│
├── docs/                          # Documentation
│   ├── ARCHITECTURE.md            # System architecture
│   ├── REFACTORING.md             # Phase 3 refactoring docs
│   └── API_DOCUMENTATION.md       # API reference
│
├── README_TESTING.md              # Testing documentation
├── requirements.txt               # Dependencies
├── pytest.ini                     # Test configuration
├── .coveragerc                    # Coverage configuration
└── Dockerfile                     # Container configuration
```

> **📖 Phase 3 Refactoring (January 2025)**: Services are now organized into focused, single-responsibility modules following the facade pattern. See [docs/REFACTORING.md](./docs/REFACTORING.md) for complete details.

## 🔧 Service Layer Details

### **Modular Architecture (Phase 3 Refactoring)**

The service layer has been refactored into focused, single-responsibility modules:

#### **Design Patterns Used**
1. **Facade Pattern**: Main services (`chat_service.py`, `mcp_client.py`, `chat_tool_handler.py`, `google_oauth.py`) act as facades that delegate to specialized modules while maintaining backward compatibility
2. **Handler Pattern**: MCP handlers route requests to appropriate Google service operations
3. **Functional Decomposition**: Complex logic broken down into focused, reusable functions
4. **Dependency Injection**: Functions accept dependencies as parameters for loose coupling

#### **Benefits**
- ✅ All files under 500 lines (code.md compliance)
- ✅ Improved maintainability through single-responsibility modules
- ✅ Enhanced testability with focused functions
- ✅ Zero breaking changes - full backward compatibility
- ✅ Clear module boundaries reduce cognitive load

### **Enhanced Chat Service Architecture**

#### **Key Methods**
- `process_chat_request()`: Main entry point for chat processing
- `_handle_google_mcp_request()`: Agentic Google tools workflow (delegates to `chat_mcp_handler`)
- `call_responses_api()`: OpenAI Responses API integration
- `handle_tool_calls()`: Traditional tool execution (delegates to `chat_tool_executor`)

#### **Agentic Workflow Implementation**
```python
async def _handle_google_mcp_request(self, user_message, ...):
    # 1. Generate function definitions based on enabled tools
    available_tools = self._create_function_definitions(enabled_tools)
    
    # 2. Use AI to select tools and parameters
    tool_selection_result = await self.call_responses_api(
        messages=messages, tools=available_tools
    )
    
    # 3. Execute selected tools via MCP
    for function_call in parsed_calls:
        result = await google_mcp_client.call_tool(tool_name, params)
        
    # 4. AI analysis of raw results
    analysis_result = await self.call_responses_api(
        messages=analysis_messages  # Contains raw data + analysis prompt
    )
    
    # 5. Return conversational response
    return {"response": final_response}
```

### **Google MCP Client Architecture**

#### **Core Components**
- **Authentication Manager**: Google OAuth 2.0 token handling
- **Tool Registry**: Dynamic tool discovery and registration  
- **Request Handler**: API call management with retry logic
- **Response Formatter**: Standardized response format for AI analysis

#### **Tool Implementation Pattern**
```python
async def _handle_gmail_tool(self, tool_name: str, credentials, arguments: dict):
    print(f"🗓️ Handling Gmail tool: {tool_name} with args: {arguments}")
    
    try:
        if tool_name == "gmail_recent":
            result = await google_oauth_service.get_recent_emails(
                credentials, max_results=arguments.get("max_results", 5)
            )
        # ... other tools
        
        print(f"✅ Gmail tool result: {result}")
        return {"success": True, "response": formatted_response}
        
    except Exception as e:
        print(f"❌ Gmail tool error: {e}")
        return {"success": False, "error": str(e)}
```

## 🧪 Testing Architecture

### **Test Categories**
1. **Unit Tests**: Individual service component testing
2. **Integration Tests**: End-to-end workflow testing
3. **API Tests**: Endpoint functionality verification
4. **MCP Tests**: Google services integration testing

### **Key Test Files**
- `test_enhanced_chat_service_ai_analysis.py`: Tests the agentic AI pipeline
- `test_mcp_client_simple_debugging.py`: Tests Google MCP integration
- `test_enhanced_chat_service_fixed.py`: Core service functionality

### **Running Tests**
```bash
# All tests
pytest

# Specific test categories
pytest tests/test_enhanced_chat_service_ai_analysis.py -v
pytest tests/test_mcp_client_simple_debugging.py -v

# With coverage
pytest --cov=app --cov-report=html
```

## 🔌 API Integration

### **OpenAI Responses API**
- **Models Supported**: GPT-4O, O1, GPT-5-mini with enhanced capabilities
- **Function Calling**: Rich tool descriptions for AI decision-making
- **Response Parsing**: Nested response structure handling

### **Google APIs**
- **Gmail API**: Email access and search with OAuth 2.0
- **Calendar API**: Event management and scheduling
- **Drive API**: File management and organization

### **Database Integration**
- **Primary**: Supabase/PostgreSQL for production
- **Fallback**: In-memory storage for development/testing
- **Services**: Conversation and user data management

## 🚀 Development Setup

### **Prerequisites**
- Python 3.9+
- PostgreSQL (or Supabase account)
- OpenAI API key
- Google Cloud Console project with APIs enabled

### **Installation**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### **Environment Configuration**
```bash
cp .env.example .env
# Edit .env with your API keys and database URLs
```

### **Running the Server**
```bash
# Development
uvicorn app.main:app --reload --port 8000

# Production
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 📊 Performance Considerations

### **Optimization Strategies**
- **Async Processing**: All external API calls are asynchronous
- **Connection Pooling**: Database connections optimized for concurrent access
- **Error Handling**: Comprehensive fallback patterns for resilience
- **Caching**: Admin status and frequently accessed data

### **Scalability Features**
- **Containerization**: Docker support for horizontal scaling
- **Database Abstraction**: Easy migration between database systems
- **Service Isolation**: Clear separation of concerns for independent scaling

## 🔒 Security Implementation

### **Authentication & Authorization**
- **JWT Tokens**: Supabase integration with automatic refresh
- **Role-Based Access**: User, admin, super_admin roles
- **Permission Validation**: Endpoint-level access control

### **Data Security**
- **Input Validation**: Pydantic models for request/response validation
- **SQL Injection Prevention**: Parameterized queries
- **Secret Management**: Environment-based configuration

---

## 📚 Related Documentation

- **[docs/REFACTORING.md](./docs/REFACTORING.md)**: Complete Phase 3 refactoring documentation
  - Module-by-module breakdown of all refactored services
  - Design patterns and architectural decisions
  - Migration guides for developers (backward compatible vs. direct module access)
  - Before/after metrics showing all files now under 500 lines

- **[docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)**: System architecture overview
  - High-level architecture diagrams
  - Data flow and sequence diagrams
  - Security and performance architecture
  - Database schema and optimization strategies

- **[docs/API_DOCUMENTATION.md](./docs/API_DOCUMENTATION.md)**: API reference
  - Complete endpoint documentation
  - Request/response schemas
  - Authentication flows
  - Error handling examples

---

**Enterprise Ready**: This backend service implements production-grade patterns with comprehensive error handling, testing, and scalability features designed for enterprise environments.
