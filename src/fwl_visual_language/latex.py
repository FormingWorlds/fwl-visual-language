"""LaTeX package ``fwl.sty``: lab colours and text fonts for letters, proposals and the CV.

The package defines every ramp step, the paper roles and the figure palette as
``xcolor`` colours, and sets Geist as the document face with Geist Mono for
code, through ``fontspec`` (LuaLaTeX or XeLaTeX). Math fonts are left to the
document.

Install it next to a document::

    python -m fwl_visual_language.latex path/to/document
"""

import argparse
import re
import shutil
from datetime import date
from pathlib import Path

from . import __version__, fonts_dir, palette, ramp, roles, tokens

__all__ = ["install_latex", "latex_name", "sty"]

STY_NAME = "fwl.sty"
FONT_DIR = "fwl-fonts"
_TTF = (
    "Geist-Regular.ttf",
    "Geist-Italic.ttf",
    "Geist-Medium.ttf",
    "Geist-MediumItalic.ttf",
    "Geist-SemiBold.ttf",
    "GeistMono-Regular.ttf",
    "GeistMono-Medium.ttf",
)
_LICENCES = ("OFL-Geist.txt",)


def latex_name(*parts):
    """Return a colour name in the package's camel case, for example ``fwlInkNineFifty``.

    Parameters
    ----------
    *parts : str
        Name parts such as ``"ink"``, ``"950"`` or ``"link-hover"``.

    Returns
    -------
    str
        ``fwl`` followed by each part in title case, letters only, with digits
        kept, for example ``fwlInk950`` or ``fwlLinkHover``.
    """
    words = []
    for p in parts:
        words += [w for w in re.split(r"[^A-Za-z0-9]+", p) if w]
    return "fwl" + "".join(w[:1].upper() + w[1:] for w in words)


def _define(name, hexv):
    return f"\\definecolor{{{name}}}{{HTML}}{{{hexv[1:]}}}"


def sty(release=None):
    """Return the text of ``fwl.sty``.

    Parameters
    ----------
    release : datetime.date, optional
        Date written into ``\\ProvidesPackage``. Defaults to 2026-10-17 so the
        generated file does not change from day to day.

    Returns
    -------
    str
        LaTeX package source.
    """
    release = release or date(2026, 10, 17)
    fonts = tokens()["fonts"]
    lines = [
        "% Forming Worlds Lab LaTeX package (fwl-visual-language "
        f"{__version__}). Generated from the lab tokens; edit tokens/fwl.json, not this file.",
        "\\NeedsTeXFormat{LaTeX2e}",
        f"\\ProvidesPackage{{fwl}}[{release:%Y/%m/%d} v{__version__} Forming Worlds Lab]",
        "\\RequirePackage{xcolor}",
        "\\RequirePackage{fontspec}",
        "",
        "% Ramps",
    ]
    for name in tokens()["ramps"]:
        lines += [_define(latex_name(name, step), h) for step, h in ramp(name).items()]
    lines += ["", "% Roles on white paper"]
    lines += [_define(latex_name(r), h) for r, h in roles("paper").items()]
    lines += ["", "% Figure palette, light ground"]
    lines += [_define(latex_name(n), h) for n, h in palette("paper")]
    lines += [
        "",
        "% Fonts: the files sit in fwl-fonts/ next to this package",
        "\\providecommand{\\fwlfontpath}{fwl-fonts/}",
        f"\\setmainfont{{{fonts['text']}}}[",
        "  Path=\\fwlfontpath,",
        "  UprightFont=Geist-Regular.ttf,",
        "  ItalicFont=Geist-Italic.ttf,",
        "  BoldFont=Geist-SemiBold.ttf,",
        "  BoldItalicFont=Geist-MediumItalic.ttf,",
        "  FontFace={md}{n}{Geist-Medium.ttf},",
        "  FontFace={md}{it}{Geist-MediumItalic.ttf}]",
        f"\\setsansfont{{{fonts['text']}}}[",
        "  Path=\\fwlfontpath,",
        "  UprightFont=Geist-Regular.ttf,",
        "  ItalicFont=Geist-Italic.ttf,",
        "  BoldFont=Geist-SemiBold.ttf,",
        "  BoldItalicFont=Geist-MediumItalic.ttf]",
        f"\\setmonofont{{{fonts['mono']}}}[",
        "  Path=\\fwlfontpath,",
        "  UprightFont=GeistMono-Regular.ttf,",
        "  BoldFont=GeistMono-Medium.ttf]",
        "\\newcommand{\\fwlmedium}{\\fontseries{md}\\selectfont}",
        "\\color{fwlText}",
        "\\endinput",
        "",
    ]
    return "\n".join(lines)


def install_latex(dest):
    """Write ``fwl.sty``, the Geist fonts and their licence into ``dest``.

    Parameters
    ----------
    dest : str or pathlib.Path
        Folder of the document. It is created if it does not exist.

    Returns
    -------
    pathlib.Path
        Path of the written package file.

    Raises
    ------
    OSError
        If ``dest`` exists and is not a folder, or cannot be written.
    """
    dest = Path(dest)
    fonts = dest / FONT_DIR
    fonts.mkdir(parents=True, exist_ok=True)
    for file in _TTF:
        shutil.copyfile(fonts_dir() / "ttf" / file, fonts / file)
    for lic in _LICENCES:
        shutil.copyfile(fonts_dir() / lic, fonts / lic)
    out = dest / STY_NAME
    out.write_text(sty(), encoding="utf-8")
    return out


def main(argv=None):
    """Command line entry point: ``python -m fwl_visual_language.latex DEST``."""
    parser = argparse.ArgumentParser(
        prog="python -m fwl_visual_language.latex",
        description="Write the Forming Worlds Lab LaTeX package and fonts.",
    )
    parser.add_argument("dest", help="folder of the LaTeX document")
    args = parser.parse_args(argv)
    print(install_latex(args.dest))


if __name__ == "__main__":
    main()
