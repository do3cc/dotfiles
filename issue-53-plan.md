# Implementation Plan: Issue #53

**Add comprehensive unit tests with pytest, hypothesis, and faker**

## Issue Summary

Add comprehensive unit testing infrastructure to the dotfiles repository using modern Python testing tools (pytest, hypothesis, and faker). This will provide robust test coverage for all Python tools and shared modules, with property-based testing for edge cases and integration tests for CLI entry points.

## Requirements Analysis

Based on the GitHub issue, the implementation requires:

1. **Testing Framework Setup**
   - pytest as the core testing framework
   - hypothesis for property-based testing
   - faker for generating realistic test data

2. **Test Coverage Scope**
   - All Python tools: `dotfiles-init`, `dotfiles-swman`, `dotfiles-pkgstatus`, `dotfiles-status`
   - Shared modules: `logging_config.py`, `output_formatting.py`

3. **Test Types**
   - Unit tests for individual functions and classes
   - Property-based tests for input validation, edge cases, and invariants
   - Integration tests for CLI entry points
   - Mocking for external dependencies (subprocess, filesystem, GitHub API)

4. **Success Criteria**
   - > 80% test coverage for all Python modules
   - Tests pass on all supported platforms (Arch, Debian, Ubuntu)
   - Property-based tests validate critical invariants
   - CI/CD integration with GitHub Actions
   - Clear test documentation

## Current State Analysis

### Project Structure

The dotfiles repository has the following Python structure:

```
src/dotfiles/
├── __init__.py
├── init.py              # dotfiles-init entry point
├── swman.py             # dotfiles-swman entry point
├── pkgstatus.py         # dotfiles-pkgstatus entry point
├── project_status.py    # dotfiles-status entry point
├── logging_config.py    # Shared logging with structlog
└── output_formatting.py # Rich-based console output
```

### Existing Test Infrastructure

- **No tests directory exists** for the main dotfiles package
- A separate `calendar-sync/` project exists with basic pytest tests (test_cli.py)
- The calendar-sync example shows the project can support pytest

### Current Testing Approach

- **Makefile test targets** focus on integration testing:
  - `make test-compile` - Verifies imports and --help methods work
  - `make test`, `make test-arch`, `make test-debian`, `make test-ubuntu` - Container-based integration tests
- No unit tests currently exist

### Pre-commit Hooks

The `.pre-commit-config.yaml` includes:

- ruff-check (linting)
- ruff-format (formatting)
- pyright (type checking)
- No pytest hook currently configured

### Dependencies

Current `pyproject.toml` dependencies:

- structlog>=25.4.0 (logging)
- rich>=13.0.0 (output formatting)
- click>=8.0.0 (CLI parsing)

### Code Characteristics Requiring Testing

1. **Subprocess Operations** - Heavy use of subprocess.run() throughout all tools
2. **File System Operations** - Config linking, path expansion, directory creation
3. **External API Calls** - GitHub API (gh CLI), package managers (pacman, apt, yay)
4. **Click CLI Entry Points** - All tools use Click decorators for CLI parsing
5. **Rich Output Formatting** - ConsoleOutput class for styled terminal output
6. **Structured Logging** - LoggingHelpers with event-based logging pattern

## Implementation Approach

### Phase 1: Test Infrastructure Setup

**1.1 Add Test Dependencies**

Update `pyproject.toml` to add test dependencies in a separate group:

```toml
[project.optional-dependencies]
test = [
    "pytest>=8.0.0",
    "pytest-cov>=4.0.0",  # Coverage reporting
    "pytest-mock>=3.12.0", # Mocking helpers
    "hypothesis>=6.90.0",  # Property-based testing
    "faker>=20.0.0",       # Test data generation
]
```

**1.2 Create Test Directory Structure**

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures and configuration
├── test_logging_config.py   # Tests for logging_config.py
├── test_output_formatting.py # Tests for output_formatting.py
├── test_init.py             # Tests for init.py
├── test_swman.py            # Tests for swman.py
├── test_pkgstatus.py        # Tests for pkgstatus.py
├── test_project_status.py   # Tests for project_status.py
└── fixtures/
    ├── __init__.py
    └── sample_data.py       # Shared test data and fixtures
```

**1.3 Configure pytest**

Add pytest configuration to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--verbose",
    "--cov=src/dotfiles",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--cov-report=xml",
    "--strict-markers",
]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "property: Property-based tests with hypothesis",
    "slow: Slow-running tests",
]

[tool.coverage.run]
source = ["src/dotfiles"]
omit = ["tests/*", ".venv/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
]
```

### Phase 2: Shared Module Tests

**2.1 Tests for `logging_config.py`**

Focus areas:

- `setup_logging()` creates proper logger with script name context
- `bind_context()` adds key-value pairs to global context
- `LoggingHelpers` methods create proper structured log events
- Log files are created with proper rotation settings
- Event-based logging pattern (snake_case events)

Test approach:

- Mock file system operations for log file creation
- Verify structlog configuration
- Validate log output format (JSON)
- Property-based tests for context binding with arbitrary keys/values

**2.2 Tests for `output_formatting.py`**

Focus areas:

- `ConsoleOutput` class initialization with verbose/quiet flags
- Output methods respect quiet/verbose settings
- Table formatting with Rich
- Progress context creation
- JSON pretty printing

Test approach:

- Mock Rich Console to capture output
- Verify emoji and styling are applied correctly
- Test verbose/quiet behavior with various combinations
- Property-based tests for table data with hypothesis strategies

### Phase 3: Tool-Specific Tests

**3.1 Tests for `init.py`**

Key functions to test:

- `expand()` - Path expansion
- `ensure_path()` - Directory creation
- `check_systemd_service_status()` - Service checking
- `Linux.run_command_with_error_handling()` - Subprocess wrapper
- CLI entry point `main()`

Test approach:

- Mock subprocess calls for all system commands
- Mock file system operations (exists, makedirs, symlink)
- Use Click's CliRunner for CLI testing
- Property-based tests for path expansion with various inputs
- Fake data for environment configurations

**3.2 Tests for `swman.py`**

Key classes/functions to test:

- `PackageManager` hierarchy (PacmanManager, YayManager, UvToolsManager, etc.)
- `is_available()` methods for each manager
- `check_updates()` and `update()` methods
- `run_with_streaming_output()` function
- CLI entry point with various flag combinations

Test approach:

- Mock subprocess.run() for package manager commands
- Mock Path operations for manager availability checks
- Test dry-run mode vs actual update mode
- Property-based tests for update result dataclasses
- Parametrize tests across all PackageManager implementations

**3.3 Tests for `pkgstatus.py`**

Key classes/functions to test:

- `StatusChecker` class initialization and cache management
- `is_cache_expired()` logic
- `get_packages_status()`, `get_git_status()`, `get_init_status()`
- Cache refresh methods
- CLI options (--json, --quiet, --refresh)

Test approach:

- Mock file system for cache file operations
- Mock time.time() for cache expiration testing
- Mock subprocess for package manager and git calls
- Property-based tests for cache expiration with various ages
- Test JSON output format validation

**3.4 Tests for `project_status.py`**

Key classes/functions to test:

- `ProjectStatusChecker` methods for fetching GitHub data
- `get_github_issues()`, `get_github_prs()` parsing
- `get_worktrees()`, `get_branches()` git operations
- Dataclasses (IssueInfo, PRInfo, BranchInfo, WorktreeInfo)
- CLI options (--no-github, --json)

Test approach:

- Mock subprocess for gh CLI and git commands
- Mock JSON responses from GitHub API
- Property-based tests for dataclass creation
- Test worktree categorization (review/feature/bugfix/experimental)

### Phase 4: Integration Tests

**4.1 CLI Integration Tests**

For each tool:

- Test `--help` flag returns expected output
- Test `--version` flag (if applicable)
- Test CLI argument parsing with Click.CliRunner
- Test invalid argument combinations return errors

**4.2 End-to-End Workflow Tests**

Selected workflows:

- pkgstatus cache lifecycle (check, refresh, expire)
- swman update simulation with dry-run
- init path expansion and directory creation

### Phase 5: Property-Based Testing Strategy

**5.1 Hypothesis Strategies**

Create custom strategies in `tests/fixtures/strategies.py`:

```python
from hypothesis import strategies as st

# Path strategies for init.py
unix_paths = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",)),
    min_size=1,
    max_size=200
)

# Package manager output strategies
package_lists = st.lists(
    st.text(min_size=1, max_size=50),
    min_size=0,
    max_size=100
)

# Log event strategies
log_events = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N")),
    min_size=1,
    max_size=50
).map(lambda s: s.lower().replace(" ", "_"))
```

**5.2 Invariant Tests**

Critical invariants to test:

- Path expansion always returns absolute paths
- Cache expiration is monotonic (never goes backwards)
- Log events are always valid snake_case identifiers
- Package manager results always have valid UpdateStatus enum values
- CLI exit codes are always 0 (success) or non-zero (error)

### Phase 6: CI/CD Integration

**6.1 Update Makefile**

Add pytest targets:

```makefile
.PHONY: test-unit test-unit-verbose test-coverage

# Run unit tests
test-unit:
	@echo "🧪 Running unit tests..."
	@uv run pytest

# Run unit tests with verbose output
test-unit-verbose:
	@echo "🧪 Running unit tests with verbose output..."
	@uv run pytest -vv

# Run unit tests with coverage report
test-coverage:
	@echo "🧪 Running unit tests with coverage..."
	@uv run pytest --cov --cov-report=html
	@echo "📊 Coverage report generated at htmlcov/index.html"

# Update existing test target to include unit tests
test: test-unit test-arch test-debian test-ubuntu
	@echo "✅ All tests completed"
```

**6.2 Update Pre-commit Hooks**

Add pytest to `.pre-commit-config.yaml`:

```yaml
- id: pytest
  name: pytest
  entry: pytest
  language: system
  files: \.py$
  pass_filenames: false
  stages: [commit]
```

**6.3 GitHub Actions Workflow**

Create `.github/workflows/test.yml`:

```yaml
name: Test Suite

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v1
      - name: Set up Python
        run: uv python install 3.12
      - name: Install dependencies
        run: uv sync --all-extras
      - name: Run unit tests
        run: uv run pytest --cov --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

### Phase 7: Documentation

**7.1 Update README**

Add testing section to repository README (or create TESTING.md):

````markdown
## Testing

This project uses pytest for comprehensive test coverage.

### Running Tests

```bash
# Run all unit tests
make test-unit

# Run with coverage report
make test-coverage

# Run specific test file
uv run pytest tests/test_init.py

# Run tests matching pattern
uv run pytest -k "test_path"
```
````

### Test Categories

- **Unit tests**: Test individual functions and classes
- **Integration tests**: Test CLI entry points and workflows
- **Property-based tests**: Use hypothesis for edge cases

### Writing Tests

See `tests/README.md` for guidelines on writing new tests.

```

**7.2 Create `tests/README.md`**

Document:
- Test structure and organization
- How to write new tests
- Mocking patterns and fixtures
- Property-based testing guidelines
- Coverage requirements

## Files to Modify

### New Files to Create

1. `tests/__init__.py` - Empty init file
2. `tests/conftest.py` - Shared fixtures (temp directories, mock subprocess, etc.)
3. `tests/test_logging_config.py` - 15-20 tests
4. `tests/test_output_formatting.py` - 15-20 tests
5. `tests/test_init.py` - 30-40 tests (largest module)
6. `tests/test_swman.py` - 25-35 tests
7. `tests/test_pkgstatus.py` - 20-30 tests
8. `tests/test_project_status.py` - 20-30 tests
9. `tests/fixtures/__init__.py` - Shared test data
10. `tests/fixtures/strategies.py` - Hypothesis strategies
11. `tests/README.md` - Testing documentation
12. `.github/workflows/test.yml` - CI/CD workflow

### Files to Modify

1. `pyproject.toml` - Add test dependencies and pytest configuration
2. `Makefile` - Add test-unit, test-coverage targets
3. `.pre-commit-config.yaml` - Add pytest hook
4. `README.md` - Add testing section (or link to TESTING.md)

## Testing Strategy

### Mocking Approach

**Subprocess Mocking:**
- Use `pytest-mock` for `subprocess.run()` and `subprocess.Popen()`
- Create fixture in `conftest.py` that returns configurable mock results
- Examples: Package manager outputs, git commands, gh CLI responses

**File System Mocking:**
- Use pytest's `tmp_path` fixture for actual file operations when safe
- Mock `os.path.exists()`, `os.makedirs()`, `os.symlink()` for destructive operations
- Mock `Path.exists()`, `Path.mkdir()` from pathlib

**External API Mocking:**
- Mock GitHub API responses using JSON fixtures
- Create sample issue/PR JSON in `tests/fixtures/github_responses.json`

**Rich/Console Mocking:**
- Mock `Console` output to capture and verify formatted output
- Use Click's `CliRunner` with `catch_exceptions=False` for debugging

### Fixture Organization

**conftest.py fixtures:**
- `mock_subprocess` - Configurable subprocess.run() mock
- `temp_config_dir` - Temporary directory for config file testing
- `sample_git_status` - Fixture for git status JSON
- `sample_package_list` - Fixture for package manager output
- `mock_logger` - Mock logger for verifying log calls
- `mock_console` - Mock Rich console for output verification

### Coverage Goals

Target coverage by module:
- `logging_config.py` - 90%+ (straightforward logging setup)
- `output_formatting.py` - 85%+ (mostly output methods)
- `init.py` - 75%+ (complex with many external calls)
- `swman.py` - 80%+ (manager classes well-suited to testing)
- `pkgstatus.py` - 85%+ (cache logic is very testable)
- `project_status.py` - 80%+ (data parsing and formatting)

## Dependencies

### Python Package Dependencies

All available via PyPI and installable with uv:
- pytest (test runner)
- pytest-cov (coverage reporting)
- pytest-mock (mocking utilities)
- hypothesis (property-based testing)
- faker (test data generation)

### Tool Dependencies

Already available in project:
- uv (package manager)
- pre-commit (git hooks)
- GitHub Actions (CI/CD platform)

### External Dependencies (for testing)

Optional but helpful:
- codecov.io account for coverage badges
- GitHub repository settings for branch protection with required checks

## Open Questions

### 1. Test Organization Philosophy

**Question:** Should we organize tests by module (current plan) or by functionality/feature?

**Context:** Currently planning one test file per source file (`test_init.py` for `init.py`). Alternative would be organizing by feature (`test_package_management.py`, `test_git_operations.py`, etc.).

**Impact:** Affects test discoverability and maintenance approach.

**Recommendation needed:** Confirm module-based organization or switch to feature-based.

### 2. Integration Test Scope

**Question:** How much overlap should exist between new unit tests and existing container integration tests?

**Context:** Makefile already has `test-arch`, `test-debian`, `test-ubuntu` that run full installations in containers. These are slow (15min timeout) but test real system integration.

**Impact:**
- Too much overlap → Wasted CI time
- Too little overlap → Gaps in coverage

**Recommendation needed:** Should unit tests mock *everything* and leave real system testing to container tests? Or should some integration tests use real subprocesses?

### 3. Mocking vs. Real Subprocess Calls

**Question:** For "safe" commands (like `git status` in a test repo), should we use real subprocess calls or always mock?

**Context:** Some operations are safe and valuable to test end-to-end:
- Git commands in temporary test repositories
- File operations in temporary directories
- Read-only package manager queries

**Impact:**
- Real calls → Slower tests but higher confidence
- Mocked calls → Faster tests but less realistic

**Recommendation needed:** Define guidelines for when to use real vs mocked subprocess calls.

### 4. Property-Based Testing Priority

**Question:** Which modules/functions should get property-based tests first?

**Context:** Property-based testing with hypothesis is powerful but time-consuming to write. Cannot realistically add it everywhere in first iteration.

**Priority candidates:**
1. Path expansion in `init.py` (lots of edge cases)
2. Cache expiration logic in `pkgstatus.py` (time-based invariants)
3. Log event validation in `logging_config.py` (format constraints)
4. Package manager result parsing (varied output formats)

**Recommendation needed:** Prioritize top 2-3 areas for initial property-based testing.

### 5. Test Data Management

**Question:** How should we manage test fixtures and sample data?

**Options:**
1. Inline test data in test files (simple, but duplicative)
2. JSON files in `tests/fixtures/` (reusable, but external)
3. Faker-generated data (realistic, but non-deterministic)
4. Combination approach (small data inline, large samples in files, random data via Faker)

**Impact:** Affects test maintainability and readability.

**Recommendation needed:** Choose fixture management strategy.

### 6. Coverage Enforcement

**Question:** Should we enforce minimum coverage thresholds in CI/CD?

**Context:** Can configure pytest-cov to fail if coverage drops below threshold (e.g., 80%).

**Pros:**
- Prevents coverage regression
- Forces thoughtful testing

**Cons:**
- May encourage "coverage theater" (tests that execute code but don't validate behavior)
- May slow down development

**Recommendation needed:** Set coverage threshold (if any) and enforcement policy.

### 7. Test Execution Performance

**Question:** What is acceptable test suite execution time?

**Context:** Fast tests encourage frequent execution. Slow tests get skipped.

**Targets to consider:**
- <5 seconds: Excellent for pre-commit hooks
- <30 seconds: Good for development workflow
- <2 minutes: Acceptable for CI/CD
- >5 minutes: Too slow, needs optimization

**Recommendation needed:** Set target execution time and strategy for fast/slow test separation.

### 8. Backward Compatibility Testing

**Question:** Should we test against multiple Python versions?

**Context:** Project requires Python >=3.12.3. Should we also test against 3.13, 3.14, etc.?

**Impact:**
- More testing → Better compatibility assurance
- More testing → Slower CI/CD, more maintenance

**Recommendation needed:** Define Python version testing matrix for CI/CD.

### 9. Documentation Depth

**Question:** How detailed should `tests/README.md` be?

**Options:**
1. Minimal (just how to run tests)
2. Moderate (run tests + basic writing guidelines)
3. Comprehensive (examples, patterns, best practices)

**Impact:** Affects contributor onboarding and test quality consistency.

**Recommendation needed:** Choose documentation depth level.

### 10. Pre-commit Hook Strictness

**Question:** Should pytest be a blocking pre-commit hook?

**Context:** Can add pytest to pre-commit hooks, but this means:
- Every commit must pass all tests
- Commits are slower (tests run each time)
- May frustrate rapid iteration

**Alternative:** Run tests only in CI/CD, not locally.

**Recommendation needed:** Should pytest be in pre-commit hooks? If yes, with what configuration?

## Implementation Timeline Estimate

### Week 1: Infrastructure & Shared Modules
- Day 1-2: Set up test infrastructure, dependencies, pytest config
- Day 3-4: Write tests for `logging_config.py` and `output_formatting.py`
- Day 5: Set up fixtures and mocking patterns in `conftest.py`

### Week 2: Core Tool Tests (Part 1)
- Day 1-3: Write tests for `init.py` (largest module)
- Day 4-5: Write tests for `swman.py`

### Week 3: Core Tool Tests (Part 2)
- Day 1-2: Write tests for `pkgstatus.py`
- Day 3-4: Write tests for `project_status.py`
- Day 5: Integration tests for CLI entry points

### Week 4: Property-Based Testing & CI/CD
- Day 1-2: Add hypothesis property-based tests for priority areas
- Day 3: Configure GitHub Actions workflow
- Day 4: Update Makefile and pre-commit hooks
- Day 5: Documentation (README updates, tests/README.md)

**Total Estimate:** 4 weeks for comprehensive implementation

## Next Steps

1. **Resolve Open Questions** - Get answers to the 10 open questions above
2. **Create Feature Branch** - Branch from this plan to implement tests
3. **Start with Phase 1** - Set up test infrastructure first
4. **Incremental PRs** - Consider breaking into multiple PRs:
   - PR 1: Test infrastructure + shared module tests
   - PR 2: init.py + swman.py tests
   - PR 3: pkgstatus.py + project_status.py tests
   - PR 4: Property-based tests + CI/CD + documentation
5. **Iterate on Coverage** - Start with basic tests, then improve coverage incrementally

## Success Metrics

Upon completion, success will be measured by:

- ✅ All test files created and passing
- ✅ Coverage >80% for all modules (verified with pytest-cov)
- ✅ CI/CD pipeline running tests automatically
- ✅ Pre-commit hooks configured (if decided)
- ✅ Documentation complete and clear
- ✅ Tests passing on all supported platforms (Arch, Debian, Ubuntu)
- ✅ Property-based tests validating critical invariants
- ✅ Zero test failures in main branch
```
