# Jama Connect user styles

Unofficial, independent user styles for Jama Connect, maintained as a personal project. Not affiliated with or endorsed by Jama Software.

## Styles

- **[JAMA Dark Mode](jama-dark.user.css)**: charcoal surfaces, light text, lime selection/focus accents, and light blue links. Covers common legacy Ext JS and modern Jama UI components without changing layout.
- **[Jama Form Row Layout](jama-form-row.user.css)**: optional label/value columns for redesigned item forms. Labels align right on wider screens; narrow screens stack the fields. Enable or disable it independently of the dark theme.

Both styles are screen-only and target `jamacloud.com` and its subdomains. For a self-hosted installation, replace the domain in your local copy with your own host. Component coverage depends on your Jama Connect version.

## Install with Stylus

1. Install the Stylus extension for your browser.
2. Open the **Raw** view of the `.user.css` file you want in this repository. If Stylus opens its installation page, review the style and install it.
3. Alternatively, open Stylus → Manage → Write new style, paste the complete file, accept UserCSS mode if offered, and save.
4. Reload Jama Connect. Disable other recoloring extensions for the site while testing.

The optional form layout can be installed the same way. Disabling either style restores the application's appearance or layout for that style's scope.

## Scope and limitations

- Includes panels, toolbars, tabs, grids, trees, menus, dialogs, common form controls, comments chrome, and activity history.
- Covers common hover, selected, disabled, and keyboard-focus states. Some icon assets may still have poor contrast.
- Read-only rich text and comment bodies generally remain light to preserve authored colors. Displayed tables and inline editor tables use dark default surfaces/text, but explicitly colored descendants are preserved.
- Semantic status/diff colors, charts, and primary/danger buttons are deliberately not blanket-recolored. Changed/inherited comparison-cell highlights retain their original fills.
- No JavaScript runs in Jama, no remote assets are loaded by the styles, no image inversion is used, and editor iframes are not injected.
- Printed content is excluded. This is not a complete or accessibility-certified theme; check the original view when interpreting color-coded data.
- Requires a current browser with CSS `:is()` and `:has()` support. A selector may need updating when Jama changes its UI.

## Validate

Requires [uv](https://docs.astral.sh/uv/) and Python. Install the test browser once, then run:

```text
uv run --with playwright python -m playwright install chromium
uv run --with playwright --with tinycss2 python check_theme.py
```

To use an installed Microsoft Edge instead:

```text
uv run --with playwright --with tinycss2 python check_theme.py --browser-channel msedge
```

The test uses only hand-written synthetic HTML/CSS and an intercepted `https://example.test/` page. It does not read HAR captures, use credentials, or connect to a Jama tenant. It checks both styles' syntax, representative computed styles, state changes, preserved colors/assets, print isolation, and responsive form layout. It cannot establish compatibility with every live Jama screen or verify a Stylus installation.

For a manual pass, inspect the project tree, item grid, an item with formatted text/tables, a dialog, menus, activity history, keyboard navigation, and print preview. Test the form layout at wide and narrow widths.

## Reporting issues

Include the browser version, affected component classes, and a minimal sanitized HTML example. Use fictional names and values. Do not upload HAR files, session data, raw page dumps, internal URLs, customer/project names, or unredacted screenshots. Ignore rules are a safety net, not a substitute for checking what you commit.
