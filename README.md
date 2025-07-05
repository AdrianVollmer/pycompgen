# pycompgen

Automatically generate shell completions for Python tools installed via uv and pipx.

## Installation

```bash
uv tool install pycompgen
```

## Usage

Run pycompgen to generate completions for all installed tools:

```bash
pycompgen
```

The tool will:
1. Detect packages installed via `uv tool` and `pipx`
2. Analyze which ones support shell completions
3. Generate completion files in `~/.local/share/pycompgen/`
4. Create a source script to load all completions

Add the source script to your shell config:

```bash
# Add to ~/.bashrc or ~/.zshrc
source ~/.local/share/pycompgen/source.sh
```

### Options

- `--cache-dir PATH`: Override the default cache directory
- `--force`: Force regeneration of all completions
- `--verbose`: Enable detailed output

## Development

Install development dependencies:

```bash
uv sync --group dev
```

Run tests:

```bash
uv run pytest
```

Run linting and formatting:

```bash
uv run ruff check src tests
uv run ruff format src tests
uv run mypy src
```