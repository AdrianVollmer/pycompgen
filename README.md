# pycompgen

Automatically generate shell completions for Python tools installed via
uv and pipx.

Currently, only zsh and bash on Linux are supported. Also, only Python
tools that use the `click` or `argcomplete` libraries are supported,
besides some select commands:

- uv
- uvx

## Installation

``` bash
uv tool install pycompgen
# Or if you prefer pipx:
pipx install pycompgen
```

## Usage

Run pycompgen to generate completions for all installed tools:

``` bash
pycompgen
```

The tool will:

1.  Detect Python packages installed via `uv tool` and `pipx` as well as
    some select commands
2.  Analyze which ones support shell completions
3.  Generate completion files in `~/.cache/pycompgen/`
4.  Create a source script to load all completions

Add the source script to your shell config:

``` bash
# Add to ~/.bashrc or ~/.zshrc
source <(pycompgen --source) ; (pycompgen &)
```

This will load the generated shell completions and generate new
completions for the next time.

### Options

- `--cache-dir PATH`: Override the default cache directory
- `--force`: Force regeneration of all completions
- `--shell`: Target shell (default: ${SHELL:-bash})
- `--verbose`: Enable detailed output
- `--source`: Only write the source file contents to stdout and exit
- `--cooldown-time`: Minimum amount of seconds between regenerations

## Development

Install development dependencies:

``` bash
uv sync --group dev
uv run pre-commit install
```

Run tests:

``` bash
uv run pytest
```

Run linting and formatting:

``` bash
uv run ruff check src tests
uv run ruff format src tests
uv run mypy src
```

## License

MIT
