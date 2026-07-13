# Contributing to behave-priority

Thank you for your interest in contributing to `behave-priority`! This document outlines the process for contributing to the project.

## Getting started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/<your-username>/behave-priority.git`
3. Install in development mode: `pip install -e ".[dev]"`
4. Create a branch: `git checkout -b my-feature`

## Development workflow

### Code style

- **Linter**: `ruff check behave_priority/ tests/` — must pass with no errors
- **Type checker**: `mypy --strict behave_priority/` — must pass with no errors
- **Line length**: 100 characters
- **Python version**: 3.11+ (use `from __future__ import annotations` for forward refs)
- **Imports**: Sorted with `ruff` (isort rules enabled)

### Testing

- All new code must have unit tests
- Integration tests run behave subprocesses — keep them fast and isolated
- Run the full suite before pushing:

```bash
pytest
```

- Check coverage:

```bash
pytest --cov=behave_priority --cov-report=term-missing
```

Coverage must stay >= 90%.

### Type safety

- All public APIs must have type hints
- `mypy --strict` must pass — no `Any` without justification, no untyped functions
- Use `Protocol` for structural typing (see `sorter.py` for examples)

### Design principles

- **Minimal intrusion**: Intercept behave's runner, don't replace it
- **Zero required dependencies**: Only `behave`
- **Programmatic configuration**: No CLI flags. All config via `setup_priority()` kwargs
- **Fail-safe**: If behave-priority misconfigures, fall back to behave's default behavior
- **Immutable config**: `PriorityConfig` is a frozen dataclass — never mutate after creation

## Pull request process

1. **Create an issue first** for new features or breaking changes — discuss before implementing
2. **Write tests** for your changes — unit tests for logic, integration tests for behave interaction
3. **Run all checks**:

   ```bash
   ruff check behave_priority/ tests/
   mypy --strict behave_priority/
   pytest
   ```

4. **Keep PRs focused** — one feature or fix per PR
5. **Update documentation** if your change affects the public API
6. **Use conventional commit messages**:

   - `feat: add stop_on_critical option`
   - `fix: preserve feature boundaries in sorter`
   - `docs: update README with API table`
   - `test: add integration tests for fail-fast`
   - `refactor: simplify check_fail_fast logic`

7. **Fill out the PR template** — all sections must be completed

## Project structure

```text
behave_priority/          # Source code
├── __init__.py           # Public exports
├── exceptions.py         # PriorityError, StopExecutionError, PriorityParseError
├── config.py             # PriorityConfig (frozen dataclass)
├── parser.py             # Tag priority parsing
├── queue.py              # PriorityQueue (thread-safe, heapq-based)
├── sorter.py             # ScenarioSorter
├── hooks.py              # setup_priority, hook functions, PriorityState
└── report.py             # PriorityReport, ReportEntry, ReportSummary

tests/
├── unit/                 # Unit tests (fakes for behave objects)
└── integration/          # Integration tests (subprocess behave runs)

ref/                      # Reference documents (not shipped)
├── project.md            # Project overview
├── design.md             # Design document
└── fases.md              # Development phases
```

## Reporting bugs

Use the bug report issue template. Include:

- Python version
- Behave version
- behave-priority version
- Minimal reproduction (feature file + environment.py)
- Expected vs actual behavior

## Suggesting features

Use the feature request issue template. Explain:

- The use case
- How it fits the design principles
- Whether it requires new dependencies

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
