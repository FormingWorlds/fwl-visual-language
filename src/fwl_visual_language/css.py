"""Web stylesheets: CSS custom properties, the Tailwind v4 theme block, web fonts.

``tokens_css`` gives every ramp step, role and figure colour as a ``--fwl-*``
custom property. Dark is the default on ``:root``; the light (mist) theme
applies when the page sets ``data-theme="light"``, or when the visitor's
system prefers light and the page sets no ``data-theme``.

``tailwind_theme_css`` gives the ``@theme`` block that the lab website builds
its utility classes from (``bg-ink-950``, ``text-signal-300``), in the same
``oklch()`` form the site uses.

``install_web_fonts`` writes ``fwl-fonts.css`` with the ``woff2`` files and
their licences::

    python -m fwl_visual_language.css static/css
"""

import argparse

from . import __version__, oklch_css, palette, ramp, roles, tokens
from ._web import font_faces_css, font_stack, install

__all__ = ["install_web_fonts", "tailwind_theme_css", "tokens_css", "web_fonts_css"]

FONTS_CSS_NAME = "fwl-fonts.css"
_HEADER = (
    "/* Forming Worlds Lab {what} (fwl-visual-language {version}). Generated from "
    "the lab tokens; edit tokens/fwl.json, not this file. */\n"
)


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
        an override. The light figure colours reach 3:1 on white
        (``--fwl-surface``), not on the mist ground; draw charts on a surface.
    """
    base = []
    for name in tokens()["ramps"]:
        base += [f"  --fwl-{name}-{step}: {hexv};" for step, hexv in ramp(name).items()]
    base += [f"  --fwl-font-{role}: {font_stack(role)};" for role in ("text", "math", "mono")]
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
    lines = []
    for name in t["ramps"]:
        lines += [
            f"  --color-{name}-{step}: {oklch_css(name, step)};"
            for step in t["ramps"][name]["steps"]
        ]
    lines += [
        f"  --font-sans: {font_stack('text')};",
        f"  --font-mono: {font_stack('mono')};",
        f"  --font-math: {font_stack('math')};",
    ]
    return (
        _HEADER.format(what="Tailwind theme", version=__version__)
        + "@theme {\n"
        + "\n".join(lines)
        + "\n}\n"
    )


def web_fonts_css():
    """Return ``@font-face`` rules for self-hosting the lab fonts.

    Returns
    -------
    str
        One rule per bundled web font, with the files in ``fwl-fonts/`` next to
        the stylesheet. Inter is limited to Greek, which Geist lacks.
    """
    return _HEADER.format(what="web fonts", version=__version__) + "\n" + font_faces_css()


def install_web_fonts(dest):
    """Write ``fwl-fonts.css``, the ``woff2`` files and their licences into ``dest``.

    Parameters
    ----------
    dest : str or pathlib.Path
        Target folder; created if it does not exist.

    Returns
    -------
    pathlib.Path
        Path of the written stylesheet.

    Raises
    ------
    OSError
        If ``dest`` exists and is not a folder, or cannot be written.
    """
    return install(dest, FONTS_CSS_NAME, web_fonts_css())


def main(argv=None):
    """Command line entry point: ``python -m fwl_visual_language.css DEST``."""
    parser = argparse.ArgumentParser(
        prog="python -m fwl_visual_language.css",
        description="Write the Forming Worlds Lab web font stylesheet and fonts.",
    )
    parser.add_argument("dest", help="folder for fwl-fonts.css and fwl-fonts/")
    args = parser.parse_args(argv)
    print(install_web_fonts(args.dest))


if __name__ == "__main__":
    main()
