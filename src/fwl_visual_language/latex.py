"""LaTeX packages: ``fwl.sty`` (colours and fonts) and ``fwlproposal.sty`` (page style).

``fwl.sty`` defines every ramp step, the paper roles and the figure palette as
``xcolor`` colours, and sets Geist as the document face with Geist Mono for
code, through ``fontspec`` (LuaLaTeX or XeLaTeX). With the ``math`` option it
loads ``unicode-math``: letters, digits and Greek in math come from Inter (Geist
has no Greek), operators, delimiters and large symbols from STIX Two Math.
``fwlproposal.sty`` loads ``fwl`` with ``math`` and sets the page, headings,
captions, links and footer of proposals and reports.

Install them next to a document::

    python -m fwl_visual_language.latex path/to/document
"""

import argparse
import re
import shutil
from datetime import date
from pathlib import Path

from . import __version__, fonts_dir, palette, ramp, roles, tokens

__all__ = ["install_latex", "latex_name", "proposal_sty", "sty"]

STY_NAME = "fwl.sty"
PROPOSAL_NAME = "fwlproposal.sty"
FONT_DIR = "fwl-fonts"
MATH_FONT = "STIXTwoMath-Regular.otf"
_TTF = (
    "Geist-Regular.ttf",
    "Geist-Italic.ttf",
    "Geist-Medium.ttf",
    "Geist-MediumItalic.ttf",
    "Geist-SemiBold.ttf",
    "Geist-SemiBoldItalic.ttf",
    "GeistMono-Regular.ttf",
    "GeistMono-Medium.ttf",
    "Inter-Regular.ttf",
    "Inter-Italic.ttf",
)
_LICENCES = ("OFL-Geist.txt", "OFL-Inter.txt", "OFL-STIX.txt")
# Bold is SemiBold (600) upright and italic; \fwlmedium selects Medium (500).
_GEIST = """
  Path=\\fwlfontpath,
  UprightFont=Geist-Regular.ttf,
  ItalicFont=Geist-Italic.ttf,
  BoldFont=Geist-SemiBold.ttf,
  BoldItalicFont=Geist-SemiBoldItalic.ttf,
  FontFace={md}{n}{Geist-Medium.ttf},
  FontFace={md}{it}{Geist-MediumItalic.ttf}]"""


def latex_name(*parts):
    """Return a colour name in the package's camel case, for example ``fwlInk950``.

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
        "\\newif\\iffwl@math",
        "\\DeclareOption{math}{\\fwl@mathtrue}",
        "\\ProcessOptions\\relax",
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
        f"\\setmainfont{{{fonts['text']}}}[" + _GEIST,
        f"\\setsansfont{{{fonts['text']}}}[" + _GEIST,
        f"\\setmonofont{{{fonts['mono']}}}[",
        "  Path=\\fwlfontpath,",
        "  UprightFont=GeistMono-Regular.ttf,",
        "  BoldFont=GeistMono-Medium.ttf,",
        "  FontFace={md}{n}{GeistMono-Medium.ttf}]",
        "\\newcommand{\\fwlmedium}{\\fontseries{md}\\selectfont}",
        "",
        f"% Math (option math): letters, digits and Greek from {fonts['math']},",
        "% everything else from STIX Two",
        "\\iffwl@math",
        "  \\RequirePackage{unicode-math}",
        f"  \\setmathfont{{{MATH_FONT}}}[Path=\\fwlfontpath]",
        "  \\setmathfont{Inter-Regular.ttf}[Path=\\fwlfontpath,",
        "    range={up/{latin,Latin,num,greek,Greek}}]",
        "  \\setmathfont{Inter-Italic.ttf}[Path=\\fwlfontpath,",
        "    range={it/{latin,Latin,greek,Greek}}]",
        "\\fi",
        "\\color{fwlText}",
        "\\endinput",
        "",
    ]
    return "\n".join(lines)


def proposal_sty(release=None):
    """Return the text of ``fwlproposal.sty``, the page style of proposals and reports.

    Parameters
    ----------
    release : datetime.date, optional
        Date written into ``\\ProvidesPackage``; the same default as :func:`sty`.

    Returns
    -------
    str
        LaTeX package source. It loads ``fwl`` with the ``math`` option, A4
        pages with 2 cm margins, numbered Geist Medium headings with the number
        in the accent colour, muted captions, lab-coloured links and a footer
        with ``\\fwlfooter`` on the left and the page number on the right.
    """
    release = release or date(2026, 10, 17)
    return "\n".join(
        [
            "% Forming Worlds Lab proposal and report style (fwl-visual-language "
            f"{__version__}). Generated; edit the generator, not this file.",
            "\\NeedsTeXFormat{LaTeX2e}",
            f"\\ProvidesPackage{{fwlproposal}}[{release:%Y/%m/%d} v{__version__} "
            "Forming Worlds Lab]",
            "\\RequirePackage[math]{fwl}",
            "\\RequirePackage[a4paper,margin=2cm]{geometry}",
            "\\RequirePackage{titlesec}",
            "\\RequirePackage{caption}",
            "\\RequirePackage{enumitem}",
            "\\RequirePackage{fancyhdr}",
            "\\RequirePackage[colorlinks=true,linkcolor=fwlLink,urlcolor=fwlLink,"
            "citecolor=fwlLink]{hyperref}",
            "",
            "\\linespread{1.08}\\selectfont",
            "\\setlength{\\parindent}{0pt}",
            "\\setlength{\\parskip}{0.5em}",
            "\\setlist{itemsep=0.15em,topsep=0.3em}",
            "",
            "% Headings: Geist Medium, the number in the accent colour",
            "\\titleformat{\\section}{\\fwlmedium\\large\\color{fwlHeading}}"
            "{\\textcolor{fwlAccent}{\\thesection}}{0.6em}{}",
            "\\titleformat{\\subsection}{\\fwlmedium\\normalsize\\color{fwlHeading}}"
            "{\\textcolor{fwlAccent}{\\thesubsection}}{0.6em}{}",
            "\\titleformat{\\paragraph}[runin]{\\fwlmedium\\color{fwlHeading}}{}{0pt}{}[.]",
            "\\titlespacing*{\\section}{0pt}{1.1em}{0.35em}",
            "\\titlespacing*{\\subsection}{0pt}{0.9em}{0.25em}",
            "\\titlespacing*{\\paragraph}{0pt}{0.5em}{0.5em}",
            "",
            "% Captions: label in the heading colour, text muted",
            "\\DeclareCaptionFont{fwlmuted}{\\color{fwlMuted}}",
            "\\DeclareCaptionFont{fwlheading}{\\fwlmedium\\color{fwlHeading}}",
            "\\captionsetup{font={small,fwlmuted},labelfont=fwlheading,labelsep=period,"
            "singlelinecheck=false}",
            "",
            "% Title block: \\fwltitle{title}{subtitle}",
            "\\newcommand{\\fwltitle}[2]{\\begingroup\\setlength{\\parskip}{0pt}"
            "{\\fwlmedium\\LARGE\\color{fwlHeading}#1\\par}"
            "\\vspace{0.3em}{\\large\\color{fwlMuted}#2\\par}"
            "\\vspace{0.5em}{\\color{fwlAccent}\\rule{3cm}{0.6pt}}\\par\\endgroup\\vspace{0.8em}}",
            "",
            "% Footer: \\renewcommand{\\fwlfooter}{...} sets the left part",
            "\\newcommand{\\fwlfooter}{}",
            "\\pagestyle{fancy}",
            "\\fancyhf{}",
            "\\renewcommand{\\headrulewidth}{0pt}",
            "\\fancyfoot[L]{\\ttfamily\\footnotesize\\color{fwlMuted}\\fwlfooter}",
            "\\fancyfoot[R]{\\ttfamily\\footnotesize\\color{fwlMuted}\\thepage}",
            "\\endinput",
            "",
        ]
    )


def install_latex(dest):
    """Write ``fwl.sty``, ``fwlproposal.sty``, the fonts and their licences into ``dest``.

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
    shutil.copyfile(fonts_dir() / "otf" / MATH_FONT, fonts / MATH_FONT)
    for lic in _LICENCES:
        shutil.copyfile(fonts_dir() / lic, fonts / lic)
    (dest / PROPOSAL_NAME).write_text(proposal_sty(), encoding="utf-8")
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
