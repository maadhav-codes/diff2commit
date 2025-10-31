# Contributing to diff2commit CLI

Thank you for your interest in contributing to diff2commitCLI! This document provides guidelines and instructions for contributing.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct. Please be respectful and constructive in your interactions.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/maadhav-codes/diff2commit/issues)
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version, etc.)
   - Relevant logs or screenshots

### Suggesting Features

1. Check existing [Issues](https://github.com/maadhav-codes/diff2commit/issues) and [Discussions](https://github.com/maadhav-codes/diff2commit/discussions)
2. Create a new issue or discussion with:
   - Clear description of the feature
   - Use cases and benefits
   - Potential implementation approach

### Pull Requests

1. **Fork the repository** and create a new branch:

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Set up development environment**:

   ```bash
   pip install -e ".[dev]"
   ```

3. **Make your changes**:

   - Write clean, readable code
   - Follow existing code style
   - Add tests for new functionality
   - Update documentation as needed

4. **Run tests and linting**:

   ```bash
   pytest tests/
   ruff check .
   black .
   mypy src/diff2commit
   ```

5. **Commit your changes**:

   - Use Conventional Commits format
   - Write clear, descriptive commit messages
   - You can use diff2commit itself!

6. **Push and create PR**:
   ```bash
   git push origin feature/your-feature-name
   ```
   - Open a pull request on GitHub
   - Describe your changes clearly
   - Link any related issues

## Development Guidelines

### Code Style

- Follow PEP 8 style guide
- Use Black for code formatting
- Use Ruff for linting
- Use type hints (mypy)
- Maximum line length: 100 characters

### Testing

- Write tests for all new features
- Maintain or improve code coverage
- Use pytest for testing
- Include both unit and integration tests

### Documentation

- Update README.md for user-facing changes
- Add docstrings to all functions and classes
- Update CHANGELOG.md
- Include code examples where appropriate

### Commit Messages

Follow Conventional Commits:

```
<type>[optional scope]: <description>

[optional body]

[optional footer]
```

Types:

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Test changes
- `build`: Build system changes
- `ci`: CI changes
- `chore`: Other changes

## Project Structure

```
diff2commit/
├── src/diff2commit/         # Main package
│   ├── ai_providers/      # AI provider implementations
│   ├── ui/                # User interface components
│   ├── cli.py             # CLI entry point
│   ├── config.py          # Configuration management
│   └── git_operations.py  # Git operations
├── tests/                 # Test suite
└── pyproject.toml         # Project configuration
```

## Getting Help

- Join discussions on [GitHub Discussions](https://github.com/maadhav-codes/diff2commit/discussions)
- Check [Documentation](https://github.com/maadhav-codes/diff2commit#readme)
- Open an issue for bugs or feature requests

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

Thank you for contributing! 🎉
