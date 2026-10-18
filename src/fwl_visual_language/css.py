"""Web stylesheets: CSS custom properties, the Tailwind v4 theme block, web fonts.

``tokens_css`` gives every ramp step, role and figure colour as a ``--fwl-*``
custom property. Dark is the default on ``:root``; the light (mist) theme
applies when the page sets ``data-theme="light"``, or when the visitor's
system prefers light and the page sets no ``data-theme``.

``tailwind_theme_css`` gives the ``@theme`` block that the lab website builds
its utility classes from (``bg-ink-950``, ``text-signal-300``), in the same
``oklch()`` form the site uses. ``tailwind_light_css`` gives the website's light
theme: the same variables reassigned to light values (``website_light`` in the
token file), and ``.on-dark`` for areas that keep the dark ramp.

``install_web_fonts`` writes ``fwl-fonts.css`` with the ``woff2`` files and
their licences::

    python -m fwl_visual_language.css static/css
"""

import argparse
import math

from . import MAX_CHROMA, __version__, _oklch_text, color, oklch_css, palette, ramp, roles, tokens
from ._web import FONT_DIR, font_faces_css, font_stack, install

__all__ = [
    "install_web_fonts",
    "tailwind_light_css",
    "tailwind_theme_css",
    "tokens_css",
    "web_fonts_css",
]

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


def _is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _light_value(name, step):
    """Return the website's light value of one ramp step in CSS form."""
    t = tokens()
    where = f"website_light.{name}.{step}"
    value = t["website_light"][name][step]
    if isinstance(value, list):
        hue = t["ramps"][name]["hue"]
        if len(value) == 2:
            value = [*value, hue]
        if len(value) != 3 or not all(_is_number(x) for x in value):
            raise ValueError(f"{where}: expected [L, C] on a ramp with a hue, or [L, C, h]")
        L, C, h = value
        if not (0 <= L <= 1 and 0 <= C <= MAX_CHROMA):
            raise ValueError(f"{where}: L must lie in [0, 1] and C in [0, {MAX_CHROMA}]")
        return _oklch_text(L, C, h)
    if not isinstance(value, str):
        raise ValueError(f"{where}: expected a ramp step, #RRGGBB or an OKLCH list")
    try:
        color(value)  # an unknown ramp or step raises KeyError, a malformed hex ValueError
    except (KeyError, ValueError) as err:
        raise type(err)(f"{where}: {err}") from err
    if value.startswith("#"):
        return value.upper()
    ref_ramp, _, ref_step = value.partition("-")
    return oklch_css(ref_ramp, ref_step)


def tailwind_light_css():
    """Return the light theme of the lab website, over the Tailwind ``@theme`` variables.

    Returns
    -------
    str
        CSS text: ``color-scheme: dark`` on ``:root``; every ``--color-<ramp>-<step>``
        reassigned to its light value under ``prefers-color-scheme: light`` (unless
        the page sets ``data-theme="dark"``) and under ``data-theme="light"``; and
        ``.on-dark``, which restores the dark values for its subtree.

    Raises
    ------
    KeyError
        If ``website_light`` and the ramps differ in their ramps or steps, or a
        value names an unknown ramp step.
    ValueError
        If a value is not a ramp step, a ``#RRGGBB`` literal, or an ``[L, C]``
        (ramp with a hue) or ``[L, C, h]`` list with L in [0, 1] and C in
        [0, ``MAX_CHROMA``].

    Notes
    -----
    ``website_light`` follows the website's classes, so a few steps differ from
    what the light roles give for the same dark step (heading, line, axis, note,
    warning); ``tests/test_css_mpl.py`` lists them.
    """
    t = tokens()
    table = t["website_light"]
    if set(table) != set(t["ramps"]):
        raise KeyError(f"website_light ramps {sorted(table)} differ from {sorted(t['ramps'])}")
    light, dark = [], []
    for name in t["ramps"]:
        steps = t["ramps"][name]["steps"]
        if set(table[name]) != set(steps):
            missing, extra = set(steps) - set(table[name]), set(table[name]) - set(steps)
            raise KeyError(
                f"website_light.{name}: missing {sorted(missing)}, unknown {sorted(extra)}"
            )
        for step in steps:
            var = f"--color-{name}-{step}"
            light.append(f"{var}: {_light_value(name, step)};")
            dark.append(f"  {var}: {oklch_css(name, step)};")
    light.append("color-scheme: light;")
    dark.append("  color-scheme: dark;")
    return "\n".join(
        [
            _HEADER.format(what="website light theme", version=__version__),
            ":root {\n  color-scheme: dark;\n}\n",
            '@media (prefers-color-scheme: light) {\n  :root:not([data-theme="dark"]) {\n'
            + "\n".join("    " + x for x in light)
            + "\n  }\n}\n",
            ':root[data-theme="light"] {\n' + "\n".join("  " + x for x in light) + "\n}\n",
            ".on-dark {\n" + "\n".join(dark) + "\n}\n",
        ]
    )


def web_fonts_css(font_dir=FONT_DIR):
    """Return ``@font-face`` rules for self-hosting the lab fonts.

    Parameters
    ----------
    font_dir : str
        URL path of the folder with the ``woff2`` files, relative to the
        stylesheet, without a trailing ``/``. ``install_web_fonts`` writes them
        to ``fwl-fonts``.

    Returns
    -------
    str
        One rule per bundled web font. Inter is loaded in full, so the math role
        (``--fwl-font-math``) renders Latin and Greek; text in Geist takes from
        it any glyph Geist lacks, Greek included.
    """
    faces = font_faces_css(font_dir, greek_only_math=False)
    return _HEADER.format(what="web fonts", version=__version__) + "\n" + faces


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
