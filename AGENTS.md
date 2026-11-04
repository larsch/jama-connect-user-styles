# Development

- Keep examples fictional and tenant-independent. Do not commit browser captures, session state, internal URLs, real project/item identifiers, or unredacted screenshots.
- Tests must run without a live Jama installation, private files, or credentials. Use the synthetic fixtures in `tests/`; do not copy vendor stylesheets or assets into them.
- Before committing style changes, run `uv run --with playwright --with tinycss2 python check_theme.py`. An installed browser may be selected with `--browser-channel msedge`.
- After each completed change, increment each affected style's UserCSS `@version`, run validation, commit, and push to the upstream branch without asking for separate approval. New styles start with an initial version; do not bump unchanged styles.
- Keep domain restrictions and print isolation intact.
- Keep the form-row layout independent from the dark theme. Preserve authored colors and meaningful status/diff highlights.
