"""Helpers shared by the web generators: colour mixing, text-safe colours, fonts."""

import shutil
from pathlib import Path

from . import contrast, fonts_dir, tokens

FONT_DIR = "fwl-fonts"
MIN_CONTRAST = 4.5
GREEK = "U+0370-03FF, U+1F00-1FFF"
LICENCES = ("OFL-Geist.txt", "OFL-Inter.txt")
_GENERIC = {"serif", "sans-serif", "monospace", "system-ui", "ui-monospace", "ui-sans-serif"}

# (role, file, style, weight). Faces of the math role cover only Greek on pages
# whose text face is not Inter; the text face has no Greek.
FACES = (
    ("text", "Geist-Regular.woff2", "normal", 400),
    ("text", "Geist-Italic.woff2", "italic", 400),
    ("text", "Geist-Medium.woff2", "normal", 500),
    ("text", "Geist-MediumItalic.woff2", "italic", 500),
    ("text", "Geist-SemiBold.woff2", "normal", 600),
    ("mono", "GeistMono-Regular.woff2", "normal", 400),
    ("mono", "GeistMono-Medium.woff2", "normal", 500),
    ("math", "Inter-Regular.woff2", "normal", 400),
    ("math", "Inter-Italic.woff2", "italic", 400),
    ("math", "Inter-Medium.woff2", "normal", 500),
    ("math", "Inter-MediumItalic.woff2", "italic", 500),
)


def _rgb(hex_color):
    h = hex_color.lstrip("#")
    return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))


def _hex(rgb):
    return "#" + "".join(f"{round(max(0, min(255, c))):02X}" for c in rgb)


def mix(a, b, t):
    """Return the colour a fraction ``t`` of the way from ``a`` to ``b`` (sRGB)."""
    return _hex(tuple(x + (y - x) * t for x, y in zip(_rgb(a), _rgb(b), strict=True)))


def text_safe(color, ink, backgrounds):
    """Move ``color`` toward ``ink`` until it reads at 4.5:1 on every background."""
    for step in range(101):
        out = mix(color, ink, step / 100)
        if all(contrast(out, bg) >= MIN_CONTRAST for bg in backgrounds):
            return out
    return ink


def font_stack(role, extra=()):
    """Return the CSS ``font-family`` list for a font role of the tokens.

    Parameters
    ----------
    role : str
        ``text``, ``math`` or ``mono``.
    extra : sequence of str
        Families to insert after the token family, before the fallbacks.

    Returns
    -------
    str
        Family names in quotes, CSS generic and vendor keywords bare, no
        duplicates. The text stack lists the math face second, so Greek, which
        the text face lacks, falls back to it.
    """
    f = tokens()["fonts"]
    fallback = f["fallback_mono"] if role == "mono" else f["fallback_sans"]
    names = [f[role], *extra]
    if role == "text":
        names.append(f["math"])
    names = list(dict.fromkeys([*names, *fallback]))
    return ", ".join(n if n in _GENERIC or n.startswith("-") else f'"{n}"' for n in names)


def font_faces_css(font_dir=FONT_DIR, greek_only_math=True):
    """Return ``@font-face`` rules for the bundled web fonts.

    Parameters
    ----------
    font_dir : str
        URL path of the folder with the ``woff2`` files, relative to the stylesheet.
    greek_only_math : bool
        Limit the math faces to Greek code points, so a browser downloads them
        only for pages that use Greek.

    Returns
    -------
    str
        One rule per face.
    """
    family = tokens()["fonts"]
    out = []
    for role, file, style, weight in FACES:
        urange = f"  unicode-range: {GREEK};\n" if role == "math" and greek_only_math else ""
        out.append(
            "@font-face {\n"
            f'  font-family: "{family[role]}";\n'
            f'  src: url("{font_dir}/{file}") format("woff2");\n'
            f"  font-style: {style};\n"
            f"  font-weight: {weight};\n"
            f"{urange}"
            "  font-display: swap;\n"
            "}\n"
        )
    return "\n".join(out)


def install(dest, name, css):
    """Write a stylesheet plus the web fonts and their licences into ``dest``.

    Parameters
    ----------
    dest : str or pathlib.Path
        Target folder; created if it does not exist.
    name : str
        File name of the stylesheet.
    css : str
        Stylesheet text.

    Returns
    -------
    pathlib.Path
        Path of the written stylesheet.

    Raises
    ------
    OSError
        If ``dest`` exists and is not a folder, or cannot be written.
    """
    dest = Path(dest)
    fonts = dest / FONT_DIR
    fonts.mkdir(parents=True, exist_ok=True)
    for _, file, _, _ in FACES:
        shutil.copyfile(fonts_dir() / "woff2" / file, fonts / file)
    for lic in LICENCES:
        shutil.copyfile(fonts_dir() / lic, fonts / lic)
    out = dest / name
    out.write_text(css, encoding="utf-8")
    return out
