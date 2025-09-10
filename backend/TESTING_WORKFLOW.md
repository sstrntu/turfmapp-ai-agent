# 🧪 Testing Workflow - Prevent Regressions

## Before Adding Any New Feature or Refactoring

### 1. **Run Regression Tests First**
```bash
# Run this BEFORE making any changes
./run_tests.sh

# Or just the critical regression tests
python -m pytest tests/test_regression_critical_flows.py -v
```

### 2. **Create Tests for Your New Feature**
```bash
# Create a new test file for your feature
cp tests/test_template.py tests/test_your_new_feature.py
```

### 3. **Follow TDD (Test-Driven Development)**
1. Write failing tests for your new feature first
2. Write the minimum code to make tests pass
3. Refactor while keeping tests green

### 4. **Run Full Test Suite**
```bash
# After making changes, run full suite
python -m pytest tests/ --cov=app --cov-report=term-missing -v
```

## During Development

### Continuous Testing
```bash
# Install pytest-watch for continuous testing
pip install pytest-watch

# Run tests automatically when files change
ptw -- tests/test_your_feature.py -v
```

### Check Coverage
```bash
# Ensure your new code is tested
python -m pytest tests/test_your_feature.py --cov=app/services/your_service --cov-report=term-missing
```

## Before Committing

### Pre-commit Checklist
- [ ] All existing tests still pass
- [ ] New feature has tests (aim for >90% coverage)  
- [ ] Regression tests still pass
- [ ] Code follows existing patterns
- [ ] No hardcoded values or secrets

### Install Pre-commit Hooks
```bash
pip install pre-commit
pre-commit install
```

## Before Deployment

### Final Safety Checks
```bash
# 1. Run complete test suite
./run_tests.sh

# 2. Build Docker image (this runs tests too)
docker build -t turfmapp-backend .

# 3. Test the built image
docker run --rm turfmapp-backend python -m pytest tests/test_regression_critical_flows.py
```

## When Tests Fail

### Debugging Failed Tests
```bash
# Run with detailed output
python -m pytest tests/failing_test.py -v -s --tb=long

# Run specific test
python -m pytest tests/test_file.py::TestClass::test_method -v -s
```

### Common Causes of Regressions
1. **Changed function signatures** - Update all callers
2. **Modified return values** - Update tests expecting old format
3. **New dependencies** - Mock them in tests
4. **Environment changes** - Update test environment setup
5. **Database schema changes** - Update test data

## Test Categories

### 🔴 **Critical Tests** (MUST NEVER FAIL)
- `test_regression_critical_flows.py` - Core user workflows
- Health checks and basic API functionality
- User authentication and security

### 🟡 **Integration Tests** (Test interactions between services)
- `test_google_mcp_integration.py`
- `test_integration/`
- API endpoint tests

### 🟢 **Unit Tests** (Test individual components)
- `test_enhanced_chat_service_fixed.py`
- `test_tool_manager.py`
- `test_mcp_client_simple.py`

## Quick Commands Reference

```bash
# Before you start work
./run_tests.sh

# During development
ptw -- tests/test_your_feature.py -v

# Before committing
python -m pytest tests/test_regression_critical_flows.py

# Before deployment
docker build -t test-build . && echo "✅ Build with tests passed"
```

## Anti-Regression Principles

1. **Never skip tests** - If they're slow, make them faster, don't skip
2. **Test public APIs** - Focus on interfaces that other code depends on
3. **Mock external dependencies** - Don't let external services break your tests
4. **Use descriptive test names** - Know what broke just from the test name
5. **Keep tests simple** - Complex tests are hard to debug when they fail

## Emergency: Rollback Strategy

If you accidentally break something:

```bash
# 1. Revert your changes
git revert <commit-hash>

# 2. Run regression tests to confirm fix
python -m pytest tests/test_regression_critical_flows.py

# 3. Create fix with proper tests
# ... fix the issue ...

# 4. Verify fix
./run_tests.sh
```

Remember: **It's better to deploy slowly with confidence than quickly with bugs!** 🚀