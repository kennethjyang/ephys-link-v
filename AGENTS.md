# Implementation Rules
- Use the Typer skill when implementing the CLI.
- Use the FastAPI skill when editing the server.
- Use uv, never pip.

# Python Imports

- Prefer absolute imports rooted at the package name. Allow single-dot
  relative imports within a subpackage when clearer.
- Use module or symbol imports according to readability. Prefer qualified
  calls when a function name alone would be ambiguous.
- Follow established aliases: use `import numpy as np` and access NumPy
  functions through `np`. Avoid arbitrary abbreviations.
- Never use wildcard imports.
- Keep imports at module scope, after the docstring and `__future__`
  imports. Separate standard-library, third-party, and first-party groups.
- Follow the configured import sorter.
- Use local or conditional imports only for a concrete reason; document
  non-obvious exceptions.
- Use dependencies' documented public APIs, not private modules or
  incidental re-exports.
- Within the project package, import from defining modules rather than
  the top-level API facade.
- Keep `__init__.py` lightweight; re-export only intentional public APIs.
- Import by package name, never through `src`. Install the package in the
  development environment; do not add `sys.path` workarounds.
