# Contributing to SGraph MCP Server

All contributions are welcome: bug reports, feature ideas, documentation improvements, and code.

## Getting Started

```bash
# Clone and install
git clone https://github.com/softagram/sgraph-mcp-server.git
cd sgraph-mcp-server
uv sync
```

## Development Workflow

1. Create a branch from `main`
2. Make your changes
3. Run tests and lint:
   ```bash
   uv run python -m pytest tests/unit/ tests/integration/ -v
   uv run ruff check src/
   ```
4. Commit with a descriptive message
5. Open a pull request against `main`

## Code Style

- **Linter**: [Ruff](https://docs.astral.sh/ruff/) (line length 100, Python 3.13)
- Run `uv run ruff check src/` before committing
- Follow existing patterns in the codebase

## Tests

| Category | Location | Purpose |
|----------|----------|---------|
| Unit | `tests/unit/` | Component isolation with mocks |
| Integration | `tests/integration/` | End-to-end with real sgraph models |
| Performance | `tests/performance/` | Validates latency targets |

Test models are in `sgraph-example-models/` and `tests/`.

Write tests for new features. For bug fixes, add a test that reproduces the bug first.

## Project Structure

```
src/
  core/          -- Model management, data conversion
  services/      -- Business logic (search, deps, overview, security)
  tools/         -- MCP tool definitions (legacy profile)
  profiles/      -- Profile implementations (claude-code, legacy)
  utils/         -- Validators, logging
tests/
  unit/          -- Fast, isolated tests
  integration/   -- Real model tests
  performance/   -- Latency benchmarks
```

## Reporting Bugs

Open an issue with:
- What you expected to happen
- What actually happened
- Steps to reproduce
- sgraph model info if relevant (language, approximate element count)

## Questions?

Open a [GitHub issue](https://github.com/softagram/sgraph-mcp-server/issues) or start a discussion.
