# 🧪 TURFMAPP Testing Guide

Comprehensive testing guide for TURFMAPP backend following code.md standards.

## 🚀 Quick Start

### Run All Tests
```bash
cd backend
python run_tests.py
```

### Run Specific Test Categories
```bash
# Basic functionality tests
python run_tests.py basic

# API endpoint tests  
python run_tests.py api

# Utility function tests
python run_tests.py utils

# Core module tests
python run_tests.py core
```

### Run Tests with Coverage
```bash
python run_tests.py coverage
```

## 📋 Test Structure

```
backend/tests/
├── conftest.py                 # Test configuration & fixtures
├── test_simple.py             # Basic functionality tests
├── test_core/                 # Core module tests
│   ├── test_config.py         # Configuration tests
│   └── test_auth.py           # Authentication tests
├── test_api/                  # API endpoint tests  
│   └── test_v1/               # Version 1 API tests
│       ├── test_auth.py       # Auth endpoints
│       ├── test_chat.py       # Chat endpoints
│       ├── test_preferences.py # User preferences
│       └── test_upload.py     # File upload
└── test_utils/                # Utility function tests
    └── test_sessions.py       # Session management
```

## 🛠️ Available Commands

### Basic Commands
| Command | Description |
|---------|-------------|
| `python run_tests.py` | Run all tests (default) |
| `python run_tests.py basic` | Run basic functionality tests only |
| `python run_tests.py api` | Run API endpoint tests only |
| `python run_tests.py utils` | Run utility function tests only |
| `python run_tests.py core` | Run core module tests only |

### Advanced Commands
| Command | Description |
|---------|-------------|
| `python run_tests.py coverage` | Run tests with coverage report |
| `python run_tests.py fast` | Fast mode (fail on first error) |
| `python run_tests.py lint` | Run code linting and formatting |
| `python run_tests.py install` | Install test dependencies |

### Specific Tests
```bash
# Run specific test file
python run_tests.py specific tests/test_simple.py

# Run specific test class
python run_tests.py specific tests/test_api/test_v1/test_auth.py::TestAuthEndpoints

# Run specific test method
python run_tests.py specific tests/test_simple.py::TestBasicFunctionality::test_simple_math
```

## 📊 Coverage Reporting

### Generate Coverage Report
```bash
python run_tests.py coverage
```

This generates:
- Terminal coverage report
- HTML coverage report in `htmlcov/` directory

### View HTML Coverage Report
```bash
# Open in browser after running coverage
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## 🧪 Test Categories Explained

### 1. Basic Tests (`test_simple.py`)
- ✅ Environment validation
- ✅ Basic Python functionality  
- ✅ Data structure operations
- ✅ Async function testing

### 2. Core Tests (`test_core/`)
- ✅ **Configuration** (`test_config.py`): App settings, environment variables
- ✅ **Authentication** (`test_auth.py`): Supabase token verification, user auth

### 3. API Tests (`test_api/test_v1/`)
- ✅ **Auth endpoints** (`test_auth.py`): Token exchange, user authentication
- ✅ **Chat endpoints** (`test_chat.py`): Message sending, conversation management
- ✅ **Preferences** (`test_preferences.py`): User preferences CRUD operations
- ✅ **Upload endpoints** (`test_upload.py`): File upload, retrieval, deletion

### 4. Utility Tests (`test_utils/`)
- ✅ **Sessions** (`test_sessions.py`): Session management, cookie handling

## 🔧 Development Workflow

### 1. Before Making Changes
```bash
# Run tests to ensure baseline
python run_tests.py fast
```

### 2. After Making Changes
```bash
# Run relevant test category
python run_tests.py api  # If you changed API code
python run_tests.py utils  # If you changed utilities

# Run all tests with coverage
python run_tests.py coverage
```

### 3. Before Committing
```bash
# Run linting and formatting
python run_tests.py lint

# Run all tests
python run_tests.py
```

## 🎯 Coverage Goals

- **Target**: 100% test coverage as specified in requirements
- **Current Structure**: Comprehensive test suite covering:
  - All API endpoints with success/error/edge cases
  - All utility functions with various inputs
  - Core authentication and configuration logic
  - File upload/download operations
  - Session management and security

## 🛡️ Test Best Practices

### 1. Test Structure (Following code.md standards)
- **Each test**: Expected use case + Edge case + Failure case
- **Proper mocking**: External dependencies (Supabase, OpenAI)
- **Type hints**: All test functions have proper type annotations
- **Docstrings**: Google-style docstrings for all test methods

### 2. Environment Setup
- Tests automatically set `TESTING=true` environment variable
- Mock Supabase connections to avoid real API calls
- Temporary directories for file upload tests
- Isolated test data between test runs

### 3. Test Naming Convention
- `test_[function_name]_[scenario]`
- Examples:
  - `test_upload_file_success`
  - `test_get_preferences_empty`
  - `test_auth_invalid_token`

## 🐛 Debugging Failed Tests

### 1. Run Single Test with Verbose Output
```bash
python run_tests.py specific tests/test_api/test_v1/test_auth.py::TestAuthEndpoints::test_exchange_tokens_success -v
```

### 2. Run with Debug Mode
```bash
cd backend
TESTING=true python -m pytest tests/test_simple.py -v -s --tb=long
```

### 3. Check Coverage for Missing Tests
```bash
python run_tests.py coverage
# Review htmlcov/index.html for uncovered lines
```

## 📦 Dependencies

### Required Testing Packages
```bash
pip install pytest pytest-asyncio pytest-mock pytest-cov coverage black flake8
```

### Auto-Install
```bash
python run_tests.py install
```

## 🌍 Environment Variables

Tests automatically set these environment variables:
- `TESTING=true` - Prevents real database connections
- `SUPABASE_URL` - Mock Supabase URL
- `OPENAI_API_KEY` - Mock OpenAI key
- `SECRET_KEY` - Test secret key

## 🚦 Continuous Integration

### GitHub Actions (Example)
```yaml
- name: Run Tests
  run: |
    cd backend
    python run_tests.py install
    python run_tests.py coverage
```

### Pre-commit Hook (Example)
```bash
#!/bin/bash
cd backend
python run_tests.py lint && python run_tests.py fast
```

## 📈 Performance

### Fast Test Execution
- Use `python run_tests.py fast` for quick feedback
- Parallel test execution where possible
- Mock external API calls to avoid network delays
- Temporary file systems for upload tests

### Test Optimization
- Group related tests in classes
- Use fixtures for common setup
- Avoid redundant database calls
- Cache mock responses where appropriate

---

## 💡 Tips

1. **Run tests frequently** during development
2. **Use coverage reports** to identify missing tests
3. **Mock external dependencies** to keep tests fast and reliable
4. **Follow the 3-case pattern**: success + edge + failure for each function
5. **Update tests** when changing functionality

For questions about testing, refer to the code.md standards document.