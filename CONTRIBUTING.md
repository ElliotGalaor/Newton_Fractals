# Contributing

Thanks for your interest in Newton Fractals! The project follows a simple team workflow.

## Workflow

1. **Open or pick an issue** describing the bug or the feature (templates are provided).
2. **Create a branch** from `main`, named after the type of change:
   `feat/…`, `fix/…`, `test/…`, `ci/…`, `cd/…`, `docs/…`, `perf/…`.
3. **Commit** with a short prefix matching the type (`feat: …`, `fix: …`, `test: …`,
   `ci: …`, `docs: …`), and reference the issue (`Closes #12`).
4. **Open a pull request** — the template asks for a summary and a test plan.
5. **CI must be green** (lint, Linux build and tests, Windows MinGW and MSVC builds).
6. **Review, then squash-merge** into `main`.

Releases are published by pushing a tag `vX.Y.Z`: the `Release` workflow builds, tests and
publishes the Windows archive, with notes generated from the merged pull requests.

## Development setup

```bash
python -m pip install -r requirements-dev.txt
cd ConsoleApplication2
g++ -O2 -fopenmp -Wall -Wextra -o main main.cpp Tableau.cpp CNum.cpp
cd ..
```

## Before opening a pull request

```bash
ruff check .            # lint
python -m pytest        # tests (engine tests need the compiled main / main.exe)
```

- New logic comes with tests in `tests/`.
- Tests must not write into the project folder (use `tmp_path`).
- The interface tests run off-screen (`QT_QPA_PLATFORM=offscreen`): no display needed.
