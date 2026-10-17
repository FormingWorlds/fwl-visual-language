"""Forming Worlds Lab theme for Documenter.jl sites.

The stylesheet keeps the stock ``documenter-light`` and ``documenter-dark``
layouts and changes only their colours and type: the lab roles and figure
palette from the tokens, Geist for text and Geist Mono for code. Greek letters,
which Geist lacks, come from Inter; its faces carry a Greek ``unicode-range``,
so a browser downloads them only for pages that use Greek.

Install it into the ``assets`` folder of a Documenter source tree::

    python -m fwl_visual_language.documenter docs/src/assets

and list ``"assets/fwl.css"`` in ``Documenter.HTML(; assets=[...])``. The
catppuccin themes keep their own colours.
"""

import argparse
import shutil
from pathlib import Path

from . import __version__, contrast, fonts_dir, palette, roles

__all__ = ["documenter_css", "install_documenter_theme"]

CSS_NAME = "fwl.css"
FONT_DIR = "fwl-fonts"
MIN_CONTRAST = 4.5

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

_GREEK = "U+0370-03FF, U+1F00-1FFF"
# (family, file, style, weight, unicode-range or None)
_FONT_FACES = (
    ("Geist", "Geist-Regular.woff2", "normal", 400, None),
    ("Geist", "Geist-Italic.woff2", "italic", 400, None),
    ("Geist", "Geist-Medium.woff2", "normal", 500, None),
    ("Geist", "Geist-MediumItalic.woff2", "italic", 500, None),
    ("Geist", "Geist-SemiBold.woff2", "normal", 600, None),
    ("Geist Mono", "GeistMono-Regular.woff2", "normal", 400, None),
    ("Geist Mono", "GeistMono-Medium.woff2", "normal", 500, None),
    ("Inter", "Inter-Regular.woff2", "normal", 400, _GREEK),
    ("Inter", "Inter-Italic.woff2", "italic", 400, _GREEK),
)
_LICENCES = ("OFL-Geist.txt", "OFL-Inter.txt")

# Docs are web pages: the light mode uses the website's mist roles.
_ROLE_MODE = {"light": "light", "dark": "dark"}


def _rgb(hex_color):
    h = hex_color.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def _hex(rgb):
    return "#" + "".join(f"{round(max(0, min(255, c))):02X}" for c in rgb)


def _mix(a, b, t):
    """Return the colour a fraction ``t`` of the way from ``a`` to ``b`` (sRGB)."""
    return _hex(tuple(x + (y - x) * t for x, y in zip(_rgb(a), _rgb(b), strict=True)))


def _text_safe(color, ink, backgrounds):
    """Move ``color`` toward ``ink`` until it reads at 4.5:1 on every background."""
    for step in range(101):
        out = _mix(color, ink, step / 100)
        if all(contrast(out, bg) >= MIN_CONTRAST for bg in backgrounds):
            return out
    return ink


def _tokens(mode):
    """Resolve the colour tokens of one mode from the lab roles and palette."""
    r = roles(_ROLE_MODE[mode])
    bg, ink = r["background"], r["text"]
    sub = _mix(bg, ink, 0.045 if mode == "light" else 0.06)
    hover = _mix(bg, ink, 0.09)
    hues = {n: c for n, c in palette(_ROLE_MODE[mode]) if n != "ink"}
    washes = {n: _mix(bg, c, 0.1) for n, c in hues.items()}
    # Every text colour must read on every surface it can sit on.
    surfaces = (bg, sub, hover, *washes.values())
    safe = {n: _text_safe(c, ink, surfaces) for n, c in hues.items()}
    return {
        "bg": bg,
        "sub": sub,
        "ink": ink,
        "muted": _text_safe(r["muted"], ink, surfaces),
        "line": r["line"],
        "hover": hover,
        "link": _text_safe(r["link"], ink, surfaces),
        "hues": hues,
        "washes": washes,
        "surfaces": surfaces,
        "safe": safe,
    }


def _variables(mode):
    t = _tokens(mode)
    lines = [
        f"  --fwl-bg: {t['bg']};",
        f"  --fwl-sub: {t['sub']};",
        f"  --fwl-text: {t['ink']};",
        f"  --fwl-muted: {t['muted']};",
        f"  --fwl-line: {t['line']};",
        f"  --fwl-hover: {t['hover']};",
        f"  --fwl-link: {t['link']};",
    ]
    for name, color in t["safe"].items():
        lines.append(f"  --fwl-{name}: {color};")
    for name, color in t["hues"].items():
        lines.append(f"  --fwl-{name}-fill: {color};")
        lines.append(f"  --fwl-{name}-wash: {t['washes'][name]};")
    # The bundled faces stop at Geist 600 and Mono 500: no faux bold or italic.
    lines += ["  background-color: var(--fwl-bg);", "  font-synthesis: none;"]
    return f"{_MODE_SELECTOR[mode]} {{\n" + "\n".join(lines) + "\n}\n"


def _font_faces():
    out = []
    for family, file, style, weight, urange in _FONT_FACES:
        extra = f"  unicode-range: {urange};\n" if urange else ""
        out.append(
            "@font-face {\n"
            f'  font-family: "{family}";\n'
            f'  src: url("{FONT_DIR}/{file}") format("woff2");\n'
            f"  font-style: {style};\n"
            f"  font-weight: {weight};\n"
            f"{extra}"
            "  font-display: swap;\n"
            "}\n"
        )
    return "\n".join(out)


SANS = (
    '"Geist", "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif'
)
MONO = '"Geist Mono", JuliaMono, "SFMono-Regular", Menlo, Consolas, monospace'

_SB = "#documenter .docs-sidebar"
_MENU = f"{_SB} ul.docs-menu"
_HEADINGS = [f".content h{i}" for i in range(1, 7)]

# (selectors, declarations). Selectors repeat the stock selectors they override, so
# they reach the same specificity and win the tie by loading after the themes.
_RULES = [
    # Page, type and text
    (
        ["body", "#documenter .docs-main", "#documenter .docs-main article", ".content"],
        ["background-color: var(--fwl-bg)", "color: var(--fwl-text)", f"font-family: {SANS}"],
    ),
    (["button", "input", "optgroup", "select", "textarea"], [f"font-family: {SANS}"]),
    (_HEADINGS, ["color: var(--fwl-text)", "font-weight: 500", "letter-spacing: -0.005em"]),
    ([f"{h} a.docs-heading-anchor" for h in _HEADINGS], ["color: inherit"]),
    ([f"{h} a.docs-heading-anchor code" for h in _HEADINGS], ["color: var(--fwl-text)"]),
    ([".content strong", ".content b", "th"], ["color: inherit", "font-weight: 500"]),
    ([".content a", ".content a code", ".content a:hover code"], ["color: var(--fwl-link)"]),
    ([".content a:hover"], ["color: var(--fwl-link)", "text-decoration: underline"]),
    ([".content hr", ".modal-card-body hr"], ["background-color: var(--fwl-line)", "border: 0"]),
    (
        [".content blockquote"],
        [
            "background-color: transparent",
            "border-left: 3px solid var(--fwl-signal-fill)",
            "color: var(--fwl-muted)",
        ],
    ),
    (
        [".content table", ".content table th", ".content table td"],
        ["border-color: var(--fwl-line)", "color: var(--fwl-text)"],
    ),
    (
        [".content table thead th", ".content table thead td"],
        ["background-color: var(--fwl-sub)", "color: var(--fwl-text)"],
    ),
    ([".content table tbody tr:hover"], ["background-color: var(--fwl-sub)"]),
    # Bulma removes the outline on focused controls; keyboard focus must stay visible.
    (
        [":focus-visible"],
        ["outline: 2px solid var(--fwl-signal-fill) !important", "outline-offset: 2px"],
    ),
    # Navbar, breadcrumb, footer, footnotes, banners
    (
        ["#documenter .docs-main header.docs-navbar"],
        ["background-color: var(--fwl-bg)", "border-color: var(--fwl-line)"],
    ),
    (["#documenter .docs-main header.docs-navbar a", ".breadcrumb a"], ["color: var(--fwl-text)"]),
    ([".breadcrumb li + li::before"], ["color: var(--fwl-muted)"]),
    (
        ["#documenter .docs-main .docs-footer"],
        ["border-top-color: var(--fwl-line)", "color: var(--fwl-muted)"],
    ),
    (["#documenter .docs-main .docs-footer a"], ["color: var(--fwl-link)"]),
    (["#documenter .docs-main section.footnotes"], ["border-top-color: var(--fwl-line)"]),
    (
        [".footnote-preview"],
        [
            "background-color: var(--fwl-bg)",
            "border-color: var(--fwl-line)",
            "color: var(--fwl-text)",
        ],
    ),
    ([".footnote-preview::before"], ["border-bottom-color: var(--fwl-line)"]),
    ([".footnote-preview.is-above::before"], ["border-top-color: var(--fwl-line)"]),
    (
        [".content section.footnotes a.tag.is-link:not(body)"],
        ["background-color: var(--fwl-sub)", "color: var(--fwl-link)"],
    ),
    (
        [".outdated-warning-overlay", ".dev-warning-overlay"],
        [
            "background-color: var(--fwl-sub)",
            "border-color: var(--fwl-line)",
            "color: var(--fwl-text)",
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
        ["color: var(--fwl-link)"],
    ),
    # Sidebar
    (
        [_SB],
        [
            "background-color: var(--fwl-sub)",
            "border-right: 1px solid var(--fwl-line)",
            "color: var(--fwl-text)",
        ],
    ),
    (
        [
            f"{_SB} .docs-package-name",
            f"{_SB} .docs-package-name a",
            f"{_SB} .docs-package-name a:hover",
        ],
        ["color: var(--fwl-text)", "font-weight: 500", "border-bottom-color: var(--fwl-line)"],
    ),
    (
        [f"{_MENU} .tocitem", f"{_MENU} .tocitem:hover"],
        ["background: transparent", "color: var(--fwl-text)"],
    ),
    ([_MENU, f"{_MENU} ul.internal"], ["border-top-color: var(--fwl-line)"]),
    ([f"{_MENU} > li li"], ["border-left-color: var(--fwl-line)"]),
    (
        [f"{_MENU} a.tocitem:hover", f"{_MENU} label.tocitem:hover"],
        ["background-color: var(--fwl-hover)", "color: var(--fwl-text)"],
    ),
    (
        [
            f"{_MENU} li.is-active",
            f"{_MENU} li.is-active .tocitem",
            f"{_MENU} li.is-active .tocitem:hover",
        ],
        ["background: var(--fwl-bg)", "color: var(--fwl-text)"],
    ),
    (
        [f"{_MENU} li.is-active ul.internal .tocitem:hover"],
        ["background: var(--fwl-hover)", "color: var(--fwl-text)"],
    ),
    (
        [f"{_MENU} li.is-active"],
        ["border-top-color: var(--fwl-line)", "border-bottom-color: var(--fwl-line)"],
    ),
    ([f"{_MENU}::-webkit-scrollbar-thumb"], ["background: var(--fwl-line)"]),
    ([f"{_MENU}::-webkit-scrollbar-thumb:hover"], ["background: var(--fwl-muted)"]),
    (
        [
            "#search-modal .modal-card-body::-webkit-scrollbar-thumb",
            "#search-modal .filter-tabs::-webkit-scrollbar-thumb",
        ],
        ["background: var(--fwl-line)"],
    ),
    (
        [f"{_SB} #documenter-search-query"],
        [
            "background-color: var(--fwl-bg)",
            "border: 1px solid var(--fwl-line)",
            "color: var(--fwl-muted)",
        ],
    ),
    ([f"{_SB} .docs-version-selector"], ["border-top-color: var(--fwl-line)"]),
    (
        [f"{_SB} .docs-version-selector .button.is-static", f"{_SB} .docs-version-selector select"],
        [
            "background-color: var(--fwl-bg)",
            "border-color: var(--fwl-line)",
            "color: var(--fwl-muted)",
        ],
    ),
    # Settings and search dialogs
    (
        [".modal-card-head", ".modal-card-body", ".modal-card-foot"],
        [
            "background-color: var(--fwl-bg)",
            "border-color: var(--fwl-line)",
            "color: var(--fwl-text)",
        ],
    ),
    ([".modal-card-title", ".modal-card-body .label"], ["color: var(--fwl-text)"]),
    ([".modal-card-body a"], ["color: var(--fwl-link)"]),
    (
        [".select select", ".input", ".textarea"],
        [
            "background-color: var(--fwl-bg)",
            "border-color: var(--fwl-line)",
            "color: var(--fwl-text)",
        ],
    ),
    (
        # Bulma sets this utility colour with !important, so only !important beats it.
        [".modal-card .has-text-primary-dark"],
        ["color: var(--fwl-link) !important"],
    ),
    ([".link-icon", ".link-icon:hover"], ["color: var(--fwl-link)"]),
    ([".input::placeholder", ".textarea::placeholder"], ["color: var(--fwl-muted)"]),
    (
        [".select:not(.is-multiple):not(.is-loading)::after"],
        ["border-color: var(--fwl-muted)"],
    ),
    (
        [".select:not(.is-multiple):not(.is-loading):hover::after"],
        ["border-color: var(--fwl-text)"],
    ),
    (
        [".input:focus", ".textarea:focus", ".select select:focus"],
        [
            "border-color: var(--fwl-signal-fill)",
            "box-shadow: 0 0 0 0.125em var(--fwl-signal-wash)",
        ],
    ),
    (
        ["kbd.search-modal-key-hints"],
        ["border-color: var(--fwl-line)", "box-shadow: 0 2px 0 1px var(--fwl-line)"],
    ),
    ([".search-result-link"], ["color: var(--fwl-text)"]),
    (
        [".search-result-link:hover", ".search-result-link:focus"],
        ["background-color: var(--fwl-hover)", "border-color: var(--fwl-line)"],
    ),
    ([".search-divider"], ["border-bottom-color: var(--fwl-line)"]),
    ([".search-result-title"], ["color: var(--fwl-text)"]),
    (
        [".property-search-result-badge", ".search-filter"],
        ["background-color: var(--fwl-sub)", "color: var(--fwl-text)"],
    ),
    (
        [".search-filter:hover", ".search-filter:focus"],
        ["background-color: var(--fwl-hover)", "color: var(--fwl-text)"],
    ),
    (
        [
            ".search-filter-selected",
            ".search-filter-selected:hover",
            ".search-filter-selected:focus",
        ],
        ["background-color: var(--fwl-signal-wash)", "color: var(--fwl-text)"],
    ),
    (
        # The light theme sets these with !important.
        [
            f".search-result-link:{state} .{badge}"
            for state in ("hover", "focus")
            for badge in ("property-search-result-badge", "search-filter")
        ],
        ["background-color: var(--fwl-line) !important", "color: var(--fwl-text) !important"],
    ),
    (
        [".search-result-highlight"],
        ["background-color: var(--fwl-ochre-wash)", "color: var(--fwl-text)"],
    ),
    # Code
    (
        [".content code", ".content kbd:not(body)", ".content samp"],
        ["background-color: var(--fwl-sub)", "color: var(--fwl-text)", f"font-family: {MONO}"],
    ),
    (
        [".content pre", ".content pre code", ".hljs", ".content pre code.hljs"],
        ["background-color: var(--fwl-sub)", "color: var(--fwl-text)"],
    ),
    ([".content pre"], ["border: 1px solid var(--fwl-line)", "border-radius: 4px"]),
    (["pre .copy-button"], ["color: var(--fwl-muted)"]),
    (
        ["pre .copy-button:hover", "pre .copy-button:focus"],
        ["color: var(--fwl-link)", "background: var(--fwl-hover)"],
    ),
    (["pre .copy-button.success"], ["color: var(--fwl-fern)"]),
    (["pre .copy-button.error"], ["color: var(--fwl-garnet)"]),
    ([".content pre code"], ["border: 0"]),
    *[([f".hljs-{token}"], [f"color: var(--fwl-{hue})"]) for token, hue in _SYNTAX.items()],
    (["code.language-julia-repl > span.hljs-meta"], ["color: var(--fwl-fern)"]),
    (
        [".hljs-addition"],
        ["color: var(--fwl-fern)", "background-color: var(--fwl-fern-wash)"],
    ),
    (
        [".hljs-deletion"],
        ["color: var(--fwl-garnet)", "background-color: var(--fwl-garnet-wash)"],
    ),
    # Admonitions: the base style serves custom categories and details blocks
    (
        [".admonition"],
        ["border-color: var(--fwl-line)", "background-color: var(--fwl-sub)", "border-radius: 4px"],
    ),
    (
        [".admonition-header .admonition-anchor"],
        ["color: inherit"],
    ),
    (
        [".admonition > .admonition-header"],
        ["color: var(--fwl-muted)", "background-color: transparent", "font-weight: 500"],
    ),
    (
        [".admonition > .admonition-body"],
        ["color: var(--fwl-text)", "background-color: transparent"],
    ),
    *[
        rule
        for kind, hue in _ADMONITIONS.items()
        for rule in (
            (
                [f".admonition.is-{kind}"],
                [
                    f"border-color: var(--fwl-{hue}-fill)",
                    f"background-color: var(--fwl-{hue}-wash)",
                ],
            ),
            ([f".admonition.is-{kind} > .admonition-header"], [f"color: var(--fwl-{hue})"]),
            ([f".admonition.is-{kind} > .admonition-body"], ["color: var(--fwl-text)"]),
        )
    ],
    # Docstrings
    (
        ["details.docstring"],
        [
            "border: 1px solid var(--fwl-line)",
            "border-radius: 4px",
            "background-color: transparent",
        ],
    ),
    (
        ["details.docstring > summary"],
        [
            "background-color: var(--fwl-sub)",
            "border-bottom-color: var(--fwl-line)",
            "color: var(--fwl-text)",
        ],
    ),
    (["details.docstring > summary::before", ".docstring-category"], ["color: var(--fwl-muted)"]),
    (
        [
            "details.docstring > section > a.docs-sourcelink:not(body)",
            "details.docstring > section > a.docs-sourcelink:not(body):hover",
        ],
        [
            "background-color: var(--fwl-hover)",
            "border-color: transparent",
            "color: var(--fwl-text)",
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
    parts = [header, _font_faces(), _variables("light"), _variables("dark")]
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
    dest = Path(dest)
    fonts = dest / FONT_DIR
    fonts.mkdir(parents=True, exist_ok=True)
    for _, file, _, _, _ in _FONT_FACES:
        shutil.copyfile(fonts_dir() / "woff2" / file, fonts / file)
    for lic in _LICENCES:
        shutil.copyfile(fonts_dir() / lic, fonts / lic)
    css = dest / CSS_NAME
    css.write_text(documenter_css(), encoding="utf-8")
    return css


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
