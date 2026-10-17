"""Forming Worlds Lab theme for Documenter.jl sites.

The stylesheet keeps the stock ``documenter-light`` and ``documenter-dark``
layouts and changes only their colours and type: the lab roles and figure
palette from the tokens, Geist for text and Geist Mono for code. Greek letters,
which Geist lacks, come from Inter; its faces carry a Greek ``unicode-range``,
so a browser downloads them only for pages that use Greek. Variables are named
``--fwl-doc-*`` so the sheet can load next to ``fwl-tokens.css``.

Install it into the ``assets`` folder of a Documenter source tree::

    python -m fwl_visual_language.documenter docs/src/assets

and list ``"assets/fwl.css"`` in ``Documenter.HTML(; assets=[...])``. The
catppuccin themes keep their own colours.
"""

import argparse

from . import __version__, palette, roles
from ._web import font_faces_css, font_stack, install, mix, text_safe

__all__ = ["documenter_css", "install_documenter_theme"]

CSS_NAME = "fwl.css"

# Scope per mode: the primary light theme has no theme class on <html> until a
# reader picks a theme in the settings dialog, which then sets theme--<name>.
_MODE_SELECTOR = {
    "light": 'html:not([class*="theme--"]), html.theme--documenter-light',
    "dark": "html.theme--documenter-dark",
}
_SCOPE = ":is(" + ", ".join(_MODE_SELECTOR.values()) + ")"

# Documenter admonition kind -> palette hue; warnings take magma as on the website.
_ADMONITIONS = {
    "info": "signal",
    "success": "fern",
    "warning": "magma",
    "danger": "garnet",
    "compat": "lagoon",
    "todo": "iris",
}

# highlight.js token class -> palette hue, or "text" / "muted".
_SYNTAX = {
    "keyword": "iris",
    "string": "fern",
    "number": "magma",
    "literal": "magma",
    "title": "signal",
    "name": "signal",
    "tag": "signal",
    "link": "signal",
    "selector-tag": "signal",
    "selector-id": "signal",
    "selector-class": "signal",
    "built_in": "lagoon",
    "type": "lagoon",
    "template-variable": "lagoon",
    "selector-attr": "lagoon",
    "selector-pseudo": "lagoon",
    "attr": "ochre",
    "attribute": "ochre",
    "symbol": "ochre",
    "bullet": "ochre",
    "meta": "garnet",
    "section": "garnet",
    "regexp": "garnet",
    "variable": "text",
    "params": "text",
    "subst": "text",
    "operator": "text",
    "punctuation": "text",
    "code": "text",
    "comment": "muted",
    "quote": "muted",
    "doctag": "muted",
}

# Docs are web pages: the light mode uses the website's mist roles.
_ROLE_MODE = {"light": "light", "dark": "dark"}


def _tokens(mode):
    """Resolve the colour tokens of one mode from the lab roles and palette."""
    r = roles(_ROLE_MODE[mode])
    bg, ink = r["background"], r["text"]
    sub = mix(bg, ink, 0.045 if mode == "light" else 0.06)
    hover = mix(bg, ink, 0.09)
    hues = {n: c for n, c in palette(_ROLE_MODE[mode]) if n != "ink"}
    washes = {n: mix(bg, c, 0.1) for n, c in hues.items()}
    # Every text colour must read on every surface it can sit on.
    surfaces = (bg, sub, hover, *washes.values())
    safe = {n: text_safe(c, ink, surfaces) for n, c in hues.items()}
    return {
        "bg": bg,
        "sub": sub,
        "ink": ink,
        "muted": text_safe(r["muted"], ink, surfaces),
        "line": r["line"],
        "hover": hover,
        "link": text_safe(r["link"], ink, surfaces),
        "hues": hues,
        "washes": washes,
        "surfaces": surfaces,
        "safe": safe,
    }


def _variables(mode):
    t = _tokens(mode)
    lines = [
        f"  --fwl-doc-bg: {t['bg']};",
        f"  --fwl-doc-sub: {t['sub']};",
        f"  --fwl-doc-text: {t['ink']};",
        f"  --fwl-doc-muted: {t['muted']};",
        f"  --fwl-doc-line: {t['line']};",
        f"  --fwl-doc-hover: {t['hover']};",
        f"  --fwl-doc-link: {t['link']};",
    ]
    for name, color in t["safe"].items():
        lines.append(f"  --fwl-doc-{name}: {color};")
    for name, color in t["hues"].items():
        lines.append(f"  --fwl-doc-{name}-fill: {color};")
        lines.append(f"  --fwl-doc-{name}-wash: {t['washes'][name]};")
    # The bundled faces stop at Geist 600 and Mono 500: no faux bold or italic.
    lines += ["  background-color: var(--fwl-doc-bg);", "  font-synthesis: none;"]
    return f"{_MODE_SELECTOR[mode]} {{\n" + "\n".join(lines) + "\n}\n"


SANS = font_stack("text")
MONO = font_stack("mono", extra=("JuliaMono",))

_SB = "#documenter .docs-sidebar"
_MENU = f"{_SB} ul.docs-menu"
_HEADINGS = [f".content h{i}" for i in range(1, 7)]

# (selectors, declarations). Each rule repeats the stock selector under _SCOPE, which
# adds (0,1,1): it outranks unscoped stock rules and ties html.theme--* ones, which
# it then wins by loading after the themes.
_RULES = [
    # Page, type and text
    (
        ["body", "#documenter .docs-main", "#documenter .docs-main article", ".content"],
        [
            "background-color: var(--fwl-doc-bg)",
            "color: var(--fwl-doc-text)",
            f"font-family: {SANS}",
        ],
    ),
    (["button", "input", "optgroup", "select", "textarea"], [f"font-family: {SANS}"]),
    (_HEADINGS, ["color: var(--fwl-doc-text)", "font-weight: 500", "letter-spacing: -0.005em"]),
    ([f"{h} a.docs-heading-anchor" for h in _HEADINGS], ["color: inherit"]),
    ([f"{h} a.docs-heading-anchor code" for h in _HEADINGS], ["color: var(--fwl-doc-text)"]),
    ([".content strong", ".content b", "th"], ["color: inherit", "font-weight: 500"]),
    ([".content a", ".content a code", ".content a:hover code"], ["color: var(--fwl-doc-link)"]),
    ([".content a:hover"], ["color: var(--fwl-doc-link)", "text-decoration: underline"]),
    (
        [".content hr", ".modal-card-body hr"],
        ["background-color: var(--fwl-doc-line)", "border: 0"],
    ),
    (
        [".content blockquote"],
        [
            "background-color: transparent",
            "border-left: 3px solid var(--fwl-doc-signal-fill)",
            "color: var(--fwl-doc-muted)",
        ],
    ),
    (
        [".content table", ".content table th", ".content table td"],
        ["border-color: var(--fwl-doc-line)", "color: var(--fwl-doc-text)"],
    ),
    (
        [".content table thead th", ".content table thead td"],
        ["background-color: var(--fwl-doc-sub)", "color: var(--fwl-doc-text)"],
    ),
    ([".content table tbody tr:hover"], ["background-color: var(--fwl-doc-sub)"]),
    # Bulma removes the outline on focused controls; keyboard focus must stay visible.
    (
        [":focus-visible"],
        ["outline: 2px solid var(--fwl-doc-signal-fill) !important", "outline-offset: 2px"],
    ),
    # Navbar, breadcrumb, footer, footnotes, banners
    (
        ["#documenter .docs-main header.docs-navbar"],
        ["background-color: var(--fwl-doc-bg)", "border-color: var(--fwl-doc-line)"],
    ),
    (
        ["#documenter .docs-main header.docs-navbar a", ".breadcrumb a"],
        ["color: var(--fwl-doc-text)"],
    ),
    ([".breadcrumb li + li::before"], ["color: var(--fwl-doc-muted)"]),
    (
        ["#documenter .docs-main .docs-footer"],
        ["border-top-color: var(--fwl-doc-line)", "color: var(--fwl-doc-muted)"],
    ),
    (["#documenter .docs-main .docs-footer a"], ["color: var(--fwl-doc-link)"]),
    (["#documenter .docs-main section.footnotes"], ["border-top-color: var(--fwl-doc-line)"]),
    (
        [".footnote-preview"],
        [
            "background-color: var(--fwl-doc-bg)",
            "border-color: var(--fwl-doc-line)",
            "color: var(--fwl-doc-text)",
        ],
    ),
    ([".footnote-preview::before"], ["border-bottom-color: var(--fwl-doc-line)"]),
    ([".footnote-preview.is-above::before"], ["border-top-color: var(--fwl-doc-line)"]),
    (
        [".content section.footnotes a.tag.is-link:not(body)"],
        ["background-color: var(--fwl-doc-sub)", "color: var(--fwl-doc-link)"],
    ),
    (
        [".outdated-warning-overlay", ".dev-warning-overlay"],
        [
            "background-color: var(--fwl-doc-sub)",
            "border-color: var(--fwl-doc-line)",
            "color: var(--fwl-doc-text)",
            "box-shadow: none",
        ],
    ),
    (
        [
            ".outdated-warning-overlay a",
            ".outdated-warning-overlay a:hover",
            ".dev-warning-overlay a",
            ".dev-warning-overlay a:hover",
        ],
        ["color: var(--fwl-doc-link)"],
    ),
    # Sidebar
    (
        [_SB],
        [
            "background-color: var(--fwl-doc-sub)",
            "border-right: 1px solid var(--fwl-doc-line)",
            "color: var(--fwl-doc-text)",
        ],
    ),
    (
        [
            f"{_SB} .docs-package-name",
            f"{_SB} .docs-package-name a",
            f"{_SB} .docs-package-name a:hover",
        ],
        [
            "color: var(--fwl-doc-text)",
            "font-weight: 500",
            "border-bottom-color: var(--fwl-doc-line)",
        ],
    ),
    (
        [f"{_MENU} .tocitem", f"{_MENU} .tocitem:hover"],
        ["background: transparent", "color: var(--fwl-doc-text)"],
    ),
    ([_MENU, f"{_MENU} ul.internal"], ["border-top-color: var(--fwl-doc-line)"]),
    ([f"{_MENU} > li li"], ["border-left-color: var(--fwl-doc-line)"]),
    (
        [f"{_MENU} a.tocitem:hover", f"{_MENU} label.tocitem:hover"],
        ["background-color: var(--fwl-doc-hover)", "color: var(--fwl-doc-text)"],
    ),
    (
        [
            f"{_MENU} li.is-active",
            f"{_MENU} li.is-active .tocitem",
            f"{_MENU} li.is-active .tocitem:hover",
        ],
        ["background: var(--fwl-doc-bg)", "color: var(--fwl-doc-text)"],
    ),
    (
        [f"{_MENU} li.is-active ul.internal .tocitem:hover"],
        ["background: var(--fwl-doc-hover)", "color: var(--fwl-doc-text)"],
    ),
    (
        [f"{_MENU} li.is-active"],
        ["border-top-color: var(--fwl-doc-line)", "border-bottom-color: var(--fwl-doc-line)"],
    ),
    ([f"{_MENU}::-webkit-scrollbar-thumb"], ["background: var(--fwl-doc-line)"]),
    ([f"{_MENU}::-webkit-scrollbar-thumb:hover"], ["background: var(--fwl-doc-muted)"]),
    (
        [
            "#search-modal .modal-card-body::-webkit-scrollbar-thumb",
            "#search-modal .filter-tabs::-webkit-scrollbar-thumb",
        ],
        ["background: var(--fwl-doc-line)"],
    ),
    (
        [f"{_SB} #documenter-search-query"],
        [
            "background-color: var(--fwl-doc-bg)",
            "border: 1px solid var(--fwl-doc-line)",
            "color: var(--fwl-doc-muted)",
        ],
    ),
    ([f"{_SB} .docs-version-selector"], ["border-top-color: var(--fwl-doc-line)"]),
    (
        [f"{_SB} .docs-version-selector .button.is-static", f"{_SB} .docs-version-selector select"],
        [
            "background-color: var(--fwl-doc-bg)",
            "border-color: var(--fwl-doc-line)",
            "color: var(--fwl-doc-muted)",
        ],
    ),
    # Settings and search dialogs
    (
        [".modal-card-head", ".modal-card-body", ".modal-card-foot"],
        [
            "background-color: var(--fwl-doc-bg)",
            "border-color: var(--fwl-doc-line)",
            "color: var(--fwl-doc-text)",
        ],
    ),
    ([".modal-card-title", ".modal-card-body .label"], ["color: var(--fwl-doc-text)"]),
    ([".modal-card-body a"], ["color: var(--fwl-doc-link)"]),
    (
        [".select select", ".input", ".textarea"],
        [
            "background-color: var(--fwl-doc-bg)",
            "border-color: var(--fwl-doc-line)",
            "color: var(--fwl-doc-text)",
        ],
    ),
    (
        # Bulma sets this utility colour with !important, so only !important beats it.
        [".modal-card .has-text-primary-dark"],
        ["color: var(--fwl-doc-link) !important"],
    ),
    ([".link-icon", ".link-icon:hover"], ["color: var(--fwl-doc-link)"]),
    ([".input::placeholder", ".textarea::placeholder"], ["color: var(--fwl-doc-muted)"]),
    (
        [".select:not(.is-multiple):not(.is-loading)::after"],
        ["border-color: var(--fwl-doc-muted)"],
    ),
    (
        [".select:not(.is-multiple):not(.is-loading):hover::after"],
        ["border-color: var(--fwl-doc-text)"],
    ),
    (
        [".input:focus", ".textarea:focus", ".select select:focus"],
        [
            "border-color: var(--fwl-doc-signal-fill)",
            "box-shadow: 0 0 0 0.125em var(--fwl-doc-signal-wash)",
        ],
    ),
    (
        ["kbd.search-modal-key-hints"],
        ["border-color: var(--fwl-doc-line)", "box-shadow: 0 2px 0 1px var(--fwl-doc-line)"],
    ),
    ([".search-result-link"], ["color: var(--fwl-doc-text)"]),
    (
        [".search-result-link:hover", ".search-result-link:focus"],
        ["background-color: var(--fwl-doc-hover)", "border-color: var(--fwl-doc-line)"],
    ),
    ([".search-divider"], ["border-bottom-color: var(--fwl-doc-line)"]),
    ([".search-result-title"], ["color: var(--fwl-doc-text)"]),
    (
        [".property-search-result-badge", ".search-filter"],
        ["background-color: var(--fwl-doc-sub)", "color: var(--fwl-doc-text)"],
    ),
    (
        [".search-filter:hover", ".search-filter:focus"],
        ["background-color: var(--fwl-doc-hover)", "color: var(--fwl-doc-text)"],
    ),
    (
        [
            ".search-filter-selected",
            ".search-filter-selected:hover",
            ".search-filter-selected:focus",
        ],
        ["background-color: var(--fwl-doc-signal-wash)", "color: var(--fwl-doc-text)"],
    ),
    (
        # The light theme sets these with !important.
        [
            f".search-result-link:{state} .{badge}"
            for state in ("hover", "focus")
            for badge in ("property-search-result-badge", "search-filter")
        ],
        [
            "background-color: var(--fwl-doc-line) !important",
            "color: var(--fwl-doc-text) !important",
        ],
    ),
    (
        [".search-result-highlight"],
        ["background-color: var(--fwl-doc-ochre-wash)", "color: var(--fwl-doc-text)"],
    ),
    # Code
    (
        [".content code", ".content kbd:not(body)", ".content samp"],
        [
            "background-color: var(--fwl-doc-sub)",
            "color: var(--fwl-doc-text)",
            f"font-family: {MONO}",
        ],
    ),
    (
        [".content pre", ".content pre code", ".hljs", ".content pre code.hljs"],
        ["background-color: var(--fwl-doc-sub)", "color: var(--fwl-doc-text)"],
    ),
    ([".content pre"], ["border: 1px solid var(--fwl-doc-line)", "border-radius: 4px"]),
    (["pre .copy-button"], ["color: var(--fwl-doc-muted)"]),
    (
        ["pre .copy-button:hover", "pre .copy-button:focus"],
        ["color: var(--fwl-doc-link)", "background: var(--fwl-doc-hover)"],
    ),
    (["pre .copy-button.success"], ["color: var(--fwl-doc-fern)"]),
    (["pre .copy-button.error"], ["color: var(--fwl-doc-garnet)"]),
    ([".content pre code"], ["border: 0"]),
    *[([f".hljs-{token}"], [f"color: var(--fwl-doc-{hue})"]) for token, hue in _SYNTAX.items()],
    (["code.language-julia-repl > span.hljs-meta"], ["color: var(--fwl-doc-fern)"]),
    (
        [".hljs-addition"],
        ["color: var(--fwl-doc-fern)", "background-color: var(--fwl-doc-fern-wash)"],
    ),
    (
        [".hljs-deletion"],
        ["color: var(--fwl-doc-garnet)", "background-color: var(--fwl-doc-garnet-wash)"],
    ),
    # Admonitions: the base style serves custom categories and details blocks
    (
        [".admonition"],
        [
            "border-color: var(--fwl-doc-line)",
            "background-color: var(--fwl-doc-sub)",
            "border-radius: 4px",
        ],
    ),
    (
        [".admonition-header .admonition-anchor"],
        ["color: inherit"],
    ),
    (
        [".admonition > .admonition-header"],
        ["color: var(--fwl-doc-muted)", "background-color: transparent", "font-weight: 500"],
    ),
    (
        [".admonition > .admonition-body"],
        ["color: var(--fwl-doc-text)", "background-color: transparent"],
    ),
    *[
        rule
        for kind, hue in _ADMONITIONS.items()
        for rule in (
            (
                [f".admonition.is-{kind}"],
                [
                    f"border-color: var(--fwl-doc-{hue}-fill)",
                    f"background-color: var(--fwl-doc-{hue}-wash)",
                ],
            ),
            ([f".admonition.is-{kind} > .admonition-header"], [f"color: var(--fwl-doc-{hue})"]),
            ([f".admonition.is-{kind} > .admonition-body"], ["color: var(--fwl-doc-text)"]),
        )
    ],
    # Docstrings
    (
        ["details.docstring"],
        [
            "border: 1px solid var(--fwl-doc-line)",
            "border-radius: 4px",
            "background-color: transparent",
        ],
    ),
    (
        ["details.docstring > summary"],
        [
            "background-color: var(--fwl-doc-sub)",
            "border-bottom-color: var(--fwl-doc-line)",
            "color: var(--fwl-doc-text)",
        ],
    ),
    (
        ["details.docstring > summary::before", ".docstring-category"],
        ["color: var(--fwl-doc-muted)"],
    ),
    (
        [
            "details.docstring > section > a.docs-sourcelink:not(body)",
            "details.docstring > section > a.docs-sourcelink:not(body):hover",
        ],
        [
            "background-color: var(--fwl-doc-hover)",
            "border-color: transparent",
            "color: var(--fwl-doc-text)",
        ],
    ),
]


def _rule(selectors, declarations):
    """Format one rule whose selectors all sit under the two-mode scope."""
    sel = ",\n".join(f"{_SCOPE} {s}" for s in selectors)
    body = "\n".join(f"  {d};" for d in declarations)
    return f"{sel} {{\n{body}\n}}\n"


def documenter_css():
    """Return the stylesheet text for Documenter.jl, light and dark.

    Returns
    -------
    str
        CSS that restyles ``documenter-light`` and ``documenter-dark``. It refers
        to the fonts as ``fwl-fonts/<file>`` next to the stylesheet.
    """
    header = (
        f"/* Forming Worlds Lab theme for Documenter.jl (fwl-visual-language {__version__}, "
        "Documenter.jl 1.19 class names). Generated by fwl_visual_language.documenter "
        "from the lab tokens; edit the generator, not this file. */\n"
    )
    parts = [header, font_faces_css(), _variables("light"), _variables("dark")]
    parts += [_rule(sel, decl) for sel, decl in _RULES]
    return "\n".join(parts)


def install_documenter_theme(dest):
    """Write the stylesheet, the fonts and their licences into ``dest``.

    Parameters
    ----------
    dest : str or pathlib.Path
        Target folder, normally ``docs/src/assets`` of a Documenter source tree.
        It is created if it does not exist.

    Returns
    -------
    pathlib.Path
        Path of the written stylesheet. Existing files of the same names are
        replaced.

    Raises
    ------
    OSError
        If ``dest`` exists and is not a folder, or cannot be written.
    """
    return install(dest, CSS_NAME, documenter_css())


def main(argv=None):
    """Command line entry point: ``python -m fwl_visual_language.documenter DEST``."""
    parser = argparse.ArgumentParser(
        prog="python -m fwl_visual_language.documenter",
        description="Write the Forming Worlds Lab Documenter.jl stylesheet and fonts.",
    )
    parser.add_argument("dest", help="assets folder of the Documenter source tree")
    args = parser.parse_args(argv)
    print(install_documenter_theme(args.dest))


if __name__ == "__main__":
    main()
