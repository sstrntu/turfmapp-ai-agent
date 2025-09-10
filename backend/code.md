# Python Code Standards - TURFMAPP AI Agent Backend

## File Organization Standards

### File Size Limits
- **Maximum file size**: 800 lines per file
- **Recommended size**: 300-500 lines per file
- **Action**: Split files exceeding 800 lines into logical modules

### File Naming Conventions
- Use descriptive, standard names without qualifiers
- ✅ `chat_service.py` (not `enhanced_chat_service.py`)
- ✅ `mcp_client.py` (not `mcp_client_simple.py`)
- ✅ `user_service.py`, `tool_manager.py`
- ❌ Avoid: `enhanced_`, `simple_`, `new_`, `old_` prefixes

### Directory Structure
```
app/
├── api/v1/           # API endpoints (FastAPI routers)
├── services/         # Business logic services
├── models/           # Database models
├── utils/            # Utility functions
├── core/             # Core functionality (auth, config)
└── database/         # Database connection and operations
```

## Code Quality Standards

### Logging
- **Required**: Use structured logging instead of print statements
- **Setup**: Configure logger at module level
```python
import logging
logger = logging.getLogger(__name__)

# Use logging instead of print
logger.info("✅ Operation completed")
logger.error("❌ Operation failed: {error}")
logger.debug("🔧 Debug information")
```

### DateTime Usage
- **Required**: Use timezone-aware datetime objects
- ✅ `datetime.now(timezone.utc)` 
- ❌ `datetime.utcnow()` (deprecated in Python 3.12+)

### Type Hints
- **Required**: Full type hints for all functions and methods
```python
from typing import List, Dict, Any, Optional
from datetime import datetime

async def process_request(
    user_id: str,
    data: Dict[str, Any],
    optional_param: Optional[str] = None
) -> Dict[str, Any]:
```

### Import Organization
```python
# Standard library imports
from __future__ import annotations
import os
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

# Third-party imports
from fastapi import APIRouter, Depends
from pydantic import BaseModel

# Local imports
from ..core.auth import get_current_user
from ..services.chat_service import ChatService
```

## Service Layer Standards

### Service Class Structure
```python
class ServiceName:
    """Service description following business logic separation."""
    
    def __init__(self):
        """Initialize service with required dependencies."""
        self.logger = logging.getLogger(__name__)
    
    async def public_method(self, param: str) -> Dict[str, Any]:
        """Public interface method with full docstring."""
        pass
    
    async def _private_method(self, param: str) -> str:
        """Private helper method with underscore prefix."""
        pass
```

### Error Handling
```python
try:
    result = await operation()
    logger.info(f"✅ Operation successful: {result}")
    return result
except SpecificException as e:
    logger.error(f"❌ Specific error: {e}")
    raise HTTPException(status_code=400, detail=str(e))
except Exception as e:
    logger.error(f"❌ Unexpected error: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

## API Standards

### FastAPI Router Structure
```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter()

class RequestModel(BaseModel):
    """Request model with validation."""
    field: str
    optional_field: Optional[str] = None

@router.post("/endpoint")
async def endpoint_function(
    request: RequestModel,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Endpoint with proper documentation."""
    try:
        # Business logic
        pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## Database Standards

### Model Definitions
- Use SQLAlchemy models with proper relationships
- Include `created_at` and `updated_at` timestamps
- Use UUIDs for primary keys where appropriate

### Service Integration
```python
class DatabaseService:
    async def create_record(self, data: Dict[str, Any]) -> str:
        """Create database record with error handling."""
        try:
            # Database operation
            logger.info("✅ Record created successfully")
            return record_id
        except Exception as e:
            logger.error(f"❌ Database error: {e}")
            # Fallback to in-memory storage for resilience
            return await self._memory_fallback(data)
```

## Testing Standards

### Test File Organization
```
tests/
├── test_services/        # Service layer tests
├── test_api/            # API endpoint tests
├── test_integration/    # Integration tests
└── test_models/         # Model tests
```

### Test Naming
- `test_<functionality>_<scenario>.py`
- Example: `test_chat_service_message_processing.py`

## Documentation Standards

### Docstrings
```python
async def process_chat_request(
    self,
    user_id: str,
    message: str,
    conversation_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process chat request with AI model integration.
    
    Args:
        user_id: Unique identifier for the user
        message: User's chat message
        conversation_id: Optional existing conversation ID
        
    Returns:
        Dictionary containing response and metadata
        
    Raises:
        HTTPException: If processing fails
    """
```

### File Headers
```python
"""
Module Name - Brief Description

Detailed description of module purpose and functionality.

Key features:
- Feature 1
- Feature 2
- Feature 3

Architecture notes:
- Design pattern used
- Integration points
- Performance considerations
"""
```

## Security Standards

### Authentication
- Use proper JWT validation
- Include user context in all operations
- Validate user permissions for sensitive operations

### Data Handling
- Never log sensitive information (passwords, tokens, API keys)
- Use environment variables for configuration
- Validate all input data with Pydantic models

## Performance Standards

### Async Operations
- Use `async/await` for I/O operations
- Implement proper connection pooling
- Handle concurrent requests efficiently

### Memory Management
- Limit response sizes to prevent memory issues
- Implement pagination for large datasets
- Use generators for streaming operations

## Code Review Checklist

Before merging code, ensure:
- [ ] File size under 800 lines
- [ ] No print statements (use logging)
- [ ] Full type hints present
- [ ] Proper error handling
- [ ] Tests included
- [ ] Documentation updated
- [ ] No deprecated datetime usage
- [ ] Security considerations addressed

## Enforcement

These standards are enforced through:
1. **Pre-commit hooks** - Run linting and formatting
2. **CI/CD pipeline** - Automated testing and validation
3. **Code reviews** - Manual verification of standards compliance
4. **Regular audits** - Periodic codebase review for standards drift

## Tools

Recommended development tools:
- **Linting**: `ruff` or `flake8`
- **Formatting**: `black`
- **Type checking**: `mypy`
- **Testing**: `pytest`
- **Documentation**: `sphinx` with autodoc