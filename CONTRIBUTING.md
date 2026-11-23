# Contributing to djinsight

Thank you for your interest in contributing to djinsight! This document provides guidelines and instructions for contributing to the project.

## Development Setup

### Prerequisites

- Python 3.9 or higher
- Redis server
- Git

### Setting up the Development Environment

1. **Clone the repository:**
   ```bash
   git clone https://github.com/krystianmagdziarz/djinsight.git
   cd djinsight
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install development dependencies:**
   ```bash
   pip install -e .[dev]
   ```

4. **Install Redis:**
   - **macOS:** `brew install redis`
   - **Ubuntu:** `sudo apt-get install redis-server`
   - **Windows:** Download from [Redis website](https://redis.io/download)

5. **Start Redis:**
   ```bash
   redis-server
   ```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=djinsight

# Run specific test file
pytest djinsight/tests/test_models.py

# Run with verbose output
pytest -v
```

### Code Quality

We use several tools to maintain code quality:

```bash
# Format code with Black
black djinsight/

# Sort imports with isort
isort djinsight/

# Lint with flake8
flake8 djinsight/

# Type checking with mypy
mypy djinsight/

# Run all quality checks
black djinsight/ && isort djinsight/ && flake8 djinsight/ && mypy djinsight/
```

### Building the Package

```bash
# Build source and wheel distributions
python -m build

# Check the package
twine check dist/*

# Install locally for testing
pip install -e .
```

## Contributing Guidelines

### Code Style

- Follow PEP 8 style guidelines
- Use Black for code formatting (line length: 88)
- Use isort for import sorting
- Add type hints where appropriate
- Write docstrings for all public functions and classes

### Commit Messages

Use clear and descriptive commit messages:

```
feat: add new template tag for analytics widget
fix: resolve Redis connection timeout issue
docs: update installation instructions
test: add tests for PageViewLog model
refactor: improve error handling in views
```

### Pull Request Process

1. **Fork the repository** and create a new branch from `main`
2. **Make your changes** following the code style guidelines
3. **Add tests** for new functionality
4. **Update documentation** if needed
5. **Run the test suite** and ensure all tests pass
6. **Run code quality checks** and fix any issues
7. **Submit a pull request** with a clear description

### Branch Naming

Use descriptive branch names:
- `feature/add-chart-widgets`
- `fix/redis-connection-timeout`
- `docs/update-readme`
- `test/add-view-tests`

## Testing

### Test Structure

Tests are organized in the `djinsight/tests/` directory:

```
djinsight/tests/
├── __init__.py
├── test_models.py
├── test_views.py
├── test_templatetags.py
├── test_tasks.py
└── test_admin.py
```

### Writing Tests

- Use Django's TestCase for database-related tests
- Use pytest fixtures for reusable test data
- Mock external dependencies (Redis, Celery)
- Test both success and error cases
- Aim for high test coverage

### Test Examples

```python
from django.test import TestCase
from djinsight.models import PageViewLog

class PageViewLogTest(TestCase):
    def test_create_page_view_log(self):
        log = PageViewLog.objects.create(
            page_id=1,
            content_type="tests.testpage",
            url="/test-page/"
        )
        self.assertEqual(log.page_id, 1)
```

## Documentation

### Updating Documentation

- Update README.md for user-facing changes
- Update docstrings for code changes
- Add examples for new features
- Update CHANGELOG.md for all changes

### Documentation Style

- Use clear, concise language
- Provide code examples
- Include configuration options
- Document all parameters and return values

## Release Process

### Release Steps

1. **Update version numbers** in:
   - `pyproject.toml`
   - `djinsight/__init__.py`

2. **Update CHANGELOG.md** with new version

3. **Create a git tag:**
   ```bash
   git tag -a v1.0.0 -m "Release version 1.0.0"
   git push origin v1.0.0
   ```

4. **Build and upload to PyPI:**
   ```bash
   python -m build
   twine upload dist/*
   ```

## Issue Reporting

### Bug Reports

When reporting bugs, please include:
- Python version
- Django version
- Wagtail version
- Redis version
- Steps to reproduce
- Expected behavior
- Actual behavior
- Error messages/stack traces

### Feature Requests

For feature requests, please provide:
- Clear description of the feature
- Use case and motivation
- Proposed implementation (if any)
- Potential impact on existing functionality

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on constructive feedback
- Respect different viewpoints and experiences

### Unacceptable Behavior

- Harassment or discrimination
- Trolling or insulting comments
- Personal attacks
- Publishing private information

## Getting Help

- **Documentation:** [Read the docs](https://djinsight.readthedocs.io/)
- **Issues:** [GitHub Issues](https://github.com/yourusername/djinsight/issues)
- **Discussions:** [GitHub Discussions](https://github.com/yourusername/djinsight/discussions)

## Recognition

Contributors will be recognized in:
- CHANGELOG.md
- README.md contributors section
- Release notes

Thank you for contributing to djinsight! 