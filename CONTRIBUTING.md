# Contributing to RTL-Gen AI

Thank you for considering contributing to RTL-Gen AI! 🎉

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [How Can I Contribute?](#how-can-i-contribute)
3. [Development Setup](#development-setup)
4. [Coding Standards](#coding-standards)
5. [Testing Guidelines](#testing-guidelines)
6. [Pull Request Process](#pull-request-process)
7. [Issue Guidelines](#issue-guidelines)

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors.

### Our Standards

**Positive behavior includes**:
- Being respectful and considerate
- Accepting constructive criticism gracefully
- Focusing on what's best for the community
- Showing empathy towards others

**Unacceptable behavior includes**:
- Harassment or discriminatory language
- Personal attacks or trolling
- Publishing others' private information
- Any conduct that could be considered inappropriate

---

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues. When creating a bug report, include:

- **Clear title and description**
- **Steps to reproduce**
- **Expected vs actual behavior**
- **Screenshots** (if applicable)
- **Environment details**:
  - OS and version
  - Python version
  - RTL-Gen AI version
  - Error messages/logs

**Bug Report Template**:
```markdown
**Description**
A clear description of the bug.

**To Reproduce**
Steps to reproduce:
1. Go to '...'
2. Click on '...'
3. See error

**Expected Behavior**
What you expected to happen.

**Screenshots**
If applicable, add screenshots.

**Environment**
- OS: [e.g., Windows 11, Ubuntu 22.04]
- Python: [e.g., 3.11.0]
- RTL-Gen AI: [e.g., 1.0.0]

**Additional Context**
Any other relevant information.
```

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. Include:

- **Clear title and description**
- **Motivation**: Why is this enhancement needed?
- **Proposed solution**
- **Alternatives considered**
- **Examples**: How would it work?

### Contributing Code

We welcome code contributions! Areas that need help:

- 🐛 **Bug Fixes**: Check "good first issue" label
- ✨ **Features**: See roadmap in CHANGELOG.md
- 📚 **Documentation**: Improve clarity and examples
- 🧪 **Tests**: Increase coverage
- ⚡ **Performance**: Optimize bottlenecks

---

## Development Setup

### Prerequisites

- Python 3.9+
- Git
- Icarus Verilog (for verification)

### Setup Steps

```bash
# 1. Fork the repository on GitHub

# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/rtl-gen-ai.git
cd rtl-gen-ai

# 3. Add upstream remote
git remote add upstream https://github.com/original/rtl-gen-ai.git

# 4. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# 5. Install dependencies
pip install -r requirements.txt

# 6. Install development dependencies
pip install pytest pytest-cov black pylint

# 7. Install in development mode
pip install -e .

# 8. Configure
cp .env.example .env
# Edit .env with your API key (or use mock)

# 9. Run tests
pytest tests/ -v

# 10. Start development server
streamlit run app.py
```

### Project Structure

```
rtl-gen-ai/
├── python/              # Core modules
│   ├── input_processor.py
│   ├── llm_client.py
│   ├── verification_engine.py
│   └── ...
├── tests/               # Test suite
├── templates/           # Prompt templates
├── examples/            # Example designs
├── scripts/             # Utility scripts
├── docs/                # Documentation
├── app.py              # Web interface
└── README.md
```

---

## Coding Standards

### Python Style

We follow **PEP 8** with some modifications:

```python
# Good
def generate_code(description: str) -> Dict[str, Any]:
    """
    Generate RTL code from description.
    
    Args:
        description: Natural language design description
        
    Returns:
        dict: Generation result with code and metadata
    """
    result = {}
    # Implementation
    return result

# Bad
def gen(d):
    r={}
    return r
```

**Key points**:
- Use type hints for all function parameters and returns
- Write docstrings for all public functions/classes
- Maximum line length: 100 characters
- Use 4 spaces for indentation (no tabs)
- Use meaningful variable names
- Add comments for complex logic

### Code Formatting

We use **Black** for automatic formatting:

```bash
# Format all Python files
black python/ tests/

# Check formatting
black --check python/ tests/
```

### Linting

We use **pylint** for code quality:

```bash
# Run pylint
pylint python/

# Ignore specific warnings (if justified)
# pylint: disable=line-too-long
```

### Import Organization

```python
# Standard library imports
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Third-party imports
import anthropic
import streamlit as st
from tenacity import retry

# Local imports
from python.config import *
from python.llm_client import LLMClient
```

---

## Testing Guidelines

### Writing Tests

Every new feature should include tests:

```python
# tests/test_my_feature.py
import pytest
from python.my_module import MyClass


class TestMyClass:
    """Test MyClass functionality."""
    
    def test_basic_functionality(self):
        """Test basic operation."""
        obj = MyClass()
        result = obj.do_something()
        
        assert result is not None
        assert result['success'] is True
    
    def test_error_handling(self):
        """Test error handling."""
        obj = MyClass()
        
        with pytest.raises(ValueError):
            obj.do_something(invalid_input="bad")
    
    def test_edge_cases(self):
        """Test edge cases."""
        obj = MyClass()
        
        # Empty input
        result = obj.do_something("")
        assert result is not None
        
        # Very large input
        large_input = "x" * 10000
        result = obj.do_something(large_input)
        assert result is not None
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_my_feature.py -v

# Run with coverage
pytest tests/ --cov=python --cov-report=html

# Run specific test
pytest tests/test_my_feature.py::TestMyClass::test_basic_functionality -v
```

### Test Coverage

Maintain **>80% code coverage**:

```bash
# Generate coverage report
pytest tests/ --cov=python --cov-report=term-missing

# View HTML report
open htmlcov/index.html
```

---

## Pull Request Process

### Before Submitting

1. **Update from upstream**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Create feature branch**:
   ```bash
   git checkout -b feature/my-feature
   ```

3. **Make changes** with clear commits:
   ```bash
   git add .
   git commit -m "Add feature: description
   
   - Detailed change 1
   - Detailed change 2
   - Fixes #123"
   ```

4. **Run tests**:
   ```bash
   pytest tests/ -v
   black python/ tests/
   pylint python/
   ```

5. **Push to your fork**:
   ```bash
   git push origin feature/my-feature
   ```

### Submitting PR

1. Go to GitHub and create Pull Request
2. Fill out PR template completely
3. Link related issues
4. Wait for review

### PR Template

```markdown
## Description
Brief description of changes.

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Related Issues
Fixes #123

## Testing
- [ ] Tests added/updated
- [ ] All tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] No new warnings generated
```

### Review Process

1. **Automated checks** must pass:
   - Tests
   - Code formatting
   - Linting

2. **Code review** by maintainer

3. **Address feedback**:
   ```bash
   # Make changes
   git add .
   git commit -m "Address review feedback"
   git push origin feature/my-feature
   ```

4. **Merge** after approval

---

## Issue Guidelines

### Creating Issues

Use appropriate labels:
- `bug`: Something isn't working
- `enhancement`: New feature request
- `documentation`: Documentation improvements
- `good first issue`: Good for newcomers
- `help wanted`: Extra attention needed

### Issue Lifecycle

1. **Open**: Issue created
2. **Triaged**: Reviewed by maintainer
3. **In Progress**: Someone working on it
4. **Review**: PR submitted
5. **Closed**: Completed or won't fix

---

## Communication

### Getting Help

- **GitHub Issues**: For bugs and features
- **Discussions**: For questions and ideas
- **Email**: support@rtl-gen-ai.com

### Response Times

We aim to respond to:
- **Critical bugs**: Within 24 hours
- **Other issues**: Within 1 week
- **Pull requests**: Within 1 week

---

## Recognition

Contributors are recognized in:
- CHANGELOG.md
- README.md contributors section
- Release notes

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing to RTL-Gen AI! 🚀**
