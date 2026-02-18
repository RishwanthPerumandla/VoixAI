# Contributing to VoixAI

Thank you for your interest in contributing to VoixAI. This document provides guidelines and instructions for contributing.

## Development Setup

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/yourusername/voixai.git
   cd voixai
   ```

3. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

4. Install dependencies:
   ```bash
   pip install torch==2.4.0+cpu --index-url https://download.pytorch.org/whl/cpu
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

5. Create `.env` file with your API keys

## Code Style

- Follow PEP 8 style guidelines
- Use type hints where appropriate
- Write docstrings for all public functions and classes
- Maximum line length: 100 characters

## Testing

Run tests before submitting:

```bash
pytest tests/ -v
```

## Pull Request Process

1. Create a new branch for your feature:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and commit them:
   ```bash
   git commit -m "Add feature: description"
   ```

3. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

4. Create a Pull Request with:
   - Clear description of changes
   - Reference to any related issues
   - Test results

## Code Review

All submissions require review. Please ensure:
- Tests pass
- Code is properly formatted (black)
- Linting passes (flake8)
- Documentation is updated

## Reporting Issues

When reporting issues, please include:
- Description of the problem
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment details (OS, Python version)
- Relevant logs

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
