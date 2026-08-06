---
description: "General testing guidelines for the project"
applyTo: "**/*test*.py, **/tests/**/*.py"
---

# Testing Guidelines

## Overview

This project uses **pytest** as the testing framework. All tests should be isolated unit tests that mock external dependencies.

## Test Structure

### File Organization
- Place tests in a `tests/` directory at the project root
- Mirror the source directory structure: `src/xyh/module.py` → `tests/test_module.py`
- Name test files with the `test_` prefix

### Test Naming
- Use descriptive names: `test_<function>_<scenario>_<expected_result>`
- Example: `test_create_xyh_analysis_valid_parameters_returns_instance()`
- Example: `test_settings_missing_config_file_raises_error()`

## Writing Tests

### Imports
```python
import pytest
from unittest.mock import Mock, patch, MagicMock
```

### Fixtures
Use fixtures for common setup:
```python
@pytest.fixture
def mock_order_analysis():
    with patch('order.Analysis') as mock:
        yield mock

@pytest.fixture
def sample_config():
    return {
        "key": "value",
        "nested": {"foo": "bar"}
    }
```

### Parametrization
Use parametrization for testing multiple cases:
```python
@pytest.mark.parametrize("m_x,m_y", [
    (300, 60),
    (400, 100),
    (500, 150),
])
def test_masses(m_x, m_y):
    assert validate_masses(m_x, m_y) is True
```

### Assertions
- Use simple `assert` statements
- Add custom error messages for clarity: `assert result == expected, f"Expected {expected}, got {result}"`
- Use `pytest.approx()` for floating point comparisons

## Mocking Guidelines

### What to Mock
- ALL imports from other project submodules
- External services and APIs
- File system operations
- Database connections
- The `order` library (use Mock objects)

### What NOT to Mock
- Standard library functions (unless they perform I/O)
- The module under test itself
- Pure functions with no side effects

### Mock Patterns
```python
# Using patch decorator
@patch('xyh.module.ExternalClass')
def test_something(mock_external):
    mock_external.return_value.method.return_value = "mocked"

# Using context manager
def test_with_context_manager():
    with patch('xyh.module.function') as mock_func:
        mock_func.return_value = 42
        # test code

# Using fixture
def test_with_fixture(mock_dependency):
    mock_dependency.method.return_value = "result"
```

## Test Categories

### Unit Tests (Default)
- Test single functions or classes in isolation
- Fast execution (<1ms per test)
- No external dependencies

### Integration Tests (If Needed)
- Mark with `@pytest.mark.integration`
- Test interactions between modules
- Can use real (but test-specific) resources

### Slow Tests
- Mark with `@pytest.mark.slow`
- Skip by default: `pytest -m "not slow"`
- Run explicitly when needed: `pytest -m slow`

## Running Tests

### Basic Commands
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_analysis.py

# Run specific test function
pytest tests/test_analysis.py::test_create_xyh_analysis

# Run with coverage
pytest --cov=src/xyh

# Run excluding slow tests
pytest -m "not slow"

# Run only integration tests
pytest -m integration
```

### Pixi Integration
```bash
# Install dev dependencies including pytest
pixi run install-dev

# Run tests via pixi task (if configured)
pixi run test
```

## Code Coverage

Aim for high coverage but prioritize meaningful tests:
- **Target**: >80% line coverage
- **Focus**: Critical paths and edge cases
- **Tool**: `pytest-cov`

Generate coverage report:
```bash
pytest --cov=src/xyh --cov-report=html
```

## Continuous Integration

Tests run automatically on:
- Every push to main branch
- Every pull request
- Scheduled nightly runs

See `.github/workflows/tests.yml` for configuration.

## Best Practices

1. **Keep tests independent** - No shared state between tests
2. **Test behavior, not implementation** - Focus on what, not how
3. **Use descriptive test names** - Should read like documentation
4. **Arrange-Act-Assert pattern** - Structure tests clearly
5. **One assertion per concept** - Multiple related assertions OK
6. **Clean up resources** - Use fixtures with teardown
7. **Document edge cases** - Explain why a test exists
