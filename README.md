# BioX

BioX is a modern, production-grade Python package scaffold for reproducible bioinformatics tooling.

## Features

- src/ layout with Hatch builds
- Typed code (mypy), linted and formatted with Ruff
- Pytest + Coverage configuration
- Pre-commit hooks
- GitHub Actions CI for tests, lint, type-checking
- Trusted publishing to PyPI via OIDC (no secrets required)

## Installation

```bash
pip install biox
```

## Usage

```python
from biox import hello
print(hello())
```

## Development

- Python >= 3.9
- Create venv, then:

```bash
pip install -U pip
pip install -e .[dev]
pre-commit install
pytest
```

## Releasing

1. Update `CHANGELOG.md` and bump `__version__` in `src/biox/__init__.py`.
2. Create a git tag like `v0.1.0` and push.
3. GitHub Actions will build and publish to PyPI using trusted publishing.

## License

MIT
