"""Self-contained synthetic smoke tests; see README.md for browser setup."""
import argparse
from pathlib import Path
import re

import tinycss2
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).parent
source = (ROOT / "jama-dark.user.css").read_text(encoding="utf-8")


def check_css(nodes):
    for node in nodes:
        assert node.type != "error", str(node)
        if node.type == "at-rule" and node.content is not None:
            check_css(tinycss2.parse_rule_list(node.content, skip_whitespace=True, skip_comments=True))
        elif node.type == "qualified-rule":
            for decl in tinycss2.parse_declaration_list(node.content, skip_whitespace=True, skip_comments=True):
                assert decl.type == "declaration", str(decl)
                assert not any(token.type == "error" for token in decl.value)


for css_path in sorted(ROOT.glob('*.user.css')):
    css_source = css_path.read_text(encoding='utf-8')
    check_css(tinycss2.parse_stylesheet(css_source, skip_whitespace=True, skip_comments=True))
    assert '@-moz-document domain("jamacloud.com")' in css_source, css_path.name
assert '@name           JAMA Dark Mode' in source
assert '@-moz-document domain("jamacloud.com")' in source
# Stylus unwraps the domain rule before injection. Emulate that, retaining @media.
inner = source[source.index("{", source.index("@-moz-document")) + 1:source.rfind("}")]
assert not re.search(r"@import|url\(|display\s*:|position\s*:", inner)
# Only the targeted brightness experiment may filter assets; never invert them.
assert re.findall(r"\bfilter\s*:\s*([^;]+);", inner) == ["brightness(1.7) !important"]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--browser-channel", help="Use an installed browser, e.g. msedge; default: Playwright Chromium")
args = parser.parse_args()
# ponytail: Synthetic baselines test selector behavior, not vendor stylesheet parity.
# Add a sanitized fixture when another component/state needs regression coverage.
fixture = (ROOT / "tests" / "components.html").read_text(encoding="utf-8").replace(
    "LIGHT_UI", (ROOT / "tests" / "light-ui.css").read_text(encoding="utf-8")
)

with sync_playwright() as p:
    browser = p.chromium.launch(channel=args.browser_channel, headless=True)
    page = browser.new_page()
    # All requests are intercepted: do not contact Jama, Pendo, or asset servers.
    page.route("**/*", lambda route: route.fulfill(content_type="text/html", body=fixture)
               if route.request.is_navigation_request() else route.abort())
    page.goto("https://example.test/offline-theme-test", wait_until="domcontentloaded")

    def style(element, prop):
        return page.locator("#" + element).evaluate("(el, prop) => getComputedStyle(el).getPropertyValue(prop)", prop)

    admin_baseline = {(el, prop): style(el, prop) for el, prop in [
        ("admin-nav", "background-color"), ("admin-nav", "width"),
        ("admin-views", "background-color"), ("admin-org-tab", "background-color"),
        ("admin-details", "background-color"), ("admin-details", "color"),
        ("admin-selected", "background-color"), ("admin-sprite", "background-image"),
        ("admin-warning-icon", "color"), ("admin-badge", "color"),
        ("unrelated-tab", "background-color"), ("unrelated-admin-button", "background-color")
    ]}
    baseline = {(el, prop): style(el, prop) for el, prop in [
        ("panel", "background-color"), ("status", "background-color"),
        ("image", "background-image"), ("input", "border-top-color"),
        ("activity-icon", "background-image"), ("activity-header", "background-color"),
        ("simple-changed", "background-color"), ("simple-inherited", "background-color"),
        ("simple-sort", "background-image"), ("simple-cell", "background-color"),
        ("history-panel", "background-color"), ("history-sprite", "background-image"),
        ("history-details", "max-height"), ("history-details", "overflow"),
        ("danger", "background-color"), ("diff", "background-color"),
        ("disabled-document-icon", "color"),
        ("jama-checked", "background-image"), ("jama-indeterminate", "background-image"),
        ("filter-checkbox", "background-image"),
        ("jama-disabled", "background-color"),
        ("template-list", "background-color"), ("template-odd", "background-color"),
        ("template-even", "background-color"), ("template-even", "border-bottom-color"),
        ("template-name", "color"), ("template-even-name", "color")
    ]}
    assert baseline["template-even", "background-color"] == "rgb(255, 255, 255)"
    page.emulate_media(media="print")
    print_before = style("panel", "background-color")
    page.emulate_media(media="screen")
    for el in ("gradient-header", "gradient-important", "gradient-button"):
        assert style(el, "background-image") != "none", el
    page.add_style_tag(content=inner)
    for el in ("admin-nav", "admin-collapse-container", "admin-tab-group", "admin-content",
               "admin-tab-panel", "admin-views", "admin-details"):
        assert style(el, "background-color") == "rgb(36, 36, 36)", el
    for el in ("admin-nav", "admin-heading", "admin-details", "admin-selected",
               "admin-org-tab", "admin-project-tab", "admin-collapse-icon"):
        assert style(el, "color") == "rgb(245, 245, 245)", el
    assert style("admin-tabs", "background-color") == "rgb(44, 44, 44)"
    assert style("admin-project-tab", "background-color") == "rgb(44, 44, 44)"
    for el in ("admin-org-tab", "admin-selected"):
        assert style(el, "background-color") == "rgb(53, 71, 41)", el
    for el in ("admin-details", "admin-project-tab", "admin-collapse", "admin-selected", "admin-org-tab"):
        page.locator("#" + el).hover()
        selected = el in ("admin-selected", "admin-org-tab")
        assert style(el, "background-color") == ("rgb(53, 71, 41)" if selected else "rgb(53, 58, 47)"), el
        page.locator("#" + el).focus()
        assert style(el, "outline-color") == "rgb(146, 209, 83)", el
        assert "rgb(146, 209, 83)" in style(el, "box-shadow"), el
    page.locator("#admin-project-tab").evaluate("el => el.setAttribute('aria-selected', 'true')")
    assert style("admin-project-tab", "background-color") == "rgb(53, 71, 41)"
    page.locator("#admin-project-tab").evaluate("el => el.setAttribute('aria-selected', 'false')")
    page.mouse.move(0, 0)
    for el, prop in (("admin-sprite", "background-image"), ("admin-warning-icon", "color"),
                     ("admin-badge", "color"), ("admin-nav", "width"),
                     ("unrelated-tab", "background-color"), ("unrelated-admin-button", "background-color")):
        assert style(el, prop) == admin_baseline[el, prop], (el, prop)
    for el in ("admin-content", "admin-divider"):
        assert style(el, "border-bottom-color") == "rgb(80, 80, 80)", el
    page.locator("#admin-nav").evaluate("el => el.classList.remove('open')")
    assert style("admin-tab-group", "display") == "none"
    assert style("admin-nav", "background-color") == "rgb(36, 36, 36)"
    page.locator("#admin-nav").evaluate("el => el.classList.add('open')")
    assert style("template-list", "background-color") == "rgb(36, 36, 36)"
    for el, background in (("template-odd", "rgb(36, 36, 36)"), ("template-even", "rgb(44, 44, 44)")):
        row = page.locator("#" + el)
        assert style(el, "background-color") == background, el
        assert style(el, "border-bottom-color") == "rgb(80, 80, 80)", el
        # Ext JS applies these classes; selection must win even on hovered stripes.
        for classes, expected in (("x-list-over", "rgb(53, 58, 47)"),
                                  ("x-list-selected", "rgb(53, 71, 41)"),
                                  ("x-list-selected x-list-over", "rgb(53, 71, 41)")):
            row.evaluate("(el, classes) => el.className = classes", classes)
            assert style(el, "background-color") == expected, (el, classes)
        row.evaluate("el => el.className = ''")
        assert style(el, "background-color") == background, el
    for el in ("template-name", "template-even-name"):
        assert style(el, "color") == "rgb(245, 245, 245)", el
    for el in ("template-edit", "template-delete"):
        assert style(el, "color") == "rgb(161, 221, 250)", el
    assert style("template-authored", "color") == "rgb(200, 30, 40)"
    assert style("unrelated-definition", "background-color") == "rgb(255, 255, 255)"
    assert style("unrelated-definition", "color") == "rgb(0, 0, 0)"
    for el in ("history-panel", "history-entries", "history-entry", "history-details", "history-timestamp-container"):
        assert style(el, "background-color") == "rgb(36, 36, 36)", el
    for el in ("history-header", "history-breadcrumbs", "history-title-bar"):
        assert style(el, "background-color") == "rgb(44, 44, 44)", el
    for el in ("history-heading", "history-title", "history-description", "history-line", "history-value",
               "history-category", "history-category-text", "history-refresh-icon", "history-close-icon", "history-clear-icon"):
        assert style(el, "color") == "rgb(245, 245, 245)", el
    for el in ("history-count", "history-timestamp", "history-empty"):
        assert style(el, "color") == "rgb(196, 196, 196)", el
    for el in ("history-expand", "history-expand-label", "history-caret", "history-breadcrumb"):
        assert style(el, "color") == "rgb(161, 221, 250)", el
    for el in ("history-search", "history-search-outline"):
        assert style(el, "background-color") == "rgb(17, 17, 17)", el
        assert style(el, "color") == "rgb(245, 245, 245)", el
        assert style(el, "border-top-color") == "rgb(80, 80, 80)", el
    assert page.locator("#history-search").evaluate("el => getComputedStyle(el, '::placeholder').color") == "rgb(196, 196, 196)"
    for el in ("history-close", "history-clear", "history-expand"):
        assert style(el, "background-color") == "rgba(0, 0, 0, 0)", el
        page.locator("#" + el).hover()
        assert style(el, "background-color") == "rgb(53, 58, 47)", el
    assert page.locator("#history-expand").get_attribute("aria-expanded") == "false"
    for prop in ("max-height", "overflow"):
        assert style("history-details", prop) == baseline["history-details", prop]
    page.locator("#history-expand").evaluate("el => el.setAttribute('aria-expanded', 'true')")
    page.locator("#history-details").evaluate("el => el.classList.remove('height-limited')")
    page.locator("#history-description").evaluate("el => el.classList.remove('height-limited')")
    assert style("history-details", "background-color") == "rgb(36, 36, 36)"
    assert style("history-description", "color") == "rgb(245, 245, 245)"
    assert style("history-details", "max-height") == "none"
    assert style("history-details", "overflow") == "visible"
    assert style("history-sprite", "background-image") == baseline["history-sprite", "background-image"]
    assert style("unrelated-details", "background-color") == "rgb(255, 255, 255)"
    assert style("unrelated-details", "color") == "rgb(0, 0, 0)"
    page.locator("#history-search").focus()
    assert style("history-search", "outline-color") == "rgb(146, 209, 83)"
    page.mouse.move(0, 0)
    for el in ("simple-header", "simple-header-th", "simple-alt", "simple-zebra"):
        assert style(el, "background-color") == "rgb(44, 44, 44)", (el, style(el, "background-color"))
    assert style("simple-cell", "background-color") == "rgb(36, 36, 36)"
    for el in ("simple-header", "simple-sort", "simple-header-th", "simple-cell", "simple-zebra", "simple-selected"):
        assert style(el, "color") == "rgb(245, 245, 245)", el
        if el != "simple-sort":
            assert style(el, "border-bottom-color") == "rgb(80, 80, 80)", el
    for el in ("simple-selected", "simple-zebra-selected"):
        assert style(el, "background-color") == "rgb(53, 71, 41)", el
    assert style("simple-hovered", "background-color") == "rgb(53, 58, 47)"
    for el in ("simple-inactive", "simple-disabled"):
        assert style(el, "color") == "rgb(196, 196, 196)", el
    for el in ("simple-edit", "simple-delete"):
        assert style(el, "color") == "rgb(161, 221, 250)", el
    for el in ("simple-changed", "simple-inherited"):
        assert style(el, "background-color") == baseline[el, "background-color"], el
        assert style(el, "color") == "rgb(32, 38, 48)", el
    assert style("simple-sort", "background-image") == baseline["simple-sort", "background-image"]
    for row, cell, expected in (
        ("simple-row", "simple-cell", "rgb(53, 58, 47)"),
        ("simple-zebra-row", "simple-zebra", "rgb(53, 58, 47)"),
        ("simple-selected-row", "simple-selected", "rgb(53, 71, 41)"),
    ):
        page.locator("#" + row).hover()
        assert style(cell, "background-color") == expected, cell
    page.mouse.move(0, 0)
    for el in ("picklist-popup", "picklist-option"):
        assert style(el, "background-color") == "rgb(36, 36, 36)", el
    for el in ("picklist-popup", "picklist-option", "option-label", "option-match", "picklist-selected"):
        assert style(el, "color") == "rgb(245, 245, 245)", el
    assert style("picklist-selected", "background-color") == "rgb(53, 71, 41)"
    page.locator("#picklist-option").hover()
    assert style("picklist-option", "background-color") == "rgb(53, 58, 47)"
    page.locator("#picklist-option").focus()
    assert style("picklist-option", "background-color") == "rgb(53, 58, 47)"
    assert style("option-dot", "background-color") == "rgb(0, 204, 102)"
    page.locator("#picklist-selected").hover()
    assert style("picklist-selected", "background-color") == "rgb(53, 71, 41)"
    page.mouse.move(0, 0)
    for el in ("picklist-trigger", "picklist-button"):
        assert style(el, "background-color") == "rgb(17, 17, 17)", el
    for el in ("picklist-button", "picklist-label", "picklist-caret"):
        assert style(el, "color") == "rgb(245, 245, 245)", el
    assert style("item-picklist", "--lluck-picklist-selected-option-color") == "#00CC66"
    assert style("picklist-trigger", "border-top-color") == "rgb(255, 0, 0)"
    page.locator("#picklist-button").evaluate("el => el.disabled = true")
    for el in ("picklist-button", "picklist-label", "picklist-caret"):
        assert style(el, "color") == "rgb(196, 196, 196)", el
    page.locator("#picklist-button").evaluate("el => el.disabled = false")
    for el in ("editor-contents", "editor-body"):
        assert style(el, "background-color") == "rgb(36, 36, 36)", el
        assert style(el, "color-scheme") == "dark", el
    for el in ("editor-contents", "editor-body", "editor-paragraph", "editor-combo-text"):
        assert style(el, "color") == "rgb(245, 245, 245)", el
    for el in ("editor-top", "editor-combo"):
        assert style(el, "background-color") == "rgb(44, 44, 44)", el
    assert style("editor-authored", "color") == "rgb(200, 30, 40)"
    assert style("editor-table", "background-color") == "rgb(36, 36, 36)"
    for el in ("editor-table", "editor-table-heading", "editor-table-cell"):
        assert style(el, "color") == "rgb(245, 245, 245)", el
        assert style(el, "border-top-color") == "rgb(80, 80, 80)", el
    assert style("editor-table-heading", "background-color") == "rgb(44, 44, 44)"
    for el in ("gradient-header", "gradient-important", "gradient-button"):
        assert style(el, "background-image") == "none", el
    for el in ("filter-sidebar", "filter-sidebar-inner", "filter-flyout"):
        assert style(el, "background-color") == "rgb(36, 36, 36)", el
        assert style(el, "color") == "rgb(245, 245, 245)", el
    for el in ("filter-sidebar-title", "filter-option-label", "filter-facet-label", "filter-keyword"):
        assert style(el, "color") == "rgb(245, 245, 245)", el
    assert style("filter-keyword", "background-color") == "rgb(17, 17, 17)"
    assert style("filter-keyword", "border-top-color") == "rgb(80, 80, 80)"
    assert style("filter-count", "color") == "rgb(196, 196, 196)"
    assert style("filter-clear", "color") == "rgb(161, 221, 250)"
    assert style("filter-clear", "background-color") == "rgba(0, 0, 0, 0)"
    assert style("filter-checkbox", "background-image") == baseline["filter-checkbox", "background-image"]
    assert style("header", "background-color") == "rgb(44, 44, 44)"
    assert style("header-title", "color") == "rgb(245, 245, 245)"
    assert style("j-execute-test", "background-color") == "rgb(36, 36, 36)"
    assert style("loading-mask", "background-color") == "rgb(17, 17, 17)"
    assert style("single-item", "background-color") == "rgb(36, 36, 36)"
    assert style("single-item", "color") == "rgb(245, 245, 245)"
    assert style("modern-tree", "color") == "rgb(245, 245, 245)"
    assert style("modern-label", "color") == "rgb(245, 245, 245)"
    assert style("panel", "background-color") == "rgb(36, 36, 36)"
    assert style("wizard-current-name", "color") == "rgb(245, 245, 245)"
    assert style("participants-panel", "background-color") == "rgb(36, 36, 36)"
    assert style("participants-panel", "color") == "rgb(245, 245, 245)"
    assert style("assignments-panel", "background-color") == "rgb(36, 36, 36)"
    assert style("assignments-panel", "color") == "rgb(245, 245, 245)"
    assert style("checkbox-wrapper", "background-color") == "rgba(0, 0, 0, 0)"
    assert style("jama-checkbox-label", "color") == "rgb(245, 245, 245)"
    for el in ("jama-unchecked", "jama-checked", "jama-indeterminate"):
        assert style(el, "background-color") == "rgb(245, 245, 245)", el
        assert style(el, "border-top-color") == "rgb(196, 196, 196)", el
    for el in ("jama-checked", "jama-indeterminate"):
        assert style(el, "background-image") == baseline[el, "background-image"], el
    assert style("jama-disabled", "background-color") == baseline["jama-disabled", "background-color"]
    assert style("react-modal", "background-color") == "rgb(36, 36, 36)"
    assert style("react-modal", "color") == "rgb(245, 245, 245)"
    assert style("react-modal", "border-top-color") == "rgb(80, 80, 80)"
    assert style("react-overlay", "background-color") == "rgba(255, 255, 255, 0.75)"
    assert style("selected", "background-color") == "rgb(53, 71, 41)"
    assert style("filter-selected", "background-color") == "rgb(53, 71, 41)"
    assert style("filter-selected", "color") == "rgb(245, 245, 245)"
    page.locator("#filter-selected").hover()
    assert style("filter-selected", "background-color") == "rgb(53, 71, 41)"
    page.locator("#filter-unselected").hover()
    assert style("filter-unselected", "background-color") == "rgb(53, 58, 47)"
    page.mouse.move(0, 0)
    assert style("disabled", "color") == "rgb(196, 196, 196)"
    assert style("tab", "color") == "rgb(196, 196, 196)"
    assert style("active-tab", "color") == "rgb(146, 209, 83)"
    assert style("variant-disabled-tab", "color") == "rgb(196, 196, 196)"
    assert style("input", "color") == "rgb(245, 245, 245)"
    assert style("input", "border-top-color") == baseline["input", "border-top-color"]
    assert style("rich", "background-color") == "rgb(255, 255, 255)"
    assert style("rich-link", "color") == "rgb(36, 92, 158)"
    assert style("authored", "color") == "rgb(200, 30, 40)"
    for el in ("rich-table", "rich-table-heading", "rich-table-cell", "rich-table-text"):
        assert style(el, "color") == "rgb(245, 245, 245)", el
    assert style("rich-table", "background-color") == "rgb(36, 36, 36)"
    assert style("rich-table-heading", "background-color") == "rgb(44, 44, 44)"
    for el in ("rich-table", "rich-table-heading", "rich-table-cell"):
        assert style(el, "border-top-color") == "rgb(80, 80, 80)", el
    assert style("table-authored", "color") == "rgb(200, 30, 40)"
    assert style("status", "background-color") == baseline["status", "background-color"]
    assert style("image", "background-image") == baseline["image", "background-image"]
    assert style("document-icon", "color") == "rgb(245, 245, 245)"
    page.locator("#document-toggle").hover()
    assert style("document-icon", "color") == "rgb(245, 245, 245)"
    assert style("disabled-document-icon", "color") == baseline["disabled-document-icon", "color"]
    assert style("filter-icon", "color") == "rgb(245, 245, 245)"
    page.locator("#filter-toggle").hover()
    assert style("filter-icon", "color") == "rgb(245, 245, 245)"
    page.locator("#filter-toggle").evaluate("el => el.disabled = true")
    assert style("filter-icon", "color") == "rgb(105, 105, 105)"
    page.locator("#filter-toggle").evaluate("el => { el.disabled = false; el.setAttribute('aria-disabled', 'true'); }")
    assert style("filter-icon", "color") == "rgb(105, 105, 105)"
    page.mouse.move(0, 0)
    assert style("column-toggle-icon", "color") == "rgb(245, 245, 245)"
    page.locator("#column-toggle-button").hover()
    assert style("column-toggle-icon", "color") == "rgb(245, 245, 245)"
    page.locator("#column-toggle-button").evaluate("el => el.disabled = true")
    assert style("column-toggle-icon", "color") == "rgb(105, 105, 105)"
    page.locator("#column-toggle-button").evaluate("el => { el.disabled = false; el.setAttribute('aria-disabled', 'true'); }")
    assert style("column-toggle-icon", "color") == "rgb(105, 105, 105)"
    page.mouse.move(0, 0)
    assert style("reload-icon", "color") == "rgb(245, 245, 245)"
    page.locator("#reload-button").hover()
    assert style("reload-icon", "color") == "rgb(245, 245, 245)"
    page.locator("#reload-button").evaluate("el => el.disabled = true")
    assert style("reload-icon", "color") == "rgb(105, 105, 105)"
    page.locator("#reload-button").evaluate("el => { el.disabled = false; el.setAttribute('aria-disabled', 'true'); }")
    assert style("reload-icon", "color") == "rgb(105, 105, 105)"
    page.mouse.move(0, 0)
    assert style("row-height-icon", "filter") == "brightness(1.7)"
    assert style("row-height-button", "filter") == "none"
    assert style("row-height-caret", "filter") == "none"
    page.locator("#row-height-button").evaluate("el => el.setAttribute('aria-disabled', 'true')")
    assert style("row-height-icon", "filter") == "none"
    page.locator("#row-height-button").evaluate("el => el.setAttribute('aria-disabled', 'false')")
    for el in ("pager-next", "pager-last"):
        assert style(el, "filter") == "brightness(1.7)", el
    for el in ("pager-first", "pager-previous"):
        assert style(el, "filter") == "none", el
    page.locator("#pager-next-button").hover()
    assert style("pager-next", "filter") == "brightness(1.7)"
    page.locator("#pager-next-button").evaluate("el => el.setAttribute('aria-disabled', 'true')")
    assert style("pager-next", "filter") == "none"
    page.mouse.move(0, 0)
    for el in ("tool-icon", "gray-icon"):
        assert style(el, "filter") == "brightness(1.7)", el
    page.locator("#gray-icon").hover()
    assert style("gray-icon", "filter") == "brightness(1.7)"
    page.mouse.move(0, 0)
    for el in ("image", "labeled-icon", "colored-icon", "disabled-icon", "disabled-parent-icon", "aria-disabled-tool", "authored"):
        assert style(el, "filter") == "none", el
    assert style("breadcrumb-pill", "background-color") == "rgb(44, 44, 44)"
    assert style("breadcrumb-pill", "color") == "rgb(245, 245, 245)"
    for el in ("sorted-header", "descending-header"):
        assert style(el, "background-color") == "rgb(53, 58, 47)", el
        assert style(el, "color") == "rgb(245, 245, 245)", el
        assert style(el, "background-image") == "none", el
    assert style("live-status", "background-color") == "rgb(156, 231, 140)"
    assert style("live-status", "color") == "rgb(0, 0, 0)"
    assert style("live-dialog-header", "background-color") == "rgb(44, 44, 44)"
    for el in ("live-grid", "live-dialog", "live-review-cell"):
        assert style(el, "background-color") == "rgb(36, 36, 36)", el
        assert style(el, "color") == "rgb(245, 245, 245)", el
    for el in ("combo", "calendar", "form", "notification", "lookup", "comment-wrap"):
        assert style(el, "background-color") == "rgb(36, 36, 36)", (el, style(el, "background-color"))
    for el in ("combo-selected", "date-selected"):
        assert style(el, "background-color") == "rgb(53, 71, 41)", el
    for el in ("combo-selected", "form-label"):
        assert style(el, "color") == "rgb(245, 245, 245)", el
    assert style("date-disabled", "color") == "rgb(196, 196, 196)"
    for el in ("wizard", "modal"):
        assert style(el, "background-color") == "rgb(44, 44, 44)", el
    assert style("progress", "background-color") == "rgb(17, 17, 17)"
    for el in ("comment-body", "preview"):
        assert style(el, "background-color") == "rgb(255, 255, 255)", el
        assert style(el, "color") == "rgb(32, 38, 48)", el
    for el in ("danger", "diff"):
        assert style(el, "background-color") == baseline[el, "background-color"], el
    for el in ("tag-button", "tag-label", "tag-remove", "tag-close"):
        assert style(el, "color") == "rgb(245, 245, 245)", el
    assert style("activity-header", "background-color") == "rgb(44, 44, 44)"
    assert style("activity-header", "background-image") == "none"
    for el in ("activity-item", "activity-body"):
        assert style(el, "background-color") == "rgb(36, 36, 36)", el
    for el in ("activity-user", "activity-action", "activity-body", "activity-notes"):
        assert style(el, "color") == "rgb(245, 245, 245)", el
    for el in ("activity-comment", "activity-date"):
        assert style(el, "color") == "rgb(196, 196, 196)", el
    assert style("activity-details", "color") == "rgb(161, 221, 250)"
    assert style("activity-icon", "background-image") == baseline["activity-icon", "background-image"]
    page.locator("#input").focus()
    assert style("input", "outline-style") == "solid"
    assert style("input", "outline-color") == "rgb(146, 209, 83)"
    page.emulate_media(media="print")
    assert style("panel", "background-color") == print_before
    for (el, prop), expected in admin_baseline.items():
        assert style(el, prop) == expected, (el, prop)
    for el, prop in (("template-list", "background-color"), ("template-odd", "background-color"),
                     ("template-even", "background-color"), ("template-even", "border-bottom-color"),
                     ("template-name", "color"), ("template-even-name", "color")):
        assert style(el, prop) == baseline[el, prop], (el, prop)
    assert style("activity-header", "background-color") == baseline["activity-header", "background-color"]
    assert style("simple-cell", "background-color") == baseline["simple-cell", "background-color"]
    assert style("history-panel", "background-color") == baseline["history-panel", "background-color"]
    assert style("gray-icon", "filter") == "none"
    assert style("tool-icon", "filter") == "none"
    page.emulate_media(media="screen")
    # Exercise the optional layout separately, without the dark style installed.
    page.goto("https://example.test/layout-test", wait_until="domcontentloaded")
    layout_source = (ROOT / "jama-form-row.user.css").read_text(encoding="utf-8")
    layout_inner = layout_source[layout_source.index("{", layout_source.index("@-moz-document")) + 1:layout_source.rfind("}")]
    page.add_style_tag(content=layout_inner)
    page.set_viewport_size({"width": 1200, "height": 800})
    assert style("layout-control", "display") == "grid"
    assert len(style("layout-control", "grid-template-columns").split()) == 2
    assert style("layout-label", "text-align") == "right"
    assert style("layout-value-wrap", "display") == "grid"
    assert style("layout-text", "overflow-x") == "auto"
    assert style("layout-category", "display") == "block"
    page.set_viewport_size({"width": 600, "height": 800})
    assert len(style("layout-control", "grid-template-columns").split()) == 1
    assert style("layout-label", "text-align") == "right"
    assert style("layout-category", "display") == "block"
    page.emulate_media(media="print")
    assert style("layout-control", "display") == "block"
    browser.close()

print("PASS: CSS syntax/domain wrapper; panels, headers, trees, selection, disabled states, input error border;")
print("      combo/calendar/form/notification/wizard/progress/lookup/comment/modal/activity/admin-nav/simple-grid/striped-list/history-panel/layout fixtures;")
print("      preserved rich text, authored color, status/diff/danger fills, image sprite, focus, and print isolation.")
print("Synthetic fixture only; live Jama screens and Stylus installation still need manual verification.")
