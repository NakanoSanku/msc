# Repository Guidelines

## Project Structure & Module Organization
- This is a `uv`-managed Python workspace (see `pyproject.toml`, `uv.lock`).
- Core packages live in `msc-base`, `msc-adb`, `msc-droidcast`, `msc-minicap`, and `msc-mumu`.
- Each package exposes code from `src/msc` (for example `msc-base/src/msc/screencap.py`).
- Place new tests alongside each package, e.g. `msc-adb/tests/test_adbcap.py`.

## Build, Test, and Development Commands
- `uv sync` — set up or update the workspace virtual environment.
- `uv run python` — run ad‑hoc scripts using the workspace environment.
- `uv run pytest` — run the test suite from the repo root once tests are added.
- `uv run python -m msc.adbcap` — example manual test of the ADB screencap implementation.

## Coding Style & Naming Conventions
- Target Python ≥ 3.9 with 4‑space indentation and PEP 8‑style formatting.
- Modules use `snake_case.py`; classes use `CamelCase` (e.g. `ScreenCap`, `ADBCap`); functions and methods use `snake_case`.
- Keep public APIs small and typed; preserve and extend existing docstrings (Chinese and/or English) instead of removing them.
- No strict formatter is enforced; when in doubt, follow nearby code and keep imports and line wrapping consistent.

## Testing Guidelines
- Use `pytest` (recommended); name files `test_*.py` and functions `test_*`.
- Prefer package‑local test trees such as `msc-minicap/tests/test_minicap.py`.
- Cover main screencap flows (raw bytes → `cv2.Mat`) and critical error paths (timeouts, invalid data, missing binaries).
- Run tests with `uv run pytest`; if needed, add `pytest` as a dev dependency via `uv add --dev pytest`.

## Commit & Pull Request Guidelines
- Follow existing history: start messages with a type tag in uppercase (e.g. `REFINE: ...`, `FIX: ...`, `BUG: ...`) plus a concise summary.
- Keep commits focused on a single logical change; avoid mixing refactors with bug fixes.
- PRs should state motivation, key changes, verification steps/commands, and link any related issues.
- For behavior changes (e.g. DroidCast, MuMu, minicap), describe before/after behavior and update or add tests when possible.

## Agent-Specific Instructions
- Edit only workspace code and top‑level configuration; do not modify `.venv` or vendored third‑party files.
- Prefer minimal, well‑scoped patches within a single package at a time.
- When dependency changes are required, update `pyproject.toml` and regenerate `uv.lock` rather than editing the lockfile by hand.

