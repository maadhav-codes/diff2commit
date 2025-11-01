# diff2commit

🤖 An AI-powered Git commit message generator that creates clear, descriptive commit messages following the Conventional Commits specification.

## Features

- **AI-Powered Generation**: Leverages GPT-4, Claude, or Gemini to analyze your changes and generate meaningful commit messages.
- **Conventional Commits**: Automatically formats messages according to the Conventional Commits specification.
- **Interactive Review**: Review, edit, and approve messages before committing.
- **Multiple AI Providers**: Support for OpenAI, and Google Gemini.
- **Cost Tracking**: Monitor token usage and API costs.
- **Customizable**: Configure models, prompts, and message formats.
- **Beautiful CLI**: Rich terminal UI with syntax highlighting.

## Installation

### From PyPI (Recommended)

```bash
pip install diff2commit
```

### From Source

```bash
git clone https://github.com/maadhav-codes/diff2commit.git
cd diff2commit
pip install -e .
```

### Using pipx (Isolated Installation)

```bash
pipx install diff2commit
```

## Quick Start

1. **Set your API key**:

```bash
export D2C_API_KEY='your-openai-api-key'
```

2. **Stage your changes**:

```bash
git add .
```

3. **Generate and commit**:

```bash
diff2commit generate
```

## Usage

### Generate Commit Message

```bash
# Generate with interactive review
diff2commit generate

# Generate multiple suggestions
diff2commit generate --count 3

# Use a different AI provider
diff2commit generate --provider gemini

# Use specific model
diff2commit generate --model gpt-4-turbo

# Skip interactive review
diff2commit generate --no-review

# Generate without committing
diff2commit generate --no-commit
```

### View Usage Statistics

```bash
# Total usage
diff2commit usage

# Current month usage
diff2commit usage --monthly

# Usage by provider
diff2commit usage --by-provider
```

### View Configuration

```bash
diff2commit config
```

### Version Information

```bash
diff2commit version
```

## Configuration

### Environment Variables

Create a `.env` file in your project or set environment variables:

```bash
# Required
D2C_API_KEY=your-api-key-here

# Optional
D2C_AI_PROVIDER=openai          # openai, or gemini
D2C_AI_MODEL=gpt-4              # Model name
D2C_MAX_TOKENS=200           # Max tokens for generation
D2C_TEMPERATURE=0.7          # Sampling temperature (0.0-2.0)
D2C_COMMIT_FORMAT=conventional
D2C_INCLUDE_EMOJI=false
D2C_MAX_SUBJECT_LENGTH=72
D2C_TRACK_USAGE=true
```

### Configuration File

Create `~/.config/diff2commit/config.toml`:

```toml
ai_provider = "openai"
ai_model = "gpt-4"
max_tokens = 200
temperature = 0.7
commit_format = "conventional"
include_emoji = false
max_subject_length = 72
track_usage = true
```

## Conventional Commits Format

The tool generates messages following the Conventional Commits specification:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation changes
- `style`: Formatting changes
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or modifying tests
- `build`: Build system changes
- `ci`: CI configuration changes
- `chore`: Other changes

## AI Providers

### OpenAI (GPT-4)

```bash
export D2C_API_KEY='sk-...'
export D2C_AI_PROVIDER='openai'
export D2C_AI_MODEL='gpt-4'
```

### Google Gemini

```bash
export D2C_API_KEY='AI...'
export D2C_AI_PROVIDER='gemini'
export D2C_AI_MODEL='gemini-pro'
```

## Cost Management

Track and manage API costs:

```bash
# View total costs
diff2commit usage

# View monthly costs
diff2commit usage --monthly

# Set monthly limit (in config)
D2C_COST_LIMIT_MONTHLY=10.0
```

## Development

### Setup Development Environment

```bash
git clone https://github.com/maadhav-codes/diff2commit.git
cd diff2commit
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest tests/
```

### Linting

```bash
ruff check .
black --check .
mypy src/
```

### Format Code

```bash
black .
ruff check --fix .
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Built with [Typer](https://typer.tiangolo.com/) for CLI
- [Rich](https://rich.readthedocs.io/) for beautiful terminal output
- [GitPython](https://gitpython.readthedocs.io/) for Git operations
- Inspired by the [Conventional Commits](https://www.conventionalcommits.org/) specification

## Support

- 📖 [Documentation](https://github.com/maadhav-codes/diff2commit#readme)
- 🐛 [Issue Tracker](https://github.com/maadhav-codes/diff2commit/issues)
- 💬 [Discussions](https://github.com/maadhav-codes/diff2commit/discussions)

---

Made with ❤️ by maadhav-codes
