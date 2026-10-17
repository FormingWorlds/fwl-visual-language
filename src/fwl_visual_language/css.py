"""Web stylesheets: CSS custom properties and the Tailwind v4 theme block.

``tokens_css`` gives every ramp step, role and figure colour as a ``--fwl-*``
custom property. Dark is the default on ``:root``; the light (mist) theme
applies when the page sets ``data-theme="light"``, or when the visitor's
system prefers light and the page sets no ``data-theme``.

``tailwind_theme_css`` gives the ``@theme`` block that the lab website builds
its utility classes from (``bg-ink-950``, ``text-signal-300``), in the same
``oklch()`` form the site uses.
"""

from . import __version__, fonts_dir, oklch_css, palette, ramp, roles, tokens

__all__ = ["tailwind_theme_css", "tokens_css", "web_fonts_css"]

_HEADER = (
    "/* Forming Worlds Lab {what} (fwl-visual-language {version}). Generated from "
    "the lab tokens; edit tokens/fwl.json, not this file. */\n"
)


_GENERIC = {"serif", "sans-serif", "monospace", "system-ui", "ui-monospace", "ui-sans-serif"}


def _font_stack(primary, fallback):
    # family names are quoted; CSS generic keywords and vendor keywords must not be
    names = list(dict.fromkeys([primary, *fallback]))
    return ", ".join(n if n in _GENERIC or n.startswith("-") else f'"{n}"' for n in names)


def _role_lines(mode, indent="  "):
    return [f"{indent}--fwl-{name}: {value};" for name, value in roles(mode).items()]


def _palette_lines(mode, indent="  "):
    return [
        f"{indent}--fwl-figure-{i}: {hexv};  /* {name} */"
        for i, (name, hexv) in enumerate(palette(mode), start=1)
    ]


def tokens_css():
    """Return the custom-property stylesheet for any web page.

    Returns
    -------
    str
        CSS text: ramp steps (``--fwl-ink-950``), font roles, and the roles and
        figure colours of the dark theme on ``:root`` with the light theme as
        an override.
    """
    t = tokens()
    fonts = t["fonts"]
    base = []
    for name in t["ramps"]:
        base += [f"  --fwl-{name}-{step}: {hexv};" for step, hexv in ramp(name).items()]
    base += [
        f"  --fwl-font-text: {_font_stack(fonts['text'], fonts['fallback_sans'])};",
        f"  --fwl-font-math: {_font_stack(fonts['math'], fonts['fallback_sans'])};",
        f"  --fwl-font-mono: {_font_stack(fonts['mono'], fonts['fallback_mono'])};",
    ]
    dark = _role_lines("dark") + _palette_lines("dark") + ["  color-scheme: dark;"]
    light = _role_lines("light", "    ") + _palette_lines("light", "    ")
    light.append("    color-scheme: light;")
    out = [_HEADER.format(what="design tokens", version=__version__)]
    out.append(":root {\n" + "\n".join(base + dark) + "\n}\n")
    out.append(
        '@media (prefers-color-scheme: light) {\n  :root:not([data-theme="dark"]) {\n'
        + "\n".join(light)
        + "\n  }\n}\n"
    )
    out.append(':root[data-theme="light"] {\n' + "\n".join(x[2:] for x in light) + "\n}\n")
    return "\n".join(out)


def tailwind_theme_css():
    """Return the Tailwind v4 ``@theme`` block of the lab website.

    Returns
    -------
    str
        An ``@theme { ... }`` block with ``--color-<ramp>-<step>`` in the
        website's ``oklch()`` form and the font roles. Tailwind turns each entry
        into utility classes.
    """
    t = tokens()
    fonts = t["fonts"]
    lines = []
    for name in t["ramps"]:
        lines += [
            f"  --color-{name}-{step}: {oklch_css(name, step)};"
            for step in t["ramps"][name]["steps"]
        ]
    lines += [
        f"  --font-sans: {_font_stack(fonts['text'], fonts['fallback_sans'])};",
        f"  --font-mono: {_font_stack(fonts['mono'], fonts['fallback_mono'])};",
        f"  --font-math: {_font_stack(fonts['math'], fonts['fallback_sans'])};",
    ]
    return (
        _HEADER.format(what="Tailwind theme", version=__version__)
        + "@theme {\n"
        + "\n".join(lines)
        + "\n}\n"
    )


_WEB_FACES = (
    ("Geist", "Geist-Regular.woff2", "normal", 400, None),
    ("Geist", "Geist-Italic.woff2", "italic", 400, None),
    ("Geist", "Geist-Medium.woff2", "normal", 500, None),
    ("Geist", "Geist-MediumItalic.woff2", "italic", 500, None),
    ("Geist", "Geist-SemiBold.woff2", "normal", 600, None),
    ("Geist Mono", "GeistMono-Regular.woff2", "normal", 400, None),
    ("Geist Mono", "GeistMono-Medium.woff2", "normal", 500, None),
    ("Inter", "Inter-Regular.woff2", "normal", 400, None),
    ("Inter", "Inter-Italic.woff2", "italic", 400, None),
    ("Inter", "Inter-Medium.woff2", "normal", 500, None),
    ("Inter", "Inter-MediumItalic.woff2", "italic", 500, None),
)


def web_fonts_css(font_dir="fonts"):
    """Return ``@font-face`` rules for self-hosting the lab fonts.

    Parameters
    ----------
    font_dir : str
        URL path of the folder that holds the ``woff2`` files, relative to the
        stylesheet.

    Returns
    -------
    str
        One ``@font-face`` rule per bundled web font.

    Raises
    ------
    FileNotFoundError
        If a listed font file is missing from the package.
    """
    out = [_HEADER.format(what="web fonts", version=__version__)]
    for family, file, style, weight, _ in _WEB_FACES:
        if not (fonts_dir() / "woff2" / file).is_file():
            raise FileNotFoundError(file)
        out.append(
            "@font-face {\n"
            f'  font-family: "{family}";\n'
            f'  src: url("{font_dir}/{file}") format("woff2");\n'
            f"  font-style: {style};\n"
            f"  font-weight: {weight};\n"
            "  font-display: swap;\n"
            "}\n"
        )
    return "\n".join(out)
